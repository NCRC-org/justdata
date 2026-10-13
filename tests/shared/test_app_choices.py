"""Shared controls column (spec 04 A2): the sticky column scrolls inside
itself only in the two-column layout, and long option lists collapse."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = (ROOT / "justdata/shared/web/static/css/app.css").read_text()
JS = ROOT / "justdata/shared/web/static/js"


def _rule(selector, css=CSS):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert m, selector
    return m.group(1)


def test_controls_scroll_inside_in_two_columns_only():
    wide = _rule(".app-controls")
    assert "position: sticky" in wide and "overflow-y: auto" in wide
    assert "max-height: calc(100vh - var(--header-h) - 2 * var(--s-4))" in wide
    assert "overflow-y: auto" in _rule(".app-controls > form")
    narrow = CSS[CSS.index("@media (max-width: 1100px) {\n  .app-controls"):]
    narrow = narrow[:narrow.index("\n}\n")]
    assert "max-height: none" in narrow and "overflow: visible" in narrow and "position: static" in narrow


def test_no_app_overrides_the_controls_column():
    for css in (ROOT / "justdata/shared/web/static/css").glob("*.css"):
        if css.name != "app.css":
            assert not re.search(r"\.app-controls[^-]", css.read_text()), css.name


def test_choices_summary_and_invalid_fields_open_the_list():
    js = (JS / "app_choices.js").read_text()
    assert "' of ' + all.length" in js and "'Change →'" in js and "data-summary" in js
    run = (JS / "app_run.js").read_text()
    assert "el.closest('details.app-choices')" in run and "list.open = true" in run
    page = (ROOT / "justdata/shared/web/templates/app_page.html").read_text()
    assert page.index("js/app_run.js") < page.index("js/app_choices.js")
