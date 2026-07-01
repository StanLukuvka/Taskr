from __future__ import annotations

import json
import os
import time
from typing import Any

from app.logic.integrations.result import IntegrationResult


OUTPUT_DIR = "/agent/output"


class FakeApiCaller:
    """Synchronous fake API integration with a deterministic poll path.

    The demo flow uses file-based handoff in ``agent/output/<run_id>/``. Each
    node reads the previous node's file and writes its own output file.

    * ``https://fake.api/scrape`` — writes ``01_scrape.json``.
    * ``https://fake.api/generate-image`` — writes ``04_image.json`` after a short delay.
    * ``https://fake.api/budget-check`` — reads ``03_design.json`` and writes ``04_image.json``.
    """

    def __init__(self, *, image_delay: float = 2.0, scrape_delay_polls: int = 0) -> None:
        """Initialize fake polling counters and the image-generation delay.

        ``scrape_delay_polls`` controls how many ``inspect`` calls the fake
        scrape binding returns ``running`` before completing. The default ``0``
        keeps the historical synchronous-completion behavior for tests.
        """
        self._poll_count: dict[str, int] = {}
        self._image_delay = image_delay
        self._scrape_delay_polls = scrape_delay_polls

    def _run_dir(self, run_id: str | None) -> str:
        return os.path.join(OUTPUT_DIR, run_id or "unknown")

    def _read_file(self, run_id: str | None, filename: str) -> dict[str, Any]:
        path = os.path.join(self._run_dir(run_id), filename)
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            return json.load(f)

    def _write_file(self, run_id: str | None, filename: str, data: dict[str, Any]) -> None:
        run_dir = self._run_dir(run_id)
        os.makedirs(run_dir, exist_ok=True)
        path = os.path.join(run_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _make_ref(self, url: str) -> str:
        import uuid
        return f"fake-{url.replace('https://', '').replace('/', '-')}-{uuid.uuid4().hex[:6]}"

    def _running(self, ref: str) -> IntegrationResult:
        self._poll_count[ref] = 0
        return IntegrationResult(status="running", external_ref=ref)

    def _complete(
        self,
        url: str,
        ref: str,
        run_id: str | None,
        input_data: dict[str, Any] | None = None,
    ) -> IntegrationResult:
        self._poll_count.pop(ref, None)
        if url in ("https://fake.api/scrape", "https://fake.api/scrape-product"):
            output = {
                "product": {
                    "id": "sku-pepsi-max",
                    "name": "Pepsi Max",
                    "brand": "Pepsi",
                    "price_usd": 1.99,
                    "image_url": "https://cdn.fake-products.io/pepsi-max-can.png",
                },
                "cost_cents": 5,
            }
            self._write_file(run_id, "01_scrape.json", output)
            return IntegrationResult(status="completed", external_ref=ref, output=output, cost_cents=5)
        if url == "https://fake.api/generate-image":
            time.sleep(self._image_delay)
            design = self._read_file(run_id, "03_design.json")
            prompt = design.get("prompt")
            budget_cents = int((input_data or {}).get("budget_cents") or 0)
            spent_cents = int((input_data or {}).get("spent_cents") or 0)
            cost_cents = 20
            if budget_cents and spent_cents + cost_cents > budget_cents:
                return IntegrationResult(
                    status="failed",
                    external_ref=ref,
                    error_code="budget_exhausted",
                    error_message="run budget exhausted before image generation",
                    error_category="budget",
                    retryable=False,
                )
            output = {
                "image_url": "https://cdn.fake-images.io/pepsi-max-001.png",
                "prompt": prompt,
                "cost_cents": cost_cents,
            }
            self._write_file(run_id, "04_image.json", output)
            return IntegrationResult(status="completed", external_ref=ref, output=output, cost_cents=cost_cents)
        if url == "https://fake.api/budget-check":
            design = self._read_file(run_id, "03_design.json")
            budget_cents = int((input_data or {}).get("budget_cents") or 0)
            spent_cents = int((input_data or {}).get("spent_cents") or 0)
            cost_cents = 20
            if budget_cents and spent_cents + cost_cents > budget_cents:
                return IntegrationResult(
                    status="failed",
                    external_ref=ref,
                    error_code="budget_exhausted",
                    error_message="run budget exhausted before image generation",
                    error_category="budget",
                    retryable=False,
                )
            output = {"ok": True, "budget_cents": budget_cents, "spent_cents": spent_cents, "cost_cents": 0}
            self._write_file(run_id, "04_budget_check.json", output)
            return IntegrationResult(status="completed", external_ref=ref, output=output, cost_cents=0)
        return IntegrationResult(
            status="completed",
            external_ref=ref,
            output={"products": []},
        )

    def start(
        self,
        binding_config: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
        *,
        run_id: str | None = None,
    ) -> IntegrationResult:
        """Initiate the fake API call and return a deterministic result.

        Routing is based on ``binding_config["url_template"]``:

        * ``https://fake.api/scrape`` → completes immediately, writes ``01_scrape.json``.
        * ``https://fake.api/generate-image`` → completes immediately, writes ``04_image.json``.
        * ``https://fake.api/budget-check`` → completes immediately, writes ``04_budget_check.json``.
        * Any other URL with ``completion_mode == "poll"`` → returns a running
          result with a poll ref (legacy path retained for tests).
        """
        if binding_config and binding_config.get("completion_mode") == "poll":
            ref = "fake-poll-123"
            self._poll_count[ref] = 0
            return IntegrationResult(status="running", external_ref=ref)

        url = (binding_config or {}).get("url_template", "")
        if url in (
            "https://fake.api/scrape",
            "https://fake.api/scrape-product",
            "https://fake.api/generate-image",
            "https://fake.api/budget-check",
        ):
            if self._scrape_delay_polls == 0 or url not in ("https://fake.api/scrape", "https://fake.api/scrape-product"):
                return self._complete(url, "", run_id, input_data)
            ref = self._make_ref(url)
            return self._running(ref)

        # Default: return the legacy two-product list for backward compat
        return IntegrationResult(
            status="completed",
            output={
                "products": [
                    {"id": "sku-pepsi", "name": "Pepsi Max"},
                    {"id": "sku-fanta", "name": "Fanta Orange"},
                ]
            },
        )

    def inspect(
        self,
        external_ref: str,
        binding_config: dict[str, Any] | None = None,
    ) -> IntegrationResult:
        """Check the status of an in-flight fake API call."""
        if external_ref.startswith("fake-"):
            self._poll_count[external_ref] = self._poll_count.get(external_ref, 0) + 1
            url = (binding_config or {}).get("url_template", "")
            threshold = self._scrape_delay_polls if "scrape" in external_ref else 1
            if self._poll_count[external_ref] >= threshold:
                return self._complete(url, external_ref, None)
            return IntegrationResult(status="running", external_ref=external_ref)
        raise NotImplementedError("FakeApiCaller.inspect is only implemented for fake poll refs")


class FakeHermesService:
    """Deterministic fake Hermes service that completes all tasks.

    For the demo flow the fake service simulates agents that:
    * search the internet for customer review quotes (``b-hermes-opinions``),
    * design an image-generation prompt and layout (``b-hermes-design``).

    Each node reads and writes handoff files in ``agent/output/<run_id>/``.
    """

    def __init__(self, delay_polls: int = 0) -> None:
        """Initialize internal tracking for task IDs.

        ``delay_polls`` controls how many ``inspect_task`` calls return
        ``running`` before completing. Default ``0`` keeps the historical
        synchronous-completion behavior for tests.
        """
        self._task_counter = 0
        self._poll_count: dict[str, int] = {}
        self._delay_polls = delay_polls

    def _run_dir(self, run_id: str | None) -> str:
        return os.path.join(OUTPUT_DIR, run_id or "unknown")

    def _read_file(self, run_id: str | None, filename: str) -> dict[str, Any]:
        path = os.path.join(self._run_dir(run_id), filename)
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            return json.load(f)

    def _write_file(self, run_id: str | None, filename: str, data: dict[str, Any]) -> None:
        run_dir = self._run_dir(run_id)
        os.makedirs(run_dir, exist_ok=True)
        path = os.path.join(run_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _task_output(self, inputs: dict[str, Any]) -> IntegrationResult:
        self._task_counter += 1
        task_id = f"ht-{self._task_counter}"
        self._poll_count[task_id] = 0
        return IntegrationResult(status="running", external_ref=task_id)

    def _complete(
        self,
        task_id: str,
        binding_config: dict[str, Any] | None = None,
        *,
        run_id: str | None = None,
    ) -> IntegrationResult:
        self._poll_count.pop(task_id, None)
        binding_id = (binding_config or {}).get("binding_id") or (binding_config or {}).get("fk_binding_id")
        product = (self._read_file(run_id, "01_scrape.json") or {}).get("product", {"name": "Pepsi Max"})

        if binding_id == "b-hermes-opinions":
            output = {
                "quotes": [
                    f"'{product['name']} is the perfect zero-sugar pick-me-up.' – Jane D.",
                    f"'I love the crisp taste of {product['name']} over regular cola.' – Alex R.",
                    f"'{product['name']} is my go-to afternoon soda.' – Sam T.",
                ],
                "cost_cents": 10,
            }
            self._write_file(run_id, "02_opinions.json", output)
            return IntegrationResult(status="completed", external_ref=task_id, output=output, cost_cents=10)

        if binding_id == "b-hermes-design":
            quotes = (self._read_file(run_id, "02_opinions.json") or {}).get("quotes", [])
            quote_texts = [q.split('–')[0].strip("'\"") for q in quotes[:2]]
            prompt = (
                f"A vibrant infographic-style advertisement for {product['name']}, "
                f"featuring the product can, a bold headline, and customer quotes: "
                f"{'; '.join(quote_texts)}. "
                "Bright blue and silver palette, clean modern layout, studio lighting, high detail."
            )
            output = {
                "prompt": prompt,
                "layout": "vertical 1080x1920: headline top, product image center, quote cards bottom",
                "cost_cents": 10,
            }
            self._write_file(run_id, "03_design.json", output)
            return IntegrationResult(status="completed", external_ref=task_id, output=output, cost_cents=10)

        # Legacy fallback for the original soda flow
        prompt = (
            "A bold, eye-catching advertisement poster for Pepsi Max, "
            "refreshing soda with condensation droplets on the can, "
            "vibrant blue and dark color palette, studio lighting, "
            "high detail, photorealistic"
        )
        output = {"prompt": prompt, "cost_cents": 10}
        return IntegrationResult(status="completed", external_ref=task_id, output=output, cost_cents=10)

    def _next_task_id(self) -> str:
        self._task_counter += 1
        return f"ht-{self._task_counter}"

    def create_task(
        self,
        inputs: dict,
        binding_config: dict[str, Any] | None = None,
        *,
        run_id: str | None = None,
        node_state_id: str | None = None,
    ) -> IntegrationResult:
        """Create a fake research/design task."""
        if self._delay_polls > 0:
            return self._task_output(inputs)
        return self._complete(self._next_task_id(), binding_config, run_id=run_id)

    def inspect_task(self, task_id: str) -> IntegrationResult:
        """Inspect a previously created task."""
        self._poll_count[task_id] = self._poll_count.get(task_id, 0) + 1
        if self._poll_count[task_id] >= self._delay_polls:
            return self._complete(task_id)
        return IntegrationResult(status="running", external_ref=task_id)
