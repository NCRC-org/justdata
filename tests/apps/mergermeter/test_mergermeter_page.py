"""MergerMeter on the analysis-app standard (spec 04 Part B)."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
JS = ROOT / "justdata" / "shared" / "web" / "static" / "js" / "mergermeter"
TEMPLATES = ROOT / "justdata" / "apps" / "mergermeter" / "templates"


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


def _page(client, path="/mergermeter/"):
    resp = client.get(path)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_standard_skeleton_and_step_order(client):
    html = _page(client)
    assert 'class="app-header"' in html and 'id="runBtn">Run analysis</button>' in html and 'form="mmForm"' in html
    steps = [html.index(s) for s in ("</span>Geography</legend>", "</span>Acquirer and target</legend>",
                                     "</span>Years</legend>", "</span>Options</legend>")]
    assert steps == sorted(steps)
    for m in ("app_states.js", "app_progress.js", "app_report.js", "app_run.js",
              "mergermeter/mm_report.js", "mergermeter/mm_banks.js", "mergermeter/mm_areas.js", "mergermeter/mm_page.js"):
        assert m in html, m
    assert "jquery" not in html.lower() and "select2" not in html.lower()


def test_controls_keep_the_former_values(client):
    html = _page(client)
    # HMDA filters: the former page's options and defaults
    for name, checked in (("action_taken", ["1"]), ("occupancy_type", ["1"]), ("total_units", ["1", "2", "3", "4"]),
                          ("construction_method", ["1", "2"]), ("not_reverse", ["1"])):
        block = html[html.index(f'id="{name}"'):]
        block = block[:block.index("</fieldset>")]
        assert re.findall(r'value="(\d)" checked', block) == checked, name
    assert '<option value="volume_50_200" selected>' in html
    assert '<option value="" selected>All loan purposes</option>' in html
    assert '<option value="31,32">' in html and '<option value="2,4">' in html
    assert re.search(r'id="sb_start_year">.*?<option value="2023" selected>', html, re.S)
    assert re.search(r'id="sb_end_year">.*?<option value="2024" selected>', html, re.S)
    # the CSV template link carries the blueprint prefix (it 404ed without it)
    assert 'href="/mergermeter/api/download-assessment-area-template"' in html


def test_report_url_renders_the_page_with_the_job(client):
    html = _page(client, "/mergermeter/report?job_id=job_abc-123")
    assert '"job_abc-123"' in html
    assert '"bad id!"' not in _page(client, "/mergermeter/report?job_id=bad id!")


def test_report_data_is_a_readiness_check(client, monkeypatch, tmp_path):
    import justdata.apps.mergermeter.blueprint as bp
    import justdata.apps.mergermeter.mergermeter_ops as ops
    monkeypatch.setattr(ops, "ensure_local_excel", lambda job_id: tmp_path / "x.xlsx" if job_id == "ready" else None)
    monkeypatch.setattr(bp, "download_json", lambda path: {"acquirer_name": "Bank A", "target_name": "Bank B",
                                                           "hmda_years": [2020, 2024], "acquirer_lei": "X" * 20,
                                                           "perf": [{"stage": "step:querying_hmda_data_for_bank_a", "ms": 900}],
                                                           "perf_ref": "abcd1234"})
    ok = client.get("/mergermeter/report-data?job_id=ready").get_json()
    assert ok == {"success": True, "job_id": "ready",
                  "metadata": {"acquirer_name": "Bank A", "target_name": "Bank B", "hmda_years": [2020, 2024]},
                  "perf": [{"stage": "step:querying_hmda_data_for_bank_a", "ms": 900}], "ref": "abcd1234"}
    monkeypatch.setattr(bp, "get_progress", lambda job_id: {"done": False})
    assert client.get("/mergermeter/report-data?job_id=running").status_code == 202
    monkeypatch.setattr(bp, "get_progress", lambda job_id: {"done": True, "error": "x"})
    assert client.get("/mergermeter/report-data?job_id=gone").status_code == 404
    assert client.get("/mergermeter/report-data?job_id=bad id").status_code == 400


def test_body_posts_the_former_fields():
    """mm_page.js sends exactly the fields /analyze reads, as form data."""
    js = (JS / "mm_page.js").read_text()
    sent = set(re.findall(r"data\.append\('([a-z_]+)'", js))
    sent |= {"action_taken", "occupancy_type", "total_units", "construction_method", "not_reverse",
             "hmda_start_year", "hmda_end_year", "sb_start_year", "sb_end_year", "baseline_hmda_start_year",
             "baseline_hmda_end_year", "baseline_sb_start_year", "baseline_sb_end_year"}
    blueprint = (ROOT / "justdata/apps/mergermeter/blueprint.py").read_text()
    read = set(re.findall(r"request\.form\.get\('([a-z_]+)'", blueprint[blueprint.index("def analyze"):]))
    assert read - {"job_id"} <= sent, read - sent
    assert "new FormData()" in js and "maxRunSeconds: MAX_RUN_S" in js


def test_no_inline_styles_icons_or_oversized_files():
    for t in ("mergermeter_analysis.html", "partials/mergermeter_controls.html", "partials/mergermeter_report_template.html"):
        text = (TEMPLATES / t).read_text()
        assert 'style="' not in text and "fa-" not in text, t
    for f in JS.glob("*.js"):
        assert len(f.read_text().splitlines()) <= 500, f.name
    assert len((TEMPLATES / "mergermeter_analysis.html").read_text().splitlines()) < 1000


def test_workbook_cells_are_escaped():
    js = (JS / "mm_report.js").read_text()
    assert "esc(t.val)" in js and "esc(w)" in js


def test_step_clock_times_each_progress_step():
    from justdata.apps.mergermeter.mergermeter_ops import _StepClock
    from justdata.shared.utils.perf import perf_stages, start_perf
    start_perf("mergermeter")
    clock = _StepClock()
    clock.mark("Querying HMDA data for Bank A...")
    clock.mark("Generating Excel report...")
    clock.mark("saving")
    assert [s["stage"] for s in perf_stages()] == ["step:querying_hmda_data_for_bank_a", "step:generating_excel_report"]
    assert all(isinstance(s["ms"], int) for s in perf_stages())


def test_goals_calculator_is_linked_from_the_results_toolbar(client):
    html = _page(client)
    actions = html[html.index('id="resultsActions"'):]
    actions = actions[:actions.index("</div>")]
    assert 'id="mmGoalsLink" href="/mergermeter/goals-calculator">Goals calculator →</a>' in actions
    js = (JS / "mm_page.js").read_text()
    assert "goals.href = BASE + '/goals-calculator?job_id=' + encodeURIComponent(jobId)" in js
