"""BranchMapper keeps bank names out of inline handlers (2026-11-10).

The bank search list and the selected-bank chips put the name inside
onclick="addBank('...')" with only ' escaped. A name containing " ended the
attribute and anything after it ran as script. Names now ride in data-*
attributes, escaped, and one delegated listener per container reads them back.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "justdata/apps/branchmapper/templates/partials/_branchmapper_scripts.html"
ESCAPE_JS = ROOT / "justdata/shared/web/static/js/escape-html.js"

EVIL = 'First " onmouseover="alert(1)" x=\'Bank\' <img src=x onerror=alert(2)>'


def _function(source, name):
    """Source of `function name(...) {...}` from the template, by brace matching."""
    start = re.search(rf"(async )?function {name}\(", source).start()
    depth, i = 0, source.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        i += 1
        if depth == 0:
            return source[start:i]


def _run(js):
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_search_results_and_chips_carry_names_as_data():
    source = SCRIPTS.read_text()
    js = "\n".join([
        ESCAPE_JS.read_text(),
        """
        const els = {};
        global.document = {getElementById: id => (els[id] = els[id] || {id, style: {}, innerHTML: ''})};
        let allBankNames = [NAME], selectedBanks = [], currentViewMode = 'sod';
        """.replace("NAME", json.dumps(EVIL)),
        _function(source, "showSearchResults"),
        _function(source, "renderBankChips"),
        """
        showSearchResults('first');
        const results = els.bankSearchResults.innerHTML;
        selectedBanks = [{name: NAME, color: '#000', branches: [], oscrEvents: []}];
        renderBankChips();
        process.stdout.write(JSON.stringify([results, els.bankChipsContainer.innerHTML]));
        """.replace("NAME", json.dumps(EVIL)),
    ])
    results, chips = _run(js)
    for html in (results, chips):
        assert "onclick" not in html
        assert "<img" not in html
        assert 'onmouseover="' not in html
        assert "First &quot; onmouseover=&quot;alert(1)&quot; x=&#39;Bank&#39; &lt;img" in html
    assert 'data-bank-name="First &quot;' in results
    assert 'data-remove-bank="First &quot;' in chips


def test_clicks_are_delegated_and_read_the_data_attributes():
    source = SCRIPTS.read_text()
    setup = _function(source, "initializeBankSearch")
    assert "closest('[data-bank-name]')" in setup and "addBank(item.dataset.bankName)" in setup
    assert "closest('[data-remove-bank]')" in setup and "removeBank(chip.dataset.removeBank)" in setup
    assert "onclick=\"addBank(" not in source
    assert "onclick=\"removeBank(" not in source


def test_page_loads_the_escape_helper(unified_client):
    with unified_client.session_transaction() as sess:
        sess["user_type"] = "admin"
        sess["firebase_user"] = {"uid": "admin-uid", "email": "admin@example.org", "email_verified": True}
    page = unified_client.get("/branchmapper/").get_data(as_text=True)
    assert page.index("js/escape-html.js") < page.index("function showSearchResults")
