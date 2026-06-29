"""FastAPI exception handlers for Taskr domain errors.

Registers a handler for TaskrError that converts domain exceptions into JSON
responses with the appropriate HTTP status code. Generic exception logging is
left to ASGI/uvicorn (or FastAPI's default 500 handler) so errors are not hidden.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors.base import TaskrError


def register_handlers(app: FastAPI) -> None:
    """Install TaskrError exception handlers on the FastAPI app."""
    @app.exception_handler(TaskrError)
    async def taskr_error_handler(request: Request, exc: TaskrError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "entity_id": exc.entity_id},
        )
