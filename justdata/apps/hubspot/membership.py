"""
HubSpot Membership Lookup Service

Provides automated membership verification at registration time by looking up
users in HubSpot by email or email domain.
"""

import os
from dataclasses import dataclass
from typing import Optional

from .client import HubSpotClient


# ========================================
# Constants
# ========================================

# HubSpot membership field configuration
HUBSPOT_MEMBERSHIP_FIELD = os.environ.get('HUBSPOT_MEMBERSHIP_FIELD', 'membership_status')

# Membership values that grant full member access
MEMBER_ACCESS_VALUES = ['CURRENT', 'LIFETIME MEMBER', 'NATIONAL PARTNER', 'RECIPROCAL']
GRACE_PERIOD_VALUES = ['GRACE PERIOD']
NO_ACCESS_VALUES = ['LAPSED', None, '']

# Personal email domains that cannot be used for organization lookup
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
    """Result of a HubSpot membership lookup."""

    is_member: bool
    membership_status: Optional[str]
    company_name: Optional[str]
    contact_id: Optional[str]
    company_id: Optional[str]
    lookup_method: str  # 'email', 'domain', or 'none'
    email_template: str  # Template name for welcome email


# ========================================
# Helper Functions
# ========================================

def is_personal_email(email: str) -> bool:
    """
    Check if an email is from a personal email provider.

    Args:
        email: Email address to check

    Returns:
        True if email is from a personal domain
    """
    if not email:
        return True

    domain = email.lower().split('@')[-1]
    return domain in PERSONAL_EMAIL_DOMAINS


def is_ncrc_email(email: str) -> bool:
    """
    Check if an email is from NCRC domain.

    Args:
        email: Email address to check

    Returns:
        True if email is @ncrc.org
    """
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
    normalized = _normalize_membership_status(status)
    return normalized in MEMBER_ACCESS_VALUES


def _is_grace_period(status: str) -> bool:
    """Check if membership status is in grace period."""
    normalized = _normalize_membership_status(status)
    return normalized in GRACE_PERIOD_VALUES


def determine_email_template(
    is_member: bool,
    is_grace: bool,
    is_ncrc: bool,
    is_personal: bool
) -> str:
    """
    Determine which email template to use for a new user.

    Args:
        is_member: User is an active member
        is_grace: User is in grace period
        is_ncrc: User has @ncrc.org email
        is_personal: User has personal email domain

    Returns:
        Email template name
    """
    if is_ncrc:
        return 'welcome_staff'
    if is_personal:
        return 'welcome_personal'
    if is_member:
        return 'welcome_member'
    if is_grace:
        return 'welcome_grace_period'
    return 'welcome_registered'


# ========================================
# Main Lookup Function
# ========================================

async def lookup_membership_by_email(email: str) -> MembershipLookupResult:
    """
    Look up membership status in HubSpot by email.

    Lookup strategy:
    1. If @ncrc.org email: Return staff result (no HubSpot lookup)
    2. If personal email domain: Return registered result (no HubSpot lookup)
    3. Otherwise:
       a. Search HubSpot contacts by email
       b. If found, get membership_status from contact
       c. If not found, search companies by email domain
       d. If company found, get membership_status from company

    Args:
        email: User's email address

    Returns:
        MembershipLookupResult with membership details
    """
    email_lower = email.lower()

    # Check for NCRC staff
    if is_ncrc_email(email_lower):
        return MembershipLookupResult(
            is_member=True,  # Staff have full access
            membership_status='STAFF',
            company_name='NCRC',
            contact_id=None,
            company_id=None,
            lookup_method='none',
            email_template='welcome_staff'
        )

    # Check for personal email
    if is_personal_email(email_lower):
        return MembershipLookupResult(
            is_member=False,
            membership_status=None,
            company_name=None,
            contact_id=None,
            company_id=None,
            lookup_method='none',
            email_template='welcome_personal'
        )

    # Try HubSpot lookup for work emails
    try:
        client = HubSpotClient()

        # 1. First, search for contact by email
        contacts = await client.search_contacts(
            filters=[{
                "propertyName": "email",
                "operator": "EQ",
                "value": email_lower
            }]
        )

        if contacts:
            contact = contacts[0]
            props = contact.get('properties', {})
            membership_status = props.get(HUBSPOT_MEMBERSHIP_FIELD, '')

            is_member = _is_active_member(membership_status)
            is_grace = _is_grace_period(membership_status)

            return MembershipLookupResult(
                is_member=is_member or is_grace,  # Grace period gets member access
                membership_status=membership_status,
                company_name=props.get('company'),
                contact_id=contact.get('id'),
                company_id=None,
                lookup_method='email',
                email_template=determine_email_template(is_member, is_grace, False, False)
            )

        # 2. If no contact found, search companies by domain
        domain = email_lower.split('@')[-1]

        companies = await client.search_companies(
            filters=[{
                "propertyName": "domain",
                "operator": "EQ",
                "value": domain
            }],
            properties=['name', 'domain', HUBSPOT_MEMBERSHIP_FIELD]
        )

        if companies:
            company = companies[0]
            props = company.get('properties', {})
            membership_status = props.get(HUBSPOT_MEMBERSHIP_FIELD, '')

            is_member = _is_active_member(membership_status)
            is_grace = _is_grace_period(membership_status)

            return MembershipLookupResult(
                is_member=is_member or is_grace,
                membership_status=membership_status,
                company_name=props.get('name'),
                contact_id=None,
                company_id=company.get('id'),
                lookup_method='domain',
                email_template=determine_email_template(is_member, is_grace, False, False)
            )

        # 3. No match found - registered non-member
        return MembershipLookupResult(
            is_member=False,
            membership_status=None,
            company_name=None,
            contact_id=None,
            company_id=None,
            lookup_method='domain',  # We tried domain lookup
            email_template='welcome_registered'
        )

    except Exception as e:
        # Log error but don't fail registration
        print(f"HubSpot lookup error for {email}: {e}")

        # Return non-member result on error
        return MembershipLookupResult(
            is_member=False,
            membership_status=None,
            company_name=None,
            contact_id=None,
            company_id=None,
            lookup_method='none',
            email_template='welcome_registered'
        )


def lookup_membership_sync(email: str) -> MembershipLookupResult:
    """
    Synchronous wrapper for lookup_membership_by_email.

    Use this in non-async contexts like Flask routes.

    Args:
        email: User's email address

    Returns:
        MembershipLookupResult with membership details
    """
    import asyncio

    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    lookup_membership_by_email(email)
                )
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(lookup_membership_by_email(email))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(lookup_membership_by_email(email))
