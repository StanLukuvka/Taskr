from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.repository import TaskrRepository
from app.runner import TaskrRunner
from app.integrations.fake import FakeApiCaller, FakeHermesService

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
# The single entry point for the Taskr HTTP API. It wires together the
# repository, runner, and fake integration services used in this backend.
app = FastAPI(title="Taskr")

# CORS is enabled for all origins during development. This must be narrowed to
# the production frontend origin before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
# These Pydantic models define the shape of incoming JSON bodies and outgoing
# JSON responses. They provide validation, serialization, and documentation.


class AnswerRequest(BaseModel):
    """Payload used to answer a question that has paused a node state.

    Attributes:
        answer: The answer text supplied by the caller.
    """

    answer: str


class CreateRunRequest(BaseModel):
    """Payload used to create a new run.

    Attributes:
        goal_slug: The goal to execute. Defaults to the seeded demo goal.
        context: Optional initial context for the run.
    """

    goal_slug: str = "soda-comparison"
    context: dict[str, Any] | None = None


class GoalResponse(BaseModel):
    """Public representation of a goal.

    Attributes:
        id: Unique identifier for the goal.
        title: Human-readable title.
        slug: URL-friendly identifier.
        question: One-line summary of what the goal answers.
    """

    id: str
    title: str
    slug: str
    question: str


class FlowNodeResponse(BaseModel):
    """Public representation of a flow node, including children.

    Attributes:
        id: Node identifier.
        kind: Node kind ("api", "hermes", "foreach").
        ord: Sibling order.
        title: Display title.
        parent_node_id: Parent identifier, if any.
        binding_id: Integration binding, if any.
        input_mapping: Mapping used to build node input.
        output_mapping: Mapping used to write node output.
        items_path: For foreach nodes, the path to the list being iterated.
        failure_policy: How failures are handled.
        children: Nested child nodes for foreach containers.
    """

    id: str
    kind: str
    ord: int
    title: str
    parent_node_id: str | None = None
    binding_id: str | None = None
    input_mapping: Any = None
    output_mapping: Any = None
    items_path: str | None = None
    failure_policy: str | None = None
    children: list["FlowNodeResponse"] = []


class FlowVersionResponse(BaseModel):
    """Public representation of a flow version and its full node tree.

    Attributes:
        id: Unique identifier for the flow version.
        flow_id: Owning flow identifier.
        version: Version number.
        status: "draft" or "active".
        nodes: Top-level nodes with nested children.
    """

    id: str
    flow_id: str
    version: int
    status: str
    nodes: list[FlowNodeResponse] = []


class FlowNodeCreateRequest(BaseModel):
    """Payload used to create a new node inside a flow version.

    Attributes:
        kind: The node type (e.g., "question", "action").
        ord: The display / execution order of the node within the flow.
        title: Human-readable title for the node.
        node_id: Optional stable identifier for the node.
        parent_node_id: Optional identifier of a parent node, for nesting.
        binding_id: Optional binding reference for external integrations.
        input_mapping: Optional mapping of input fields for this node.
        output_mapping: Optional mapping of output fields for this node.
        policy_refs: Optional policy references attached to the node.
    """

    kind: str
    ord: int
    title: str
    node_id: str | None = None
    parent_node_id: str | None = None
    binding_id: str | None = None
    input_mapping: dict[str, Any] | None = None
    output_mapping: dict[str, Any] | None = None
    policy_refs: dict[str, Any] | None = None


class RunResponse(BaseModel):
    """Public representation of a run and its associated node states.

    Attributes:
        id: Unique identifier for the run.
        status: Current run status (e.g., "pending", "running", "paused").
        flow_id: Identifier of the flow being executed.
        flow_version_id: Identifier of the flow version being executed.
        context: Execution context (arbitrary JSON-compatible data).
        pause_reason: Reason the run is paused, if applicable.
        failure_summary: Summary of any failure, if applicable.
        created_at: ISO timestamp when the run was created.
        started_at: ISO timestamp when the run started, if available.
        finished_at: ISO timestamp when the run finished, if available.
        node_states: List of node state records joined with node metadata.
    """

    id: str
    status: str
    flow_id: str
    flow_version_id: str
    context: Any
    pause_reason: str | None = None
    failure_summary: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    node_states: list[dict[str, Any]] = []


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


