"""/contact?ref= (spec 04 decision 5, Jad 2026-10-07).

An app's error state links "Report a problem" to /contact?ref=<id>. The page
shows the reference above the form and includes it in the email the form
builds. The form has no mail backend, so it must not claim a message was sent.
"""

import pytest


@pytest.fixture
def client():
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    # /contact is public only on the testing deploy; locally the gate admits staff.
    with client.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return client


def test_reference_shown_and_carried_into_the_form(client):
    html = client.get("/contact?ref=ab12cd34").get_data(as_text=True)
    assert 'id="contactRef">Reference: <span>ab12cd34</span>' in html
    assert 'data-ref="ab12cd34"' in html
    assert '<option value="support" selected>' in html


@pytest.mark.parametrize("ref", ["", "<script>alert(1)</script>", "a b", "x" * 65])
def test_missing_or_malformed_reference_is_not_echoed(client, ref):
    html = client.get("/contact", query_string={"ref": ref} if ref else None).get_data(as_text=True)
    assert 'id="contactRef"' not in html
    assert "data-ref=" not in html
    assert "alert(1)" not in html


def test_form_does_not_claim_a_message_was_sent(client):
    html = client.get("/contact").get_data(as_text=True)
    assert "Thank you for your message" not in html
    assert 'data-to="info@ncrc.org"' in html
