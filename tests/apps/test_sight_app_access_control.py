"""Access control tests for the tester-facing Sight apps.

Covers the three gaps found in the 2026-08-08 routing audit and re-verified
2026-09-18: the no-op 'partial' access level, routes with no login requirement,
and force_refresh being enforced only in the template.
"""

from unittest.mock import patch

import pytest


# Routes that are deliberately reachable without authentication.
PUBLIC_ROUTES = {"/health", "/landing", "/__landing__", "/static/<path:filename>"}

DENIED = (301, 302, 401, 403)


def _concrete_path(rule):
    """Substitute placeholder values so parameterised rules can be requested."""
    path = rule.rule
    for arg in rule.arguments:
        path = path.replace(f"<{arg}>", "TEST")
        for converter in ("string:", "int:", "path:"):
            path = path.replace(f"<{converter}{arg}>", "TEST" if converter != "int:" else "1")
    return path


def _enumerate_routes(app, blueprint_name):
    for rule in app.url_map.iter_rules():
        # Static asset routes are public by design, including the blueprint-scoped
        # ones each Sight app registers as "<blueprint>.static".
        if rule.endpoint == "landing" or rule.endpoint.split(".")[-1] == "static":
            continue
        if not rule.endpoint.startswith(f"{blueprint_name}."):
            continue
        if rule.rule in PUBLIC_ROUTES:
            continue
        yield rule


@pytest.mark.parametrize(
    "app_fixture,blueprint_name",
    [
        ("lendsight_app", "lendsight"),
        ("bizsight_app", "bizsight"),
        ("branchsight_app", "branchsight"),
    ],
)
def test_no_route_is_reachable_anonymously(app_fixture, blueprint_name, request):
    """Every route except /health must deny an unauthenticated caller.

    Guards the regression where BranchSight's and BizSight's /analyze, /report,
    /report-data and /download carried no login requirement at all.
    """
    app = request.getfixturevalue(app_fixture)
    client = app.test_client()

    reachable = []
    for rule in _enumerate_routes(app, blueprint_name):
        path = _concrete_path(rule)
        method = "POST" if "POST" in rule.methods else "GET"
        resp = client.open(path, method=method, json={} if method == "POST" else None)
        if resp.status_code not in DENIED:
            reachable.append(f"{method} {path} -> {resp.status_code}")

    assert not reachable, "routes reachable without authentication: " + ", ".join(reachable)


@pytest.mark.parametrize(
    "client_fixture,prefix",
    [
        ("lendsight_client", "lendsight"),
        ("bizsight_client", "bizsight"),
        ("branchsight_client", "branchsight"),
    ],
)
def test_anonymous_json_request_gets_401(client_fixture, prefix, request):
    client = request.getfixturevalue(client_fixture)
    resp = client.post("/analyze", json={})
    assert resp.status_code == 401
    assert resp.get_json()["code"] == "auth_required"


def test_locked_tier_denied_on_bizsight(bizsight_client, sign_in):
    """public_registered is 'locked' on BizSight, below the 'limited' view gate."""
    sign_in(bizsight_client, "public_registered")
    resp = bizsight_client.post("/analyze", json={})
    assert resp.status_code == 403
    assert resp.get_json()["required_level"] == "limited"


def test_limited_tier_may_view_lendsight_but_not_export(lendsight_client, sign_in):
    """public_registered is 'limited' on LendSight: viewing allowed, export not.

    This is the distinction the no-op 'partial' level erased.
    """
    sign_in(lendsight_client, "public_registered")

    denied = lendsight_client.get("/download", json={})
    assert denied.status_code == 403
    assert denied.get_json()["required_level"] == "full"

    # The view gate passes; the handler then 404s for lack of a job, which is
    # the correct post-authorisation behaviour.
    allowed = lendsight_client.get("/report-data", json={})
    assert allowed.status_code != 403


@pytest.mark.parametrize(
    "client_fixture", ["lendsight_client", "bizsight_client", "branchsight_client"]
)
def test_member_tier_may_export(client_fixture, sign_in, request):
    client = request.getfixturevalue(client_fixture)
    sign_in(client, "member")
    resp = client.get("/download", json={})
    assert resp.status_code != 403


class TestForceRefreshIsServerEnforced:
    """force_refresh triggers fresh BigQuery + Anthropic spend, so it must be
    checked server-side, not only hidden in the template."""

    CACHED = {"job_id": "job-1", "result_data": {"x": 1}, "cache_key": "key-1"}
    PAYLOAD = {
        "county_data": {"state": "MD", "counties": ["Montgomery"]},
        "years": "2020-2022",
        "force_refresh": True,
    }

    def test_member_cannot_bypass_cache(self, bizsight_client, sign_in):
        sign_in(bizsight_client, "member")
        with patch("justdata.apps.bizsight.blueprint.get_cached_result") as cached, \
             patch("justdata.apps.bizsight.blueprint.log_usage"), \
             patch("justdata.apps.bizsight.blueprint.update_progress"):
            cached.return_value = self.CACHED
            resp = bizsight_client.post("/analyze", json=self.PAYLOAD)

        assert cached.called, "cache must still be consulted for a non-privileged user"
        assert resp.get_json()["cached"] is True

    def test_staff_may_bypass_cache(self, bizsight_client, sign_in):
        sign_in(bizsight_client, "staff")
        with patch("justdata.apps.bizsight.blueprint.get_cached_result") as cached, \
             patch("justdata.apps.bizsight.blueprint.log_usage"), \
             patch("justdata.apps.bizsight.blueprint.create_progress_tracker"), \
             patch("threading.Thread"):
            resp = bizsight_client.post("/analyze", json=self.PAYLOAD)

        assert not cached.called, "privileged user's force_refresh should skip the cache"
        assert resp.status_code == 200


class TestCanForceRefresh:
    def test_privileged_roles_allowed(self):
        from justdata.main.auth import can_force_refresh

        for tier in ("staff", "senior_executive", "admin"):
            assert can_force_refresh(tier) is True

    def test_everyone_else_denied(self):
        from justdata.main.auth import can_force_refresh

        for tier in ("public_anonymous", "public_registered", "member",
                     "member_premium", "non_member_org"):
            assert can_force_refresh(tier) is False


def test_access_matrix_has_no_duplicate_keys():
    """A duplicated dict key silently discards the first definition."""
    import ast
    import inspect

    from justdata.main import auth

    tree = ast.parse(inspect.getsource(auth))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "ACCESS_MATRIX" for t in node.targets
        ):
            keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
            duplicates = {k for k in keys if keys.count(k) > 1}
            assert not duplicates, f"duplicate ACCESS_MATRIX keys: {duplicates}"
            return
    pytest.fail("ACCESS_MATRIX assignment not found")
