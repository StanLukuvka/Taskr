from __future__ import annotations

from fastapi import APIRouter

from app.endpoint.builders import build_flow_response, build_flow_version_response
from app.endpoint.deps import _get_repo
from app.errors.data import FlowVersionNotFoundError, FlowVersionNotDraftError
from app.errors.flow import FlowSlugAlreadyInUseError
from app.errors.logic import FlowNotFoundError, FlowNodeNotFoundError
from app.flow.models import (
    FlowCreateRequest,
    FlowNodeCreateRequest,
    FlowNodeResponse,
    FlowNodeUpdateRequest,
    FlowResponse,
    FlowResponseFull,
    FlowVersionCreateResponse,
    FlowVersionResponse,
)

"""Flow, flow version, and flow node endpoints.

This router exposes the management surface for flows, their versioned
definitions, and the individual nodes that compose a version. Endpoints here
are read/write against the repository layer only; they do not drive run
execution.

Domain exceptions are raised directly and converted to HTTP responses by the
exception handler registered in app.errors.handlers.
"""

router = APIRouter()
