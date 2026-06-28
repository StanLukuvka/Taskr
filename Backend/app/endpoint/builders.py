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
