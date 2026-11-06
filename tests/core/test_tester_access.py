"""Testing-site admission (spec 08, build step 2).

On JUSTDATA_ENV=testing a non-staff sign-in is admitted only when the HubSpot
contact for the email has justdata_tester_authorized ticked. The API is
checked live; the BigQuery mirror is the fallback when the API fails. An
admitted public user becomes 'tester', which opens the three Sight apps on
testing and nothing anywhere else. Refusals open no session and are logged by
UID and reason, never email.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from justdata.main.auth import ACCESS_MATRIX, determine_user_type, get_access_row
from justdata.main.auth.access_overlay import TESTER_APPS
from justdata.main.auth.routes import login
from justdata.main.auth.services import tester_access as ta

EMAIL = "fake.tester@example.org"
UID = "test-tester-uid"


# ---------------------------------------------------------------------------
# HubSpot and BigQuery stand-ins
# ---------------------------------------------------------------------------

def _response(status, properties=None):
    request = httpx.Request("GET", "https://api.hubapi.com/x")
    return httpx.Response(status, json={"properties": properties or {}}, request=request)


@pytest.fixture
def hubspot(monkeypatch):
    """Records calls; .reply is what the next call returns (or raises)."""
    state = SimpleNamespace(calls=[], reply=_response(404))

    def fake_get(url, params, headers):
        state.calls.append({"url": url, "params": params, "headers": headers})
        if isinstance(state.reply, Exception):
            raise state.reply
        return state.reply

    monkeypatch.setenv(ta.TOKEN_ENV, "test-token")
    monkeypatch.setattr(ta, "_hubspot_get", fake_get)
    return state


@pytest.fixture
def mirror(monkeypatch):
    """The BigQuery fallback: .rows is returned, or .error is raised."""
    state = SimpleNamespace(calls=0, rows=[], error=None)

    def fake_mirror(email):
        state.calls += 1
        if state.error:
            return ta.AdmissionResult(False, ta.HUBSPOT_UNAVAILABLE, "bigquery_mirror")
        if not state.rows:
            return ta.AdmissionResult(False, ta.NO_CONTACT, "bigquery_mirror")
        ok = ta._ticked(state.rows[0])
        return ta.AdmissionResult(ok, ta.AUTHORIZED if ok else ta.NOT_AUTHORIZED, "bigquery_mirror")

    monkeypatch.setattr(ta, "_lookup_mirror", fake_mirror)
    return state


# ---------------------------------------------------------------------------
# check_tester_access
# ---------------------------------------------------------------------------

def test_ticked_box_is_authorized(hubspot, mirror):
    hubspot.reply = _response(200, {ta.TESTER_PROPERTY: "true"})
    result = ta.check_tester_access(EMAIL)
    assert (result.authorized, result.reason, result.source) == (True, ta.AUTHORIZED, "hubspot_api")
    call = hubspot.calls[0]
    assert call["params"] == {"idProperty": "email", "properties": ta.TESTER_PROPERTY}
    assert call["headers"]["Authorization"] == "Bearer test-token"
    assert mirror.calls == 0


@pytest.mark.parametrize("properties", [{ta.TESTER_PROPERTY: "false"}, {ta.TESTER_PROPERTY: ""},
                                        {ta.TESTER_PROPERTY: None}, {}])
def test_unticked_or_missing_property_is_refused(hubspot, mirror, properties):
    """Contact exists but the box is unticked, empty, or the property doesn't exist."""
    hubspot.reply = _response(200, properties)
    result = ta.check_tester_access(EMAIL)
    assert (result.authorized, result.reason) == (False, ta.NOT_AUTHORIZED)
    assert mirror.calls == 0


def test_no_contact_is_refused(hubspot, mirror):
    hubspot.reply = _response(404)
    result = ta.check_tester_access(EMAIL)
    assert (result.authorized, result.reason) == (False, ta.NO_CONTACT)
    assert mirror.calls == 0


def test_missing_token_refuses_without_calling_hubspot(hubspot, mirror, monkeypatch):
    monkeypatch.delenv(ta.TOKEN_ENV)
    result = ta.check_tester_access(EMAIL)
    assert (result.authorized, result.reason) == (False, ta.TOKEN_MISSING)
    assert hubspot.calls == [] and mirror.calls == 0


