#!/usr/bin/env python3
"""
Push BigQuery / Firebase service account JSON from .env (or the environment)
into Google Secret Manager using the same names Cloud Run expects.

Local: values are read from .env unless already set in the process environment.
CI:   set GitHub Actions secrets and pass them as env vars to this step.

Usage:
  python3 scripts/sync_cloudrun_bq_secrets.py --project justdata-ncrc
  python3 scripts/sync_cloudrun_bq_secrets.py --project justdata-ncrc --env-file /path/.env
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

# (env var name, Secret Manager secret id) — matches deploy-cloudrun.yml / deploy-cloudrun.sh
SECRET_PAIRS: List[Tuple[str, str]] = [
    ("GOOGLE_APPLICATION_CREDENTIALS_JSON", "bigquery-credentials"),
    ("FIREBASE_CREDENTIALS_JSON", "firebase-admin-credentials"),
    ("LENDSIGHT_CREDENTIALS_JSON", "lendsight-bq-credentials"),
    ("BIZSIGHT_CREDENTIALS_JSON", "bizsight-bq-credentials"),
    ("BRANCHSIGHT_CREDENTIALS_JSON", "branchsight-bq-credentials"),
    ("BRANCHMAPPER_CREDENTIALS_JSON", "branchmapper-bq-credentials"),
    ("MERGERMETER_CREDENTIALS_JSON", "mergermeter-bq-credentials"),
    ("DATAEXPLORER_CREDENTIALS_JSON", "dataexplorer-bq-credentials"),
    ("LENDERPROFILE_CREDENTIALS_JSON", "lenderprofile-bq-credentials"),
    ("ANALYTICS_CREDENTIALS_JSON", "analytics-bq-credentials"),
    ("ELECTWATCH_CREDENTIALS_JSON", "electwatch-bq-credentials"),
]


def _strip_wrappers(raw: str) -> str:
    s = raw.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        s = s[1:-1].strip()
    return s


def load_dotenv_file(path: str) -> Dict[str, str]:
    try:
        from dotenv import dotenv_values
    except ImportError:
        print("python-dotenv is required (pip install python-dotenv)", file=sys.stderr)
        sys.exit(1)
    data = dotenv_values(path) or {}
    return {k: v for k, v in data.items() if v is not None and str(v).strip() != ""}


def resolve_value(env_key: str, file_vals: Dict[str, str]) -> Optional[str]:
    v = os.environ.get(env_key)
    if v is not None and str(v).strip():
        return _strip_wrappers(str(v))
    if env_key in file_vals:
        return _strip_wrappers(str(file_vals[env_key]))
    return None


def validate_sa_json(payload: str, env_key: str) -> dict:
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError as e:
        raise SystemExit(f"{env_key}: invalid JSON ({e})") from e
    if not isinstance(obj, dict):
        raise SystemExit(f"{env_key}: JSON must be an object")
    if obj.get("type") != "service_account":
        raise SystemExit(f"{env_key}: expected type service_account")
    if not obj.get("client_email"):
        raise SystemExit(f"{env_key}: missing client_email")
    return obj


def gcloud(cmd: List[str], project: str) -> None:
    full = ["gcloud", *cmd, f"--project={project}"]
    r = subprocess.run(full, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        sys.exit(r.returncode)


def secret_exists(secret_id: str, project: str) -> bool:
    r = subprocess.run(
        ["gcloud", "secrets", "describe", secret_id, f"--project={project}"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def upsert_secret(secret_id: str, payload: bytes, project: str) -> None:
    if not secret_exists(secret_id, project):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(payload)
            path = f.name
        try:
            gcloud(
                [
                    "secrets",
                    "create",
                    secret_id,
                    "--replication-policy=automatic",
                    f"--data-file={path}",
                ],
                project,
            )
        finally:
            os.unlink(path)
        print(f"  created secret {secret_id}")
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(payload)
        path = f.name
    try:
        gcloud(["secrets", "versions", "add", secret_id, f"--data-file={path}"], project)
    finally:
        os.unlink(path)
    print(f"  added version to {secret_id}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", default=os.environ.get("GCP_PROJECT_ID", "justdata-ncrc"))
    p.add_argument("--env-file", default=".env", help="Path to .env (default: .env)")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error if any expected env key is missing (for CI)",
    )
    args = p.parse_args()

    file_vals: Dict[str, str] = {}
    if os.path.isfile(args.env_file):
        file_vals = load_dotenv_file(args.env_file)
        print(f"Loaded keys from {args.env_file}: {len(file_vals)} entries")
    elif args.strict:
        print(f"No env file at {args.env_file} (--strict)", file=sys.stderr)
        sys.exit(1)

    missing = []
    for env_key, secret_id in SECRET_PAIRS:
        raw = resolve_value(env_key, file_vals)
        if not raw:
            msg = f"skip {env_key} -> {secret_id} (not set)"
            if args.strict:
                missing.append(env_key)
            else:
                print(msg)
            continue
        obj = validate_sa_json(raw, env_key)
        email = obj["client_email"]
        payload = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        print(f"sync {env_key} -> {secret_id} ({email})")
        upsert_secret(secret_id, payload, args.project)

    if missing:
        print("Missing required credential env vars:", ", ".join(missing), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
