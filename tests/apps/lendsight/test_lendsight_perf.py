"""LendSight records stage timings (spec 04 A5, Part B item 10)."""

import ast
import inspect


def test_queries_and_narrative_are_timed():
    import justdata.apps.lendsight.core as core
    tree = ast.parse(inspect.getsource(core.run_analysis))
    stages = {
        item.context_expr.args[0].value
        for node in ast.walk(tree) if isinstance(node, ast.With)
        for item in node.items
        if isinstance(item.context_expr, ast.Call) and getattr(item.context_expr.func, "id", "") == "timed"
    }
    assert {"bq:tiered_summary", "bq:mortgage_report", "narrative:table_discussions",
            "narrative:key_findings"} <= stages


def test_report_data_returns_perf(monkeypatch):
    from justdata.main.app import create_app
    import justdata.apps.lendsight.blueprint as bp
    stages = [{"stage": "bq:mortgage_report", "ms": 1234}]
    monkeypatch.setattr(bp, "get_analysis_result_by_job_id", lambda job_id: {
        "report_data": {"demographic_overview": []},
        "metadata": {"counties": ["Cook County, Illinois"], "years": [2021], "perf": stages, "perf_ref": "abcd1234"},
        "ai_insights": {},
    })
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    body = client.get("/lendsight/report-data?job_id=x").get_json()
    assert body["perf"] == stages and body["ref"] == "abcd1234"
