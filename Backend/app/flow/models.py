from __future__ import annotations

from typing import Any, Literal

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


class FlowResponseFull(FlowResponse):
    """Full representation of a flow including its versions.

    Attributes:
        id: Unique flow identifier.
        title: Human-readable title.
        slug: URL-friendly slug.
        description: The human-readable description of what the flow answers.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        active_flow_version_id: Active published flow version, if one exists.
        active_flow_version_status: Status of the active version, if one exists.
    """

    created_at: str | None = None
    updated_at: str | None = None
    active_flow_version_id: str | None = None
    active_flow_version_status: Literal["draft", "active", "archived"] | None = None


class FlowCreateRequest(BaseModel):
    """Payload used to create a new flow.

    Attributes:
        title: Human-readable title for the flow.
        slug: URL-friendly unique slug.
        description: The human-readable description of what the flow answers.
    """

    title: str
    slug: str
    description: str


# ── Flow node models ────────────────────────────────────────

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
        item_key_path: For foreach nodes, the path to each item's stable key.
        failure_policy: How failures are handled.
        policy_refs: Policy references attached to the node.
        children: Nested child nodes for foreach containers.
    """

    id: str
    kind: Literal["api", "hermes", "foreach"]
    ord: int
    title: str
    parent_node_id: str | None = None
    binding_id: str | None = None
    input_mapping: dict[str, Any] | None = None
    output_mapping: dict[str, Any] | None = None
    items_path: str | None = None
    item_key_path: str | None = None
    failure_policy: Literal["stop", "continue"] | None = None
    policy_refs: list[str] | None = None
    children: list["FlowNodeResponse"] = []


class FlowNodeCreateRequest(BaseModel):
    """Payload used to create a new node inside a flow version.

    Attributes:
        kind: The node type (e.g., "api", "hermes", "foreach").
        ord: The display / execution order of the node within the flow.
        title: Human-readable title for the node.
        node_id: Optional stable identifier for the node.
        parent_node_id: Optional identifier of a parent node, for nesting.
        binding_id: Optional binding reference for external integrations.
        input_mapping: Optional mapping of input fields for this node.
        output_mapping: Optional mapping of output fields for this node.
        items_path: Optional path to the items list (foreach only).
        item_key_path: Optional path to the unique key within each item (foreach only).
        failure_policy: Optional failure policy ("stop" or "continue").
        policy_refs: Optional policy references attached to the node.
    """

    kind: Literal["api", "hermes", "foreach"]
    ord: int
    title: str
    node_id: str | None = None
    parent_node_id: str | None = None
    binding_id: str | None = None
    input_mapping: dict[str, Any] | None = None
    output_mapping: dict[str, Any] | None = None
    items_path: str | None = None
    item_key_path: str | None = None
    failure_policy: Literal["stop", "continue"] = "stop"
    policy_refs: list[str] | None = None


class FlowNodeUpdateRequest(BaseModel):
    """Payload used to update an existing flow node.

    All fields are optional; only provided fields are updated.

    Attributes:
        title: New title for the node.
        ord: New display / execution order.
        binding_id: New binding reference.
        input_mapping: New input mapping.
        output_mapping: New output mapping.
        items_path: New items path (foreach only).
        item_key_path: New item key path (foreach only).
        failure_policy: New failure policy ("stop" or "continue").
        policy_refs: New policy references.
    """

    title: str | None = None
    ord: int | None = None
    binding_id: str | None = None
    input_mapping: dict[str, Any] | None = None
    output_mapping: dict[str, Any] | None = None
    items_path: str | None = None
    item_key_path: str | None = None
    failure_policy: Literal["stop", "continue"] | None = None
    policy_refs: list[str] | None = None


# ── Flow version models ─────────────────────────────────────

class FlowVersionResponse(BaseModel):
    """Public representation of a flow version and its full node tree.

    Attributes:
        id: Unique identifier for the flow version.
        flow_id: Owning flow identifier.
        version: Version number.
        status: "draft", "active", or "archived".
        nodes: Top-level nodes with nested children.
    """

    id: str
    flow_id: str
    version: int
    status: Literal["draft", "active", "archived"]
    nodes: list[FlowNodeResponse] = []


class FlowVersionCreateResponse(BaseModel):
    """Response after creating a flow version.

    Attributes:
        id: Flow version identifier.
        flow_id: Parent flow identifier.
        version: Version number.
        status: Version status ("draft", "active", "archived").
    """

    id: str
    flow_id: str
    version: int
    status: Literal["draft", "active", "archived"]
