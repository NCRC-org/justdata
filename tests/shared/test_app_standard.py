"""Spec 04 Part A: the analysis-app standard (app_page.html, app.css,
state partials, app_states.js, /dev/app-states)."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from justdata.shared.web.app_page import app_page_context, find_app

WEB = Path(__file__).resolve().parents[2] / "justdata" / "shared" / "web"
APP_CSS = WEB / "static" / "css" / "app.css"
APP_STATES_JS = WEB / "static" / "js" / "app_states.js"


@pytest.fixture
def debug_app(monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "1")
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


def _preview(debug_app):
    # The platform gate admits staff only outside the testing overlay.
    client = debug_app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    resp = client.get("/dev/app-states")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_context_reads_the_registry():
    ctx = app_page_context("branchsight", form_id="f")
    assert ctx["app"].name == "BranchSight"
    assert ctx["group_label"] == find_app("branchsight")[0] == "Analyze branches"
    assert ctx["shows_juxtaposition"] is True
    with pytest.raises(ValueError):
        app_page_context("lendsight", form_id="f", exports=("docx",))
    with pytest.raises(KeyError):
        find_app("nope")


def test_preview_renders_the_skeleton(debug_app):
    html = _preview(debug_app)
    for needle in ('id="results"', 'aria-live="polite"', 'aria-busy="false"', 'id="resultsBody"',
                   'data-state="idle"', 'data-action="reset"', 'form="devStatesForm"',
                   'id="appStateLoading"', 'id="appStateEmpty"', 'id="appStateError"',
                   'js/app_states.js', 'class="app-header"'):
        assert needle in html, needle
    assert re.search(r'id="runBtn">Run analysis</button>', html)


def test_app_css_loads_after_shell_css(debug_app):
    html = _preview(debug_app)
    assert html.index("css/shell.css") < html.index("css/app.css")


def test_sources_copy_and_juxtaposition_note(debug_app):
    html = _preview(debug_app)
    assert ("Figures are computed from the public datasets listed below, "
            "with the years and exclusions stated for each.") in html
    assert "matched with confidence" not in html
    assert "NCRC's published methodology" not in html
    assert "How this analysis is built" not in html
    assert "Correlation is not causation." in html


def test_toolbar_renders_only_listed_exports(debug_app):
    from flask import render_template
    with debug_app.test_request_context("/"):
        none = render_template("partials/app_results_toolbar.html", exports=())
        csv_only = render_template("partials/app_results_toolbar.html", exports=("csv",))
    assert "data-export" not in none and "copy-citation" in none
    assert 'data-export="csv"' in csv_only and 'data-export="pdf"' not in csv_only
    with debug_app.test_request_context("/"):
        xlsx_pdf = render_template("partials/app_results_toolbar.html", exports=("xlsx", "pdf"))
    assert 'data-export="xlsx">Download Excel' in xlsx_pdf and 'data-export="csv"' not in xlsx_pdf


def test_error_state_hides_an_empty_reference(debug_app):
    from flask import render_template
    with debug_app.test_request_context("/"):
        bare = render_template("partials/app_state_error.html")
        with_ref = render_template("partials/app_state_error.html", error_ref="ab12cd34")
    assert 'id="errorRefLine" hidden' in bare and 'href="/contact"' in bare
    assert "ab12cd34" in with_ref and "hidden" not in with_ref


@pytest.mark.parametrize("debug,flask_debug,registered", [
    (False, None, False), (False, "0", False), (False, "1", True), (True, None, True),
])
def test_dev_route_only_registered_in_debug(monkeypatch, debug, flask_debug, registered):
    from flask import Flask
    from justdata.shared.web.dev_routes import register_dev_routes
    if flask_debug is None:
        monkeypatch.delenv("FLASK_DEBUG", raising=False)
    else:
        monkeypatch.setenv("FLASK_DEBUG", flask_debug)
    app = Flask(__name__)
    app.debug = debug
    assert register_dev_routes(app) is registered
    assert ("dev.app_states_preview" in app.view_functions) is registered


def test_app_css_is_scoped_to_app_classes():
    """No visual change to unmigrated apps: every rule targets .app-* only."""
    css = re.sub(r"/\*.*?\*/", "", APP_CSS.read_text(), flags=re.S)
    css = re.sub(r"@keyframes[^{]*\{(?:[^{}]*\{[^}]*\})*\s*\}", "", css)
    selectors = []
    for sel in re.findall(r"([^{}]+)\{[^{}]*\}", css):
        sel = sel.strip()
        if sel.startswith("@media"):
            sel = sel.split(")", 1)[1].strip()
        selectors += [s.strip() for s in sel.split(",") if s.strip()]
    assert selectors
    for s in selectors:
        # .shell-main.app-main applies only on app_page.html (main_class)
        assert s.startswith((".app-", ".shell-main.app-main")), s
    # .report-prose is defined in style.css; app.css may only add spacing
    # inside results, never redefine the class itself.
    assert not any(sel.startswith(".report-prose") for sel in selectors)
    assert "--color-fg-accent" not in css


def test_app_states_js_size():
    assert len(APP_STATES_JS.read_text().splitlines()) < 300


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.parametrize("citation,expected", [
    ({"dataset": "HMDA", "years": "2018 to 2024", "geography": "Cook County, IL",
      "lenders": ["JPMorgan Chase"], "url": "https://example.org/r?job_id=1"},
     "NCRC JustData, LendSight. HMDA 2018 to 2024; Cook County, IL; JPMorgan Chase. "
     "Generated 2026-10-07. https://example.org/r?job_id=1"),
    ({"dataset": "HMDA", "geography": "Cook County, IL", "lenders": ["A", "B"]},
     "NCRC JustData, LendSight. HMDA; Cook County, IL; A, B. Generated 2026-10-07."),
    ({}, "NCRC JustData, LendSight. Generated 2026-10-07."),
])
def test_citation_format(citation, expected):
    script = (
        f"require({json.dumps(str(APP_STATES_JS))});"
        f"process.stdout.write(AppStates.formatCitation('LendSight', {json.dumps(citation)},"
        " new Date(2026, 9, 7)));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    assert out.stdout == expected


def _node(expr):
    script = f"require({json.dumps(str(APP_STATES_JS))}); process.stdout.write(JSON.stringify({expr}));"
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.parametrize("elapsed_s,since_update_s,expected", [
    (30, 30, None),            # running, recent progress
    (59, 59, None),            # just under the stall limit
    (60, 60, "stalled"),       # no progress for 60 s
    (300, 61, "stalled"),      # progress stopped mid-run
    (599, 5, None),            # long run that keeps reporting progress
    (600, 5, "max"),           # still reporting progress, but 10 minutes total
    (900, 900, "max"),         # both limits passed: the absolute cap wins
])
def test_timeout_paths(elapsed_s, since_update_s, expected):
    now = 10_000_000
    started = now - elapsed_s * 1000
    last_update = now - since_update_s * 1000
    assert _node(f"AppStates.timeoutReason({now}, {started}, {last_update})") == expected


def test_idle_text_default_and_override(debug_app):
    from flask import render_template
    with debug_app.test_request_context("/"):
        default = render_template("partials/app_state_idle.html")
        custom = render_template("partials/app_state_idle.html",
                                 idle_message="Choose a geography and a lender, then run the analysis.")
    assert 'Choose a geography<span class="app-wide-only"> on the left</span>, then run the analysis.' in default
    assert "lender" not in default
    assert "Choose a geography and a lender, then run the analysis." in custom
    assert "app-wide-only" not in custom
    assert ".app-wide-only { display: none; }" in APP_CSS.read_text()


APP_PROGRESS_JS = WEB / "static" / "js" / "app_progress.js"


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.parametrize("text,expected", [
    ("We couldn't complete this analysis. Reference: ab12cd34",
     {"message": "We couldn't complete this analysis.", "ref": "ab12cd34"}),
    ("No data found for the specified parameters", {"message": "No data found for the specified parameters", "ref": None}),
    ("", {"message": "", "ref": None}),
])
def test_progress_error_text_splits_message_and_reference(text, expected):
    script = (f"require({json.dumps(str(APP_PROGRESS_JS))});"
              f"process.stdout.write(JSON.stringify(AppProgress.splitRef({json.dumps(text)})));")
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == expected


def test_app_page_loads_progress_module(debug_app):
    html = _preview(debug_app)
    assert html.index("js/app_states.js") < html.index("js/app_progress.js")


def test_methods_link_only_inside_the_results_actions(debug_app):
    from flask import render_template
    with debug_app.test_request_context("/"):
        without = render_template("partials/app_results_toolbar.html", exports=())
        with_link = render_template("partials/app_results_toolbar.html", exports=(), methods_anchor="methodsSection")
    assert "Methods" not in without
    actions = with_link[with_link.index('id="resultsActions" hidden'):]
    assert '<a class="btn btn-ghost btn-sm" href="#methodsSection">Methods →</a>' in actions


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_missing_narrative_line_is_defined_once():
    assert _node("AppStates.NARRATIVE_MISSING") == "A written summary was not generated for this run."
    assert ".app-narrative-missing" in APP_CSS.read_text()


APP_REPORT_JS = WEB / "static" / "js" / "app_report.js"


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.parametrize("text,expected", [
    ("**Total:** fell <script>x</script>", "<p><strong>Total:</strong> fell &lt;script&gt;x&lt;/script&gt;</p>"),
    ("• one\n• two", "<ul><li>one</li><li>two</li></ul>"),
    ("See [NCRC](https://ncrc.org).", '<p>See <a href="https://ncrc.org" target="_blank" rel="noopener">NCRC</a>.</p>'),
    ("[bad](javascript:alert(1))", "<p>[bad](javascript:alert(1))</p>"),
    ("## Heading\nBody", "<p>Body</p>"),
])
def test_narrative_is_escaped_before_markdown(text, expected):
    script = (f"require({json.dumps(str(APP_REPORT_JS))});"
              f"process.stdout.write(AppReport.formatNarrative({json.dumps(text)}));")
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    assert out.stdout == expected


def test_app_report_js_size():
    assert len(APP_REPORT_JS.read_text().splitlines()) < 300
