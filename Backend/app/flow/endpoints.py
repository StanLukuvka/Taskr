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


@router.delete("/flow_nodes/{node_id}", tags=["Flow Nodes"])
def delete_flow_node(node_id: str):
    """Delete a flow node and its children.

    The flow version must be in draft status.

    Args:
        node_id: The ID of the flow node to delete.

    Returns:
        A confirmation message.

    Raises:
        FlowNodeNotFoundError: 404 if the node does not exist.
        FlowVersionNotFoundError: 404 if the flow version does not exist.
        FlowVersionNotDraftError: 400 if the flow version is not draft.
    """
    repo = _get_repo()
    node = repo.load_flow_node(node_id)

    #USER: Theoretically if version is incremented and not a random UUID a USER can delete the id twice, even if a flow was newly created

    if node is None:
        raise FlowNodeNotFoundError(f"Flow node {node_id} not found", entity_id=node_id)

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

    repo.delete_flow_node(node_id)
    return {"status": "deleted", "node_id": node_id}


# ── Flow & version management ───────────────────────────────

@router.post("/flows", response_model=FlowResponseFull, tags=["Flows"])
def create_flow(body: FlowCreateRequest):
    """Create a new flow.

    Args:
        body: The flow creation payload.

    Returns:
        The newly created flow record.

    Raises:
        FlowSlugAlreadyInUseError: 400 if the slug is already in use.
    """
    repo = _get_repo()
    existing = repo.load_flow_by_slug(body.slug)
    if existing:
        raise FlowSlugAlreadyInUseError(
            f"Flow slug '{body.slug}' is already in use", entity_id=body.slug
        )
    return repo.create_flow(body.title, body.slug, body.description)


@router.post(
    "/flows/{flow_id}/versions",
    response_model=FlowVersionCreateResponse,
    tags=["Flow Versions"],
)
def create_flow_version(flow_id: str):
    """Create a new draft flow version for a flow.

    The version number is auto-incremented. The new version starts in draft
    status so nodes can be added before publishing.

    Args:
        flow_id: The ID of the flow to create a version for.

    Returns:
        The newly created flow version record.

    Raises:
        FlowNotFoundError: 404 if the flow does not exist.
    """
    repo = _get_repo()
    flow = repo.load_flow(flow_id)
    if not flow:
        raise FlowNotFoundError(f"Flow {flow_id} not found", entity_id=flow_id)
    return repo.create_flow_version(flow_id)


@router.post(
    "/flow_versions/{flow_version_id}/publish",
    response_model=FlowVersionCreateResponse,
    tags=["Flow Versions"],
)
def publish_flow_version(flow_version_id: str):
    """Publish a draft flow version, making it the active version.

    Any previously active version for the same flow is archived.

    Args:
        flow_version_id: The ID of the draft flow version to publish.

    Returns:
        The updated flow version record with status "active".

    Raises:
        FlowVersionNotFoundError: 404 if the version does not exist.
        FlowVersionNotDraftError: 400 if it is not in draft status.
    """
    repo = _get_repo()
    return repo.publish_flow_version(flow_version_id)


@router.get("/flows", response_model=list[FlowResponse], tags=["Flows"])
def list_flows():
    """List all flows.

    Returns:
        A list of FlowResponse records.
    """
    repo = _get_repo()
    repo.seed_data()
    flows = repo.load_all_flows()
    return [build_flow_response(f) for f in flows]


@router.get(
    "/flow_versions/{flow_version_id}",
    response_model=FlowVersionResponse,
    tags=["Flow Versions"],
)
def get_flow_version(flow_version_id: str):
    """Retrieve a flow version and its full node tree.

    Args:
        flow_version_id: The ID of the flow version.

    Returns:
        A FlowVersionResponse containing the version metadata and nested nodes.

    Raises:
        FlowVersionNotFoundError: 404 if the flow version does not exist.
    """
    repo = _get_repo()
    version = repo.load_flow_version(flow_version_id)
    if version is None:
        raise FlowVersionNotFoundError(
            f"Flow version {flow_version_id} not found",
            entity_id=flow_version_id,
        )
    return build_flow_version_response(version, repo)
