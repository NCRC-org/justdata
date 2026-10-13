"""A failed cache write never stops the LendSight report from rendering.

The in-memory fallback holds the raw result, whose HHI tables have int year
keys beside 'Loan Purpose'; Flask's sorted JSON could not order them (500)."""

import numpy as np
import pandas as pd


def test_report_data_serves_a_raw_fallback_result(monkeypatch):
    from justdata.main.app import create_app
    import justdata.apps.lendsight.blueprint as bp
    monkeypatch.setattr(bp, "get_analysis_result_by_job_id", lambda job_id: None)
    bp._result_fallback["raw-1"] = {
        "report_data": {
            "market_concentration": [{"Loan Purpose": "All Loans", 2024: np.float64(304.87), 2025: None}],
            "market_concentration_state": [{"state": "Illinois", "rows": [{"Loan Purpose": "All Loans", "2024": 199.8}]}],
            "summary": pd.DataFrame([{"year": 2024, "total_loans": np.int64(10), "share": np.nan}]),
        },
        "metadata": {"counties": ["Cook County, Illinois"], "years": [2024]},
        "ai_insights": {},
    }
    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    for _ in range(2):  # a reload works too
        resp = c.get("/lendsight/report-data?job_id=raw-1")
        assert resp.status_code == 200, resp.get_data(as_text=True)
        data = resp.get_json()["data"]
        assert data["market_concentration"][0]["2024"] == 304.87
        assert data["summary"][0]["share"] is None
    bp._result_fallback.pop("raw-1", None)
