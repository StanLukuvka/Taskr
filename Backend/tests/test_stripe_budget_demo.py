from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from typing import Any, Iterator

import httpx
import pytest

from app.data.repository import SCHEMA_PATH, TaskrRepository
from app.logic.integrations.api import ApiIntegration
from app.logic.integrations.hermes import HermesIntegration
from app.logic.integrations.stripe import StripeIntegration
from app.logic.runner import TaskrRunner
from tools.fake_image_provider import FakeImageProviderHandler
from tools.seed_stripe_budget_demo import seed as seed_stripe_budget_demo


@contextmanager
def _fake_image_provider(initial_balance: int = 0) -> Iterator[str]:
    class TestFakeImageProviderHandler(FakeImageProviderHandler):
        balance = initial_balance

    server = ThreadingHTTPServer(("127.0.0.1", 0), TestFakeImageProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _make_repo(db_uri: str = "file:taskr-stripe-budget-demo?mode=memory&cache=shared") -> TaskrRepository:
    conn = sqlite3.connect(db_uri, uri=True, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text())
    return TaskrRepository(conn)


def _tick_until_terminal(runner: TaskrRunner, repo: TaskrRepository, run_id: str, max_ticks: int = 10) -> dict[str, Any]:
    run = repo.load_run(run_id)
    assert run is not None
    for _ in range(max_ticks):
        if run["status"] != "running":
            return run
        runner.tick(run_id)
        run = repo.load_run(run_id)
        assert run is not None
    pytest.fail(f"run {run_id} did not reach terminal state after {max_ticks} ticks")


def test_stripe_budget_demo_completes_and_tracks_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    stripe_calls: list[dict[str, Any]] = []

    def fake_post(*args: Any, **kwargs: Any) -> httpx.Response:
        stripe_calls.append({"args": args, "kwargs": kwargs})
        request = httpx.Request("POST", args[0])
        return httpx.Response(200, json={"id": "pi_budget_demo"}, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)

    with _fake_image_provider(initial_balance=0) as provider_url:
        repo = _make_repo()
        seed_stripe_budget_demo(provider_url, repo=repo)
        runner = TaskrRunner(
            repo,
            ApiIntegration(timeout=2.0, allow_private=True),
            HermesIntegration(timeout=2.0),
            StripeIntegration(timeout=2.0),
        )

        run = runner.create_run("stripe-budget-demo", context={"budget_cents": 100})
        final_run = _tick_until_terminal(runner, repo, run["run_id"])
        node_states = {state["fk_flow_node_id"]: state for state in repo.load_node_states_for_run(run["run_id"])}

    assert final_run["status"] == "completed"
    assert final_run["total_cost_cents"] > 0
    assert final_run["total_cost_cents"] == 50
    assert node_states["top_up_if_low"]["cost_cents"] == 50
    assert node_states["generate_image"]["output"]["image_url"] == f"{provider_url}/image/1"
    assert node_states["generate_image"]["output"]["credits_deducted"] == 10
    assert node_states["generate_image"]["output"]["balance"] == 40
    assert stripe_calls
    assert stripe_calls[0]["kwargs"]["data"]["amount"] == "50"
