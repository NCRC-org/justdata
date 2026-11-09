"""GA4 events carry no email or display name (spec 08).

analytics-events.js adds common parameters to every event; the Firebase UID
stays, the email and display name don't.
"""

from pathlib import Path

JS = Path(__file__).resolve().parents[2] / "justdata/shared/web/static/js/analytics-events.js"


def test_events_send_no_email_or_display_name():
    source = JS.read_text()
    for needle in ("user_email", "user_display_name", "currentUser.email", "currentUser.displayName"):
        assert needle not in source, needle


def test_events_still_send_the_uid():
    assert "enrichedParams.firebase_uid = currentUser.uid" in JS.read_text()
