"""BranchSight reuses cached analyses instead of regenerating them.

BranchSight stored results with store_cached_result but never called
get_cached_result, so every request re-ran the BigQuery queries and the Claude
narrative calls, and its Regenerate Report control had nothing to bypass.

Patched at the backend's own dependencies rather than at the blueprint, so the
real cache-lookup and privilege logic in justdata.backend.reports runs.
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
    """Drive /analyze with external services stubbed but the backend real."""
    def _run(user_type="staff", payload=None, cached=CACHED):
        sign_in(branchsight_client, user_type)
        with patch("justdata.backend.reports.get_cached_result") as get_cached, \
             patch("justdata.backend.reports.log_usage") as usage, \
             patch("justdata.backend.reports.update_progress"), \
             patch("justdata.apps.branchsight.blueprint.create_progress_tracker"), \
             patch("justdata.apps.branchsight.blueprint.parse_web_parameters") as parse, \
             patch("justdata.apps.branchsight.blueprint.run_in_background") as started:
            get_cached.return_value = cached
            parse.return_value = (["Montgomery County, Maryland"], [2020, 2021, 2022])
            resp = branchsight_client.post("/analyze", json=payload or PAYLOAD)
            return resp, get_cached, usage, started
    return _run


def test_cache_hit_skips_reanalysis(branchsight_analyze):
    resp, get_cached, usage, started = branchsight_analyze()

    assert get_cached.called
    assert resp.get_json() == {"success": True, "job_id": "cached-job-1", "cached": True}
    assert not started.called, "a cache hit must not start an analysis job"
    assert usage.call_args.kwargs["cache_hit"] is True


def test_cache_miss_runs_the_analysis(branchsight_analyze):
    resp, get_cached, _usage, started = branchsight_analyze(cached=None)

    assert get_cached.called
    body = resp.get_json()
    assert body["success"] is True
    assert "cached" not in body
    assert started.called, "a cache miss must start the analysis job"


class TestForceRefresh:
    """Regenerate Report now has something to bypass, and is privileged-only."""

    def test_staff_bypasses_the_cache(self, branchsight_analyze):
        _resp, get_cached, _usage, started = branchsight_analyze(
            user_type="staff", payload={**PAYLOAD, "force_refresh": True}
        )
        assert not get_cached.called
        assert started.called

    def test_member_cannot_bypass_the_cache(self, branchsight_analyze):
        resp, get_cached, _usage, started = branchsight_analyze(
            user_type="member", payload={**PAYLOAD, "force_refresh": True}
        )
        assert get_cached.called, "non-privileged force_refresh must still hit the cache"
        assert resp.get_json()["cached"] is True
        assert not started.called


def test_blueprint_goes_through_the_shared_backend():
    """The plumbing lives in justdata.backend, not in the blueprint."""
    from justdata.apps.branchsight import blueprint

    for name in ("lookup_cached_analysis", "record_cache_hit", "record_completion",
                 "run_in_background", "sse_response", "identify_caller"):
        assert hasattr(blueprint, name), f"blueprint should use backend.{name}"

    # The duplicated plumbing it used to own is gone.
    for name in ("get_cached_result", "log_usage", "update_progress"):
        assert not hasattr(blueprint, name), f"{name} should come from the backend now"
