"""
Daily HubSpot → BigQuery sync for CRM cache (companies, contacts).
Optional: create HubSpot contacts for JustData users not yet in HubSpot.

Cloud Run Job entrypoint: HubSpotDailySync().run()
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from justdata.shared.utils.bigquery_client import get_bigquery_client

logger = logging.getLogger(__name__)

HUBSPOT_API = "https://api.hubapi.com"

COMPANY_PROPERTIES = [
    "name",
    "domain",
    "membership_status",
    "current_membership_status",
    "city",
    "state",
    "country",
    "industry",
    "phone",
]

CONTACT_PROPERTIES = [
    "email",
    "firstname",
    "lastname",
    "company",
    "membership_status",
    "jobtitle",
    "phone",
]

# Disposable / personal domains to exclude when pushing new contacts (see migration 28)
_DISPOSABLE_DOMAINS = (
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "protonmail.com",
    "proton.me",
    "live.com",
    "msn.com",
    "comcast.net",
    "verizon.net",
    "att.net",
    "sbcglobal.net",
    "ymail.com",
    "rocketmail.com",
    "mail.com",
    "zoho.com",
    "fastmail.com",
    "tutanota.com",
    "hey.com",
    "pm.me",
    "googlemail.com",
    "earthlink.net",
    "cox.net",
    "charter.net",
    "optonline.net",
    "frontier.com",
    "windstream.net",
)


def _configure_logging() -> None:
    if not logging.root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
    logging.getLogger("httpx").setLevel(logging.INFO)


def _sync_ts() -> str:
    """UTC timestamp string for BigQuery TIMESTAMP JSON inserts."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _extract_company_id_from_contact(obj: Dict[str, Any]) -> Optional[str]:
    ass = obj.get("associations") or {}
    companies = ass.get("companies")
    if not companies:
        return None
    if isinstance(companies, dict):
        results = companies.get("results") or []
        if results and isinstance(results[0], dict):
            cid = results[0].get("id")
            return str(cid) if cid is not None else None
    return None


