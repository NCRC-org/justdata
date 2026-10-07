"""BizSight's analysis years come from one place (ticket 13229487819: config
said 2019-2023 while the analysis ran 2020-2024)."""

import re
from pathlib import Path

from justdata.apps.bizsight.config import BizSightConfig

APP = Path(__file__).resolve().parents[3] / "justdata" / "apps" / "bizsight"


def test_config_is_the_five_most_recent_loaded_years():
    assert BizSightConfig.SB_YEARS == list(range(2020, 2025))
    assert BizSightConfig.DEFAULT_YEARS == BizSightConfig.SB_YEARS


def test_bumping_the_latest_year_needs_the_hardcoded_years_handled():
    """core.py, report_builder.py and ai_analysis.py still name 2020 and 2024
    directly. Moving SB_LATEST_YEAR without replacing them would label and
    compute the wrong years, so this pins the two together until they are
    replaced (platform ticket 11535494229)."""
    literal = re.compile(r"\b2024\b")
    still_hardcoded = [f for f in ("core.py", "report_builder.py", "ai_analysis.py")
                       if literal.search((APP / f).read_text())]
    if still_hardcoded:
        assert BizSightConfig.SB_LATEST_YEAR == 2024, (
            f"SB_LATEST_YEAR moved but {still_hardcoded} still hardcode 2024")


def test_default_request_uses_the_config_window(monkeypatch):
    from justdata.main.app import create_app
    import justdata.apps.bizsight.blueprint as bp
    seen = {}
    monkeypatch.setattr(bp, "lookup_cached_analysis", lambda app, params, *a, **k: seen.update(params) or None)
    monkeypatch.setattr(bp, "run_in_background", lambda work, **kw: None)
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    resp = client.post("/bizsight/analyze", json={"county_data": {
        "county_fips": "031", "county_name": "Cook County", "geoid5": "17031",
        "name": "Cook County, Illinois", "state_fips": "17", "state_name": "Illinois"}})
    assert resp.status_code == 200
    assert seen["years"] == ",".join(map(str, BizSightConfig.SB_YEARS))
