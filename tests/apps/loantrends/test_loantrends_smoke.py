"""Smoke tests for loantrends blueprint."""


def test_loantrends_index(unified_client):
    resp = unified_client.get("/loantrends/")
    assert resp.status_code in (200, 302, 401, 403)


def test_loantrends_dashboard_data(unified_client):
    resp = unified_client.get("/loantrends/api/dashboard-data")
    assert resp.status_code in (200, 401, 403)


def test_loantrends_available_graphs(unified_client):
    resp = unified_client.get("/loantrends/api/available-graphs")
    assert resp.status_code in (200, 401, 403)
