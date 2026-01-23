"""
HubSpot Integration for Analytics Application.

This module provides the structure for linking JustData/Firebase users
to HubSpot contacts and companies for enhanced analytics and coalition building.

# =============================================================================
# INTEGRATION OVERVIEW
# =============================================================================
#
# PURPOSE:
#   Link Firebase authenticated users to HubSpot CRM records to:
#   1. Identify which organizations are researching the same entities
#   2. Enable coalition-building outreach based on shared interests
#   3. Track organizational engagement with JustData tools
#   4. Provide org-level analytics (not just anonymous user_id)
#
# ARCHITECTURE:
#
#   +------------------+      +-------------------+      +------------------+
#   |  Firebase Auth   |----->|  Firestore User   |----->|  HubSpot Contact |
#   |  (user_id)       |      |  Profile          |      |  (contact_id)    |
#   +------------------+      +-------------------+      +------------------+
#                                     |                          |
#                                     |                          v
#                                     |                  +------------------+
#                                     +----------------->|  HubSpot Company |
#                                                        |  (company_id)    |
#                                                        +------------------+
#
# LINKING METHODS (choose one or more):
#
#   Option A: Email Match
#     - User signs in with email via Firebase Auth
#     - Look up HubSpot contact by email
#     - Store hubspot_contact_id in Firestore user profile
#
#   Option B: Manual Admin Linking
#     - Admin interface to manually link users to HubSpot contacts
#     - Useful for users with different email addresses
#
#   Option C: HubSpot OAuth
#     - User authorizes JustData to access their HubSpot identity
#     - Automatically links their HubSpot contact
#
#   Option D: Domain-Based Inference
#     - Match user email domain to HubSpot company domain
#     - Less precise but works for org-level analytics
#
# =============================================================================
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# DATA MODELS
# =============================================================================

class HubSpotLinkStatus(Enum):
    """Status of the user-to-HubSpot link."""
    NOT_LINKED = "not_linked"
    PENDING = "pending"           # Link requested, awaiting verification
    LINKED = "linked"             # Successfully linked
    FAILED = "failed"             # Link attempt failed
    MANUALLY_LINKED = "manual"    # Admin manually linked


@dataclass
class HubSpotContactLink:
    """
    Represents the link between a Firebase user and HubSpot contact.

    This would be stored in Firestore under the user's profile document
    at path: users/{firebase_uid}/hubspot_link
    """
    # Firebase identifiers
    firebase_uid: str
    firebase_email: Optional[str] = None

    # HubSpot identifiers
    hubspot_contact_id: Optional[str] = None
    hubspot_company_id: Optional[str] = None

    # Cached HubSpot data (denormalized for query performance)
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    company_type: Optional[str] = None  # nonprofit, government, academic, etc.

    # Link metadata
    link_status: HubSpotLinkStatus = HubSpotLinkStatus.NOT_LINKED
    link_method: Optional[str] = None  # 'email_match', 'manual', 'oauth', 'domain'
    linked_at: Optional[str] = None    # ISO timestamp
    linked_by: Optional[str] = None    # Admin UID if manually linked

    # Sync metadata
    last_synced_at: Optional[str] = None
    sync_error: Optional[str] = None


@dataclass
class OrganizationAnalytics:
    """
    Aggregated analytics at the organization level.

    Used for coalition building - shows which orgs are researching
    the same entities.
    """
    hubspot_company_id: str
    company_name: str
    company_type: Optional[str]

    # Aggregated activity
    total_users: int
    total_events: int

    # Research focus
    counties_researched: List[str]      # FIPS codes
    lenders_researched: List[str]       # LEIs or RSSDIDs
    apps_used: List[str]                # App names

    # Activity window
    first_activity: str
    last_activity: str


# =============================================================================
# FIRESTORE SCHEMA
# =============================================================================
"""
Firestore Collection Structure for HubSpot Integration:

users/{firebase_uid}
├── email: string
├── userType: string (existing field)
├── displayName: string
├── ... (existing user fields)
│
└── hubspot/  (subcollection or nested object)
    ├── contact_id: string
    ├── company_id: string
    ├── contact_name: string
    ├── company_name: string
    ├── company_type: string
    ├── link_status: string
    ├── link_method: string
    ├── linked_at: timestamp
    ├── last_synced: timestamp
    └── sync_error: string (if any)

# Alternative: Separate collection for HubSpot links
hubspot_links/{firebase_uid}
├── firebase_uid: string
├── firebase_email: string
├── hubspot_contact_id: string
├── hubspot_company_id: string
├── ... (all HubSpotContactLink fields)
│
# Index for reverse lookups
hubspot_links_by_company/{hubspot_company_id}
├── users: array<firebase_uid>

