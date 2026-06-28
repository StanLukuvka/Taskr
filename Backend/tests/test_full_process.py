"""End-to-end integration test for the full Taskr lifecycle.

This test exercises the seeded "Soda Comparison" demo flow through the HTTP
API using TestClient. It runs the flow from run creation through to completion,
including answering a blocking question raised by the fake Hermes integration.
"""

from __future__ import annotations

import sqlite3
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.data.repository import TaskrRepository
from app.endpoint.deps import _get_repo, _get_runner
from app.logic.integrations.fake import FakeApiCaller, FakeHermesService
from app.logic.runner import TaskrRunner
from app.main.app import app


def _make_runner() -> TaskrRunner:
    """Create a runner backed by a fresh in-memory repo with demo data."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    from app.data.repository import SCHEMA_PATH
    conn.executescript(SCHEMA_PATH.read_text())
    repo = TaskrRepository(conn)
    repo.seed_data()
    return TaskrRunner(repo, FakeApiCaller(), FakeHermesService())


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Yield a TestClient with in-memory dependencies and fresh fake services."""
    runner = _make_runner()
    app.dependency_overrides[_get_runner] = lambda: runner
    app.dependency_overrides[_get_repo] = lambda: runner.repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _tick_until(client: TestClient, run_id: str, max_ticks: int = 10) -> dict:
    """Tick a run until it is no longer running, or max_ticks is reached."""
    run = None
    for _ in range(max_ticks):
        run = client.post(f"/runs/{run_id}/tick").json()
        if run["status"] != "running":
            break
    assert run is not None
    return run


def test_full_process_seeded_flow(client: TestClient) -> None:
    """Run the seeded Soda Comparison flow from creation to completion."""
    # 1. Create a run
    create_resp = client.post("/runs", json={"context": {"brand": "soda"}})
    assert create_resp.status_code == 200, create_resp.text
    run = create_resp.json()
    run_id = run["id"]
    assert run["status"] in ("pending", "running")
    assert run["context"]["brand"] == "soda"

    # 2. Advance until the run blocks or completes
    run = _tick_until(client, run_id)
    assert run["status"] == "paused"

    # 3. Find the open question for Fanta Orange
    questions_resp = client.get(f"/runs/{run_id}/questions")
    assert questions_resp.status_code == 200, questions_resp.text
    questions = questions_resp.json()
    assert len(questions) == 1
    question = questions[0]
    assert "Fanta" in question["prompt"]
    node_state_id = question["node_state_id"]

    # 4. Answer the question
    answer_resp = client.post(
        f"/runs/{run_id}/node-states/{node_state_id}/answer",
        json={"answer": "yes"},
    )
    assert answer_resp.status_code == 200, answer_resp.text
    assert answer_resp.json()["status"] == "answered"

    # 5. Tick to completion
    run = _tick_until(client, run_id)
    assert run["status"] == "completed"

    # 6. Verify node states
    states_resp = client.get(f"/runs/{run_id}/node-states")
    assert states_resp.status_code == 200, states_resp.text
    states = states_resp.json()["node_states"]
    by_id = {s["node_id"]: s for s in states}
    assert by_id["n-collect"]["status"] == "completed"
    assert by_id["n-foreach"]["status"] == "completed"
    assert by_id["n-notify"]["status"] == "completed"

    # 7. Verify the final run shape
    run_resp = client.get(f"/runs/{run_id}")
    assert run_resp.status_code == 200
    final_run = run_resp.json()
    assert final_run["status"] == "completed"
    assert final_run["flow_id"] == "flow-soda"
