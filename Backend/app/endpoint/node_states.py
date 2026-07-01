from __future__ import annotations

from fastapi import APIRouter

from app.endpoint.builders import build_node_state_public
from app.endpoint.deps import _get_repo, _get_runner
from app.endpoint.models import (
    NodeStateResponse,
    NodeStatesListResponse,
    RetryNodeResponse,
)
from app.errors.logic import NodeStateNotFoundError, RunNotFoundError

"""Node state endpoints.

This router exposes the runtime states of individual flow nodes within a run.

Domain exceptions are raised directly and converted to HTTP responses by the
exception handler registered in app.errors.handlers.
"""

router = APIRouter()


# ── Node state inspection ───────────────────────────────────

@router.get(
    "/runs/{run_id}/node-states",
    response_model=NodeStatesListResponse,
    tags=["Node States"],
    operation_id="node_states_list_node_states",
    summary="List node states",
)
def list_node_states(run_id: str):
    """List all node states associated with a run.

    Args:
        run_id: The ID of the parent run.

    Returns:
        A dictionary with a single key, "node_states", containing the public
        representations of each node state.

    Raises:
        RunNotFoundError: 404 if the run does not exist.
    """
    repo = _get_repo()
    run = repo.load_run(run_id)
    if run is None:
        raise RunNotFoundError(f"Run {run_id} not found", entity_id=run_id)
    states = repo.load_node_states_for_run(run_id)
    return {"node_states": [build_node_state_public(s) for s in states]}


@router.get(
    "/runs/{run_id}/node-states/{node_state_id}",
    response_model=NodeStateResponse,
    tags=["Node States"],
    operation_id="node_states_get_node_state",
    summary="Get a node state",
)
def get_node_state(run_id: str, node_state_id: str):
    """Retrieve a single node state by run ID and node state ID.

    Args:
        run_id: The ID of the parent run.
        node_state_id: The ID of the node state to retrieve.

    Returns:
        The public representation of the node state.

    Raises:
        RunNotFoundError: 404 if the run does not exist.
        NodeStateNotFoundError: 404 if the node state does not exist or
            belongs to a different run.
    """
    repo = _get_repo()
    run = repo.load_run(run_id)
    if run is None:
        raise RunNotFoundError(f"Run {run_id} not found", entity_id=run_id)
    state = repo.load_node_state(node_state_id)
    if state is None or state["fk_run_id"] != run_id:
        raise NodeStateNotFoundError(
            f"Node state {node_state_id} not found", entity_id=node_state_id
        )
    return build_node_state_public(state)


# ── Node state lifecycle actions ────────────────────────────
@router.post(
    "/runs/{run_id}/node-states/{node_state_id}/retry",
    response_model=RetryNodeResponse,
    tags=["Node States"],
    operation_id="node_states_retry_node_state",
    summary="Retry a node state",
)
def retry_node_state(run_id: str, node_state_id: str):
    """Reset a top-level node state to pending so it re-runs on the next tick.

    Args:
        run_id: The ID of the parent run.
        node_state_id: The ID of the node state to retry.

    Returns:
        A RetryNodeResponse with the new status and identifiers.

    Raises:
        RunNotFoundError: 404 if the run does not exist.
        NodeStateNotFoundError: 404 if the node state does not exist or belongs to another run.
        NodeStateRetryError: 400 if the node state is inside a foreach loop or not an action node.
    """
    runner = _get_runner()
    state = runner.retry_node(run_id, node_state_id)
    return {"status": state["status"], "node_state_id": state["node_state_id"], "run_id": run_id}
