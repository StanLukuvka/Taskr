"""Logic-layer domain exceptions.

Raised by the runner when execution-state invariants are violated.
"""

from app.errors.base import TaskrError


# ── Flow & version errors ───────────────────────────────────

class FlowNotFoundError(TaskrError):
    status_code = 404
    detail = "Flow not found"


class NoActiveFlowVersionError(TaskrError):
    status_code = 404
    detail = "No active flow version for flow"


class FlowNodeNotFoundError(TaskrError):
    status_code = 404
    detail = "Flow node not found"


# ── Run errors ──────────────────────────────────────────────

class RunNotFoundError(TaskrError):
    status_code = 404
    detail = "Run not found"


class RunAlreadyTerminalError(TaskrError):
    status_code = 400
    detail = "Run is already in a terminal state"


class MissingFlowForRunError(TaskrError):
    status_code = 404
    detail = "Missing flow for run"


# ── Node state errors ───────────────────────────────────────

class NodeStateNotFoundError(TaskrError):
    status_code = 404
    detail = "Node state not found"


# ── Question errors ─────────────────────────────────────────

class QuestionNotFoundError(TaskrError):
    status_code = 404
    detail = "Question not found"


class MissingNodeStateForQuestionError(TaskrError):
    status_code = 404
    detail = "Missing node state for question"


class MissingRunForQuestionError(TaskrError):
    status_code = 404
    detail = "Missing run for question"


class NoOpenQuestionError(TaskrError):
    status_code = 400
    detail = "No open question for node state"


class RunRestartTargetError(TaskrError):
    """Raised when the restart_from target node is invalid."""

    status_code = 400
    detail = "Invalid restart target"


class NodeStateRetryError(TaskrError):
    """Raised when a node state cannot be retried."""

    status_code = 400
    detail = "Node state cannot be retried"
