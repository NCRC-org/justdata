"""The /apps launcher (spec 03) on the testing deploy.

The launcher, the nav drawer and the landing roster all render from
nav_groups, so for every role that can open /apps the three must list the
same tools, in the same order, with the same open/locked state.
"""

import re
from markupsafe import escape
from pathlib import Path

import pytest

from justdata.main.auth import get_access_row
from justdata.main.launcher_content import HEADER_LINES
from justdata.shared.web.registry import resolve_registry

APPS_ROLES = ("public_registered", "member", "member_premium", "non_member_org",
              "staff", "senior_executive", "admin")
PARTIALS = sorted((Path(__file__).resolve().parents[2]
                   / "justdata/shared/web/templates/partials").glob("apps_*.html"))


@pytest.fixture
def platform_app(monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


def _get(app, path, user_type):
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = user_type
        s["firebase_user"] = {"uid": f"t-{user_type}", "email": "t@example.org", "email_verified": True}
    resp = client.get(path)
    assert resp.status_code == 200, (path, user_type)
    return resp.get_data(as_text=True)


def _launcher(html):
    """[(key, locked)] for every card or staff row, in page order."""
    main = html[html.index('id="appsLauncher"'):]
    out = []
    for m in re.finditer(r'<(article|a) class="([^"]*)" data-card="(\w+)"|<a href="[^"]*" class="(apps-row)" data-card="(\w+)"', main):
        if m.group(3):
            out.append((m.group(3), "is-locked" in m.group(2)))
        else:
            out.append((m.group(5), False))
    return out


def _drawer_items(user_type):
    return [(i["key"], i["state"] == "locked") for g in resolve_registry(get_access_row, user_type)
            if g["label"] for i in g["items"]]


@pytest.mark.parametrize("user_type", APPS_ROLES)
def test_launcher_matches_drawer_and_landing_roster(platform_app, user_type):
    launcher = _launcher(_get(platform_app, "/apps", user_type))
    assert launcher == _drawer_items(user_type)
    landing = _get(platform_app, "/", user_type)
    roster = landing[landing.index('id="roster"'):landing.index('id="cited"')]
    names = re.findall(r'class="home-roster-name">([^<]+)<', roster)
    by_key = {i["key"]: i["name"] for g in resolve_registry(get_access_row, user_type) for i in g["items"]}
    assert names == [by_key[k] for k, _ in launcher]


def test_public_registered_sees_four_locked_tools_and_the_request_panel(platform_app):
    html = _get(platform_app, "/apps", "public_registered")
    assert _launcher(html) == [("lendsight", True), ("bizsight", True), ("branchsight", True), ("mergermeter", True)]
    assert 'id="request-access"' in html
    assert "Request member access" in html
    assert str(escape(HEADER_LINES["free"])) in html


@pytest.mark.parametrize("user_type", ("member", "member_premium", "non_member_org"))
def test_testers_see_four_open_tools_and_no_panel(platform_app, user_type):
    html = _get(platform_app, "/apps", user_type)
    assert _launcher(html) == [("lendsight", False), ("bizsight", False), ("branchsight", False), ("mergermeter", False)]
    assert 'id="request-access"' not in html
    assert str(escape(HEADER_LINES["tester"])) in html


def test_staff_get_rows_and_no_panel(platform_app):
    html = _get(platform_app, "/apps", "staff")
    assert 'class="apps-rows"' in html
    assert 'id="request-access"' not in html
    assert str(escape(HEADER_LINES["staff"])) in html


def test_pending_request_replaces_the_button(platform_app, monkeypatch):
    import justdata.main.auth.services.membership as membership
    monkeypatch.setattr(membership, "member_request_status", lambda uid: ("pending", {}))
    html = _get(platform_app, "/apps", "public_registered")
    panel = html[html.index('id="request-access"'):]
    assert "Your request is pending review." in panel
    assert "openMemberRequestModal()" not in panel


def test_launcher_partials_lock_is_the_only_icon_and_no_guide_links():
    for path in PARTIALS:
        text = path.read_text()
        assert set(re.findall(r'data-lucide="([\w-]+)"', text)) <= {"lock"}, path.name
        assert "Guide →" not in text.replace("\"Guide →\"", ""), path.name
        assert "/about#" not in text, path.name
