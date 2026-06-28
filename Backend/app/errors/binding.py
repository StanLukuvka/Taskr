"""Typed domain exceptions for integration bindings.

All binding exceptions inherit from TaskrError so tests can catch ValueError
and the FastAPI exception handler can convert them into proper HTTP responses.
"""

from app.errors.base import TaskrError


class BindingNotFoundError(TaskrError):
    """Raised when a requested binding does not exist."""

    status_code = 404
    detail = "Binding not found"


class BindingKindMismatchError(TaskrError):
    """Raised when an operation expects a binding of a different kind."""

    status_code = 400
    detail = "Binding kind mismatch"


class BindingInUseError(TaskrError):
    """Raised when a binding cannot be deleted because flow nodes reference it."""

    status_code = 409
    detail = "Binding is in use by one or more flow nodes"
