"""Global staff-only gate on the testing deploy (spec 02, gate PR).

On JUSTDATA_ENV=testing, check_privileged_access() also admits TESTER_ROLES,
anyone on the exact TESTING_PUBLIC_PATHS, and a signed-in public_registered
user on TESTING_REGISTERED_PATHS (/apps). Every other route still returns the
restricted page (or a 403 for /api/) to the public roles. Off the testing
deploy nothing changes: non-staff roles get the restricted page everywhere,
including "/".
"""

import pytest

from justdata.main.app import EXEMPT_PATHS
from justdata.main.auth.access_overlay import (
    TESTER_APPS, TESTER_ROLES, TESTING_PUBLIC_PATHS, TESTING_REGISTERED_PATHS,
)

PUBLIC_ROLES = ("public_anonymous", "public_registered")
# Only access_restricted.html renders this logo block.
RESTRICTED_MARKER = 'alt="NCRC - National Community Reinvestment Coalition"'


@pytest.fixture
def platform_app():
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


def _get(app, path, user_type):
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = user_type
        if user_type != "public_anonymous":
            s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return client.get(path)


def _is_restricted(resp, path):
    if path.startswith("/api/"):
        return resp.status_code == 403
    return resp.status_code == 200 and RESTRICTED_MARKER in resp.get_data(as_text=True)


def _gated_paths(app):
    """Every parameterless GET route the global gate applies to."""
    paths = set()
    for rule in app.url_map.iter_rules():
        p = rule.rule
        if "GET" not in rule.methods or "<" in p:
            continue
        if any(p.startswith(e) for e in EXEMPT_PATHS):
            continue
        paths.add(p)
    return sorted(paths)


@pytest.mark.parametrize("user_type", PUBLIC_ROLES)
def test_testing_public_paths_render_for_public_roles(platform_app, monkeypatch, user_type):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    for path in sorted(TESTING_PUBLIC_PATHS):
        resp = _get(platform_app, path, user_type)
        assert resp.status_code == 200, path
        assert RESTRICTED_MARKER not in resp.get_data(as_text=True), path


@pytest.mark.parametrize("user_type", PUBLIC_ROLES)
def test_testing_every_other_route_stays_restricted_for_public_roles(platform_app, monkeypatch, user_type):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    allowed = TESTING_PUBLIC_PATHS | (TESTING_REGISTERED_PATHS if user_type == "public_registered" else set())
    leaked = [
        p for p in _gated_paths(platform_app)
        if p not in allowed and not _is_restricted(_get(platform_app, p, user_type), p)
    ]
    assert leaked == []


def test_testing_apps_page_opens_for_signed_in_public_registered_only(platform_app, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    assert not _is_restricted(_get(platform_app, "/apps", "public_registered"), "/apps")
    # A session claiming public_registered without a signed-in user stays out.
    client = platform_app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "public_registered"
    assert _is_restricted(client.get("/apps"), "/apps")
    assert _is_restricted(_get(platform_app, "/apps", "public_anonymous"), "/apps")


def test_testing_public_registered_cannot_open_any_app(platform_app, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    for path in ("/lendsight/", "/bizsight/", "/branchsight/", "/mergermeter/",
                 "/branchmapper/", "/dataexplorer/", "/dotlender/", "/analytics/"):
        resp = _get(platform_app, path, "public_registered")
        assert _is_restricted(resp, path) or resp.status_code in (301, 302, 308, 401, 403), path


def test_testing_public_roles_see_the_four_tester_apps_locked(monkeypatch):
    from justdata.main.auth import get_access_row
    from justdata.shared.web.registry import resolve_registry
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    for role in ("public_anonymous", "public_registered"):
        items = {i["key"]: i["state"] for g in resolve_registry(get_access_row, role)
                 for i in g["items"] if i["key"] not in ("home", "apps")}
        assert items == {key: "locked" for key in TESTER_APPS}, role


def test_public_paths_match_exactly_not_as_prefixes(monkeypatch):
    from justdata.main.auth.access_overlay import testing_gate_admits
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    for path in ("/lendsight", "/apps", "/about/x", "/contacts", "/admin/users"):
        assert not testing_gate_admits(path, "public_anonymous"), path


@pytest.mark.parametrize("user_type", TESTER_ROLES)
def test_testing_admits_tester_roles_past_the_global_gate(platform_app, monkeypatch, user_type):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    for path in ("/apps", "/lendsight/", "/bizsight/", "/branchsight/", "/mergermeter/"):
        assert not _is_restricted(_get(platform_app, path, user_type), path), path


@pytest.mark.parametrize("env", [None, "staging", "production"])
@pytest.mark.parametrize("user_type", PUBLIC_ROLES + TESTER_ROLES)
def test_other_deploys_keep_the_staff_only_gate(platform_app, monkeypatch, env, user_type):
    if env is None:
        monkeypatch.delenv("JUSTDATA_ENV", raising=False)
    else:
        monkeypatch.setenv("JUSTDATA_ENV", env)
    for path in ("/", "/about", "/contact", "/apps", "/lendsight/"):
        assert _is_restricted(_get(platform_app, path, user_type), path), (env, path)


@pytest.mark.parametrize("user_type", TESTER_ROLES)
def test_status_dashboard_is_staff_only(platform_app, monkeypatch, user_type):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    resp = _get(platform_app, "/status", user_type)
    assert resp.status_code in (302, 403)
    assert "Status Dashboard" not in resp.get_data(as_text=True)


def test_status_dashboard_still_renders_for_staff(platform_app, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    resp = _get(platform_app, "/status", "staff")
    assert resp.status_code == 200
    assert "Status Dashboard" in resp.get_data(as_text=True)
