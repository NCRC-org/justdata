"""Smoke tests for bizsight blueprint."""


def test_bizsight_index(unified_client):
    resp = unified_client.get("/bizsight/")
    assert resp.status_code in (200, 302, 401, 403)


def test_bizsight_health(unified_client):
    resp = unified_client.get("/bizsight/health")
    assert resp.status_code == 200


def test_bizsight_data(unified_client):
    resp = unified_client.get("/bizsight/data")
    assert resp.status_code in (200, 401, 403)


def test_bizsight_api_states(unified_client):
    resp = unified_client.get("/bizsight/api/states")
    assert resp.status_code in (200, 401, 403)


def test_bizsight_api_planning_regions(unified_client):
    """Verifies the ported /api/planning-regions endpoint is reachable."""
    resp = unified_client.get("/bizsight/api/planning-regions")
    assert resp.status_code in (200, 401, 403)
