"""Smoke tests for electwatch blueprint."""


def test_electwatch_index(unified_client):
    resp = unified_client.get("/electwatch/")
    assert resp.status_code in (200, 302, 401, 403)


def test_electwatch_health(unified_client):
    resp = unified_client.get("/electwatch/health")
    assert resp.status_code in (200, 401, 403)


def test_electwatch_api_search(unified_client):
    """Verifies the ported /api/search endpoint is reachable."""
    resp = unified_client.get("/electwatch/api/search")
    assert resp.status_code in (200, 400, 401, 403)


def test_electwatch_api_bills_search(unified_client):
    """Verifies the ported /api/bills/search endpoint is reachable."""
    resp = unified_client.get("/electwatch/api/bills/search")
    assert resp.status_code in (200, 400, 401, 403)
