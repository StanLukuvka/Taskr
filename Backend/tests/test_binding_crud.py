"""Unit tests for integration binding CRUD operations.

These tests exercise the repository layer directly (no HTTP layer) using
in-memory SQLite to verify that API and Hermes bindings can be created, listed,
fetched, updated, and deleted, and that the associated validation and in-use
constraints are enforced.
"""

from __future__ import annotations

import sqlite3
import time
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.data.repository import TaskrRepository
from app.endpoint.deps import _get_repo
from app.endpoint.models_bindings import (
    ApiBindingConfig,
    ApiBindingCreateRequest,
    HermesBindingConfig,
    HermesBindingCreateRequest,
)
from app.errors.binding import BindingInUseError, BindingKindMismatchError
from app.main.app import app


def _make_repo() -> TaskrRepository:
    """Create an in-memory repository with the canonical schema applied."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    from app.data.repository import SCHEMA_PATH

    conn.executescript(SCHEMA_PATH.read_text())
    return TaskrRepository(conn)


def _full_api_config() -> dict:
    """Return a complete API binding config with default values."""
    return {
        "method": "POST",
        "url_template": "https://fake.api/collect",
        "auth_ref": "api-key",
        "headers": {"Content-Type": "application/json"},
        "request_mode": "json",
        "completion_mode": "response",
        "external_ref_path": None,
        "status_method": "GET",
        "status_url_template": None,
        "status_path": None,
        "success_values": ["success", "completed"],
        "failure_values": ["failure", "failed", "cancelled"],
        "result_path": None,
    }


def _full_hermes_config() -> dict:
    """Return a complete Hermes binding config with default values."""
    return {
        "board": "research",
        "profile": "default",
        "task_title_template": "Research {{product.name}}",
        "task_body_template": "Find information about {{product.name}}.",
        "skills": ["web_search", "summarizer"],
        "tenant_template": "{{tenant}}",
        "workspace_template": "{{workspace}}",
        "goal_mode": False,
    }


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Yield a TestClient with the repository dependency overridden to memory."""
    repo = _make_repo()
    app.dependency_overrides[_get_repo] = lambda: repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Repository CRUD
# ---------------------------------------------------------------------------

class TestBindingCRUD:
    """Tests for binding creation and lookup at the repository layer."""

    def test_create_api_binding(self):
        """Creating an API binding persists parent and child rows."""
        repo = _make_repo()
        config = _full_api_config()
        binding = repo.create_binding(
            kind="api",
            display_title="Collect API",
            config=config,
        )

        assert binding["binding_id"].startswith("b-")
        assert binding["kind"] == "api"
        assert binding["display_title"] == "Collect API"
        assert binding["is_enabled"] == 1
        assert binding["method"] == "POST"
        assert binding["url_template"] == "https://fake.api/collect"
        assert binding["headers"] == {"Content-Type": "application/json"}

        # Verify the child row exists independently.
        row = repo._one(
            "SELECT * FROM API_BINDING_CONFIG WHERE fk_binding_id = ?",
            (binding["binding_id"],),
        )
        assert row is not None
        assert row["method"] == "POST"

    def test_create_hermes_binding(self):
        """Creating a Hermes binding persists parent and child rows."""
        repo = _make_repo()
        config = _full_hermes_config()
        binding = repo.create_binding(
            kind="hermes",
            display_title="Hermes Research",
            config=config,
        )

        assert binding["binding_id"].startswith("b-")
        assert binding["kind"] == "hermes"
        assert binding["display_title"] == "Hermes Research"
        assert binding["board"] == "research"
        assert binding["task_title_template"] == "Research {{product.name}}"
        assert binding["skills"] == ["web_search", "summarizer"]

        row = repo._one(
            "SELECT * FROM HERMES_BINDING_CONFIG WHERE fk_binding_id = ?",
            (binding["binding_id"],),
        )
        assert row is not None
        assert row["board"] == "research"

    def test_list_bindings_returns_both_kinds(self):
        """load_all_bindings returns API and Hermes bindings."""
        repo = _make_repo()
        api = repo.create_binding(
            kind="api",
            display_title="API Binding",
            config=_full_api_config(),
        )
        hermes = repo.create_binding(
            kind="hermes",
            display_title="Hermes Binding",
            config=_full_hermes_config(),
        )

        bindings = repo.load_all_bindings()
        ids = {b["binding_id"] for b in bindings}

        assert len(bindings) == 2
        assert api["binding_id"] in ids
        assert hermes["binding_id"] in ids

    def test_get_binding_returns_nested_config(self):
        """load_binding returns the binding with nested kind-specific config."""
        repo = _make_repo()
        created = repo.create_binding(
            kind="api",
            display_title="API Binding",
            config=_full_api_config(),
        )

        binding = repo.load_binding(created["binding_id"])

        assert binding is not None
        assert binding["binding_id"] == created["binding_id"]
        assert binding["kind"] == "api"
        assert binding["method"] == "POST"
        assert binding["headers"] == {"Content-Type": "application/json"}

    def test_update_binding_display_title_and_config(self):
        """Updating a binding changes display_title and config fields."""
        repo = _make_repo()
        binding = repo.create_binding(
            kind="api",
            display_title="Old Title",
            config=_full_api_config(),
        )
        original_updated_at = binding["updated_at"]

        # Ensure the timestamp granularity changes.
        time.sleep(1.1)

        new_config = _full_api_config()
        new_config["url_template"] = "https://fake.api/updated"
        updated = repo.update_binding(
            binding["binding_id"],
            display_title="New Title",
            config=new_config,
        )

        assert updated["display_title"] == "New Title"
        assert updated["url_template"] == "https://fake.api/updated"
        assert updated["updated_at"] != original_updated_at

    def test_delete_binding_removes_parent_and_child_rows(self):
        """Deleting a binding removes the parent and child config rows."""
        repo = _make_repo()
        binding = repo.create_binding(
            kind="api",
            display_title="API Binding",
            config=_full_api_config(),
        )
        binding_id = binding["binding_id"]

        repo.delete_binding(binding_id)

        assert repo.load_binding(binding_id) is None
        assert (
            repo._one(
                "SELECT * FROM API_BINDING_CONFIG WHERE fk_binding_id = ?",
                (binding_id,),
            )
            is None
        )


