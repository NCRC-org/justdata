"""LendSight analyses the five most recent verified HMDA years (ticket
13229533844: it was pinned to 2020-2024 after 2025 was loaded and verified)."""

from justdata.shared.core import hmda_years


def test_window_follows_latest_hmda_year(monkeypatch):
    from justdata.apps.lendsight.core import analysis_years, parse_web_parameters
    assert analysis_years() == list(range(hmda_years.LATEST_HMDA_YEAR - 4, hmda_years.LATEST_HMDA_YEAR + 1))
    for years_str in ("", "auto", "auto (last 5)", "all"):
        _, years = parse_web_parameters("Cook County, Illinois", years_str)
        assert years == analysis_years(), years_str

    # A future bump moves the window without touching LendSight.
    monkeypatch.setattr(hmda_years, "LATEST_HMDA_YEAR", hmda_years.LATEST_HMDA_YEAR + 1)
    assert analysis_years()[-1] == hmda_years.LATEST_HMDA_YEAR


def test_window_includes_2025_now_that_it_is_verified():
    from justdata.apps.lendsight.core import analysis_years
    assert hmda_years.LATEST_HMDA_YEAR >= 2025
    assert 2025 in analysis_years() and len(analysis_years()) == 5


def test_cache_key_uses_the_resolved_window_not_the_page_years(monkeypatch):
    from justdata.main.app import create_app
    import justdata.apps.lendsight.blueprint as bp
    from justdata.apps.lendsight.core import analysis_years

    seen = {}
    monkeypatch.setattr(bp, "lookup_cached_analysis",
                        lambda app, params, *a, **k: seen.update(params) or None)
    monkeypatch.setattr(bp, "run_in_background", lambda work, **kw: None)
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    resp = client.post("/lendsight/analyze", json={
        "selection_type": "county", "state_code": "17", "loan_purpose": ["purchase"],
        "years": "2018,2019,2020,2021,2022,2023,2024",   # what the old page sent
        "counties": "Cook County, Illinois",
        "counties_data": [{"name": "Cook County, Illinois", "geoid5": "17031",
                           "state_fips": "17", "county_fips": "031"}],
    })
    assert resp.status_code == 200
    assert seen["years"] == ",".join(map(str, analysis_years()))
