from __future__ import annotations

import os
from typing import Any

import httpx

from app.errors.integration import StripeConfigurationError


class StripeIntegration:
    """Thin Stripe test-mode client used by the budget demo."""

    def __init__(self, timeout: float = 10.0, secret_key: str | None = None) -> None:
        self.timeout = timeout
        self.secret_key = secret_key

    def _resolve_secret_key(self) -> str:
        key = self.secret_key or os.environ.get("STRIPE_SECRET_KEY")
        if not key:
            raise StripeConfigurationError("STRIPE_SECRET_KEY is required")
        if not key.startswith("sk_test_"):
            raise StripeConfigurationError("STRIPE_SECRET_KEY must be a Stripe test-mode key")
        return key

    def charge(
        self,
        amount_cents: int,
        description: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Create and confirm a Stripe test PaymentIntent."""
        try:
            secret_key = self._resolve_secret_key()
            response = httpx.post(
                "https://api.stripe.com/v1/payment_intents",
                auth=(secret_key, ""),
                headers={"Idempotency-Key": idempotency_key},
                data={
                    "amount": str(int(amount_cents)),
                    "currency": "usd",
                    "description": description,
                    "confirm": "true",
                    "payment_method": "pm_card_visa",
                    "automatic_payment_methods[enabled]": "true",
                    "automatic_payment_methods[allow_redirects]": "never",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except StripeConfigurationError as exc:
            return {"ok": False, "error": exc.detail if hasattr(exc, "detail") else str(exc)}
        except httpx.HTTPStatusError as exc:
            try:
                payload = exc.response.json()
                message = payload.get("error", {}).get("message") or exc.response.text
            except ValueError:
                message = exc.response.text
            return {"ok": False, "error": message}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        return {
            "ok": True,
            "amount_cents": int(amount_cents),
            "payment_intent_id": payload.get("id"),
        }
