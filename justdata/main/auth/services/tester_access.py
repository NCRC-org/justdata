"""
Testing-site admission (spec 08, JUSTDATA_ENV=testing only).

HubSpot decides who may sign in to the testing site. A non-staff sign-in is
admitted only when the HubSpot contact for that email has the checkbox
property justdata_tester_authorized ticked. A missing contact, a missing
property or an unticked box is a refusal. Contact-exists alone is not enough:
the daily HubSpot sync adds every past production user as a contact
(Jad, 2026-11-06, revising decision 2).

- check_tester_access: live HubSpot lookup by email; the BigQuery mirror
  (hubspot.contacts) is the fallback, used only when the API call fails
- admit_or_refuse: the login route's entry point; reuses a recent
  authorization, records the result on the Firestore user record, and logs
  refusals
- log_refusal: UID and reason only, never the email, to a BigQuery table whose
  day partitions expire after 90 days
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

import httpx

from justdata.main.auth.services.firebase_client import get_firestore_client

logger = logging.getLogger(__name__)

HUBSPOT_API = "https://api.hubapi.com"
TESTER_PROPERTY = "justdata_tester_authorized"
TOKEN_ENV = "HUBSPOT_ACCESS_TOKEN"
API_TIMEOUT = 5

# Login runs on every page load, so a recent authorization is reused rather
# than calling HubSpot each time. Refusals are never reused: a contact Jay
# ticks is admitted on the next attempt.
RECHECK_AFTER = timedelta(minutes=15)

REFUSAL_RETENTION_DAYS = 90

# Refusal reasons, as logged. The page groups them into two messages.
AUTHORIZED = "authorized"
NO_CONTACT = "no_contact"
NOT_AUTHORIZED = "not_authorized"
TOKEN_MISSING = "token_missing"
HUBSPOT_UNAVAILABLE = "hubspot_unavailable"
UNAVAILABLE_REASONS = (TOKEN_MISSING, HUBSPOT_UNAVAILABLE)

# How /admin/users and the refusals page name each reason
REASON_LABELS = {
    AUTHORIZED: "Authorized",
    NO_CONTACT: "No HubSpot contact",
    NOT_AUTHORIZED: "Box not ticked",
    TOKEN_MISSING: "HubSpot token missing",
    HUBSPOT_UNAVAILABLE: "HubSpot unavailable",
}
REFUSALS_SHOWN = 500


@dataclass
class AdmissionResult:
    authorized: bool
    reason: str
    source: str  # 'hubspot_api', 'bigquery_mirror', 'recent_check' or 'none'


def _project_id() -> str:
    return os.getenv("JUSTDATA_PROJECT_ID", "justdata-ncrc")


def _refusal_table() -> str:
    dataset = "cache_testing" if os.getenv("JUSTDATA_ENV") == "testing" else "cache"
    return f"{_project_id()}.{dataset}.signin_refusals"


def _ticked(value) -> bool:
    """HubSpot returns checkbox values as the strings 'true' and 'false'."""
    return str(value).strip().lower() == "true"


def _hubspot_get(url: str, params: dict, headers: dict) -> httpx.Response:
    return httpx.get(url, params=params, headers=headers, timeout=API_TIMEOUT)


def _lookup_api(email: str, token: str) -> AdmissionResult:
    """Raises on any failure other than a missing contact."""
    resp = _hubspot_get(
        f"{HUBSPOT_API}/crm/v3/objects/contacts/{quote(email, safe='')}",
        params={"idProperty": "email", "properties": TESTER_PROPERTY},
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 404:
        return AdmissionResult(False, NO_CONTACT, "hubspot_api")
    resp.raise_for_status()
    value = (resp.json().get("properties") or {}).get(TESTER_PROPERTY)
    if _ticked(value):
        return AdmissionResult(True, AUTHORIZED, "hubspot_api")
    return AdmissionResult(False, NOT_AUTHORIZED, "hubspot_api")


def _lookup_mirror(email: str) -> AdmissionResult:
    """The daily BigQuery copy. Until the sync copies the tester property the
    query fails, and the sign-in is refused as unavailable."""
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    from justdata.shared.utils.bigquery_client import get_bigquery_client

    project = _project_id()
    sql = f"""
    SELECT CAST({TESTER_PROPERTY} AS STRING) AS authorized
    FROM `{project}.hubspot.contacts`
    WHERE LOWER(TRIM(email)) = LOWER(TRIM(@email))
    LIMIT 1
    """
    try:
        client = get_bigquery_client(project_id=project, app_name="hubspot")
        job_config = QueryJobConfig(query_parameters=[ScalarQueryParameter("email", "STRING", email)])
        rows = list(client.query(sql, job_config=job_config).result())
    except Exception as e:
        logger.warning("Tester check: BigQuery mirror fallback failed: %s", e)
        return AdmissionResult(False, HUBSPOT_UNAVAILABLE, "bigquery_mirror")
    if not rows:
        return AdmissionResult(False, NO_CONTACT, "bigquery_mirror")
    if _ticked(rows[0]["authorized"]):
        return AdmissionResult(True, AUTHORIZED, "bigquery_mirror")
    return AdmissionResult(False, NOT_AUTHORIZED, "bigquery_mirror")


def check_tester_access(email: str) -> AdmissionResult:
    """Is this email an authorized tester? Never raises."""
    token = (os.getenv(TOKEN_ENV) or "").strip()
    if not token:
        logger.error("Tester check: %s is not set; refusing tester sign-ins", TOKEN_ENV)
        return AdmissionResult(False, TOKEN_MISSING, "none")
    if not email:
        return AdmissionResult(False, NO_CONTACT, "none")
    try:
        return _lookup_api(email.strip(), token)
    except Exception as e:
        logger.warning("Tester check: HubSpot API failed (%s); trying the BigQuery mirror", type(e).__name__)
        return _lookup_mirror(email.strip())


def _as_utc(value) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def recent_authorization(user_doc: dict) -> bool:
    """True if the user record holds an authorization checked within RECHECK_AFTER."""
    access = (user_doc or {}).get("testerAccess") or {}
    checked_at = _as_utc(access.get("checkedAt"))
    return bool(access.get("authorized")) and checked_at is not None and \
        datetime.now(timezone.utc) - checked_at < RECHECK_AFTER


def record_result(uid: str, result: Optional[AdmissionResult], user_type: Optional[str] = None) -> None:
    """Write a fresh check's result and timestamp to the Firestore user record,
    and the user type when admission changes it. result is None for a reused
    authorization, so its timestamp is never moved forward."""
    db = get_firestore_client()
    if not db or not uid:
        return
    update = {}
    if result is not None:
        update["testerAccess"] = {
            "authorized": result.authorized,
            "reason": result.reason,
            "source": result.source,
            "checkedAt": datetime.now(timezone.utc),
        }
    if user_type:
        update["userType"] = user_type
    if not update:
        return
    try:
        db.collection("users").document(uid).update(update)
    except Exception as e:
        logger.warning("Tester check: could not record the result for %s: %s", uid, e)


_refusal_table_ready = False


def _ensure_refusal_table(client) -> None:
    global _refusal_table_ready
    if _refusal_table_ready:
        return
    from google.cloud import bigquery

    table = bigquery.Table(_refusal_table(), schema=[
        bigquery.SchemaField("refused_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("uid", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("reason", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source", "STRING"),
    ])
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="refused_at",
        expiration_ms=REFUSAL_RETENTION_DAYS * 24 * 60 * 60 * 1000,
    )
    client.create_table(table, exists_ok=True)
    _refusal_table_ready = True


def log_refusal(uid: str, result: AdmissionResult) -> None:
    """One row per refusal: UID, reason and source. No email."""
    print(f"[tester_access] refused uid={uid} reason={result.reason} source={result.source}")
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client

        client = get_bigquery_client(project_id=_project_id())
        _ensure_refusal_table(client)
        errors = client.insert_rows_json(_refusal_table(), [{
            "refused_at": datetime.now(timezone.utc).isoformat(),
            "uid": uid,
            "reason": result.reason,
            "source": result.source,
        }])
        if errors:
            logger.warning("Tester check: refusal log insert errors: %s", errors)
    except Exception as e:
        logger.warning("Tester check: could not log the refusal: %s", e)


def recent_refusals(limit: int = REFUSALS_SHOWN) -> list:
    """Newest refusals first: time, UID, reason and source. Empty when the
    table doesn't exist yet (no refusal on this deploy) or can't be read."""
    from google.api_core.exceptions import NotFound
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    from justdata.shared.utils.bigquery_client import get_bigquery_client

    sql = (f"SELECT refused_at, uid, reason, source FROM `{_refusal_table()}` "
           "ORDER BY refused_at DESC LIMIT @limit")
    job_config = QueryJobConfig(query_parameters=[ScalarQueryParameter("limit", "INT64", limit)])
    try:
        client = get_bigquery_client(project_id=_project_id())
        rows = client.query(sql, job_config=job_config).result()
        return [{"refused_at": r["refused_at"], "uid": r["uid"], "reason": r["reason"],
                 "source": r["source"]} for r in rows]
    except NotFound:
        return []
    except Exception as e:
        logger.warning("Tester check: could not read refusals: %s", e)
        return []


def admit_or_refuse(uid: str, email: str, user_doc: dict, user_type: str) -> tuple:
    """Admission for a non-staff sign-in on the testing deploy.

    Returns (result, user_type). An admitted public user becomes 'tester';
    member, member_premium and non_member_org keep their type, since the
    Firestore users collection is shared with production.
    """
    if recent_authorization(user_doc):
        result = AdmissionResult(True, AUTHORIZED, "recent_check")
    else:
        result = check_tester_access(email)

    if not result.authorized:
        record_result(uid, result)
        log_refusal(uid, result)
        return result, user_type

    new_type = "tester" if user_type in ("public_anonymous", "public_registered") else user_type
    changed_type = new_type if new_type != user_type else None
    if result.source != "recent_check":
        record_result(uid, result, changed_type)
    elif changed_type:
        record_result(uid, None, changed_type)
    return result, new_type
