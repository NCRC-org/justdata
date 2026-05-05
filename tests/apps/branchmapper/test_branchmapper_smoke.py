"""Smoke tests for branchmapper blueprint."""


def test_branchmapper_index(unified_client):
    resp = unified_client.get("/branchmapper/")
    assert resp.status_code in (200, 302, 401, 403)


def test_branchmapper_health(unified_client):
    resp = unified_client.get("/branchmapper/health")
    assert resp.status_code == 200


def test_branchmapper_counties(unified_client):
    resp = unified_client.get("/branchmapper/counties")
    assert resp.status_code in (200, 401, 403)


def test_branchmapper_states(unified_client):
    resp = unified_client.get("/branchmapper/states")
    assert resp.status_code in (200, 401, 403)


def test_branchmapper_bank_list(unified_client):
    resp = unified_client.get("/branchmapper/api/bank-list")
    assert resp.status_code in (200, 401, 403)