# Index for coalition queries
hubspot_links_by_contact/{hubspot_contact_id}
├── firebase_uid: string
"""


# =============================================================================
# HUBSPOT API CLIENT (PLACEHOLDER)
# =============================================================================

class HubSpotClient:
    """
    Client for interacting with HubSpot API.

    TODO: Implement using hubspot-api-client package
    pip install hubspot-api-client

    Required HubSpot scopes:
    - crm.objects.contacts.read
    - crm.objects.companies.read
    - crm.objects.contacts.write (if creating/updating contacts)
    """

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize HubSpot client.

        Args:
            access_token: HubSpot private app access token
                         Get from: HubSpot Settings -> Integrations -> Private Apps
        """
        self.access_token = access_token
        # TODO: Initialize hubspot.Client
        # from hubspot import HubSpot
        # self.client = HubSpot(access_token=access_token)
        pass

    def get_contact_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Look up a HubSpot contact by email address.

        Args:
            email: Email address to search for

        Returns:
            Contact record with id, properties, and associated company

        TODO: Implement with:
            self.client.crm.contacts.basic_api.get_by_id(
                contact_id,
                properties=["email", "firstname", "lastname", "company"],
                associations=["companies"]
            )
        """
        # PLACEHOLDER
        pass

    def get_contact_by_id(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a HubSpot contact by ID.

        Args:
            contact_id: HubSpot contact ID

        Returns:
            Contact record with properties and associations
        """
        # PLACEHOLDER
        pass

    def get_company_by_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a HubSpot company by ID.

        Args:
            company_id: HubSpot company ID

        Returns:
            Company record with properties

        TODO: Implement with:
            self.client.crm.companies.basic_api.get_by_id(
                company_id,
                properties=["name", "domain", "industry", "type"]
            )
        """
        # PLACEHOLDER
        pass

    def search_companies_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Search for HubSpot companies by domain.

        Args:
            domain: Company website domain (e.g., "ncrc.org")

        Returns:
            List of matching company records
        """
        # PLACEHOLDER
        pass

    def get_contacts_for_company(self, company_id: str) -> List[Dict[str, Any]]:
        """
        Get all contacts associated with a company.

        Args:
            company_id: HubSpot company ID

        Returns:
            List of contact records
        """
        # PLACEHOLDER
        pass


# =============================================================================
# LINKING SERVICE (PLACEHOLDER)
# =============================================================================

class UserHubSpotLinkingService:
    """
    Service for managing links between Firebase users and HubSpot contacts.
    """

    def __init__(self, hubspot_client: HubSpotClient):
        self.hubspot = hubspot_client
        # TODO: Initialize Firestore client
        # from firebase_admin import firestore
        # self.db = firestore.client()

    def link_user_by_email(self, firebase_uid: str, email: str) -> HubSpotContactLink:
        """
        Attempt to link a Firebase user to HubSpot by email match.

        Process:
        1. Search HubSpot for contact with matching email
        2. If found, get associated company
        3. Store link in Firestore user profile
        4. Return link status

        Args:
            firebase_uid: Firebase user ID
            email: User's email address

        Returns:
            HubSpotContactLink with result status
        """
        # PLACEHOLDER IMPLEMENTATION
        link = HubSpotContactLink(
            firebase_uid=firebase_uid,
            firebase_email=email,
            link_status=HubSpotLinkStatus.NOT_LINKED
        )

        # TODO:
        # 1. contact = self.hubspot.get_contact_by_email(email)
        # 2. if contact: get company associations
        # 3. Store in Firestore: db.collection('users').document(firebase_uid).update(...)
        # 4. Update link status

        return link

    def link_user_manually(
        self,
        firebase_uid: str,
        hubspot_contact_id: str,
        admin_uid: str
    ) -> HubSpotContactLink:
        """
        Manually link a Firebase user to a HubSpot contact (admin action).

        Args:
            firebase_uid: Firebase user ID to link
            hubspot_contact_id: HubSpot contact ID to link to
            admin_uid: Admin user performing the link

        Returns:
            HubSpotContactLink with result status
        """
        # PLACEHOLDER
        pass

    def get_user_link(self, firebase_uid: str) -> Optional[HubSpotContactLink]:
        """
        Get the HubSpot link for a Firebase user.

        Args:
            firebase_uid: Firebase user ID

        Returns:
            HubSpotContactLink if linked, None otherwise
        """
        # TODO: Fetch from Firestore
        # doc = db.collection('users').document(firebase_uid).get()
        # return HubSpotContactLink from doc data
        pass

    def get_users_by_company(self, hubspot_company_id: str) -> List[str]:
        """
        Get all Firebase user IDs linked to a HubSpot company.

        Useful for org-level analytics queries.

        Args:
            hubspot_company_id: HubSpot company ID

        Returns:
            List of Firebase user IDs
        """
        # TODO: Query Firestore for users with matching company_id
        pass

    def sync_user_data(self, firebase_uid: str) -> HubSpotContactLink:
        """
        Sync/refresh HubSpot data for a linked user.

        Pulls latest contact and company data from HubSpot
        and updates Firestore cache.

        Args:
            firebase_uid: Firebase user ID

        Returns:
            Updated HubSpotContactLink
        """
        # TODO: Re-fetch from HubSpot and update Firestore
        pass