class RunListItem(BaseModel):
    """Public representation of a run in list views.

    Attributes:
        id: Run identifier.
        status: Run status.
        flow_id: Owning flow identifier.
        flow_version_id: Executed flow version.
        pause_reason: Reason for pause, if any.
        created_at: ISO timestamp.
        started_at: ISO timestamp.
        finished_at: ISO timestamp.
    """

    id: str
    status: str
    flow_id: str
    flow_version_id: str
    pause_reason: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


# ---------------------------------------------------------------------------
# Dependencies — shared state across requests
# ---------------------------------------------------------------------------
# These module-level instances are intentionally shared across requests. The
# current backend uses fake implementations, so constructing them once and
# reusing them is sufficient for the in-memory behavior they provide.

# Shared fake API caller used by the runner when nodes perform external calls.
_shared_api = FakeApiCaller()
# Shared fake Hermes service used by the runner for AI / agent interactions.
_shared_hermes = FakeHermesService()


def _get_runner() -> TaskrRunner:
    """Build a TaskrRunner with a fresh repository connection.

    Returns a runner configured with a new repository connection and the
    shared fake integration services. The connection is obtained from the
    repository's connection factory, which creates or reuses the configured
    database handle.
    """
    # Obtain a database connection from the repository layer.
    conn = TaskrRepository.get_connection()
    # Construct the repository around that connection.
    repo = TaskrRepository(conn)
    # Return the runner wired to the shared fakes.
    return TaskrRunner(repo, _shared_api, _shared_hermes)


def _get_repo() -> TaskrRepository:
    """Build a TaskrRepository with a fresh connection.

    This is a lightweight factory used by endpoints that only need data access
    and do not drive the run execution engine.
    """
    # Create a repository using the shared connection factory.
    conn = TaskrRepository.get_connection()
    return TaskrRepository(conn)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
# The following functions define the Taskr HTTP API. They are grouped by
# resource: flow node management, run execution, and node state inspection.


@app.on_event("startup")
def on_startup():
    """Initialize the application database schema on startup.

    This event handler runs once when the FastAPI process starts. It ensures
    that all tables required by the repository layer exist before the first
    request is handled.
    """
    # Apply the schema defined by the repository layer.
    TaskrRepository.apply_schema()


@app.post("/flow_versions/{flow_version_id}/flow_nodes")
def create_flow_node(flow_version_id: str, body: FlowNodeCreateRequest):
    """Create a new flow node within a flow version.

    Validates that the target flow version exists and is still in "draft"
    status, then delegates creation to the repository layer.

    Args:
        flow_version_id: The ID of the flow version that will own the node.
        body: The flow node creation payload.

    Returns:
        The newly created flow node record.

    Raises:
        HTTPException: 404 if the flow version does not exist, or 400 if it is
            not in draft status.
    """
    # Get a repository handle for this request.
    repo = _get_repo()

    # Load the requested flow version. Using the repository's low-level helper
    # returns the row as a dictionary or None if no row was found.
    version = repo._one("SELECT * FROM flow_versions WHERE id = ?", (flow_version_id,))
    if version is None:
        # The referenced flow version does not exist in the database.
        raise HTTPException(404, f"Flow version {flow_version_id} not found")

    # Only allow modifications to draft versions. Published or locked versions
    # should be considered immutable so that existing runs remain stable.
    if version["status"] != "draft":
        raise HTTPException(400, f"Flow version {flow_version_id} is not in draft status")

    # Persist the new node using the repository's high-level factory.
    node = repo.create_flow_node(
        flow_version_id=flow_version_id,
        kind=body.kind,
        ord=body.ord,
        title=body.title,
        node_id=body.node_id,
        parent_node_id=body.parent_node_id,
        binding_id=body.binding_id,
        input_mapping=body.input_mapping,
        output_mapping=body.output_mapping,
        policy_refs=body.policy_refs,
    )
    return node


