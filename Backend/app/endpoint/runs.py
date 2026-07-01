from __future__ import annotations

from fastapi import APIRouter

from app.endpoint.builders import build_run_list_item, build_run_response
from app.endpoint.deps import _get_repo, _get_runner
from app.endpoint.models import (
    CreateRunRequest,
    RestartFromRequest,
    RestartFromResponse,
    RunActionResponse,
    RunListItem,
    RunResponse,
)
from app.errors.logic import RunNotFoundError

"""Run lifecycle endpoints.

This router covers the full lifecycle of a run: creation, listing, retrieval,
advancement (tick), cancellation, retry, and deletion.

Domain exceptions (RunNotFoundError, RunAlreadyTerminalError, etc.) are raised
directly and converted to HTTP responses by the exception handler registered
in app.errors.handlers.
"""

router = APIRouter()


# ── Run creation & listing ──────────────────────────────────

@router.post(
    "/runs",
    response_model=RunResponse,
    tags=["Runs"],
    operation_id="runs_create_run",
    summary="Create a run",
)
def create_run(body: CreateRunRequest | None = None):
    """Create a new run for a flow or a specific flow version.

    If no body is provided, the seeded "soda-comparison" demo flow is used
    with an empty context. If ``flow_version_id`` is provided it takes
    precedence over ``flow_slug`` and the run uses that exact version.

    Args:
        body: Optional run creation payload containing a flow slug, an exact
            flow version id, and/or context.

    Returns:
        A RunResponse containing the created run and its initial node states.
    """
    runner = _get_runner()
    context = body.context if body else {}
    if body and body.flow_version_id:
        run = runner.create_run(
            flow_version_id=body.flow_version_id,
            context=context,
        )
    else:
        flow_slug = body.flow_slug if body else None
        run = runner.create_run(flow_slug=flow_slug, context=context)
    return build_run_response(run, runner.repo)


@router.get(
    "/runs",
    response_model=list[RunListItem],
    tags=["Runs"],
    operation_id="runs_list_runs",
    summary="List runs",
)
def list_runs():
    """List all runs.

    Returns:
        A list of RunListItem records, ordered by creation time.
    """
    repo = _get_repo()
    runs = repo.load_all_runs()
    return [build_run_list_item(r) for r in runs]


# ── Run inspection ──────────────────────────────────────────


@router.post(
    "/runs/{run_id}/tick",
    response_model=RunResponse,
    tags=["Runs"],
    operation_id="runs_tick_run",
    summary="Tick a run",
)
def tick_run(run_id: str):
    """Advance a run by one execution tick.

    Args:
        run_id: The ID of the run to advance.

    Returns:
        A RunResponse reflecting the run state after the tick.

    Raises:
        RunNotFoundError: 404 if the run does not exist.
    """
    runner = _get_runner()
    run = runner.repo.load_run(run_id)
    if run is None:
        raise RunNotFoundError(f"Run {run_id} not found", entity_id=run_id)
    runner.tick(run_id)
    run = runner.repo.load_run(run_id)
    return build_run_response(run, runner.repo)


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    tags=["Runs"],
    operation_id="runs_get_run",
    summary="Get a run",
)
def get_run(run_id: str):
    """Retrieve a single run by ID.

    Args:
        run_id: The ID of the run to retrieve.

    Returns:
        A RunResponse containing the run metadata and node states.

    Raises:
        RunNotFoundError: 404 if the run does not exist.
    """
    repo = _get_repo()
    run = repo.load_run(run_id)
    if run is None:
        raise RunNotFoundError(f"Run {run_id} not found", entity_id=run_id)
    return build_run_response(run, repo)


# ── Run lifecycle actions ───────────────────────────────────

@router.post(
    "/runs/{run_id}/cancel",
    response_model=RunActionResponse,
    tags=["Runs"],
    operation_id="runs_cancel_run",
    summary="Cancel a run",
)
def cancel_run(run_id: str):
    """Cancel a run.

    Marks the run and all non-terminal node_states as cancelled. In-flight
    calls to external APIs are not interrupted; cancellation is a local state
    change that prevents future ticks from advancing the run.

    Args:
        run_id: The ID of the run to cancel.

    Returns:
        A RunActionResponse with status "cancelled".

    Raises:
        RunNotFoundError: 404 if the run does not exist.
        RunAlreadyTerminalError: 400 if it is already terminal.
    """
    runner = _get_runner()
    runner.cancel_run(run_id)
    return {"status": "cancelled", "run_id": run_id}


@router.post(
    "/runs/{run_id}/retry",
    response_model=RunResponse,
    tags=["Runs"],
    operation_id="runs_retry_run",
    summary="Retry a run",
)
def retry_run(run_id: str):
    """Retry a run by creating a fresh run from the same flow and context.

    The original run is left unchanged. The new run is created from the same
    flow version and initial context as the original.

    Args:
        run_id: The ID of the run to retry.

    Returns:
        A RunResponse for the newly created run.

    Raises:
        RunNotFoundError: 404 if the run does not exist.
    """
    runner = _get_runner()
    new_run = runner.retry_run(run_id)
    return build_run_response(new_run, runner.repo)


@router.post(
    "/runs/{run_id}/restart_from",
    response_model=RestartFromResponse,
    tags=["Runs"],
    operation_id="runs_restart_from",
    summary="Restart a run from a node",
)
def restart_from(run_id: str, body: RestartFromRequest):
    """Create a new run starting from a specific node.

    The source run is left unchanged. Upstream completed top-level action
    node outputs are copied into the new run; the target node and all
    downstream nodes are left pending.

    Args:
        run_id: The ID of the source run.
        body: The restart payload containing the target flow node id.

    Returns:
        A RestartFromResponse for the newly created run.

    Raises:
        RunNotFoundError: 404 if the source run does not exist.
        FlowNodeNotFoundError: 404 if the target node is not in the flow version.
        RunRestartTargetError: 400 if the target node is not a top-level action node.
    """
    runner = _get_runner()
    new_run = runner.restart_from(run_id, body.node_id)
    return {**build_run_response(new_run, runner.repo), "source_run_id": run_id}


@router.delete(
    "/runs/{run_id}",
    response_model=RunActionResponse,
    tags=["Runs"],
    operation_id="runs_delete_run",
    summary="Delete a run",
)
def delete_run(run_id: str):
    """Delete a run and all its child records.

    Args:
        run_id: The ID of the run to delete.

    Returns:
        A RunActionResponse with status "deleted".

    Raises:
        RunNotFoundError: 404 if the run does not exist.
    """
    runner = _get_runner()
    runner.delete_run(run_id)
    return {"status": "deleted", "run_id": run_id}
