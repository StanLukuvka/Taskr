"""Taskr domain exceptions — re-exports for convenience.

Import from here instead of the per-layer modules:
    from app.errors import RunNotFoundError, FlowVersionNotFoundError
"""

from app.errors.base import TaskrError
from app.errors.binding import BindingInUseError, BindingKindMismatchError, BindingNotFoundError
from app.errors.data import FlowVersionNotFoundError, FlowVersionNotDraftError
from app.errors.flow import FlowSlugAlreadyInUseError
from app.errors.logic import (
    FlowNotFoundError,
    FlowNodeNotFoundError,
    MissingFlowForRunError,
    MissingNodeStateForQuestionError,
    MissingRunForQuestionError,
    NoActiveFlowVersionError,
    NoOpenQuestionError,
    NodeStateNotFoundError,
    NodeStateRetryError,
    QuestionNotFoundError,
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
    # flow
    "FlowSlugAlreadyInUseError",
    # logic
    "FlowNotFoundError",
    "FlowNodeNotFoundError",
    "NoActiveFlowVersionError",
    "NoOpenQuestionError",
    "RunNotFoundError",
    "RunAlreadyTerminalError",
    "RunRestartTargetError",
    "MissingFlowForRunError",
    "QuestionNotFoundError",
    "MissingNodeStateForQuestionError",
    "MissingRunForQuestionError",
    "NodeStateNotFoundError",
    "NodeStateRetryError",
]
