from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.flow.endpoints import router as flows_router
from app.endpoint.node_states import router as node_states_router
from app.endpoint.runs import router as runs_router
from app.data.repository import TaskrRepository
from app.errors.handlers import register_handlers

"""FastAPI application.

The single entry point for the Taskr HTTP API. It wires together the
routers, CORS, startup schema bootstrap, and the static frontend mount.
Endpoint logic lives in the app.endpoints subpackage; this module only
assembles the application.
"""

OPENAPI_TAGS = [
    {
        "name": "Flows",
        "description": "Discover and manage the top-level flows that Taskr can execute.",
    },
    {
        "name": "Runs",
        "description": "Create and advance execution runs for a selected flow.",
    },
    {
        "name": "Flow Versions",
        "description": "Inspect and manage versioned flow definitions for a flow.",
    },
    {
        "name": "Node States",
        "description": "Inspect and interact with the runtime states of individual flow nodes.",
    },
    {
        "name": "Questions",
        "description": "View and answer questions raised by pausing node states.",
    },
    {
        "name": "Flow Nodes",
        "description": "Create and inspect nodes inside a flow version.",
    },
]

app = FastAPI(title="Taskr", openapi_tags=OPENAPI_TAGS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flows_router)
app.include_router(runs_router)
app.include_router(node_states_router)

register_handlers(app)


@app.on_event("startup")
def on_startup():
    """Initialize the application database schema on startup.

    This event handler runs once when the FastAPI process starts. It ensures
    that all tables required by the repository layer exist before the first
    request is handled.
    """
    TaskrRepository.apply_schema()


_frontend_path = Path(__file__).resolve().parent.parent.parent.parent / "Frontend" / "dist"
if _frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_path), html=True), name="frontend")
