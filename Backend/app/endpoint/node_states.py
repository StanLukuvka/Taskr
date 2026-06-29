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
