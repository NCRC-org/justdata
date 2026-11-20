"""Sign out of all devices (spec 14, section 3).

The app session is a signed cookie, so it can't be deleted on other devices.
Instead the user record holds `sessionsRevokedAt` (whole seconds, UTC epoch).
A session opened before that time, or a Firebase ID token issued before it,
is treated as signed out. get_current_user() and the login route both check.

Firebase refresh tokens are revoked at the same time, so a browser that keeps
its Firebase sign-in can't mint a new ID token and sign itself back in.

Each instance caches the value for CACHE_SECONDS per user, so another device
is signed out within about a minute. The instance that handles the request
updates its own cache at once. If Firestore can't be read, nothing is revoked
(fail open): an outage must not sign everyone out.
"""
import logging
import time
from typing import Optional

from justdata.main.auth.services.firebase_client import get_firestore_client

logger = logging.getLogger(__name__)

FIELD = "sessionsRevokedAt"
CACHE_SECONDS = 60
_cache = {}  # uid -> (fetched_at, revoked_at or None)


def revoked_at(uid: str) -> Optional[int]:
    """The user's sessionsRevokedAt in epoch seconds, or None."""
    if not uid:
        return None
    hit = _cache.get(uid)
    now = time.time()
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    value = None
    db = get_firestore_client()
    if db is None:
        return None
    try:
        doc = db.collection("users").document(uid).get()
        raw = (doc.to_dict() or {}).get(FIELD) if doc.exists else None
        value = int(raw) if raw is not None else None
    except Exception as e:  # fail open, see module docstring
        logger.warning("Session revocation: could not read %s: %s", uid, type(e).__name__)
        return hit[1] if hit else None
    _cache[uid] = (now, value)
    return value


def is_revoked(uid: str, issued_at) -> bool:
    """True if a session or token issued at `issued_at` (epoch seconds) predates
    the user's revocation. A session with no issue time counts as revoked once
    the user has revoked, since it was opened before this check existed."""
    cutoff = revoked_at(uid)
    if cutoff is None:
        return False
    try:
        return issued_at is None or int(issued_at) < cutoff
    except (TypeError, ValueError):
        return True


def revoke_all_sessions(uid: str) -> int:
    """Record the revocation and revoke Firebase refresh tokens. Returns the
    cutoff. Raises if the user record can't be written."""
    from firebase_admin import auth as firebase_auth

    cutoff = int(time.time())
    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Firestore is not available")
    db.collection("users").document(uid).set({FIELD: cutoff}, merge=True)
    _cache[uid] = (time.time(), cutoff)
    try:
        firebase_auth.revoke_refresh_tokens(uid)
    except Exception as e:
        # The app-side cutoff already signs every session out; a browser could
        # sign back in only until its current ID token expires (an hour).
        logger.warning("Session revocation: refresh tokens not revoked for %s: %s", uid, type(e).__name__)
    return cutoff
