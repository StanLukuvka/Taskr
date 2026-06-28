from __future__ import annotations

import json
import re
from string import Formatter
from typing import Any

import httpx

from app.logic.integrations.fake import IntegrationResult


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


class ApiIntegration:
    """Real HTTP API integration for API-backed flow nodes.

    ``start`` dispatches a configured HTTP request and returns an
    :class:`IntegrationResult`. ``inspect`` is intended for polling and raises
    ``NotImplementedError`` for the synchronous ``response`` completion mode.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        """Initialize the integration with a request timeout.

        Args:
            timeout: Default timeout in seconds for each HTTP request.
        """
        self.timeout = timeout

    def start(self, binding_config: dict[str, Any], input_data: dict[str, Any]) -> IntegrationResult:
        """Execute the configured HTTP request.

        Args:
            binding_config: API binding configuration including ``method``,
                ``url_template``, ``headers``, and optional ``completion_mode``.
            input_data: Resolved input data used to render the URL template.

        Returns:
            An :class:`IntegrationResult` describing the completed or failed
            HTTP call.
        """
        method = binding_config.get("method", "GET")
        url_template = binding_config["url_template"]
        headers = dict(binding_config.get("headers") or {})
        request_mode = binding_config.get("request_mode", "json")
        url = resolve_url_template(url_template, input_data)

        body = None
        if method in {"POST", "PUT", "PATCH"} and request_mode == "json" and input_data:
            body = json.dumps(input_data)
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

        try:
            response = httpx.request(method, url, headers=headers, content=body, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return IntegrationResult(
                status="failed",
                error_code="http_error",
                error_message=f"HTTP {exc.response.status_code}: {exc.response.text}",
                native_state={"status_code": exc.response.status_code, "body": exc.response.text},
            )
        except httpx.HTTPError as exc:
            return IntegrationResult(
                status="failed",
                error_code="http_error",
                error_message=str(exc),
                native_state={"exception": type(exc).__name__},
            )

        return IntegrationResult(
            status="completed",
            output={"status": "ok", "status_code": response.status_code, "body": response.text},
            native_state={"status_code": response.status_code, "body": response.text},
        )

    def inspect(self, external_ref: str, binding_config: dict[str, Any] | None = None) -> IntegrationResult:
        """Poll the status of an asynchronous API call.

        Args:
            external_ref: Identifier returned by a previous ``start`` call.
            binding_config: Optional binding config used for polling.

        Raises:
            NotImplementedError: Polling is not implemented for the first
                version of the real API integration.
        """
        raise NotImplementedError("ApiIntegration.inspect polling is not implemented")
