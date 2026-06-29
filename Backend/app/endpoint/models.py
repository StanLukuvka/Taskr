from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

"""Pydantic models for run execution and node states.

These models represent the runtime execution layer — the state of
runs in progress and their node states.
"""


# ── Node state models ───────────────────────────────────────

class NodeStateResponse(BaseModel):
    """Public representation of a single node state.

    Attributes:
        id: Unique identifier for the node state.
        run_id: Parent run identifier.
        node_id: Identifier of the flow node being executed.
        node_title: Display title of the flow node.
        node_kind: Kind of the flow node ("api", "hermes", "foreach").
        loop_iteration_id: For nodes inside a foreach loop, the iteration id.
        status: Current execution status (e.g., "pending", "running", "completed").
        binding_id: Integration binding used, if any.
        binding_snapshot: Snapshot of the binding configuration at execution time.
        external_ref: External reference returned by the integration, if any.
        input: Resolved input passed to the node, if available.
        raw_output: Raw output returned by the integration, if available.
        output: Mapped output after applying output_mapping, if available.
        cost_cents: Spend attributed to this node execution in cents.
        error_code: Error code if the node failed.
        error_message: Error message if the node failed.
        attempt: Number of attempts made.
        created_at: ISO timestamp when the node state was created.
        started_at: ISO timestamp when execution started.
        finished_at: ISO timestamp when execution finished.
        updated_at: ISO timestamp of the last update.
    """

    id: str
    run_id: str
    node_id: str
    node_title: str | None = None
    node_kind: str | None = None
    loop_iteration_id: str | None = None
    status: Literal["pending", "ready", "dispatching", "running", "completed", "failed", "cancelled"]
    binding_id: str | None = None
    binding_snapshot: Any = None
    external_ref: str | None = None
    input: Any = None
    raw_output: Any = None
    output: Any = None
    cost_cents: int = 0
    error_code: str | None = None
    error_message: str | None = None
    attempt: int
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None


class NodeStatesListResponse(BaseModel):
    """Wrapper for a list of node states.

    Attributes:
        node_states: The list of node state records.
    """

    node_states: list[NodeStateResponse] = []


# ── Run models ──────────────────────────────────────────────

class CreateRunRequest(BaseModel):
    """Payload used to create a new run.

    Attributes:
        flow_slug: The flow to execute. Defaults to the seeded demo flow.
        flow_version_id: Optional exact flow version to run. If provided,
            flow_slug is ignored.
        context: Optional initial context for the run.
    """

    flow_slug: str | None = None
    flow_version_id: str | None = None
    context: dict[str, Any] | None = None


class RunResponse(BaseModel):
    """Public representation of a run and its associated node states.

    Attributes:
        id: Unique identifier for the run.
        status: Current run status (e.g., "pending", "running", "completed").
        flow_id: Identifier of the flow being executed.
        flow_version_id: Identifier of the flow version being executed.
        context: Execution context (arbitrary JSON-compatible data).
        cost_cents: Total spend recorded for this run in cents.
        failure_summary: Summary of any failure, if applicable.
        created_at: ISO timestamp when the run was created.
        started_at: ISO timestamp when the run started, if available.
        finished_at: ISO timestamp when the run finished, if available.
        node_states: List of node state records joined with node metadata.
    """

    id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    flow_id: str
    flow_version_id: str
    context: Any
    cost_cents: int = 0
    total_cost_cents: int = 0
    failure_summary: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    node_states: list[NodeStateResponse] = []


class RunListItem(BaseModel):
    """Public representation of a run in list views.

    Attributes:
        id: Run identifier.
        status: Run status.
        flow_id: Owning flow identifier.
        flow_version_id: Executed flow version.
        created_at: ISO timestamp.
        started_at: ISO timestamp.
        finished_at: ISO timestamp.
    """

    id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    flow_id: str
    flow_version_id: str
    total_cost_cents: int = 0
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class RunActionResponse(BaseModel):
    """Response returned after a run-level action such as cancel or retry.

    Attributes:
        status: The action status string.
        run_id: The run identifier, if applicable.
    """

    status: str
    run_id: str | None = None


class QuestionResponse(BaseModel):
    """Public representation of a question raised during node execution.

    Attributes:
        id: Unique identifier for the question.
        node_state_id: Identifier of the node state that raised the question.
        prompt: Text prompt shown to the user.
        options: Optional list of selectable options or structured choices.
        status: Current status of the question (e.g., "open", "answered").
        created_at: ISO timestamp when the question was created.
    """

    id: str
    node_state_id: str
    prompt: str
    options: Any = None
    status: str
    created_at: str | None = None


class NodeStateQuestionsResponse(BaseModel):
    """Wrapper for a list of questions on a node state.

    Attributes:
        questions: The list of question records.
    """

    questions: list[QuestionResponse] = []


class AnswerRequest(BaseModel):
    """Payload used to answer a question that has paused a node state.

    Attributes:
        answer: The answer text supplied by the caller.
    """

    answer: str


# ── Question models ─────────────────────────────────────────

class AnswerResponse(BaseModel):
    """Response returned after answering a question.

    Attributes:
        status: The answer status string.
    """

    status: str


class RestartFromRequest(BaseModel):
    """Payload to restart a run from a specific flow node.

    Attributes:
        node_id: The flow node id to restart from.
    """

    node_id: str


class RestartFromResponse(RunResponse):
    """Response for a restart_from request.

    Attributes:
        source_run_id: The id of the run that was restarted from.
    """

    source_run_id: str


class RetryNodeResponse(BaseModel):
    """Response after retrying a node state.

    Attributes:
        status: The new status of the node state.
        node_state_id: The id of the retried node state.
        run_id: The id of the parent run.
    """

    status: str
    node_state_id: str
    run_id: str
