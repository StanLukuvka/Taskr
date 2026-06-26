from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.mapping import resolve_mapping, resolve_output_mapping, resolve_path


# =============================================================================
# TaskrRunner — core workflow execution engine
# =============================================================================
#
# A run is a single execution of a goal's active flow version.  Each top-level
# node in the flow gets a persisted ``node_state`` record.  The runner advances
# a run one logical step at a time via ``tick()``.  It is otherwise stateless:
# all state lives in the repository, and the runner re-reads it on every call.
#
# Supported node kinds at the top level:
#   * ``action`` — a single unit of work backed by a binding (API or Hermes).
#   * ``foreach`` — a loop that creates per-item iterations and runs child
#     action nodes for each item.
#
# Key invariants maintained by this module:
#   * A node_state is dispatched at most once.  Dispatch is recorded by
#     incrementing ``attempt`` and moving the status to ``running``.
#   * A run is paused while any of its node_states are blocked on a question.
#   * Completed outputs are written back via ``output_mapping`` so downstream
#     nodes can read them as ``$nodes.<node_id>.output``.
#   * Failure in any node fails the whole run.
# =============================================================================


class TaskrRunner:
    """The core state machine for executing Taskr workflow runs.

    The runner is responsible for creating runs, advancing them one logical
    step at a time (a "tick"), and integrating results returned by external
    systems (APIs or Hermes tasks).  It is designed to be stateless with
    respect to run data: the injected ``repo`` is the source of truth and is
    read from/written to on every transition.

    Attributes
    ----------
    repo
        Persistence layer for goals, flow versions, runs, node_states, loop
        states, questions, and bindings.
    api
        Integration client for API-backed bindings.  Must provide ``start()``
        and ``inspect(external_ref)``.
    hermes
        Integration client for Hermes-backed bindings.  Must provide
        ``create_task(input)``, ``inspect_task(ref_or_id)``, and
        ``answer_question(hermes_task_id, answer)``.
    """

    def __init__(self, repo, api_caller, hermes_service):
        """Initialize the runner with its persistence and integration services.

        Parameters
        ----------
        repo
            Repository instance used for all state persistence.
        api_caller
            Client responsible for API-style node bindings.
        hermes_service
            Client responsible for Hermes-style node bindings.
        """
        self.repo = repo
        self.api = api_caller
        self.hermes = hermes_service

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def create_run(self, goal_slug: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a new run for ``goal_slug`` and materialize its node_states.

        Steps:
        1. Load the goal by slug; if it does not exist, seed initial data and
           try again.
        2. Load the active flow version for the resolved goal.
        3. Persist a run record bound to the goal and flow version.
        4. Create a ``node_state`` for every top-level node in the flow so
           the run has a concrete state to advance from.

        Parameters
        ----------
        goal_slug : str
            Human-readable slug that identifies the goal to run.
        context : dict[str, Any] | None, optional
            Optional key/value context injected into the run and available to
            mappings as ``$scope``.

        Returns
        -------
        dict[str, Any]
            The newly created run record.

        Raises
        ------
        ValueError
            If the goal slug cannot be resolved or the goal has no active flow
            version.
        """
        # Resolve the goal.  Seeding is a fallback for empty dev/test DBs.
        goal = self.repo.load_goal_by_slug(goal_slug)
        if goal is None:
            self.repo.seed_data()
            goal = self.repo.load_goal_by_slug(goal_slug)
        if not goal:
            raise ValueError(f"unknown goal slug: {goal_slug}")

        # A goal must have an active flow version before it can be executed.
        flow_version = self.repo.load_active_flow_version(goal["id"])
        if not flow_version:
            raise ValueError(f"no active flow version for goal: {goal['id']}")

        # Persist the run and bind it to the resolved goal/flow version.
        run = self.repo.create_run(goal["id"], flow_version["id"], context or {})

        # Materialize node_states for every top-level node.  Child nodes of
        # foreach loops are created lazily when their iteration is advanced.
        for node in self.repo.load_top_level_nodes(flow_version["id"]):
            self.repo.get_or_create_node_state(run["id"], node["id"], None)

        return run

    def tick(self, run_id: str | None = None) -> list[str]:
        """Advance active runs by one logical step.

        If ``run_id`` is provided, only that run is advanced (if it exists and
        is in a runnable status).  Otherwise every run whose status is
        ``running`` or ``paused`` is advanced once.

        Parameters
        ----------
        run_id : str | None, optional
            Optional run id to tick.  If omitted, all active runs are ticked.

        Returns
        -------
        list[str]
            The ids of the runs that were advanced.  Empty if no run matched
            or the targeted run was not active.
        """
        # Single-run mode: validate, skip if terminal, and advance.
        if run_id is not None:
            run = self.repo.load_run(run_id)
            if not run:
                raise ValueError(f"unknown run id: {run_id}")
            if run["status"] not in {"running", "paused"}:
                return []
            self.advance_run(run)
            return [run_id]

        # Global mode: advance every run that is still runnable.
        runs = self.repo.list_runs(["running", "paused"])
        results = []
        for run in runs:
            self.advance_run(run)
            results.append(run["id"])
        return results

    def advance_run(self, run: dict[str, Any]) -> None:
        """Advance a single run by evaluating its top-level nodes.

        The runner processes top-level nodes in flow order.  If any node
        reports ``blocked`` the run is paused and advancement stops
        immediately.  If any node is still in progress, the run remains
        ``running`` and the loop breaks after the first non-completed node to
        avoid advancing later nodes before their dependencies finish.  Once all
        top-level nodes are completed, the run itself is marked completed.

        Parameters
        ----------
        run : dict[str, Any]
            The run record to advance.  May be mutated and re-persisted.
        """
        # If the run is paused and still has open questions, nothing can be
        # advanced until a question is answered.
        if run["status"] == "paused" and self.repo.load_open_questions(run["id"]):
            return

        # A paused run with no remaining open questions can resume.  Clear
        # the pause reason so downstream processing can proceed.
        if run["status"] == "paused":
            run["status"] = "running"
            run["pause_reason"] = None
            run = self.repo.save_run(run)

        # Walk top-level nodes.  We assume sequential dependencies: do not
        # advance a later node until all earlier nodes are completed.
        all_completed = True
        for node in self.repo.load_top_level_nodes(run["flow_version_id"]):
            state = self.repo.get_or_create_node_state(run["id"], node["id"], None)
            if state["status"] == "completed":
                # This node is already done; move on to the next one.
                continue

            # Dispatch based on node kind.  Foreach nodes manage their own
            # child iterations; everything else is treated as an action.
            if node["kind"] == "foreach":
                status = self.advance_foreach(run, node, state)
            else:
                status = self.advance_action(run, node, state)

            # Blocked means a question is pending; stop immediately so the run
            # stays paused while the user answers.
            if status == "blocked":
                return

            # Any non-completed status means this node still has work to do.
            # Because later nodes may depend on it, stop advancing the run.
            if status != "completed":
                all_completed = False
                break

        # If every top-level node completed during this pass, finalize the run.
        if all_completed:
            run = self.repo.load_run(run["id"])
            run["status"] = "completed"
            run["pause_reason"] = None
            run["finished_at"] = self._now()
            self.repo.save_run(run)

    # ------------------------------------------------------------------
    # Node advancement
    # ------------------------------------------------------------------

    def advance_foreach(
        self,
        run: dict[str, Any],
        node: dict[str, Any],
        state: dict[str, Any],
    ) -> str:
        """Advance a ``foreach`` node by iterating over its items.

        On first dispatch the node resolves its ``items_path`` against the
        runtime context and creates a ``loop_state`` plus one
        ``loop_iteration`` record per item.  The runner then walks iterations
        in order and advances each child action node within the iteration.  If
        an iteration is blocked, the whole foreach node is blocked.

        Completed outputs from child nodes are collected into the iteration's
        ``output`` so the parent node's final output can aggregate per-item
        results.

        Parameters
        ----------
        run : dict[str, Any]
            The run record.
        node : dict[str, Any]
            The foreach node definition.
        state : dict[str, Any]
            The node_state for this foreach node.

        Returns
        -------
        str
            The resulting status of the foreach node (e.g. ``completed``,
            ``blocked``, ``running``).
        """
        # Terminal shortcut: nothing more to do for this node.
        if state["status"] == "completed":
            return "completed"

        # First time this foreach node is advanced: build the loop state and
        # create an iteration for every item resolved from items_path.
        if state["status"] in {"pending", "ready"}:
            loop_state = self.repo.get_loop_state(state["id"])
            if loop_state is None:
                loop_state = self.repo.create_loop_state(state["id"])

                # Resolve the collection this loop should iterate over.
                items = resolve_path(node["items_path"], context=self._runtime_context(run)) or []

                # Persist each item with a stable iteration key.  Prefer an
                # explicit ``id`` field when the item is a dict; otherwise fall
                # back to the positional index.
                for position, item in enumerate(items):
                    iteration_key = item.get("id") if isinstance(item, dict) and item.get("id") else str(position)
                    self.repo.create_loop_iteration(loop_state["id"], iteration_key, position, item)

                # Re-read the loop state now that iterations are persisted.
                loop_state = self.repo.get_loop_state(state["id"])

            # Mark the foreach node as running and record its start time.
            state["status"] = "running"
            state["started_at"] = state.get("started_at") or self._now()
            self.repo.save_node_state(state)

        # Load the current loop state and child nodes for this foreach.
        loop_state = self.repo.get_loop_state(state["id"])
        child_nodes = self.repo.load_child_nodes(node["id"])

        # Iterate through loop iterations in order.  Each iteration advances
        # all of its child action nodes before the next iteration starts.
        for iteration in self.repo.load_loop_iterations(loop_state["id"]):
            if iteration["status"] == "completed":
                continue

            # Track the iteration's overall status across its children.
            iteration_status = "completed"

            # Collect non-null outputs from each child so they can be surfaced
            # as the iteration's combined output.
            collected_output: dict[str, Any] = {}

            for child in child_nodes:
                # Get or create the child node_state scoped to this iteration.
                child_state = self.repo.get_or_create_node_state(
                    run["id"], child["id"], iteration["id"]
                )

                # Advance the child action with the current loop item as context.
                child_status = self.advance_action(run, child, child_state, item=iteration["item"])

                # Re-read the persisted child state to capture any output.
                child_state = self.repo.load_node_state(child_state["id"])
                if child_state and child_state.get("output") is not None:
                    collected_output[child["id"]] = child_state["output"]

                # A blocked child blocks the entire iteration and foreach.
                if child_status == "blocked":
                    iteration_status = "blocked"
                    break

                # If the child is not yet completed, propagate its status and
                # stop processing more children/iterations for this tick.
                if child_status != "completed":
                    iteration_status = child_status
                    break

            # Persist the iteration's latest status and any collected output.
            iteration["status"] = iteration_status
            if collected_output:
                iteration["output"] = collected_output
            self.repo.save_loop_iteration(iteration)

            # Propagate blocking back up to the foreach node and the run.
            if iteration_status == "blocked":
                state["status"] = "blocked"
                self.repo.save_node_state(state)
                return "blocked"

            # If this iteration still has work, the foreach node is not done.
            if iteration_status != "completed":
                state["status"] = iteration_status
                self.repo.save_node_state(state)
                return iteration_status

        # All iterations completed; finalize the foreach node.
        state["status"] = "completed"
        state["finished_at"] = self._now()
        self.repo.save_node_state(state)
        return "completed"

    def advance_action(
        self,
        run: dict[str, Any],
        node: dict[str, Any],
        state: dict[str, Any],
        item: dict[str, Any] | None = None,
    ) -> str:
        """Advance an action node by dispatching or polling its binding.

        Action nodes are backed by a binding, which is either an ``api`` call or
        a ``hermes`` task.  The first time an action is advanced (status
        ``pending`` or ``ready``), the runner resolves its input mapping,
        records the attempt, and starts the external work.  On subsequent ticks
        while the node is ``running``, the runner polls the external system for
        status.

        Parameters
        ----------
        run : dict[str, Any]
            The run record.
        node : dict[str, Any]
            The action node definition.
        state : dict[str, Any]
            The node_state for this action.
        item : dict[str, Any] | None, optional
            The current loop item when this action is a child of a foreach
            node.  Available to input mappings as ``$item``.

        Returns
        -------
        str
            The resulting status of the action node.
        """
        # Terminal and blocked shortcuts.
        if state["status"] == "completed":
            return "completed"
        if state["status"] == "blocked":
            return "blocked"

        # Ensure the node state is bound to the current binding definition.
        # Binding snapshots let us detect drift if the binding changes later.
        binding = self.repo.load_binding(node["binding_id"])
        state["binding_id"] = binding["id"]
        state["binding_snapshot"] = binding

        # First dispatch: resolve inputs, record the attempt, and start the
        # external integration.
        if state["status"] in {"pending", "ready"}:
            state["attempt"] = state.get("attempt", 0) + 1
            state["status"] = "running"
            state["started_at"] = state.get("started_at") or self._now()
            state["input"] = resolve_mapping(
                node["input_mapping"],
                context=self._runtime_context(run),
                item=item,
                scope=run.get("context") or {},
            )

            if binding["kind"] == "api":
                # API bindings are fire-and-forget from the runner's POV.
                result = self.api.start()
            else:
                # Hermes bindings create a task in the Hermes service.  The
                # external_ref is the primary handle for later inspection.
                state["external_ref"] = state.get("external_ref") or f"hermes-{state['id']}"
                result = self.hermes.create_task(state["input"])

            state = self.repo.save_node_state(state)
            return self.apply_integration_result(run, node, state, result, item=item)

        # Polling path: the node is already running, so check for a result.
        if state["status"] == "running":
            if binding["kind"] == "api":
                # API calls are only inspectable if we already have an external_ref.
                if state.get("external_ref"):
                    result = self.api.inspect(state["external_ref"])
                else:
                    return state["status"]
            else:
                # Hermes tasks can be inspected by external_ref or by node id.
                result = self.hermes.inspect_task(state["external_ref"] or state["id"])

            return self.apply_integration_result(run, node, state, result, item=item)

        # Any other status is returned as-is (defensive fallback).
        return state["status"]

    def apply_integration_result(
        self,
        run: dict[str, Any],
        node: dict[str, Any],
        state: dict[str, Any],
        result,
        *,
        item: dict[str, Any] | None = None,
    ) -> str:
        """Persist and react to the result returned by an integration.

        This method maps the integration result onto the node_state.  Depending
        on the result status, it may finalize the node as completed, pause the
        run for a question, fail the run, or simply persist an intermediate
        status.

        Parameters
        ----------
        run : dict[str, Any]
            The run record.
        node : dict[str, Any]
            The action node definition.
        state : dict[str, Any]
            The node_state being updated.
        result
            The integration result object.  Expected attributes include
            ``status``, ``native_state``, ``output``, ``error_code``,
            ``error_message``, ``external_ref``, and ``question_request``.
        item : dict[str, Any] | None, optional
            The current loop item, passed through to output mapping.

        Returns
        -------
        str
            The status reported by the integration result.
        """
        # Copy the integration's reported state into the node_state.
        state["status"] = result.status
        state["native_state"] = result.native_state
        state["raw_output"] = result.output
        state["error_code"] = result.error_code
        state["error_message"] = result.error_message
        if result.external_ref:
            state["external_ref"] = result.external_ref

        # Completed: resolve the output mapping and finalize the node.
        if result.status == "completed":
            state["output"] = resolve_output_mapping(
                node["output_mapping"],
                context=self._runtime_context(run),
                item=item,
                result=result.output,
                scope=run.get("context") or {},
            )
            state["finished_at"] = self._now()
            self.repo.save_node_state(state)
            return "completed"

        # Blocked: the integration needs a human answer.  Persist the state,
        # create a question record, and pause the whole run.
        if result.status == "blocked":
            self.repo.save_node_state(state)
            if result.question_request is not None:
                self.repo.create_question(
                    state["id"],
                    result.question_request.prompt,
                    result.question_request.options,
                    hermes_task_id=state.get("external_ref"),
                )
            run = self.repo.load_run(run["id"])
            run["status"] = "paused"
            run["pause_reason"] = "question"
            self.repo.save_run(run)
            return "blocked"

        # Failed: finalize the node and mark the run as failed.
        if result.status == "failed":
            state["finished_at"] = self._now()
            self.repo.save_node_state(state)
            run = self.repo.load_run(run["id"])
            run["status"] = "failed"
            run["failure_summary"] = state.get("error_message") or "node failed"
            self.repo.save_run(run)
            return "failed"

        # Any other status (e.g. ``running``) is just persisted for the next tick.
        self.repo.save_node_state(state)
        return result.status

    # ------------------------------------------------------------------
    # Question handling
    # ------------------------------------------------------------------

    def answer_question(self, question_id: str, answer: str) -> None:
        """Record an answer for a question and resume the related run.

        This method validates the question, forwards the answer to the Hermes
        service when the question was created from a Hermes task, persists the
        answer, and transitions the node_state and run back to ``running`` so
        the next tick can continue.

        Parameters
        ----------
        question_id : str
            The id of the question being answered.
        answer : str
            The answer provided by the user.

        Raises
        ------
        ValueError
            If the question, its node_state, or its run cannot be found.
        """
        # Locate the question and its associated node_state/run.
        question = self.repo.load_question(question_id)
        if not question:
            raise ValueError(f"unknown question id: {question_id}")

        state = self.repo.load_node_state(question["node_state_id"])
        if not state:
            raise ValueError(f"missing node state for question: {question_id}")

        run = self.repo.load_run(state["run_id"])
        if not run:
            raise ValueError(f"missing run for question: {question_id}")

        # If the question originated from a Hermes task, notify Hermes too.
        if question.get("hermes_task_id"):
            self.hermes.answer_question(question["hermes_task_id"], answer)

        # Persist the answer metadata.
        question["answer"] = answer
        question["status"] = "answered"
        question["answered_at"] = self._now()
        self.repo.save_question(question)

        # Wake up the node so the next tick can poll for completion.
        state["status"] = "running"
        self.repo.save_node_state(state)

        # Resume the run and clear the pause reason.
        run["status"] = "running"
        run["pause_reason"] = None
        self.repo.save_run(run)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _runtime_context(self, run: dict[str, Any]) -> dict[str, Any]:
        """Build the context object used by input/output mappings.

        The runtime context exposes completed outputs from top-level nodes
        (only those not inside a loop iteration) as ``$nodes.<node_id>`` and
        the run's user context as ``$scope``.

        Parameters
        ----------
        run : dict[str, Any]
            The run record whose context is being built.

        Returns
        -------
        dict[str, Any]
            Mapping context with ``nodes`` and ``scope`` keys.
        """
        # Gather outputs from top-level node_states.  Iteration-scoped child
        # outputs are intentionally excluded here; they are accessed via the
        # foreach node/iteration output when needed.
        node_outputs: dict[str, Any] = {}
        for state in self.repo.load_node_states_for_run(run["id"]):
            if state.get("loop_iteration_id") is None:
                node_outputs[state["node_id"]] = {
                    "output": state.get("output"),
                    "raw_output": state.get("raw_output"),
                    "status": state.get("status"),
                }

        return {"nodes": node_outputs, "scope": run.get("context") or {}}

    def _now(self) -> str:
        """Return the current UTC time as an ISO 8601 string.

        Returns
        -------
        str
            UTC timestamp formatted as ``%Y-%m-%dT%H:%M:%SZ``.
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
