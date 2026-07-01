"""Unit tests for flow and flow node CRUD operations.

These tests exercise the repository layer directly (no HTTP layer) using
in-memory SQLite to verify that flows, flow versions, and flow nodes can
be created, updated, deleted, and published correctly.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.data.repository import TaskrRepository
from app.logic.runner import TaskrRunner
from app.logic.integrations.fake import FakeApiCaller, FakeHermesService


def _make_repo() -> TaskrRepository:
    """Create an in-memory repository with the canonical schema applied."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    from app.data.repository import SCHEMA_PATH
    conn.executescript(SCHEMA_PATH.read_text())
    return TaskrRepository(conn)


# ---------------------------------------------------------------------------
# Flow CRUD
# ---------------------------------------------------------------------------

class TestFlowCRUD:
    """Tests for flow creation and lookup."""

    def test_create_flow(self):
        """Creating a flow persists it with the given title, slug, and description."""
        repo = _make_repo()
        flow = repo.create_flow("Test Flow", "test-flow", "What is the answer?")

        assert flow["flow_id"].startswith("flow-")
        assert flow["title"] == "Test Flow"
        assert flow["slug"] == "test-flow"
        assert flow["description"] == "What is the answer?"

    def test_load_flow_by_id(self):
        """load_flow returns a flow by its id."""
        repo = _make_repo()
        created = repo.create_flow("Test Flow", "test-flow", "What?")
        loaded = repo.load_flow(created["flow_id"])

        assert loaded is not None
        assert loaded["flow_id"] == created["flow_id"]
        assert loaded["slug"] == "test-flow"

    def test_load_flow_nonexistent_returns_none(self):
        """load_flow returns None for a non-existent id."""
        repo = _make_repo()
        assert repo.load_flow("flow-does-not-exist") is None


# ---------------------------------------------------------------------------
# Flow Version CRUD
# ---------------------------------------------------------------------------

class TestFlowVersionCRUD:
    """Tests for flow version creation and publishing."""

    def test_create_flow_version(self):
        """Creating a flow version auto-increments the version number."""
        repo = _make_repo()
        flow = repo.create_flow("Test Flow", "test-flow", "What?")

        v1 = repo.create_flow_version(flow["flow_id"])
        assert v1["fk_flow_id"] == flow["flow_id"]
        assert v1["version"] == 1
        assert v1["status"] == "draft"

    def test_create_second_version_increments(self):
        """Creating a second version increments the version number."""
        repo = _make_repo()
        flow = repo.create_flow("Test Flow", "test-flow", "What?")

        v1 = repo.create_flow_version(flow["flow_id"])
        v2 = repo.create_flow_version(flow["flow_id"])

        assert v2["version"] == 2
        assert v2["status"] == "draft"

    def test_publish_draft_version(self):
        """Publishing a draft version sets it to active."""
        repo = _make_repo()
        flow = repo.create_flow("Test Flow", "test-flow", "What?")
        v1 = repo.create_flow_version(flow["flow_id"])

        published = repo.publish_flow_version(v1["flow_version_id"])

        assert published["status"] == "active"
        assert published["activated_at"] is not None

    def test_publish_archives_previous_active(self):
        """Publishing a new version archives the previously active one."""
        repo = _make_repo()
        flow = repo.create_flow("Test Flow", "test-flow", "What?")
        v1 = repo.create_flow_version(flow["flow_id"])
        repo.publish_flow_version(v1["flow_version_id"])

        v2 = repo.create_flow_version(flow["flow_id"])
        repo.publish_flow_version(v2["flow_version_id"])

        v1_refreshed = repo.load_flow_version(v1["flow_version_id"])
        v2_refreshed = repo.load_flow_version(v2["flow_version_id"])
        assert v1_refreshed["status"] == "archived"
        assert v2_refreshed["status"] == "active"

    def test_publish_non_draft_raises(self):
        """Publishing a non-draft version raises ValueError."""
        repo = _make_repo()
        flow = repo.create_flow("Test Flow", "test-flow", "What?")
        v1 = repo.create_flow_version(flow["flow_id"])
        repo.publish_flow_version(v1["flow_version_id"])

        with pytest.raises(ValueError, match="not in draft"):
            repo.publish_flow_version(v1["flow_version_id"])

    def test_publish_unknown_version_raises(self):
        """Publishing a non-existent version raises ValueError."""
        repo = _make_repo()
        with pytest.raises(ValueError, match="Flow version not found"):
            repo.publish_flow_version("fv-does-not-exist")


