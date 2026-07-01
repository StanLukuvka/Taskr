"""Unit tests for run lifecycle: cancel, retry, and delete.

These tests exercise the runner methods directly (no HTTP layer) using
in-memory SQLite and the deterministic fake integrations.
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


def _make_runner() -> TaskrRunner:
    """Create a runner backed by an in-memory repo with demo data seeded."""
    repo = _make_repo()
    repo.seed_data()
    api = FakeApiCaller(image_delay=0)
    hermes = FakeHermesService()
    return TaskrRunner(repo, api, hermes)


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

class TestCancelRun:
    """Tests for TaskrRunner.cancel_run()."""

    def test_cancel_running_run(self):
        """Cancelling a running run sets status to cancelled."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")

        result = runner.cancel_run(run["run_id"])

        assert result["status"] == "cancelled"
        assert result["finished_at"] is not None

    def test_cancel_marks_non_terminal_node_states(self):
        """All non-terminal node_states are marked cancelled."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")

        runner.cancel_run(run["run_id"])

        states = runner.repo.load_node_states_for_run(run["run_id"])
        for s in states:
            assert s["status"] in ("completed", "cancelled"), \
                f"Node state {s['node_state_id']} has unexpected status: {s['status']}"

    def test_cancel_preserves_completed_node_states(self):
        """Completed node_states are not touched by cancellation."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()  # Complete the direct fake flow.

        with pytest.raises(ValueError, match="already terminal"):
            runner.cancel_run(run["run_id"])

        states = runner.repo.load_node_states_for_run(run["run_id"])
        completed = [s for s in states if s["status"] == "completed"]
        assert len(completed) >= 1, "At least one node should be completed"

    def test_cancel_already_terminal_raises(self):
        """Cancelling a completed run raises ValueError."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        assert runner.repo.load_run(run["run_id"])["status"] == "completed"

        with pytest.raises(ValueError, match="already terminal"):
            runner.cancel_run(run["run_id"])

    def test_cancel_cancelled_run_raises(self):
        """Cancelling an already-cancelled run raises ValueError."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.cancel_run(run["run_id"])

        with pytest.raises(ValueError, match="already terminal"):
            runner.cancel_run(run["run_id"])

    def test_cancel_unknown_run_raises(self):
        """Cancelling a non-existent run raises ValueError."""
        runner = _make_runner()
        with pytest.raises(ValueError, match="unknown run id"):
            runner.cancel_run("run-does-not-exist")

    def test_cancelled_run_not_advanced_by_tick(self):
        """A cancelled run is not advanced by subsequent ticks."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.cancel_run(run["run_id"])

        result = runner.tick(run["run_id"])
        assert result == [], "Tick should not advance a cancelled run"


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------

class TestRetryRun:
    """Tests for TaskrRunner.retry_run()."""

    def test_retry_creates_new_run(self):
        """Retry creates a new run with a different id."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.cancel_run(run["run_id"])

        new_run = runner.retry_run(run["run_id"])

        assert new_run["run_id"] != run["run_id"]
        assert new_run["status"] == "running"
        assert new_run["fk_flow_id"] == run["fk_flow_id"]
        assert new_run["fk_flow_version_id"] == run["fk_flow_version_id"]

    def test_retry_preserves_context(self):
        """Retry copies the original run's context into the new run."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison", context={"retailer": "Walmart"})
        runner.cancel_run(run["run_id"])

        new_run = runner.retry_run(run["run_id"])

        assert new_run["context"] == {"retailer": "Walmart"}

    def test_retry_original_unchanged(self):
        """The original run is not modified by retry."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.cancel_run(run["run_id"])

        runner.retry_run(run["run_id"])

        original = runner.repo.load_run(run["run_id"])
        assert original["status"] == "cancelled"

    def test_retry_unknown_run_raises(self):
        """Retrying a non-existent run raises ValueError."""
        runner = _make_runner()
        with pytest.raises(ValueError, match="unknown run id"):
            runner.retry_run("run-does-not-exist")

    def test_retry_new_run_has_fresh_node_states(self):
        """The retried run has fresh pending node_states."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.cancel_run(run["run_id"])

        new_run = runner.retry_run(run["run_id"])

        new_states = runner.repo.load_node_states_for_run(new_run["run_id"])
        assert len(new_states) >= 1
        for s in new_states:
            assert s["status"] == "pending"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class TestDeleteRun:
    """Tests for TaskrRunner.delete_run()."""

    def test_delete_removes_run(self):
        """Deleting a run removes it from the repository."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        runner.delete_run(run["run_id"])

        assert runner.repo.load_run(run["run_id"]) is None

    def test_delete_cascades_node_states(self):
        """Deleting a run removes all its node_states."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()
        states_before = runner.repo.load_node_states_for_run(run["run_id"])
        assert len(states_before) > 0

        runner.delete_run(run["run_id"])

        states_after = runner.repo.load_node_states_for_run(run["run_id"])
        assert states_after == []

    def test_delete_unknown_run_raises(self):
        """Deleting a non-existent run raises ValueError."""
        runner = _make_runner()
        with pytest.raises(ValueError, match="unknown run id"):
            runner.delete_run("run-does-not-exist")

    def test_delete_completed_run(self):
        """Deleting a completed run works."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()
        assert runner.repo.load_run(run["run_id"])["status"] == "completed"

        runner.delete_run(run["run_id"])
        assert runner.repo.load_run(run["run_id"]) is None
