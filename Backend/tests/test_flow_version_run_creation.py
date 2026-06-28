"""Tests for creating runs from a specific flow version."""

from __future__ import annotations

import sqlite3

import pytest

from app.data.repository import TaskrRepository
from app.errors import FlowVersionNotFoundError, NoActiveFlowVersionError
from app.logic.integrations.fake import FakeApiCaller, FakeHermesService
from app.logic.runner import TaskrRunner


def _make_repo() -> TaskrRepository:
    """Create an in-memory repository with the canonical schema applied."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    from app.data.repository import SCHEMA_PATH
    conn.executescript(SCHEMA_PATH.read_text())
    return TaskrRepository(conn)


def _make_runner() -> TaskrRunner:
    """Create a runner backed by an in-memory repo with demo data seeded."""
    repo = _make_repo()
    repo.seed_data()
    api = FakeApiCaller()
    hermes = FakeHermesService()
    return TaskrRunner(repo, api, hermes)


class TestCreateRunFromFlowVersion:
    def test_create_run_from_flow_version_id(self):
        runner = _make_runner()
        repo = runner.repo
        flow = repo.load_flow_by_slug("soda-comparison")
        version = repo.load_active_flow_version(flow["flow_id"])

        run = runner.create_run(flow_version_id=version["flow_version_id"], context={"brand": "Coke"})

        assert run["fk_flow_version_id"] == version["flow_version_id"]
        assert run["fk_flow_id"] == version["fk_flow_id"]
        assert run["context"]["brand"] == "Coke"

    def test_create_run_from_flow_version_ignores_slug(self):
        runner = _make_runner()
        repo = runner.repo
        flow = repo.load_flow_by_slug("soda-comparison")
        version = repo.load_active_flow_version(flow["flow_id"])

        run = runner.create_run(
            flow_slug="does-not-matter",
            flow_version_id=version["flow_version_id"],
            context={},
        )

        assert run["fk_flow_version_id"] == version["flow_version_id"]

    def test_create_run_from_unknown_flow_version_raises(self):
        runner = _make_runner()

        with pytest.raises(FlowVersionNotFoundError):
            runner.create_run(flow_version_id="fv-does-not-exist")

    def test_create_run_from_slug_still_works(self):
        runner = _make_runner()
        repo = runner.repo

        run = runner.create_run("soda-comparison", {"brand": "Pepsi"})

        assert run["context"]["brand"] == "Pepsi"
        flow = repo.load_flow_by_slug("soda-comparison")
        assert run["fk_flow_id"] == flow["flow_id"]

    def test_create_run_default_slug_fallback(self):
        runner = _make_runner()
        repo = runner.repo

        run = runner.create_run()

        flow = repo.load_flow_by_slug("soda-comparison")
        assert run["fk_flow_id"] == flow["flow_id"]

    def test_create_run_from_slug_without_active_version_raises(self):
        runner = _make_runner()
        repo = runner.repo

        flow = repo.create_flow("No Version", "no-version", "no active version")
        with pytest.raises(NoActiveFlowVersionError):
            runner.create_run("no-version")
