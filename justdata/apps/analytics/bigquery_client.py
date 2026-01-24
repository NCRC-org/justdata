"""
BigQuery client for Analytics application.

Queries Firebase Analytics data exported to BigQuery for:
- User location patterns
- Research activity by geography
- Lender interest tracking
- Coalition-building opportunities

# =============================================================================
# HUBSPOT INTEGRATION (PLANNED)
# =============================================================================
#
# The analytics queries below use Firebase user_id (anonymous) and user_pseudo_id.
# To enable coalition building with organization context, we need to link
# Firebase users to HubSpot contacts.
#
# DATA FLOW:
#   Firebase Auth (user_id) --> User Profile (Firestore) --> HubSpot Contact ID
#                                     |
#                                     v
#                            HubSpot Company ID (organization)
#
# ENRICHMENT POINTS:
#   1. get_coalition_opportunities() - Add organization names from HubSpot
#   2. get_lender_interest() - Group by HubSpot company for org-level insights
#   3. get_user_locations() - Enrich with organization/contact data
#   4. get_research_activity() - Add researcher organization context
#
# REQUIRED HUBSPOT DATA:
#   - Contact ID (linked to Firebase user)
#   - Contact Email
#   - Company ID (organization)
#   - Company Name
#   - Company Type (nonprofit, government, etc.)
#   - Contact's Role/Title
#
# See hubspot_integration.py for the integration module structure.
# =============================================================================
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.oauth2 import service_account

from .config import config


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


def sync_new_events() -> dict:
    """
    Sync new events from usage_log to backfilled_events.

    This function queries the usage_log table for entries newer than the last
    sync timestamp, transforms them to match the backfilled_events schema,
    and inserts them. Called on dashboard load with rate limiting.

    Returns:
        dict with 'synced_count', 'last_sync', 'skipped' (if rate limited)
    """
    global _last_sync_check

    # Rate limiting - only sync once per hour
    now = datetime.utcnow()
    if _last_sync_check and (now - _last_sync_check).total_seconds() < SYNC_CHECK_INTERVAL_SECONDS:
        return {'skipped': True, 'reason': 'Rate limited'}

    _last_sync_check = now

    try:
        # Get last sync timestamp from Firestore
        from justdata.main.auth import get_firestore_client
        db = get_firestore_client()
        last_sync_ts = None

        if db:
            try:
                sync_doc = db.collection('system').document('analytics_sync').get()
                if sync_doc.exists:
                    data = sync_doc.to_dict()
                    last_sync_ts = data.get('last_sync_timestamp')
            except Exception as e:
                print(f"[WARN] Analytics: Could not read sync timestamp from Firestore: {e}")

        client = get_bigquery_client()

        # Build the timestamp filter
        if last_sync_ts:
            # Handle both datetime and Firestore Timestamp
            if hasattr(last_sync_ts, 'isoformat'):
                ts_str = last_sync_ts.strftime('%Y-%m-%d %H:%M:%S')
            else:
                ts_str = str(last_sync_ts)
            timestamp_filter = f"AND timestamp > TIMESTAMP('{ts_str}')"
        else:
            # First sync - get last 7 days of data
            seven_days_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
            timestamp_filter = f"AND timestamp > TIMESTAMP('{seven_days_ago}')"

        # Query usage_log for new entries with report events
        # Map event names to standard format
        sync_query = f"""
            WITH new_events AS (
                SELECT
                    GENERATE_UUID() as event_id,
                    timestamp as event_timestamp,
                    CASE
                        WHEN action = 'lendsight_report_generated' THEN 'lendsight_report'
                        WHEN action = 'bizsight_report_generated' THEN 'bizsight_report'
                        WHEN action = 'branchsight_report_generated' THEN 'branchsight_report'
                        WHEN action = 'dataexplorer_area_report' THEN 'dataexplorer_area_report'
                        WHEN action = 'dataexplorer_lender_report' THEN 'dataexplorer_lender_report'
                        ELSE action
                    END as event_name,
                    user_id,
                    CAST(NULL AS STRING) as user_email,
                    CAST(NULL AS STRING) as user_type,
                    CAST(NULL AS STRING) as organization_name,
                    JSON_VALUE(details, '$.county_fips') as county_fips,
                    JSON_VALUE(details, '$.county_name') as county_name,
                    JSON_VALUE(details, '$.state') as state,
                    JSON_VALUE(details, '$.lender_id') as lender_id,
                    JSON_VALUE(details, '$.lender_name') as lender_name,
                    JSON_VALUE(details, '$.lei') as lender_id_alt,
                    JSON_VALUE(details, '$.respondent_name') as lender_name_alt,
                    CAST(NULL AS STRING) as hubspot_contact_id,
                    CAST(NULL AS STRING) as hubspot_company_id
                FROM `{BACKFILL_PROJECT}.{BACKFILL_DATASET}.usage_log`
                WHERE action IN (
                    'lendsight_report_generated',
                    'bizsight_report_generated',
                    'branchsight_report_generated',
                    'dataexplorer_area_report',
                    'dataexplorer_lender_report'
                )
                {timestamp_filter}
            )
            SELECT
                event_id,
                event_timestamp,
                event_name,
                user_id,
                user_email,
                user_type,
                organization_name,
                county_fips,
                county_name,
                state,
                COALESCE(lender_id, lender_id_alt) as lender_id,
                COALESCE(lender_name, lender_name_alt) as lender_name,
                hubspot_contact_id,
                hubspot_company_id
            FROM new_events
        """

        # Get the count of new events first
        count_query = f"""
            SELECT COUNT(*) as cnt
            FROM `{BACKFILL_PROJECT}.{BACKFILL_DATASET}.usage_log`
            WHERE action IN (
                'lendsight_report_generated',
                'bizsight_report_generated',
                'branchsight_report_generated',
                'dataexplorer_area_report',
                'dataexplorer_lender_report'
            )
            {timestamp_filter}
        """

        count_result = list(client.query(count_query).result())
        new_count = count_result[0].cnt if count_result else 0

        if new_count == 0:
            # Update last sync time even if no new events
            if db:
                try:
                    db.collection('system').document('analytics_sync').set({
                        'last_sync_timestamp': now,
                        'last_sync_count': 0,
                        'status': 'no_new_events'
                    }, merge=True)
                except Exception as e:
                    print(f"[WARN] Analytics: Could not update sync timestamp: {e}")

            return {'synced_count': 0, 'last_sync': now.isoformat()}

        # Insert new events into backfilled_events
        insert_query = f"""
            INSERT INTO `{BACKFILL_PROJECT}.{BACKFILL_DATASET}.backfilled_events`
            (event_id, event_timestamp, event_name, user_id, user_email, user_type,
             organization_name, county_fips, county_name, state, lender_id, lender_name,
             hubspot_contact_id, hubspot_company_id)
            {sync_query}
        """

        try:
            client.query(insert_query).result()
            synced_count = new_count
        except Exception as e:
            print(f"[ERROR] Analytics: Failed to insert synced events: {e}")
            return {'error': str(e), 'synced_count': 0}

        # Update sync timestamp in Firestore
        if db:
            try:
                db.collection('system').document('analytics_sync').set({
                    'last_sync_timestamp': now,
                    'last_sync_count': synced_count,
                    'status': 'success'
                }, merge=True)
            except Exception as e:
                print(f"[WARN] Analytics: Could not update sync timestamp: {e}")

        # Clear cache to pick up new data
        clear_analytics_cache()

        print(f"[INFO] Analytics: Synced {synced_count} new events from usage_log")
        return {'synced_count': synced_count, 'last_sync': now.isoformat()}

    except Exception as e:
        print(f"[ERROR] Analytics sync failed: {e}")
        return {'error': str(e), 'synced_count': 0}


# Use unified view combining backfilled data + live Firebase export
# The all_events view is in justdata-f7da7.justdata_analytics and combines:
#   - Historical: hdma1-242116.justdata_analytics.backfilled_events (Nov 24, 2025 - Jan 22, 2026)
#   - Live: justdata-f7da7.analytics_520863329.events_* (Jan 23, 2026 onwards)
ANALYTICS_PROJECT = 'justdata-f7da7'
ANALYTICS_DATASET = 'justdata_analytics'
EVENTS_TABLE = f'{ANALYTICS_PROJECT}.{ANALYTICS_DATASET}.all_events'

# Backfill source (for sync_new_events function - syncs from usage_log to backfilled_events)
BACKFILL_PROJECT = 'hdma1-242116'
BACKFILL_DATASET = 'justdata_analytics'

# Target apps for main analytics counts
TARGET_APPS = [
    'lendsight_report',
    'bizsight_report',
    'branchsight_report',
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


def get_bigquery_client():
    """Get or create BigQuery client."""
    global _client
    if _client is None:
        # Try to get credentials from environment
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            try:
                # Handle JSON that may have literal newlines in the private key
                # This can happen when the secret is stored with actual newlines
                # instead of escaped \n sequences
                import re

                # First, try to parse as-is
                try:
                    creds_dict = json.loads(creds_json)
                except json.JSONDecodeError:
                    # If that fails, try to fix newlines in the private_key field
                    # Replace literal newlines within the JSON string values with escaped newlines
                    # This regex finds the private_key field and escapes any literal newlines within it
                    def escape_newlines_in_key(match):
                        key_content = match.group(1)
                        # Replace literal newlines with escaped newlines
                        key_content = key_content.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
                        return f'"private_key":"{key_content}"'

                    fixed_json = re.sub(
                        r'"private_key"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
                        escape_newlines_in_key,
                        creds_json,
                        flags=re.DOTALL
                    )

                    # If regex didn't help, try a simpler approach: escape all newlines
                    try:
                        creds_dict = json.loads(fixed_json)
                    except json.JSONDecodeError:
                        # Last resort: try to load using ast.literal_eval after some cleanup
                        print(f"[WARN] Analytics: Could not parse credentials JSON, falling back to default auth")
                        _client = bigquery.Client(project=ANALYTICS_PROJECT)
                        return _client

                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                _client = bigquery.Client(
                    project=ANALYTICS_PROJECT,
                    credentials=credentials
                )
            except Exception as e:
                print(f"[ERROR] Analytics: Error parsing credentials: {e}")
                # Fall back to default credentials
                _client = bigquery.Client(project=ANALYTICS_PROJECT)
        else:
            # Fall back to default credentials
            _client = bigquery.Client(project=ANALYTICS_PROJECT)
    return _client


def _format_date_suffix(days: int) -> str:
    """Get date suffix for BigQuery table partitions."""
    date = datetime.utcnow() - timedelta(days=days)
    return date.strftime('%Y%m%d')


# County centroids cache - loaded once from BigQuery
_county_centroids = None

def get_county_centroids() -> Dict[str, Dict[str, float]]:
    """
    Get county FIPS -> centroid coordinates mapping.
    Uses BigQuery public dataset for US county boundaries.
    Returns dict like {'01001': {'lat': 32.5, 'lng': -86.5}, ...}
    """
    global _county_centroids

    if _county_centroids is not None:
        return _county_centroids

    client = get_bigquery_client()

    # Query county centroids from BigQuery public dataset
    query = """
        SELECT
            geo_id AS county_fips,
            ST_Y(ST_CENTROID(county_geom)) AS latitude,
            ST_X(ST_CENTROID(county_geom)) AS longitude
        FROM `bigquery-public-data.geo_us_boundaries.counties`
    """

    try:
        results = client.query(query).result()
        _county_centroids = {}
        for row in results:
            if row.county_fips and row.latitude and row.longitude:
                _county_centroids[row.county_fips] = {
                    'lat': float(row.latitude),
                    'lng': float(row.longitude)
                }
        print(f"[INFO] Loaded {len(_county_centroids)} county centroids")
        return _county_centroids
    except Exception as e:
        print(f"[WARN] Could not load county centroids: {e}")
        _county_centroids = {}
        return _county_centroids


def _enrich_with_coordinates(data: List[Dict], fips_field: str = 'county_fips') -> List[Dict]:
    """
    Add latitude/longitude to data records based on county FIPS code.

    Args:
        data: List of data records
        fips_field: Field name containing county FIPS code

    Returns:
        Data enriched with latitude/longitude coordinates
    """
    centroids = get_county_centroids()

    for item in data:
        fips = item.get(fips_field)
        if fips and fips in centroids:
            item['latitude'] = centroids[fips]['lat']
            item['longitude'] = centroids[fips]['lng']
        else:
            # Clear any existing bogus coordinates
            item['latitude'] = None
            item['longitude'] = None

    return data


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


def _enrich_with_county_names(client, data: List[Dict]) -> List[Dict]:
    """Add county names to data using geo.cbsa_to_county table."""
    fips_list = [d['county_fips'] for d in data if d.get('county_fips')]
    if not fips_list:
        return data

    fips_str = "', '".join(fips_list)
    query = f"""
        SELECT DISTINCT geoid5 AS county_fips, County AS county_name
        FROM `hdma1-242116.geo.cbsa_to_county`
        WHERE geoid5 IN ('{fips_str}')
    """

    try:
        results = client.query(query).result()
        name_lookup = {row['county_fips']: row['county_name'] for row in results}

        for item in data:
            fips = item.get('county_fips')
            if fips and fips in name_lookup:
                item['county_name'] = name_lookup[fips]
            else:
                item['county_name'] = None

        return data
    except Exception as e:
        print(f"Error enriching county names: {e}")
        return data


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

    date_filter = f"AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    # User type filter
    user_type_filter = ""
    if user_types:
        types_str = "', '".join(user_types)
        user_type_filter = f" AND user_type IN ('{types_str}')"
    elif exclude_user_types:
        types_str = "', '".join(exclude_user_types)
        user_type_filter = f" AND (user_type IS NULL OR user_type NOT IN ('{types_str}'))"

    # Include all lender-related events
    query = f"""
        SELECT
            lender_id,
            lender_name,
            state AS researcher_state,
            county_name AS researcher_city,
            COUNT(DISTINCT user_id) AS unique_users,
            COUNT(*) AS event_count,
            MAX(event_timestamp) AS last_activity
        FROM `{EVENTS_TABLE}`
        WHERE lender_id IS NOT NULL
            {date_filter}
            {user_type_filter}
        GROUP BY lender_id, lender_name, researcher_state, researcher_city
        HAVING COUNT(DISTINCT user_id) >= {min_users}
        ORDER BY event_count DESC, unique_users DESC
        LIMIT 500
    """

    try:
        results = client.query(query).result()
        data = [dict(row) for row in results]
        _set_cached(cache_key, data)
        return data
    except Exception as e:
        print(f"BigQuery error in get_lender_interest: {e}")
        return []


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
                COALESCE(user_id, event_id) AS user_id,
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
                COALESCE(user_id, event_id) AS user_id,
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

        # Enrich county entities with names if missing
        county_data = [d for d in data if d.get('entity_type') == 'county' and not d.get('entity_name')]
        if county_data:
            fips_to_name = {}
            fips_list = [d['entity_id'] for d in county_data if d.get('entity_id')]
            if fips_list:
                fips_str = "', '".join(fips_list)

                name_query = f"""
                    SELECT DISTINCT geoid5, County
                    FROM `hdma1-242116.geo.cbsa_to_county`
                    WHERE geoid5 IN ('{fips_str}')
                """
                try:
                    name_results = client.query(name_query).result()
                    for row in name_results:
                        fips_to_name[row['geoid5']] = row['County']

                    for item in data:
                        if item.get('entity_type') == 'county' and not item.get('entity_name'):
                            item['entity_name'] = fips_to_name.get(item['entity_id'])
                except:
                    pass

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

    # Total users and events (filtered to target apps only)
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

    try:
        totals_result = list(client.query(totals_query).result())
        if totals_result:
            total_users = totals_result[0].get('total_users', 0)
            total_events = totals_result[0].get('total_events', 0)
            total_lenders = totals_result[0].get('total_lenders', 0)
        else:
            total_users = 0
            total_events = 0
            total_lenders = 0
    except Exception as e:
        print(f"BigQuery error getting totals: {e}")
        total_users = 0
        total_events = 0
        total_lenders = 0

    # Top researched counties (filtered to target apps)
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

    try:
        top_counties = [dict(row) for row in client.query(top_counties_query).result()]
        # Enrich with county names if missing
        data_needing_names = [d for d in top_counties if d.get('county_fips') and not d.get('county_name')]
        if data_needing_names:
            top_counties = _enrich_with_county_names(client, top_counties)
    except Exception as e:
        print(f"BigQuery error getting top counties: {e}")
        top_counties = []

    # Top researched lenders (from lender-tracking apps)
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

    try:
        top_lenders = [dict(row) for row in client.query(top_lenders_query).result()]
    except Exception as e:
        print(f"BigQuery error getting top lenders: {e}")
        top_lenders = []

    # App usage breakdown (target apps only)
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

    try:
        app_usage = [dict(row) for row in client.query(app_usage_query).result()]
    except Exception as e:
        print(f"BigQuery error getting app usage: {e}")
        app_usage = []

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

    query = f"""
        SELECT
            user_id,
            MAX(state) AS last_state,
            MAX(county_name) AS last_county,
            COUNT(*) AS total_reports,
            COUNT(DISTINCT county_fips) AS counties_researched,
            COUNT(DISTINCT lender_id) AS lenders_researched,
            MAX(event_timestamp) AS last_activity,
            MIN(event_timestamp) AS first_activity
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            AND user_id IS NOT NULL
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
            AND user_id IS NOT NULL
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


def _enrich_users_from_firestore(users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich user records with profile data from Firestore.

    Args:
        users: List of user records with at least user_id

    Returns:
        Users enriched with user_email, user_type, organization_name, user_name
    """
    try:
        from firebase_admin import firestore
        db = firestore.client()
    except Exception as e:
        print(f"Could not connect to Firestore: {e}")
        return users

    for user in users:
        user_id = user.get('user_id')
        if not user_id:
            continue

        try:
            # Get user profile from Firestore
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                profile = user_doc.to_dict()
                user['user_email'] = profile.get('email', '')
                user['user_name'] = profile.get('displayName', profile.get('email', ''))
                user['user_type'] = profile.get('userType', '')
                user['organization_name'] = profile.get('organizationName', '')
        except Exception as e:
            # Continue even if one user fails
            print(f"Failed to get Firestore profile for {user_id}: {e}")
            continue

    return users


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

    date_filter = f"WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)" if days > 0 else ""

    query = f"""
        SELECT
            DATE(event_timestamp) AS date,
            COUNT(*) AS event_count,
            COUNT(DISTINCT COALESCE(user_id, event_id)) AS unique_users
        FROM `{EVENTS_TABLE}`
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