@app.post("/runs", response_model=RunResponse)
def create_run(body: CreateRunRequest | None = None):
    """Create a new run for a flow.

    If no body is provided, the seeded "soda-comparison" demo flow is used
    with an empty context. This keeps the endpoint usable for quick manual
    tests while also allowing a frontend to specify which flow to run and
    what initial context to pass.

    Args:
        body: Optional run creation payload containing the flow slug and context.

    Returns:
        A RunResponse containing the created run and its initial node states.
    """
    # Build a runner that can both persist data and execute logic.
    runner = _get_runner()

    # Ensure demo data exists (flows, flow versions, flow nodes, etc.).
    runner.repo.seed_data()

    # Use the provided flow slug and context, or fall back to the demo defaults.
    flow_slug = body.flow_slug if body else "soda-comparison"
    context = body.context if body else {}

    # Create a new run for the requested flow.
    run = runner.create_run(flow_slug, context)

    # Marshal the run record into the public response shape.
    return _build_run_response(run, runner.repo)


@app.get("/flows", response_model=list[FlowResponse], tags=["Flows"])
def list_flows():
    """List all flows.

    Returns:
        A list of FlowResponse records.
    """
    repo = _get_repo()
    repo.seed_data()
    return repo.load_all_flows()


@app.get("/runs", response_model=list[RunListItem])
def list_runs():
    """List all runs.

    Returns:
        A list of RunListItem records, ordered by creation time.
    """
    repo = _get_repo()
    runs = repo._all("SELECT * FROM runs ORDER BY created_at, id")
    return [
        {
            "id": r["id"],
            "status": r["status"],
            "flow_id": r["flow_id"],
            "flow_version_id": r["flow_version_id"],
            "pause_reason": r.get("pause_reason"),
            "created_at": r.get("created_at"),
            "started_at": r.get("started_at"),
            "finished_at": r.get("finished_at"),
        }
        for r in runs
    ]


@app.get("/flow_versions/{flow_version_id}", response_model=FlowVersionResponse)
def get_flow_version(flow_version_id: str):
    """Retrieve a flow version and its full node tree.

    Args:
        flow_version_id: The ID of the flow version.

    Returns:
        A FlowVersionResponse containing the version metadata and nested nodes.

    Raises:
        HTTPException: 404 if the flow version does not exist.
    """
    repo = _get_repo()
    version = repo.load_flow_version(flow_version_id)
    if version is None:
        raise HTTPException(404, f"Flow version {flow_version_id} not found")

    def build_subtree(parent_id: str | None) -> list[dict[str, Any]]:
        if parent_id is None:
            rows = repo.load_top_level_nodes(flow_version_id)
        else:
            rows = repo.load_child_nodes(parent_id)
        return [
            {
                "id": r["id"],
                "kind": r["kind"],
                "ord": r["ord"],
                "title": r["title"],
                "parent_node_id": r.get("parent_node_id"),
                "binding_id": r.get("binding_id"),
                "input_mapping": r.get("input_mapping"),
                "output_mapping": r.get("output_mapping"),
                "items_path": r.get("items_path"),
                "failure_policy": r.get("failure_policy"),
                "children": build_subtree(r["id"]),
            }
            for r in rows
        ]

    return {
        "id": version["id"],
        "goal_id": version["goal_id"],
        "version": version["version"],
        "status": version["status"],
        "nodes": build_subtree(None),
    }


