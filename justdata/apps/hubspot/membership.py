"""
Resolve NCRC membership using HubSpot data mirrored in BigQuery (justdata-ncrc.hubspot).
Used at registration for non-@ncrc.org work emails.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

from justdata.shared.utils.bigquery_client import get_bigquery_client

logger = logging.getLogger(__name__)

# Aligns with `hubspot.active_members` view (scripts/migration/28_create_hubspot_tables.sql)
_ACTIVE_MEMBERSHIP = frozenset(
    {
        "CURRENT",
        "GRACE PERIOD",
        "LIFETIME MEMBER",
        "NATIONAL PARTNER",
        "RECIPROCAL",
    }
)


@dataclass
class MembershipLookupResult:
    contact_id: Optional[str]
    company_id: Optional[str]
    company_name: Optional[str]
    membership_status: Optional[str]
    lookup_method: str
    email_template: Optional[str]
    is_member: bool


def is_ncrc_email(email: str) -> bool:
    return bool(email and email.strip().lower().endswith("@ncrc.org"))


def _normalize_status(raw: Optional[str]) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    return raw.strip().upper()


def lookup_membership_sync(email: str) -> MembershipLookupResult:
    """
    Look up HubSpot contact by email in BigQuery cache.
    Falls back to non-member if BQ is unavailable or email is unknown.
    """
    empty = MembershipLookupResult(
        contact_id=None,
        company_id=None,
        company_name=None,
        membership_status=None,
        lookup_method="none",
        email_template=None,
        is_member=False,
    )
    if not email or not str(email).strip():
        return empty

    project = os.getenv("JUSTDATA_PROJECT_ID", "justdata-ncrc")
    try:
        client = get_bigquery_client(project_id=project, app_name="hubspot")
    except Exception as e:
        logger.warning("HubSpot membership lookup: BigQuery client failed: %s", e)
        return MembershipLookupResult(
            contact_id=None,
            company_id=None,
            company_name=None,
            membership_status=None,
            lookup_method="bigquery_error",
            email_template=None,
            is_member=False,
        )

    q = f"""
    SELECT
      c.hubspot_contact_id,
      c.email,
      c.membership_status AS contact_membership_status,
      c.company_name AS contact_company_name,
      c.hubspot_company_id,
      co.name AS company_table_name
    FROM `{project}.hubspot.contacts` c
    LEFT JOIN `{project}.hubspot.companies` co
      ON c.hubspot_company_id = co.hubspot_company_id
    WHERE LOWER(TRIM(c.email)) = LOWER(TRIM(@email))
    LIMIT 1
    """
    job_config = QueryJobConfig(
        query_parameters=[
            ScalarQueryParameter("email", "STRING", email.strip()),
        ]
    )
    try:
        rows = list(client.query(q, job_config=job_config).result())
    except Exception as e:
        logger.warning("HubSpot membership lookup query failed: %s", e)
        return MembershipLookupResult(
            contact_id=None,
            company_id=None,
            company_name=None,
            membership_status=None,
            lookup_method="bigquery_error",
            email_template=None,
            is_member=False,
        )

    if not rows:
        return MembershipLookupResult(
            contact_id=None,
            company_id=None,
            company_name=None,
            membership_status=None,
            lookup_method="not_in_cache",
            email_template=None,
            is_member=False,
        )

    row = rows[0]
    status = _normalize_status(row["contact_membership_status"])
    is_member = status in _ACTIVE_MEMBERSHIP
    company_name = row["company_table_name"] or row["contact_company_name"]

    cid = row["hubspot_contact_id"]
    ccid = row["hubspot_company_id"]

    return MembershipLookupResult(
        contact_id=str(cid) if cid is not None else None,
        company_id=str(ccid) if ccid is not None else None,
        company_name=company_name,
        membership_status=row["contact_membership_status"],
        lookup_method="bigquery_cache",
        email_template=None,
        is_member=is_member,
    )
