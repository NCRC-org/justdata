"""LendSight on the spec 04 standard (Part B checklist)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LS_JS = ROOT / "justdata" / "shared" / "web" / "static" / "js" / "lendsight"


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


def _page(client, path="/lendsight/"):
    resp = client.get(path)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_page_uses_the_standard_skeleton(client):
    html = _page(client)
    assert 'class="app-header"' in html and 'class="app-container app-workbench"' in html
    assert 'id="runBtn">Run analysis</button>' in html and 'form="lsForm"' in html
    # Steps in the fixed order; LendSight has no lender step.
    steps = [html.index(s) for s in ("</span>Geography</legend>", "</span>Years</legend>", "</span>Options</legend>")]
    assert steps == sorted(steps)
    assert "js/app_states.js" in html and "js/app_progress.js" in html


def test_header_and_sources_state_the_analysis_years(client):
    from justdata.apps.lendsight.core import analysis_years
    years = analysis_years()
    html = _page(client)
    assert f'<span class="app-vintage">HMDA {years[0]} to {years[-1]}</span>' in html
    assert f"{years[0]} to {years[-1]}, the five most recent years of HMDA data." in html
    assert "Correlation is not causation." in html
    assert "matched with confidence" not in html


def test_exports_listed_are_the_ones_lendsight_has(client):
    html = _page(client)
    assert 'data-export="xlsx"' in html and 'data-export="pdf"' in html
    assert 'data-export="csv"' not in html
    assert 'href="#methodsSection">Methods →</a>' in html


def test_legacy_scripts_are_gone(client):
    """jQuery, Select2, Font Awesome and the shared app.js (which loaded twice)
    are no longer part of the LendSight page."""
    html = _page(client)
    for gone in ("jquery", "select2", "font-awesome", "js/app.js", "fa-"):
        assert gone not in html.lower(), gone


def test_report_url_renders_the_same_page_with_the_job(client):
    html = _page(client, "/lendsight/report?job_id=abc-123")
    assert '"jobId": "abc-123"' in html or 'jobId: "abc-123"' in html
    assert 'id="lsReportTemplate"' in html


@pytest.mark.parametrize("job_id", ["<script>alert(1)</script>", "a b", "x" * 65])
def test_report_url_ignores_malformed_job_ids(client, job_id):
    html = _page(client, f"/lendsight/report?job_id={job_id}")
    assert "alert(1)" not in html
    assert "jobId: null" in html


def test_lendsight_js_modules_stay_small():
    files = sorted(LS_JS.glob("*.js"))
    assert [f.name for f in files] == ["ls_charts.js", "ls_page.js", "ls_report.js", "ls_tables.js"]
    for f in files:
        assert len(f.read_text().splitlines()) <= 500, f.name
    shared = ROOT / "justdata" / "shared" / "web" / "static" / "js"
    total = sum(f.stat().st_size for f in files) + sum(
        (shared / name).stat().st_size for name in ("app_states.js", "app_progress.js", "app_report.js"))
    assert total <= 250 * 1024  # spec 04 A5 budget for the app's own JS
