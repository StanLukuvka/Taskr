from __future__ import annotations

from typing import Any

from app.data.repository import TaskrRepository

"""Response builder functions for Taskr API endpoints.

These helpers translate raw repository records into the public dictionary
shapes expected by the Pydantic response models. Keeping them here avoids
duplicating field-mapping logic across endpoint modules and gives a single
place to adjust the response contract.
"""


# ── Run response builders ───────────────────────────────────

def build_flow_response(flow: dict[str, Any]) -> dict[str, Any]:
    """Build a public FlowResponse dictionary from a raw flow record.

    Args:
        flow: The raw flow record from the repository.

    Returns:
        A dictionary matching the FlowResponse model.
    """
    return {
        "id": flow["flow_id"],
        "title": flow["title"],
        "slug": flow["slug"],
        "description": flow["description"],
    }


def build_run_response(run: dict[str, Any], repo: TaskrRepository) -> dict[str, Any]:
    """Build a public RunResponse dictionary from a run record.

    This helper joins node states with their corresponding flow node metadata
    (title and kind) and copies the top-level run fields into the response.

    Args:
        run: The raw run record from the repository.
        repo: The repository used to query node states.

    Returns:
        A dictionary matching the RunResponse model.

    Note:
        The node-state query uses repo.load_node_states_for_run_with_node_info()
        to join node states with their flow node metadata (title, kind, ord).
    """
    states = repo.load_node_states_for_run_with_node_info(run["run_id"])

    return {
        "id": run["run_id"],
        "status": run["status"],
        "flow_id": run["fk_flow_id"],
        "flow_version_id": run["fk_flow_version_id"],
        "context": run.get("context"),
        "pause_reason": run.get("pause_reason"),
        "failure_summary": run.get("failure_summary"),
        "created_at": run.get("created_at"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "node_states": states,
    }

