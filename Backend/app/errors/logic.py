"""Logic-layer domain exceptions.

Raised by the runner when execution-state invariants are violated.
"""

from app.errors.base import TaskrError

class FlowNodeNotFoundError(TaskrError):
    status_code = 404
    detail = "Flow node not found"

