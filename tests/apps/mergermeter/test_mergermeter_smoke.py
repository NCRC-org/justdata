"""Smoke tests for mergermeter blueprint."""


def test_mergermeter_index(unified_client):
    resp = unified_client.get("/mergermeter/")
    assert resp.status_code in (200, 302, 401, 403)


def test_mergermeter_health(unified_client):
    resp = unified_client.get("/mergermeter/health")
    assert resp.status_code == 200


def test_mergermeter_goals_calculator(unified_client):
    resp = unified_client.get("/mergermeter/goals-calculator")
    assert resp.status_code in (200, 302, 401, 403)


def test_mergermeter_api_search_banks(unified_client):
    resp = unified_client.get("/mergermeter/api/search-banks")
    assert resp.status_code in (200, 400, 401, 403)


def test_mergermeter_api_save_goals_config(unified_client):
    """Verifies the ported /api/save-goals-config endpoint is reachable."""
    resp = unified_client.get("/mergermeter/api/save-goals-config")
    assert resp.status_code in (200, 400, 401, 403, 405)
