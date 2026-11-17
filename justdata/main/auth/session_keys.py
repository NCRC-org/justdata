"""Per-account page state kept in the Flask session, and the one function that
clears it.

The analysis apps remember the current run in the session (job id, the
geography and years the form sent) for their own in-page flow. The session is a
signed cookie that outlives a sign-out, so without this a second account on the
same browser inherited the first account's last run (BZ-022). Every successful
sign-in and every sign-out calls clear_app_session().

tests/shared/test_session_isolation.py fails if code writes a session key that
is not listed here, so a new key cannot slip past the clear.
"""

from flask import session

# Every session key an app writes. Auth keys (firebase_user, user_type) are
# managed by justdata.main.auth and are not page state.
APP_SESSION_KEYS = (
    # BizSight, LendSight, BranchSight, MergerMeter
    'job_id',
    'county_data',
    'counties',
    'years',
    'selection_type',
    'loan_purpose',
    # MergerMeter goals calculator
    'goals_config',
    'goals_bank_name',
    # ElectWatch (archived, code retained)
    'official_id',
)


def clear_app_session():
    """Drop every app's page state from the session."""
    for key in APP_SESSION_KEYS:
        session.pop(key, None)
