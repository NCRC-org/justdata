"""BizSight records stage timings (spec 04 A5, Part B item 10)."""

import ast
import inspect


def test_queries_and_narrative_are_timed():
    import justdata.apps.bizsight.core as core
    tree = ast.parse(inspect.getsource(core.run_analysis))
    stages = {
        item.context_expr.args[0].value
        for node in ast.walk(tree) if isinstance(node, ast.With)
        for item in node.items
        if isinstance(item.context_expr, ast.Call) and getattr(item.context_expr.func, "id", "") == "timed"
    }
    assert {"bq:aggregate", "bq:disclosure_latest", "bq:disclosure_all_years",
            "bq:county_summary", "narrative:all_sections"} <= stages


def test_progress_steps_are_ones_the_tracker_knows():
    """Unknown step names are silently dropped by the shared tracker."""
    import re
    import justdata.apps.bizsight.core as core
    from justdata.shared.utils.progress_tracker import ProgressTracker
    known = set(ProgressTracker("x").steps) | {"error"}
    used = set(re.findall(r"update_progress\('([a-z_]+)'", inspect.getsource(core)))
    assert used <= known, used - known


def test_report_data_returns_perf(monkeypatch):
    from justdata.main.app import create_app
    import justdata.apps.bizsight.blueprint as bp
    stages = [{"stage": "bq:aggregate", "ms": 812}]
    monkeypatch.setattr(bp, "get_analysis_result_by_job_id",
                        lambda job_id: {"metadata": {"perf": stages, "perf_ref": "beef1234"}})
    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    body = c.get("/bizsight/report-data?job_id=x").get_json()
    assert body["perf"] == stages and body["ref"] == "beef1234"
