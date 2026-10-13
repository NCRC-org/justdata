"""BranchSight Geography Context: Census tract data served by the server
(the Census API requires a key, so the former browser calls never worked)."""

import pytest


@pytest.fixture
def client():
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return c


def test_route_returns_tract_context(client, monkeypatch):
    import justdata.apps.branchsight.blueprint as bp
    ctx = {"acs_year": 2022, "lmi_threshold": 40100.8, "groups": {}}
    monkeypatch.setattr(bp, "tract_context", lambda g: ctx)
    assert client.get("/branchsight/geography-context/01085").get_json() == ctx
    assert client.get("/branchsight/geography-context/1085x").status_code == 400


def test_route_error_has_a_reference(client, monkeypatch):
    import justdata.apps.branchsight.blueprint as bp
    def boom(g):
        raise RuntimeError("key=SECRET")
    monkeypatch.setattr(bp, "tract_context", boom)
    resp = client.get("/branchsight/geography-context/01085")
    assert resp.status_code == 502 and "SECRET" not in resp.get_json()["error"]


def test_tract_context_groups(monkeypatch):
    from justdata.apps.branchsight import data_utils
    import requests
    tracts = [["pop", "inc", "race", "white", "state", "county", "tract"],
              ["1000", "30000", "1000", "200", "01", "085", "1"],   # LMI and majority-minority
              ["500", "90000", "500", "100", "01", "085", "2"],     # majority-minority only
              ["400", "20000", "400", "300", "01", "085", "3"],     # LMI only
              ["0", "10000", "0", "0", "01", "085", "4"],           # no population: left out
              ["300", "-666666666", "300", "290", "01", "085", "5"]]  # no income estimate
    county = [["B19113_001E", "state", "county"], ["50000", "01", "085"]]
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return type("R", (), {"json": lambda self: tracts if params["for"] == "tract:*" else county})()
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr("justdata.shared.utils.census_historical_utils._get_census_api_key", lambda: "k")
    data_utils.tract_context.cache_clear()
    out = data_utils.tract_context("01085")
    g = out["groups"]
    assert out["lmi_threshold"] == 40000
    assert g["all"] == {"tracts": 4, "population": 2200}
    assert g["both"]["tracts"] == 1 and g["mmct_only"]["tracts"] == 1 and g["lmi_only"]["tracts"] == 1
    assert all(p["key"] == "k" for p in calls)
