"""Smoke tests for dotlender blueprint.

Platform note: justdata/main/app.py has a global before_request handler
(check_privileged_access) that returns the access_restricted page with
status 200 for any non-privileged user, and the route's staff_required
decorator requires `firebase_user` in the session. These tests set both
session keys when impersonating privileged users, and differentiate
authorized vs. restricted responses by checking the body for a marker
that only appears on the real DotLender page.
"""

DOTLENDER_PAGE_MARKER = b"dotlender-filters"


def _authed_session(client, user_type):
    """Populate session with both firebase_user and user_type."""
    with client.session_transaction() as sess:
        sess["firebase_user"] = {
            "uid": f"test-{user_type}",
            "email": f"test-{user_type}@ncrc.org",
            "email_verified": True,
        }
        sess["user_type"] = user_type


def test_dotlender_health(unified_client):
    """Health endpoint is gated by global before_request when unauthenticated,
    but reachable with privileged session."""
    _authed_session(unified_client, "admin")
    resp = unified_client.get("/dotlender/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "app": "dotlender"}


def test_dotlender_index_unauthenticated(unified_client):
    """Unauthenticated request gets restricted page, not the dotlender page."""
    resp = unified_client.get("/dotlender/")
    assert resp.status_code in (200, 302, 401, 403)
    if resp.status_code == 200:
        assert DOTLENDER_PAGE_MARKER not in resp.data


def test_dotlender_index_staff(unified_client):
    """Staff user can access DotLender."""
    _authed_session(unified_client, "staff")
    resp = unified_client.get("/dotlender/")
    assert resp.status_code == 200
    assert DOTLENDER_PAGE_MARKER in resp.data


def test_dotlender_index_senior_executive(unified_client):
    """Senior executive can access DotLender."""
    _authed_session(unified_client, "senior_executive")
    resp = unified_client.get("/dotlender/")
    assert resp.status_code == 200
    assert DOTLENDER_PAGE_MARKER in resp.data


def test_dotlender_index_admin(unified_client):
    """Admin user can access DotLender."""
    _authed_session(unified_client, "admin")
    resp = unified_client.get("/dotlender/")
    assert resp.status_code == 200
    assert DOTLENDER_PAGE_MARKER in resp.data


def test_dotlender_index_member(unified_client):
    """Member user is blocked — gets restricted page or redirect, not DotLender content."""
    _authed_session(unified_client, "member")
    resp = unified_client.get("/dotlender/")
    assert resp.status_code in (200, 302, 401, 403)
    if resp.status_code == 200:
        assert DOTLENDER_PAGE_MARKER not in resp.data


def test_race_choropleth_route_exists(unified_client):
    """POST /dotlender/api/race-choropleth is registered (not 404/405).

    Empty body should produce a 400 validation error from _prep_request
    (invalid geography) — the test cares only that the route exists.
    """
    _authed_session(unified_client, "admin")
    resp = unified_client.post(
        "/dotlender/api/race-choropleth",
        json={},
        content_type="application/json",
    )
    assert resp.status_code not in (404, 405)
    # Most likely 400 from validate_geography on empty body.
    assert resp.status_code in (200, 400)
