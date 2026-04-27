"""BigQuery client core for the Analytics app.

Holds the BigQuery client singleton, the analytics cache, the
EVENTS_TABLE constant pool used across queries, and the
get_valid_user_filter SQL helper.
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional


# Initialize BigQuery client
_client = None

# =============================================================================
# CACHING - Analytics data updates nightly, so cache aggressively
# =============================================================================
_cache = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache (data only updates nightly)


def _cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments."""
    key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def _get_cached(key: str) -> Optional[Any]:
    """Get value from cache if not expired."""
    if key in _cache:
        data, timestamp = _cache[key]
        if datetime.utcnow() - timestamp < timedelta(seconds=CACHE_TTL_SECONDS):
            return data
        else:
            del _cache[key]
    return None


def _set_cached(key: str, value: Any) -> None:
    """Store value in cache with current timestamp."""
    _cache[key] = (value, datetime.utcnow())


def clear_analytics_cache() -> None:
    """Clear all cached analytics data. Call this after nightly data refresh."""
    global _cache
    _cache = {}


# Analytics data source configuration
#
# The unified view combines data from:
# 1. Backfilled historical events (pre-Firebase)
# 2. Firebase Analytics export (Jan 22-26, 2026 from justdata-f7da7)
# 3. GA4 BigQuery export (Jan 27+ from justdata-ncrc)
#
# All data flows into justdata-ncrc.firebase_analytics.all_events
ANALYTICS_DATASET = 'firebase_analytics'
EVENTS_TABLE = 'justdata-ncrc.firebase_analytics.all_events'

# Project where we run queries (where service account has bigquery.jobs.create permission)
# This is different from ANALYTICS_VIEW_PROJECT - we can query cross-project data
# using fully-qualified table names while running jobs in our home project
QUERY_PROJECT = 'justdata-ncrc'

# Backfill source (for sync_new_events function - syncs from usage_log to backfilled_events)
BACKFILL_PROJECT = 'justdata-ncrc'
BACKFILL_DATASET = 'cache'  # Source dataset for usage_log
BACKFILL_TARGET_DATASET = 'firebase_analytics'  # Target dataset for backfilled_events

# Target apps for main analytics counts
TARGET_APPS = [
    'lendsight_report',
    'bizsight_report',
    'branchsight_report',
    'mergermeter_report',
    'branchmapper_report',
    'dataexplorer_area_report',
    'dataexplorer_lender_report'
]

# Apps that track lender data (for lender-specific metrics)
LENDER_APPS = [
    'lendsight_report',
    'bizsight_report',
    'mergermeter_report',
    'lenderprofile_view',
    'dataexplorer_lender_report'
]

# Last sync tracking
_last_sync_check = None
SYNC_CHECK_INTERVAL_SECONDS = 3600  # Only check/sync once per hour


def get_valid_user_filter(table_alias: str = '') -> str:
    """
    Returns a SQL WHERE clause fragment to filter out invalid/test users.

    Filters out:
    - NULL user_id
    - Empty user_id
    - Anonymous user emails
    - Test user emails
    - GA4 client IDs (format: numbers.numbers) which are anonymous

    Args:
        table_alias: Optional table alias prefix (e.g., 'e.' for 'e.user_id')

    Returns:
        SQL WHERE clause fragment (without leading AND)

    Usage:
        query = f'''
            SELECT * FROM events e
            WHERE {get_valid_user_filter('e.')}
            AND other_conditions
        '''
    """
    prefix = f"{table_alias}" if table_alias else ""
    return f"""
        {prefix}user_id IS NOT NULL
        AND {prefix}user_id != ''
        AND ({prefix}user_email IS NULL OR (
            {prefix}user_email NOT LIKE '%test%'
            AND {prefix}user_email NOT LIKE '%anonymous%'
            AND {prefix}user_email != 'anonymous'
        ))
        AND NOT REGEXP_CONTAINS({prefix}user_id, r'^[0-9]+\\.[0-9]+$')
    """.strip()


def get_bigquery_client():
    """Get or create the BigQuery client for the Analytics app.

    Delegates to the shared client at justdata.shared.utils.bigquery_client.
    The shared client handles ANALYTICS_CREDENTIALS_JSON (and the standard
    GOOGLE_APPLICATION_CREDENTIALS_JSON fallback) plus per-app caching.
    """
    global _client
    if _client is None:
        from justdata.shared.utils.bigquery_client import (
            get_bigquery_client as shared_get_bigquery_client,
        )
        _client = shared_get_bigquery_client(project_id=QUERY_PROJECT, app_name='analytics')
    return _client
