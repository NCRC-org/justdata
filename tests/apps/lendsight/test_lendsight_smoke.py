"""Smoke tests for lendsight blueprint."""


def test_lendsight_index(unified_client):
    resp = unified_client.get("/lendsight/")
    assert resp.status_code in (200, 302, 401, 403)


def test_lendsight_health(unified_client):
    resp = unified_client.get("/lendsight/health")
    assert resp.status_code == 200


def test_lendsight_counties(unified_client):
    resp = unified_client.get("/lendsight/counties")
    assert resp.status_code in (200, 401, 403)


def test_lendsight_states(unified_client):
    resp = unified_client.get("/lendsight/states")
    assert resp.status_code in (200, 401, 403)


def test_lendsight_years(unified_client):
    resp = unified_client.get("/lendsight/years")
    assert resp.status_code in (200, 401, 403)
