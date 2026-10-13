"""A failed cache write never stops the BizSight report from rendering."""

import numpy as np
import pandas as pd
import pytest

RESULT = {
    "success": True,
    "report_data": {"aggregate_data": pd.DataFrame([{"year": 2024, "num_under_100k": 5, "amt_under_100k": np.float64(12.5)}])},
    "county_summary_table": [{"Variable": "Total Loans", "2024": np.int64(5)}],
    "comparison_table": [], "top_lenders_table": [],
    "summary_table": {"total_loans": np.int64(5), "pct_loans_to_lmi_tracts": np.float64("nan")},
    "hhi_by_year": [{"year": 2024, "hhi_value": np.float64(517.37), "state_hhi_value": 377.37}],
    "metadata": {"county_name": "Cook County, Illinois", "years": [2024]},
}


@pytest.fixture
def client(monkeypatch):
    from justdata.main.app import create_app
    import justdata.apps.bizsight.blueprint as bp

    def failing_store(**kwargs):
        raise RuntimeError("BigQuery insert failed")
    monkeypatch.setattr(bp, "run_in_background", lambda work, **kw: work())
    monkeypatch.setattr(bp, "lookup_cached_analysis", lambda *a, **k: None)
    monkeypatch.setattr(bp, "record_completion", lambda *a, **k: None)
    monkeypatch.setattr(bp, "store_cached_result", failing_store)
    monkeypatch.setattr(bp, "get_analysis_result_by_job_id", lambda job_id: None)
    monkeypatch.setattr(bp, "run_analysis", lambda *a, **k: dict(RESULT))
    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return c


def test_report_loads_after_a_failed_cache_write(client):
    resp = client.post("/bizsight/analyze", json={
        "county_data": {"name": "Cook County, Illinois", "geoid5": "17031", "state_name": "Illinois"},
        "years": "2024"})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    job_id = resp.get_json()["job_id"]
    for _ in range(2):  # a reload works too
        data = client.get(f"/bizsight/report-data?job_id={job_id}")
        assert data.status_code == 200, data.get_data(as_text=True)
        body = data.get_json()
        assert body["success"] is True
        assert body["county_summary_table"][0]["2024"] == 5
        assert body["summary_table"]["pct_loans_to_lmi_tracts"] is None
        assert body["hhi_by_year"][0]["state_hhi_value"] == 377.37
        assert "report_data" not in body


def test_fallback_is_bounded():
    import justdata.apps.bizsight.blueprint as bp
    assert bp._FALLBACK_LIMIT == 20
