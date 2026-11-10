"""The admin and senior executive lists grant their role only to a verified
address (Codex review finding 3; hotfix of the list rule in 8495209)."""

import pytest

from justdata.main.auth import ADMIN_EMAILS, SENIOR_EXECUTIVE_EMAILS, determine_user_type

LISTED = [(ADMIN_EMAILS[0], "admin"), (SENIOR_EXECUTIVE_EMAILS[0], "senior_executive")]


@pytest.mark.parametrize("email, role", LISTED)
def test_lists_grant_their_role_only_to_a_verified_address(email, role):
    assert determine_user_type(email, True, auth_provider="password") == role
    assert determine_user_type(email, True, auth_provider="google.com") == role
    unverified = determine_user_type(email, False, auth_provider="password")
    assert unverified not in ("admin", "senior_executive", "staff")
    # A record already holding the role loses it while the address is unverified
    assert determine_user_type(email, False, current_type=role, auth_provider="password") == unverified
