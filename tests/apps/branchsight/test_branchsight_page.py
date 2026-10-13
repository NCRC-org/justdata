"""BranchSight on the spec 04 standard (Part B checklist)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BR_JS = ROOT / "justdata" / "shared" / "web" / "static" / "js" / "branchsight"


@pytest.fixture
def client():
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return c


def _page(client, path="/branchsight/"):
    resp = client.get(path)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_page_uses_the_standard_skeleton(client):
    html = _page(client)
    assert 'class="app-header"' in html and 'id="runBtn">Run analysis</button>' in html
    assert 'form="brForm"' in html
    steps = [html.index(s) for s in ("</span>Geography</legend>", "</span>Years</legend>", "</span>Options</legend>")]
    assert steps == sorted(steps)
    for m in ("app_states.js", "app_progress.js", "app_report.js", "app_run.js", "branchsight/br_page.js"):
        assert m in html, m


def test_header_and_years_come_from_config(client):
    from justdata.apps.branchsight.config import SOD_YEARS as y
    html = _page(client)
    assert f'<span class="app-vintage">FDIC Summary of Deposits {y[0]} to {y[-1]}</span>' in html
    assert f"{y[0]} to {y[-1]}, the five most recent years of FDIC Summary of Deposits data." in html
    assert "matched with confidence" not in html


def test_toolbar_exports_and_methods_link(client):
    html = _page(client)
    assert 'data-export="xlsx"' in html and 'data-export="pdf"' in html and 'data-export="csv"' not in html
    assert 'href="#methodsSection">Methods →</a>' in html


def test_no_legacy_scripts_placeholders_or_key_messages(client):
    html = _page(client)
    for gone in ("jquery", "select2", "font-awesome", "js/app.js", "fa-",
                 "lorem", "refresh the page", "claude_api_key"):
        assert gone not in html.lower(), gone
    js = (BR_JS / "br_report.js").read_text().lower()
    assert "refresh the page" not in js and "api key" not in js


def test_report_url_renders_the_page_with_the_job(client):
    assert 'jobId: "abc-123"' in _page(client, "/branchsight/report?job_id=abc-123")
    assert "jobId: null" in _page(client, "/branchsight/report?job_id=%3Cscript%3E")


def test_analyze_ignores_page_years(client, monkeypatch):
    import justdata.apps.branchsight.blueprint as bp
    from justdata.apps.branchsight.config import SOD_YEARS
    seen = {}

    def fake_lookup(app, params, caller, force_refresh_requested=False):
        seen.update(params)
        return None
    monkeypatch.setattr(bp, "lookup_cached_analysis", fake_lookup)
    monkeypatch.setattr(bp, "run_in_background", lambda fn, job_id=None: None)
    resp = client.post("/branchsight/analyze", json={
        "selection_type": "county", "state_code": "Alabama",
        "counties": "Lowndes County, Alabama", "years": "1999"})
    assert resp.get_json()["success"] is True
    assert seen["years"] == SOD_YEARS


def test_branchsight_js_modules_stay_small():
    for f in BR_JS.glob("*.js"):
        assert len(f.read_text().splitlines()) <= 500, f.name



def test_geography_context_comes_from_the_server():
    """The Census API refuses keyless browser calls; the page asks the server."""
    js = (BR_JS / "br_report.js").read_text()
    assert "api.census.gov" not in js and "/geography-context/" in js
