"""Taskr domain exceptions — re-exports for convenience.

Import from here instead of the per-layer modules:
    from app.errors import RunNotFoundError, FlowVersionNotFoundError
"""

from app.errors.base import TaskrError
from app.errors.data import FlowVersionNotFoundError, FlowVersionNotDraftError
from app.errors.flow import FlowSlugAlreadyInUseError
from app.errors.logic import (
    FlowNotFoundError,
    FlowNodeNotFoundError,
    MissingFlowForRunError,
    MissingNodeStateForQuestionError,
    MissingRunForQuestionError,
    NoActiveFlowVersionError,
    NodeStateNotFoundError,
    QuestionNotFoundError,
    RunAlreadyTerminalError,
    RunNotFoundError,
)

__all__ = [
    "TaskrError",
    # data
    "FlowVersionNotFoundError",
    "FlowVersionNotDraftError",
    # flow
    "FlowSlugAlreadyInUseError",
    # logic
    "FlowNotFoundError",
    "FlowNodeNotFoundError",
    "NoActiveFlowVersionError",
    "RunNotFoundError",
    "RunAlreadyTerminalError",
    "MissingFlowForRunError",
    "QuestionNotFoundError",
    "MissingNodeStateForQuestionError",
    "MissingRunForQuestionError",
    "NodeStateNotFoundError",
]
