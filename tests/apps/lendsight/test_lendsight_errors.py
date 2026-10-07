"""LendSight never shows raw exception text (spec 04 A3); users get a short
message and a reference id, and the traceback goes to the server log."""

import re
import uuid

import pytest

SECRET = "boom: table justdata-ncrc.private.thing not found"
REF = re.compile(r"Reference: [0-9a-f]{8}$")


@pytest.fixture
def client(monkeypatch):
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return c


def _boom(*a, **k):
    raise RuntimeError(SECRET)


@pytest.mark.parametrize("path", ["/lendsight/report-data?job_id=x", "/lendsight/download?job_id=x&format=pdf"])
def test_report_routes_hide_exception_text(client, monkeypatch, path):
    import justdata.apps.lendsight.blueprint as bp
    monkeypatch.setattr(bp, "get_analysis_result_by_job_id", _boom)
    resp = client.get(path)
    body = resp.get_data(as_text=True)
    assert resp.status_code == 500
    assert SECRET not in body and "RuntimeError" not in body
    assert REF.search(resp.get_json()["error"])


def test_failed_run_reports_generic_error_with_reference(client, monkeypatch):
    import justdata.apps.lendsight.blueprint as bp
    from justdata.shared.utils.progress_tracker import get_progress

    monkeypatch.setattr(bp, "run_in_background", lambda work, **kw: work())
    monkeypatch.setattr(bp, "lookup_cached_analysis", lambda *a, **k: None)
    monkeypatch.setattr(bp, "record_completion", lambda *a, **k: None)
    monkeypatch.setattr(bp, "new_job_id", lambda: f"test-{uuid.uuid4().hex}")
    monkeypatch.setattr(bp, "run_analysis", _boom)
    resp = client.post("/lendsight/analyze", json={
        "selection_type": "county", "state_code": "17", "loan_purpose": ["purchase"],
        "counties": "Cook County, Illinois",
        "counties_data": [{"name": "Cook County, Illinois", "geoid5": "17031",
                           "state_fips": "17", "county_fips": "031"}],
    })
    assert resp.status_code == 200
    progress = get_progress(resp.get_json()["job_id"])
    assert progress["done"] is True
    assert SECRET not in progress["error"]
    assert progress["error"].startswith("We couldn't complete this analysis.")
    assert REF.search(progress["error"])


def test_exception_inside_run_analysis_is_not_shown(client, monkeypatch):
    """run_analysis catches its own exceptions; their text must not reach the
    progress stream either (it used to return "Analysis failed: <exception>")."""
    import justdata.apps.lendsight.blueprint as bp
    import justdata.apps.lendsight.core as core
    from justdata.shared.utils.progress_tracker import get_progress

    monkeypatch.setattr(bp, "run_in_background", lambda work, **kw: work())
    monkeypatch.setattr(bp, "lookup_cached_analysis", lambda *a, **k: None)
    monkeypatch.setattr(bp, "record_completion", lambda *a, **k: None)
    monkeypatch.setattr(bp, "new_job_id", lambda: f"test-{uuid.uuid4().hex}")
    monkeypatch.setattr(core, "parse_web_parameters", _boom)
    monkeypatch.setattr(bp, "parse_web_parameters", lambda *a, **k: (["Cook County, Illinois"], [2025]))
    monkeypatch.setattr(bp, "run_analysis", core.run_analysis)
    resp = client.post("/lendsight/analyze", json={
        "selection_type": "county", "state_code": "17", "loan_purpose": ["purchase"],
        "counties": "Cook County, Illinois",
    })
    progress = get_progress(resp.get_json()["job_id"])
    assert progress["done"] is True
    assert SECRET not in progress["error"]
    assert progress["error"].startswith("We couldn't complete this analysis.")
    assert REF.search(progress["error"])
