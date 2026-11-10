#!/usr/bin/env python3
"""
Remove every spec 10 load-test account in one pass. Dry run by default.

    python scripts/remove_load_accounts.py            # report only
    python scripts/remove_load_accounts.py --apply

Finds Firebase users with BOTH the load_account claim and a
jd-load-NN@example.org address, then removes, for each: the testing
usage_log and signin_refusals rows, the Firestore activity rows and users
record, the Firebase account, and the HubSpot contact (archived only if it
is still non-marketing; otherwise left for a person to check). Rows written
in the last ~30 minutes can't be deleted from BigQuery yet; rerun later.
See justdata/main/auth/services/load_accounts.py.
"""

import argparse
import os
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
from justdata.shared.utils.bigquery_client import get_bigquery_client


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--apply', action='store_true', help='remove the accounts (default is a dry run)')
    args = parser.parse_args()

    if not get_firebase_app():
        print("Firebase is not configured: set FIREBASE_CREDENTIALS_JSON in .env.")
        return 1
    project = os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
    bq = load_accounts.BigQueryDeleter(get_bigquery_client(project_id=project))
    problems = load_accounts.remove(firebase_auth, get_firestore_client(), bq, project, apply=args.apply)
    if not args.apply:
        print("Dry run: nothing was removed. Pass --apply to remove.")
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
