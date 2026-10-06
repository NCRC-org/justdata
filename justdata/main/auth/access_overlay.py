"""Testing-site access overlay (JUSTDATA_ENV=testing only).

The external-tester deploy (`justdata-testing`) shows non-staff users exactly
four apps. Rather than edit ACCESS_MATRIX, which staging and production share,
this overlay rewrites a matrix row at read time, and only when
JUSTDATA_ENV == "testing". Every access check goes through
get_access_row() in main/auth/__init__.py, which calls overlay_row(), so the
route gate, the nav drawer and the /apps launcher cannot disagree.

This resolves decision D2 (MergerMeter is tester-facing) for the testing
deploy only. It is the one deliberate access change made with spec 01.

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
