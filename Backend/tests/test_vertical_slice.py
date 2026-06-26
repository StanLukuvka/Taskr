"""Vertical slice test for the Taskr state machine.

This test exercises the core happy path without a real web server:
- an API node completes immediately,
- a foreach node fans out over the resulting list,
- a Hermes node blocks on a question for the second item,
- answering the question lets the run complete.

It asserts the run is paused, resumed, and eventually completed, and it
verifies that no node_state is dispatched more than once.
"""

from __future__ import annotations

import sqlite3

from app.repository import TaskrRepository
from app.runner import TaskrRunner
from app.integrations.fake import FakeApiCaller, FakeHermesService


def _make_repo() -> TaskrRepository:
    """Create an in-memory repository with the canonical schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.executescript(open("schema.sql").read())
    return TaskrRepository(conn)


def test_run_pauses_for_question_and_resumes():
    """End-to-end state machine test using the demo soda-comparison flow."""
    # Set up the repository with deterministic fake integrations.
    repo = _make_repo()
    api = FakeApiCaller()
    hermes = FakeHermesService()
    runner = TaskrRunner(repo, api, hermes)

    # Seed the demo flow (goal, version, bindings, nodes) and start a run.
    repo.seed_data()
    run = repo.create_run("g-soda", "fv-1", {})

    # Tick 1: collect products, enter foreach, execute "Coke" iteration, then
    # block on "Fanta" with a question about paid search.
    runner.tick()

    # Run should be paused waiting for a human answer.
    run = repo.load_run(run["id"])
    assert run["status"] == "paused", f"Expected paused, got {run['status']}"
    assert run["pause_reason"] == "question"

    # Exactly one open question should exist for the blocked Fanta iteration.
    questions = repo.load_open_questions(run["id"])
    assert len(questions) == 1, f"Expected 1 open question, got {len(questions)}"
    assert questions[0]["prompt"] == "Use paid search for Fanta?"

    # Provide the answer. The runner updates the question, the node state, and
    # the run so the next tick can continue.
    runner.answer_question(questions[0]["id"], "No, use organic sources only.")

    # Verify question is answered.
    q = repo.load_question(questions[0]["id"])
    assert q["status"] == "answered"
    assert q["answer"] == "No, use organic sources only."

    # Tick 2: resume the Fanta iteration, then finish the final API node.
    runner.tick()

    # The whole run should now be completed.
    run = repo.load_run(run["id"])
    assert run["status"] == "completed", f"Expected completed, got {run['status']}"

    # The demo list has two products (Coke, Fanta), so both iterations must be done.
    assert repo.count_completed_iterations(run["id"]) == 2

    # The state machine should not have retried any node_state.
    assert repo.count_duplicate_dispatches(run["id"]) == 0

    # Every node state that belongs to the run must be terminal.
    states = repo._all(
        """
        SELECT ns.status, fn.title, fn.kind
        FROM node_states ns
        JOIN flow_nodes fn ON fn.id = ns.node_id
        WHERE ns.run_id = ?
        """,
        (run["id"],),
    )
    for s in states:
        assert s["status"] in (
            "completed", "failed"
        ), f"Node {s['title']} ({s['kind']}) has non-terminal status: {s['status']}"
