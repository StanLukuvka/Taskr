from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.errors.integration import StripeConfigurationError
from app.logic.integrations.stripe import StripeIntegration
from app.logic.runner import TaskrRunner


def test_charge_posts_confirmed_test_mode_payment_intent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    captured: dict[str, Any] = {}

    def fake_post(*args: Any, **kwargs: Any) -> httpx.Response:
        captured["args"] = args
        captured["kwargs"] = kwargs
        request = httpx.Request("POST", args[0])
        return httpx.Response(200, json={"id": "pi_123"}, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)

    result = StripeIntegration(timeout=2.0).charge(
        amount_cents=50,
        description="Top-up for image generation",
        idempotency_key="run-1:node-1",
    )

    assert result == {"ok": True, "amount_cents": 50, "payment_intent_id": "pi_123"}
    assert captured["args"] == ("https://api.stripe.com/v1/payment_intents",)
    assert captured["kwargs"]["auth"] == ("sk_test_123", "")
    assert captured["kwargs"]["headers"] == {"Idempotency-Key": "run-1:node-1"}
    assert captured["kwargs"]["data"] == {
        "amount": "50",
        "currency": "usd",
        "description": "Top-up for image generation",
        "confirm": "true",
        "payment_method": "pm_card_visa",
        "automatic_payment_methods[enabled]": "true",
        "automatic_payment_methods[allow_redirects]": "never",
    }


def test_charge_requires_test_mode_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")

    result = StripeIntegration().charge(50, "Top-up", "idem-1")

    assert result == {"ok": False, "error": "STRIPE_SECRET_KEY must be a Stripe test-mode key"}
    with pytest.raises(StripeConfigurationError, match="test-mode"):
        StripeIntegration()._resolve_secret_key()


def test_charge_maps_http_failure_to_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")

    def fake_post(*args: Any, **kwargs: Any) -> httpx.Response:
        request = httpx.Request("POST", args[0])
        return httpx.Response(402, json={"error": {"message": "card declined"}}, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)

    result = StripeIntegration().charge(50, "Top-up", "idem-1")

    assert result == {"ok": False, "error": "card declined"}


def test_taskr_runner_accepts_injected_stripe_service() -> None:
    stripe = object()
    runner = TaskrRunner(repo=object(), api_caller=object(), hermes_service=object(), stripe_service=stripe)

    assert runner.stripe is stripe