@app.get("/runs/{run_id}/questions", response_model=list[QuestionResponse])
def get_run_questions(run_id: str):
    """List all open questions for a run.

    Args:
        run_id: The ID of the run.

    Returns:
        A list of open QuestionResponse records.

    Raises:
        HTTPException: 404 if the run does not exist.
    """
    repo = _get_repo()
    run = repo.load_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")
    return repo.load_open_questions(run_id)


@app.post("/runs/{run_id}/tick", response_model=RunResponse)
def tick_run(run_id: str):
    """Advance a run by one execution tick.

    A tick evaluates pending node states, executes the next ready node, and
    updates the run's status. This endpoint returns the run after the tick has
    been applied.

    Args:
        run_id: The ID of the run to advance.

    Returns:
        A RunResponse reflecting the run state after the tick.

    Raises:
        HTTPException: 404 if the run does not exist.
    """
    # Obtain a runner for the request.
    runner = _get_runner()

    # Verify that the referenced run exists before advancing it.
    run = runner.repo.load_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")

    # Advance only this run. runner.tick() with no argument would tick all
    # running/paused runs, which is not what this endpoint promises.
    runner.tick(run_id)

    # Reload the run so the response reflects the latest persisted state.
    run = runner.repo.load_run(run_id)
    return _build_run_response(run, runner.repo)


@app.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str):
    """Retrieve a single run by ID.

    Args:
        run_id: The ID of the run to retrieve.

    Returns:
        A RunResponse containing the run metadata and node states.

    Raises:
        HTTPException: 404 if the run does not exist.
    """
    # Use a repository-only handle since this is a read-only endpoint.
    repo = _get_repo()

    # Load the run record; return 404 if it is not present.
    run = repo.load_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")

    # Build the public response with joined node state metadata.
    return _build_run_response(run, repo)


@app.get("/runs/{run_id}/node-states")
def list_node_states(run_id: str):
    """List all node states associated with a run.

    Args:
        run_id: The ID of the parent run.

    Returns:
        A dictionary with a single key, "node_states", containing the public
        representations of each node state.

    Raises:
        HTTPException: 404 if the run does not exist.
    """
    repo = _get_repo()

    # Validate the parent run exists before returning its children.
    run = repo.load_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")

    # Load all node states for this run.
    states = repo.load_node_states_for_run(run_id)

    # Convert each raw state record into the public shape.
    return {"node_states": [_node_state_public(s) for s in states]}


@app.get("/runs/{run_id}/node-states/{node_state_id}")
def get_node_state(run_id: str, node_state_id: str):
    """Retrieve a single node state by run ID and node state ID.

    Args:
        run_id: The ID of the parent run.
        node_state_id: The ID of the node state to retrieve.

    Returns:
        The public representation of the node state.

    Raises:
        HTTPException: 404 if the run or node state does not exist, or if the
            node state belongs to a different run.
    """
    repo = _get_repo()

    # Verify the parent run exists.
    run = repo.load_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")

    # Load the requested node state and ensure it belongs to the given run.
    state = repo.load_node_state(node_state_id)
    if state is None or state["run_id"] != run_id:
        raise HTTPException(404, f"Node state {node_state_id} not found")

    return _node_state_public(state)


@app.get("/runs/{run_id}/node-states/{node_state_id}/questions")
def get_node_state_questions(run_id: str, node_state_id: str):
    """List all questions associated with a node state.

    Args:
        run_id: The ID of the parent run.
        node_state_id: The ID of the node state whose questions are queried.

    Returns:
        A dictionary with a single key, "questions", containing the question
        records.

    Raises:
        HTTPException: 404 if the run or node state does not exist, or if the
            node state belongs to a different run.
    """
    repo = _get_repo()

    # Validate the parent run exists.
    run = repo.load_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")

    # Validate the node state exists and belongs to the requested run.
    state = repo.load_node_state(node_state_id)
    if state is None or state["run_id"] != run_id:
        raise HTTPException(404, f"Node state {node_state_id} not found")

    # Load all questions linked to the node state.
    questions = repo.load_questions_for_node_state(node_state_id)
    return {"questions": questions}


