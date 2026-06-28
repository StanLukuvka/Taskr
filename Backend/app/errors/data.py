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
