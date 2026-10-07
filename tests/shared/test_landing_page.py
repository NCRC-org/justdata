"""Landing page at "/" (spec 02)."""

import re
from pathlib import Path

import pytest

from justdata.main.landing_content import DATA_INVENTORY, PLATFORM_STATS

PARTIALS = sorted((Path(__file__).resolve().parents[2]
                   / "justdata/shared/web/templates/partials").glob("home_*.html"))
RESTRICTED_MARKER = 'alt="NCRC - National Community Reinvestment Coalition"'


@pytest.fixture
def platform_app():
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


def _home(app, user_type, signed_in=True):
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = user_type
        if signed_in:
            s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    resp = client.get("/")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


@pytest.mark.parametrize("user_type,signed_in,expected,absent", [
    ("public_anonymous", False, ["Sign in", "Create an account"], ["Open the apps", "Request member access"]),
    ("public_registered", True, ["Request member access"], ["Open the apps", "Create an account"]),
    ("member", True, ["Open the apps"], ["Create an account", "Request member access"]),
    ("non_member_org", True, ["Open the apps"], ["Create an account", "Request member access"]),
])
def test_testing_landing_cta_matches_viewer(platform_app, monkeypatch, user_type, signed_in, expected, absent):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    html = _home(platform_app, user_type, signed_in)
    assert RESTRICTED_MARKER not in html
    # The shell header carries its own sign-in and member-request controls,
    # so check the hero's calls to action only.
    hero = re.search(r'<section class="[^"]*home-hero.*?</section>', html, re.S).group(0)
    for text in expected:
        assert text in hero, text
    for text in absent:
        assert text not in hero, text


def test_landing_renders_verified_facts_only(platform_app, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    html = _home(platform_app, "public_anonymous", signed_in=False)
    for row in DATA_INVENTORY:
        assert row["name"] in html and row["vintage"] in html
    for stat in PLATFORM_STATS:
        assert stat["label"] in html
    for dropped in ("100%", "no licensed", "merger applications", "#methodology"):
        assert dropped not in html


def test_landing_roster_counts_what_the_viewer_can_see(platform_app, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    html = _home(platform_app, "public_anonymous", signed_in=False)
    assert "Three tools, one set of public records" in html
    assert html.count('class="home-q"') == 3
    assert "MergerMeter" not in html[html.index('id="home-q-h"'):html.index('id="roster"')]


def test_landing_has_no_icons_and_small_partials():
    for path in PARTIALS:
        text = path.read_text()
        assert "data-lucide" not in text, path.name
        assert not re.search(r"\bfa-", text), path.name
        assert len(text.splitlines()) < 150, path.name
