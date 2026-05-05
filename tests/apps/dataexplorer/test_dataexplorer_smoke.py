"""Smoke tests for dataexplorer blueprint."""


def test_dataexplorer_index(unified_client):
    resp = unified_client.get("/dataexplorer/")
    assert resp.status_code in (200, 302, 401, 403)


def test_dataexplorer_health(unified_client):
    resp = unified_client.get("/dataexplorer/health")
    assert resp.status_code == 200


def test_dataexplorer_wizard(unified_client):
    resp = unified_client.get("/dataexplorer/wizard")
    assert resp.status_code in (200, 302, 401, 403)


def test_dataexplorer_api_states(unified_client):
    resp = unified_client.get("/dataexplorer/api/states")
    assert resp.status_code in (200, 401, 403)


def test_dataexplorer_api_metros(unified_client):
    resp = unified_client.get("/dataexplorer/api/metros")
    assert resp.status_code in (200, 401, 403)


def test_dataexplorer_api_search_lender(unified_client):
    """Ported /api/search-lender is POST; GET should not 500."""
    resp = unified_client.get("/dataexplorer/api/search-lender")
    assert resp.status_code in (200, 400, 401, 403, 405)


def test_dataexplorer_api_config_data_types(unified_client):
    """Verifies the ported /api/config/data-types endpoint is reachable."""
    resp = unified_client.get("/dataexplorer/api/config/data-types")
    assert resp.status_code in (200, 401, 403)
