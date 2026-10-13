"""BranchSight Geography Context: tract counts from the FFIEC census data,
on the same LMI and majority-minority definitions as the SOD branch flags."""

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
    ctx = {"ffiec_year": 2025, "groups": {}}
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


def test_tract_context_uses_the_branch_flag_definitions(monkeypatch):
    """LMI is FFIEC income level 1 or 2; majority-minority is 50% or more (the
    SOD flags count 50.0% tracts as majority-minority)."""
    from types import SimpleNamespace as Row
    from justdata.apps.branchsight import data_utils
    rows = [Row(year="2025", income_level=1, minority_population=80.0, total_persons=1000),  # both
            Row(year="2025", income_level=3, minority_population=50.0, total_persons=500),   # majority-minority only
            Row(year="2025", income_level=2, minority_population=49.9, total_persons=400),   # LMI only
            Row(year="2025", income_level=4, minority_population=10.0, total_persons=300),   # neither
            Row(year="2025", income_level=0, minority_population=None, total_persons=200),   # income unknown: neither
            Row(year="2025", income_level=1, minority_population=90.0, total_persons=0)]     # no population: left out
    seen = {}

    class Client:
        def query(self, sql, job_config=None):
            seen["sql"], seen["params"] = sql, job_config.query_parameters
            return type("J", (), {"result": lambda self: rows})()
    monkeypatch.setattr(data_utils, "get_bigquery_client", lambda *a, **k: Client())
    data_utils.tract_context.cache_clear()
    out = data_utils.tract_context("01085")
    g = out["groups"]
    assert out["ffiec_year"] == 2025
    assert g["all"] == {"tracts": 5, "population": 2400}
    assert g["both"] == {"tracts": 1, "population": 1000}
    assert g["mmct_only"] == {"tracts": 1, "population": 500}
    assert g["lmi_only"] == {"tracts": 1, "population": 400}
    assert "shared.census" in seen["sql"] and seen["params"][0].value == "01085"
