"""/account, "Your account" (spec 14, phase 1), and sign out of all devices.

Every role's view on the testing deploy, escaping of the display name, the
profile and sign-out actions, and the session cutoff that signs other devices
out. Firebase, Firestore and BigQuery are faked.
"""
import html
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

import pytest

from justdata.main import account as account_mod
from justdata.main.account import history
from justdata.main.auth import session_revocation

MARKER = b'id="account-h"'
PKG = __import__("pathlib").Path(__file__).resolve().parents[2] / "justdata"
SIGHT = "LendSight, BizSight and BranchSight"


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    """Default fakes: a password account, no user record, no report history."""
    session_revocation._cache.clear()
    state = SimpleNamespace(
        doc={},
        record=SimpleNamespace(display_name="Pat Doe", email="pat@example.org", email_verified=True,
                               provider_data=[SimpleNamespace(provider_id="password")]),
        rows=[],
    )
    monkeypatch.setattr(account_mod, "get_user_doc", lambda uid: state.doc)
    monkeypatch.setattr(account_mod, "_auth_record", lambda uid: state.record)
    monkeypatch.setattr(history, "fetch_rows", lambda uid: state.rows)
    monkeypatch.setattr(session_revocation, "get_firestore_client", lambda: None)
    return state


def _sign_in(client, user_type, uid="acct-uid", signed_in_at=None):
    with client.session_transaction() as sess:
        sess["firebase_user"] = {"uid": uid, "email": "pat@example.org", "name": "Pat Doe",
                                 "email_verified": True, "provider": "password",
                                 "signed_in_at": signed_in_at or int(time.time())}
        sess["user_type"] = user_type


def _page(client, user_type, env="testing", monkeypatch=None):
    if monkeypatch is not None:
        if env:
            monkeypatch.setenv("JUSTDATA_ENV", env)
        else:
            monkeypatch.delenv("JUSTDATA_ENV", raising=False)
    _sign_in(client, user_type)
    return client.get("/account")


# ---------------------------------------------------------------- every role

@pytest.mark.parametrize("user_type,sentence", [
    ("tester", f"You have a JustData tester account. It opens {SIGHT}."),
    ("member", f"You have an NCRC member account. It opens {SIGHT}."),
    ("member_premium", f"You have an NCRC premium member account. It opens {SIGHT}."),
    ("non_member_org", f"You have a partner organization account. It opens {SIGHT}."),
    ("staff", f"You have an NCRC staff account. It opens {SIGHT}."),
    ("senior_executive", f"You have an NCRC senior executive account. It opens {SIGHT}."),
])
def test_each_role_sees_its_access_in_plain_words(unified_client, monkeypatch, user_type, sentence):
    resp = _page(unified_client, user_type, monkeypatch=monkeypatch)
    assert resp.status_code == 200 and MARKER in resp.data
    body = resp.get_data(as_text=True)
    assert sentence in body
    assert 'href="/admin/users">Admin tools' not in body
    for anchor in ("#profile", "#access", "#security", "#reports", "#data"):
        assert f'href="{anchor}"' in body


def test_admin_sees_every_app_and_the_admin_tools_link(unified_client, monkeypatch):
    body = _page(unified_client, "admin", monkeypatch=monkeypatch).get_data(as_text=True)
    assert "You have a JustData administrator account. It opens LendSight, BizSight, BranchSight, " \
           "MergerMeter, Analytics, Administration, BranchMapper, DotLender and DataExplorer." in body
    assert 'href="/admin/users">Admin tools' in body


def test_registered_user_without_apps_is_pointed_to_request_access(unified_client, monkeypatch):
    resp = _page(unified_client, "public_registered", monkeypatch=monkeypatch)
    assert resp.status_code == 200 and MARKER in resp.data
    body = html.unescape(resp.get_data(as_text=True))
    assert "You have a registered account. It doesn't open any apps yet." in body
    assert 'href="/apps#request-access"' in body


