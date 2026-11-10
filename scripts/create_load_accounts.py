#!/usr/bin/env python3
"""
Create the spec 10 load-test accounts (Firebase side). Dry run by default.

    python scripts/create_load_accounts.py            # report only
    python scripts/create_load_accounts.py --apply    # on Jad's go, after Jay's walkthrough

Before --apply, Jad imports the 20 HubSpot contacts (jd-load-01@example.org
to jd-load-20@example.org): justdata_tester_authorized ticked, set as
non-marketing, on the "JustData load accounts" list. The dry run reads each
contact (HUBSPOT_ACCESS_TOKEN in the environment) and reports any that
aren't ready. Passwords go to ~/.justdata-load-accounts.json (mode 600) and
are never printed. See justdata/main/auth/services/load_accounts.py.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load environment variables from .env file if it exists
env_file = REPO_ROOT / '.env'
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

from firebase_admin import auth as firebase_auth

from justdata.main.auth.services import load_accounts
from justdata.main.auth.services.firebase_client import get_firebase_app, get_firestore_client


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--apply', action='store_true', help='create the accounts (default is a dry run)')
    parser.add_argument('--count', type=int, default=load_accounts.LOAD_COUNT)
    args = parser.parse_args()

    if not get_firebase_app():
        print("Firebase is not configured: set FIREBASE_CREDENTIALS_JSON in .env.")
        return 1
    problems = load_accounts.create(firebase_auth, get_firestore_client(),
                                    addresses=load_accounts.load_addresses(args.count), apply=args.apply)
    if not args.apply:
        print("Dry run: nothing was created. Pass --apply to create.")
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
