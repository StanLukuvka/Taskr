"""Flow-layer domain exceptions.

Raised by flow management endpoints and flow operations.
"""

from app.errors.base import TaskrError


class FlowSlugAlreadyInUseError(TaskrError):
    status_code = 400
    detail = "Flow slug is already in use"
