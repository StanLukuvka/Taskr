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

    @staticmethod
    def get_connection() -> sqlite3.Connection:
        """Open the SQLite DB, enable WAL and foreign keys, and apply the schema if needed."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        if not TaskrRepository._schema_exists(conn):
            conn.executescript(SCHEMA_PATH.read_text())
            conn.commit()
        return conn
    
    @staticmethod
    def _schema_exists(conn: sqlite3.Connection) -> bool:
        """Quick check: does the schema look already applied?"""
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'FLOW'"
        ).fetchone()
        return row is not None

    @staticmethod
    def apply_schema() -> None:
        """Force-apply the schema. Used by FastAPI on startup."""
        conn = TaskrRepository.get_connection()
        try:
            conn.executescript(SCHEMA_PATH.read_text())
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def reset_db() -> None:
        """Delete the DB file and re-apply the schema. Useful for tests."""
        DB_PATH.unlink(missing_ok=True)
        TaskrRepository.apply_schema()

    def _one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        """Run a SELECT and return a single row, or None."""
        row = self.conn.execute(query, params).fetchone()
        return self._row_to_dict(row) if row else None

    def _all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Run a SELECT and return every row as a dict."""
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: sqlite3.Row, table_hint: str | None = None) -> dict[str, Any]:
        """Convert a sqlite3.Row to a Python dict and auto-parse JSON columns.

        If table_hint is provided, only the JSON columns for that table are
        parsed. If None, every known JSON column is attempted (safe because
        json.loads only runs on string values).
        """
        data = dict(row)
        tables = [table_hint] if table_hint else _JSON_FIELDS.keys()
        for table in tables:
            for key in _JSON_FIELDS.get(table, set()):
                if key in data and isinstance(data[key], str):
                    data[key] = json.loads(data[key])
        return data

    def _json(self, value: Any) -> str | None:
        """Serialize a value to JSON, or return None for None."""
        if value is None:
            return None
        return json.dumps(value)

    # ── Seeding ──────────────────────────────────────────────────

    def seed_data(self) -> None:
        """Seed the demo flow data. Delegates to app.seed.seed_demo_data."""
        from app.flow.seed import seed_demo_data
        seed_demo_data(self)

    # ── Flow CRUD ──────────────────────────────────────────────────

    def load_all_flows(self) -> list[dict[str, Any]]:
        """Return every flow in the system, ordered by title."""
        return self._all("SELECT * FROM FLOW ORDER BY title, slug")

    # ── Run lifecycle ──────────────────────────────────────────────────

    def load_all_runs(self) -> list[dict[str, Any]]:
        """Return every run, ordered by creation time."""
        return self._all("SELECT * FROM RUN ORDER BY created_at, run_id")

    def load_flow(self, flow_id: str) -> dict[str, Any] | None:
        """Fetch a single flow by id."""
        row = self.conn.execute("SELECT * FROM FLOW WHERE flow_id = ?", (flow_id,)).fetchone()
        return self._row_to_dict(row, "FLOW") if row else None

    def load_flow_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Fetch a flow by its URL-friendly slug."""
        return self._one("SELECT * FROM FLOW WHERE slug = ?", (slug,))

    # ── Flow version management ──────────────────────────────────────────────────

    def load_flow_version(self, flow_version_id: str) -> dict[str, Any] | None:
        """Fetch a single flow version by id."""
        return self._one("SELECT * FROM FLOW_VERSION WHERE flow_version_id = ?", (flow_version_id,))

    def create_flow_version(self, flow_id: str) -> dict[str, Any]:
        """Create a new draft flow version for a flow.

        The version number is auto-incremented based on existing versions.
        """
        row = self.conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS next_version FROM FLOW_VERSION WHERE fk_flow_id = ?",
            (flow_id,),
        ).fetchone()
        next_version = int(row["next_version"])
        version_id = f"fv-{uuid.uuid4().hex[:12]}"
        self.conn.execute(
            "INSERT INTO FLOW_VERSION (flow_version_id, fk_flow_id, version, status) VALUES (?, ?, ?, 'draft')",
            (version_id, flow_id, next_version),
        )
        self.conn.commit()
        return self.load_flow_version(version_id)

    def publish_flow_version(self, flow_version_id: str) -> dict[str, Any]:
        """Activate a draft flow version. Any previously active version is archived."""
        version = self.load_flow_version(flow_version_id)
        if not version:
            raise FlowVersionNotFoundError(entity_id=flow_version_id)
        if version["status"] != "draft":
            raise FlowVersionNotDraftError(entity_id=flow_version_id)

        self.conn.execute(
            "UPDATE FLOW_VERSION SET status = 'archived' WHERE fk_flow_id = ? AND status = 'active'",
            (version["fk_flow_id"],),
        )
        self.conn.execute(
            "UPDATE FLOW_VERSION SET status = 'active', activated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE flow_version_id = ?",
            (flow_version_id,),
        )
        self.conn.commit()
        return self.load_flow_version(flow_version_id)
