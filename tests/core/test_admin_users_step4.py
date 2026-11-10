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

def test_user_list_shows_the_tester_check_and_firebase_flags(admin_client, directory):
    body = admin_client.get("/api/auth/users").get_json()
    by_uid = {u["uid"]: u for u in body["users"]}

    tester = by_uid["u-tester"]
    assert tester["testerAccess"] == {"authorized": True, "reason": ta.AUTHORIZED,
                                      "checkedAt": CHECKED.isoformat()}
    # Firebase's flag wins over the stale Firestore copy
    assert tester["emailVerified"] is True
    assert tester["providerData"] == ["password"]

    plain = by_uid["u-plain"]
    assert plain["testerAccess"] is None
    assert plain["emailVerified"] is False
    assert plain["providerData"] == ["google.com", "password"]


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


def test_admin_page_takes_its_roles_from_the_server_list(admin_client, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "production")
    page = admin_client.get("/admin/users").get_data(as_text=True)
    assert "const VALID_USER_TYPES = [" in page
    for role in VALID_USER_TYPES:
        assert f'"{role}"' in page
    assert "admin-users-access.js" in page
    assert 'href="/admin/sign-in-refusals"' in page
    # No hand-written role options left in the page
    assert '<option value="staff">' not in page


# ---------------------------------------------------------------------------
# Refused sign-ins
# ---------------------------------------------------------------------------

def test_refusals_page_lists_uid_time_and_reason_without_email(admin_client, monkeypatch):
    rows = [{"refused_at": CHECKED, "uid": "uid-refused-1", "reason": ta.NOT_AUTHORIZED, "source": "hubspot_api"},
            {"refused_at": CHECKED, "uid": "uid-refused-2", "reason": ta.NO_CONTACT, "source": "hubspot_api"}]
    monkeypatch.setattr(ta, "recent_refusals", lambda limit=ta.REFUSALS_SHOWN: rows)
    page = admin_client.get("/admin/sign-in-refusals").get_data(as_text=True)
    assert "uid-refused-1" in page and "uid-refused-2" in page
    assert "Box not ticked" in page and "No HubSpot contact" in page
    assert "2026-11-10 15:00" in page
    assert "@" not in page.split('id="signinRefusals"')[1].split("</section>")[0].replace("mailto:", "")


def test_refusals_page_with_nothing_logged(admin_client, monkeypatch):
    monkeypatch.setattr(ta, "recent_refusals", lambda limit=ta.REFUSALS_SHOWN: [])
    page = admin_client.get("/admin/sign-in-refusals").get_data(as_text=True)
    assert "No refused sign-ins are logged on this deploy." in page


@pytest.mark.parametrize("role", ["staff", "senior_executive", "tester", "public_registered"])
def test_refusals_page_is_admin_only(unified_client, monkeypatch, role):
    monkeypatch.setattr(ta, "recent_refusals", lambda limit=ta.REFUSALS_SHOWN: [
        {"refused_at": CHECKED, "uid": "secret-uid", "reason": ta.NO_CONTACT, "source": "x"}])
    with unified_client.session_transaction() as sess:
        sess["user_type"] = role
        sess["firebase_user"] = {"uid": "u", "email": "u@example.org", "email_verified": True}
    page = unified_client.get("/admin/sign-in-refusals").get_data(as_text=True)
    assert "secret-uid" not in page


def test_recent_refusals_reads_newest_first_from_the_env_table(monkeypatch):
    captured = SimpleNamespace(sql=None, limit=None)

    class FakeClient:
        def query(self, sql, job_config):
            captured.sql = sql
            captured.limit = job_config.query_parameters[0].value
            return SimpleNamespace(result=lambda: [
                {"refused_at": CHECKED, "uid": "u1", "reason": ta.NO_CONTACT, "source": "hubspot_api"}])

    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    monkeypatch.setattr("justdata.shared.utils.bigquery_client.get_bigquery_client",
                        lambda project_id=None, app_name=None: FakeClient())
    rows = ta.recent_refusals(limit=50)
    assert "cache_testing.signin_refusals" in captured.sql
    assert "ORDER BY refused_at DESC" in captured.sql
    assert captured.limit == 50
    assert rows == [{"refused_at": CHECKED, "uid": "u1", "reason": ta.NO_CONTACT, "source": "hubspot_api"}]
    assert "email" not in captured.sql


def test_recent_refusals_is_empty_before_the_first_refusal(monkeypatch):
    from google.api_core.exceptions import NotFound

    class MissingTable:
        def query(self, sql, job_config):
            raise NotFound("table not found")

    monkeypatch.setattr("justdata.shared.utils.bigquery_client.get_bigquery_client",
                        lambda project_id=None, app_name=None: MissingTable())
    assert ta.recent_refusals() == []
