"""Data-layer domain exceptions.

Raised by the repository when persistence-layer invariants are violated.
"""

from app.errors.base import TaskrError


class FlowVersionNotFoundError(TaskrError):
    status_code = 404
    detail = "Flow version not found"


class FlowVersionNotDraftError(TaskrError):
    status_code = 400
    detail = "Flow version is not in draft status"


class FlowVersionNotActiveError(TaskrError):
    """Raised when a run is created against a non-active flow version."""

    status_code = 400
    detail = "Flow version is not active"


class CostAmountInvalidError(TaskrError):
    """Raised when a cost-tracking mutation receives a negative amount."""

    status_code = 400
    detail = "Cost amount must be non-negative"
