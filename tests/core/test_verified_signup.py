"""Testing-site sign-up verification (spec 08, build step 3).

On JUSTDATA_ENV=testing a password account must have a verified email
(email_verified in the signed Firebase token) before the tester list is
checked; until then sign-in opens no session and points at /verify-email.
Without this, anyone could sign up with a ticked tester's address they don't
own. Google accounts arrive verified; staff and the other deploys are
unchanged.
"""

from types import SimpleNamespace

import httpx
import pytest

from justdata.main.auth.routes import login
from justdata.main.auth.services import tester_access as ta

EMAIL = "fake.tester@example.org"
UID = "test-verify-uid"


def _ticked():
    request = httpx.Request("GET", "https://api.hubapi.com/x")
    return httpx.Response(200, json={"properties": {ta.TESTER_PROPERTY: "true"}}, request=request)


class FakeDb:
    def collection(self, name):
        return self

    def document(self, uid):
        return self

    def update(self, data):
        pass


@pytest.fixture
def signin(monkeypatch):
    """A sign-in whose contact is ticked; set .verified, .provider, .user_doc."""
    state = SimpleNamespace(verified=False, provider="password", email=EMAIL,
                            user_doc={"userType": "public_registered"},
                            hubspot_calls=0, refusals=[])

    def fake_get(url, params, headers):
        state.hubspot_calls += 1
        return _ticked()

    monkeypatch.setattr(login, "get_firebase_app", lambda: object())
    monkeypatch.setattr(login, "verify_firebase_token", lambda token: {
        "uid": UID, "email": state.email, "email_verified": state.verified,
        "firebase": {"sign_in_provider": state.provider}})
    monkeypatch.setattr(login, "create_or_update_user_doc", lambda **k: dict(state.user_doc))
    monkeypatch.setattr(login, "log_activity", lambda *a, **k: None)
    monkeypatch.setenv(ta.TOKEN_ENV, "test-token")
    monkeypatch.setattr(ta, "_hubspot_get", fake_get)
    monkeypatch.setattr(ta, "get_firestore_client", lambda: FakeDb())
    monkeypatch.setattr(ta, "log_refusal", lambda uid, result: state.refusals.append(result))
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    return state


def _post_login(client):
    return client.post("/api/auth/login", json={"idToken": "t", "user": {}})


def test_unverified_password_account_waits_for_verification(unified_client, signin):
    resp = _post_login(unified_client)

    assert resp.status_code == 403
    body = resp.get_json()
    assert body["code"] == "email_not_verified"
    assert body["redirect"] == "/verify-email"
    with unified_client.session_transaction() as sess:
        assert "firebase_user" not in sess
    # The tester list isn't checked, and nothing goes in the refusal log
    assert signin.hubspot_calls == 0
    assert signin.refusals == []


def test_verified_password_account_goes_on_to_the_tester_check(unified_client, signin):
    signin.verified = True
    resp = _post_login(unified_client)
    assert resp.status_code == 200
    assert resp.get_json()["user_type"] == "tester"
    assert signin.hubspot_calls == 1


def test_unverified_ncrc_password_account_also_waits(unified_client, signin):
    """Unverified @ncrc.org password accounts are public_registered, not staff."""
    signin.email = "someone@ncrc.org"
    resp = _post_login(unified_client)
    assert resp.get_json()["code"] == "email_not_verified"


def test_rule_applies_to_password_accounts_only(unified_client, signin):
    signin.provider = "google.com"
    resp = _post_login(unified_client)
    assert resp.status_code == 200
    assert resp.get_json()["user_type"] == "tester"


def test_staff_skip_the_rule(unified_client, signin):
    signin.user_doc = {"userType": "staff"}
    signin.email = "someone@ncrc.org"
    resp = _post_login(unified_client)
    assert resp.status_code == 200
    assert resp.get_json()["user_type"] == "staff"


def test_no_rule_off_the_testing_site(unified_client, signin, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "production")
    resp = _post_login(unified_client)
    assert resp.status_code == 200
    assert resp.get_json()["user_type"] == "public_registered"
    assert signin.hubspot_calls == 0


@pytest.mark.parametrize("path", ["/verify-email", "/email-verified"])
def test_verify_page_renders_signed_out_on_testing(unified_client, monkeypatch, path):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    resp = unified_client.get(path)
    assert resp.status_code == 200
    page = resp.get_data(as_text=True)
    assert "Verify your email first" in page
    assert 'id="verifyContinueBtn"' in page


def test_email_verified_page_is_unchanged_off_testing(unified_client, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "production")
    with unified_client.session_transaction() as sess:
        sess["user_type"] = "staff"
        sess["firebase_user"] = {"uid": UID, "email": "someone@ncrc.org", "email_verified": True}
    page = unified_client.get("/email-verified").get_data(as_text=True)
    assert "Checking Verification" in page
    assert "Verify your email first" not in page
