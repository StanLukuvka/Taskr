"""Unit tests for the runner tick engine and foreach loops.

These tests exercise the core state machine directly (no HTTP layer) using
in-memory SQLite and the deterministic fake integrations.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.data.repository import TaskrRepository
from app.errors.data import CostAmountInvalidError
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


def _make_runner() -> TaskrRunner:
    """Create a runner backed by an in-memory repo with demo data seeded."""
    repo = _make_repo()
    repo.seed_data()
    api = FakeApiCaller()
    hermes = FakeHermesService()
    return TaskrRunner(repo, api, hermes)


# ---------------------------------------------------------------------------
# Tick
# ---------------------------------------------------------------------------

class TestTick:
    """Tests for TaskrRunner.tick()."""

    def test_tick_unknown_run_raises(self):
        """Ticking a non-existent run raises ValueError."""
        runner = _make_runner()
        with pytest.raises(ValueError, match="unknown run id"):
            runner.tick("run-does-not-exist")

    def test_tick_skips_terminal_run(self):
        """Ticking a completed run returns empty list (no advancement)."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()
        assert runner.repo.load_run(run["run_id"])["status"] == "completed"

        result = runner.tick(run["run_id"])
        assert result == []

    def test_tick_global_advances_all_active(self):
        """Global tick (no run_id) advances all running runs."""
        runner = _make_runner()
        run1 = runner.create_run("soda-comparison")
        run2 = runner.create_run("soda-comparison")

        result = runner.tick()

        assert len(result) == 2
        assert run1["run_id"] in result
        assert run2["run_id"] in result
        assert runner.repo.load_run(run1["run_id"])["status"] == "completed"
        assert runner.repo.load_run(run2["run_id"])["status"] == "completed"

    def test_tick_single_run_advances_only_target(self):
        """Targeted tick only advances the specified run."""
        runner = _make_runner()
        run1 = runner.create_run("soda-comparison")
        run2 = runner.create_run("soda-comparison")

        result = runner.tick(run1["run_id"])

        assert result == [run1["run_id"]]
        assert runner.repo.load_run(run1["run_id"])["status"] == "completed"
        # run2 should still be in running status with pending node states.
        run2_states = runner.repo.load_node_states_for_run(run2["run_id"])
        assert runner.repo.load_run(run2["run_id"])["status"] == "running"
        assert all(s["status"] == "pending" for s in run2_states)


# ---------------------------------------------------------------------------
# Foreach
# ---------------------------------------------------------------------------

class TestForeach:
    """Tests for foreach node execution."""

    def test_foreach_creates_iterations(self):
        """A foreach node creates one iteration per item from items_path."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        assert runner.repo.count_completed_iterations(run["run_id"]) == 2

    def test_foreach_completes_directly(self):
        """The foreach completes directly with the fake Hermes service."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        run_status = runner.repo.load_run(run["run_id"])["status"]
        assert run_status == "completed"
        assert runner.repo.count_completed_iterations(run["run_id"]) == 2

    def test_foreach_no_duplicate_dispatches(self):
        """No node_state is dispatched more than once during foreach execution."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        assert runner.repo.count_duplicate_dispatches(run["run_id"]) == 0

    def test_foreach_all_nodes_terminal_after_completion(self):
        """Every node_state is terminal after the run completes."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        states = runner.repo.load_node_states_for_run(run["run_id"])
        for s in states:
            assert s["status"] in ("completed", "failed"), \
                f"Node state {s['node_state_id']} is non-terminal: {s['status']}"


# ---------------------------------------------------------------------------
# Run creation and context
# ---------------------------------------------------------------------------

class TestCreateRun:
    """Tests for TaskrRunner.create_run()."""

    def test_create_run_materializes_top_level_node_states(self):
        """Creating a run creates node_states for every top-level node."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")

        states = runner.repo.load_node_states_for_run(run["run_id"])
        # The demo flow has 3 top-level nodes: Collect Products, For Each, Send Notification.
        assert len(states) == 3
        for s in states:
            assert s["status"] == "pending"

    def test_create_run_with_context(self):
        """Creating a run with context preserves it."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison", context={"retailer": "Target"})

        assert run["context"] == {"retailer": "Target"}

    def test_create_run_initializes_cost_tracking_to_zero(self):
        """Creating a run initializes run and node cost columns to zero."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")

        assert run["total_cost_cents"] == 0
        states = runner.repo.load_node_states_for_run(run["run_id"])
        assert states
        assert all(s["cost_cents"] == 0 for s in states)

    def test_repository_add_cost_helpers_increment_costs(self):
        """Cost helper methods increment run and node cost columns."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        state = runner.repo.load_node_states_for_run(run["run_id"])[0]

        updated_run = runner.repo.add_run_cost(run["run_id"], 50)
        updated_state = runner.repo.add_node_cost(state["node_state_id"], 50)

        assert updated_run is not None
        assert updated_run["total_cost_cents"] == 50
        assert updated_state is not None
        assert updated_state["cost_cents"] == 50

    def test_save_node_state_persists_cost_cents(self):
        """Saving a node state preserves cost_cents alongside runtime fields."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        state = runner.repo.load_node_states_for_run(run["run_id"])[0]
        state["cost_cents"] = 25

        updated_state = runner.repo.save_node_state(state)

        assert updated_state["cost_cents"] == 25

    def test_repository_rejects_negative_cost_amounts(self):
        """Cost helper methods reject negative amounts with a TaskrError subclass."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        state = runner.repo.load_node_states_for_run(run["run_id"])[0]

        with pytest.raises(CostAmountInvalidError):
            runner.repo.add_run_cost(run["run_id"], -1)
        with pytest.raises(CostAmountInvalidError):
            runner.repo.add_node_cost(state["node_state_id"], -1)

    def test_create_run_default_flow(self):
        """Creating a run without a slug uses the default seeded flow."""
        runner = _make_runner()
        run = runner.create_run()

        assert run["fk_flow_id"] == "flow-soda"

    def test_create_run_unknown_flow_raises(self):
        """Creating a run for an unknown flow raises ValueError."""
        runner = _make_runner()
        with pytest.raises(ValueError, match="unknown flow slug"):
            runner.create_run("does-not-exist")
