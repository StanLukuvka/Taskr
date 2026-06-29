"""Vertical slice test for the Taskr state machine.

This test exercises the core happy path without a real web server:
- an API node completes immediately,
- a foreach node fans out over the resulting list,
- Hermes child nodes complete directly,
- the run completes without deprecated interruption state.

It asserts direct completion and verifies that no node_state is dispatched more
than once.
"""

from __future__ import annotations

import sqlite3

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


def test_run_completes_without_interruption_pause():
    """End-to-end state machine test using the demo soda-comparison flow."""
    repo = _make_repo()
    api = FakeApiCaller()
    hermes = FakeHermesService()
    runner = TaskrRunner(repo, api, hermes)

    repo.seed_data()
    run = repo.create_run("flow-soda", "fv-1", {})

    runner.tick()

    run = repo.load_run(run["run_id"])
    assert run["status"] == "completed", f"Expected completed, got {run['status']}"

    # The demo list has two products, so both iterations must be done.
    assert repo.count_completed_iterations(run["run_id"]) == 2

    # The state machine should not have retried any node_state.
    assert repo.count_duplicate_dispatches(run["run_id"]) == 0

    # Every node state that belongs to the run must be terminal.
    states = repo._all(
        """
        SELECT ns.status, fn.title, fn.kind
        FROM NODE_STATE ns
        JOIN FLOW_NODE fn ON fn.flow_node_id = ns.fk_flow_node_id
        WHERE ns.fk_run_id = ?
        """,
        (run["run_id"],),
    )
    for s in states:
        assert s["status"] in (
            "completed", "failed"
        ), f"Node {s['title']} ({s['kind']}) has non-terminal status: {s['status']}"
