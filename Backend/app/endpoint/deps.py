from __future__ import annotations

import os

from app.data.repository import TaskrRepository
from app.logic.integrations.api import ApiIntegration
from app.logic.integrations.fake import FakeApiCaller, FakeHermesService
from app.logic.integrations.hermes import HermesIntegration
from app.logic.integrations.stripe import StripeIntegration
from app.logic.runner import TaskrRunner

"""Shared dependencies for Taskr API endpoints.

This module owns the integration singletons and the lightweight factory
functions used by every endpoint module to obtain a runner or repository.
Centralising them here keeps endpoint modules free of wiring concerns and
ensures all endpoints share the same integration instances.

When the ``TASKR_USE_FAKE_INTEGRATIONS`` environment variable is set to ``"1"``
the runner is wired with :class:`FakeApiCaller` and
:class:`FakeHermesService` instead of the real HTTP clients. This is used by
the hackathon demo dev server so the full flow can be exercised without real
external services.
"""

_USE_FAKE = os.environ.get("TASKR_USE_FAKE_INTEGRATIONS") == "1"

if _USE_FAKE:
    _shared_api = FakeApiCaller(scrape_delay_polls=1)
    _shared_hermes = FakeHermesService(delay_polls=2)
else:
    _shared_api = ApiIntegration(allow_private=os.environ.get("TASKR_ALLOW_PRIVATE_URLS") == "1")
    _shared_hermes = HermesIntegration()
_shared_stripe = StripeIntegration()


def _get_runner() -> TaskrRunner:
    """Build a TaskrRunner with a fresh repository connection.

    Returns a runner configured with a new repository connection and the
    shared integration services. The connection is obtained from the
    repository's connection factory, which creates or reuses the configured
    database handle.

    The function also honours FastAPI ``app.dependency_overrides`` so tests can
    inject a runner backed by fake services without modifying endpoints.
    """
    # Local import to avoid circular imports: deps is imported while the FastAPI
    # app is still being assembled, but ``app`` is only needed during requests.
    from app.main.app import app

    if _get_runner in app.dependency_overrides:
        return app.dependency_overrides[_get_runner]()
    conn = TaskrRepository.get_connection()
    repo = TaskrRepository(conn)
    return TaskrRunner(repo, _shared_api, _shared_hermes, _shared_stripe)


def _get_repo() -> TaskrRepository:
    """Build a TaskrRepository with a fresh connection.

    This is a lightweight factory used by endpoints that only need data access
    and do not drive the run execution engine.
    """
    # Local import to avoid circular imports (see ``_get_runner`` above).
    from app.main.app import app

    if _get_repo in app.dependency_overrides:
        return app.dependency_overrides[_get_repo]()
    conn = TaskrRepository.get_connection()
    return TaskrRepository(conn)
