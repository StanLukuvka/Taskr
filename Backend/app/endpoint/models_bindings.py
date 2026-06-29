from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Annotated

"""Pydantic models for integration binding CRUD endpoints.

A binding is a discriminated union keyed by `kind`. The shared fields live in
the parent INTEGRATION_BINDING table, while kind-specific config lives in either
API_BINDING_CONFIG or HERMES_BINDING_CONFIG. These models mirror that schema so
requests and responses are validated, documented in OpenAPI, and easy to
consume from the UI.
"""


class BindingBase(BaseModel):
    """Shared fields for every integration binding."""

    display_title: str
    is_enabled: bool = True


class BindingResponseBase(BaseModel):
    """Shared read-only fields for a binding response."""

    id: str
    display_title: str
    is_enabled: bool
    created_at: str
    updated_at: str


class ApiBindingConfig(BaseModel):
    """Configuration specific to an API binding."""

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    url_template: str
    auth_ref: str | None = None
    headers: dict[str, str] = {}
    request_mode: Literal["json", "query", "none"] = "json"
    completion_mode: Literal["response", "poll"] = "response"
    external_ref_path: str | None = None
    status_method: Literal["GET", "POST"] = "GET"
    status_url_template: str | None = None
    status_path: str | None = None
    success_values: list[str] = ["success", "completed"]
    failure_values: list[str] = ["failure", "failed", "cancelled"]
    result_path: str | None = None

    @model_validator(mode="after")
    def check_poll_fields(self) -> "ApiBindingConfig":
        """Enforce that poll mode provides all required polling fields."""
        if self.completion_mode == "poll":
            if self.external_ref_path is None or self.status_url_template is None or self.status_path is None:
                raise ValueError("poll mode requires external_ref_path, status_url_template, and status_path")
        return self

    @field_validator("success_values", "failure_values")
    @classmethod
    def _non_empty_lists(cls, value: list[str]) -> list[str]:
        """Keep the schema-friendly default of at least one value."""
        return value if value else []


class ApiBindingCreateRequest(BindingBase):
    """Payload to create an API binding."""

    kind: Literal["api"]
    config: ApiBindingConfig


class ApiBindingUpdateRequest(BaseModel):
    """Payload to update an API binding."""

    kind: Literal["api"]
    display_title: str | None = None
    is_enabled: bool | None = None
    config: ApiBindingConfig | None = None


class ApiBindingResponse(BindingResponseBase):
    """API binding response with config nested."""

    kind: Literal["api"]
    config: ApiBindingConfig


class HermesBindingConfig(BaseModel):
    """Configuration specific to a Hermes binding."""

    board: str
    profile: str | None = None
    task_title_template: str
    task_body_template: str
    skills: list[str] = []
    tenant_template: str | None = None
    workspace_template: str | None = None
    goal_mode: bool = False


class HermesBindingCreateRequest(BindingBase):
    """Payload to create a Hermes binding."""

    kind: Literal["hermes"]
    config: HermesBindingConfig


class HermesBindingUpdateRequest(BaseModel):
    """Payload to update a Hermes binding."""

    kind: Literal["hermes"]
    display_title: str | None = None
    is_enabled: bool | None = None
    config: HermesBindingConfig | None = None


class HermesBindingResponse(BindingResponseBase):
    """Hermes binding response with config nested."""

    kind: Literal["hermes"]
    config: HermesBindingConfig


BindingCreateRequest = Annotated[
    Union[ApiBindingCreateRequest, HermesBindingCreateRequest],
    Field(discriminator="kind"),
]

BindingUpdateRequest = Annotated[
    Union[ApiBindingUpdateRequest, HermesBindingUpdateRequest],
    Field(discriminator="kind"),
]

BindingResponse = Annotated[
    Union[ApiBindingResponse, HermesBindingResponse],
    Field(discriminator="kind"),
]
