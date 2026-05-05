"""Smoke tests for branchsight blueprint."""


def test_branchsight_index(unified_client):
    resp = unified_client.get("/branchsight/")
    assert resp.status_code in (200, 302, 401, 403)


def test_branchsight_health(unified_client):
    resp = unified_client.get("/branchsight/health")
    assert resp.status_code == 200


def test_branchsight_counties(unified_client):
    resp = unified_client.get("/branchsight/counties")
    assert resp.status_code in (200, 401, 403)


def test_branchsight_states(unified_client):
    resp = unified_client.get("/branchsight/states")
    assert resp.status_code in (200, 401, 403)


def test_branchsight_metro_areas(unified_client):
    resp = unified_client.get("/branchsight/metro-areas")
    assert resp.status_code in (200, 401, 403)