@app.post("/runs/{run_id}/node-states/{node_state_id}/answer")
def answer_node_state_question(run_id: str, node_state_id: str, body: AnswerRequest):
    """Answer the first open question for a node state.

    The endpoint answers the oldest open question associated with the node
    state. It is the caller's responsibility to ensure that questions are
    answered in the order they were raised.

    Args:
        run_id: The ID of the parent run.
        node_state_id: The ID of the node state whose question is answered.
        body: The answer payload.

    Returns:
        A dictionary with key "status" set to "answered".

    Raises:
        HTTPException: 404 if the run or node state does not exist, 400 if there
            is no open question to answer.
    """
    # Use a runner so the answer can be processed through the execution engine.
    runner = _get_runner()

    # Validate the parent run exists.
    run = runner.repo.load_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")

    # Validate the node state exists and belongs to the requested run.
    state = runner.repo.load_node_state(node_state_id)
    if state is None or state["run_id"] != run_id:
        raise HTTPException(404, f"Node state {node_state_id} not found")

    # Find the open questions for this node state. If there are none, the node
    # is not in a state that accepts an answer.
    questions = runner.repo.load_open_questions_for_node_state(node_state_id)
    if not questions:
        raise HTTPException(400, f"No open question for node state {node_state_id}")

    # Answer the first open question. The repository is expected to return
    # questions in creation order, so this corresponds to the oldest question.
    runner.answer_question(questions[0]["id"], body.answer)
    return {"status": "answered"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# The following functions translate internal repository records into the
# public shapes returned by the API. They are intentionally kept simple and
# close to the endpoints that use them.


def _build_run_response(run: dict[str, Any], repo: TaskrRepository) -> dict[str, Any]:
    """Build a public RunResponse dictionary from a run record.

    This helper joins node states with their corresponding flow node metadata
    (title and kind) and copies the top-level run fields into the response.

    Args:
        run: The raw run record from the repository.
        repo: The repository used to query node states.

    Returns:
        A dictionary matching the RunResponse model.
    """
    # Query node states with joined node metadata, ordered by execution order.
    states = repo._all(
        """
        SELECT ns.*, fn.title AS node_title, fn.kind AS node_kind
        FROM node_states ns
        JOIN flow_nodes fn ON fn.id = ns.node_id
        WHERE ns.run_id = ?
        ORDER BY fn.ord, fn.id
        """,
        (run["id"],),
    )

    # Map the raw run record fields into the public response shape.
    return {
        "id": run["id"],
        "status": run["status"],
        "flow_id": run["flow_id"],
        "flow_version_id": run["flow_version_id"],
        "context": run.get("context"),
        "pause_reason": run.get("pause_reason"),
        "failure_summary": run.get("failure_summary"),
        "created_at": run.get("created_at"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "node_states": states,
    }


def _node_state_public(state: dict[str, Any]) -> dict[str, Any]:
    """Build a public representation of a node state record.

    This helper filters the raw node state record down to the fields that are
    safe to expose over the API. Optional fields use .get() so that missing
    values are returned as None rather than raising KeyError.

    Args:
        state: The raw node state record from the repository.

    Returns:
        A dictionary with the public node state fields.
    """
    return {
        "id": state["id"],
        "run_id": state["run_id"],
        "node_id": state["node_id"],
        "status": state["status"],
        "binding_id": state.get("binding_id"),
        "external_ref": state.get("external_ref"),
        "output": state.get("output"),
        "error_code": state.get("error_code"),
        "error_message": state.get("error_message"),
        # attempt defaults to 0 when not present in the record.
        "attempt": state.get("attempt", 0),
        "created_at": state.get("created_at"),
        "started_at": state.get("started_at"),
        "finished_at": state.get("finished_at"),
    }
