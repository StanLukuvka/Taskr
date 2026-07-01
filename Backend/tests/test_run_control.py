"""Tests for run-control extensions: restart_from and retry_node."""

from __future__ import annotations

import sqlite3

import pytest

from app.data.repository import TaskrRepository
from app.errors.logic import (
    FlowNodeNotFoundError,
    NodeStateNotFoundError,
    NodeStateRetryError,
    RunNotFoundError,
    RunRestartTargetError,
)
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


def _make_services():
    """Return deterministic fake integration services."""
    return FakeApiCaller(image_delay=0), FakeHermesService()


class TestRestartFrom:
    """Tests for restart_from run control."""

    def test_restart_from_creates_new_run_with_same_flow_version_and_context(self):
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        repo.seed_data()
        source = runner.create_run("soda-comparison", {"brand": "Coke"})

        nodes = repo.load_top_level_nodes(source["fk_flow_version_id"])
        # Target the final API node (Generate Image).
        target = next(n for n in nodes if n["kind"] == "api" and n["ord"] > 0)

        new_run = runner.restart_from(source["run_id"], target["flow_node_id"])

        assert new_run["run_id"] != source["run_id"]
        assert new_run["fk_flow_id"] == source["fk_flow_id"]
        assert new_run["fk_flow_version_id"] == source["fk_flow_version_id"]
        assert new_run["context"] == source["context"]
        assert new_run["status"] == "running"

    def test_restart_from_copies_completed_upstream_outputs(self):
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        repo.seed_data()
        source = runner.create_run("soda-comparison", {"brand": "Coke"})

        # Tick until the first action completes. The demo flow's first node is "Scrape Product".
        runner.tick(source["run_id"])

        nodes = repo.load_top_level_nodes(source["fk_flow_version_id"])
        first_node = nodes[0]
        # Target the final API node so the research node is skipped in the restart.
        target = next(n for n in nodes if n["kind"] == "api" and n["ord"] > 0)
        source_state = repo.get_or_create_node_state(source["run_id"], first_node["flow_node_id"], None)
        assert source_state["status"] == "completed"

        new_run = runner.restart_from(source["run_id"], target["flow_node_id"])

        new_states = repo.load_node_states_for_run(new_run["run_id"])
        first_new_state = next(s for s in new_states if s["fk_flow_node_id"] == first_node["flow_node_id"])
        assert first_new_state["status"] == "completed"
        assert first_new_state["output"] == source_state["output"]

    def test_restart_from_leaves_target_and_downstream_nodes_pending(self):
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        repo.seed_data()
        source = runner.create_run("soda-comparison", {"brand": "Coke"})
        runner.tick(source["run_id"])

        nodes = repo.load_top_level_nodes(source["fk_flow_version_id"])
        # Target the final API node (Generate Image); only the scrape node is upstream of it.
        target = next(n for n in nodes if n["kind"] == "api" and n["ord"] > 0)
        downstream = [n for n in nodes if n["ord"] > target["ord"]]

        new_run = runner.restart_from(source["run_id"], target["flow_node_id"])

        new_states = repo.load_node_states_for_run(new_run["run_id"])
        by_node = {s["fk_flow_node_id"]: s for s in new_states}

        assert by_node[target["flow_node_id"]]["status"] == "pending"
        for node in downstream:
            assert by_node[node["flow_node_id"]]["status"] == "pending"

    def test_restart_from_raises_404_for_missing_source_run(self):
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        with pytest.raises(RunNotFoundError):
            runner.restart_from("run-missing", "n-doesnotmatter")

    def test_restart_from_raises_400_for_non_action_target(self):
        """restart_from rejects nodes that are not top-level action nodes.

        The demo flow no longer has a foreach node, so we create a temporary
        draft version with a foreach node to exercise this error path.
        """
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        repo.seed_data()
        source = runner.create_run("soda-comparison", {})

        # Create a draft version with a foreach node to test the guard.
        flow = repo.load_flow_by_slug("soda-comparison")
        version = repo.create_flow_version(flow["flow_id"])
        repo.create_flow_node(
            version["flow_version_id"],
            "foreach",
            0,
            "Loop",
            node_id="n-test-foreach",
            items_path="$nodes.n-scrape.output.product",
        )
        repo.publish_flow_version(version["flow_version_id"])

        source2 = runner.create_run(flow_version_id=version["flow_version_id"])
        foreach_node = next(n for n in repo.load_top_level_nodes(version["flow_version_id"]) if n["kind"] == "foreach")

        with pytest.raises(RunRestartTargetError):
            runner.restart_from(source2["run_id"], foreach_node["flow_node_id"])

    def test_restart_from_raises_404_for_node_not_in_flow_version(self):
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        repo.seed_data()
        source = runner.create_run("soda-comparison", {})

        with pytest.raises(FlowNodeNotFoundError):
            runner.restart_from(source["run_id"], "n-not-in-flow")