@pytest.mark.parametrize("failure", [_response(500), _response(401), httpx.ConnectTimeout("timed out")])
def test_api_failure_falls_back_to_the_mirror(hubspot, mirror, failure):
    hubspot.reply = failure
    mirror.rows = ["true"]
    result = ta.check_tester_access(EMAIL)
    assert (result.authorized, result.source) == (True, "bigquery_mirror")
    assert mirror.calls == 1


def test_api_and_mirror_both_failing_is_refused_as_unavailable(hubspot, mirror):
    hubspot.reply = _response(503)
    mirror.error = True
    result = ta.check_tester_access(EMAIL)
    assert (result.authorized, result.reason) == (False, ta.HUBSPOT_UNAVAILABLE)


def test_mirror_without_the_property_column_is_unavailable(monkeypatch):
    """Today's mirror has no justdata_tester_authorized column, so the query fails."""
    class FailingClient:
        def query(self, *a, **k):
            raise RuntimeError("Unrecognized name: justdata_tester_authorized")

    monkeypatch.setattr("justdata.shared.utils.bigquery_client.get_bigquery_client",
                        lambda **k: FailingClient())
    result = ta._lookup_mirror(EMAIL)
    assert (result.authorized, result.reason) == (False, ta.HUBSPOT_UNAVAILABLE)


# ---------------------------------------------------------------------------
# Reusing a recent authorization
# ---------------------------------------------------------------------------

def _doc(minutes_ago, authorized=True):
    checked = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return {"testerAccess": {"authorized": authorized, "checkedAt": checked}}


def test_recent_authorization_is_reused():
    assert ta.recent_authorization(_doc(5))
    assert not ta.recent_authorization(_doc(20))
    assert not ta.recent_authorization(_doc(5, authorized=False))
    assert not ta.recent_authorization({})


def test_naive_timestamps_read_as_utc():
    naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    assert ta.recent_authorization({"testerAccess": {"authorized": True, "checkedAt": naive}})


# ---------------------------------------------------------------------------
# The login route
# ---------------------------------------------------------------------------

class FakeDb:
    def __init__(self):
        self.updates = []

    def collection(self, name):
        return self

    def document(self, uid):
        return self

    def update(self, data):
        self.updates.append(data)


@pytest.fixture
def signin(monkeypatch):
    """Stub Firebase, Firestore and the refusal log; returns a state object."""
    state = SimpleNamespace(user_doc={"userType": "public_registered"}, provider="password",
                            email=EMAIL, refusals=[], db=FakeDb())
    monkeypatch.setattr(login, "get_firebase_app", lambda: object())
    monkeypatch.setattr(login, "verify_firebase_token", lambda token: {
        "uid": UID, "email": state.email, "email_verified": True,
        "firebase": {"sign_in_provider": state.provider}})
    monkeypatch.setattr(login, "create_or_update_user_doc", lambda **k: dict(state.user_doc))
    monkeypatch.setattr(login, "log_activity", lambda *a, **k: None)
    monkeypatch.setattr(ta, "get_firestore_client", lambda: state.db)
    monkeypatch.setattr(ta, "log_refusal", lambda uid, result: state.refusals.append((uid, result)))
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    return state


def _post_login(client):
    return client.post("/api/auth/login", json={"idToken": "t", "user": {}})


def test_refused_signin_opens_no_session(unified_client, signin, hubspot, mirror):
    hubspot.reply = _response(200, {ta.TESTER_PROPERTY: "false"})
    resp = _post_login(unified_client)

    assert resp.status_code == 403
    body = resp.get_json()
    assert body["code"] == "tester_not_authorized"
    assert body["redirect"] == "/access-refused?reason=not_listed"
    with unified_client.session_transaction() as sess:
        assert "firebase_user" not in sess
    uid, result = signin.refusals[0]
    assert uid == UID and result.reason == ta.NOT_AUTHORIZED
    recorded = signin.db.updates[0]["testerAccess"]
    assert recorded["authorized"] is False and recorded["reason"] == ta.NOT_AUTHORIZED
    assert "userType" not in signin.db.updates[0]


def test_missing_token_refuses_with_the_unavailable_message(unified_client, signin, hubspot, mirror, monkeypatch):
    monkeypatch.delenv(ta.TOKEN_ENV)
    resp = _post_login(unified_client)
    assert resp.status_code == 403
    assert resp.get_json()["reason"] == "unavailable"
    assert signin.refusals[0][1].reason == ta.TOKEN_MISSING


