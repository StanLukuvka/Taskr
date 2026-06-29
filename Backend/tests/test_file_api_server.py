from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from tools.file_api_server import FileApiHandler
from http.server import ThreadingHTTPServer


@contextmanager
def file_api(root: Path) -> Iterator[str]:
    class TestHandler(FileApiHandler):
        ROOT = root.resolve()

    server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def post_json(base_url: str, path: str, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        base_url + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def test_write_and_read_round_trip(tmp_path: Path) -> None:
    with file_api(tmp_path) as base_url:
        status, payload = post_json(base_url, "/write", {"path": "nested/ping.txt", "content": "ping"})
        assert status == 200
        assert payload == {"status": "ok", "path": "nested/ping.txt", "bytes": 4}
        assert (tmp_path / "nested" / "ping.txt").read_text(encoding="utf-8") == "ping"

        status, payload = post_json(base_url, "/read", {"path": "nested/ping.txt"})
        assert status == 200
        assert payload == {"status": "ok", "content": "ping"}


def test_ensure_checks_existing_content_and_writes_followup(tmp_path: Path) -> None:
    (tmp_path / "pong.txt").write_text("pong", encoding="utf-8")

    with file_api(tmp_path) as base_url:
        status, payload = post_json(
            base_url,
            "/ensure",
            {
                "exists_path": "pong.txt",
                "expected_content": "pong",
                "write_path": "ping_2.txt",
                "write_content": "Done",
            },
        )

    assert status == 200
    assert payload == {"status": "ok"}
    assert (tmp_path / "ping_2.txt").read_text(encoding="utf-8") == "Done"


def test_ensure_reports_missing_and_mismatch(tmp_path: Path) -> None:
    (tmp_path / "pong.txt").write_text("not-pong", encoding="utf-8")

    with file_api(tmp_path) as base_url:
        status, payload = post_json(
            base_url,
            "/ensure",
            {"exists_path": "missing.txt", "expected_content": "pong", "write_path": "out.txt"},
        )
        assert status == 409
        assert payload == {"status": "missing", "path": "missing.txt"}

        status, payload = post_json(
            base_url,
            "/ensure",
            {"exists_path": "pong.txt", "expected_content": "pong", "write_path": "out.txt"},
        )
        assert status == 409
        assert payload == {"status": "mismatch", "expected": "pong", "actual": "not-pong"}


def test_rejects_path_traversal(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("original", encoding="utf-8")

    with file_api(tmp_path) as base_url:
        for endpoint, payload in [
            ("/write", {"path": "../outside.txt", "content": "owned"}),
            ("/read", {"path": "../outside.txt"}),
            (
                "/ensure",
                {
                    "exists_path": "../outside.txt",
                    "expected_content": "original",
                    "write_path": "out.txt",
                    "write_content": "Done",
                },
            ),
        ]:
            status, payload = post_json(base_url, endpoint, payload)
            assert status == 400
            assert payload == {"status": "error", "message": "invalid path"}

    assert outside.read_text(encoding="utf-8") == "original"
