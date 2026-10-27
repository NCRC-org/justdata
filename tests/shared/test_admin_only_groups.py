"""Both staff groups are admin-only (Jad, 2026-10-27, spec 05 line 2).

MergerMeter, Analytics and Administration (Staff tools) and BranchMapper,
DotLender and DataExplorer (In consolidation) are hidden from plain staff and
senior_executive: not in the drawer, on /apps or in the landing roster, and
their routes refuse those roles. Admin keeps all six. Checked on every deploy
the matrix serves, with and without the testing overlay.
"""

import pytest

from justdata.main.auth import get_access_row, get_app_access
from justdata.shared.web.registry import resolve_registry

ADMIN_ONLY = ("mergermeter", "analytics", "admin", "branchmapper", "dotlender", "dataexplorer")
PAGES = {"mergermeter": "/mergermeter/", "analytics": "/analytics/", "admin": "/admin/users",
         "branchmapper": "/branchmapper/", "dotlender": "/dotlender/", "dataexplorer": "/dataexplorer/"}
PLAIN_STAFF = ("staff", "senior_executive")


@pytest.fixture(params=("testing", "staging"))
def platform_app(request, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", request.param)
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


def _client(app, user_type):
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = user_type
        s["firebase_user"] = {"uid": f"t-{user_type}", "email": "t@example.org", "email_verified": True}
    return client


def _keys(user_type):
    groups = resolve_registry(get_access_row, user_type, is_staff=True)
    return {i["key"] for g in groups for i in g["items"]}


@pytest.mark.parametrize("user_type", PLAIN_STAFF)
def test_plain_staff_cannot_see_or_open_the_staff_groups(platform_app, user_type):
    assert not _keys(user_type) & set(ADMIN_ONLY)
    for app_name in ADMIN_ONLY:
        assert get_app_access(app_name, user_type) == "hidden", app_name
    client = _client(platform_app, user_type)
    for path in ("/apps", "/"):
        html = client.get(path).get_data(as_text=True)
        for app_name in ADMIN_ONLY:
            assert f'data-card="{app_name}"' not in html, (path, app_name)
            assert f'data-app="{app_name}"' not in html, (path, app_name)
            assert f'href="{PAGES[app_name]}"' not in html, (path, app_name)
    for app_name, path in PAGES.items():
        resp = client.get(path)
        assert resp.status_code == 302, (app_name, resp.status_code)


@pytest.mark.parametrize("user_type", PLAIN_STAFF)
def test_plain_staff_keep_the_sight_apps(platform_app, user_type):
    assert {"lendsight", "bizsight", "branchsight"} <= _keys(user_type)


def test_admin_keeps_all_six(platform_app):
    assert set(ADMIN_ONLY) <= _keys("admin")
    client = _client(platform_app, "admin")
    html = client.get("/apps").get_data(as_text=True)
    for app_name in ADMIN_ONLY:
        assert f'data-card="{app_name}"' in html, app_name
    for app_name in ("mergermeter", "dotlender", "admin"):
        assert client.get(PAGES[app_name]).status_code == 200, app_name


@pytest.mark.parametrize("method,path", (("post", "/mergermeter/analyze"), ("get", "/dataexplorer/api/states"),
                                         ("get", "/analytics/api/summary")))
def test_plain_staff_api_calls_are_refused(platform_app, method, path):
    resp = getattr(_client(platform_app, "staff"), method)(path, json={} if method == "post" else None)
    assert resp.status_code in (302, 403), resp.status_code