def test_signed_out_gets_no_account_page(unified_client, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    resp = unified_client.get("/account")
    assert MARKER not in resp.data


def test_outside_testing_the_staff_gate_still_applies(unified_client, monkeypatch):
    assert MARKER not in _page(unified_client, "member", env=None, monkeypatch=monkeypatch).data
    assert MARKER in _page(unified_client, "staff", env=None, monkeypatch=monkeypatch).data


def test_phase_one_has_no_delete_section_and_no_red(unified_client, monkeypatch):
    body = _page(unified_client, "tester", monkeypatch=monkeypatch).get_data(as_text=True)
    assert "Delete account" not in body and "btn-danger" not in body
    assert "Download my data" not in body and "Remove from my history" not in body
    css = PKG / "shared/web/static/css/account.css"
    text = css.read_text().lower()
    for red in ("--ncrc-red", "#e82e2e", "#a22020", "--color-danger", "--color-error"):
        assert red not in text


# ------------------------------------------------------------- what renders

def test_profile_facts_and_optional_lines(unified_client, monkeypatch, fakes):
    fakes.doc = {"hubspot_company_name": "Example CDFI",
                 "testerAccess": {"authorized": True, "checkedAt": datetime(2026, 11, 20, 15, tzinfo=timezone.utc)}}
    body = _page(unified_client, "tester", monkeypatch=monkeypatch).get_data(as_text=True)
    assert "Example CDFI" in body
    assert "Access last confirmed Nov. 20, 2026." in body
    assert "You sign in with email and password." in body
    assert 'id="accountResetPassword"' in body


def test_lines_without_data_are_left_out(unified_client, monkeypatch, fakes):
    fakes.record = SimpleNamespace(display_name="Pat", email="pat@example.org", email_verified=True,
                                   provider_data=[SimpleNamespace(provider_id="google.com")])
    body = _page(unified_client, "tester", monkeypatch=monkeypatch).get_data(as_text=True)
    assert "<dt>Organization</dt>" not in body         # no HubSpot company on record
    assert "Access last confirmed" not in body          # no check on record
    assert 'id="accountResetPassword"' not in body      # Google account: no password to reset
    assert "Link Microsoft 365" not in body             # hidden until the Entra registration exists
    assert 'id="agreements"' not in body and 'href="#agreements"' not in body


def test_agreements_render_once_the_field_exists(unified_client, monkeypatch, fakes):
    fakes.doc = {"agreements_accepted": {"tester_agreement": {
        "acceptedAt": datetime(2026, 9, 3, 14, tzinfo=timezone.utc)}}}
    body = _page(unified_client, "tester", monkeypatch=monkeypatch).get_data(as_text=True)
    assert "You accepted the tester agreement on Sept. 3, 2026." in body
    assert 'href="#agreements"' in body


def test_report_history_lists_only_runs_that_open(unified_client, monkeypatch, fakes):
    fakes.rows = [
        {"job_id": "job-1", "app_name": "lendsight", "ran_at": datetime(2026, 11, 19, 18, tzinfo=timezone.utc),
         "parameters_json": '{"counties": "Loving County, Texas"}'},
        {"job_id": "job-2", "app_name": "bizsight", "ran_at": datetime(2026, 11, 18, 18, tzinfo=timezone.utc),
         "parameters_json": '{"county_data": {"name": "Baltimore city, Maryland"}}'},
        {"job_id": "job-3", "app_name": "mergermeter", "ran_at": datetime(2026, 11, 17, tzinfo=timezone.utc),
         "parameters_json": "{}"},
    ]
    body = _page(unified_client, "tester", monkeypatch=monkeypatch).get_data(as_text=True)
    assert 'href="/lendsight/report?job_id=job-1"' in body and "Loving County, Texas" in body
    assert 'href="/bizsight/report?job_id=job-2"' in body and "Baltimore city, Maryland" in body
    assert "job-3" not in body                          # testers can't open MergerMeter
    assert "Nov. 19, 2026" in body


def test_history_failure_shows_the_empty_line(unified_client, monkeypatch):
    monkeypatch.setattr(history, "fetch_rows", mock.Mock(side_effect=RuntimeError("bq down")))
    body = _page(unified_client, "tester", monkeypatch=monkeypatch).get_data(as_text=True)
    assert "Reports you run will be listed here." in body


# ----------------------------------------------------------------- escaping

def test_display_name_is_escaped_everywhere_it_is_shown(unified_client, monkeypatch, fakes):
    evil = '<script>alert(1)</script>"><img src=x onerror=alert(2)>'
    fakes.record = SimpleNamespace(display_name=evil, email="pat@example.org", email_verified=True,
                                   provider_data=[])
    fakes.rows = [{"job_id": "j", "app_name": "lendsight", "ran_at": None,
                   "parameters_json": '{"counties": "<b>x</b>"}'}]
    body = _page(unified_client, "tester", monkeypatch=monkeypatch).get_data(as_text=True)
    assert "<script>alert(1)" not in body and "<img src=x" not in body and "<b>x</b>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "&#34;&gt;&lt;img" in body or "&quot;&gt;&lt;img" in body


def test_account_js_sets_text_only():
    js = (PKG / "shared/web/static/js/account.js").read_text()
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js


# ------------------------------------------------------------ profile action

@pytest.mark.parametrize("raw,ok", [
    ("Pat Doe", True), ("  Pat   Doe  ", True), ("Zoë Ñúñez-O'Brien", True),
    ("", False), ("   ", False), ("x" * 81, False), ("Pat\x00Doe", False), ("Pat‮Doe", False), (None, False),
])
def test_display_name_validation(raw, ok):
    name, error = account_mod.clean_display_name(raw)
    assert (error is None) == ok
    if ok:
        assert name == " ".join(raw.split())


def test_saving_the_name_updates_firebase_firestore_and_the_session(unified_client, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    _sign_in(unified_client, "tester")
    db = mock.MagicMock()
    monkeypatch.setattr(account_mod, "get_firestore_client", lambda: db)
    with mock.patch("firebase_admin.auth.update_user") as update:
        resp = unified_client.post("/api/account/profile", json={"display_name": "  Pat   Q. Doe "})
    assert resp.status_code == 200 and resp.get_json()["display_name"] == "Pat Q. Doe"
    update.assert_called_once_with("acct-uid", display_name="Pat Q. Doe")
    db.collection.return_value.document.assert_called_with("acct-uid")
    with unified_client.session_transaction() as sess:
        assert sess["firebase_user"]["name"] == "Pat Q. Doe"


def test_a_bad_name_is_refused_and_nothing_is_written(unified_client, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    _sign_in(unified_client, "tester")
    with mock.patch("firebase_admin.auth.update_user") as update:
        resp = unified_client.post("/api/account/profile", json={"display_name": "x" * 200})
    assert resp.status_code == 400 and not update.called


def test_profile_needs_a_signed_in_user(unified_client, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    with mock.patch("firebase_admin.auth.update_user") as update:
        resp = unified_client.post("/api/account/profile", json={"display_name": "Pat"})
    assert resp.status_code in (401, 403) and not update.called


# ------------------------------------------------- sign out of all devices

class FakeDoc:
    def __init__(self, store, uid):
        self.store, self.uid = store, uid

    def get(self):
        data = self.store.get(self.uid)
        return SimpleNamespace(exists=data is not None, to_dict=lambda: dict(data or {}))

    def set(self, values, merge=False):
        self.store.setdefault(self.uid, {}).update(values)


class FakeDb:
    def __init__(self):
        self.store = {}

    def collection(self, name):
        return SimpleNamespace(document=lambda uid: FakeDoc(self.store, uid))


def test_cutoff_rules(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(session_revocation, "get_firestore_client", lambda: db)
    assert session_revocation.is_revoked("u", 100) is False          # never revoked
    db.store["u"] = {"sessionsRevokedAt": 1000}
    session_revocation._cache.clear()
    assert session_revocation.is_revoked("u", 999) is True
    assert session_revocation.is_revoked("u", 1000) is False
    assert session_revocation.is_revoked("u", None) is True          # session from before this feature


def test_firestore_outage_revokes_nothing(monkeypatch):
    class Broken:
        def collection(self, name):
            raise RuntimeError("down")
    monkeypatch.setattr(session_revocation, "get_firestore_client", lambda: Broken())
    assert session_revocation.is_revoked("u", 1) is False


def test_sign_out_everywhere_ends_this_session_and_older_ones(unified_client, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    db = FakeDb()
    monkeypatch.setattr(session_revocation, "get_firestore_client", lambda: db)
    _sign_in(unified_client, "tester", signed_in_at=int(time.time()) - 600)
    with mock.patch("firebase_admin.auth.revoke_refresh_tokens") as revoke:
        resp = unified_client.post("/api/account/sign-out-everywhere")
    assert resp.status_code == 200 and resp.get_json()["redirect"] == "/"
    revoke.assert_called_once_with("acct-uid")
    assert "sessionsRevokedAt" in db.store["acct-uid"]
    with unified_client.session_transaction() as sess:
        assert "firebase_user" not in sess

    # Another browser still holding a cookie from before the cutoff is signed out.
    _sign_in(unified_client, "tester", signed_in_at=int(time.time()) - 600)
    assert MARKER not in unified_client.get("/account").data
    with unified_client.session_transaction() as sess:
        assert "firebase_user" not in sess

    # A sign-in after the cutoff works.
    _sign_in(unified_client, "tester", signed_in_at=int(time.time()) + 1)
    assert MARKER in unified_client.get("/account").data


def test_login_refuses_a_token_issued_before_the_cutoff(unified_client, monkeypatch):
    from justdata.main.auth.routes import login as login_mod
    db = FakeDb()
    db.store["acct-uid"] = {"sessionsRevokedAt": int(time.time())}
    monkeypatch.setattr(session_revocation, "get_firestore_client", lambda: db)
    monkeypatch.setattr(login_mod, "get_firebase_app", lambda: object())
    monkeypatch.setattr(login_mod, "verify_firebase_token", lambda t: {
        "uid": "acct-uid", "email": "pat@example.org", "iat": int(time.time()) - 3600,
        "email_verified": True, "firebase": {"sign_in_provider": "password"}})
    create = mock.Mock()
    monkeypatch.setattr(login_mod, "create_or_update_user_doc", create)
    resp = unified_client.post("/api/auth/login", json={"idToken": "t", "user": {}})
    assert resp.status_code == 401 and resp.get_json()["code"] == "session_revoked"
    assert not create.called


def test_auth_js_signs_firebase_out_on_session_revoked():
    js = (PKG / "shared/web/static/js/auth.js").read_text()
    block = js[js.index("data.code === 'session_revoked'"):][:300]
    assert "firebaseAuth.signOut()" in block


def test_header_menu_and_drawer_link_to_the_account_page():
    root = PKG / "shared/web/templates/partials"
    assert 'href="/account"' in (root / "_header.html").read_text()
    assert 'href="/account"' in (root / "_nav.html").read_text()
