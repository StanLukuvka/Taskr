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

    # --- Legacy 3-node soda flow (kept for existing runs/tests) ----------------
    conn.execute(
        "INSERT OR IGNORE INTO FLOW (flow_id, title, slug, description) VALUES (?, ?, ?, ?)",
        ("flow-soda", "Soda Comparison", "soda-comparison", "Scrape a product, research it, and generate an image"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO FLOW_VERSION (flow_version_id, fk_flow_id, version, status) VALUES (?, ?, ?, ?)",
        ("fv-1", "flow-soda", 1, "draft"),
    )

    legacy_bindings = [
        ("b-api-scrape", "api", "Scrape Product"),
        ("b-hermes-research", "hermes", "Research Product"),
        ("b-api-generate", "api", "Generate Image"),
    ]
    for binding in legacy_bindings:
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

    legacy_nodes = [
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
    for node in legacy_nodes:
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

    # --- New 3-node product image-prompt flow -------------------------------
    conn.execute(
        "INSERT OR IGNORE INTO FLOW (flow_id, title, slug, description) VALUES (?, ?, ?, ?)",
        ("flow-prompt", "Product Image Prompt", "product-image-prompt", "Move product input to Hermes input, generate an image prompt via Hermes, then confirm with a fake image API"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO FLOW_VERSION (flow_version_id, fk_flow_id, version, status) VALUES (?, ?, ?, ?)",
        ("fv-3", "flow-prompt", 1, "draft"),
    )

    prompt_bindings = [
        ("b-api-move-input-files", "api", "Move Input Files"),
        ("b-hermes-generate-image-prompt", "hermes", "Generate Image Prompt"),
        ("b-api-fake-image-success", "api", "Image API"),
    ]
    for binding in prompt_bindings:
        conn.execute(
            "INSERT OR IGNORE INTO INTEGRATION_BINDING (binding_id, kind, display_title) VALUES (?, ?, ?)",
            binding,
        )

    conn.execute(
        "INSERT OR IGNORE INTO API_BINDING_CONFIG (fk_binding_id, method, url_template, completion_mode) VALUES (?, ?, ?, ?)",
        ("b-api-move-input-files", "POST", "https://fake.api/move-input-files", "response"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO API_BINDING_CONFIG (fk_binding_id, method, url_template, completion_mode) VALUES (?, ?, ?, ?)",
        ("b-api-fake-image-success", "POST", "https://fake.api/generate-image", "response"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO HERMES_BINDING_CONFIG (fk_binding_id, board, task_title_template, task_body_template, skills) VALUES (?, ?, ?, ?, ?)",
        (
            "b-hermes-generate-image-prompt",
            "taskr",
            "Generate image prompt for product",
            "Read the product JSON file in /agent/output/hermes input, then produce an image-generation prompt. Write the prompt to /agent/output/hermes input/prompt.json and return JSON with a single key 'prompt'.",
            json.dumps(["file_read", "prompt_engineering"]),
        ),
    )

    prompt_nodes = [
        (
            "n-move-input-files", "fv-3", None, 0, "Move Input Files", "api", "b-api-move-input-files",
            json.dumps({}), json.dumps({"moved": "$result.moved"}), None, "stop",
        ),
        (
            "n-generate-image-prompt", "fv-3", None, 1, "Generate Image Prompt", "hermes", "b-hermes-generate-image-prompt",
            json.dumps({}),
            json.dumps({"prompt": "$result.prompt"}), None, "stop",
        ),
        (
            "n-fake-image-api", "fv-3", None, 2, "Image API", "api", "b-api-fake-image-success",
            json.dumps({"prompt": "$nodes.n-generate-image-prompt.output.prompt"}),
            json.dumps({"success": "$result.success"}), None, "stop",
        ),
    ]
    for node in prompt_nodes:
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
        WHERE flow_version_id = 'fv-3' AND status = 'draft'
        """
    )
    conn.commit()
