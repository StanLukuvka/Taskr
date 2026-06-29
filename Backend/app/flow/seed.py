"""Standalone demo data seeding for the Taskr backend.

This module creates a sample "Soda Comparison" flow so the MVP can be
exercised without a flow-design UI. The sample flow exercises API calls,
a foreach loop, and Hermes task completion.

The function takes a TaskrRepository and populates it idempotently.
"""

from __future__ import annotations

import json

from app.data.repository import TaskrRepository


def seed_demo_data(repo: TaskrRepository) -> None:
    """Insert the demo flow, flow version, bindings, and nodes if they do not exist.

    Args:
        repo: A TaskrRepository instance with an active connection.
    """
    conn = repo.conn

    conn.execute(
        "INSERT OR IGNORE INTO FLOW (flow_id, title, slug, description) VALUES (?, ?, ?, ?)",
        ("flow-soda", "Soda Comparison", "soda-comparison", "Compare soda products"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO FLOW_VERSION (flow_version_id, fk_flow_id, version, status) VALUES (?, ?, ?, ?)",
        ("fv-1", "flow-soda", 1, "draft"),
    )

    bindings = [
        ("b-api-collect", "api", "Collect Products"),
        ("b-hermes-research", "hermes", "Research Product"),
        ("b-api-notify", "api", "Send Notification"),
    ]
    for binding in bindings:
        conn.execute(
            "INSERT OR IGNORE INTO INTEGRATION_BINDING (binding_id, kind, display_title) VALUES (?, ?, ?)",
            binding,
        )

    conn.execute(
        "INSERT OR IGNORE INTO API_BINDING_CONFIG (fk_binding_id, method, url_template, completion_mode) VALUES (?, ?, ?, ?)",
        ("b-api-collect", "POST", "https://fake.api/collect", "response"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO API_BINDING_CONFIG (fk_binding_id, method, url_template, completion_mode) VALUES (?, ?, ?, ?)",
        ("b-api-notify", "POST", "https://fake.api/notify", "response"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO HERMES_BINDING_CONFIG (fk_binding_id, board, task_title_template, task_body_template) VALUES (?, ?, ?, ?)",
        ("b-hermes-research", "taskr", "Research {{product.name}}", "Research {{product.name}} for soda comparison."),
    )

    flow_nodes = [
        (
            "n-collect", "fv-1", None, 0, "Collect Products", "api", "b-api-collect",
            json.dumps({}), json.dumps({"products": "$result.products"}), None, "stop",
        ),
        (
            "n-foreach", "fv-1", None, 1, "For Each Product", "foreach", None,
            json.dumps({}), json.dumps({}), "$nodes.n-collect.output.products", "stop",
        ),
        (
            "n-research", "fv-1", "n-foreach", 0, "Research Product", "hermes", "b-hermes-research",
            json.dumps({"product": "$item"}), json.dumps({"result": "$result.summary"}), None, "stop",
        ),
        (
            "n-notify", "fv-1", None, 2, "Send Notification", "api", "b-api-notify",
            json.dumps({}), json.dumps({}), None, "continue",
        ),
    ]
    for node in flow_nodes:
        node_id = node[0]
        exists = conn.execute("SELECT 1 FROM FLOW_NODE WHERE flow_node_id = ?", (node_id,)).fetchone()
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO FLOW_NODE (
                flow_node_id, fk_flow_version_id, fk_parent_flow_node_id, ord, title, kind, fk_binding_id,
                input_mapping, output_mapping, items_path, failure_policy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            node,
        )

    conn.execute(
        """
        UPDATE FLOW_VERSION
        SET status = 'active', activated_at = COALESCE(activated_at, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        WHERE flow_version_id = 'fv-1' AND status = 'draft'
        """
    )
    conn.commit()