# ---------------------------------------------------------------------------
# Endpoint validation
# ---------------------------------------------------------------------------

class TestBindingEndpoints:
    """Tests for binding endpoint-level validation and constraints."""

    def test_update_with_wrong_kind_returns_400(self, client: TestClient):
        """PUT with a mismatched kind returns 400 and a BindingKindMismatchError."""
        created = client.post(
            "/bindings",
            json={
                "kind": "api",
                "display_title": "API Binding",
                "config": _full_api_config(),
            },
        )
        assert created.status_code == 201
        binding_id = created.json()["id"]

        response = client.put(
            f"/bindings/{binding_id}",
            json={
                "kind": "hermes",
                "display_title": "Now Hermes",
                "config": _full_hermes_config(),
            },
        )

        assert response.status_code == 400
        assert "kind" in response.json()["detail"].lower()

    def test_delete_binding_in_use_returns_409(self, client: TestClient):
        """Deleting a binding referenced by a flow node returns 409."""
        repo = _make_repo()
        repo.seed_data()
        app.dependency_overrides[_get_repo] = lambda: repo
        flow = repo.load_flow_by_slug("soda-comparison")
        version = repo.create_flow_version(flow["flow_id"])
        binding_id = "b-api-collect"

        repo.create_flow_node(
            flow_version_id=version["flow_version_id"],
            kind="api",
            ord=0,
            title="Test Node",
            binding_id=binding_id,
        )

        try:
            response = client.delete(f"/bindings/{binding_id}")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 409
        assert "in use" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------

class TestBindingPydanticValidation:
    """Tests for request model validation at the Pydantic layer."""

    def test_create_api_binding_missing_method_fails(self):
        """An API binding config without a method fails Pydantic validation."""
        config = _full_api_config()
        del config["method"]
        with pytest.raises(ValueError):
            ApiBindingCreateRequest(
                display_title="Bad API",
                kind="api",
                config=ApiBindingConfig(**config),
            )

    def test_create_hermes_binding_missing_board_fails(self):
        """A Hermes binding config without a board fails Pydantic validation."""
        config = _full_hermes_config()
        del config["board"]
        with pytest.raises(ValueError):
            HermesBindingCreateRequest(
                display_title="Bad Hermes",
                kind="hermes",
                config=HermesBindingConfig(**config),
            )

    def test_poll_mode_missing_status_url_template_fails(self):
        """API poll mode missing required status_url_template fails validation."""
        config = _full_api_config()
        config["completion_mode"] = "poll"
        config["external_ref_path"] = "$.id"
        config["status_path"] = "$.status"
        # status_url_template is intentionally left as None.
        with pytest.raises(ValueError, match="poll"):
            ApiBindingConfig(**config)
