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
    BIGQUERY_PROJECT = os.environ.get('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
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



config = AnalyticsConfig()
