from __future__ import annotations

import os

from app.data.repository import TaskrRepository
from app.logic.integrations.api import ApiIntegration
from app.logic.integrations.hermes import HermesIntegration
from app.logic.integrations.stripe import StripeIntegration
from app.logic.runner import TaskrRunner

"""Shared dependencies for Taskr API endpoints.

This module owns the integration singletons and the lightweight factory
functions used by every endpoint module to obtain a runner or repository.
Centralising them here keeps endpoint modules free of wiring concerns and
ensures all endpoints share the same integration instances.
"""

_shared_api = ApiIntegration(allow_private=os.environ.get("TASKR_ALLOW_PRIVATE_URLS") == "1")
_shared_hermes = HermesIntegration()
_shared_stripe = StripeIntegration()
def _get_repo() -> TaskrRepository:
    """Build a TaskrRepository with a fresh connection.

    This is a lightweight factory used by endpoints that only need data access
    and do not drive the run execution engine.
    """
    conn = TaskrRepository.get_connection()
    return TaskrRepository(conn)
