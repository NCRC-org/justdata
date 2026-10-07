"""
Membership business logic.

Membership-related routes live in justdata.main.auth.routes.organizations:
- /set-organization
- /membership-status
- /member-request/status
- /member-request/dismiss-prompt

member_request_status() below is the single lookup behind
/member-request/status; the /apps launcher reads it server-side too, so the
two can never disagree. Other membership logic is still inside the route
handlers.

External membership data lookups against HubSpot live in
justdata.apps.hubspot.membership and are imported lazily inside the route
handlers to avoid circular imports.
"""

from justdata.main.auth.services.firebase_client import get_firestore_client, get_user_doc

MEMBER_TYPES = ('member', 'member_premium', 'non_member_org', 'staff', 'senior_executive', 'admin')


def member_request_status(uid):
    """Return (status, user_doc) for a signed-in user's member request.

    status is one of "member", "pending", "denied" or "unknown". user_doc is
    the Firestore user document, or None when there is no uid, no Firestore
    client, no document or the lookup fails (status is then "unknown").
    """
    if not uid or not get_firestore_client():
        return 'unknown', None
    try:
        user_doc = get_user_doc(uid)
    except Exception:
        return 'unknown', None
    if not user_doc:
        return 'unknown', None

    hubspot_status = (user_doc.get('hubspot_membership_status') or '').strip().upper()
    if (user_doc.get('userType') or '') in MEMBER_TYPES:
        return 'member', user_doc
    if hubspot_status == 'PENDING':
        return 'pending', user_doc
    if hubspot_status in ('DENIED', 'EXPIRED'):
        return 'denied', user_doc
    return 'unknown', user_doc
