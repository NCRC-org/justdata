"""Admin pages escape user-supplied fields (stored XSS fix, 2026-11-10).

A user controls their name and organization at sign-up. /admin/users used to
put them into the page as HTML, so a name like <script>...</script> ran in an
admin's browser. These tests render the real page, run its scripts in node
against such a user, and check that the markup comes out as text.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC_JS = Path(__file__).resolve().parents[2] / "justdata/shared/web/static/js"

SCRIPT_NAME = "<script>alert('name')</script>"
SCRIPT_ORG = '<img src=x onerror="alert(1)"><script>alert(\'org\')</script>'
QUOTE_EMAIL = "o'brien<b>@example.org"

EVIL_USER = {
    "uid": "uid-evil", "email": QUOTE_EMAIL, "displayName": SCRIPT_NAME,
    "organization": SCRIPT_ORG, "userType": "tester", "providerData": ["password"],
    "emailVerified": True, "testerAccess": None, "loginCount": 1,
}

# Just enough DOM for the page's inline script to load and render
DOM_STUB = """
const elements = {};
function el(id) {
  if (!elements[id]) elements[id] = {
    id, innerHTML: '', textContent: '', value: '', disabled: false, checked: false,
    style: {}, dataset: {}, classList: {add() {}, remove() {}, contains() { return false; }},
    addEventListener() {}, removeAttribute() {}, setAttribute() {}, appendChild(c) { this.child = c; },
    insertAdjacentHTML(pos, html) { this.innerHTML += html; }, remove() {}, focus() {},
    querySelectorAll() { return []; }, querySelector() { return null; },
  };
  return elements[id];
}
global.document = {
  getElementById: el, addEventListener() {}, querySelectorAll() { return []; },
  querySelector() { return null; }, createElement(tag) { return el('created-' + tag); },
};
global.window = {JustDataAuth: {getToken: async () => 't', getCurrentUser: () => null}, lucide: null};
global.setTimeout = () => 0;
console.log = console.warn = () => {};  // the page logs; keep stdout for results
"""


def _admin_page(unified_client, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "production")
    with unified_client.session_transaction() as sess:
        sess["user_type"] = "admin"
        sess["firebase_user"] = {"uid": "admin-uid", "email": "admin@example.org", "email_verified": True}
    return unified_client.get("/admin/users").get_data(as_text=True)


def _inline_script(page):
    blocks = re.findall(r"<script>(.*?)</script>", page, flags=re.S)
    return next(b for b in blocks if "function renderTable" in b)


def _run(page, calls):
    script = "\n".join([
        DOM_STUB,
        (STATIC_JS / "escape-html.js").read_text(),
        _inline_script(page),
        (STATIC_JS / "admin-users-access.js").read_text(),
        calls,
    ])
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


def _assert_text_only(html):
    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;alert(&#39;name&#39;)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_user_table_shows_markup_in_name_and_organization_as_text(unified_client, monkeypatch):
    page = _admin_page(unified_client, monkeypatch)
    html = _run(page, f"""
        allUsers = [{json.dumps(EVIL_USER)}];
        renderTable(allUsers);
        process.stdout.write(document.getElementById('usersTableBody').innerHTML);
    """)
    _assert_text_only(html)
    assert "o&#39;brien&lt;b&gt;@example.org" in html
    # The email no longer rides in an onclick handler, where escaping can't help
    assert "openResetPasswordModal('uid-evil')" in html
    assert "brien" not in html.split("openResetPasswordModal")[1].split(")")[0]


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_delete_confirmation_shows_markup_as_text(unified_client, monkeypatch):
    page = _admin_page(unified_client, monkeypatch)
    html = _run(page, f"""
        allUsers = [{json.dumps(EVIL_USER)}];
        selectedUsers = new Set(['uid-evil']);
        openDeleteModal();
        process.stdout.write(document.getElementById('deleteUserList').innerHTML);
    """)
    assert "<script>" not in html and "<b>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_toast_messages_are_text(unified_client, monkeypatch):
    page = _admin_page(unified_client, monkeypatch)
    html = _run(page, """
        let captured = '';
        document.getElementById('toastContainer').appendChild = (t) => { captured = t.innerHTML; };
        showToast("<script>alert('toast')</script>", 'error');
        process.stdout.write(captured);
    """)
    assert "<script>" not in html and "&lt;script&gt;" in html


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_reset_password_modal_looks_the_email_up(unified_client, monkeypatch):
    page = _admin_page(unified_client, monkeypatch)
    out = _run(page, f"""
        allUsers = [{json.dumps(EVIL_USER)}];
        openResetPasswordModal('uid-evil');
        process.stdout.write(document.getElementById('resetPasswordEmail').textContent);
    """)
    assert out == QUOTE_EMAIL  # set as textContent, so no escaping needed


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_escape_html_helper():
    script = (STATIC_JS / "escape-html.js").read_text() + """
        process.stdout.write(JSON.stringify([
            escapeHtml(`<a href="x">'&'</a>`), escapeHtml(null), escapeHtml(undefined), escapeHtml(0)]));
    """
    out = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert out == ["&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;", "", "", "0"]


def test_every_page_loads_the_helper_before_its_own_scripts(unified_client, monkeypatch):
    page = _admin_page(unified_client, monkeypatch)
    assert page.index("js/escape-html.js") < page.index("function renderTable")

