"""Taskr domain exceptions — re-exports for convenience.

Import from here instead of the per-layer modules:
    from app.errors import RunNotFoundError, FlowVersionNotFoundError
"""

from app.errors.base import TaskrError
from app.errors.binding import BindingInUseError, BindingKindMismatchError, BindingNotFoundError
from app.errors.data import CostAmountInvalidError, FlowVersionNotActiveError, FlowVersionNotDraftError, FlowVersionNotFoundError
from app.errors.flow import FlowSlugAlreadyInUseError
from app.errors.integration import (
    HermesConfigurationError,
    HermesIntegrationError,
    StripeConfigurationError,
    StripeIntegrationError,
)
from app.errors.logic import (
    FlowNotFoundError,
    FlowNodeNotFoundError,
    MissingFlowForRunError,
    NoActiveFlowVersionError,
    NodeStateNotFoundError,
    NodeStateRetryError,
    RunAlreadyTerminalError,
    RunNotFoundError,
    RunRestartTargetError,
)

__all__ = [
    "TaskrError",
    # binding
    "BindingNotFoundError",
    "BindingKindMismatchError",
    "BindingInUseError",
    # data
    "FlowVersionNotFoundError",
    "FlowVersionNotDraftError",
    "FlowVersionNotActiveError",
    "CostAmountInvalidError",
    # integration
    "HermesConfigurationError",
    "HermesIntegrationError",
    "StripeConfigurationError",
    "StripeIntegrationError",
    # flow
    "FlowSlugAlreadyInUseError",
    # logic
    "FlowNotFoundError",
    "FlowNodeNotFoundError",
    "NoActiveFlowVersionError",
    "RunNotFoundError",
    "RunAlreadyTerminalError",
    "RunRestartTargetError",
    "MissingFlowForRunError",
    "NodeStateNotFoundError",
    "NodeStateRetryError",
]
