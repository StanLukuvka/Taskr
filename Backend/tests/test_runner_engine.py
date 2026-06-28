"""Unit tests for the runner tick engine, foreach loops, and questions.

These tests exercise the core state machine directly (no HTTP layer) using
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
        questions = runner.repo.load_open_questions(run["run_id"])
        runner.answer_question(questions[0]["question_id"], "yes")
        runner.tick()
        assert runner.repo.load_run(run["run_id"])["status"] == "completed"

        result = runner.tick(run["run_id"])
        assert result == []

    def test_tick_global_advances_all_active(self):
        """Global tick (no run_id) advances all running/paused runs."""
        runner = _make_runner()
        run1 = runner.create_run("soda-comparison")
        run2 = runner.create_run("soda-comparison")

        result = runner.tick()

        # Both runs should have been advanced.
        assert len(result) == 2
        assert run1["run_id"] in result
        assert run2["run_id"] in result

    def test_tick_single_run_advances_only_target(self):
        """Targeted tick only advances the specified run."""
        runner = _make_runner()
        run1 = runner.create_run("soda-comparison")
        run2 = runner.create_run("soda-comparison")

        result = runner.tick(run1["run_id"])

        assert result == [run1["run_id"]]
        # run2 should still be in running status with pending node states.
        run2_states = runner.repo.load_node_states_for_run(run2["run_id"])
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

        # The demo flow's foreach iterates over two products (Coke, Fanta).
        assert runner.repo.count_completed_iterations(run["run_id"]) >= 1

    def test_foreach_blocks_on_question(self):
        """The foreach pauses the run when a child blocks on a question."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        run_status = runner.repo.load_run(run["run_id"])["status"]
        assert run_status == "paused"
        assert runner.repo.load_open_questions(run["run_id"]) != []

    def test_foreach_completes_after_answer(self):
        """The foreach completes all iterations after the question is answered."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        questions = runner.repo.load_open_questions(run["run_id"])
        assert len(questions) == 1

        runner.answer_question(questions[0]["question_id"], "yes")
        runner.tick()

        run_status = runner.repo.load_run(run["run_id"])["status"]
        assert run_status == "completed"
        assert runner.repo.count_completed_iterations(run["run_id"]) == 2

    def test_foreach_no_duplicate_dispatches(self):
        """No node_state is dispatched more than once during foreach execution."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()
        questions = runner.repo.load_open_questions(run["run_id"])
        runner.answer_question(questions[0]["question_id"], "yes")
        runner.tick()

        assert runner.repo.count_duplicate_dispatches(run["run_id"]) == 0

    def test_foreach_all_nodes_terminal_after_completion(self):
        """Every node_state is terminal after the run completes."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()
        questions = runner.repo.load_open_questions(run["run_id"])
        runner.answer_question(questions[0]["question_id"], "yes")
        runner.tick()

        states = runner.repo.load_node_states_for_run(run["run_id"])
        for s in states:
            assert s["status"] in ("completed", "failed"), \
                f"Node state {s['node_state_id']} is non-terminal: {s['status']}"


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

class TestQuestions:
    """Tests for question handling."""

    def test_open_question_has_prompt(self):
        """The open question created during foreach has the expected prompt."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        questions = runner.repo.load_open_questions(run["run_id"])
        assert len(questions) == 1
        assert "Fanta" in questions[0]["prompt"]

    def test_answer_changes_question_status(self):
        """Answering a question marks it as answered."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        questions = runner.repo.load_open_questions(run["run_id"])
        q_id = questions[0]["question_id"]

        runner.answer_question(q_id, "No, use organic sources only.")

        q = runner.repo.load_question(q_id)
        assert q["status"] == "answered"
        assert q["answer"] == "No, use organic sources only."
        assert q["answered_at"] is not None

    def test_answer_resumes_run(self):
        """Answering a question sets the run back to running."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        questions = runner.repo.load_open_questions(run["run_id"])
        runner.answer_question(questions[0]["question_id"], "yes")

        run_status = runner.repo.load_run(run["run_id"])["status"]
        assert run_status == "running"

    def test_answer_sets_node_state_to_running(self):
        """Answering a question sets the blocked node_state back to running."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        questions = runner.repo.load_open_questions(run["run_id"])
        q_id = questions[0]["question_id"]
        q = runner.repo.load_question(q_id)
        state_before = runner.repo.load_node_state(q["fk_node_state_id"])
        assert state_before["status"] == "blocked"

        runner.answer_question(q_id, "yes")

        state_after = runner.repo.load_node_state(q["fk_node_state_id"])
        assert state_after["status"] == "running"

    def test_answer_unknown_question_raises(self):
        """Answering a non-existent question raises ValueError."""
        runner = _make_runner()
        with pytest.raises(ValueError, match="unknown question id"):
            runner.answer_question("q-does-not-exist", "yes")

    def test_no_open_questions_after_answer(self):
        """After answering, no open questions remain for the run."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")
        runner.tick()

        questions = runner.repo.load_open_questions(run["run_id"])
        runner.answer_question(questions[0]["question_id"], "yes")

        assert runner.repo.load_open_questions(run["run_id"]) == []


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

    def test_create_unknown_flow_raises(self):
        """Creating a run for an unknown flow slug raises ValueError."""
        runner = _make_runner()
        with pytest.raises(ValueError, match="unknown flow slug"):
            runner.create_run("does-not-exist")

    def test_create_run_status_is_running(self):
        """A newly created run has status 'running'."""
        runner = _make_runner()
        run = runner.create_run("soda-comparison")

        assert run["status"] == "running"
        assert run["started_at"] is not None
