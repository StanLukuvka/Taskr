from __future__ import annotations

import os

from app.data.repository import TaskrRepository


DEFAULT_PROVIDER_URL = "http://127.0.0.1:9122"


def seed(provider_url: str | None = None, repo: TaskrRepository | None = None) -> None:
    provider_url = (provider_url or os.environ.get("TASKR_FAKE_IMAGE_PROVIDER_URL") or DEFAULT_PROVIDER_URL).rstrip("/")
    owns_connection = repo is None
    conn = TaskrRepository.get_connection() if owns_connection else repo.conn
    try:
        repo = repo or TaskrRepository(conn)
        flow = repo.load_flow_by_slug("stripe-budget-demo")
        if flow is None:
            flow = repo.create_flow(
                "Stripe Budget Demo",
                "stripe-budget-demo",
                "Check fake provider credits, top up through Stripe when low, then generate an image.",
            )

        version = repo.create_flow_version(flow["flow_id"])
        b_credits = repo.create_binding(
            "api",
            "Fake Image Provider Credits",
            config={
                "method": "GET",
                "url_template": f"{provider_url}/credits",
                "request_mode": "json",
                "completion_mode": "response",
            },
        )
        b_top_up = repo.create_binding(
            "api",
            "Stripe Top Up",
            config={
                "method": "POST",
                "url_template": "stripe://top-up",
                "request_mode": "json",
                "completion_mode": "response",
            },
        )
        b_provider_top_up = repo.create_binding(
            "api",
            "Fake Image Provider Top Up",
            config={
                "method": "POST",
                "url_template": f"{provider_url}/topup",
                "request_mode": "json",
                "completion_mode": "response",
            },
        )
        b_generate = repo.create_binding(
            "api",
            "Fake Image Provider Generate",
            config={
                "method": "POST",
                "url_template": f"{provider_url}/generate",
                "request_mode": "json",
                "completion_mode": "response",
            },
        )

        repo.create_flow_node(
            version["flow_version_id"],
            "api",
            0,
            "Check Credits",
            node_id="check_credits",
            binding_id=b_credits["binding_id"],
            input_mapping={},
            output_mapping={"balance": "$result.json.balance"},
        )
        repo.create_flow_node(
            version["flow_version_id"],
            "api",
            1,
            "Stripe Top Up If Low",
            node_id="top_up_if_low",
            binding_id=b_top_up["binding_id"],
            input_mapping={
                "amount_cents": 50,
                "description": "Top-up for image generation",
                "balance": "$nodes.check_credits.output.balance",
                "budget_cents": "$scope.budget_cents",
            },
            output_mapping={
                "ok": "$result.ok",
                "charged": "$result.charged",
                "balance": "$result.balance",
                "cost_cents": "$result.cost_cents",
            },
        )
        repo.create_flow_node(
            version["flow_version_id"],
            "api",
            2,
            "Apply Provider Credits",
            node_id="apply_provider_credits",
            binding_id=b_provider_top_up["binding_id"],
            input_mapping={"amount": "$nodes.top_up_if_low.output.cost_cents"},
            output_mapping={"balance": "$result.json.balance"},
        )
        repo.create_flow_node(
            version["flow_version_id"],
            "api",
            3,
            "Generate Image",
            node_id="generate_image",
            binding_id=b_generate["binding_id"],
            input_mapping={},
            output_mapping={
                "image_url": "$result.json.image_url",
                "balance": "$result.json.balance",
                "credits_deducted": "$result.json.credits_deducted",
            },
        )

        repo.publish_flow_version(version["flow_version_id"])
        print(f"Seeded stripe-budget-demo flow using {provider_url}.")
    finally:
        if owns_connection:
            conn.close()


if __name__ == "__main__":
    seed()
