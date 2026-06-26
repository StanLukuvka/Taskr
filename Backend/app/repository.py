from __future__ import annotations

import json
import pathlib
import sqlite3
import uuid
from collections.abc import Iterable
from typing import Any

# Paths to the project root, the SQLite database file, and the canonical schema DDL.
# The DB is created automatically on first connection if the 'flows' table is missing.
ROOT = pathlib.Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "taskr.db"
SCHEMA_PATH = ROOT / "schema.sql"


# Columns that SQLite stores as JSON text. When rows are converted to dicts
# via _row_to_dict(), these columns are parsed with json.loads(). This keeps
# the raw SQL simple while still letting Python work with dicts/lists.
_JSON_FIELDS = {
    "runs": {"context"},
    "flow_nodes": {"input_mapping", "output_mapping", "policy_refs"},
    "integration_bindings": {"headers", "success_values", "failure_values", "skills"},
    "node_states": {"binding_snapshot", "native_state", "input", "raw_output", "output"},
    "questions": {"options"},
    "loop_states": {"snapshot_metadata"},
    "loop_iterations": {"item", "output"},
}


class TaskrRepository:
    """All SQLite access lives here.

    The repository is intentionally thin: it runs raw SQL, converts JSON columns
    to Python dicts, and returns plain dicts. It does NOT contain business logic;
    that lives in TaskrRunner.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    # ------------------------------------------------------------------
    # Low-level query helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

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
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'flows'"
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

    # ------------------------------------------------------------------
    # Seed data for the demo flow
    # ------------------------------------------------------------------
    # This is temporary scaffolding: it creates a sample "Soda Comparison"
    # flow so the MVP can be exercised without a flow-design UI. The sample
    # flow exercises API calls, a foreach loop, and Hermes question blocking.

    def seed_data(self) -> None:
        """Insert the demo flow, flow version, bindings, and nodes if they do not exist."""
        self.conn.execute(
            "INSERT OR IGNORE INTO flows (id, title, slug, question) VALUES (?, ?, ?, ?)",
            ("flow-soda", "Soda Comparison", "soda-comparison", "Compare soda products"),
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO flow_versions (id, flow_id, version, status) VALUES (?, ?, ?, ?)",
            ("fv-1", "flow-soda", 1, "draft"),
        )

        bindings = [
            ("b-api-collect", "api", "Collect Products"),
            ("b-hermes-research", "hermes", "Research Product"),
            ("b-api-notify", "api", "Send Notification"),
        ]
        for binding in bindings:
            self.conn.execute(
                "INSERT OR IGNORE INTO integration_bindings (id, kind, display_title) VALUES (?, ?, ?)",
                binding,
            )

        self.conn.execute(
            "INSERT OR IGNORE INTO api_binding_config (binding_id, method, url_template, completion_mode) VALUES (?, ?, ?, ?)",
            ("b-api-collect", "POST", "https://fake.api/collect", "response"),
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO api_binding_config (binding_id, method, url_template, completion_mode) VALUES (?, ?, ?, ?)",
            ("b-api-notify", "POST", "https://fake.api/notify", "response"),
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO hermes_binding_config (binding_id, board, task_title_template, task_body_template) VALUES (?, ?, ?, ?)",
            ("b-hermes-research", "taskr", "Research {{product.name}}", "Research {{product.name}} for soda comparison."),
        )

        # ord defines sibling order; parent_node_id defines the tree.
        flow_nodes = [
            (
                "n-collect", "fv-1", None, 0, "Collect Products", "api", "b-api-collect",
                self._json({}), self._json({"products": "$result.products"}), None, "stop",
            ),
            (
                "n-foreach", "fv-1", None, 1, "For Each Product", "foreach", None,
                self._json({}), self._json({}), "$nodes.n-collect.output.products", "stop",
            ),
            (
                "n-research", "fv-1", "n-foreach", 0, "Research Product", "hermes", "b-hermes-research",
                self._json({"product": "$item"}), self._json({"result": "$result.summary"}), None, "stop",
            ),
            (
                "n-notify", "fv-1", None, 2, "Send Notification", "api", "b-api-notify",
                self._json({}), self._json({}), None, "continue",
            ),
        ]
        for node in flow_nodes:
            node_id = node[0]
            exists = self.conn.execute("SELECT 1 FROM flow_nodes WHERE id = ?", (node_id,)).fetchone()
            if exists:
                continue
            self.conn.execute(
                """
                INSERT INTO flow_nodes (
                    id, flow_version_id, parent_node_id, ord, title, kind, binding_id,
                    input_mapping, output_mapping, items_path, failure_policy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                node,
            )

        # The schema triggers prevent edits to published flow versions, so we
        # must activate the version only after all nodes are written.
        self.conn.execute(
            """
            UPDATE flow_versions
            SET status = 'active', activated_at = COALESCE(activated_at, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            WHERE id = 'fv-1' AND status = 'draft'
            """
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Flows, flow versions, and runs
    # ------------------------------------------------------------------

    def load_all_flows(self) -> list[dict[str, Any]]:
        """Return every flow in the system, ordered by title."""
        return self._all("SELECT * FROM flows ORDER BY title, slug")

    def load_flow_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Fetch a flow by its URL-friendly slug."""
        return self._one("SELECT * FROM flows WHERE slug = ?", (slug,))

    def load_flow_version(self, flow_version_id: str) -> dict[str, Any] | None:
        """Fetch a single flow version by id."""
        return self._one("SELECT * FROM flow_versions WHERE id = ?", (flow_version_id,))

    def load_active_flow_version(self, flow_id: str) -> dict[str, Any] | None:
        """Fetch the currently active flow version for a flow."""
        return self._one(
            "SELECT * FROM flow_versions WHERE flow_id = ? AND status = 'active' ORDER BY version DESC LIMIT 1",
            (flow_id,),
        )

    def create_run(self, flow_id: str, flow_version_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a new run and return it. Runs start with status 'running'."""
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        self.conn.execute(
            """
            INSERT INTO runs (id, flow_id, flow_version_id, status, context, started_at)
            VALUES (?, ?, ?, 'running', ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            """,
            (run_id, flow_id, flow_version_id, self._json(context or {})),
        )
        self.conn.commit()
        return self.load_run(run_id)

    def list_runs(self, statuses: Iterable[str]) -> list[dict[str, Any]]:
        """Return all runs with any of the given statuses."""
        statuses = list(statuses)
        placeholders = ",".join("?" for _ in statuses)
        return self._all(
            f"SELECT * FROM runs WHERE status IN ({placeholders}) ORDER BY created_at, id",
            tuple(statuses),
        )

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        """Fetch a single run by id."""
        row = self.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return self._row_to_dict(row, "runs") if row else None

    def save_run(self, run: dict[str, Any]) -> dict[str, Any]:
        """Persist changes to a run row and return the refreshed run."""
        self.conn.execute(
            """
            UPDATE runs
            SET status = ?, context = ?, pause_reason = ?, failure_summary = ?,
                started_at = ?, finished_at = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE id = ?
            """,
            (
                run["status"],
                self._json(run.get("context") or {}),
                run.get("pause_reason"),
                run.get("failure_summary"),
                run.get("started_at"),
                run.get("finished_at"),
                run["id"],
            ),
        )
        self.conn.commit()
        return self.load_run(run["id"])

    # ------------------------------------------------------------------
    # Flow nodes (design-time graph)
    # ------------------------------------------------------------------

    def create_flow_node(
        self,
        flow_version_id: str,
        kind: str,
        ord: int,
        title: str,
        *,
        node_id: str | None = None,
        parent_node_id: str | None = None,
        binding_id: str | None = None,
        input_mapping: dict[str, Any] | None = None,
        output_mapping: dict[str, Any] | None = None,
        policy_refs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Insert a new node into a flow version. Only draft versions are editable."""
        node_id = node_id or f"n-{uuid.uuid4().hex[:12]}"
        self.conn.execute(
            """
            INSERT INTO flow_nodes (id, flow_version_id, kind, parent_node_id, ord, title, binding_id, input_mapping, output_mapping, policy_refs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                flow_version_id,
                kind,
                parent_node_id,
                ord,
                title,
                binding_id,
                self._json(input_mapping or {}),
                self._json(output_mapping or {}),
                self._json(policy_refs or {}),
            ),
        )
        self.conn.commit()
        return self.load_flow_node(node_id)

    def load_flow_node(self, node_id: str) -> dict[str, Any] | None:
        """Fetch a single flow node by id."""
        row = self.conn.execute("SELECT * FROM flow_nodes WHERE id = ?", (node_id,)).fetchone()
        return self._row_to_dict(row, "flow_nodes") if row else None

    def load_top_level_nodes(self, flow_version_id: str) -> list[dict[str, Any]]:
        """Return top-level nodes for a flow version, ordered by ord."""
        rows = self.conn.execute(
            "SELECT * FROM flow_nodes WHERE flow_version_id = ? AND parent_node_id IS NULL ORDER BY ord, id",
            (flow_version_id,),
        ).fetchall()
        return [self._row_to_dict(row, "flow_nodes") for row in rows]

    def load_child_nodes(self, parent_node_id: str) -> list[dict[str, Any]]:
        """Return children of a parent node, ordered by ord."""
        rows = self.conn.execute(
            "SELECT * FROM flow_nodes WHERE parent_node_id = ? ORDER BY ord, id",
            (parent_node_id,),
        ).fetchall()
        return [self._row_to_dict(row, "flow_nodes") for row in rows]

    # ------------------------------------------------------------------
    # Bindings
    # ------------------------------------------------------------------
    # A binding is the reusable configuration that tells a node how to talk to
    # an external system. The generic part is in integration_bindings; the
    # kind-specific part (URL, method, Hermes board, etc.) is joined from
    # api_binding_config or hermes_binding_config.

    def load_binding(self, binding_id: str) -> dict[str, Any] | None:
        """Fetch a binding plus its kind-specific configuration."""
        binding = self._one("SELECT * FROM integration_bindings WHERE id = ?", (binding_id,))
        if not binding:
            return None
        config_table = "api_binding_config" if binding["kind"] == "api" else "hermes_binding_config"
        config = self._one(f"SELECT * FROM {config_table} WHERE binding_id = ?", (binding_id,)) or {}
        binding.update(config)
        return binding

    # ------------------------------------------------------------------
    # Node states (runtime execution rows)
    # ------------------------------------------------------------------
    # Each node_state is one execution of a node in a run. For foreach loops,
    # a node_state is also created for each loop iteration, linked via
    # loop_iteration_id. The runner uses get_or_create_node_state() to lazily
    # materialize these rows as the flow is discovered.

    def get_or_create_node_state(self, run_id: str, node_id: str, loop_iteration_id: str | None) -> dict[str, Any]:
        """Find the node_state for this (run, node, iteration), or create a pending one."""
        if loop_iteration_id is None:
            row = self.conn.execute(
                "SELECT * FROM node_states WHERE run_id = ? AND node_id = ? AND loop_iteration_id IS NULL",
                (run_id, node_id),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM node_states WHERE run_id = ? AND node_id = ? AND loop_iteration_id = ?",
                (run_id, node_id, loop_iteration_id),
            ).fetchone()
        if row:
            return self._row_to_dict(row, "node_states")

        state_id = f"ns-{uuid.uuid4().hex[:12]}"
        binding = self.conn.execute("SELECT binding_id FROM flow_nodes WHERE id = ?", (node_id,)).fetchone()
        self.conn.execute(
            """
            INSERT INTO node_states (id, run_id, node_id, loop_iteration_id, status, binding_id)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (state_id, run_id, node_id, loop_iteration_id, binding[0] if binding else None),
        )
        self.conn.commit()
        return self.load_node_state(state_id)

    def load_node_state(self, node_state_id: str) -> dict[str, Any] | None:
        """Fetch a single node_state by id."""
        row = self.conn.execute("SELECT * FROM node_states WHERE id = ?", (node_state_id,)).fetchone()
        return self._row_to_dict(row, "node_states") if row else None

    def load_node_states_for_run(self, run_id: str) -> list[dict[str, Any]]:
        """Return all node_states for a run, oldest first."""
        rows = self.conn.execute(
            "SELECT * FROM node_states WHERE run_id = ? ORDER BY created_at, id",
            (run_id,),
        ).fetchall()
        return [self._row_to_dict(row, "node_states") for row in rows]

    def save_node_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """Persist all mutable fields on a node_state and return the refreshed row."""
        self.conn.execute(
            """
            UPDATE node_states
            SET status = ?, binding_id = ?, binding_snapshot = ?, external_ref = ?, native_state = ?,
                input = ?, raw_output = ?, output = ?, error_code = ?, error_message = ?, attempt = ?,
                started_at = ?, finished_at = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE id = ?
            """,
            (
                state["status"],
                state.get("binding_id"),
                self._json(state.get("binding_snapshot")),
                state.get("external_ref"),
                self._json(state.get("native_state")),
                self._json(state.get("input")),
                self._json(state.get("raw_output")),
                self._json(state.get("output")),
                state.get("error_code"),
                state.get("error_message"),
                state.get("attempt", 0),
                state.get("started_at"),
                state.get("finished_at"),
                state["id"],
            ),
        )
        self.conn.commit()
        return self.load_node_state(state["id"])

    # ------------------------------------------------------------------
    # Loop state and loop iterations (foreach internals)
    # ------------------------------------------------------------------
    # A foreach node has one loop_state per node_state, and one loop_iteration
    # per item. The loop_state tracks initialization/snapshot timing; the
    # iterations track the per-item child executions.

    def get_loop_state(self, node_state_id: str) -> dict[str, Any] | None:
        """Fetch the loop_state for a given foreach node_state, or None."""
        row = self.conn.execute("SELECT * FROM loop_states WHERE node_state_id = ?", (node_state_id,)).fetchone()
        return self._row_to_dict(row, "loop_states") if row else None

    def create_loop_state(self, node_state_id: str) -> dict[str, Any]:
        """Create a fresh loop_state for a foreach node_state."""
        loop_state_id = f"ls-{uuid.uuid4().hex[:12]}"
        self.conn.execute(
            "INSERT INTO loop_states (id, node_state_id) VALUES (?, ?)",
            (loop_state_id, node_state_id),
        )
        self.conn.commit()
        return self.get_loop_state(node_state_id)

    def save_loop_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """Persist timing/metadata on a loop_state."""
        self.conn.execute(
            """
            UPDATE loop_states
            SET initialized_at = ?, snapshot_completed_at = ?, snapshot_metadata = ?
            WHERE id = ?
            """,
            (
                state.get("initialized_at"),
                state.get("snapshot_completed_at"),
                self._json(state.get("snapshot_metadata")),
                state["id"],
            ),
        )
        self.conn.commit()
        return self.get_loop_state(state["node_state_id"])

    def create_loop_iteration(self, loop_state_id: str, iteration_key: str, position: int, item: dict[str, Any]) -> dict[str, Any]:
        """Create one iteration row for a foreach loop."""
        iteration_id = f"li-{uuid.uuid4().hex[:12]}"
        self.conn.execute(
            """
            INSERT INTO loop_iterations (id, loop_state_id, iteration_key, position, item, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (iteration_id, loop_state_id, iteration_key, position, self._json(item)),
        )
        self.conn.commit()
        return self.load_loop_iteration(iteration_id)

    def load_loop_iteration(self, iteration_id: str) -> dict[str, Any] | None:
        """Fetch a single loop iteration by id."""
        row = self.conn.execute("SELECT * FROM loop_iterations WHERE id = ?", (iteration_id,)).fetchone()
        return self._row_to_dict(row, "loop_iterations") if row else None

    def load_loop_iterations(self, loop_state_id: str) -> list[dict[str, Any]]:
        """Return all iterations for a loop_state, ordered by position."""
        rows = self.conn.execute(
            "SELECT * FROM loop_iterations WHERE loop_state_id = ? ORDER BY position, id",
            (loop_state_id,),
        ).fetchall()
        return [self._row_to_dict(row, "loop_iterations") for row in rows]

    def save_loop_iteration(self, iteration: dict[str, Any]) -> dict[str, Any]:
        """Persist status/output on a loop iteration."""
        self.conn.execute(
            """
            UPDATE loop_iterations
            SET status = ?, output = ?, error_summary = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE id = ?
            """,
            (iteration["status"], self._json(iteration.get("output")), iteration.get("error_summary"), iteration["id"]),
        )
        self.conn.commit()
        return self.load_loop_iteration(iteration["id"])

    # ------------------------------------------------------------------
    # Questions
    # ------------------------------------------------------------------
    # Questions are tied to a specific node_state, not a run. This matters when
    # a foreach loop produces multiple executions of the same node: each one
    # can have its own open question.

    def create_question(
        self,
        node_state_id: str,
        prompt: str,
        options: list[str] | None = None,
        *,
        hermes_task_id: str | None = None,
        hermes_run_id: str | None = None,
    ) -> dict[str, Any]:
        """Create an open question attached to a node_state."""
        question_id = f"q-{uuid.uuid4().hex[:12]}"
        self.conn.execute(
            """
            INSERT INTO questions (id, node_state_id, hermes_task_id, hermes_run_id, prompt, options, status)
            VALUES (?, ?, ?, ?, ?, ?, 'open')
            """,
            (question_id, node_state_id, hermes_task_id, hermes_run_id, prompt, self._json(options)),
        )
        self.conn.commit()
        return self.load_question(question_id)

    def load_open_questions(self, run_id: str) -> list[dict[str, Any]]:
        """Return all open questions across every node_state in a run."""
        rows = self.conn.execute(
            "SELECT q.* FROM questions q JOIN node_states s ON s.id = q.node_state_id WHERE s.run_id = ? AND q.status = 'open' ORDER BY q.created_at, q.id",
            (run_id,),
        ).fetchall()
        return [self._row_to_dict(row, "questions") for row in rows]

    def load_questions_for_node_state(self, node_state_id: str) -> list[dict[str, Any]]:
        """Return all questions (open or closed) for a node_state."""
        rows = self.conn.execute(
            "SELECT * FROM questions WHERE node_state_id = ? ORDER BY created_at, id",
            (node_state_id,),
        ).fetchall()
        return [self._row_to_dict(row, "questions") for row in rows]

    def load_open_questions_for_node_state(self, node_state_id: str) -> list[dict[str, Any]]:
        """Return only open questions for a node_state."""
        rows = self.conn.execute(
            "SELECT * FROM questions WHERE node_state_id = ? AND status = 'open' ORDER BY created_at, id",
            (node_state_id,),
        ).fetchall()
        return [self._row_to_dict(row, "questions") for row in rows]

    def load_question(self, question_id: str) -> dict[str, Any] | None:
        """Fetch a single question by id."""
        row = self.conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        return self._row_to_dict(row, "questions") if row else None

    def save_question(self, question: dict[str, Any]) -> dict[str, Any]:
        """Persist an answer and change status on a question."""
        self.conn.execute(
            """
            UPDATE questions
            SET hermes_task_id = ?, hermes_run_id = ?, prompt = ?, options = ?, answer = ?,
                status = ?, answered_at = ?, dismissed_at = ?
            WHERE id = ?
            """,
            (
                question.get("hermes_task_id"),
                question.get("hermes_run_id"),
                question["prompt"],
                self._json(question.get("options")),
                question.get("answer"),
                question["status"],
                question.get("answered_at"),
                question.get("dismissed_at"),
                question["id"],
            ),
        )
        self.conn.commit()
        return self.load_question(question["id"])

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def count_completed_iterations(self, run_id: str) -> int:
        """Count how many foreach iterations reached 'completed' status."""
        row = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM loop_iterations li
            JOIN loop_states ls ON ls.id = li.loop_state_id
            JOIN node_states ns ON ns.id = ls.node_state_id
            WHERE ns.run_id = ? AND li.status = 'completed'
            """,
            (run_id,),
        ).fetchone()
        return int(row[0])

    def count_duplicate_dispatches(self, run_id: str) -> int:
        """Diagnostic: count extra dispatch attempts beyond the first for each node_state.

        The state machine aims for at most one external dispatch per node_state.
        A non-zero number here indicates the duplicate-dispatch guard failed.
        """
        row = self.conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN attempt > 1 THEN attempt - 1 ELSE 0 END), 0) FROM node_states WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return int(row[0])
