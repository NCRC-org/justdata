"""BizSight on the spec 04 standard (Part B checklist)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BS_JS = ROOT / "justdata" / "shared" / "web" / "static" / "js" / "bizsight"


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


def _page(client, path="/bizsight/"):
    resp = client.get(path)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_page_uses_the_standard_skeleton(client):
    html = _page(client)
    assert 'class="app-header"' in html and 'id="runBtn">Run analysis</button>' in html
    assert 'form="bsForm"' in html
    steps = [html.index(s) for s in ("</span>Geography</legend>", "</span>Years</legend>", "</span>Options</legend>")]
    assert steps == sorted(steps)
    for m in ("app_states.js", "app_progress.js", "app_report.js", "app_run.js", "bizsight/bs_page.js"):
        assert m in html, m


def test_header_and_years_come_from_config(client):
    from justdata.apps.bizsight.config import BizSightConfig
    y = BizSightConfig.SB_YEARS
    html = _page(client)
    assert f'<span class="app-vintage">CRA small business {y[0]} to {y[-1]}</span>' in html
    assert f"{y[0]} to {y[-1]}, the five most recent years of CRA small business data." in html
    assert "Correlation is not causation." in html and "matched with confidence" not in html


def test_toolbar_exports_and_methods_link(client):
    html = _page(client)
    assert 'data-export="xlsx"' in html and 'data-export="pdf"' in html and 'data-export="csv"' not in html
    assert 'href="#section6">Methods →</a>' in html


def test_no_placeholder_citation_and_no_legacy_scripts(client):
    html = _page(client)
    assert "[County Name]" not in html and '<span id="bsCitation"></span>' in html
    for gone in ("jquery", "select2", "font-awesome", "js/app.js", "fa-"):
        assert gone not in html.lower(), gone


def test_report_url_renders_the_page_with_the_job(client):
    assert 'jobId: "abc-123"' in _page(client, "/bizsight/report?job_id=abc-123")
    assert "jobId: null" in _page(client, "/bizsight/report?job_id=%3Cscript%3E")


def test_bizsight_js_modules_stay_small():
    for f in BS_JS.glob("*.js"):
        assert len(f.read_text().splitlines()) <= 500, f.name
