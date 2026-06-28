from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QuestionRequest:
    """Request for a blocking human question.

    Attributes:
        prompt: The question text to present to the user.
        options: Optional list of allowed answer choices. If ``None``, free-text
            answers may be accepted.
    """

    prompt: str
    options: list[str] | None = None


@dataclass
class IntegrationResult:
    """Outcome of a fake integration operation.

    Attributes:
        status: Lifecycle status of the operation. Expected values are
            ``running``, ``blocked``, ``completed``, or ``failed``.
        external_ref: Identifier assigned by the external system (if any).
        output: Payload produced by a successful completion.
        error_code: Machine-readable error code for failures.
        error_message: Human-readable error description for failures.
        question_request: Question to ask when the operation is ``blocked``.
        native_state: Raw state snapshot from the external system.
    """

    status: str
    external_ref: str | None = None
    output: Any = None
    error_code: str | None = None
    error_message: str | None = None
    question_request: QuestionRequest | None = None
    native_state: dict | None = None


class FakeApiCaller:
    """Synchronous fake API integration.

    Always returns a completed result immediately, so ``inspect`` is never used
    in this simplified implementation.
    """

    def start(
        self,
        binding_config: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
    ) -> IntegrationResult:
        """Initiate the fake API call and return a deterministic result.

        Args:
            binding_config: Optional binding config (ignored by the fake caller).
            input_data: Optional resolved input data (ignored by the fake caller).

        Returns:
            A completed result containing a small fixed product catalog.
        """
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
        """Check the status of an in-flight API call.

        Args:
            external_ref: Identifier returned by a previous ``start`` call.
            binding_config: Optional binding config (ignored by the fake caller).

        Raises:
            NotImplementedError: This fake caller never needs to poll because
                ``start`` always completes synchronously.
        """
        raise NotImplementedError("FakeApiCaller.inspect is never called for synchronous completions")


class FakeHermesService:
    """Deterministic fake Hermes service.

    - Products other than sku-fanta complete immediately.
    - sku-fanta blocks with a question on create, then completes on inspect after answer_question().
    """

    def __init__(self) -> None:
        """Initialize internal tracking for task IDs and answered questions."""
        self._task_counter = 0
        self._answered: set[str] = set()

    def create_task(self, inputs: dict) -> IntegrationResult:
        """Create a fake research task for the supplied product.

        The behavior is intentionally deterministic:

        * ``sku-fanta`` returns a ``blocked`` result asking for approval.
        * Every other product returns a ``completed`` result.

        Args:
            inputs: Dictionary that should contain a ``product`` entry with
                ``id`` and ``name`` keys.

        Returns:
            An :class:`IntegrationResult` describing the initial task state.
        """
        self._task_counter += 1
        task_id = f"ht-{self._task_counter}"

        product = inputs.get("product") or {}
        product_id = product.get("id")
        product_name = product.get("name", "product")

        if product_id == "sku-fanta":
            return IntegrationResult(
                status="blocked",
                external_ref=task_id,
                question_request=QuestionRequest(
                    prompt="Use paid search for Fanta?",
                ),
            )

        return IntegrationResult(
            status="completed",
            external_ref=task_id,
            output={"summary": f"researched {product_name}"},
        )

    def inspect_task(self, task_id: str) -> IntegrationResult:
        """Inspect a previously created task.

        Once the blocking question for ``sku-fanta`` has been answered via
        :meth:`answer_question`, inspection returns ``completed``. Otherwise,
        the task remains ``blocked`` with the same question.

        Args:
            task_id: External identifier returned by :meth:`create_task`.

        Returns:
            The current status of the task.
        """
        if task_id in self._answered:
            return IntegrationResult(
                status="completed",
                output={"summary": "researched Fanta Orange"},
            )
        return IntegrationResult(
            status="blocked",
            question_request=QuestionRequest(prompt="Use paid search for Fanta?"),
        )

    def answer_question(self, task_id: str, answer: str) -> None:
        """Record that the blocking question for a task has been answered.

        Args:
            task_id: External identifier of the task that was answered.
            answer: The answer provided (ignored in this fake implementation).
        """
        self._answered.add(task_id)
