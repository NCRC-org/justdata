"""Smoke tests for analytics blueprint.

Verifies that key routes return expected status codes via the unified
platform test client. Intentionally shallow — existence and response
shape only, not data correctness.
"""


def test_analytics_index(unified_client):
    resp = unified_client.get("/analytics/")
    assert resp.status_code in (200, 302, 401, 403)


def test_analytics_health(unified_client):
    resp = unified_client.get("/analytics/health")
    assert resp.status_code == 200


def test_analytics_summary_api(unified_client):
    resp = unified_client.get("/analytics/api/summary")
    assert resp.status_code in (200, 401, 403)


def test_analytics_users_api(unified_client):
    resp = unified_client.get("/analytics/api/users")
    assert resp.status_code in (200, 401, 403)


def test_analytics_user_types_api(unified_client):
    resp = unified_client.get("/analytics/api/user-types")
    assert resp.status_code in (200, 401, 403)
