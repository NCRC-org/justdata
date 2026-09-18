"""BranchSight reuses cached analyses instead of regenerating them.

BranchSight stored results with store_cached_result but never called
get_cached_result, so every request re-ran the BigQuery queries and the Claude
narrative calls, and its Regenerate Report control had nothing to bypass.
"""

from unittest.mock import patch

import pytest

CACHED = {
    "job_id": "cached-job-1",
    "result_data": {"success": True},
    "cache_key": "branchsight_abc123",
}

PAYLOAD = {
    "selection_type": "county",
    "state_code": "24",
    "counties": "Montgomery County, Maryland",
    "years": "2020-2022",
}


@pytest.fixture
def branchsight_analyze(branchsight_client, sign_in):
    """Drive /analyze with the external services stubbed out."""
    def _run(user_type="staff", payload=None, cached=CACHED):
        sign_in(branchsight_client, user_type)
        with patch("justdata.apps.branchsight.blueprint.get_cached_result") as get_cached, \
             patch("justdata.apps.branchsight.blueprint.log_usage") as usage, \
             patch("justdata.apps.branchsight.blueprint.update_progress"), \
             patch("justdata.apps.branchsight.blueprint.create_progress_tracker"), \
             patch("justdata.apps.branchsight.blueprint.parse_web_parameters") as parse, \
             patch("threading.Thread") as thread:
            get_cached.return_value = cached
            parse.return_value = (["Montgomery County, Maryland"], [2020, 2021, 2022])
            resp = branchsight_client.post("/analyze", json=payload or PAYLOAD)
            return resp, get_cached, usage, thread
    return _run


def test_cache_hit_skips_reanalysis(branchsight_analyze):
    resp, get_cached, usage, thread = branchsight_analyze()

    assert get_cached.called
    assert resp.get_json() == {"success": True, "job_id": "cached-job-1", "cached": True}
    assert not thread.called, "a cache hit must not start an analysis thread"
    assert usage.call_args.kwargs["cache_hit"] is True


def test_cache_miss_runs_the_analysis(branchsight_analyze):
    resp, get_cached, _usage, thread = branchsight_analyze(cached=None)

    assert get_cached.called
    body = resp.get_json()
    assert body["success"] is True
    assert "cached" not in body
    assert thread.called, "a cache miss must start the analysis thread"


class TestForceRefresh:
    """Regenerate Report now has something to bypass, and is privileged-only."""

    def test_staff_bypasses_the_cache(self, branchsight_analyze):
        _resp, get_cached, _usage, thread = branchsight_analyze(
            user_type="staff", payload={**PAYLOAD, "force_refresh": True}
        )
        assert not get_cached.called
        assert thread.called

    def test_member_cannot_bypass_the_cache(self, branchsight_analyze):
        resp, get_cached, _usage, thread = branchsight_analyze(
            user_type="member", payload={**PAYLOAD, "force_refresh": True}
        )
        assert get_cached.called, "non-privileged force_refresh must still hit the cache"
        assert resp.get_json()["cached"] is True
        assert not thread.called


def test_branchsight_reads_the_cache_it_writes():
    """The import-level regression: it wrote to the cache but never read it."""
    from justdata.apps.branchsight import blueprint

    assert hasattr(blueprint, "get_cached_result")
    assert hasattr(blueprint, "store_cached_result")
    assert hasattr(blueprint, "log_usage")
