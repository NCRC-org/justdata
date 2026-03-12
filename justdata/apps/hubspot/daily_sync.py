#!/usr/bin/env python3
"""
HubSpot Daily Sync Job

Bidirectional sync between HubSpot CRM and BigQuery:
  Phase 1: Pull all Companies and Contacts from HubSpot into BigQuery
  Phase 2: Push new JustData users (work-email, not in HubSpot) back to HubSpot

Run daily via Cloud Run Job + Cloud Scheduler.
Manual run:
    python -c "from justdata.apps.hubspot.daily_sync import HubSpotDailySync; HubSpotDailySync().run()"
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / '.env')

LOG_DIR = REPO_ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f'hubspot_sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# BigQuery config
PROJECT_ID = os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
HUBSPOT_DATASET = 'hubspot'
COMPANIES_TABLE = f'{PROJECT_ID}.{HUBSPOT_DATASET}.companies'
CONTACTS_TABLE = f'{PROJECT_ID}.{HUBSPOT_DATASET}.contacts'
USAGE_LOG_TABLE = f'{PROJECT_ID}.cache.usage_log'

# HubSpot API config
HUBSPOT_BASE_URL = 'https://api.hubapi.com'
HUBSPOT_PAGE_SIZE = 100

# Properties to fetch from HubSpot
COMPANY_PROPERTIES = [
    'name', 'domain', 'membership_status', 'current_membership_status',
    'city', 'state', 'country', 'industry', 'phone'
]
CONTACT_PROPERTIES = [
    'email', 'firstname', 'lastname', 'company',
    'membership_status', 'jobtitle', 'phone'
]

# Personal email domains (excluded from reverse push, not from membership lookup)
PERSONAL_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'aol.com', 'icloud.com', 'me.com', 'mac.com',
    'protonmail.com', 'proton.me', 'live.com', 'msn.com',
    'comcast.net', 'verizon.net', 'att.net', 'sbcglobal.net',
    'ymail.com', 'rocketmail.com', 'mail.com', 'zoho.com',
    'fastmail.com', 'tutanota.com', 'hey.com', 'pm.me',
    'googlemail.com', 'earthlink.net', 'cox.net', 'charter.net',
    'optonline.net', 'frontier.com', 'windstream.net'
}


class HubSpotDailySync:
    """Daily bidirectional sync between HubSpot CRM and BigQuery."""

    def __init__(self):
        self.access_token = os.getenv('HUBSPOT_ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError('HUBSPOT_ACCESS_TOKEN environment variable is required')

        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        self.bq_client = None
        self.stats = {
            'companies_synced': 0,
            'contacts_synced': 0,
            'new_users_pushed': 0,
            'errors': [],
        }

    def _get_bq_client(self):
        """Lazy-init BigQuery client using shared utility."""
        if self.bq_client is None:
            from justdata.shared.utils.bigquery_client import get_bigquery_client
            self.bq_client = get_bigquery_client(PROJECT_ID, app_name='HUBSPOT')
        return self.bq_client

    def run(self):
        """Execute the full sync pipeline."""
        start = datetime.now()
        logger.info('=' * 60)
        logger.info('HubSpot Daily Sync - Starting')
        logger.info(f'Time: {start.isoformat()}')
        logger.info('=' * 60)

        try:
            self._phase1_pull_companies()
            self._phase1_pull_contacts()
            self._phase2_push_new_users()

            elapsed = (datetime.now() - start).total_seconds()
            logger.info('=' * 60)
            logger.info('HubSpot Daily Sync - Complete')
            logger.info(f'Duration: {elapsed:.1f}s')
            logger.info(f'Companies synced: {self.stats["companies_synced"]}')
            logger.info(f'Contacts synced: {self.stats["contacts_synced"]}')
            logger.info(f'New users pushed to HubSpot: {self.stats["new_users_pushed"]}')
            if self.stats['errors']:
                logger.warning(f'Errors: {len(self.stats["errors"])}')
                for err in self.stats['errors'][:10]:
                    logger.warning(f'  - {err}')
            logger.info('=' * 60)

        except Exception as e:
            logger.error(f'Sync failed: {e}', exc_info=True)
            raise

    # =========================================================================
    # Phase 1: HubSpot -> BigQuery
    # =========================================================================

    def _phase1_pull_companies(self):
        """Fetch all companies from HubSpot and write to BigQuery."""
        logger.info('Phase 1a: Pulling companies from HubSpot...')
        import httpx

        all_companies = []
        after = None
        page = 0

        with httpx.Client(timeout=30.0) as client:
            while True:
                page += 1
                params = {
                    'limit': HUBSPOT_PAGE_SIZE,
                    'properties': ','.join(COMPANY_PROPERTIES),
                }
                if after:
                    params['after'] = after

                resp = client.get(
                    f'{HUBSPOT_BASE_URL}/crm/v3/objects/companies',
                    headers=self.headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

                results = data.get('results', [])
                for company in results:
                    props = company.get('properties', {})
                    all_companies.append({
                        'hubspot_company_id': company['id'],
                        'name': props.get('name'),
                        'domain': props.get('domain'),
                        'membership_status': props.get('membership_status'),
                        'current_membership_status': props.get('current_membership_status'),
                        'city': props.get('city'),
                        'state': props.get('state'),
                        'country': props.get('country'),
                        'industry': props.get('industry'),
                        'phone': props.get('phone'),
                    })

                paging = data.get('paging', {})
                next_link = paging.get('next', {})
                after = next_link.get('after')

                if page % 20 == 0:
                    logger.info(f'  Companies: fetched {len(all_companies)} so far (page {page})...')

                if not after:
                    break

                self._rate_limit_pause(page)

        logger.info(f'  Fetched {len(all_companies)} companies from HubSpot')
        self._write_companies_to_bq(all_companies)
        self.stats['companies_synced'] = len(all_companies)

    def _phase1_pull_contacts(self):
        """Fetch all contacts from HubSpot (with company associations) and write to BigQuery."""
        logger.info('Phase 1b: Pulling contacts from HubSpot...')
        import httpx

        all_contacts = []
        after = None
        page = 0

        with httpx.Client(timeout=30.0) as client:
            while True:
                page += 1
                params = {
                    'limit': HUBSPOT_PAGE_SIZE,
                    'properties': ','.join(CONTACT_PROPERTIES),
                    'associations': 'companies',
                }
                if after:
                    params['after'] = after

                resp = client.get(
                    f'{HUBSPOT_BASE_URL}/crm/v3/objects/contacts',
                    headers=self.headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

                results = data.get('results', [])
                for contact in results:
                    props = contact.get('properties', {})

                    company_id = None
                    associations = contact.get('associations', {})
                    companies_assoc = associations.get('companies', {})
                    assoc_results = companies_assoc.get('results', [])
                    if assoc_results:
                        company_id = assoc_results[0].get('id')

                    all_contacts.append({
                        'hubspot_contact_id': contact['id'],
                        'email': props.get('email'),
                        'firstname': props.get('firstname'),
                        'lastname': props.get('lastname'),
                        'company_name': props.get('company'),
                        'hubspot_company_id': company_id,
                        'membership_status': props.get('membership_status'),
                        'jobtitle': props.get('jobtitle'),
                        'phone': props.get('phone'),
                    })

                paging = data.get('paging', {})
                next_link = paging.get('next', {})
                after = next_link.get('after')

                if page % 50 == 0:
                    logger.info(f'  Contacts: fetched {len(all_contacts)} so far (page {page})...')

                if not after:
                    break

                self._rate_limit_pause(page)

        logger.info(f'  Fetched {len(all_contacts)} contacts from HubSpot')
        self._write_contacts_to_bq(all_contacts)
        self.stats['contacts_synced'] = len(all_contacts)

    def _write_companies_to_bq(self, companies: List[Dict[str, Any]]):
        """Truncate and reload companies table in BigQuery."""
        if not companies:
            logger.warning('  No companies to write')
            return

        client = self._get_bq_client()
        now = datetime.utcnow().isoformat()

        logger.info(f'  Truncating {COMPANIES_TABLE}...')
        client.query(f'DELETE FROM `{COMPANIES_TABLE}` WHERE TRUE').result()

        rows = []
        for c in companies:
            rows.append({
                'hubspot_company_id': c['hubspot_company_id'],
                'name': c.get('name'),
                'domain': c.get('domain'),
                'membership_status': c.get('membership_status'),
                'current_membership_status': c.get('current_membership_status'),
                'city': c.get('city'),
                'state': c.get('state'),
                'country': c.get('country'),
                'industry': c.get('industry'),
                'phone': c.get('phone'),
                'synced_at': now,
            })

        self._batch_insert_bq(COMPANIES_TABLE, rows, 'companies')

    def _write_contacts_to_bq(self, contacts: List[Dict[str, Any]]):
        """Truncate and reload contacts table in BigQuery."""
        if not contacts:
            logger.warning('  No contacts to write')
            return

        client = self._get_bq_client()
        now = datetime.utcnow().isoformat()

        logger.info(f'  Truncating {CONTACTS_TABLE}...')
        client.query(f'DELETE FROM `{CONTACTS_TABLE}` WHERE TRUE').result()

        rows = []
        for c in contacts:
            rows.append({
                'hubspot_contact_id': c['hubspot_contact_id'],
                'email': c.get('email'),
                'firstname': c.get('firstname'),
                'lastname': c.get('lastname'),
                'company_name': c.get('company_name'),
                'hubspot_company_id': c.get('hubspot_company_id'),
                'membership_status': c.get('membership_status'),
                'jobtitle': c.get('jobtitle'),
                'phone': c.get('phone'),
                'synced_at': now,
            })

        self._batch_insert_bq(CONTACTS_TABLE, rows, 'contacts')

    def _batch_insert_bq(self, table_id: str, rows: List[Dict], label: str):
        """Insert rows into BigQuery in batches using streaming insert."""
        client = self._get_bq_client()
        batch_size = 5000
        total = len(rows)

        for i in range(0, total, batch_size):
            batch = rows[i:i + batch_size]
            errors = client.insert_rows_json(table_id, batch)
            if errors:
                error_msg = f'BigQuery insert errors for {label} batch {i // batch_size + 1}: {errors[:3]}'
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)
            else:
                logger.info(f'  Inserted {label} batch {i // batch_size + 1} ({len(batch)} rows)')

        logger.info(f'  Wrote {total} {label} to BigQuery')

    # =========================================================================
    # Phase 2: BigQuery -> HubSpot (push new users)
    # =========================================================================

    def _phase2_push_new_users(self):
        """Find JustData users not in HubSpot and create them as contacts."""
        logger.info('Phase 2: Finding JustData users not in HubSpot...')

        client = self._get_bq_client()

        domains_list = ', '.join(f"'{d}'" for d in sorted(PERSONAL_EMAIL_DOMAINS))

        query = f"""
            SELECT DISTINCT
                u.user_email,
                u.user_type
            FROM `{USAGE_LOG_TABLE}` u
            LEFT JOIN `{CONTACTS_TABLE}` h
                ON LOWER(u.user_email) = LOWER(h.email)
            WHERE h.email IS NULL
                AND u.user_email IS NOT NULL
                AND u.error_message IS NULL
                AND LOWER(SPLIT(u.user_email, '@')[OFFSET(1)]) NOT IN ({domains_list})
            ORDER BY u.user_email
        """

        try:
            results = list(client.query(query).result())
        except Exception as e:
            error_msg = f'Failed to query new users: {e}'
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return

        if not results:
            logger.info('  No new users to push to HubSpot')
            return

        logger.info(f'  Found {len(results)} new users to push to HubSpot')

        new_contacts = []
        for row in results:
            new_contacts.append({
                'properties': {
                    'email': row.user_email,
                    'justdata_source': 'JustData Platform',
                }
            })

        self._batch_create_contacts(new_contacts)

    def _batch_create_contacts(self, contacts: List[Dict[str, Any]]):
        """Create contacts in HubSpot using the batch API."""
        import httpx

        batch_size = 100
        total_created = 0

        with httpx.Client(timeout=30.0) as client:
            for i in range(0, len(contacts), batch_size):
                batch = contacts[i:i + batch_size]

                try:
                    resp = client.post(
                        f'{HUBSPOT_BASE_URL}/crm/v3/objects/contacts/batch/create',
                        headers=self.headers,
                        json={'inputs': batch},
                    )

                    if resp.status_code == 201:
                        created = resp.json().get('results', [])
                        total_created += len(created)
                        logger.info(f'  Created batch {i // batch_size + 1}: {len(created)} contacts')
                    elif resp.status_code == 207:
                        # Partial success
                        data = resp.json()
                        created = data.get('results', [])
                        errors = data.get('errors', [])
                        total_created += len(created)
                        logger.warning(
                            f'  Batch {i // batch_size + 1}: {len(created)} created, '
                            f'{len(errors)} errors'
                        )
                        if errors:
                            self.stats['errors'].append(
                                f'Batch create partial failure: {errors[:3]}'
                            )
                    else:
                        error_msg = f'Batch create failed (HTTP {resp.status_code}): {resp.text[:200]}'
                        logger.error(f'  {error_msg}')
                        self.stats['errors'].append(error_msg)

                except Exception as e:
                    error_msg = f'Batch create exception: {e}'
                    logger.error(f'  {error_msg}')
                    self.stats['errors'].append(error_msg)

                self._rate_limit_pause(i // batch_size)

        self.stats['new_users_pushed'] = total_created
        logger.info(f'  Total new contacts created in HubSpot: {total_created}')

    # =========================================================================
    # Utility
    # =========================================================================

    def _rate_limit_pause(self, request_count: int):
        """Pause to stay within HubSpot rate limits (150 req / 10s)."""
        if request_count > 0 and request_count % 140 == 0:
            logger.info('  Rate limit pause (2s)...')
            time.sleep(2)


if __name__ == '__main__':
    HubSpotDailySync().run()
