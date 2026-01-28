"""
Configuration for Analytics application.
"""

import os


class AnalyticsConfig:
    """Analytics application configuration."""

    APP_NAME = "Analytics"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Internal analytics dashboard for JustData usage patterns"

    # BigQuery configuration
    BIGQUERY_PROJECT = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')
    ANALYTICS_DATASET = 'firebase_analytics'

    # Firebase configuration
    FIREBASE_PROJECT = 'justdata-ncrc'
    MEASUREMENT_ID = 'G-DWS9XPNT7J'

    # Default query parameters
    DEFAULT_DAYS = 90
    DEFAULT_MIN_USERS = 3

    # Cache settings (seconds)
    CACHE_TTL = 300  # 5 minutes

    # Port for standalone running
    PORT = int(os.environ.get('ANALYTICS_PORT', 8087))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    # =========================================================================
    # HUBSPOT INTEGRATION (PLANNED)
    # =========================================================================
    #
    # To enable HubSpot integration for linking users to CRM contacts:
    #
    # 1. Create a HubSpot Private App:
    #    - Go to HubSpot Settings -> Integrations -> Private Apps
    #    - Create new app with scopes:
    #      * crm.objects.contacts.read
    #      * crm.objects.companies.read
    #    - Copy the access token
    #
    # 2. Set environment variable:
    #    HUBSPOT_ACCESS_TOKEN=pat-na1-xxxxxxxx
    #
    # 3. The integration will:
    #    - Link Firebase users to HubSpot contacts by email
    #    - Show organization name in user popups
    #    - Enable coalition building with org-level insights
    #
    # See hubspot_integration.py for implementation details.
    # =========================================================================

    # HubSpot API Configuration
    HUBSPOT_ACCESS_TOKEN = os.environ.get('HUBSPOT_ACCESS_TOKEN', None)
    HUBSPOT_ENABLED = HUBSPOT_ACCESS_TOKEN is not None

    # Firestore collection for HubSpot links
    HUBSPOT_LINKS_COLLECTION = 'hubspot_links'

    # Sync settings
    HUBSPOT_SYNC_INTERVAL_HOURS = int(os.environ.get('HUBSPOT_SYNC_INTERVAL_HOURS', 24))


config = AnalyticsConfig()
