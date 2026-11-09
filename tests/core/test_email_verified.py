"""POST /api/auth/email-verified grants staff only on Firebase's own flag.

It trusted the caller: any signed-in @ncrc.org password account that posted
to it became staff, verified or not. It now reads email_verified from the
Firebase user record and changes nothing when the flag is false.
"""

from types import SimpleNamespace

import pytest

from justdata.main.auth.routes import login

URL = "/api/auth/email-verified"


class _FakeDoc:
    def __init__(self, writes):
        self._writes = writes

    def update(self, data):
        self._writes.append(data)


class _FakeDb:
    def __init__(self):
        self.writes = []

    def collection(self, name):
        return self

    def document(self, uid):
        return _FakeDoc(self.writes)


@pytest.fixture
def fake_db(monkeypatch):
    db = _FakeDb()
    monkeypatch.setattr(login, "get_firebase_app", lambda: object())
    monkeypatch.setattr(login, "get_firestore_client", lambda: db)
    monkeypatch.setattr(login, "log_activity", lambda *a, **k: None)
    return db


def _firebase_says(monkeypatch, verified, email="new-signup@ncrc.org"):
    record = SimpleNamespace(email_verified=verified, email=email)
    monkeypatch.setattr(login.firebase_auth, "get_user", lambda uid: record)


def _signed_in(client, email="new-signup@ncrc.org"):
    with client.session_transaction() as sess:
        sess["firebase_user"] = {"uid": "test-signup", "email": email,
                                 "provider": "password", "email_verified": False}
        sess["user_type"] = "public_registered"


def test_unverified_ncrc_signup_is_refused(unified_client, fake_db, monkeypatch):
    _firebase_says(monkeypatch, verified=False)
    _signed_in(unified_client)

    resp = unified_client.post(URL)

    assert resp.status_code == 403
    assert resp.get_json()["email_verified"] is False
    assert fake_db.writes == []
    with unified_client.session_transaction() as sess:
        assert sess["user_type"] == "public_registered"


def test_verified_ncrc_signup_becomes_staff(unified_client, fake_db, monkeypatch):
    _firebase_says(monkeypatch, verified=True)
    _signed_in(unified_client)

    resp = unified_client.post(URL)

    assert resp.status_code == 200
    assert resp.get_json()["user_type"] == "staff"
    assert fake_db.writes[0]["userType"] == "staff"
    assert fake_db.writes[0]["emailVerified"] is True


def test_firebase_email_is_used_over_the_session(unified_client, fake_db, monkeypatch):
    _firebase_says(monkeypatch, verified=True, email="someone@example.com")
    _signed_in(unified_client, email="someone@ncrc.org")

    resp = unified_client.post(URL)

    assert resp.status_code == 200
    assert "userType" not in fake_db.writes[0]


def test_unknown_firebase_user_is_refused(unified_client, fake_db, monkeypatch):
    def missing(uid):
        raise login.firebase_auth.UserNotFoundError("no such user")
    monkeypatch.setattr(login.firebase_auth, "get_user", missing)
    _signed_in(unified_client)

    resp = unified_client.post(URL)

    assert resp.status_code == 401
    assert fake_db.writes == []


def test_signed_out_is_refused(unified_client, fake_db):
    assert unified_client.post(URL).status_code == 401
