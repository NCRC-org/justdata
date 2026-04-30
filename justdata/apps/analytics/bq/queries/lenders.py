"""Lender queries."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from justdata.apps.analytics.sql_loader import load_sql

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


def get_lender_interest(
    days: int = 90,
    min_users: int = 1,
    user_types: Optional[List[str]] = None,
    exclude_user_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get lenders being researched with researcher locations.

    Args:
        days: Number of days to look back (0 = all time)
        min_users: Minimum unique users researching this lender (for coalition filtering)
        user_types: Optional list of user types to include
        exclude_user_types: Optional list of user types to exclude

    Returns:
        List of lender interest records
    """
    # Check cache first
    cache_key = _cache_key('get_lender_interest', days=days, min_users=min_users,
                           user_types=user_types, exclude_user_types=exclude_user_types)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    client = get_bigquery_client()

    date_filter = f"AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    # User type filter
    user_type_filter = ""
    if user_types:
        types_str = "', '".join(user_types)
        user_type_filter = f" AND user_type IN ('{types_str}')"
    elif exclude_user_types:
        types_str = "', '".join(exclude_user_types)
        user_type_filter = f" AND (user_type IS NULL OR user_type NOT IN ('{types_str}'))"

    # Query usage_log and join with GA4 page views to get geo data
    # GA4 captures user location via IP automatically
    date_filter_ga4 = f"AND TIMESTAMP_MICROS(ga.event_timestamp) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""
    
    # Apply valid user filter to exclude test/anonymous users
    user_filter = get_valid_user_filter()

    query = f"""
        WITH merger_events AS (
            SELECT
                COALESCE(
                    JSON_VALUE(parameters_json, '$.acquirer_lei'),
                    JSON_VALUE(parameters_json, '$.target_lei')
                ) AS lender_id,
                timestamp AS event_timestamp,
                user_id,
                user_email,
                user_type
            FROM `justdata-ncrc.cache.usage_log`
            WHERE app_name = 'mergermeter'
                AND error_message IS NULL
                AND (JSON_VALUE(parameters_json, '$.acquirer_lei') IS NOT NULL
                     OR JSON_VALUE(parameters_json, '$.target_lei') IS NOT NULL)
                AND {user_filter}
                {date_filter}
                {user_type_filter}
        ),
        ga_geo AS (
            SELECT DISTINCT
                geo.region as geo_region,
                geo.city as geo_city,
                user_pseudo_id,
                TIMESTAMP_MICROS(event_timestamp) as event_time
            FROM `justdata-ncrc.analytics_521852976.events_*` ga
            WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL {days if days > 0 else 365} DAY))
                AND event_name = 'page_view'
                AND (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') LIKE '%mergermeter%'
                AND geo.region IS NOT NULL
                {date_filter_ga4}
        )
        SELECT 
            me.lender_id,
            me.event_timestamp,
            me.user_id,
            me.user_email,
            me.user_type,
            gg.geo_region,
            gg.geo_city
        FROM merger_events me
        LEFT JOIN ga_geo gg ON 
            ABS(TIMESTAMP_DIFF(me.event_timestamp, gg.event_time, MINUTE)) <= 30
        ORDER BY me.event_timestamp DESC
        LIMIT 1000
    """

    try:
        results = client.query(query).result()
        raw_events = [dict(row) for row in results]

        # Aggregate by lender + geo location from GA4
        lender_geo_data = {}
        geo_count = 0
        
        for event in raw_events:
            lender_id = event.get('lender_id')
            if not lender_id:
                continue
            
            geo_region = event.get('geo_region')
            geo_city = event.get('geo_city')
            
            if geo_region and geo_city:
                geo_count += 1
                key = f"{lender_id}_{geo_region}_{geo_city}"
                if key not in lender_geo_data:
                    lender_geo_data[key] = {
                        'lender_id': lender_id,
                        'lender_name': None,
                        'researcher_state': geo_region,
                        'researcher_city': geo_city,
                        'researcher_county_fips': None,
                        'latitude': None,
                        'longitude': None,
                        'unique_users': set(),
                        'event_count': 0,
                        'last_activity': None
                    }
                lender_geo_data[key]['unique_users'].add(event.get('user_id') or 'anonymous')
                lender_geo_data[key]['event_count'] += 1
                ts = event.get('event_timestamp')
                if ts and (lender_geo_data[key]['last_activity'] is None or ts > lender_geo_data[key]['last_activity']):
                    lender_geo_data[key]['last_activity'] = ts
        
        # Convert to list and finalize
        data = []
        for item in lender_geo_data.values():
            item['unique_users'] = len(item['unique_users'])
            if item['event_count'] >= min_users:
                data.append(item)
        
        # Sort by event count
        data.sort(key=lambda x: x['event_count'], reverse=True)
        data = data[:500]
        
        # Enrich with coordinates using city/state lookup
        data = _enrich_lender_interest_with_coordinates(data)

        # Enrich with lender names from GLEIF table
        data = _enrich_lender_names(data)

        _set_cached(cache_key, data)
        return data
    except Exception as e:
        print(f"BigQuery error in get_lender_interest: {e}")
        import traceback
        traceback.print_exc()
        return []



