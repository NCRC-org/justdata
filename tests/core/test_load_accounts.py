"""Spec 10 load-test accounts: create and remove (justdata/main/auth/services/load_accounts.py).

Everything runs against fakes; nothing here touches Firebase, Firestore,
BigQuery or HubSpot. The real scripts are dry runs unless --apply.
"""

import json
import os
import stat
from types import SimpleNamespace

import pytest

from justdata.main.auth.services import load_accounts as la

READY = {"exists": True, "id": "hs-1", "ticked": True, "marketable": False}


class FakeAuth:
    class UserNotFoundError(Exception):
        pass

    def __init__(self, users=()):
        self.users = {u.email: u for u in users}
        self.created, self.claims, self.deleted = [], {}, []

    def get_user_by_email(self, email):
        if email not in self.users:
            raise self.UserNotFoundError(email)
        return self.users[email]

    def create_user(self, email, password, email_verified, display_name):
        user = SimpleNamespace(uid=f"uid-{email[:10]}", email=email, custom_claims=None)
        self.created.append({"email": email, "password": password, "email_verified": email_verified,
                             "display_name": display_name})
        self.users[email] = user
        return user

    def set_custom_user_claims(self, uid, claims):
        self.claims[uid] = claims

    def list_users(self):
        return SimpleNamespace(users=list(self.users.values()), get_next_page=lambda: None)

    def delete_user(self, uid):
        self.deleted.append(uid)


class FakeDb:
    def __init__(self, activity=None):
        self.sets, self.deletes, self.activity = {}, [], activity or {}

    def collection(self, name):
        db = self

        class Ref:
            def document(self, uid):
                return SimpleNamespace(set=lambda data: db.sets.__setitem__(uid, data),
                                       delete=lambda: db.deletes.append((name, uid)))

            def where(self, field, op, value):
                rows = db.activity.get(value, [])
                return SimpleNamespace(stream=lambda: [
                    SimpleNamespace(reference=SimpleNamespace(delete=lambda r=r: db.deletes.append(("activity", r))))
                    for r in rows])
        return Ref()


class FakeBq:
    def __init__(self, fail=False):
        self.sql, self.fail = [], fail

    def delete_rows(self, sql, uids):
        if self.fail:
            raise RuntimeError("streaming buffer")
        self.sql.append((sql, list(uids)))


def _load_user(n, claim=True):
    return SimpleNamespace(uid=f"load-{n}", email=f"jd-load-{n:02d}@example.org",
                           custom_claims={la.CLAIM: True} if claim else None)


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------

def test_twenty_addresses_on_example_org():
    addresses = la.load_addresses()
    assert len(addresses) == 20
    assert addresses[0] == "jd-load-01@example.org" and addresses[-1] == "jd-load-20@example.org"
    assert all(la.is_load_address(a) for a in addresses)


@pytest.mark.parametrize("email", ["someone@ncrc.org", "jd-load-01@ncrc.org", "jd-load-1@example.org",
                                   "xjd-load-01@example.org", "jd-load-01@example.org.evil", None, ""])
def test_other_addresses_are_not_load_addresses(email):
    assert not la.is_load_address(email)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def test_dry_run_creates_nothing(tmp_path):
    auth, db, lines = FakeAuth(), FakeDb(), []
    problems = la.create(auth, db, apply=False, password_file=str(tmp_path / "pw.json"),
                         lookup=lambda e: READY, out=lines.append)
    assert problems == 0
    assert auth.created == [] and db.sets == {} and auth.claims == {}
    assert not (tmp_path / "pw.json").exists()
    assert len(lines) == 20 and all("would create" in line for line in lines)


def test_apply_creates_verified_tagged_accounts_and_keeps_passwords_private(tmp_path):
    auth, db, lines = FakeAuth(), FakeDb(), []
    path = tmp_path / "pw.json"
    problems = la.create(auth, db, addresses=la.load_addresses(2), apply=True, password_file=str(path),
                         lookup=lambda e: READY, out=lines.append)
    assert problems == 0
    assert [c["email"] for c in auth.created] == la.load_addresses(2)
    assert all(c["email_verified"] for c in auth.created)
    assert all(claims == {la.CLAIM: True} for claims in auth.claims.values())
    for record in db.sets.values():
        assert record["loadAccount"] is True and record["userType"] == "public_registered"
    saved = json.loads(path.read_text())
    assert set(saved) == set(la.load_addresses(2))
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    # Passwords are never printed
    assert not any(pw in line for pw in saved.values() for line in lines)


@pytest.mark.parametrize("contact, reason", [
    ({"exists": False}, "no HubSpot contact"),
    ({**READY, "ticked": False}, "tester box not ticked"),
    ({**READY, "marketable": True}, "still a marketing contact"),
    ({"error": "HUBSPOT_ACCESS_TOKEN not set"}, "HUBSPOT_ACCESS_TOKEN not set"),
])
def test_contact_not_ready_blocks_creation(tmp_path, contact, reason):
    auth, lines = FakeAuth(), []
    problems = la.create(auth, FakeDb(), addresses=la.load_addresses(1), apply=True,
                         password_file=str(tmp_path / "pw.json"), lookup=lambda e: contact, out=lines.append)
    assert problems == 1 and auth.created == []
    assert reason in lines[0]