# ---------------------------------------------------------------------------
# Flow Node CRUD
# ---------------------------------------------------------------------------

class TestFlowNodeCRUD:
    """Tests for flow node create/update/delete."""

    def _make_repo_with_binding(self):
        """Create a repo with a flow, version, and an API binding."""
        repo = _make_repo()
        repo.seed_data()
        # Use the existing seeded flow version (fv-1) which is active,
        # but we need a draft version for node editing. Create a new one.
        flow = repo.load_flow_by_slug("soda-comparison")
        version = repo.create_flow_version(flow["flow_id"])
        # Reuse the seeded API binding.
        return repo, version, "b-api-scrape"

    def test_create_flow_node(self):
        """Creating a flow node persists it in the flow version."""
        repo, version, binding_id = self._make_repo_with_binding()

        node = repo.create_flow_node(
            flow_version_id=version["flow_version_id"],
            kind="api",
            ord=0,
            title="Test Node",
            binding_id=binding_id,
        )

        assert node["flow_node_id"].startswith("n-")
        assert node["kind"] == "api"
        assert node["title"] == "Test Node"
        assert node["fk_flow_version_id"] == version["flow_version_id"]

    def test_update_flow_node_title(self):
        """Updating a node's title changes it."""
        repo, version, binding_id = self._make_repo_with_binding()
        node = repo.create_flow_node(
            flow_version_id=version["flow_version_id"],
            kind="api",
            ord=0,
            title="Original Title",
            binding_id=binding_id,
        )

        updated = repo.update_flow_node(node["flow_node_id"], {"title": "New Title"})

        assert updated["title"] == "New Title"
        assert updated["flow_node_id"] == node["flow_node_id"]

    def test_update_flow_node_ord(self):
        """Updating a node's ord changes it."""
        repo, version, binding_id = self._make_repo_with_binding()
        node = repo.create_flow_node(
            flow_version_id=version["flow_version_id"],
            kind="api",
            ord=0,
            title="Test Node",
            binding_id=binding_id,
        )

        updated = repo.update_flow_node(node["flow_node_id"], {"ord": 5})

        assert updated["ord"] == 5

    def test_update_flow_node_input_mapping(self):
        """Updating input_mapping persists the new mapping."""
        repo, version, binding_id = self._make_repo_with_binding()
        node = repo.create_flow_node(
            flow_version_id=version["flow_version_id"],
            kind="api",
            ord=0,
            title="Test Node",
            binding_id=binding_id,
        )

        new_mapping = {"query": "$scope.search_term"}
        updated = repo.update_flow_node(node["flow_node_id"], {"input_mapping": new_mapping})

        assert updated["input_mapping"] == new_mapping

    def test_delete_flow_node(self):
        """Deleting a flow node removes it from the version."""
        repo, version, binding_id = self._make_repo_with_binding()
        node = repo.create_flow_node(
            flow_version_id=version["flow_version_id"],
            kind="api",
            ord=0,
            title="Test Node",
            binding_id=binding_id,
        )

        repo.delete_flow_node(node["flow_node_id"])
        assert repo.load_flow_node(node["flow_node_id"]) is None

    def test_delete_flow_node_cascades_children(self):
        """Deleting a foreach node also deletes its child nodes."""
        repo, version, binding_id = self._make_repo_with_binding()
        parent = repo.create_flow_node(
            flow_version_id=version["flow_version_id"],
            kind="foreach",
            ord=0,
            title="Loop",
            node_id="loop-test-1",
            items_path="$nodes.n-collect.output.products",
        )
        child = repo.create_flow_node(
            flow_version_id=version["flow_version_id"],
            kind="api",
            ord=0,
            title="Child",
            parent_node_id="loop-test-1",
            binding_id=binding_id,
        )

        repo.delete_flow_node(parent["flow_node_id"])
        assert repo.load_flow_node(parent["flow_node_id"]) is None
        assert repo.load_flow_node(child["flow_node_id"]) is None

    def test_update_no_fields_returns_unchanged(self):
        """Updating with an empty dict returns the node unchanged."""
        repo, version, binding_id = self._make_repo_with_binding()
        node = repo.create_flow_node(
            flow_version_id=version["flow_version_id"],
            kind="api",
            ord=0,
            title="Test Node",
            binding_id=binding_id,
        )

        result = repo.update_flow_node(node["flow_node_id"], {})
        assert result["title"] == "Test Node"
        assert result["ord"] == 0
