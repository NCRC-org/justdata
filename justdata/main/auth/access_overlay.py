"""Testing-site access overlay (JUSTDATA_ENV=testing only).

The external-tester deploy (`justdata-testing`) shows non-staff users exactly
three apps, the Sight apps. Rather than edit ACCESS_MATRIX, which staging and production share,
this overlay rewrites a matrix row at read time, and only when
JUSTDATA_ENV == "testing". Every access check goes through
get_access_row() in main/auth/__init__.py, which calls overlay_row(), so the
route gate, the nav drawer and the /apps launcher cannot disagree.

D2 is resolved (Jad, 2026-10-07): MergerMeter is staff-only on every deploy.
The overlay does not touch it; ACCESS_MATRIX already hides it from non-staff.

The global staff-only gate (check_privileged_access in main/app.py) reads
testing_gate_admits() below: on the testing deploy it also admits TESTER_ROLES,
and anyone on the exact TESTING_PUBLIC_PATHS.

On the testing deploy, for every non-staff role:
  - apps outside TESTER_APPS resolve to "hidden" (not shown, not even locked)
  - for the public roles (not TESTER_ROLES), all three TESTER_APPS resolve to
    "locked": the global gate never lets them open an app, so the drawer,
    launcher and landing roster must not show one as open (LendSight is
    'limited' for public_registered in the matrix)
Staff roles (PRIVILEGED_ROLES) are never touched.

A signed-in public_registered user may also open /apps itself on the testing
deploy (TESTING_REGISTERED_PATHS), to see the locked tools and request access.
"""

import os

# The three Sight apps. MergerMeter is staff-only (D2) and is not a tester app.
TESTER_APPS = ("lendsight", "bizsight", "branchsight")

# Non-staff roles admitted as external testers. non_member_org is included
# because not every tester org (fair-lending orgs, researchers) is an NCRC member.
TESTER_ROLES = ("member", "member_premium", "non_member_org")


# Paths anyone may open on the testing deploy, matched exactly (never as a
# prefix: "/" as a prefix would exempt every route). The landing page and the
# two pages it and the footer link to.
TESTING_PUBLIC_PATHS = frozenset({"/", "/about", "/contact"})

# Extra exact paths for a signed-in public_registered user on the testing
# deploy: the launcher, where every tool shows locked with the request-access
# panel. Signed-out visitors stay blocked. Decided by Jad 2026-10-07.
TESTING_REGISTERED_PATHS = frozenset({"/apps"})


def is_testing_env() -> bool:
    """Read at call time so tests can set JUSTDATA_ENV per case."""
    return os.getenv("JUSTDATA_ENV") == "testing"


def overlay_row(app_name: str, row: dict, staff_roles) -> dict:
    """Return the matrix row for app_name with the testing overlay applied.

    Outside JUSTDATA_ENV=testing the row is returned unchanged.
    """
    if not is_testing_env():
        return row
    out = dict(row)
    for role in set(out) | set(TESTER_ROLES):
        if role in staff_roles:
            continue
        if app_name not in TESTER_APPS:
            out[role] = "hidden"
        elif role not in TESTER_ROLES:
            out[role] = "locked"
    return out


def testing_gate_admits(path: str, user_type: str, signed_in: bool = False) -> bool:
    """True if the global staff-only gate should let this request through
    because of the testing deploy: a tester role (TESTER_ROLES), an exact
    TESTING_PUBLIC_PATHS match for anyone, or an exact TESTING_REGISTERED_PATHS
    match for a signed-in public_registered user. Always False off the testing
    deploy, so staging and production keep the staff-only gate unchanged.
    Routes still apply their own require_access checks after this.
    """
    if not is_testing_env():
        return False
    if path in TESTING_PUBLIC_PATHS or user_type in TESTER_ROLES:
        return True
    return signed_in and user_type == "public_registered" and path in TESTING_REGISTERED_PATHS


def is_tester(user_type: str) -> bool:
    """A tester role on the testing deploy (can open the three tester apps)."""
    return is_testing_env() and user_type in TESTER_ROLES
