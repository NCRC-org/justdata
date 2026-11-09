"""scripts/revoke_elevated_role.py: dry run by default; --apply sets
public_registered, revokes refresh tokens and logs one row with no email."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/revoke_elevated_role.py"
spec = importlib.util.spec_from_file_location("revoke_elevated_role", SCRIPT)
revoke_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(revoke_script)


class FakeDb:
    def __init__(self, user):
        self.user, self.updates, self.rows = user, [], []

    def collection(self, name):
        db = self

        class Collection:
            def document(self, uid):
                return SimpleNamespace(
                    get=lambda: SimpleNamespace(exists=db.user is not None, to_dict=lambda: db.user),
                    update=db.updates.append)

            def add(self, row):
                db.rows.append((name, row))
        return Collection()


auth_state = SimpleNamespace(revoked=[])


@pytest.fixture(autouse=True)
def _reset():
    auth_state.revoked = []


def _fake_auth():
    return SimpleNamespace(revoke_refresh_tokens=lambda uid: auth_state.revoked.append(uid))


def test_dry_run_changes_nothing():
    db = FakeDb({"userType": "staff", "email": "someone@ncrc.org"})
    assert revoke_script.revoke("u1", "audit", "jad", db=db, auth=_fake_auth()) == 0
    assert db.updates == [] and db.rows == [] and auth_state.revoked == []


@pytest.mark.parametrize("role", ["staff", "senior_executive", "admin"])
def test_apply_revokes_and_logs_one_row_without_email(role):
    db = FakeDb({"userType": role, "email": "someone@ncrc.org"})
    assert revoke_script.revoke("u1", "audit", "jad", apply=True, db=db, auth=_fake_auth()) == 0
    assert db.updates[0]["userType"] == "public_registered"
    assert db.updates[0]["roleRevokedFrom"] == role
    assert auth_state.revoked == ["u1"]
    assert len(db.rows) == 1
    name, row = db.rows[0]
    assert name == "activity" and row["action"] == "role_revoked"
    assert row["metadata"] == {"from_role": role, "to_role": "public_registered", "reason": "audit", "by": "jad"}
    assert "email" not in row


@pytest.mark.parametrize("user", [None, {"userType": "member"}, {"userType": "public_registered"}])
def test_refuses_missing_or_non_elevated_users(user):
    db = FakeDb(user)
    assert revoke_script.revoke("u1", "audit", "jad", apply=True, db=db, auth=_fake_auth()) == 1
    assert db.updates == [] and db.rows == [] and auth_state.revoked == []


def test_mask_keeps_one_letter_and_the_domain():
    assert revoke_script.mask("someone@ncrc.org") == "s***@ncrc.org"
    assert revoke_script.mask(None) == "(none)"
