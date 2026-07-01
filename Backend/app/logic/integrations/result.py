from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IntegrationResult:
    status: str
    external_ref: str | None = None
    output: Any = None
    error_code: str | None = None
    error_message: str | None = None
    error_category: str | None = None
    retryable: bool | None = None
    native_state: dict | None = None
    cost_cents: int | None = None
