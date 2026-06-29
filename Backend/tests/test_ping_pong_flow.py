from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator

import pytest

from app.data.repository import SCHEMA_PATH, TaskrRepository
from app.logic.integrations.api import ApiIntegration
from app.logic.integrations.hermes import HermesIntegration
from app.logic.runner import TaskrRunner
from tools.file_api_server import FileApiHandler


@contextmanager
def _file_api(root: Path) -> Iterator[str]:
    class TestFileHandler(FileApiHandler):
        ROOT = root.resolve()

    server = ThreadingHTTPServer(("127.0.0.1", 0), TestFileHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def _mock_hermes(output_root: Path) -> Iterator[tuple[str, Any]]:
    class MockHermesHandler(BaseHTTPRequestHandler):
        last_authorization: str | None = None
        last_payload: dict[str, Any] | None = None
        inspect_count = 0

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/runs":
                self.send_response(404)
                self.end_headers()
                return
            type(self).last_authorization = self.headers.get("Authorization")
            length = int(self.headers.get("Content-Length", "0"))
            type(self).last_payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self._send_json(200, {"run_id": "hermes-run-1", "status": "started"})

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/v1/runs/hermes-run-1":
                self.send_response(404)
                self.end_headers()
                return
            type(self).inspect_count += 1
            (output_root / "pong.txt").write_text("pong", encoding="utf-8")
            self._send_json(200, {"run_id": "hermes-run-1", "status": "completed", "output": "done"})

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    server = HTTPServer(("127.0.0.1", 0), MockHermesHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", MockHermesHandler
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _make_repo() -> TaskrRepository:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text())
    return TaskrRepository(conn)


def _seed_ping_pong(repo: TaskrRepository, file_api_base_url: str) -> None:
    flow = repo.create_flow(
        "Ping Pong Demo",
        "ping-pong",
        "Three-node demo: write ping, ask Hermes to write pong, ensure done.",
    )
    version = repo.create_flow_version(flow["flow_id"])
    b_write = repo.create_binding(
        "api",
        "File API Write",
        config={
            "method": "POST",
            "url_template": f"{file_api_base_url}/write",
            "request_mode": "json",
            "completion_mode": "response",
        },
    )
    b_hermes = repo.create_binding(
        "hermes",
        "Hermes Write Pong",
        config={
            "board": "taskr",
            "task_title_template": "{{prompt}}",
            "task_body_template": (
                "Read the file /agent/output/ping.txt, "
                "then write the literal string 'pong' to /agent/output/pong.txt. "
                "Reply with the single word 'done' when finished."
            ),
            "skills": [],
        },
    )
    b_ensure = repo.create_binding(
        "api",
        "File API Ensure Done",
        config={
            "method": "POST",
            "url_template": f"{file_api_base_url}/ensure",
            "request_mode": "json",
            "completion_mode": "response",
        },
    )

    repo.create_flow_node(
        version["flow_version_id"],
        "api",
        0,
        "Write Ping",
        binding_id=b_write["binding_id"],
        input_mapping={"path": "ping.txt", "content": "ping"},
        output_mapping={},
    )
    repo.create_flow_node(
        version["flow_version_id"],
        "hermes",
        1,
        "Hermes Write Pong",
        binding_id=b_hermes["binding_id"],
        input_mapping={"prompt": "$scope.prompt"},
        output_mapping={"hermes_output": "$result"},
    )
    repo.create_flow_node(
        version["flow_version_id"],
        "api",
        2,
        "Ensure Done",
        binding_id=b_ensure["binding_id"],
        input_mapping={
            "exists_path": "pong.txt",
            "expected_content": "pong",
            "write_path": "ping_2.txt",
            "write_content": "Done",
        },
        output_mapping={"status": "$result.status"},
    )
    repo.publish_flow_version(version["flow_version_id"])


def test_ping_pong_flow_writes_expected_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with _file_api(tmp_path) as file_api_base_url, _mock_hermes(tmp_path) as (hermes_url, hermes_handler):
        monkeypatch.setenv("HERMES_URL", hermes_url)
        monkeypatch.setenv("API_SERVER_KEY", "test-key")
        repo = _make_repo()
        _seed_ping_pong(repo, file_api_base_url)
        runner = TaskrRunner(
            repo,
            ApiIntegration(timeout=2.0, allow_private=True),
            HermesIntegration(timeout=2.0),
        )

        run = runner.create_run("ping-pong", context={"prompt": "write pong"})
        assert runner.tick(run["run_id"]) == [run["run_id"]]
        assert repo.load_run(run["run_id"])["status"] == "running"

        assert runner.tick(run["run_id"]) == [run["run_id"]]
        final_run = repo.load_run(run["run_id"])

    assert final_run is not None
    assert final_run["status"] == "completed"
    assert (tmp_path / "ping.txt").read_text(encoding="utf-8") == "ping"
    assert (tmp_path / "pong.txt").read_text(encoding="utf-8") == "pong"
    assert (tmp_path / "ping_2.txt").read_text(encoding="utf-8") == "Done"
    assert hermes_handler.inspect_count == 1
    assert hermes_handler.last_authorization == "Bearer test-key"
    payload = hermes_handler.last_payload
    assert payload is not None
    assert payload["input"] == "write pong"
    assert payload["instructions"].startswith("Read the file /agent/output/ping.txt")
