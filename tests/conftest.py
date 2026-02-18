"""
Shared test fixtures for JustData test suite.

Provides mock clients and app factories so tests don't need
live BigQuery credentials, API keys, or running servers.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Environment fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    """Set safe defaults for all env vars so tests never hit real services."""
    defaults = {
        "SECRET_KEY": "test-secret-key-not-for-production",
        "GCP_PROJECT_ID": "test-project",
        "JUSTDATA_PROJECT_ID": "test-project",
        "CLAUDE_API_KEY": "sk-test-fake-key",
        "ANTHROPIC_API_KEY": "sk-test-fake-key",
        "OPENAI_API_KEY": "sk-test-fake-key",
        "CENSUS_API_KEY": "test-census-key",
        "FLASK_DEBUG": "false",
        "MAPBOX_ACCESS_TOKEN": "pk.test-token",
    }
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)


# ---------------------------------------------------------------------------
# BigQuery mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client that returns empty results by default.

    Usage:
        def test_something(mock_bigquery_client):
            mock_bigquery_client.query.return_value.result.return_value = [
                {"county": "Montgomery", "state": "MD"}
            ]
    """
    with patch("justdata.shared.utils.bigquery_client.get_bigquery_client") as mock:
        client = MagicMock()
        # Default: query returns empty iterator
        query_job = MagicMock()
        query_job.result.return_value = iter([])
        query_job.total_rows = 0
        client.query.return_value = query_job
        mock.return_value = client
        yield client


@pytest.fixture
def mock_bigquery_rows():
    """Helper to create mock BigQuery Row objects.

    Usage:
        def test_query(mock_bigquery_client, mock_bigquery_rows):
            rows = mock_bigquery_rows([
                {"name": "Bank A", "deposits": 1000000},
                {"name": "Bank B", "deposits": 2000000},
            ])
            mock_bigquery_client.query.return_value.result.return_value = rows
    """
    def _make_rows(data):
        rows = []
        for item in data:
            row = MagicMock()
            row.__getitem__ = lambda self, key, d=item: d[key]
            row.get = lambda key, default=None, d=item: d.get(key, default)
            row.keys.return_value = item.keys()
            row.values.return_value = item.values()
            rows.append(row)
        return iter(rows)
    return _make_rows


# ---------------------------------------------------------------------------
# AI provider mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ai_provider():
    """Mock the shared AI provider so tests never call Claude/OpenAI.

    Usage:
        def test_analysis(mock_ai_provider):
            mock_ai_provider.return_value = "AI-generated narrative text"
    """
    with patch("justdata.shared.analysis.ai_provider.ask_ai") as mock:
        mock.return_value = "Mock AI analysis response for testing."
        yield mock


# ---------------------------------------------------------------------------
# Flask app fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def branchsight_app():
    """Create a BranchSight Flask test app."""
    try:
        from justdata.apps.branchsight.app import app
        app.config["TESTING"] = True
        return app
    except Exception:
        pytest.skip("BranchSight app could not be imported")


@pytest.fixture
def branchsight_client(branchsight_app):
    """BranchSight test client."""
    return branchsight_app.test_client()


@pytest.fixture
def lendsight_app():
    """Create a LendSight Flask test app."""
    try:
        from justdata.apps.lendsight.app import app
        app.config["TESTING"] = True
        return app
    except Exception:
        pytest.skip("LendSight app could not be imported")


@pytest.fixture
def lendsight_client(lendsight_app):
    """LendSight test client."""
    return lendsight_app.test_client()


@pytest.fixture
def bizsight_app():
    """Create a BizSight Flask test app."""
    try:
        from justdata.apps.bizsight.app import app
        app.config["TESTING"] = True
        return app
    except Exception:
        pytest.skip("BizSight app could not be imported")


@pytest.fixture
def bizsight_client(bizsight_app):
    """BizSight test client."""
    return bizsight_app.test_client()


# ---------------------------------------------------------------------------
# Progress tracker mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_progress_tracker():
    """Mock progress tracker so tests don't need SSE infrastructure."""
    with patch("justdata.shared.utils.progress_tracker.update_progress") as mock_update, \
         patch("justdata.shared.utils.progress_tracker.get_progress") as mock_get, \
         patch("justdata.shared.utils.progress_tracker.create_progress_tracker") as mock_create:
        mock_get.return_value = {"status": "complete", "progress": 100}
        mock_create.return_value = "test-job-id"
        yield {
            "update": mock_update,
            "get": mock_get,
            "create": mock_create,
        }


# ---------------------------------------------------------------------------
# FDIC API mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_fdic_client():
    """Mock FDIC API client for branch/merger event tests."""
    with patch("justdata.apps.lenderprofile.services.fdic_client.FDICClient") as mock_cls:
        client = MagicMock()
        client.get_branch_events.return_value = []
        client.get_merger_events.return_value = []
        client.get_history.return_value = {"data": [], "totals": {"count": 0}}
        mock_cls.return_value = client
        yield client
