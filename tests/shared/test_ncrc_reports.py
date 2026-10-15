"""NCRC report links live in one list and every one answers (Workflow 13277128272)."""

import re
from datetime import date
from pathlib import Path

import pytest
import requests

from justdata.shared.ncrc_reports import NCRC_REPORTS

ROOT = Path(__file__).resolve().parents[2]
# Site navigation and the contact source, not report links
NOT_REPORTS = {"https://ncrc.org/membership/", "https://ncrc.org/contact/"}


def _get(url):
    """GET once more after a 5xx, a timeout or a dropped connection, so a
    transient server error does not read as a dead link. A 4xx or a redirect
    is an answer and is not retried."""
    for attempt in (1, 2):
        try:
            resp = requests.get(url, timeout=30, allow_redirects=False,
                                headers={"User-Agent": "NCRC JustData link check"})
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise
            continue
        if resp.status_code < 500 or attempt == 2:
            return resp


@pytest.mark.network
@pytest.mark.parametrize("report", NCRC_REPORTS, ids=lambda r: r.key)
def test_every_report_url_returns_200(report):
    """A direct 200, no redirect: a moved report should be updated in the list."""
    resp = _get(report.url)
    assert resp.status_code == 200, f"{report.key}: {report.url} returned {resp.status_code}"


def test_link_check_retries_a_server_error_once(monkeypatch):
    answers = iter([503, 200])
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return type("R", (), {"status_code": next(answers)})()
    monkeypatch.setattr(requests, "get", fake_get)
    assert _get("https://ncrc.org/x/").status_code == 200 and len(calls) == 2


def test_link_check_does_not_retry_a_missing_page(monkeypatch):
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return type("R", (), {"status_code": 404})()
    monkeypatch.setattr(requests, "get", fake_get)
    assert _get("https://ncrc.org/x/").status_code == 404 and len(calls) == 1


def test_entries_are_complete_and_unique():
    assert len({r.key for r in NCRC_REPORTS}) == len(NCRC_REPORTS)
    assert len({r.url for r in NCRC_REPORTS}) == len(NCRC_REPORTS)
    for r in NCRC_REPORTS:
        assert r.title and r.url.startswith("https://ncrc.org/")
        date.fromisoformat(r.last_checked)


def test_no_report_url_outside_the_list():
    url = re.compile(r"https?://(?:www\.)?ncrc\.org/[A-Za-z0-9_./?=&%-]+")
    stray = []
    for path in (ROOT / "justdata").rglob("*"):
        if path.suffix not in (".py", ".html", ".js") or "electwatch" in path.parts:
            continue
        if path.name == "ncrc_reports.py":
            continue
        for found in url.findall(path.read_text(errors="ignore")):
            if found not in NOT_REPORTS:
                stray.append(f"{path.relative_to(ROOT)}: {found}")
    assert not stray, stray


def test_bizsight_cra_link_comes_from_the_list():
    from justdata.main.app import create_app
    app = create_app()
    with app.test_request_context():
        assert app.jinja_env.globals["ncrc_report_url"]("cra") == "https://ncrc.org/cra/"
