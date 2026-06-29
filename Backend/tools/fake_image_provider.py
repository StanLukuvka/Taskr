from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit


DEFAULT_PORT = 9122
DEFAULT_BALANCE = 100
GENERATE_COST = 10

# Image rendering constants (see fake-image-provider-design.md sections 3 & 6).
DEFAULT_WIDTH = 400
DEFAULT_HEIGHT = 300
MIN_DIMENSION = 1
MAX_DIMENSION = 2048
DEFAULT_FORMAT = "png"
# Maps a requested format (after alias normalisation) to its HTTP Content-Type.
CONTENT_TYPE_BY_FORMAT = {
    "png": "image/png",
    "jpeg": "image/jpeg",
}
# User-facing format aliases normalise to a canonical key in CONTENT_TYPE_BY_FORMAT.
FORMAT_ALIASES = {
    "png": "png",
    "jpeg": "jpeg",
    "jpg": "jpeg",
}


class ParamError(Exception):
    """Raised when an /image/<id> query parameter fails validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class FakeImageProviderHandler(BaseHTTPRequestHandler):
    """Tiny stateful fake image provider for the Stripe budget demo."""

    balance = DEFAULT_BALANCE
    # Monotonic counter for IDs minted by /generate.
    next_image_id = 1

    def do_GET(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        path = parts.path

        if path == "/credits":
            self._send_json(200, {"balance": type(self).balance})
            return

        if path.startswith("/image/"):
            self._handle_image(path, parts.query)
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/credits":
            self._send_json(200, {"balance": type(self).balance})
            return

        payload = self._read_json()
        if payload is None:
            self._send_json(400, {"ok": False, "error": "invalid json"})
            return

        if self.path == "/topup":
            amount = self._parse_positive_amount(payload)
            if amount is None:
                self._send_json(400, {"ok": False, "error": "amount must be a positive integer"})
                return
            type(self).balance += amount
            self._send_json(200, {"ok": True, "balance": type(self).balance})
            return

        if self.path == "/deduct":
            amount = self._parse_positive_amount(payload)
            if amount is None:
                self._send_json(400, {"ok": False, "error": "amount must be a positive integer"})
                return
            if type(self).balance < amount:
                self._send_json(402, {"ok": False, "error": "insufficient credits", "balance": type(self).balance})
                return
            type(self).balance -= amount
            self._send_json(200, {"ok": True, "balance": type(self).balance})
            return

        if self.path == "/generate":
            if type(self).balance < GENERATE_COST:
                self._send_json(402, {"ok": False, "error": "insufficient credits", "balance": type(self).balance})
                return
            type(self).balance -= GENERATE_COST
            image_id = type(self).next_image_id
            type(self).next_image_id += 1
            image_url = f"http://127.0.0.1:{self.server.server_port}/image/{image_id}"
            self._send_json(
                200,
                {
                    "ok": True,
                    "image_url": image_url,
                    "balance": type(self).balance,
                    "credits_deducted": GENERATE_COST,
                },
            )
            return

        self._send_json(404, {"error": "not found"})

    # --- /image/<id> handling -------------------------------------------------

    def _handle_image(self, path: str, query: str) -> None:
        image_id = path[len("/image/"):]
        if not image_id:
            self._send_json(404, {"error": "not found"})
            return

        params = parse_qs(query, keep_blank_values=True)
        try:
            width = self._parse_dimension(params, "width", DEFAULT_WIDTH)
            height = self._parse_dimension(params, "height", DEFAULT_HEIGHT)
            fmt = self._parse_format(params)
        except ParamError as exc:
            self._send_json(400, {"error": exc.message})
            return

        try:
            from tools import fake_image_renderer
        except ImportError:
            try:
                import fake_image_renderer  # type: ignore[no-redef]
            except ImportError:
                self._send_json(500, {"error": "image rendering unavailable: renderer module not found"})
                return

        try:
            image_bytes = fake_image_renderer.render_image(image_id, width, height, fmt)
        except RuntimeError as exc:
            # Renderer signals a missing optional dependency (e.g. Pillow) via RuntimeError.
            self._send_json(500, {"error": str(exc)})
            return

        self._send_image(image_bytes, CONTENT_TYPE_BY_FORMAT[fmt])

    def _parse_dimension(self, params: dict[str, list[str]], name: str, default: int) -> int:
        raw_values = params.get(name)
        if not raw_values:
            return default
        raw = raw_values[0]
        error = f"{name} must be an integer between {MIN_DIMENSION} and {MAX_DIMENSION}"
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise ParamError(error)
        if value < MIN_DIMENSION or value > MAX_DIMENSION:
            raise ParamError(error)
        return value

    def _parse_format(self, params: dict[str, list[str]]) -> str:
        raw_values = params.get("format")
        if not raw_values:
            return DEFAULT_FORMAT
        raw = raw_values[0].lower()
        fmt = FORMAT_ALIASES.get(raw)
        if fmt is None:
            raise ParamError("format must be one of: png, jpeg")
        return fmt

    # --- shared helpers -------------------------------------------------------

    def _read_json(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _parse_positive_amount(self, payload: dict[str, Any]) -> int | None:
        amount = payload.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            return None
        return amount

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_image(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def run(host: str = "127.0.0.1", port: int = DEFAULT_PORT, *, initial_balance: int = DEFAULT_BALANCE) -> ThreadingHTTPServer:
    FakeImageProviderHandler.balance = initial_balance
    FakeImageProviderHandler.next_image_id = 1
    server = ThreadingHTTPServer((host, port), FakeImageProviderHandler)
    print(f"Fake image provider listening on http://{host}:{server.server_port} with balance={initial_balance}")
    server.serve_forever()
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Taskr fake image provider.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", str(DEFAULT_PORT))))
    parser.add_argument("--initial-balance", type=int, default=DEFAULT_BALANCE)
    args = parser.parse_args()
    run(args.host, args.port, initial_balance=args.initial_balance)
