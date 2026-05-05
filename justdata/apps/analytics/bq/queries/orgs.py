"""Organization-level / coalition queries."""
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


def get_coalition_opportunities(
    days: int = 90,
    min_users: int = 3,
    entity_type: Optional[str] = None,
    state: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get entities (counties or lenders) with multiple researchers.
    Useful for identifying coalition-building opportunities.

    Args:
        days: Number of days to look back (0 = all time)
        min_users: Minimum unique users researching same entity
        entity_type: Filter by 'county' or 'lender'
        state: Filter by state code (e.g., 'CA', 'NY')

    Returns:
        List of coalition opportunity records
    """
    # Check cache first
    cache_key = _cache_key('get_coalition_opportunities', days=days, min_users=min_users, entity_type=entity_type, state=state)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    client = get_bigquery_client()

    date_filter = f"AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""
    state_filter = f"AND state = '{state}'" if state else ""

    # Note: organization_name may not exist in events table - using NULL for now
    # Will be enriched from Firestore user profiles
    query = f"""
        WITH all_research AS (
            -- Lender research
            SELECT
                'lender' AS entity_type,
                lender_id AS entity_id,
                lender_name AS entity_name,
                user_id,
                CAST(NULL AS STRING) AS user_organization,
                state AS researcher_state,
                event_timestamp
            FROM `{EVENTS_TABLE}`
            WHERE event_name IN ('{TARGET_APPS[3]}', '{TARGET_APPS[4]}')
                {date_filter}
                AND lender_id IS NOT NULL
                {state_filter}

            UNION ALL

            -- County research
            SELECT
                'county' AS entity_type,
                county_fips AS entity_id,
                CONCAT(county_name, ', ', state) AS entity_name,
                user_id,
                CAST(NULL AS STRING) AS user_organization,
                state AS researcher_state,
                event_timestamp
            FROM `{EVENTS_TABLE}`
            WHERE event_name IN ('{TARGET_APPS[0]}', '{TARGET_APPS[1]}', '{TARGET_APPS[2]}')
                {date_filter}
                AND county_fips IS NOT NULL
                {state_filter}
        )
        SELECT
            entity_type,
            entity_id,
            MAX(entity_name) AS entity_name,
            COUNT(DISTINCT user_id) AS unique_users,
            COUNT(DISTINCT user_organization) AS unique_organizations,
            ARRAY_AGG(DISTINCT user_organization IGNORE NULLS LIMIT 20) AS organizations,
            ARRAY_AGG(DISTINCT researcher_state IGNORE NULLS LIMIT 20) AS researcher_states,
            MAX(event_timestamp) AS last_activity
        FROM all_research
        GROUP BY entity_type, entity_id
        HAVING COUNT(DISTINCT user_id) >= {min_users}
    """

    if entity_type:
        query = f"""
            SELECT * FROM ({query})
            WHERE entity_type = '{entity_type}'
        """

    query += " ORDER BY unique_users DESC, unique_organizations DESC LIMIT 200"

    try:
        results = client.query(query).result()
        data = [dict(row) for row in results]

        # Enrich county entities with coordinates from Census Bureau Gazetteer
        for item in data:
            if item.get('entity_type') == 'county':
                fips = item.get('entity_id')
                centroid = lookup_county_centroid(county_fips=fips)
                if centroid:
                    item['latitude'] = centroid['lat']
                    item['longitude'] = centroid['lng']
                    # Update entity_name if missing
                    if not item.get('entity_name') and centroid.get('name'):
                        state = centroid.get('state', '')
                        item['entity_name'] = f"{centroid['name']}, {state}"
                else:
                    item['latitude'] = None
                    item['longitude'] = None

        _set_cached(cache_key, data)
        return data
    except Exception as e:
        print(f"BigQuery error in get_coalition_opportunities: {e}")
        return []


def get_summary(days: int = 90) -> Dict[str, Any]:
    """
    Get summary metrics for the dashboard.

    Args:
        days: Number of days to look back (0 = all time)

    Returns:
        Summary dict with total_users, total_events, total_lenders, top_counties, top_lenders
    """
    # Check cache first
    cache_key = _cache_key('get_summary', days=days)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    client = get_bigquery_client()

    # Build app filters
    target_apps_str = "', '".join(TARGET_APPS)
    lender_apps_str = "', '".join(LENDER_APPS)

    # Build date filter
    date_filter = f"AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    # NOTE: Don't filter users here - we want to count ALL events for dashboard metrics

    # Define all queries
    totals_query = f"""
        SELECT
            COUNT(DISTINCT user_id) AS total_users,
            COUNT(*) AS total_events,
            (SELECT COUNT(DISTINCT lender_id) FROM `{EVENTS_TABLE}`
             WHERE event_name IN ('{lender_apps_str}') {date_filter} AND lender_id IS NOT NULL) AS total_lenders
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            {date_filter}
    """

    top_counties_query = f"""
        SELECT
            county_fips,
            state,
            county_name,
            COUNT(*) AS total_reports
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            {date_filter}
            AND county_fips IS NOT NULL
        GROUP BY county_fips, state, county_name
        ORDER BY total_reports DESC
        LIMIT 5
    """

    top_lenders_query = f"""
        SELECT
            lender_id,
            lender_name,
            COUNT(*) AS total_events
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{lender_apps_str}')
            {date_filter}
            AND lender_id IS NOT NULL
        GROUP BY lender_id, lender_name
        ORDER BY total_events DESC
        LIMIT 5
    """

    app_usage_query = f"""
        SELECT
            event_name,
            COUNT(*) AS event_count,
            COUNT(DISTINCT user_id) AS unique_users
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            {date_filter}
        GROUP BY event_name
        ORDER BY event_count DESC
    """

    # Run all 4 queries in PARALLEL using ThreadPoolExecutor
    # This reduces total time from sum(query_times) to max(query_times)
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def run_query(query_name, query):
        """Execute a single BigQuery query and return results."""
        try:
            results = list(client.query(query).result())
            return query_name, results, None
        except Exception as e:
            return query_name, None, str(e)

    queries = {
        'totals': totals_query,
        'top_counties': top_counties_query,
        'top_lenders': top_lenders_query,
        'app_usage': app_usage_query
    }

    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_query, name, q): name for name, q in queries.items()}
        for future in as_completed(futures):
            query_name, data, error = future.result()
            if error:
                print(f"BigQuery error in {query_name}: {error}")
                results[query_name] = []
            else:
                results[query_name] = data

    # Process totals
    total_users = 0
    total_events = 0
    total_lenders = 0
    if results.get('totals'):
        row = results['totals'][0] if results['totals'] else {}
        total_users = row.get('total_users', 0) or 0
        total_events = row.get('total_events', 0) or 0
        total_lenders = row.get('total_lenders', 0) or 0

    # Process top counties
    top_counties = [dict(row) for row in results.get('top_counties', [])]
    data_needing_names = [d for d in top_counties if d.get('county_fips') and not d.get('county_name')]
    if data_needing_names:
        top_counties = _enrich_with_county_names(client, top_counties)

    # Process top lenders - resolve LEI codes to human-readable names
    top_lenders = [dict(row) for row in results.get('top_lenders', [])]
    for lender in top_lenders:
        if lender.get('lender_id'):
            name = _lookup_single_lender_name(lender['lender_id'])
            if name:
                lender['lender_name'] = name

    # Process app usage
    app_usage = [dict(row) for row in results.get('app_usage', [])]

    result = {
        'total_users': total_users,
        'total_events': total_events,
        'total_lenders': total_lenders,
        'top_counties': top_counties,
        'top_lenders': top_lenders,
        'app_usage': app_usage,
        'days': days
    }
    _set_cached(cache_key, result)
    return result