# =============================================================================
# ANALYTICS ENRICHMENT (PLACEHOLDER)
# =============================================================================

class HubSpotAnalyticsEnricher:
    """
    Enriches analytics data with HubSpot organization context.

    Used by bigquery_client.py to add org-level insights to queries.
    """

    def __init__(self, linking_service: UserHubSpotLinkingService):
        self.linking = linking_service

    def enrich_user_with_org(self, user_id: str) -> Dict[str, Any]:
        """
        Get organization info for a user.

        Args:
            user_id: Firebase user ID

        Returns:
            Dict with company_name, company_type, etc.
        """
        # TODO: Look up link and return org data
        pass

    def get_organization_activity(
        self,
        hubspot_company_id: str,
        days: int = 90
    ) -> OrganizationAnalytics:
        """
        Get aggregated activity for an organization.

        Args:
            hubspot_company_id: HubSpot company ID
            days: Lookback period

        Returns:
            OrganizationAnalytics with aggregated data
        """
        # TODO:
        # 1. Get all users linked to company
        # 2. Query BigQuery for their combined activity
        # 3. Aggregate results
        pass

    def find_coalition_partners(
        self,
        entity_type: str,  # 'county' or 'lender'
        entity_id: str,    # FIPS or LEI
        min_orgs: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find organizations researching the same entity.

        This is the core coalition-building query.

        Args:
            entity_type: 'county' or 'lender'
            entity_id: County FIPS code or Lender LEI
            min_orgs: Minimum organizations to consider a coalition opportunity

        Returns:
            List of organizations with their research activity on this entity
        """
        # TODO:
        # 1. Query BigQuery for users researching this entity
        # 2. Map user_ids to HubSpot companies
        # 3. Aggregate by company
        # 4. Return companies with >= min_orgs
        pass


# =============================================================================
# CONFIGURATION
# =============================================================================
"""
Required Environment Variables:

HUBSPOT_ACCESS_TOKEN - Private app access token from HubSpot
    Get from: HubSpot Settings -> Integrations -> Private Apps
    Required scopes:
    - crm.objects.contacts.read
    - crm.objects.companies.read

Optional:
HUBSPOT_SYNC_INTERVAL_HOURS - How often to sync user data (default: 24)
"""


# =============================================================================
# ADMIN API ENDPOINTS (PLACEHOLDER)
# =============================================================================
"""
These endpoints would be added to blueprint.py for admin users:

GET /analytics/api/hubspot/users
    List all users with their HubSpot link status

GET /analytics/api/hubspot/users/<firebase_uid>
    Get HubSpot link details for a specific user

POST /analytics/api/hubspot/users/<firebase_uid>/link
    Manually link a user to HubSpot contact
    Body: { "hubspot_contact_id": "..." }

POST /analytics/api/hubspot/users/<firebase_uid>/sync
    Force sync of user's HubSpot data

GET /analytics/api/hubspot/companies
    List all HubSpot companies with linked users

GET /analytics/api/hubspot/companies/<company_id>/activity
    Get organization-level activity analytics

GET /analytics/api/hubspot/coalitions/<entity_type>/<entity_id>
    Get coalition opportunities for an entity
    (which orgs are researching same county/lender)
"""


# =============================================================================
# IMPLEMENTATION CHECKLIST
# =============================================================================
"""
Phase 1: Basic Linking
[ ] Install hubspot-api-client package
[ ] Create HubSpot private app with required scopes
[ ] Implement HubSpotClient.get_contact_by_email()
[ ] Implement HubSpotClient.get_company_by_id()
[ ] Add hubspot subcollection to Firestore user schema
[ ] Implement UserHubSpotLinkingService.link_user_by_email()
[ ] Add admin endpoint to manually link users

Phase 2: Automatic Linking
[ ] Add post-signup hook to attempt email-based linking
[ ] Handle users with no HubSpot match gracefully
[ ] Add UI indicator showing link status in user profile

Phase 3: Analytics Enrichment
[ ] Implement HubSpotAnalyticsEnricher.enrich_user_with_org()
[ ] Update BigQuery queries to join with HubSpot data
[ ] Add org-level filters to dashboard
[ ] Implement coalition partner discovery

Phase 4: Advanced Features
[ ] Two-way sync (update HubSpot with JustData activity)
[ ] Organization activity dashboards
[ ] Coalition outreach tools
[ ] Activity-based lead scoring for HubSpot
"""
