from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class FileApiHandler(BaseHTTPRequestHandler):
    ROOT: Path = Path("/agent/output")

    def _safe_path(self, rel: str) -> Path | None:
        if not isinstance(rel, str) or not rel:
            return None
        try:
            root = self.ROOT.resolve()
            target = (root / rel).resolve()
        except (OSError, RuntimeError, ValueError):
            return None
        if target == root or root in target.parents:
            return target
        return None

    def _read_body(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0:
            return {}
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return body if isinstance(body, dict) else None

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_POST(self) -> None:  # noqa: N802
        body = self._read_body()
        if body is None:
            self._send_json(400, {"status": "error", "message": "invalid json"})
            return

        if self.path == "/write":
            target = self._safe_path(body.get("path", ""))
            if target is None:
                self._send_json(400, {"status": "error", "message": "invalid path"})
                return
            content = body.get("content", "")
            if not isinstance(content, str):
                self._send_json(400, {"status": "error", "message": "content must be a string"})
                return
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            self._send_json(
                200,
                {
                    "status": "ok",
                    "path": str(target.relative_to(self.ROOT)),
                    "bytes": len(content.encode("utf-8")),
                },
            )
            return

        if self.path == "/read":
            target = self._safe_path(body.get("path", ""))
            if target is None:
                self._send_json(400, {"status": "error", "message": "invalid path"})
                return
            if not target.exists() or not target.is_file():
                self._send_json(404, {"status": "not_found"})
                return
            self._send_json(200, {"status": "ok", "content": target.read_text(encoding="utf-8")})
            return

        if self.path == "/ensure":
            exists_target = self._safe_path(body.get("exists_path", ""))
            write_target = self._safe_path(body.get("write_path", ""))
            if exists_target is None or write_target is None:
                self._send_json(400, {"status": "error", "message": "invalid path"})
                return
            if not exists_target.exists() or not exists_target.is_file():
                self._send_json(409, {"status": "missing", "path": body.get("exists_path")})
                return
            actual = exists_target.read_text(encoding="utf-8")
            expected = body.get("expected_content", "")
            if actual != expected:
                self._send_json(409, {"status": "mismatch", "expected": expected, "actual": actual})
                return
            write_content = body.get("write_content", "")
            if not isinstance(write_content, str):
                self._send_json(400, {"status": "error", "message": "write_content must be a string"})
                return
            write_target.parent.mkdir(parents=True, exist_ok=True)
            write_target.write_text(write_content, encoding="utf-8")
            self._send_json(200, {"status": "ok"})
            return

        self._send_json(404, {"status": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9121)
    parser.add_argument("--root", type=str, default="/agent/output")
    args = parser.parse_args()

    FileApiHandler.ROOT = Path(args.root).resolve()
    FileApiHandler.ROOT.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), FileApiHandler)
    print(f"File API server listening on http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
