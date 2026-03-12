"""
HubSpot Membership Lookup Service

Verifies user membership by looking up contacts and companies in the
hubspot BigQuery dataset (synced daily from HubSpot CRM).

Lookup flow:
  1. @ncrc.org → staff access (no lookup)
  2. Query hubspot.contacts by email (all domains, including personal)
  3. If contact found with active membership_status → member access
  4. If not found and personal email domain → public_registered (no domain fallback)
  5. If not found and work email → fallback: query hubspot.companies by domain
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ========================================
# Constants
# ========================================

HUBSPOT_MEMBERSHIP_FIELD = os.environ.get('HUBSPOT_MEMBERSHIP_FIELD', 'membership_status')

MEMBER_ACCESS_VALUES = ['CURRENT', 'LIFETIME MEMBER', 'NATIONAL PARTNER', 'RECIPROCAL']
GRACE_PERIOD_VALUES = ['GRACE PERIOD']
NO_ACCESS_VALUES = ['LAPSED', None, '']

PROJECT_ID = os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
CONTACTS_TABLE = f'{PROJECT_ID}.hubspot.contacts'
COMPANIES_TABLE = f'{PROJECT_ID}.hubspot.companies'

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


# ========================================
# Data Classes
# ========================================

@dataclass
class MembershipLookupResult:
    """Result of a membership lookup."""

    is_member: bool
    membership_status: Optional[str]
    company_name: Optional[str]
    contact_id: Optional[str]
    company_id: Optional[str]
    lookup_method: str  # 'email', 'domain', or 'none'
    email_template: str


# ========================================
# Helper Functions
# ========================================

def is_personal_email(email: str) -> bool:
    """Check if an email is from a personal email provider."""
    if not email:
        return True
    domain = email.lower().split('@')[-1]
    return domain in PERSONAL_EMAIL_DOMAINS


def is_ncrc_email(email: str) -> bool:
    """Check if an email is from NCRC domain."""
    if not email:
        return False
    return email.lower().endswith('@ncrc.org')


def _normalize_membership_status(status: Optional[str]) -> str:
    """Normalize membership status for comparison."""
    if not status:
        return ''
    return status.upper().strip()


def _is_active_member(status: str) -> bool:
    """Check if membership status grants member access."""
    return _normalize_membership_status(status) in MEMBER_ACCESS_VALUES


def _is_grace_period(status: str) -> bool:
    """Check if membership status is in grace period."""
    return _normalize_membership_status(status) in GRACE_PERIOD_VALUES


def determine_email_template(
    is_member: bool, is_grace: bool, is_ncrc: bool, is_personal: bool
) -> str:
    """Determine which email template to use for a new user."""
    if is_ncrc:
        return 'welcome_staff'
    if is_member:
        return 'welcome_member'
    if is_grace:
        return 'welcome_grace_period'
    if is_personal:
        return 'welcome_personal'
    return 'welcome_registered'


# ========================================
# BigQuery Lookup (primary path)
# ========================================

def _get_bq_client():
    """Get BigQuery client for hubspot dataset."""
    from justdata.shared.utils.bigquery_client import get_bigquery_client
    return get_bigquery_client(PROJECT_ID, app_name='HUBSPOT')


def _lookup_contact_in_bq(email: str) -> Optional[dict]:
    """Query hubspot.contacts in BigQuery by email."""
    client = _get_bq_client()
    query = f"""
        SELECT
            hubspot_contact_id,
            email,
            firstname,
            lastname,
            company_name,
            hubspot_company_id,
            membership_status
        FROM `{CONTACTS_TABLE}`
        WHERE LOWER(email) = @email
        LIMIT 1
    """
    job_config = _make_query_config([
        ("email", "STRING", email.lower()),
    ])
    rows = list(client.query(query, job_config=job_config).result())
    if rows:
        row = rows[0]
        return {
            'hubspot_contact_id': row.hubspot_contact_id,
            'email': row.email,
            'company_name': row.company_name,
            'hubspot_company_id': row.hubspot_company_id,
            'membership_status': row.membership_status,
        }
    return None


def _lookup_company_by_domain_in_bq(domain: str) -> Optional[dict]:
    """Query hubspot.companies in BigQuery by domain."""
    client = _get_bq_client()
    query = f"""
        SELECT
            hubspot_company_id,
            name,
            domain,
            membership_status,
            current_membership_status
        FROM `{COMPANIES_TABLE}`
        WHERE LOWER(domain) = @domain
        LIMIT 1
    """
    job_config = _make_query_config([
        ("domain", "STRING", domain.lower()),
    ])
    rows = list(client.query(query, job_config=job_config).result())
    if rows:
        row = rows[0]
        return {
            'hubspot_company_id': row.hubspot_company_id,
            'name': row.name,
            'domain': row.domain,
            'membership_status': row.membership_status,
            'current_membership_status': row.current_membership_status,
        }
    return None


def _make_query_config(params):
    """Build a BigQuery QueryJobConfig with scalar parameters."""
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    return QueryJobConfig(
        query_parameters=[
            ScalarQueryParameter(name, type_, val)
            for name, type_, val in params
        ]
    )


# ========================================
# Main Lookup Function
# ========================================

def lookup_membership_by_email(email: str) -> MembershipLookupResult:
    """
    Look up membership status using the BigQuery hubspot dataset.

    Flow (matches the plan diagram):
      1. @ncrc.org → staff
      2. Query hubspot.contacts by email (ALL domains)
      3. Contact found → check membership_status
      4. Not found + personal domain → public_registered
      5. Not found + work domain → fallback to company-by-domain
    """
    email_lower = email.lower().strip()

    # 1. NCRC staff
    if is_ncrc_email(email_lower):
        return MembershipLookupResult(
            is_member=True,
            membership_status='STAFF',
            company_name='NCRC',
            contact_id=None,
            company_id=None,
            lookup_method='none',
            email_template='welcome_staff',
        )

    try:
        # 2. Look up contact by email (regardless of domain type)
        contact = _lookup_contact_in_bq(email_lower)

        if contact:
            status = contact.get('membership_status', '')
            is_member = _is_active_member(status)
            is_grace = _is_grace_period(status)
            personal = is_personal_email(email_lower)

            return MembershipLookupResult(
                is_member=is_member or is_grace,
                membership_status=status,
                company_name=contact.get('company_name'),
                contact_id=contact.get('hubspot_contact_id'),
                company_id=contact.get('hubspot_company_id'),
                lookup_method='email',
                email_template=determine_email_template(
                    is_member, is_grace, False, personal
                ),
            )

        # 3. Contact not found — check if personal domain
        if is_personal_email(email_lower):
            return MembershipLookupResult(
                is_member=False,
                membership_status=None,
                company_name=None,
                contact_id=None,
                company_id=None,
                lookup_method='none',
                email_template='welcome_personal',
            )

        # 4. Work email, no contact → fallback: company by domain
        domain = email_lower.split('@')[-1]
        company = _lookup_company_by_domain_in_bq(domain)

        if company:
            status = company.get('membership_status') or company.get('current_membership_status', '')
            is_member = _is_active_member(status)
            is_grace = _is_grace_period(status)

            return MembershipLookupResult(
                is_member=is_member or is_grace,
                membership_status=status,
                company_name=company.get('name'),
                contact_id=None,
                company_id=company.get('hubspot_company_id'),
                lookup_method='domain',
                email_template=determine_email_template(
                    is_member, is_grace, False, False
                ),
            )

        # 5. Nothing found
        return MembershipLookupResult(
            is_member=False,
            membership_status=None,
            company_name=None,
            contact_id=None,
            company_id=None,
            lookup_method='domain',
            email_template='welcome_registered',
        )

    except Exception as e:
        logger.error(f"Membership lookup error for {email}: {e}", exc_info=True)
        return MembershipLookupResult(
            is_member=False,
            membership_status=None,
            company_name=None,
            contact_id=None,
            company_id=None,
            lookup_method='none',
            email_template='welcome_registered',
        )


# Backward-compatible alias (was previously async; now synchronous since BigQuery is sync)
lookup_membership_sync = lookup_membership_by_email
