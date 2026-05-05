"""Usage / activity queries."""
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


def get_user_locations(
    days: int = 90,
    state: Optional[str] = None,
    user_types: Optional[List[str]] = None,
    exclude_user_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get user clusters by city/state with coordinates.

    Args:
        days: Number of days to look back (0 = all time)
        state: Optional state filter (2-letter code)
        user_types: Optional list of user types to include
        exclude_user_types: Optional list of user types to exclude

    Returns:
        List of location records with user counts
    """
    # Check cache first
    cache_key = _cache_key('get_user_locations', days=days, state=state,
                           user_types=user_types, exclude_user_types=exclude_user_types)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    client = get_bigquery_client()

    date_filter = f"AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    # User type filter
    user_type_filter = ""
    if user_types:
        types_str = "', '".join(user_types)
        user_type_filter = f" AND user_type IN ('{types_str}')"
    elif exclude_user_types:
        types_str = "', '".join(exclude_user_types)
        user_type_filter = f" AND (user_type IS NULL OR user_type NOT IN ('{types_str}'))"

    # Use target apps for user locations
    target_apps_str = "', '".join(TARGET_APPS)

    query = f"""
        SELECT
            county_fips,
            state,
            county_name AS city,
            COUNT(DISTINCT user_id) AS unique_users,
            COUNT(*) AS total_events,
            MAX(event_timestamp) AS last_activity,
            hubspot_contact_id,
            hubspot_company_id,
            organization_name
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            AND state IS NOT NULL
            {date_filter}
            {user_type_filter}
    """

    if state:
        query += f" AND state = '{state}'"

    query += """
        GROUP BY county_fips, state, county_name, hubspot_contact_id, hubspot_company_id, organization_name
        ORDER BY unique_users DESC
        LIMIT 500
    """

    try:
        results = client.query(query).result()
        data = [dict(row) for row in results]

        # Enrich with county centroid coordinates
        data = _enrich_with_coordinates(data, 'county_fips')

        _set_cached(cache_key, data)
        return data
    except Exception as e:
        print(f"BigQuery error in get_user_locations: {e}")
        return []


def get_research_activity(
    days: int = 90,
    app: Optional[str] = None,
    state: Optional[str] = None,
    user_types: Optional[List[str]] = None,
    exclude_user_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get counties being researched with report counts.

    Args:
        days: Number of days to look back (0 = all time)
        app: Optional app filter (e.g., 'lendsight_report')
        state: Optional state filter
        user_types: Optional list of user types to include
        exclude_user_types: Optional list of user types to exclude

    Returns:
        List of county research records
    """
    # Check cache first
    cache_key = _cache_key('get_research_activity', days=days, app=app, state=state,
                           user_types=user_types, exclude_user_types=exclude_user_types)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    client = get_bigquery_client()

    date_filter = f"AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    # User type filter
    user_type_filter = ""
    if user_types:
        types_str = "', '".join(user_types)
        user_type_filter = f" AND user_type IN ('{types_str}')"
    elif exclude_user_types:
        types_str = "', '".join(exclude_user_types)
        user_type_filter = f" AND (user_type IS NULL OR user_type NOT IN ('{types_str}'))"

    # Use target apps for research activity
    target_apps_str = "', '".join(TARGET_APPS)

    query = f"""
        SELECT
            county_fips,
            state,
            county_name,
            event_name AS app_name,
            COUNT(DISTINCT user_id) AS unique_users,
            COUNT(*) AS report_count,
            MAX(event_timestamp) AS last_activity
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            {date_filter}
            {user_type_filter}
    """

    if app:
        query += f" AND event_name = '{app}'"
    if state:
        query += f" AND state = '{state}'"

    query += """
        GROUP BY county_fips, state, county_name, app_name
        ORDER BY report_count DESC
        LIMIT 500
    """

    try:
        results = client.query(query).result()
        data = [dict(row) for row in results]

        # Enrich with county names from geo table if missing
        data_needing_names = [d for d in data if d.get('county_fips') and not d.get('county_name')]
        if data_needing_names:
            data = _enrich_with_county_names(client, data)

        # Enrich with county centroid coordinates
        data = _enrich_with_coordinates(data, 'county_fips')

        _set_cached(cache_key, data)
        return data
    except Exception as e:
        print(f"BigQuery error in get_research_activity: {e}")
        return []



def get_user_activity_timeline(days: int = 30) -> List[Dict[str, Any]]:
    """
    Get daily activity counts for timeline chart.

    Args:
        days: Number of days to look back (0 = all time)

    Returns:
        List of daily activity records
    """
    # Check cache first
    cache_key = _cache_key('get_user_activity_timeline', days=days)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    client = get_bigquery_client()

    date_filter = f"AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    query = f"""
        SELECT
            DATE(event_timestamp) AS date,
            COUNT(*) AS event_count,
            COUNT(DISTINCT user_id) AS unique_users
        FROM `{EVENTS_TABLE}`
        WHERE 1=1
        {date_filter}
        GROUP BY date
        ORDER BY date ASC
    """

    try:
        results = client.query(query).result()
        data = [dict(row) for row in results]
        _set_cached(cache_key, data)
        return data
    except Exception as e:
        print(f"BigQuery error in get_user_activity_timeline: {e}")
        return []


