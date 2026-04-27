"""User profile queries."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from justdata.apps.analytics.bq.client import (
    EVENTS_TABLE,
    QUERY_PROJECT,
    LENDER_APPS,
    TARGET_APPS,
    _cache_key,
    _get_cached,
    _set_cached,
    get_bigquery_client,
    get_valid_user_filter,
)
from justdata.apps.analytics.bq.transforms import (
    _enrich_lender_interest_with_coordinates,
    _enrich_lender_names,
    _enrich_users_from_firestore,
    _enrich_with_coordinates,
    _enrich_with_county_names,
    _is_ga4_client_id,
    _lookup_single_lender_name,
    _normalize_state_to_code,
    geocode_ip,
)
from justdata.apps.analytics.bq.centroids import (
    lookup_cbsa_centroid,
    lookup_county_centroid,
    validate_coordinates,
)


def get_users(
    days: int = 90,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get list of users with their activity summary.

    Note: User email, type, and organization are not in BigQuery events table.
    These should be enriched from Firestore user profiles if needed.

    Args:
        days: Number of days to look back (0 = all time)
        search: Optional search term for user_id

    Returns:
        List of user records with activity counts
    """
    # Check cache first
    cache_key = _cache_key('get_users', days=days, search=search)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    client = get_bigquery_client()
    target_apps_str = "', '".join(TARGET_APPS)

    date_filter = f"AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""
    search_filter = ""
    if search:
        search_filter = f"AND user_id LIKE '%{search}%'"

    # Apply valid user filter to exclude test/anonymous users
    user_filter = get_valid_user_filter()

    query = f"""
        SELECT
            user_id,
            COUNT(*) AS total_reports,
            COUNT(DISTINCT county_fips) AS counties_researched,
            COUNT(DISTINCT lender_id) AS lenders_researched,
            MAX(event_timestamp) AS last_activity,
            MIN(event_timestamp) AS first_activity,
            ARRAY_AGG(DISTINCT event_name ORDER BY event_name) AS apps_used
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            AND {user_filter}
            {date_filter}
            {search_filter}
        GROUP BY user_id
        ORDER BY total_reports DESC
        LIMIT 200
    """

    try:
        results = client.query(query).result()
        data = [dict(row) for row in results]

        # Enrich with Firestore user profile data
        data = _enrich_users_from_firestore(data)

        _set_cached(cache_key, data)
        return data
    except Exception as e:
        print(f"BigQuery error in get_users: {e}")
        return []


def get_user_activity(
    user_id: str,
    days: int = 90
) -> Dict[str, Any]:
    """
    Get detailed activity for a specific user.

    Args:
        user_id: The user ID to look up
        days: Number of days to look back (0 = all time)

    Returns:
        Dict with user details and activity breakdown
    """
    client = get_bigquery_client()
    target_apps_str = "', '".join(TARGET_APPS)

    date_filter = f"AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    # Get user summary (user email, type, org from Firestore, not BigQuery)
    summary_query = f"""
        SELECT
            user_id,
            COUNT(*) AS total_reports,
            COUNT(DISTINCT county_fips) AS counties_researched,
            COUNT(DISTINCT lender_id) AS lenders_researched,
            MAX(event_timestamp) AS last_activity,
            MIN(event_timestamp) AS first_activity
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            AND user_id = '{user_id}'
            {date_filter}
        GROUP BY user_id
    """

    # Get activity by app
    by_app_query = f"""
        SELECT
            event_name,
            COUNT(*) AS count
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            AND user_id = '{user_id}'
            {date_filter}
        GROUP BY event_name
        ORDER BY count DESC
    """

    # Get recent reports
    recent_query = f"""
        SELECT
            event_timestamp,
            event_name,
            county_name,
            state,
            lender_name,
            lender_id
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            AND user_id = '{user_id}'
            {date_filter}
        ORDER BY event_timestamp DESC
        LIMIT 20
    """

    # Get counties researched
    counties_query = f"""
        SELECT
            county_fips,
            county_name,
            state,
            COUNT(*) AS report_count
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            AND user_id = '{user_id}'
            AND county_fips IS NOT NULL
            {date_filter}
        GROUP BY county_fips, county_name, state
        ORDER BY report_count DESC
        LIMIT 20
    """

    # Get lenders researched
    lenders_query = f"""
        SELECT
            lender_id,
            lender_name,
            COUNT(*) AS report_count
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            AND user_id = '{user_id}'
            AND lender_id IS NOT NULL
            {date_filter}
        GROUP BY lender_id, lender_name
        ORDER BY report_count DESC
        LIMIT 20
    """

    try:
        # Execute queries
        summary_result = list(client.query(summary_query).result())
        by_app_result = [dict(row) for row in client.query(by_app_query).result()]
        recent_result = [dict(row) for row in client.query(recent_query).result()]
        counties_result = [dict(row) for row in client.query(counties_query).result()]
        lenders_result = [dict(row) for row in client.query(lenders_query).result()]

        if not summary_result:
            return {'error': 'User not found'}

        summary = dict(summary_result[0])

        return {
            'user': summary,
            'by_app': by_app_result,
            'recent_reports': recent_result,
            'counties': counties_result,
            'lenders': lenders_result
        }
    except Exception as e:
        print(f"BigQuery error in get_user_activity: {e}")
        return {'error': str(e)}


def get_entity_users(
    entity_type: str,
    entity_id: str,
    days: int = 90
) -> List[Dict[str, Any]]:
    """
    Get users researching a specific entity (county or lender).

    Enriches user data from Firestore profiles to include email, user_type,
    and organization_name.

    Args:
        entity_type: 'county' or 'lender'
        entity_id: FIPS code (county) or LEI (lender)
        days: Number of days to look back (0 = all time)

    Returns:
        List of user records with activity counts for this entity
    """
    client = get_bigquery_client()
    target_apps_str = "', '".join(TARGET_APPS)
    date_filter = f"AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    # Apply valid user filter to exclude test/anonymous users
    user_filter = get_valid_user_filter()

    # Build entity filter based on type
    if entity_type == 'county':
        entity_filter = f"AND county_fips = '{entity_id}'"
    elif entity_type == 'lender':
        entity_filter = f"AND lender_id = '{entity_id}'"
    else:
        return []

    query = f"""
        SELECT
            user_id,
            COUNT(*) AS report_count,
            MAX(event_timestamp) AS last_activity,
            MIN(event_timestamp) AS first_activity
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            AND {user_filter}
            {entity_filter}
            {date_filter}
        GROUP BY user_id
        ORDER BY report_count DESC
        LIMIT 50
    """

    try:
        results = client.query(query).result()
        users = [dict(row) for row in results]

        # Enrich with Firestore user profile data
        users = _enrich_users_from_firestore(users)

        return users
    except Exception as e:
        print(f"BigQuery error in get_entity_users: {e}")
        return []


