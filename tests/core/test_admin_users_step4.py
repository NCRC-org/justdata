"""/admin/users for spec 08 (build step 4).

- Each user shows the HubSpot tester check (result and time) and Firebase's
  own providers and emailVerified flag.
- /admin/sign-in-refusals lists signin_refusals rows: time, UID, reason; no email.
- The role editor accepts only VALID_USER_TYPES, the same list the access
  matrix is keyed by.
"""

import typing
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from justdata.main.auth import (
    ACCESS_MATRIX, FEATURE_PERMISSIONS, TIER_PRICING, VALID_USER_TYPES, UserType,
)
from justdata.main.auth.routes import users
from justdata.main.auth.services import tester_access as ta

CHECKED = datetime(2026, 11, 10, 15, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# One role list
# ---------------------------------------------------------------------------

def test_one_role_list_shared_with_the_access_matrix():
    assert list(typing.get_args(UserType)) == VALID_USER_TYPES
    for app, row in ACCESS_MATRIX.items():
        assert set(row) == set(VALID_USER_TYPES), app
    assert set(FEATURE_PERMISSIONS) == set(VALID_USER_TYPES)
    assert set(TIER_PRICING) == set(VALID_USER_TYPES)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeDoc:
    def __init__(self, uid, data):
        self.id, self._data, self.exists = uid, data, data is not None

    def to_dict(self):
        return dict(self._data)


class FakeDb:
    def __init__(self, docs):
        self.docs, self.updates = docs, []

    def collection(self, name):
        db = self

        class Ref:
            def stream(self):
                return [FakeDoc(uid, d) for uid, d in db.docs.items()]

            def where(self, *a, **k):
                return self

            def document(self, uid):
                return SimpleNamespace(
                    get=lambda: FakeDoc(uid, db.docs.get(uid)),
                    update=lambda data: (db.updates.append((uid, data)), db.docs[uid].update(data)))
        return Ref()


def _auth_user(uid, providers, verified):
    return SimpleNamespace(uid=uid, email_verified=verified,
                           provider_data=[SimpleNamespace(provider_id=p) for p in providers])


@pytest.fixture
def admin_client(unified_client):
    with unified_client.session_transaction() as sess:
        sess["user_type"] = "admin"
        sess["firebase_user"] = {"uid": "admin-uid", "email": "admin@example.org", "email_verified": True}
    return unified_client


@pytest.fixture
def directory(monkeypatch):
    docs = {
        "u-tester": {"email": "t@example.org", "userType": "tester", "emailVerified": False,
                     "testerAccess": {"authorized": True, "reason": ta.AUTHORIZED,
                                      "source": "hubspot_api", "checkedAt": CHECKED}},
        "u-plain": {"email": "p@example.org", "userType": "public_registered"},
    }
    db = FakeDb(docs)
    page = SimpleNamespace(users=[_auth_user("u-tester", ["password"], True),
                                  _auth_user("u-plain", ["google.com", "password"], False)],
                           get_next_page=lambda: None)
    monkeypatch.setattr(users, "get_firestore_client", lambda: db)
    monkeypatch.setattr(users, "get_firebase_app", lambda: object())
    monkeypatch.setattr(users.firebase_auth, "list_users", lambda: page)
    return db


# ---------------------------------------------------------------------------
# The user list
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", VALID_USER_TYPES)
def test_role_editor_accepts_every_valid_role(admin_client, directory, role):
    resp = admin_client.put("/api/auth/users/u-plain", json={"userType": role})
    assert resp.status_code == 200
    assert directory.docs["u-plain"]["userType"] == role


@pytest.mark.parametrize("role", ["superuser", "Admin", "", "staff "])
def test_role_editor_refuses_anything_else(admin_client, directory, role):
    resp = admin_client.put("/api/auth/users/u-plain", json={"userType": role})
    assert resp.status_code == 400
    assert resp.get_json()["valid_types"] == VALID_USER_TYPES
    assert directory.updates == []
