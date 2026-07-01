from __future__ import annotations

import ipaddress
import json
import os
import re
from string import Formatter
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from app.logic.integrations.result import IntegrationResult


def _validate_url(url: str, *, allow_private: bool = False) -> None:
    """Validate a resolved URL before it is sent by the server.

    Blocks non-HTTP(S) schemes, embedded credentials, and private/loopback
    hosts unless the caller has explicitly opted in (e.g. tests). This is a
    defense-in-depth guard against SSRF from binding configs or user input.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme must be http or https, got {parsed.scheme!r}")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not contain credentials")

    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL must have a host")

    if not allow_private:
        if host.lower() in {"localhost", "127.0.0.1", "::1", "0:0:0:0:0:0:0:1"}:
            raise ValueError("URL must not target localhost/loopback")
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast:
                raise ValueError("URL must not target private/reserved/multicast IP")
        except ValueError:
            pass


def resolve_url_template(template: str, data: dict[str, Any] | None = None) -> str:
    """Resolve a URL template against a flat dictionary of values.

    Supports both ``{key}`` (string.Formatter) style placeholders and simple
    ``$key`` style placeholders. Values that are missing are left unchanged so
    callers can still perform additional resolution if needed, but the common
    case of simple substitution is handled here.

    Args:
        template: URL template containing placeholders.
        data: Dictionary of values to substitute. Defaults to an empty dict.

    Returns:
        The URL template with all known placeholders replaced.
    """
    data = data or {}

    # $-style placeholders first
    def _replace_var(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(data.get(key, match.group(0)))

    resolved = re.sub(r"\$([a-zA-Z_][a-zA-Z0-9_]*)", _replace_var, template)

    # {key}-style placeholders second
    formatter = Formatter()
    result_parts = []
    for literal_text, field_name, format_spec, conversion in formatter.parse(resolved):
        if field_name is None:
            result_parts.append(literal_text)
            continue
        value = data.get(field_name)
        if value is None:
            result_parts.append(f"{literal_text}{{{field_name}}}")
            continue
        fmt = ""
        if conversion:
            fmt += f"!{conversion}"
        if format_spec:
            fmt += f":{format_spec}"
        result_parts.append(f"{literal_text}{formatter.convert_field(value, conversion) if conversion else value:{format_spec}}")

    return "".join(result_parts)


def _default_auth_lookup(auth_ref: str | None) -> str | None:
    """Resolve a configured auth reference from the environment."""
    if not auth_ref:
        return None
    env_name = f"TASKR_AUTH_{auth_ref.upper().replace('-', '_')}"
    return os.environ.get(env_name)


def _extract_json_path(data: Any, path: str | None) -> Any:
    """Extract a tiny dot/bracket JSON path from a decoded JSON payload."""
    if not path:
        return data

    current = data
    for part in path.split("."):
        if current is None:
            return None

        key = part
        indices: list[int] = []
        while key.endswith("]") and "[" in key:
            key, index_text = key[:-1].rsplit("[", 1)
            try:
                indices.insert(0, int(index_text))
            except ValueError:
                return None

        if key:
            if not isinstance(current, dict):
                return None
            current = current.get(key)

        for index in indices:
            if not isinstance(current, list) or index < 0 or index >= len(current):
                return None
            current = current[index]

    return current


def _classify_http_error(status_code: int) -> tuple[str, bool]:
    """Return broad error category and retryability for an HTTP status."""
    if status_code in {408, 429, 502, 503, 504}:
        return "http_server", True
    if 400 <= status_code < 500:
        return "http_client", False
    if 500 <= status_code < 600:
        return "http_server", False
    return "unknown", False


class ApiIntegration:
    """Real HTTP API integration for API-backed flow nodes.

    ``start`` dispatches a configured HTTP request and returns an
    :class:`IntegrationResult`. ``inspect`` supports asynchronous polling when
    the binding uses ``completion_mode=poll``.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        auth_lookup: Callable[[str | None], str | None] | None = None,
        allow_private: bool = False,
    ) -> None:
        """Initialize the integration with a request timeout and auth lookup."""
        self.timeout = timeout
        self.auth_lookup = auth_lookup or _default_auth_lookup
        self.allow_private = allow_private

    def _http_error_result(self, exc: httpx.HTTPError, external_ref: str | None = None) -> IntegrationResult:
        """Convert an httpx exception into a classified integration failure."""
        if isinstance(exc, httpx.TimeoutException):
            return IntegrationResult(
                status="failed",
                external_ref=external_ref,
                error_code="timeout",
                error_message=str(exc),
                error_category="timeout",
                retryable=True,
                native_state={"exception": type(exc).__name__},
            )
        if isinstance(exc, (httpx.ConnectError, httpx.NetworkError)):
            return IntegrationResult(
                status="failed",
                external_ref=external_ref,
                error_code="transport",
                error_message=str(exc),
                error_category="transport",
                retryable=True,
                native_state={"exception": type(exc).__name__},
            )
        if isinstance(exc, httpx.HTTPStatusError):
            category, retryable = _classify_http_error(exc.response.status_code)
            return IntegrationResult(
                status="failed",
                external_ref=external_ref,
                error_code="http_error",
                error_message=f"HTTP {exc.response.status_code}: {exc.response.text}",
                error_category=category,
                retryable=retryable,
                native_state={"status_code": exc.response.status_code, "body": exc.response.text},
            )
        return IntegrationResult(
            status="failed",
            external_ref=external_ref,
            error_code="http_error",
            error_message=str(exc),
            error_category="unknown",
            retryable=False,
            native_state={"exception": type(exc).__name__},
        )

    def _resolve_headers(self, binding_config: dict[str, Any]) -> dict[str, str]:
        """Resolve binding headers, adding bearer auth from ``auth_ref`` when available."""
        headers = dict(binding_config.get("headers") or {})
        auth_ref = binding_config.get("auth_ref")
        if "Authorization" not in headers and auth_ref:
            token = self.auth_lookup(auth_ref)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    def start(
        self,
        binding_config: dict[str, Any],
        input_data: dict[str, Any],
        run_id: str | None = None,
    ) -> IntegrationResult:
        """Execute the configured HTTP request."""
        method = binding_config.get("method", "GET")
        url_template = binding_config["url_template"]
        headers = self._resolve_headers(binding_config)
        request_mode = binding_config.get("request_mode", "json")
        completion_mode = binding_config.get("completion_mode", "response")
        url = resolve_url_template(url_template, input_data)

        body = None
        if method in {"POST", "PUT", "PATCH"} and request_mode == "json" and input_data:
            body = json.dumps(input_data)
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

        try:
            _validate_url(url, allow_private=self.allow_private)
            response = httpx.request(
                method, url, headers=headers, content=body, timeout=self.timeout, follow_redirects=False
            )
            response.raise_for_status()
        except ValueError as exc:
            return IntegrationResult(
                status="failed",
                error_code="invalid_url",
                error_message=str(exc),
                error_category="configuration",
                retryable=False,
                native_state={"url": url_template},
            )
        except httpx.HTTPError as exc:
            return self._http_error_result(exc)

        if completion_mode == "poll":
            try:
                payload = response.json()
            except ValueError:
                payload = {"body": response.text}
            external_ref = _extract_json_path(payload, binding_config.get("external_ref_path"))
            return IntegrationResult(
                status="running",
                external_ref=str(external_ref) if external_ref is not None else None,
                native_state={"status_code": response.status_code, "body": payload},
            )

        try:
            json_body = response.json()
        except ValueError:
            json_body = None

        return IntegrationResult(
            status="completed",
            output={"status": "ok", "status_code": response.status_code, "body": response.text, "json": json_body},
            native_state={"status_code": response.status_code, "body": response.text},
        )

    def inspect(self, external_ref: str, binding_config: dict[str, Any] | None = None) -> IntegrationResult:
        """Poll the status of an asynchronous API call."""
        binding_config = binding_config or {}
        if binding_config.get("completion_mode", "response") != "poll":
            return IntegrationResult(
                status="failed",
                error_code="inspect_not_supported",
                error_message="ApiIntegration.inspect is only supported for poll mode",
                error_category="unknown",
                retryable=False,
            )

        status_url_template = binding_config.get("status_url_template")
        if not status_url_template:
            return IntegrationResult(
                status="failed",
                external_ref=external_ref,
                error_code="missing_status_url",
                error_message="status_url_template is required for poll mode",
                error_category="unknown",
                retryable=False,
            )

        url = resolve_url_template(status_url_template, {"external_ref": external_ref, "ref": external_ref})
        status_method = binding_config.get("status_method", "GET")

        try:
            _validate_url(url, allow_private=self.allow_private)
            response = httpx.request(
                status_method,
                url,
                headers=self._resolve_headers(binding_config),
                timeout=self.timeout,
                follow_redirects=False,
            )
            response.raise_for_status()
        except ValueError as exc:
            return IntegrationResult(
                status="failed",
                external_ref=external_ref,
                error_code="invalid_url",
                error_message=str(exc),
                error_category="configuration",
                retryable=False,
                native_state={"url": status_url_template},
            )
        except httpx.HTTPError as exc:
            return self._http_error_result(exc, external_ref=external_ref)

        try:
            payload = response.json()
        except ValueError:
            return IntegrationResult(
                status="failed",
                external_ref=external_ref,
                error_code="invalid_json",
                error_message=f"Status response was not JSON: {response.text}",
                error_category="decode",
                retryable=False,
                native_state={"status_code": response.status_code},
            )

        status = _extract_json_path(payload, binding_config.get("status_path"))
        if status is None:
            return IntegrationResult(
                status="failed",
                external_ref=external_ref,
                error_code="missing_status",
                error_message="status_path did not resolve to a value",
                error_category="unknown",
                retryable=False,
                native_state={"status_code": response.status_code, "body": payload},
            )

        status_str = str(status).lower()
        success_values = {str(v).lower() for v in binding_config.get("success_values", ["success", "completed"])}
        failure_values = {str(v).lower() for v in binding_config.get("failure_values", ["failure", "failed", "cancelled"])}

        if status_str in success_values:
            if binding_config.get("result_path") is not None:
                output = _extract_json_path(payload, binding_config.get("result_path"))
            else:
                output = payload
            return IntegrationResult(
                status="completed",
                external_ref=external_ref,
                output=output,
                native_state={"status_code": response.status_code, "body": payload},
            )

        if status_str in failure_values:
            return IntegrationResult(
                status="failed",
                external_ref=external_ref,
                error_code="external_failure",
                error_message=f"External status was {status}",
                error_category="external_failure",
                retryable=False,
                native_state={"status_code": response.status_code, "body": payload},
            )

        return IntegrationResult(
            status="running",
            external_ref=external_ref,
            native_state={"status_code": response.status_code, "body": payload},
        )
