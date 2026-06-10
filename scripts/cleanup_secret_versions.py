#!/usr/bin/env python3
"""
One-time cleanup of surplus enabled versions in Secret Manager.

Default: dry-run (no modifications).
Use --execute to actually destroy. Requires typed confirmation.

Usage:
    python scripts/cleanup_secret_versions.py            # dry-run
    python scripts/cleanup_secret_versions.py --execute  # destructive
"""

import argparse
import json
import sys
import time
from datetime import datetime
from google.cloud import secretmanager
from google.auth import default as google_auth_default

PROJECT_ID = "justdata-ncrc"

SECRETS = [
    "analytics-bq-credentials",
    "bigquery-credentials",
    "bizsight-bq-credentials",
    "branchmapper-bq-credentials",
    "branchsight-bq-credentials",
    "dataexplorer-bq-credentials",
    "electwatch-bq-credentials",
    "firebase-admin-credentials",
    "lenderprofile-bq-credentials",
    "lendsight-bq-credentials",
    "mergermeter-bq-credentials",
]

CONFIRMATION_PHRASE = "DESTROY"


def get_principal():
    """Return the active credential's principal for logging."""
    credentials, _ = google_auth_default()
    # service_account_email for SA creds, otherwise fall back to a placeholder
    return getattr(credentials, "service_account_email", "user-adc")


def list_enabled_versions(client, secret_name):
    """Return enabled versions for a secret, sorted newest first."""
    parent = f"projects/{PROJECT_ID}/secrets/{secret_name}"
    versions = list(client.list_secret_versions(
        request={"parent": parent, "filter": "state:ENABLED"}
    ))
    versions.sort(key=lambda v: v.create_time, reverse=True)
    return versions


def process_secret(client, secret_name, execute):
    """Process one secret. Returns a dict for the log."""
    result = {
        "secret": secret_name,
        "kept": None,
        "destroyed": [],
        "errors": [],
        "skipped_reason": None,
    }

    try:
        versions = list_enabled_versions(client, secret_name)
    except Exception as e:
        result["errors"].append(f"list_secret_versions failed: {e}")
        return result

    if not versions:
        result["skipped_reason"] = "no enabled versions"
        return result

    if len(versions) > 1 and versions[0].create_time == versions[1].create_time:
        result["skipped_reason"] = "tied latest create_time; manual review"
        return result

    latest = versions[0]
    to_destroy = versions[1:]
    result["kept"] = latest.name

    print(f"\n{secret_name}")
    print(f"  Keeping:    {latest.name.split('/')[-1]} (created {latest.create_time})")
    print(f"  Candidates: {len(to_destroy)} versions to destroy")

    if not execute:
        return result

    for v in to_destroy:
        try:
            client.destroy_secret_version(request={"name": v.name})
            result["destroyed"].append(v.name)
            print(f"    Destroyed: {v.name.split('/')[-1]}")
        except Exception as e:
            result["errors"].append(f"destroy {v.name} failed: {e}")
            print(f"    ERROR destroying {v.name.split('/')[-1]}: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="Actually destroy versions. Without this, dry-run only.")
    args = parser.parse_args()

    start = time.time()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    mode = "execute" if args.execute else "dry-run"

    principal = get_principal()
    print(f"Project:   {PROJECT_ID}")
    print(f"Principal: {principal}")
    print(f"Mode:      {mode}")
    print(f"Secrets:   {len(SECRETS)}")

    if args.execute:
        print(f"\nThis will permanently destroy old enabled versions across "
              f"{len(SECRETS)} secrets in {PROJECT_ID}.")
        print(f"Type '{CONFIRMATION_PHRASE}' to proceed, anything else to abort.")
        response = input("> ")
        if response != CONFIRMATION_PHRASE:
            print("Aborted.")
            sys.exit(1)

    client = secretmanager.SecretManagerServiceClient()
    results = []
    for secret_name in SECRETS:
        results.append(process_secret(client, secret_name, args.execute))

    # Summary
    total_destroyed = sum(len(r["destroyed"]) for r in results)
    total_errors = sum(len(r["errors"]) for r in results)
    skipped = [r["secret"] for r in results if r["skipped_reason"]]

    print(f"\n{'='*60}")
    print(f"Done in {time.time() - start:.1f}s")
    print(f"Mode:      {mode}")
    print(f"Destroyed: {total_destroyed}")
    print(f"Errors:    {total_errors}")
    if skipped:
        print(f"Skipped:   {len(skipped)} ({', '.join(skipped)})")

    log_path = f"cleanup_log_{timestamp}.json"
    with open(log_path, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "project": PROJECT_ID,
            "principal": principal,
            "mode": mode,
            "results": [
                {**r, "destroyed": [n for n in r["destroyed"]]}
                for r in results
            ],
        }, f, indent=2, default=str)
    print(f"Log:       {log_path}")


if __name__ == "__main__":
    main()