def get_lender_detail(
    lender_id: str,
    days: int = 90
) -> Dict[str, Any]:
    """
    Get detailed information for a specific lender including reports and researchers.

    Args:
        lender_id: The lender ID (LEI) to look up
        days: Number of days to look back (0 = all time)

    Returns:
        Dict with lender info, reports, and researchers
    """
    client = get_bigquery_client()

    date_filter = f"AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    # User filter for usage_log table (uses different column names than events table)
    user_filter_usage = """
        user_id IS NOT NULL
        AND user_id != ''
        AND (user_email IS NULL OR (
            user_email NOT LIKE '%test%'
            AND user_email NOT LIKE '%anonymous%'
            AND user_email != 'anonymous'
        ))
        AND NOT REGEXP_CONTAINS(user_id, r'^[0-9]+\\.[0-9]+$')
    """

    # Query the usage_log table for MergerMeter events for this lender
    # MergerMeter events store lender_id in parameters_json as acquirer_lei or target_lei
    summary_query = f"""
        SELECT
            '{lender_id}' AS lender_id,
            COUNT(*) AS total_reports,
            COUNT(DISTINCT user_id) AS unique_researchers,
            MIN(timestamp) AS first_activity,
            MAX(timestamp) AS last_activity
        FROM `justdata-ncrc.cache.usage_log`
        WHERE app_name = 'mergermeter'
            AND error_message IS NULL
            AND (JSON_VALUE(parameters_json, '$.acquirer_lei') = '{lender_id}'
                 OR JSON_VALUE(parameters_json, '$.target_lei') = '{lender_id}')
            AND {user_filter_usage}
            {date_filter}
    """

    # Get all reports for this lender with acquirer/target info from parameters
    reports_query = load_sql("lender_reports.sql").format(date_filter=date_filter, lender_id=lender_id, user_filter_usage=user_filter_usage)

    # Get researchers for this lender
    researchers_query = f"""
        SELECT
            user_id,
            user_email,
            COUNT(*) AS report_count,
            MAX(timestamp) AS last_activity,
            MIN(timestamp) AS first_activity
        FROM `justdata-ncrc.cache.usage_log`
        WHERE app_name = 'mergermeter'
            AND error_message IS NULL
            AND (JSON_VALUE(parameters_json, '$.acquirer_lei') = '{lender_id}'
                 OR JSON_VALUE(parameters_json, '$.target_lei') = '{lender_id}')
            AND {user_filter_usage}
            {date_filter}
        GROUP BY user_id, user_email
        ORDER BY report_count DESC
        LIMIT 100
    """

    try:
        # Execute queries
        summary_result = list(client.query(summary_query).result())
        reports_result = [dict(row) for row in client.query(reports_query).result()]
        researchers_result = [dict(row) for row in client.query(researchers_query).result()]

        if not summary_result or summary_result[0].total_reports == 0:
            return {'error': 'Lender not found'}

        summary = dict(summary_result[0])
        
        # Enrich lender name from GLEIF
        lender_name = _lookup_single_lender_name(lender_id)
        summary['lender_name'] = lender_name or 'Unknown Lender'

        # Enrich researchers with Firestore user profile data
        researchers_result = _enrich_users_from_firestore(researchers_result)

        return {
            'lender': summary,
            'reports': reports_result,
            'researchers': researchers_result
        }
    except Exception as e:
        print(f"BigQuery error in get_lender_detail: {e}")
        return {'error': str(e)}


