#!/usr/bin/env python3
"""
Revoke a staff, senior_executive or admin role from one user, by UID.

Sets the Firestore users/{uid} userType to public_registered, revokes the
user's Firebase refresh tokens, and writes one row to the Firestore
activity collection (UID, roles, reason, who ran it; no email).

Dry run by default; pass --apply to make the change.

    python scripts/revoke_elevated_role.py --uid <UID> --reason "<why>" --by <your email>
    python scripts/revoke_elevated_role.py --uid <UID> --reason "<why>" --by <your email> --apply

Two limits to know before relying on it:
- Sign-in recomputes the role. A verified @ncrc.org address, a Google
  @ncrc.org sign-in, or a verified address on the admin or senior executive
  list gets its role back at the next sign-in. The revocation holds only
  while the address doesn't qualify (for example, an unverified account).
- Revoking refresh tokens ends the Firebase sign-in, not a JustData session
  cookie that already holds the role. Those last up to 30 days, until
  SECRET_KEY changes.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load environment variables from .env file if it exists
env_file = REPO_ROOT / '.env'
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

from firebase_admin import auth as firebase_auth

from justdata.main.auth.services.firebase_client import get_firebase_app, get_firestore_client

ELEVATED_ROLES = ('staff', 'senior_executive', 'admin')
NEW_ROLE = 'public_registered'


def mask(email):
    if not email or '@' not in email:
        return '(none)'
    user, domain = email.split('@', 1)
    return f"{user[0]}***@{domain}"


def revoke(uid, reason, by, apply=False, db=None, auth=firebase_auth):
    """Returns 0 on success (or a clean dry run), 1 if nothing was done."""
    db = db or get_firestore_client()
    ref = db.collection('users').document(uid)
    doc = ref.get()
    if not doc.exists:
        print(f"No user record for uid={uid}. Nothing done.")
        return 1
    data = doc.to_dict() or {}
    role = data.get('userType')
    print(f"uid={uid} email={mask(data.get('email'))} role={role}")
    if role not in ELEVATED_ROLES:
        print(f"Role is not one of {', '.join(ELEVATED_ROLES)}. Nothing done.")
        return 1

    if not apply:
        print(f"Dry run: would set {role} -> {NEW_ROLE}, revoke refresh tokens and log one row. "
              "Pass --apply to make the change.")
        return 0

    now = datetime.now(timezone.utc)
    ref.update({'userType': NEW_ROLE, 'roleRevokedAt': now, 'roleRevokedFrom': role})
    auth.revoke_refresh_tokens(uid)
    db.collection('activity').add({
        'uid': uid,
        'action': 'role_revoked',
        'metadata': {'from_role': role, 'to_role': NEW_ROLE, 'reason': reason, 'by': by},
        'timestamp': now,
    })
    print(f"Done: {role} -> {NEW_ROLE}, refresh tokens revoked, activity row written.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--uid', required=True)
    parser.add_argument('--reason', required=True)
    parser.add_argument('--by', required=True, help='email of the person running this')
    parser.add_argument('--apply', action='store_true', help='make the change (default is a dry run)')
    args = parser.parse_args()

    if not get_firebase_app():
        print("Firebase is not configured: set FIREBASE_CREDENTIALS_JSON in .env.")
        return 1
    return revoke(args.uid, args.reason, args.by, apply=args.apply)


if __name__ == '__main__':
    sys.exit(main())
