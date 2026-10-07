"""member_request_status(): the one lookup behind /api/auth/member-request/status and /apps."""

import pytest

import justdata.main.auth.services.membership as membership


@pytest.mark.parametrize("doc,expected", [
    ({"userType": "member"}, "member"),
    ({"userType": "public_registered", "hubspot_membership_status": " pending "}, "pending"),
    ({"userType": "public_registered", "hubspot_membership_status": "DENIED"}, "denied"),
    ({"userType": "public_registered", "hubspot_membership_status": "EXPIRED"}, "denied"),
    ({"userType": "public_registered"}, "unknown"),
])
def test_status_from_user_doc(monkeypatch, doc, expected):
    monkeypatch.setattr(membership, "get_firestore_client", lambda: object())
    monkeypatch.setattr(membership, "get_user_doc", lambda uid: doc)
    assert membership.member_request_status("uid-1") == (expected, doc)


def test_unknown_without_uid_client_doc_or_on_error(monkeypatch):
    assert membership.member_request_status(None) == ("unknown", None)
    monkeypatch.setattr(membership, "get_firestore_client", lambda: None)
    assert membership.member_request_status("uid-1") == ("unknown", None)
    monkeypatch.setattr(membership, "get_firestore_client", lambda: object())
    monkeypatch.setattr(membership, "get_user_doc", lambda uid: None)
    assert membership.member_request_status("uid-1") == ("unknown", None)

    def boom(uid):
        raise RuntimeError("firestore down")
    monkeypatch.setattr(membership, "get_user_doc", boom)
    assert membership.member_request_status("uid-1") == ("unknown", None)
