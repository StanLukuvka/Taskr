"""Integration tests for the real HTTP API integration.

These tests spin up a local HTTP server thread so the suite exercises real
HTTP requests without depending on external network services.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Generator

import pytest

from app.logic.integrations.api import ApiIntegration, resolve_url_template
from app.logic.integrations.fake import IntegrationResult


class _PingHandler(BaseHTTPRequestHandler):
    """Minimal handler that returns 200 for /ok and 500 for /fail."""

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/ok":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "pong"}).encode())
        elif self.path == "/fail":
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"internal server error")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


@pytest.fixture
def api_integration() -> ApiIntegration:
    """Return an API integration with a short timeout for tests."""
    return ApiIntegration(timeout=2.0)


@pytest.fixture
def local_server() -> Generator[str, None, None]:
    """Yield the base URL of a local HTTP server that handles /ok and /fail."""
    server = HTTPServer(("127.0.0.1", 0), _PingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = server.server_address
    yield f"http://{address[0]}:{address[1]}"
    server.shutdown()
    server.server_close()


def test_resolve_url_template_curly() -> None:
    """``resolve_url_template`` substitutes curly-braced placeholders."""
    template = "https://api.example.com/v1/items/{id}"
    assert resolve_url_template(template, {"id": "abc-123"}) == "https://api.example.com/v1/items/abc-123"


def test_resolve_url_template_dollar() -> None:
    """``resolve_url_template`` substitutes dollar-prefixed placeholders."""
    template = "https://api.example.com/v1/items/$id"
    assert resolve_url_template(template, {"id": "abc-123"}) == "https://api.example.com/v1/items/abc-123"


def test_resolve_url_template_missing_key_left_intact() -> None:
    """Unknown placeholders are left in the template so callers can re-resolve."""
    template = "https://api.example.com/v1/items/{id}/others/{other}"
    assert resolve_url_template(template, {"id": "abc"}) == "https://api.example.com/v1/items/abc/others/{other}"


def test_api_ping_success(api_integration: ApiIntegration, local_server: str) -> None:
    """A real GET to a 200 endpoint returns a completed result."""
    binding = {"method": "GET", "url_template": f"{local_server}/ok", "headers": {}}
    result = api_integration.start(binding, {})

    assert isinstance(result, IntegrationResult)
    assert result.status == "completed"
    assert result.output == {"status": "ok", "status_code": 200, "body": '{"message": "pong"}'}
    assert result.native_state == {"status_code": 200, "body": '{"message": "pong"}'}


def test_api_ping_failure(api_integration: ApiIntegration, local_server: str) -> None:
    """A real GET to a 500 endpoint returns a failed result."""
    binding = {"method": "GET", "url_template": f"{local_server}/fail", "headers": {}}
    result = api_integration.start(binding, {})

    assert isinstance(result, IntegrationResult)
    assert result.status == "failed"
    assert result.error_code == "http_error"
    assert "500" in (result.error_message or "")
    assert result.native_state is not None
    assert result.native_state.get("status_code") == 500


def test_api_inspect_raises_not_implemented(api_integration: ApiIntegration) -> None:
    """Polling is not implemented in the first version."""
    with pytest.raises(NotImplementedError):
        api_integration.inspect("ref-123", {})