def test_existing_untagged_account_is_never_touched(tmp_path):
    real = SimpleNamespace(uid="real", email="jd-load-01@example.org", custom_claims=None)
    auth, db = FakeAuth([real]), FakeDb()
    problems = la.create(auth, db, addresses=la.load_addresses(1), apply=True,
                         password_file=str(tmp_path / "pw.json"), lookup=lambda e: READY, out=lambda s: None)
    assert problems == 1 and auth.created == [] and db.sets == {} and auth.claims == {}


def test_rerun_skips_accounts_already_made(tmp_path):
    auth = FakeAuth([_load_user(1)])
    lines = []
    la.create(auth, FakeDb(), addresses=la.load_addresses(1), apply=True,
              password_file=str(tmp_path / "pw.json"), lookup=lambda e: READY, out=lines.append)
    assert auth.created == [] and "already a load account" in lines[0]


def test_non_load_address_refused(tmp_path):
    auth = FakeAuth()
    problems = la.create(auth, FakeDb(), addresses=["someone@ncrc.org"], apply=True,
                         password_file=str(tmp_path / "pw.json"), lookup=lambda e: READY, out=lambda s: None)
    assert problems == 1 and auth.created == []


# ---------------------------------------------------------------------------
# Find and remove
# ---------------------------------------------------------------------------

def test_find_needs_both_the_claim_and_the_address():
    stray_claim = SimpleNamespace(uid="x", email="someone@ncrc.org", custom_claims={la.CLAIM: True})
    untagged = _load_user(2, claim=False)
    auth = FakeAuth([_load_user(1), stray_claim, untagged])
    assert [u.uid for u in la.find_load_accounts(auth)] == ["load-1"]


def test_remove_dry_run_changes_nothing():
    auth, db, bq, lines = FakeAuth([_load_user(1)]), FakeDb({"load-1": ["a1", "a2"]}), FakeBq(), []
    problems = la.remove(auth, db, bq, "proj", apply=False, lookup=lambda e: READY, out=lines.append)
    assert problems == 0
    assert bq.sql == [] and db.deletes == [] and auth.deleted == []
    assert any("2 activity row(s)" in line and "archive HubSpot contact hs-1" in line for line in lines)


def test_remove_apply_clears_every_store_by_uid():
    auth = FakeAuth([_load_user(1), _load_user(2)])
    db, bq = FakeDb({"load-1": ["a1"]}), FakeBq()
    archived = []
    http = SimpleNamespace(delete=lambda url, headers, timeout: (archived.append(url), SimpleNamespace(status_code=204))[1])
    problems = la.remove(auth, db, bq, "proj", apply=True, http=http, lookup=lambda e: READY, out=lambda s: None)
    assert problems == 0
    assert [s for s, _ in bq.sql] == [
        "DELETE FROM `proj.cache_testing.usage_log` WHERE user_id IN UNNEST(@uids)",
        "DELETE FROM `proj.cache_testing.signin_refusals` WHERE uid IN UNNEST(@uids)",
    ]
    assert all(uids == ["load-1", "load-2"] for _, uids in bq.sql)
    assert ("activity", "a1") in db.deletes
    assert ("users", "load-1") in db.deletes and ("users", "load-2") in db.deletes
    assert auth.deleted == ["load-1", "load-2"]
    assert len(archived) == 2


def test_marketing_contact_is_left_for_a_person():
    auth, http_calls = FakeAuth([_load_user(1)]), []
    http = SimpleNamespace(delete=lambda *a, **k: http_calls.append(a))
    problems = la.remove(auth, FakeDb(), FakeBq(), "proj", apply=True, http=http,
                         lookup=lambda e: {**READY, "marketable": True}, out=lambda s: None)
    assert problems == 1 and http_calls == []
    assert auth.deleted == ["load-1"]  # the JustData side is still removed


def test_bigquery_failure_is_reported_not_fatal():
    auth = FakeAuth([_load_user(1)])
    problems = la.remove(auth, FakeDb(), FakeBq(fail=True), "proj", apply=True,
                         http=SimpleNamespace(delete=lambda *a, **k: SimpleNamespace(status_code=204)),
                         lookup=lambda e: READY, out=lambda s: None)
    assert problems == 2 and auth.deleted == ["load-1"]


def test_nothing_found_is_a_clean_no_op():
    lines = []
    assert la.remove(FakeAuth(), FakeDb(), FakeBq(), "proj", apply=True, out=lines.append) == 0
    assert lines == ["Found 0 load account(s)"]


# ---------------------------------------------------------------------------
# HubSpot read
# ---------------------------------------------------------------------------

def _http_get(status, props=None):
    return SimpleNamespace(get=lambda url, headers, timeout, params: SimpleNamespace(
        status_code=status, json=lambda: {"id": "hs-9", "properties": props or {}}))


@pytest.mark.parametrize("marketable_value, expected", [("false", False), ("true", True), ("", True), (None, True)])
def test_only_an_explicit_false_counts_as_non_marketing(monkeypatch, marketable_value, expected):
    monkeypatch.setenv(la.TOKEN_ENV, "t")
    props = {"justdata_tester_authorized": "true", "hs_marketable_status": marketable_value}
    contact = la.hubspot_contact("jd-load-01@example.org", http=_http_get(200, props))
    assert contact["exists"] and contact["ticked"] and contact["marketable"] is expected


def test_hubspot_missing_contact_and_missing_token(monkeypatch):
    monkeypatch.setenv(la.TOKEN_ENV, "t")
    assert la.hubspot_contact("jd-load-01@example.org", http=_http_get(404)) == {"exists": False}
    monkeypatch.delenv(la.TOKEN_ENV)
    assert "error" in la.hubspot_contact("jd-load-01@example.org", http=_http_get(200))
