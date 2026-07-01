"""Standalone demo data seeding for the Taskr backend.

This module creates a sample "Soda Comparison" flow so the MVP can be
exercised without a flow-design UI. The sample flow exercises the hackathon
demo narrative:

1. A fake API scrape node returns a product object (Pepsi Max).
2. A Hermes agent node searches the internet for Pepsi Max reviews and
   returns an image-generation prompt.
3. An image API node sleeps briefly then returns a fake image URL.

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
        ("flow-soda", "Soda Comparison", "soda-comparison", "Scrape a product, research it, and generate an image"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO FLOW_VERSION (flow_version_id, fk_flow_id, version, status) VALUES (?, ?, ?, ?)",
        ("fv-1", "flow-soda", 1, "draft"),
    )

    bindings = [
        ("b-api-scrape", "api", "Scrape Product"),
        ("b-hermes-research", "hermes", "Research Product"),
        ("b-api-generate", "api", "Generate Image"),
    ]
    for binding in bindings:
        conn.execute(
            "INSERT OR IGNORE INTO INTEGRATION_BINDING (binding_id, kind, display_title) VALUES (?, ?, ?)",
            binding,
        )

    conn.execute(
        "INSERT OR IGNORE INTO API_BINDING_CONFIG (fk_binding_id, method, url_template, completion_mode) VALUES (?, ?, ?, ?)",
        ("b-api-scrape", "GET", "https://fake.api/scrape", "response"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO API_BINDING_CONFIG (fk_binding_id, method, url_template, completion_mode) VALUES (?, ?, ?, ?)",
        ("b-api-generate", "POST", "https://fake.api/generate-image", "response"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO HERMES_BINDING_CONFIG (fk_binding_id, board, task_title_template, task_body_template) VALUES (?, ?, ?, ?)",
        (
            "b-hermes-research",
            "taskr",
            "Research {{product.name}}",
            "Search the internet for {{product.name}} reviews and return an image-generation prompt.",
        ),
    )

    flow_nodes = [
        (
            "n-scrape", "fv-1", None, 0, "Scrape Product", "api", "b-api-scrape",
            json.dumps({}), json.dumps({"product": "$result.product"}), None, "stop",
        ),
        (
            "n-research", "fv-1", None, 1, "Research Product", "hermes", "b-hermes-research",
            json.dumps({"product": "$nodes.n-scrape.output.product"}),
            json.dumps({"prompt": "$result.prompt"}), None, "stop",
        ),
        (
            "n-generate", "fv-1", None, 2, "Generate Image", "api", "b-api-generate",
            json.dumps({"prompt": "$nodes.n-research.output.prompt"}),
            json.dumps({"image_url": "$result.image_url"}), None, "stop",
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
