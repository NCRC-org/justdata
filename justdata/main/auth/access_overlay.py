"""Testing-site access overlay (JUSTDATA_ENV=testing only).

The external-tester deploy (`justdata-testing`) shows non-staff users exactly
four apps. Rather than edit ACCESS_MATRIX, which staging and production share,
this overlay rewrites a matrix row at read time, and only when
JUSTDATA_ENV == "testing". Every access check goes through
get_access_row() in main/auth/__init__.py, which calls overlay_row(), so the
route gate, the nav drawer and the /apps launcher cannot disagree.

This resolves decision D2 (MergerMeter is tester-facing) for the testing
deploy only. It is the one deliberate access change made with spec 01.

The global staff-only gate (check_privileged_access in main/app.py) reads
testing_gate_admits() below: on the testing deploy it also admits TESTER_ROLES,
and anyone on the exact TESTING_PUBLIC_PATHS.

On the testing deploy, for every non-staff role:
  - apps outside TESTER_APPS resolve to "hidden" (not shown, not even locked)
  - mergermeter resolves to "full" for TESTER_ROLES and "locked" for the
    other non-staff roles, so they see the same four apps as testers
Staff roles (PRIVILEGED_ROLES) are never touched.
"""

import os

TESTER_APPS = ("lendsight", "bizsight", "branchsight", "mergermeter")

# Non-staff roles admitted as external testers. They get full MergerMeter
# access on the testing site. non_member_org is included because not every
# tester org (fair-lending orgs, researchers) is an NCRC member.
TESTER_ROLES = ("member", "member_premium", "non_member_org")


# Paths anyone may open on the testing deploy, matched exactly (never as a
# prefix: "/" as a prefix would exempt every route). The landing page and the
# two pages it and the footer link to.
TESTING_PUBLIC_PATHS = frozenset({"/", "/about", "/contact"})


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
        elif app_name == "mergermeter":
            out[role] = "full" if role in TESTER_ROLES else "locked"
    return out


def testing_gate_admits(path: str, user_type: str) -> bool:
    """True if the global staff-only gate should let this request through
    because of the testing deploy: a tester role (TESTER_ROLES), or an exact
    TESTING_PUBLIC_PATHS match for anyone. Always False off the testing deploy,
    so staging and production keep the staff-only gate unchanged. Routes still
    apply their own require_access checks after this.
    """
    if not is_testing_env():
        return False
    return path in TESTING_PUBLIC_PATHS or user_type in TESTER_ROLES
