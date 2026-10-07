"""BranchSight stage timings, progress steps and error text (spec 04 A3, A5)."""

import ast
import inspect
import re

import pytest

import justdata.apps.branchsight.core as core


def _client(monkeypatch=None):
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return c


def test_queries_and_narratives_are_timed():
    tree = ast.parse(inspect.getsource(core.run_analysis))
    stages = {
        item.context_expr.args[0].value
        for node in ast.walk(tree) if isinstance(node, ast.With)
        for item in node.items
        if isinstance(item.context_expr, ast.Call) and getattr(item.context_expr.func, "id", "") == "timed"
    }
    assert {"bq:county_match", "bq:branch_report", "build_report", "narrative:key_findings",
            "narrative:table1", "narrative:table2", "narrative:hhi_trends"} <= stages


def test_progress_steps_are_ones_the_tracker_knows():
    from justdata.shared.utils.progress_tracker import ProgressTracker
    known = set(ProgressTracker("x").steps)
    used = set(re.findall(r"update_progress\('([a-z_]+)'", inspect.getsource(core)))
    assert used <= known, used - known


def test_core_never_marks_the_job_done():
    """Only the blueprint completes the job, after the result is stored."""
    assert "complete(" not in inspect.getsource(core)


class Tracker:
    def __getattr__(self, name):
        return lambda *a, **k: None


def test_query_failure_shows_no_exception_text(monkeypatch):
    monkeypatch.setattr(core, "find_exact_county_match", lambda c: [c])
    def boom(*a):
        raise RuntimeError("403 Access Denied: secret-table")
    monkeypatch.setattr(core, "execute_branch_query", boom)
    out = core.run_analysis("Lowndes County, Alabama", "all", "j", Tracker())
    assert out["success"] is False and "403" not in out["error"] and "secret" not in out["error"]
    assert isinstance(out["exception"], RuntimeError)


def test_one_query_covers_all_years(monkeypatch):
    calls = []
    monkeypatch.setattr(core, "find_exact_county_match", lambda c: [c])
    monkeypatch.setattr(core, "execute_branch_query", lambda sql, county, years: calls.append((county, years)) or [])
    out = core.run_analysis("Lowndes County, Alabama", "all", "j", Tracker())
    assert calls == [("Lowndes County, Alabama", core.SOD_YEARS)]
    assert out == {"success": False, "error": "No data found for the specified parameters"}


def test_sql_uses_query_parameters():
    sql = core.load_sql_template()
    assert sql.count("IN UNNEST(@years)") == 2 and sql.count("= @county") == 2


def test_report_data_returns_perf(monkeypatch):
    import justdata.apps.branchsight.blueprint as bp
    stages = [{"stage": "bq:branch_report", "ms": 640}]
    monkeypatch.setattr(bp, "get_analysis_result_by_job_id",
                        lambda job_id: {"report_data": {}, "metadata": {"perf": stages, "perf_ref": "beef1234"}})
    body = _client().get("/branchsight/report-data?job_id=x").get_json()
    assert body["perf"] == stages and body["ref"] == "beef1234"


def test_report_data_error_has_a_reference_not_exception_text(monkeypatch):
    import justdata.apps.branchsight.blueprint as bp
    def boom(job_id):
        raise RuntimeError("Traceback secret")
    monkeypatch.setattr(bp, "get_analysis_result_by_job_id", boom)
    resp = _client().get("/branchsight/report-data?job_id=x")
    assert resp.status_code == 500
    err = resp.get_json()["error"]
    assert "secret" not in err and "Reference:" in err
