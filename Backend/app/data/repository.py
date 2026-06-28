from __future__ import annotations

import json
import pathlib
import sqlite3
import uuid
from collections.abc import Iterable
from typing import Any

from app.errors.data import FlowVersionNotFoundError, FlowVersionNotDraftError

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent  # Backend/
DB_PATH = ROOT / "taskr.db"
SCHEMA_PATH = pathlib.Path(__file__).resolve().parent / "schema.sql"  # app/data/schema.sql


_JSON_FIELDS = {
    "RUN": {"context"},
    "FLOW_NODE": {"input_mapping", "output_mapping", "policy_refs"},
    "INTEGRATION_BINDING": {"headers", "success_values", "failure_values", "skills"},
    "NODE_STATE": {"binding_snapshot", "native_state", "input", "raw_output", "output"},
    "QUESTION": {"options"},
    "LOOP_STATE": {"snapshot_metadata"},
    "LOOP_ITERATION": {"item", "output"},
}


class TaskrRepository:
    """All SQLite access lives here.

    The repository is intentionally thin: it runs raw SQL, converts JSON columns
    to Python dicts, and returns plain dicts. It does NOT contain business logic;
    that lives in TaskrRunner.
    """

    # ── Connection & schema management ──────────────────────────────────────────

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        """Run a SELECT and return a single row, or None."""
        row = self.conn.execute(query, params).fetchone()
        return self._row_to_dict(row) if row else None

    def _all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Run a SELECT and return every row as a dict."""
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]
