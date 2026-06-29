from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Generator

import pytest

from app.errors.integration import HermesConfigurationError
from app.logic.integrations.hermes import HermesIntegration
from app.logic.integrations.result import IntegrationResult


class _HermesRunsHandler(BaseHTTPRequestHandler):
    last_authorization: str | None = None
    last_payload: dict[str, Any] | None = None

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/runs":
            self.send_response(404)
            self.end_headers()
            return
        type(self).last_authorization = self.headers.get("Authorization")
        length = int(self.headers.get("Content-Length", 0))
        type(self).last_payload = json.loads(self.rfile.read(length).decode("utf-8"))
        self._send_json(200, {"run_id": "run-123", "status": "started"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/v1/runs/run-started":
            self._send_json(200, {"run_id": "run-started", "status": "started"})
            return
        if self.path == "/v1/runs/run-running":
            self._send_json(200, {"run_id": "run-running", "status": "running"})
            return
        if self.path == "/v1/runs/run-completed":
            self._send_json(200, {"run_id": "run-completed", "status": "completed", "output": {"ok": True}})
            return
        if self.path == "/v1/runs/run-waiting":
            self._send_json(200, {"run_id": "run-waiting", "status": "waiting"})
            return
        if self.path == "/v1/runs/run-failed":
            self._send_json(200, {"run_id": "run-failed", "status": "failed"})
            return
        if self.path == "/v1/runs/run-rate-limit":
            self._send_json(429, {"error": "too many requests"})
            return
        self.send_response(404)
        self.end_headers()

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


@pytest.fixture
def hermes_server() -> Generator[str, None, None]:
    _HermesRunsHandler.last_authorization = None
    _HermesRunsHandler.last_payload = None
    server = HTTPServer(("127.0.0.1", 0), _HermesRunsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = server.server_address
    yield f"http://{address[0]}:{address[1]}/v1"
    server.shutdown()
    server.server_close()


def test_create_task_posts_run_payload(monkeypatch: pytest.MonkeyPatch, hermes_server: str) -> None:
    monkeypatch.setenv("HERMES_URL", hermes_server)
    monkeypatch.setenv("API_SERVER_KEY", "secret-key")
    integration = HermesIntegration(timeout=2.0)

    result = integration.create_task(
        {"product": "cola"},
        {
            "config": {
                "task_title_template": "Research {{product}}",
                "task_body_template": "Summarize {{product}}",
                "skills": ["research"],
            }
        },
        run_id="taskr-run",
        node_state_id="node-state",
    )

    assert isinstance(result, IntegrationResult)
    assert result.status == "running"
    assert result.external_ref == "run-123"
    assert _HermesRunsHandler.last_authorization == "Bearer secret-key"
    assert _HermesRunsHandler.last_payload == {
        "input": "Research cola",
        "session_id": "taskr-taskr-run-node-state",
        "instructions": "Summarize cola",
        "skills": ["research"],
    }


def test_inspect_task_maps_nonterminal_and_completed(monkeypatch: pytest.MonkeyPatch, hermes_server: str) -> None:
    monkeypatch.setenv("HERMES_URL", hermes_server)
    integration = HermesIntegration(timeout=2.0)

    assert integration.inspect_task("run-started").status == "running"
    assert integration.inspect_task("run-running").status == "running"

    completed = integration.inspect_task("run-completed")
    assert completed.status == "completed"
    assert completed.external_ref == "run-completed"
    assert completed.output == {"ok": True}


def test_inspect_task_maps_unknown_status_to_failed(monkeypatch: pytest.MonkeyPatch, hermes_server: str) -> None:
    monkeypatch.setenv("HERMES_URL", hermes_server)
    integration = HermesIntegration()

    result = integration.inspect_task("run-waiting")

    assert result.status == "failed"
    assert result.error_code == "hermes_failed"
    assert result.native_state == {"run_id": "run-waiting", "status": "waiting"}


def test_http_errors_are_classified(monkeypatch: pytest.MonkeyPatch, hermes_server: str) -> None:
    monkeypatch.setenv("HERMES_URL", hermes_server)
    integration = HermesIntegration(timeout=2.0)

    result = integration.inspect_task("run-rate-limit")

    assert result.status == "failed"
    assert result.error_code == "HTTP_429"
    assert result.error_category == "http_server"
    assert result.retryable is True


def test_missing_hermes_url_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERMES_URL", raising=False)
    integration = HermesIntegration(timeout=2.0)

    with pytest.raises(HermesConfigurationError, match="HERMES_URL is not set"):
        integration.create_task({}, {})
