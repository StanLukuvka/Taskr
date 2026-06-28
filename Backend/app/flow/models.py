from __future__ import annotations

from typing import Any

from pydantic import BaseModel

"""Pydantic models for flow definitions.

These models represent the flow template layer — the definitions of
what can be run, not the runtime execution state.
"""


# ── Flow models ─────────────────────────────────────────────

class FlowResponse(BaseModel):
    """Public representation of a flow.

    Attributes:
        id: Unique identifier for the flow.
        title: Human-readable title.
        slug: URL-friendly identifier.
        description: One-line summary of what the flow answers.
    """

    id: str
    title: str
    slug: str
    description: str

