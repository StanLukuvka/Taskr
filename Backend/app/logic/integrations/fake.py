from __future__ import annotations

from typing import Any

from app.logic.integrations.result import IntegrationResult


class FakeApiCaller:
    """Synchronous fake API integration with a deterministic poll path."""

    def __init__(self) -> None:
        """Initialize fake polling counters."""
        self._poll_count: dict[str, int] = {}

    def start(
        self,
        binding_config: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
    ) -> IntegrationResult:
        """Initiate the fake API call and return a deterministic result."""
        if binding_config and binding_config.get("completion_mode") == "poll":
            ref = "fake-poll-123"
            self._poll_count[ref] = 0
            return IntegrationResult(status="running", external_ref=ref)

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
            if self._poll_count[external_ref] >= 2:
                return IntegrationResult(status="completed", external_ref=external_ref, output={"products": []})
            return IntegrationResult(status="running", external_ref=external_ref)
        raise NotImplementedError("FakeApiCaller.inspect is only implemented for fake poll refs")


class FakeHermesService:
    """Deterministic fake Hermes service that completes all tasks."""

    def __init__(self) -> None:
        """Initialize internal tracking for task IDs."""
        self._task_counter = 0

    def create_task(
        self,
        inputs: dict,
        binding_config: dict[str, Any] | None = None,
        *,
        run_id: str | None = None,
        node_state_id: str | None = None,
    ) -> IntegrationResult:
        """Create a fake research task that always completes."""
        self._task_counter += 1
        task_id = f"ht-{self._task_counter}"
        return IntegrationResult(status="completed", external_ref=task_id, output="done")

    def inspect_task(self, task_id: str) -> IntegrationResult:
        """Inspect a previously created task."""
        return IntegrationResult(status="completed", external_ref=task_id, output="done")
