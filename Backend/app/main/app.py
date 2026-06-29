from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.data.repository import TaskrRepository
from app.endpoint.bindings import router as bindings_router
from app.endpoint.node_states import router as node_states_router
from app.endpoint.runs import router as runs_router
from app.errors.handlers import register_handlers
from app.flow.endpoints import router as flows_router

"""FastAPI application.

The single entry point for the Taskr HTTP API. It wires together the
routers, CORS, startup schema bootstrap, and the static frontend mount.
Endpoint logic lives in the app.endpoint and app.flow subpackages; this
module only assembles the application.
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
        "name": "Flow Nodes",
        "description": "Create and inspect nodes inside a flow version.",
    },
    {
        "name": "Bindings",
        "description": "Create and manage integration bindings for external API and Hermes connections.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the application database and seed demo data on startup.

    Resets the database to a clean state on every restart so the demo
    always starts from a known-good baseline. This avoids stale data
    inconsistencies from schema changes or partial seeds.
    """
    TaskrRepository.reset_db()
    conn = TaskrRepository.get_connection()
    try:
        repo = TaskrRepository(conn)
        repo.seed_data()
    finally:
        conn.close()
    yield


app = FastAPI(title="Taskr", openapi_tags=OPENAPI_TAGS, lifespan=lifespan)

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
app.include_router(bindings_router)

register_handlers(app)


_frontend_path = Path(__file__).resolve().parent.parent.parent.parent / "Frontend" / "dist"
_frontend_index = _frontend_path / "index.html"
_spa_paths = ("/runs", "/flows", "/bindings", "/flow_versions")


@app.middleware("http")
async def serve_frontend_history_routes(request: Request, call_next):
    wants_html = "text/html" in request.headers.get("accept", "")
    if (
        request.method == "GET"
        and wants_html
        and _frontend_index.exists()
        and request.url.path.startswith(_spa_paths)
    ):
        return FileResponse(_frontend_index)
    return await call_next(request)


if _frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_path), html=True), name="frontend")
