"""Cache lookup, privilege handling and usage logging."""

from unittest.mock import patch

import pytest
from flask import Flask

from justdata.backend.reports import (
    Caller,
    CachedAnalysis,
    identify_caller,
    lookup_cached_analysis,
    record_cache_hit,
    record_completion,
)

PARAMS = {"counties": ["Montgomery County, Maryland"], "years": [2022]}
RAW_HIT = {"job_id": "job-9", "cache_key": "key-9", "result_data": {"ok": True}}


@pytest.fixture
def app():
    a = Flask(__name__)
    a.secret_key = "test"
    return a


class TestIdentifyCaller:
    def test_reads_the_authenticated_user(self, app):
        with app.test_request_context():
            with patch("justdata.backend.reports.get_current_user") as user, \
                 patch("justdata.backend.reports.get_user_type", return_value="staff"):
                user.return_value = {"uid": "u1", "email": "someone@ncrc.org"}
                caller = identify_caller()

        assert caller == Caller(user_type="staff", user_id="u1",
                                user_email="someone@ncrc.org")

    def test_falls_back_to_the_session(self, app):
        """Some sign-in paths populate the session without get_current_user seeing it."""
        with app.test_request_context():
            from flask import session
            session["firebase_user"] = {"uid": "u2", "email": "other@ncrc.org"}
            with patch("justdata.backend.reports.get_current_user", return_value=None), \
                 patch("justdata.backend.reports.get_user_type", return_value="member"):
                caller = identify_caller()

        assert caller.user_id == "u2"
        assert caller.user_email == "other@ncrc.org"


class TestLookup:
    def _lookup(self, user_type, force, cached=RAW_HIT):
        with patch("justdata.backend.reports.get_cached_result") as get_cached:
            get_cached.return_value = cached
            result = lookup_cached_analysis(
                "branchsight", PARAMS,
                Caller(user_type=user_type),
                force_refresh_requested=force,
            )
            return result, get_cached

    def test_returns_the_cached_analysis(self):
        result, get_cached = self._lookup("member", force=False)
        assert get_cached.called
        assert result == CachedAnalysis(job_id="job-9", cache_key="key-9",
                                        result_data={"ok": True})

    def test_returns_none_on_a_miss(self):
        result, _ = self._lookup("member", force=False, cached=None)
        assert result is None

    @pytest.mark.parametrize("tier", ["staff", "senior_executive", "admin"])
    def test_privileged_force_refresh_bypasses(self, tier):
        result, get_cached = self._lookup(tier, force=True)
        assert result is None
        assert not get_cached.called, "bypass must not even query the cache"

    @pytest.mark.parametrize("tier", ["public_registered", "member", "member_premium",
                                      "non_member_org"])
    def test_unprivileged_force_refresh_is_ignored(self, tier):
        """Regenerating costs a full BigQuery scan plus AI calls, so it stays staff-gated."""
        result, get_cached = self._lookup(tier, force=True)
        assert get_cached.called
        assert result is not None

    def test_synthesises_a_cache_key_when_missing(self):
        result, _ = self._lookup("member", force=False,
                                 cached={"job_id": "j", "result_data": {}})
        assert result.cache_key.startswith("branchsight_")


class TestUsageLogging:
    CACHED = CachedAnalysis(job_id="job-9", cache_key="key-9", result_data={})

    def test_cache_hit_marks_progress_done_and_logs(self):
        with patch("justdata.backend.reports.log_usage") as usage, \
             patch("justdata.backend.reports.update_progress") as progress:
            record_cache_hit("branchsight", PARAMS, Caller(user_type="staff"),
                             self.CACHED, started_at=0.0, request_id="r1")

        assert progress.call_args.args[0] == "job-9"
        assert progress.call_args.args[1]["done"] is True
        kwargs = usage.call_args.kwargs
        assert kwargs["cache_hit"] is True
        assert kwargs["costs"]["total"] == 0.0

    def test_completion_logs_a_miss(self):
        with patch("justdata.backend.reports.log_usage") as usage:
            record_completion("branchsight", PARAMS, Caller(user_type="staff"),
                              "job-new", started_at=0.0, request_id="r2")

        assert usage.call_args.kwargs["cache_hit"] is False
        assert usage.call_args.kwargs["job_id"] == "job-new"

    def test_logging_failure_never_breaks_the_analysis(self):
        """Usage logging is telemetry; a BigQuery hiccup must not fail the report."""
        with patch("justdata.backend.reports.log_usage", side_effect=RuntimeError("bq down")):
            record_completion("branchsight", PARAMS, Caller(user_type="staff"),
                              "job-new", started_at=0.0)