class TestRetryNode:
    """Tests for retry_node run control."""

    def test_retry_node_resets_failed_top_level_node_state(self):
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        repo.seed_data()
        run = runner.create_run("soda-comparison", {})

        nodes = repo.load_top_level_nodes(run["fk_flow_version_id"])
        action_node = next(n for n in nodes if n["kind"] == "api")
        state = repo.get_or_create_node_state(run["run_id"], action_node["flow_node_id"], None)
        state["status"] = "failed"
        state["error_code"] = "500"
        state["error_message"] = "boom"
        state["attempt"] = 1
        repo.save_node_state(state)

        reset = runner.retry_node(run["run_id"], state["node_state_id"])

        assert reset["status"] == "pending"
        assert reset["error_code"] is None
        assert reset["error_message"] is None
        assert reset["attempt"] == 0

    def test_retry_node_sets_failed_run_back_to_running(self):
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        repo.seed_data()
        run = runner.create_run("soda-comparison", {})
        run["status"] = "failed"
        run["finished_at"] = "2026-01-01T00:00:00Z"
        run["failure_summary"] = "node failed"
        repo.save_run(run)

        nodes = repo.load_top_level_nodes(run["fk_flow_version_id"])
        action_node = next(n for n in nodes if n["kind"] == "api")
        state = repo.get_or_create_node_state(run["run_id"], action_node["flow_node_id"], None)
        state["status"] = "failed"
        repo.save_node_state(state)

        runner.retry_node(run["run_id"], state["node_state_id"])

        refreshed = repo.load_run(run["run_id"])
        assert refreshed["status"] == "running"
        assert refreshed["finished_at"] is None
        assert refreshed["failure_summary"] is None

    def test_retry_node_raises_404_for_node_state_in_different_run(self):
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        repo.seed_data()
        run1 = runner.create_run("soda-comparison", {})
        run2 = runner.create_run("soda-comparison", {})

        nodes = repo.load_top_level_nodes(run1["fk_flow_version_id"])
        action_node = next(n for n in nodes if n["kind"] == "api")
        other_state = repo.get_or_create_node_state(run2["run_id"], action_node["flow_node_id"], None)

        with pytest.raises(NodeStateNotFoundError):
            runner.retry_node(run1["run_id"], other_state["node_state_id"])

    def test_retry_node_raises_400_for_loop_iteration_state(self):
        """retry_node rejects node states inside a foreach loop.

        The demo flow no longer has a foreach node, so we create a draft
        version with one to exercise this error path.
        """
        repo = _make_repo()
        api, hermes = _make_services()
        runner = TaskrRunner(repo, api, hermes)

        repo.seed_data()
        flow = repo.load_flow_by_slug("soda-comparison")
        version = repo.create_flow_version(flow["flow_id"])
        repo.create_flow_node(
            version["flow_version_id"],
            "foreach",
            0,
            "Loop",
            node_id="n-test-foreach",
            items_path="$nodes.n-scrape.output.product",
        )
        repo.create_flow_node(
            version["flow_version_id"],
            "api",
            0,
            "Child",
            node_id="n-test-child",
            parent_node_id="n-test-foreach",
            binding_id="b-api-scrape",
        )
        repo.publish_flow_version(version["flow_version_id"])

        run = runner.create_run(flow_version_id=version["flow_version_id"])

        nodes = repo.load_top_level_nodes(version["flow_version_id"])
        foreach_node = next(n for n in nodes if n["kind"] == "foreach")
        child_node = next(n for n in repo.load_child_nodes(foreach_node["flow_node_id"]))

        foreach_state = repo.get_or_create_node_state(run["run_id"], foreach_node["flow_node_id"], None)
        loop_state = repo.create_loop_state(foreach_state["node_state_id"])
        iteration = repo.create_loop_iteration(loop_state["loop_state_id"], "item-1", 0, {"name": "Soda"})
        child_state = repo.get_or_create_node_state(
            run["run_id"], child_node["flow_node_id"], iteration["loop_iteration_id"]
        )

        with pytest.raises(NodeStateRetryError):
            runner.retry_node(run["run_id"], child_state["node_state_id"])
