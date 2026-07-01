from __future__ import annotations

import os
import re
from typing import Any

import httpx

from app.errors.integration import HermesConfigurationError
from app.logic.integrations.result import IntegrationResult


def _classify_hermes_http_error(status_code: int) -> tuple[str, bool]:
    if status_code in {408, 429, 502, 503, 504}:
        return "http_server", True
    if 400 <= status_code < 500:
        return "http_client", False
    if 500 <= status_code < 600:
        return "http_server", False
    return "unknown", False


class HermesIntegration:
    """Real HTTP client for the Hermes /v1/runs API."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._base_url_cache: str | None = None

    def _resolve_base_url(self) -> str:
        if self._base_url_cache is None:
            url = os.environ.get("HERMES_URL")
            if not url:
                raise HermesConfigurationError("HERMES_URL is not set")
            self._base_url_cache = url.rstrip("/")
        return self._base_url_cache

    def _headers(self) -> dict[str, str]:
        token = os.environ.get("API_SERVER_KEY")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _render_template(template: str, data: dict[str, Any]) -> str:
        def repl(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            return str(data.get(key, match.group(0)))

        return re.sub(r"\{\{\s*([\w\.]+)\s*\}\}", repl, template)

    def _http_error_result(self, exc: httpx.HTTPError) -> IntegrationResult:
        if isinstance(exc, httpx.HTTPStatusError):
            category, retryable = _classify_hermes_http_error(exc.response.status_code)
            return IntegrationResult(
                status="failed",
                error_code=f"HTTP_{exc.response.status_code}",
                error_message=f"HTTP {exc.response.status_code}: {exc.response.text}",
                error_category=category,
                retryable=retryable,
                native_state={"status_code": exc.response.status_code, "body": exc.response.text},
            )
        if isinstance(exc, httpx.TimeoutException):
            return IntegrationResult(
                status="failed",
                error_code="timeout",
                error_message=str(exc),
                error_category="timeout",
                retryable=True,
                native_state={"exception": type(exc).__name__},
            )
        return IntegrationResult(
            status="failed",
            error_code="transport_error",
            error_message=str(exc),
            error_category="transport",
            retryable=True,
            native_state={"exception": type(exc).__name__},
        )

    def create_task(
        self,
        input_data: dict[str, Any],
        binding_config: dict[str, Any] | None = None,
        *,
        run_id: str | None = None,
        node_state_id: str | None = None,
    ) -> IntegrationResult:
        config = (binding_config or {}).get("config") or (binding_config or {})
        rendered_input = self._render_template(config.get("task_title_template", ""), input_data)
        rendered_instructions = self._render_template(config.get("task_body_template", ""), input_data)
        session_id = "taskr"
        if run_id:
            session_id = f"{session_id}-{run_id}"
        if node_state_id:
            session_id = f"{session_id}-{node_state_id}"
        payload = {
            "input": rendered_input,
            "session_id": session_id,
            "instructions": rendered_instructions,
            "skills": config.get("skills", []),
        }
        url = f"{self._resolve_base_url()}/runs"
        try:
            response = httpx.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return self._http_error_result(exc)
        body = response.json()
        return IntegrationResult(status="running", external_ref=body.get("run_id"), native_state=body)

    def inspect_task(self, run_id: str) -> IntegrationResult:
        url = f"{self._resolve_base_url()}/runs/{run_id}"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return self._http_error_result(exc)
        return self._to_result(response.json())

    def _to_result(self, payload: dict[str, Any]) -> IntegrationResult:
        status = payload.get("status", "failed")
        cost_cents = payload.get("cost_cents")
        if cost_cents is not None:
            try:
                cost_cents = int(cost_cents)
            except (TypeError, ValueError):
                cost_cents = None
        if status in {"started", "running"}:
            return IntegrationResult(
                status="running",
                external_ref=payload.get("run_id"),
                native_state=payload,
                cost_cents=cost_cents,
            )
        if status == "completed":
            return IntegrationResult(
                status="completed",
                external_ref=payload.get("run_id"),
                output=payload.get("output"),
                native_state=payload,
                cost_cents=cost_cents,
            )
        return IntegrationResult(
            status="failed",
            external_ref=payload.get("run_id"),
            error_code="hermes_failed",
            error_message=f"Hermes run ended with status {status}",
            error_category="external_failure",
            retryable=False,
            native_state=payload,
            cost_cents=cost_cents,
        )