class HubSpotDailySync:
    def __init__(self) -> None:
        _configure_logging()
        self.token = (os.environ.get("HUBSPOT_ACCESS_TOKEN") or "").strip()
        self.project_id = os.environ.get("JUSTDATA_PROJECT_ID", "justdata-ncrc")
        self.errors: List[str] = []
        self._companies_synced = 0
        self._contacts_synced = 0
        self._pushed = 0

    def run(self) -> None:
        started = time.perf_counter()
        t0 = datetime.now(timezone.utc).isoformat()
        logger.info("=" * 60)
        logger.info("HubSpot Daily Sync - Starting")
        logger.info("Time: %s", t0)
        logger.info("=" * 60)

        if not self.token:
            raise RuntimeError("HUBSPOT_ACCESS_TOKEN is not set")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
            logger.info("Phase 1a: Pulling companies from HubSpot...")
            companies = self._fetch_all_companies(client, headers)
            logger.info("  Fetched %s companies from HubSpot", len(companies))

            bq = get_bigquery_client(project_id=self.project_id, app_name="hubspot")
            synced = _sync_ts()
            company_rows = [self._company_to_bq_row(c, synced) for c in companies]
            self._truncate_and_insert(
                bq,
                f"{self.project_id}.hubspot.companies",
                company_rows,
                "companies",
            )
            self._companies_synced = len(company_rows)

            logger.info("Phase 1b: Pulling contacts from HubSpot...")
            contacts = self._fetch_all_contacts(client, headers)
            logger.info("  Fetched %s contacts from HubSpot", len(contacts))
            contact_rows = [self._contact_to_bq_row(c, synced) for c in contacts]
            self._truncate_and_insert(
                bq,
                f"{self.project_id}.hubspot.contacts",
                contact_rows,
                "contacts",
            )
            self._contacts_synced = len(contact_rows)

            logger.info("Phase 2: Finding JustData users not in HubSpot...")
            self._phase2_push_new_users(client, headers, bq)

        elapsed = time.perf_counter() - started
        logger.info("=" * 60)
        logger.info("HubSpot Daily Sync - Complete")
        logger.info("Duration: %.1fs", elapsed)
        logger.info("Companies synced: %s", self._companies_synced)
        logger.info("Contacts synced: %s", self._contacts_synced)
        logger.info("New users pushed to HubSpot: %s", self._pushed)
        if self.errors:
            logger.warning("Errors: %s", len(self.errors))
            for e in self.errors:
                logger.warning("  - %s", e)
        else:
            logger.info("Errors: 0")
        logger.info("=" * 60)

    def _fetch_all_companies(
        self, client: httpx.Client, headers: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        after: Optional[str] = None
        page = 0
        url = f"{HUBSPOT_API}/crm/v3/objects/companies"
        props = ",".join(COMPANY_PROPERTIES)
        while True:
            params: Dict[str, Any] = {
                "limit": 100,
                "properties": props,
            }
            if after:
                params["after"] = after
            data = self._hubspot_get(client, url, headers, params)
            batch = data.get("results") or []
            out.extend(batch)
            page += 1
            if page % 20 == 0:
                logger.info(
                    "  Companies: fetched %s so far (page %s)...", len(out), page
                )
            paging = data.get("paging") or {}
            next_page = paging.get("next") or {}
            after = next_page.get("after")
            if not after:
                break
        return out

    def _fetch_all_contacts(
        self, client: httpx.Client, headers: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        after: Optional[str] = None
        page = 0
        url = f"{HUBSPOT_API}/crm/v3/objects/contacts"
        props = ",".join(CONTACT_PROPERTIES)
        while True:
            params: Dict[str, Any] = {
                "limit": 100,
                "properties": props,
                "associations": "companies",
            }
            if after:
                params["after"] = after
            data = self._hubspot_get(client, url, headers, params)
            batch = data.get("results") or []
            out.extend(batch)
            page += 1
            if page % 50 == 0:
                logger.info(
                    "  Contacts: fetched %s so far (page %s)...", len(out), page
                )
            paging = data.get("paging") or {}
            next_page = paging.get("next") or {}
            after = next_page.get("after")
            if not after:
                break
        return out

    def _hubspot_get(
        self,
        client: httpx.Client,
        url: str,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        last: Optional[httpx.Response] = None
        for attempt in range(3):
            r = client.get(url, headers=headers, params=params)
            last = r
            if r.status_code == 429:
                wait = 2**attempt
                logger.warning("HubSpot rate limit (429), retrying in %ss...", wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        if last is not None:
            last.raise_for_status()
        raise RuntimeError("HubSpot GET failed after retries")

    def _company_to_bq_row(
        self, obj: Dict[str, Any], synced: str
    ) -> Dict[str, Any]:
        props = obj.get("properties") or {}
        return {
            "hubspot_company_id": str(obj.get("id", "")),
            "name": props.get("name"),
            "domain": props.get("domain"),
            "membership_status": props.get("membership_status"),
            "current_membership_status": props.get("current_membership_status"),
            "city": props.get("city"),
            "state": props.get("state"),
            "country": props.get("country"),
            "industry": props.get("industry"),
            "phone": props.get("phone"),
            "synced_at": synced,
        }

    def _contact_to_bq_row(
        self, obj: Dict[str, Any], synced: str
    ) -> Dict[str, Any]:
        props = obj.get("properties") or {}
        company_id = _extract_company_id_from_contact(obj)
        return {
            "hubspot_contact_id": str(obj.get("id", "")),
            "email": props.get("email"),
            "firstname": props.get("firstname"),
            "lastname": props.get("lastname"),
            "company_name": props.get("company"),
            "hubspot_company_id": company_id,
            "membership_status": props.get("membership_status"),
            "jobtitle": props.get("jobtitle"),
            "phone": props.get("phone"),
            "synced_at": synced,
        }

    def _truncate_and_insert(
        self,
        bq: Any,
        table_id: str,
        rows: List[Dict[str, Any]],
        label: str,
    ) -> None:
        logger.info("  Truncating %s...", table_id)
        bq.query(f"TRUNCATE TABLE `{table_id}`").result()
        if not rows:
            logger.info("  No rows to insert for %s", label)
            return
        batch_size = 5000
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            errors = bq.insert_rows_json(table_id, chunk)
            if errors:
                raise RuntimeError(f"BigQuery insert failed: {errors}")
            logger.info(
                "  Inserted %s batch %s (%s rows)",
                label,
                (i // batch_size) + 1,
                len(chunk),
            )
        logger.info("  Wrote %s %s to BigQuery", len(rows), label)

    def _phase2_push_new_users(
        self, client: httpx.Client, headers: Dict[str, str], bq: Any
    ) -> None:
        """Emails from usage_log that are not in hubspot.contacts (work emails only)."""
        domain_list = ", ".join(f"'{d}'" for d in _DISPOSABLE_DOMAINS)
        sql = f"""
        SELECT DISTINCT user_email
        FROM `{self.project_id}.cache.usage_log` u
        LEFT JOIN `{self.project_id}.hubspot.contacts` h
          ON LOWER(TRIM(u.user_email)) = LOWER(TRIM(h.email))
        WHERE h.email IS NULL
          AND u.user_email IS NOT NULL
          AND u.error_message IS NULL
          AND LOWER(SPLIT(u.user_email, '@')[OFFSET(1)]) NOT IN ({domain_list})
        """
        try:
            emails = []
            for r in bq.query(sql).result():
                v = r["user_email"]
                if v:
                    emails.append(str(v))
        except Exception as e:
            msg = f"Phase 2 query failed: {e}"
            logger.warning(msg)
            self.errors.append(msg)
            return

        logger.info("  Found %s new users to push to HubSpot", len(emails))
        if not emails:
            return

        url = f"{HUBSPOT_API}/crm/v3/objects/contacts/batch/create"
        batch_size = 100
        for i in range(0, len(emails), batch_size):
            chunk = emails[i : i + batch_size]
            payload = {
                "inputs": [{"properties": {"email": em}} for em in chunk],
            }
            r = client.post(url, headers=headers, json=payload)
            if r.status_code == 409:
                err = f"Batch create failed (HTTP 409): {r.text[:500]}"
                logger.error("  %s", err)
                self.errors.append(err)
                continue
            if r.status_code >= 400:
                err = f"Batch create failed (HTTP {r.status_code}): {r.text[:500]}"
                logger.error("  %s", err)
                self.errors.append(err)
                continue
            self._pushed += len(chunk)

        logger.info("  Total new contacts created in HubSpot: %s", self._pushed)
