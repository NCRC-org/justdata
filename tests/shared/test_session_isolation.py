"""BZ-022: a report never renders from the session, and sign-in and sign-out
clear every app's page state.

Before the fix, /report, /report-data and /download fell back to the job id in
the Flask session. The session is a signed cookie that survived sign-out, so
user B signing in on user A's browser opened A's last report at
/bizsight/report. Now those routes need the job id in the URL, and
clear_app_session() runs on every successful sign-in and every sign-out.
"""

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from justdata.main.auth.session_keys import APP_SESSION_KEYS

APPS = ("bizsight", "lendsight", "branchsight", "mergermeter")
AUTH_KEYS = {"firebase_user", "user_type"}
A_JOB = "jobA0000000000000000000000000001"

# What user A's last run leaves in the session, per app (see each app's
# /analyze), plus the goals calculator's keys.
A_PAGE_STATE = {
    "job_id": A_JOB,
    "county_data": {"geoid5": "24510", "name": "Baltimore city"},
    "counties": "24510",
    "years": "2020,2021,2022,2023,2024",
    "selection_type": "county",
    "loan_purpose": ["purchase"],
    "goals_config": {"x": 1},
    "goals_bank_name": "A Bank",
}


@pytest.fixture
def platform_app(monkeypatch):
    monkeypatch.delenv("JUSTDATA_ENV", raising=False)
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


def _as_user_a(client):
    """User A (admin) signed in, with a finished run in the session."""
    with client.session_transaction() as s:
        s["firebase_user"] = {"uid": "uid-a", "email": "a@example.org", "email_verified": True}
        s["user_type"] = "admin"
        s.update(A_PAGE_STATE)


def _login_as_b(client):
    """POST /api/auth/login for user B with Firebase and Firestore stubbed."""
    decoded = {"uid": "uid-b", "email": "b@example.org", "email_verified": True,
               "firebase": {"sign_in_provider": "google.com"}}
    mod = "justdata.main.auth.routes.login"
    with patch(f"{mod}.get_firebase_app", return_value=object()), \
         patch(f"{mod}.verify_firebase_token", return_value=decoded), \
         patch(f"{mod}.create_or_update_user_doc",
               return_value={"userType": "admin", "organization": "NCRC"}), \
         patch(f"{mod}.log_activity"):
        resp = client.post("/api/auth/login", json={"idToken": "t", "user": {}})
    assert resp.status_code == 200, resp.get_data(as_text=True)


def _page_state(client):
    with client.session_transaction() as s:
        return {k for k in APP_SESSION_KEYS if k in s}


def test_logout_clears_every_app_key(platform_app):
    client = platform_app.test_client()
    _as_user_a(client)
    assert _page_state(client)
    assert client.post("/api/auth/logout").status_code == 200
    with client.session_transaction() as s:
        assert not (set(s.keys()) & (set(APP_SESSION_KEYS) | AUTH_KEYS)), dict(s)


def test_login_clears_every_app_key_without_a_logout(platform_app):
    """B signs in over A's session with no sign-out in between."""
    client = platform_app.test_client()
    _as_user_a(client)
    _login_as_b(client)
    assert _page_state(client) == set()
    with client.session_transaction() as s:
        assert s["firebase_user"]["uid"] == "uid-b"


@pytest.mark.parametrize("app_name", APPS)
@pytest.mark.parametrize("sign_out_first", (True, False))
def test_user_b_on_user_a_browser_gets_the_form(platform_app, app_name, sign_out_first):
    """A runs a report (and maybe signs out); B signs in on the same client and
    opens /<app>/report with no job id: the form, not A's report."""
    client = platform_app.test_client()
    _as_user_a(client)
    if sign_out_first:
        client.post("/api/auth/logout")
    _login_as_b(client)

    resp = client.get(f"/{app_name}/report")
    assert resp.status_code == 302
    assert resp.headers["Location"].rstrip("/").endswith(f"/{app_name}")

    # The form page itself carries no job id.
    form = client.get(f"/{app_name}/").get_data(as_text=True)
    assert A_JOB not in form


@pytest.mark.parametrize("app_name", APPS)
def test_report_without_job_id_redirects_even_with_one_in_session(platform_app, app_name):
    """The session may hold the current job for the in-page flow, but no page
    renders from it."""
    client = platform_app.test_client()
    _as_user_a(client)
    resp = client.get(f"/{app_name}/report")
    assert resp.status_code == 302
    assert resp.headers["Location"].rstrip("/").endswith(f"/{app_name}")
    # A bad id is treated the same way.
    assert client.get(f"/{app_name}/report?job_id=../x").status_code == 302


@pytest.mark.parametrize("app_name", APPS)
@pytest.mark.parametrize("endpoint", ("report-data", "download"))
def test_data_and_download_need_the_job_id_in_the_url(platform_app, app_name, endpoint):
    client = platform_app.test_client()
    _as_user_a(client)
    # Patch the name each route calls, so a lookup of A's session job would show.
    target = ("justdata.apps.mergermeter.mergermeter_ops.ensure_local_excel"
              if app_name == "mergermeter"
              else f"justdata.apps.{app_name}.blueprint.get_analysis_result_by_job_id")
    with patch(target, return_value=None) as lookup:
        resp = client.get(f"/{app_name}/{endpoint}")
    assert resp.status_code == 400, resp.get_data(as_text=True)
    lookup.assert_not_called()


def test_mergermeter_excel_data_needs_the_job_id_in_the_url(platform_app):
    client = platform_app.test_client()
    _as_user_a(client)
    assert client.get("/mergermeter/excel-data").status_code == 400


@pytest.mark.parametrize("role", ("member", "member_premium", "non_member_org", "tester"))
def test_testing_overlay_blocks_tester_roles_from_mergermeter_job_urls(platform_app, monkeypatch, role):
    """BZ-015 stays a design question (any signed-in user with a job URL opens
    that report), but tester roles still cannot open a MergerMeter job URL on
    the testing deploy."""
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    client = platform_app.test_client()
    with client.session_transaction() as s:
        s["firebase_user"] = {"uid": "uid-t", "email": "t@example.org", "email_verified": True}
        s["user_type"] = role
    for path in (f"/mergermeter/report?job_id={A_JOB}",
                 f"/mergermeter/report-data?job_id={A_JOB}",
                 f"/mergermeter/excel-data?job_id={A_JOB}",
                 f"/mergermeter/download?job_id={A_JOB}"):
        resp = client.get(path)
        body = resp.get_data(as_text=True)
        blocked = resp.status_code in (302, 401, 403) or (
            resp.status_code == 200 and 'alt="NCRC - National Community Reinvestment Coalition"' in body)
        assert blocked, f"{role} {path} -> {resp.status_code}"
        assert A_JOB not in body


def test_every_session_key_the_code_writes_is_cleared():
    """A new session key must be added to APP_SESSION_KEYS (or be an auth key),
    or sign-out would leave it behind."""
    root = Path(__file__).resolve().parents[2] / "justdata"
    written = set()
    pattern = re.compile(r"""\bsession\[\s*['"]([A-Za-z0-9_]+)['"]\s*\]\s*=(?!=)""")
    for path in root.rglob("*.py"):
        written |= set(pattern.findall(path.read_text(encoding="utf-8", errors="ignore")))
    missing = written - set(APP_SESSION_KEYS) - AUTH_KEYS
    assert not missing, f"session keys not cleared on sign-in/out: {sorted(missing)}"
