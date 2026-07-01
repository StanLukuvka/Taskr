from __future__ import annotations

import json
import os
import time
from typing import Any

from app.logic.integrations.result import IntegrationResult


OUTPUT_DIR = "/agent/output"


class FakeApiCaller:
    """Synchronous fake API integration with deterministic routing.

    Demo flow (``product-image-prompt``) uses two fake API calls:

    * ``https://fake.api/move-input-files`` — copies ``agent/output/product input/*``
      to ``agent/output/hermes input/`` and returns ``{"moved": true}``.
    * ``https://fake.api/generate-image`` — accepts a prompt and returns
      ``{"success": true}`` (no image URL, just confirmation).

    Legacy paths are kept for the original ``flow-soda`` tests.
    """

    PRODUCT_INPUT_DIR = os.path.join(OUTPUT_DIR, "product input")
    HERMES_INPUT_DIR = os.path.join(OUTPUT_DIR, "hermes input")

    def __init__(self, *, image_delay: float = 0.0, scrape_delay_polls: int = 0) -> None:
        """Initialize fake polling counters and optional image delay.

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

    def _move_input_files(self, ref: str) -> IntegrationResult:
        """Copy all files from ``product input`` to ``hermes input``."""
        os.makedirs(self.HERMES_INPUT_DIR, exist_ok=True)
        moved: list[str] = []
        if os.path.isdir(self.PRODUCT_INPUT_DIR):
            for filename in os.listdir(self.PRODUCT_INPUT_DIR):
                src = os.path.join(self.PRODUCT_INPUT_DIR, filename)
                if os.path.isfile(src):
                    dst = os.path.join(self.HERMES_INPUT_DIR, filename)
                    with open(src, "rb") as f:
                        data = f.read()
                    with open(dst, "wb") as f:
                        f.write(data)
                    moved.append(filename)
        output = {"moved": True, "files": moved, "cost_cents": 1}
        return IntegrationResult(status="completed", external_ref=ref, output=output, cost_cents=1)

    def _generate_image_success(self, ref: str, input_data: dict[str, Any] | None) -> IntegrationResult:
        """Image provider: simply confirms the prompt was received."""
        if self._image_delay:
            time.sleep(self._image_delay)
        prompt = (input_data or {}).get("prompt")
        output = {"success": True, "prompt": prompt, "cost_cents": 5}
        return IntegrationResult(status="completed", external_ref=ref, output=output, cost_cents=5)

    def _complete(
        self,
        url: str,
        ref: str,
        run_id: str | None,
        input_data: dict[str, Any] | None = None,
    ) -> IntegrationResult:
        self._poll_count.pop(ref, None)
        if url == "https://fake.api/move-input-files":
            return self._move_input_files(ref)
        if url == "https://fake.api/generate-image":
            return self._generate_image_success(ref, input_data)
        # Legacy: scrape and product infographic paths
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

        * ``https://fake.api/move-input-files`` → copies files and returns ``moved``.
        * ``https://fake.api/generate-image`` → returns ``success: true``.
        * ``https://fake.api/scrape`` / ``scrape-product`` → legacy demo product.
        * Any other URL with ``completion_mode == "poll"`` → returns a running
          result with a poll ref (legacy path retained for tests).
        """
        if binding_config and binding_config.get("completion_mode") == "poll":
            ref = "fake-poll-123"
            self._poll_count[ref] = 0
            return IntegrationResult(status="running", external_ref=ref)

        url = (binding_config or {}).get("url_template", "")
        if url in (
            "https://fake.api/move-input-files",
            "https://fake.api/generate-image",
            "https://fake.api/scrape",
            "https://fake.api/scrape-product",
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

    For the demo flow the fake service simulates an agent that reads a product
    JSON file from ``agent/output/hermes input/`` and returns an image
    generation prompt. It also writes the prompt back to that directory so the
    next node can use it if needed.

    A legacy fallback prompt is kept for the original ``flow-soda`` tests.
    """

    HERMES_INPUT_DIR = os.path.join(OUTPUT_DIR, "hermes input")

    def __init__(self, delay_polls: int = 0) -> None:
        """Initialize internal tracking for task IDs.

        ``delay_polls`` controls how many ``inspect_task`` calls return
        ``running`` before completing. Default ``0`` keeps the historical
        synchronous-completion behavior for tests.
        """
        self._task_counter = 0
        self._poll_count: dict[str, int] = {}
        self._delay_polls = delay_polls
        self._task_context: dict[str, tuple[dict[str, Any] | None, str | None]] = {}

    def _read_hermes_input(self, filename: str) -> dict[str, Any]:
        path = os.path.join(self.HERMES_INPUT_DIR, filename)
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            return json.load(f)

    def _write_hermes_input(self, filename: str, data: dict[str, Any]) -> None:
        os.makedirs(self.HERMES_INPUT_DIR, exist_ok=True)
        path = os.path.join(self.HERMES_INPUT_DIR, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _task_output(self, inputs: dict[str, Any], binding_config: dict[str, Any] | None, run_id: str | None) -> IntegrationResult:
        self._task_counter += 1
        task_id = f"ht-{self._task_counter}"
        self._poll_count[task_id] = 0
        self._task_context[task_id] = (binding_config, run_id)
        return IntegrationResult(status="running", external_ref=task_id)

    def _generate_prompt(self) -> str:
        """Return the canned Hermes image-prompt output for the demo.

        This is a fixed string — the fake Hermes agent "inspects" the moved
        files and "returns" this prompt word for word.
        """
        return (
            "Create image\n"
            "Input summary - Product data: Pepsi Max 1.5L, NZ $1.99 (was $4.49, "
            "save $2.50), 1.33/L. No sugar, maximum taste, low calories. Ingredients "
            "include carbonated water, colour 150d, sweeteners 951/950, caffeine, "
            "phenylalanine present. Made in NZ from local and imported ingredients. - "
            "Image: studio hero shot of a 1.5L Pepsi Max bottle, black cap, dark cola, "
            "label with black/blue dot-matrix pattern, Pepsi globe, \"MAX TASTE ZERO "
            "SUGAR\" above the logo, \"PEPSI\" across the globe, \"MAX\" in red below, "
            "clean white background, bright commercial product lighting."
        )

    def _complete(
        self,
        task_id: str,
        binding_config: dict[str, Any] | None = None,
        *,
        run_id: str | None = None,
    ) -> IntegrationResult:
        self._poll_count.pop(task_id, None)
        binding_id = (binding_config or {}).get("binding_id") or (binding_config or {}).get("fk_binding_id")

        # Demo binding: generate an image prompt from the product file.
        if binding_id == "b-hermes-generate-image-prompt":
            prompt = self._generate_prompt()
            self._write_hermes_input("prompt.json", {"prompt": prompt})
            output = {"prompt": prompt, "cost_cents": 10}
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
            return self._task_output(inputs, binding_config, run_id)
        return self._complete(self._next_task_id(), binding_config, run_id=run_id)

    def inspect_task(self, task_id: str) -> IntegrationResult:
        """Inspect a previously created task."""
        self._poll_count[task_id] = self._poll_count.get(task_id, 0) + 1
        if self._poll_count[task_id] >= self._delay_polls:
            binding_config, run_id = self._task_context.pop(task_id, (None, None))
            return self._complete(task_id, binding_config, run_id=run_id)
        return IntegrationResult(status="running", external_ref=task_id)
