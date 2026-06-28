"""Base exception class for all Taskr domain errors.

Every domain-specific exception inherits from TaskrError, carrying:
  - status_code: the HTTP status to return (default 400)
  - detail: a human-readable error message
  - entity_id: optional identifier of the entity that caused the error

The FastAPI exception handler in handlers.py catches TaskrError and
converts it to a JSON response using these attributes.
"""


class TaskrError(ValueError):
    """Base for all Taskr domain exceptions.

    Inherits from ValueError so that existing code catching ValueError
    (including tests using pytest.raises(ValueError, match=...)) continues
    to work. The .status_code and .entity_id attributes allow the FastAPI
    exception handler to produce the correct HTTP response.
    """

    status_code: int = 400
    detail: str = "Taskr error"

    def __init__(self, detail: str | None = None, *, entity_id: str | None = None):
        self.detail = detail or self.detail
        self.entity_id = entity_id
        super().__init__(self.detail)
