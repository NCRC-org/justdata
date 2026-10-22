"""The Administration page (/admin/users) renders for admins.

It was rendered through a bare Jinja Environment with none of the app's
globals. Once the shell footer read `ncrc_contact` (#217), the page raised
UndefinedError and returned 500 on testing (Jay round 2 #1).
"""

from justdata.shared.contact import NCRC_CONTACT

PAGE_MARKER = b'id="totalUsers"'


def _signed_in(client, user_type):
    with client.session_transaction() as sess:
        sess["firebase_user"] = {"uid": f"test-{user_type}", "email": f"test-{user_type}@ncrc.org",
                                 "email_verified": True}
        sess["user_type"] = user_type


def test_admin_sees_the_page_with_the_shell_footer(unified_client):
    _signed_in(unified_client, "admin")
    resp = unified_client.get("/admin/users")
    assert resp.status_code == 200
    assert PAGE_MARKER in resp.data
    assert NCRC_CONTACT["email"].encode() in resp.data


def test_non_admins_do_not_get_the_page(unified_client):
    for user_type in ("staff", "member"):
        _signed_in(unified_client, user_type)
        resp = unified_client.get("/admin/users")
        assert PAGE_MARKER not in resp.data
