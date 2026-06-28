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


# ── Flow node management ────────────────────────────────────

@router.post(
    "/flow_versions/{flow_version_id}/flow_nodes",
    response_model=FlowNodeResponse,
    tags=["Flow Nodes"],
)
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
        FlowVersionNotFoundError: 404 if the flow version does not exist.
        FlowVersionNotDraftError: 400 if it is not in draft status.
    """

    # USER: Concurrency issue here. potential running condition here  
    repo = _get_repo()

    version = repo._one(
        "SELECT * FROM FLOW_VERSION WHERE flow_version_id = ?", (flow_version_id,)
    )
    if version is None:
        raise FlowVersionNotFoundError(
            f"Flow version {flow_version_id} not found", entity_id=flow_version_id
        )

    if version["status"] != "draft":
        raise FlowVersionNotDraftError(
            f"Flow version {flow_version_id} is not in draft status",
            entity_id=flow_version_id,
        )

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
        items_path=body.items_path,
        item_key_path=body.item_key_path,
        failure_policy=body.failure_policy,
        policy_refs=body.policy_refs,
    )
    return node


@router.patch(
    "/flow_nodes/{node_id}", response_model=FlowNodeResponse, tags=["Flow Nodes"]
)
def update_flow_node(node_id: str, body: FlowNodeUpdateRequest):
    """Update an existing flow node.

    Only fields provided in the body are updated. The flow version must be
    in draft status; published or archived versions are immutable.

    Args:
        node_id: The ID of the flow node to update.
        body: The update payload containing only fields to change.

    Returns:
        The updated flow node record.

    Raises:
        FlowNodeNotFoundError: 404 if the node does not exist.
        FlowVersionNotFoundError: 404 if the flow version does not exist.
        FlowVersionNotDraftError: 400 if the flow version is not draft.
    """
    repo = _get_repo()
    node = repo.load_flow_node(node_id)
    if node is None:
        raise FlowNodeNotFoundError(f"Flow node {node_id} not found", entity_id=node_id)
    # USER: Concurrency issue here. potential running condition here  
    version = repo._one(
        "SELECT * FROM FLOW_VERSION WHERE flow_version_id = ?", (node["fk_flow_version_id"],)
    )
    if version is None:
        raise FlowVersionNotFoundError(
            f"Flow version {node['fk_flow_version_id']} not found",
            entity_id=node["fk_flow_version_id"],
        )
    if version["status"] != "draft":
        raise FlowVersionNotDraftError(
            f"Flow version {node['fk_flow_version_id']} is not in draft status",
            entity_id=node["fk_flow_version_id"],
        )

    updates = body.model_dump(exclude_none=True)
    return repo.update_flow_node(node_id, updates)