def test_admitted_public_user_becomes_tester(unified_client, signin, hubspot, mirror):
    hubspot.reply = _response(200, {ta.TESTER_PROPERTY: "true"})
    resp = _post_login(unified_client)

    assert resp.status_code == 200
    assert resp.get_json()["user_type"] == "tester"
    with unified_client.session_transaction() as sess:
        assert sess["user_type"] == "tester"
    assert signin.db.updates[0]["userType"] == "tester"
    assert signin.db.updates[0]["testerAccess"]["authorized"] is True
    assert signin.refusals == []


def test_admitted_member_keeps_member(unified_client, signin, hubspot, mirror):
    """Firestore users is shared with production: never downgrade a member."""
    signin.user_doc = {"userType": "member"}
    hubspot.reply = _response(200, {ta.TESTER_PROPERTY: "true"})
    resp = _post_login(unified_client)
    assert resp.get_json()["user_type"] == "member"
    assert "userType" not in signin.db.updates[0]


def test_unticked_member_is_refused(unified_client, signin, hubspot, mirror):
    signin.user_doc = {"userType": "member"}
    hubspot.reply = _response(200, {ta.TESTER_PROPERTY: "false"})
    assert _post_login(unified_client).status_code == 403


def test_recent_authorization_skips_hubspot_and_keeps_its_timestamp(unified_client, signin, hubspot, mirror):
    signin.user_doc = {"userType": "tester", **_doc(5)}
    resp = _post_login(unified_client)
    assert resp.get_json()["user_type"] == "tester"
    assert hubspot.calls == []
    assert signin.db.updates == []


def test_staff_skip_the_check(unified_client, signin, hubspot, mirror):
    signin.user_doc = {"userType": "staff"}
    signin.email = "someone@ncrc.org"
    resp = _post_login(unified_client)
    assert resp.status_code == 200
    assert resp.get_json()["user_type"] == "staff"
    assert hubspot.calls == []


def test_no_check_off_the_testing_site(unified_client, signin, hubspot, mirror, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "production")
    resp = _post_login(unified_client)
    assert resp.status_code == 200
    assert resp.get_json()["user_type"] == "public_registered"
    assert hubspot.calls == []


# ---------------------------------------------------------------------------
# The tester role
# ---------------------------------------------------------------------------

def test_tester_has_public_registered_access_off_testing(monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "production")
    for app in ACCESS_MATRIX:
        assert get_access_row(app)["tester"] == get_access_row(app)["public_registered"], app


def test_tester_opens_only_the_sight_apps_on_testing(monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    for app in ACCESS_MATRIX:
        expected = "full" if app in TESTER_APPS else "hidden"
        assert get_access_row(app)["tester"] == expected, app


def test_tester_type_is_kept_at_signin():
    assert determine_user_type(EMAIL, True, current_type="tester", auth_provider="password") == "tester"


# ---------------------------------------------------------------------------
# The refusal page
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reason, heading", [("not_listed", "not on the tester list"),
                                             ("unavailable", "couldn't check the tester list"),
                                             ("anything-else", "not on the tester list")])
def test_refusal_page_renders_signed_out_on_testing(unified_client, monkeypatch, reason, heading):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    resp = unified_client.get(f"/access-refused?reason={reason}")
    assert resp.status_code == 200
    assert heading in resp.get_data(as_text=True).replace("&#39;", "'")


# ---------------------------------------------------------------------------
# The refusal log
# ---------------------------------------------------------------------------

def test_refusal_log_holds_uid_and_reason_only_with_90_day_partitions(monkeypatch):
    captured = SimpleNamespace(table=None, rows=None)

    class FakeClient:
        def create_table(self, table, exists_ok):
            captured.table = table

        def insert_rows_json(self, table_id, rows):
            captured.table_id, captured.rows = table_id, rows
            return []

    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    monkeypatch.setattr(ta, "_refusal_table_ready", False)
    monkeypatch.setattr("justdata.shared.utils.bigquery_client.get_bigquery_client",
                        lambda **k: FakeClient())
    ta.log_refusal(UID, ta.AdmissionResult(False, ta.NOT_AUTHORIZED, "hubspot_api"))

    assert captured.table_id.endswith(".cache_testing.signin_refusals")
    assert captured.table.time_partitioning.expiration_ms == 90 * 24 * 60 * 60 * 1000
    row = captured.rows[0]
    assert set(row) == {"refused_at", "uid", "reason", "source"}
    assert row["uid"] == UID and row["reason"] == ta.NOT_AUTHORIZED
    assert EMAIL not in str(row)
