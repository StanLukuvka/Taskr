from __future__ import annotations

import time
from typing import Any

from app.logic.integrations.result import IntegrationResult


class FakeApiCaller:
    """Synchronous fake API integration with a deterministic poll path.

    The demo flow uses two fake API bindings distinguished by their
    ``url_template``:

    * ``https://fake.api/scrape`` — returns a product object (Pepsi Max).
    * ``https://fake.api/generate-image`` — returns a fake image URL after a
      short poll delay.
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

    def _make_ref(self, url: str) -> str:
        import uuid
        return f"fake-{url.replace('https://', '').replace('/', '-')}-{uuid.uuid4().hex[:6]}"

    def _running(self, ref: str) -> IntegrationResult:
        self._poll_count[ref] = 0
        return IntegrationResult(status="running", external_ref=ref)

    def _complete(self, url: str, ref: str) -> IntegrationResult:
        self._poll_count.pop(ref, None)
        if url == "https://fake.api/scrape":
            return IntegrationResult(
                status="completed",
                external_ref=ref,
                output={
                    "product": {
                        "id": "sku-pepsi-max",
                        "name": "Pepsi Max",
                        "brand": "Pepsi",
                    },
                    "cost_cents": 5,
                },
            )
        if url == "https://fake.api/generate-image":
            time.sleep(self._image_delay)
            return IntegrationResult(
                status="completed",
                external_ref=ref,
                output={
                    "image_url": "https://cdn.fake-images.io/pepsi-max-001.png",
                    "cost_cents": 20,
                },
            )
        return IntegrationResult(
            status="completed",
            external_ref=ref,
            output={"products": []},
        )

    def start(
        self,
        binding_config: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
    ) -> IntegrationResult:
        """Initiate the fake API call and return a deterministic result.

        Routing is based on ``binding_config["url_template"]``:

        * ``https://fake.api/scrape`` → returns ``running`` with a poll ref.
        * ``https://fake.api/generate-image`` → returns ``running`` with a poll ref.
        * Any other URL with ``completion_mode == "poll"`` → returns a running
          result with a poll ref (legacy path retained for tests).
        """
        if binding_config and binding_config.get("completion_mode") == "poll":
            ref = "fake-poll-123"
            self._poll_count[ref] = 0
            return IntegrationResult(status="running", external_ref=ref)

        url = (binding_config or {}).get("url_template", "")
        if url in ("https://fake.api/scrape", "https://fake.api/generate-image"):
            if self._scrape_delay_polls == 0:
                return self._complete(url, "")
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
                return self._complete(url, external_ref)
            return IntegrationResult(status="running", external_ref=external_ref)
        raise NotImplementedError("FakeApiCaller.inspect is only implemented for fake poll refs")


class FakeHermesService:
    """Deterministic fake Hermes service that completes all tasks.

    For the demo flow the fake service simulates an agent that searches the
    internet for product reviews and returns an image-generation prompt.
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

    def _task_output(self, inputs: dict[str, Any]) -> IntegrationResult:
        self._task_counter += 1
        task_id = f"ht-{self._task_counter}"
        self._poll_count[task_id] = 0
        return IntegrationResult(status="running", external_ref=task_id)

    def _complete(self, task_id: str) -> IntegrationResult:
        self._poll_count.pop(task_id, None)
        prompt = (
            "A bold, eye-catching advertisement poster for Pepsi Max, "
            "refreshing soda with condensation droplets on the can, "
            "vibrant blue and dark color palette, studio lighting, "
            "high detail, photorealistic"
        )
        return IntegrationResult(status="completed", external_ref=task_id, output={"prompt": prompt, "cost_cents": 10})

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
        """Create a fake research task."""
        if self._delay_polls > 0:
            return self._task_output(inputs)
        return self._complete(self._next_task_id())

    def inspect_task(self, task_id: str) -> IntegrationResult:
        """Inspect a previously created task."""
        self._poll_count[task_id] = self._poll_count.get(task_id, 0) + 1
        if self._poll_count[task_id] >= self._delay_polls:
            return self._complete(task_id)
        return IntegrationResult(status="running", external_ref=task_id)
