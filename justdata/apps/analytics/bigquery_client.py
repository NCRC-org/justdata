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
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.oauth2 import service_account

from .config import config

# IP Geocoding cache to avoid repeated API calls
_ip_geo_cache: Dict[str, Dict] = {}

def geocode_ip(ip_address: str) -> Optional[Dict[str, Any]]:
    """
    Convert IP address to geographic location using ip-api.com (free tier).
    
    Args:
        ip_address: IP address to geocode
        
    Returns:
        Dict with 'state', 'city', 'lat', 'lng' or None if failed
    """
    if not ip_address or ip_address in ('127.0.0.1', 'localhost', '::1'):
        return None
    
    # Check cache first
    if ip_address in _ip_geo_cache:
        return _ip_geo_cache[ip_address]
    
    try:
        # ip-api.com free tier: 45 requests/minute, no API key needed
        response = requests.get(
            f'http://ip-api.com/json/{ip_address}',
            params={'fields': 'status,regionName,city,lat,lon'},
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                result = {
                    'state': data.get('regionName'),
                    'city': data.get('city'),
                    'lat': data.get('lat'),
                    'lng': data.get('lon')
                }
                _ip_geo_cache[ip_address] = result
                return result
    except Exception as e:
        print(f"[WARN] IP geocoding failed for {ip_address}: {e}")
    
    _ip_geo_cache[ip_address] = None
    return None


# State name to abbreviation mapping for coordinate lookups
STATE_NAME_TO_ABBREV = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'
}

# State FIPS codes to 2-letter abbreviation
STATE_FIPS_TO_ABBREV = {
    '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO',
    '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA', '15': 'HI',
    '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY',
    '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN',
    '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH',
    '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND', '39': 'OH',
    '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD',
    '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA',
    '54': 'WV', '55': 'WI', '56': 'WY'
}


def _normalize_state_to_code(state: str) -> str:
    """Convert full state name, FIPS code, or abbreviation to 2-letter code."""
    if not state:
        return state
    state = str(state).strip()
    # Already a 2-letter code
    if len(state) == 2 and state.upper() in [v for v in STATE_NAME_TO_ABBREV.values()]:
        return state.upper()
    # State FIPS code (2 digits)
    if len(state) == 2 and state in STATE_FIPS_TO_ABBREV:
        return STATE_FIPS_TO_ABBREV[state]
    # Try exact name match
    if state in STATE_NAME_TO_ABBREV:
        return STATE_NAME_TO_ABBREV[state]
    # Try case-insensitive match
    for name, code in STATE_NAME_TO_ABBREV.items():
        if name.lower() == state.lower():
            return code
    return state


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

    The usage_log table has these columns:
    - app_name: 'lendsight', 'bizsight', 'branchsight', etc.
    - parameters_json: JSON with app-specific params
    - user_type, user_id, user_email, timestamp, etc.

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
            # First sync - get all historical data (no time limit)
            timestamp_filter = ""

        # Query usage_log for new entries with report events
        # The actual usage_log schema uses:
        # - app_name (not action): 'lendsight', 'bizsight', 'branchsight', etc.
        # - parameters_json (not details): JSON with app-specific params
        # - user_type, user_id, user_email columns
        #
        # Extract county/lender data from parameters_json based on app:
        # - bizsight: county_data.geoid5, county_data.name, county_data.state_name
        # - lendsight: counties (semicolon-separated), state_code
        # - branchsight: counties, state_code
        # - mergermeter: acquirer_lei, target_lei
        sync_query = f"""
            WITH new_events AS (
                SELECT
                    GENERATE_UUID() as event_id,
                    timestamp as event_timestamp,
                    CASE app_name
                        WHEN 'lendsight' THEN 'lendsight_report'
                        WHEN 'bizsight' THEN 'bizsight_report'
                        WHEN 'branchsight' THEN 'branchsight_report'
                        WHEN 'mergermeter' THEN 'mergermeter_report'
                        WHEN 'dataexplorer' THEN 'dataexplorer_report'
                        ELSE CONCAT(app_name, '_report')
                    END as event_name,
                    user_id,
                    user_email,
                    user_type,
                    CAST(NULL AS STRING) as organization_name,
                    -- Extract county_fips based on app type
                    CASE 
                        WHEN app_name = 'bizsight' THEN 
                            COALESCE(
                                JSON_VALUE(parameters_json, '$.county_data.geoid5'),
                                JSON_VALUE(parameters_json, '$.county_data.GEOID5')
                            )
                        WHEN app_name IN ('lendsight', 'branchsight') THEN
                            -- For lendsight/branchsight, counties is a string like "County, State; County2, State"
                            -- We can't easily extract FIPS from this, so leave NULL for now
                            -- The coordinates will be looked up by county name instead
                            CAST(NULL AS STRING)
                        ELSE CAST(NULL AS STRING)
                    END as county_fips,
                    -- Extract county_name based on app type
                    CASE 
                        WHEN app_name = 'bizsight' THEN 
                            JSON_VALUE(parameters_json, '$.county_data.name')
                        WHEN app_name IN ('lendsight', 'branchsight') THEN
                            -- Extract first county name from semicolon-separated list
                            SPLIT(JSON_VALUE(parameters_json, '$.counties'), ';')[SAFE_OFFSET(0)]
                        ELSE CAST(NULL AS STRING)
                    END as county_name,
                    -- Extract state based on app type
                    CASE 
                        WHEN app_name = 'bizsight' THEN 
                            JSON_VALUE(parameters_json, '$.county_data.state_name')
                        WHEN app_name IN ('lendsight', 'branchsight') THEN
                            JSON_VALUE(parameters_json, '$.state_code')
                        ELSE CAST(NULL AS STRING)
                    END as state,
                    -- Extract lender_id (for mergermeter)
                    CASE 
                        WHEN app_name = 'mergermeter' THEN 
                            COALESCE(
                                JSON_VALUE(parameters_json, '$.acquirer_lei'),
                                JSON_VALUE(parameters_json, '$.target_lei')
                            )
                        ELSE CAST(NULL AS STRING)
                    END as lender_id,
                    -- Extract lender_name (typically not in params, leave NULL)
                    CAST(NULL AS STRING) as lender_name,
                    CAST(NULL AS STRING) as hubspot_contact_id,
                    CAST(NULL AS STRING) as hubspot_company_id
                FROM `{BACKFILL_PROJECT}.{BACKFILL_DATASET}.usage_log`
                WHERE app_name IN ('lendsight', 'bizsight', 'branchsight', 'mergermeter', 'dataexplorer')
                    AND error_message IS NULL  -- Only successful reports
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
                lender_id,
                lender_name,
                hubspot_contact_id,
                hubspot_company_id
            FROM new_events
        """

        # Get the count of new events first
        count_query = f"""
            SELECT COUNT(*) as cnt
            FROM `{BACKFILL_PROJECT}.{BACKFILL_DATASET}.usage_log`
            WHERE app_name IN ('lendsight', 'bizsight', 'branchsight', 'mergermeter', 'dataexplorer')
                AND error_message IS NULL
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
        # Target is firebase_analytics.backfilled_events which feeds the all_events view
        insert_query = f"""
            INSERT INTO `{BACKFILL_PROJECT}.{BACKFILL_TARGET_DATASET}.backfilled_events`
            (event_id, event_timestamp, event_name, user_id, user_email, user_type,
             organization_name, county_fips, county_name, state, lender_id, lender_name,
             hubspot_contact_id, hubspot_company_id, source, backfill_timestamp)
            SELECT 
                event_id, event_timestamp, event_name, user_id, user_email, user_type,
                organization_name, county_fips, county_name, state, lender_id, lender_name,
                hubspot_contact_id, hubspot_company_id, 
                'sync' AS source,
                CURRENT_TIMESTAMP() AS backfill_timestamp
            FROM ({sync_query})
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


def force_full_sync() -> dict:
    """
    Force a full sync of all historical usage_log data to backfilled_events.
    
    This resets the sync timestamp and bypasses rate limiting to perform
    a complete sync. Use this after running the migration script to populate
    initial data.
    
    Returns:
        dict with 'synced_count', 'last_sync', or 'error'
    """
    global _last_sync_check
    
    try:
        # Reset the rate limit
        _last_sync_check = None
        
        # Reset the sync timestamp in Firestore to force full sync
        from justdata.main.auth import get_firestore_client
        db = get_firestore_client()
        
        if db:
            try:
                db.collection('system').document('analytics_sync').delete()
                print("[INFO] Analytics: Reset sync timestamp for full sync")
            except Exception as e:
                print(f"[WARN] Analytics: Could not reset sync timestamp: {e}")
        
        # Now run the sync (with no timestamp filter, it will sync all data)
        return sync_new_events()
        
    except Exception as e:
        print(f"[ERROR] Analytics force sync failed: {e}")
        return {'error': str(e), 'synced_count': 0}


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
                        _client = bigquery.Client(project=QUERY_PROJECT)
                        return _client

                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                _client = bigquery.Client(
                    project=QUERY_PROJECT,
                    credentials=credentials
                )
            except Exception as e:
                print(f"[ERROR] Analytics: Error parsing credentials: {e}")
                # Fall back to default credentials
                _client = bigquery.Client(project=QUERY_PROJECT)
        else:
            # Fall back to default credentials
            _client = bigquery.Client(project=QUERY_PROJECT)
    return _client


def _format_date_suffix(days: int) -> str:
    """Get date suffix for BigQuery table partitions."""
    date = datetime.utcnow() - timedelta(days=days)
    return date.strftime('%Y%m%d')


# County and CBSA centroids cache - loaded once from Census Bureau Gazetteer data
_county_centroids = None
_cbsa_centroids = None

# BigQuery tables for centroids (created by Jay after CSV upload)
COUNTY_CENTROIDS_TABLE = 'justdata-ncrc.shared.county_centroids'
CBSA_CENTROIDS_TABLE = 'justdata-ncrc.shared.cbsa_centroids'

# Local CSV fallback paths (for development/testing before BigQuery upload)
import os
LOCAL_COUNTY_CSV = os.path.join(os.path.dirname(__file__), 'demo_data', 'county_centroids_2024.csv')
LOCAL_CBSA_CSV = os.path.join(os.path.dirname(__file__), 'demo_data', 'cbsa_centroids_2024.csv')


def normalize_county_name(county_name: str) -> str:
    """
    Normalize county name for matching with centroid data.

    Handles:
    - Trailing FIPS codes: "Baltimore city, Maryland, 24" -> "Baltimore city"
    - State suffixes: "Alameda County, California" -> "Alameda County"
    - Extra whitespace

    Args:
        county_name: Raw county name from events table

    Returns:
        Normalized county name for centroid lookup
    """
    import re
    if not county_name:
        return None

    # Remove trailing FIPS codes (pattern: ", ##" at end)
    county_name = re.sub(r',\s*\d{2}$', '', county_name)

    # Remove state name if appended (pattern: ", StateName" at end)
    # But preserve suffixes like "city" in "Baltimore city"
    county_name = re.sub(r',\s*[A-Z][a-z]+(\s+[A-Z][a-z]+)*$', '', county_name)

    # Standardize spacing
    county_name = ' '.join(county_name.split())

    return county_name.strip()


def get_county_centroids() -> Dict[str, Dict[str, float]]:
    """
    Get county FIPS -> centroid coordinates mapping.

    Uses Census Bureau Gazetteer data (2024) for accurate centroids.
    First tries BigQuery table, falls back to local CSV if not available.

    Returns dict like {'01001': {'lat': 32.5, 'lng': -86.5}, ...}
    Also returns name lookup: {'01001': 'Autauga County', ...}
    """
    global _county_centroids

    if _county_centroids is not None:
        return _county_centroids

    _county_centroids = {'by_fips': {}, 'by_name': {}}

    # Try BigQuery first
    try:
        client = get_bigquery_client()
        query = f"""
            SELECT
                county_fips,
                state_code,
                county_name,
                county_name_normalized,
                latitude,
                longitude
            FROM `{COUNTY_CENTROIDS_TABLE}`
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """
        results = client.query(query).result()

        for row in results:
            fips = str(row.county_fips).zfill(5)
            _county_centroids['by_fips'][fips] = {
                'lat': float(row.latitude),
                'lng': float(row.longitude),
                'name': row.county_name,
                'state': row.state_code
            }
            # Also index by normalized name + state for flexible matching
            name_key = f"{row.county_name_normalized}|{row.state_code}".lower()
            _county_centroids['by_name'][name_key] = {
                'lat': float(row.latitude),
                'lng': float(row.longitude),
                'fips': fips,
                'name': row.county_name
            }

        print(f"[INFO] Loaded {len(_county_centroids['by_fips'])} county centroids from BigQuery")
        return _county_centroids

    except Exception as e:
        print(f"[WARN] Could not load county centroids from BigQuery: {e}")

    # Fall back to local CSV
    try:
        import pandas as pd
        if os.path.exists(LOCAL_COUNTY_CSV):
            df = pd.read_csv(LOCAL_COUNTY_CSV)
            for _, row in df.iterrows():
                fips = str(row['county_fips']).zfill(5)
                _county_centroids['by_fips'][fips] = {
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude']),
                    'name': row['county_name'],
                    'state': row['state_code']
                }
                name_key = f"{row['county_name_normalized']}|{row['state_code']}".lower()
                _county_centroids['by_name'][name_key] = {
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude']),
                    'fips': fips,
                    'name': row['county_name']
                }
            print(f"[INFO] Loaded {len(_county_centroids['by_fips'])} county centroids from local CSV")
        else:
            print(f"[WARN] Local county centroids CSV not found: {LOCAL_COUNTY_CSV}")
    except Exception as e:
        print(f"[ERROR] Failed to load county centroids from CSV: {e}")

    return _county_centroids


def get_cbsa_centroids() -> Dict[str, Dict[str, float]]:
    """
    Get CBSA code -> centroid coordinates mapping.

    Uses Census Bureau Gazetteer data (2024) for accurate CBSA centroids.
    First tries BigQuery table, falls back to local CSV if not available.

    Returns dict like {'47900': {'lat': 38.8, 'lng': -77.0, 'name': 'Washington-Arlington...'}, ...}
    """
    global _cbsa_centroids

    if _cbsa_centroids is not None:
        return _cbsa_centroids

    _cbsa_centroids = {}

    # Try BigQuery first
    try:
        client = get_bigquery_client()
        query = f"""
            SELECT
                cbsa_code,
                cbsa_name,
                principal_city,
                states,
                latitude,
                longitude
            FROM `{CBSA_CENTROIDS_TABLE}`
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """
        results = client.query(query).result()

        for row in results:
            _cbsa_centroids[str(row.cbsa_code)] = {
                'lat': float(row.latitude),
                'lng': float(row.longitude),
                'name': row.cbsa_name,
                'principal_city': row.principal_city,
                'states': row.states
            }

        print(f"[INFO] Loaded {len(_cbsa_centroids)} CBSA centroids from BigQuery")
        return _cbsa_centroids

    except Exception as e:
        print(f"[WARN] Could not load CBSA centroids from BigQuery: {e}")

    # Fall back to local CSV
    try:
        import pandas as pd
        if os.path.exists(LOCAL_CBSA_CSV):
            df = pd.read_csv(LOCAL_CBSA_CSV)
            for _, row in df.iterrows():
                _cbsa_centroids[str(row['cbsa_code'])] = {
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude']),
                    'name': row['cbsa_name'],
                    'principal_city': row['principal_city'],
                    'states': row['states']
                }
            print(f"[INFO] Loaded {len(_cbsa_centroids)} CBSA centroids from local CSV")
        else:
            print(f"[WARN] Local CBSA centroids CSV not found: {LOCAL_CBSA_CSV}")
    except Exception as e:
        print(f"[ERROR] Failed to load CBSA centroids from CSV: {e}")

    return _cbsa_centroids


def lookup_county_centroid(county_fips: str = None, county_name: str = None, state: str = None) -> Optional[Dict]:
    """
    Look up county centroid by FIPS code or by name+state.

    Args:
        county_fips: 5-digit FIPS code (preferred)
        county_name: County name (will be normalized)
        state: 2-letter state code (required if using county_name)

    Returns:
        Dict with 'lat', 'lng', 'name' or None if not found
    """
    centroids = get_county_centroids()

    # Try FIPS lookup first (most reliable)
    if county_fips:
        fips = str(county_fips).zfill(5)
        if fips in centroids['by_fips']:
            return centroids['by_fips'][fips]

    # Fall back to name+state lookup
    if county_name and state:
        normalized = normalize_county_name(county_name)
        if normalized:
            name_key = f"{normalized}|{state}".lower()
            if name_key in centroids['by_name']:
                return centroids['by_name'][name_key]

            # Try without normalization (exact match)
            exact_key = f"{county_name.lower().strip()}|{state}".lower()
            if exact_key in centroids['by_name']:
                return centroids['by_name'][exact_key]

    return None


def lookup_cbsa_centroid(cbsa_code: str) -> Optional[Dict]:
    """
    Look up CBSA centroid by code.

    Args:
        cbsa_code: CBSA code (e.g., '47900')

    Returns:
        Dict with 'lat', 'lng', 'name', 'principal_city' or None if not found
    """
    if not cbsa_code:
        return None

    centroids = get_cbsa_centroids()
    return centroids.get(str(cbsa_code))


# State bounding boxes for coordinate validation (approximate)
STATE_BOUNDS = {
    'AL': {'lat_min': 30.2, 'lat_max': 35.0, 'lng_min': -88.5, 'lng_max': -84.9},
    'AK': {'lat_min': 51.2, 'lat_max': 71.4, 'lng_min': -179.2, 'lng_max': -129.9},
    'AZ': {'lat_min': 31.3, 'lat_max': 37.0, 'lng_min': -114.8, 'lng_max': -109.0},
    'AR': {'lat_min': 33.0, 'lat_max': 36.5, 'lng_min': -94.6, 'lng_max': -89.6},
    'CA': {'lat_min': 32.5, 'lat_max': 42.0, 'lng_min': -124.5, 'lng_max': -114.1},
    'CO': {'lat_min': 36.9, 'lat_max': 41.0, 'lng_min': -109.1, 'lng_max': -102.0},
    'CT': {'lat_min': 40.9, 'lat_max': 42.1, 'lng_min': -73.7, 'lng_max': -71.8},
    'DE': {'lat_min': 38.5, 'lat_max': 39.8, 'lng_min': -75.8, 'lng_max': -75.0},
    'FL': {'lat_min': 24.4, 'lat_max': 31.0, 'lng_min': -87.6, 'lng_max': -80.0},
    'GA': {'lat_min': 30.4, 'lat_max': 35.0, 'lng_min': -85.6, 'lng_max': -80.8},
    'HI': {'lat_min': 18.9, 'lat_max': 22.2, 'lng_min': -160.2, 'lng_max': -154.8},
    'ID': {'lat_min': 42.0, 'lat_max': 49.0, 'lng_min': -117.2, 'lng_max': -111.0},
    'IL': {'lat_min': 36.9, 'lat_max': 42.5, 'lng_min': -91.5, 'lng_max': -87.0},
    'IN': {'lat_min': 37.8, 'lat_max': 41.8, 'lng_min': -88.1, 'lng_max': -84.8},
    'IA': {'lat_min': 40.4, 'lat_max': 43.5, 'lng_min': -96.6, 'lng_max': -90.1},
    'KS': {'lat_min': 37.0, 'lat_max': 40.0, 'lng_min': -102.1, 'lng_max': -94.6},
    'KY': {'lat_min': 36.5, 'lat_max': 39.1, 'lng_min': -89.6, 'lng_max': -81.9},
    'LA': {'lat_min': 28.9, 'lat_max': 33.0, 'lng_min': -94.0, 'lng_max': -88.8},
    'ME': {'lat_min': 43.0, 'lat_max': 47.5, 'lng_min': -71.1, 'lng_max': -66.9},
    'MD': {'lat_min': 37.9, 'lat_max': 39.7, 'lng_min': -79.5, 'lng_max': -75.0},
    'MA': {'lat_min': 41.2, 'lat_max': 42.9, 'lng_min': -73.5, 'lng_max': -69.9},
    'MI': {'lat_min': 41.7, 'lat_max': 48.3, 'lng_min': -90.4, 'lng_max': -82.4},
    'MN': {'lat_min': 43.5, 'lat_max': 49.4, 'lng_min': -97.2, 'lng_max': -89.5},
    'MS': {'lat_min': 30.2, 'lat_max': 35.0, 'lng_min': -91.7, 'lng_max': -88.1},
    'MO': {'lat_min': 36.0, 'lat_max': 40.6, 'lng_min': -95.8, 'lng_max': -89.1},
    'MT': {'lat_min': 44.4, 'lat_max': 49.0, 'lng_min': -116.1, 'lng_max': -104.0},
    'NE': {'lat_min': 40.0, 'lat_max': 43.0, 'lng_min': -104.1, 'lng_max': -95.3},
    'NV': {'lat_min': 35.0, 'lat_max': 42.0, 'lng_min': -120.0, 'lng_max': -114.0},
    'NH': {'lat_min': 42.7, 'lat_max': 45.3, 'lng_min': -72.6, 'lng_max': -70.7},
    'NJ': {'lat_min': 38.9, 'lat_max': 41.4, 'lng_min': -75.6, 'lng_max': -73.9},
    'NM': {'lat_min': 31.3, 'lat_max': 37.0, 'lng_min': -109.1, 'lng_max': -103.0},
    'NY': {'lat_min': 40.5, 'lat_max': 45.0, 'lng_min': -79.8, 'lng_max': -71.9},
    'NC': {'lat_min': 33.8, 'lat_max': 36.6, 'lng_min': -84.3, 'lng_max': -75.5},
    'ND': {'lat_min': 45.9, 'lat_max': 49.0, 'lng_min': -104.1, 'lng_max': -96.6},
    'OH': {'lat_min': 38.4, 'lat_max': 42.0, 'lng_min': -84.8, 'lng_max': -80.5},
    'OK': {'lat_min': 33.6, 'lat_max': 37.0, 'lng_min': -103.0, 'lng_max': -94.4},
    'OR': {'lat_min': 41.9, 'lat_max': 46.3, 'lng_min': -124.6, 'lng_max': -116.5},
    'PA': {'lat_min': 39.7, 'lat_max': 42.3, 'lng_min': -80.5, 'lng_max': -74.7},
    'RI': {'lat_min': 41.1, 'lat_max': 42.0, 'lng_min': -71.9, 'lng_max': -71.1},
    'SC': {'lat_min': 32.0, 'lat_max': 35.2, 'lng_min': -83.4, 'lng_max': -78.5},
    'SD': {'lat_min': 42.5, 'lat_max': 45.9, 'lng_min': -104.1, 'lng_max': -96.4},
    'TN': {'lat_min': 35.0, 'lat_max': 36.7, 'lng_min': -90.3, 'lng_max': -81.7},
    'TX': {'lat_min': 25.8, 'lat_max': 36.5, 'lng_min': -106.7, 'lng_max': -93.5},
    'UT': {'lat_min': 37.0, 'lat_max': 42.0, 'lng_min': -114.1, 'lng_max': -109.0},
    'VT': {'lat_min': 42.7, 'lat_max': 45.0, 'lng_min': -73.4, 'lng_max': -71.5},
    'VA': {'lat_min': 36.5, 'lat_max': 39.5, 'lng_min': -83.7, 'lng_max': -75.2},
    'WA': {'lat_min': 45.5, 'lat_max': 49.0, 'lng_min': -124.8, 'lng_max': -116.9},
    'WV': {'lat_min': 37.2, 'lat_max': 40.6, 'lng_min': -82.6, 'lng_max': -77.7},
    'WI': {'lat_min': 42.5, 'lat_max': 47.1, 'lng_min': -92.9, 'lng_max': -86.8},
    'WY': {'lat_min': 41.0, 'lat_max': 45.0, 'lng_min': -111.1, 'lng_max': -104.1},
    'DC': {'lat_min': 38.8, 'lat_max': 39.0, 'lng_min': -77.1, 'lng_max': -76.9},
    'PR': {'lat_min': 17.9, 'lat_max': 18.5, 'lng_min': -67.3, 'lng_max': -65.6},
}


def validate_coordinates(lat: float, lng: float, state: str = None) -> dict:
    """
    Validate that coordinates are within reasonable bounds.

    Args:
        lat: Latitude
        lng: Longitude
        state: Optional 2-letter state code for more specific validation

    Returns:
        Dict with 'valid' (bool) and 'reason' (str if invalid)
    """
    # Basic range check
    if lat is None or lng is None:
        return {'valid': False, 'reason': 'Missing coordinates'}

    if abs(lat) > 90:
        return {'valid': False, 'reason': f'Latitude {lat} out of range (-90 to 90)'}

    if abs(lng) > 180:
        return {'valid': False, 'reason': f'Longitude {lng} out of range (-180 to 180)'}

    # Check for null island (0, 0)
    if lat == 0 and lng == 0:
        return {'valid': False, 'reason': 'Coordinates are (0, 0) - null island'}

    # US mainland bounds (rough check)
    US_BOUNDS = {
        'lat_min': 24.0,  # Southern tip of Florida Keys
        'lat_max': 49.5,  # Northern border with Canada
        'lng_min': -125.0,  # West coast
        'lng_max': -66.0   # East coast
    }

    # Allow Alaska, Hawaii, Puerto Rico
    in_alaska = 51.0 <= lat <= 72.0 and -180.0 <= lng <= -129.0
    in_hawaii = 18.0 <= lat <= 23.0 and -161.0 <= lng <= -154.0
    in_puerto_rico = 17.5 <= lat <= 18.6 and -68.0 <= lng <= -65.0
    in_mainland = (US_BOUNDS['lat_min'] <= lat <= US_BOUNDS['lat_max'] and
                   US_BOUNDS['lng_min'] <= lng <= US_BOUNDS['lng_max'])

    if not (in_mainland or in_alaska or in_hawaii or in_puerto_rico):
        return {'valid': False, 'reason': f'Coordinates ({lat}, {lng}) outside US bounds'}

    # State-specific validation if state provided
    if state and state.upper() in STATE_BOUNDS:
        bounds = STATE_BOUNDS[state.upper()]
        if not (bounds['lat_min'] <= lat <= bounds['lat_max'] and
                bounds['lng_min'] <= lng <= bounds['lng_max']):
            return {
                'valid': False,
                'reason': f'Coordinates ({lat}, {lng}) outside {state} bounds'
            }

    return {'valid': True, 'reason': None}


def _enrich_with_coordinates(data: List[Dict], fips_field: str = 'county_fips') -> List[Dict]:
    """
    Add latitude/longitude to data records based on county FIPS code or name+state.

    Uses Census Bureau Gazetteer data for accurate centroids.
    Falls back to name+state lookup if FIPS doesn't match.
    Validates coordinates are within reasonable bounds.

    Args:
        data: List of data records
        fips_field: Field name containing county FIPS code

    Returns:
        Data enriched with latitude/longitude coordinates
    """
    for item in data:
        fips = item.get(fips_field)
        county_name = item.get('county_name') or item.get('city')
        state = item.get('state')
        
        # Normalize state to 2-letter code (centroids table uses codes)
        state_code = _normalize_state_to_code(state) if state else None

        # Try lookup by FIPS first, then by name+state
        centroid = lookup_county_centroid(
            county_fips=fips,
            county_name=county_name,
            state=state_code
        )

        if centroid:
            lat = centroid['lat']
            lng = centroid['lng']

            # Validate coordinates
            validation = validate_coordinates(lat, lng, state)
            if validation['valid']:
                item['latitude'] = lat
                item['longitude'] = lng
                # Also update county_name if we have a better one from centroids
                if not item.get('county_name') and centroid.get('name'):
                    item['county_name'] = centroid['name']
            else:
                # Invalid coordinates - log warning and skip
                print(f"[WARN] Invalid coordinates for {county_name}, {state}: {validation['reason']}")
                item['latitude'] = None
                item['longitude'] = None
        else:
            # Clear any existing bogus coordinates
            item['latitude'] = None
            item['longitude'] = None
            if fips or county_name:
                print(f"[WARN] No centroid found for: fips={fips}, name={county_name}, state={state}")

    return data


# Cache for lender names
_lender_names_cache: Dict[str, str] = {}

def _enrich_lender_names(data: List[Dict]) -> List[Dict]:
    """
    Look up lender names from the GLEIF reference table for any records missing lender_name.
    
    Args:
        data: List of records with lender_id (LEI) field
        
    Returns:
        Data enriched with lender_name from GLEIF data
    """
    global _lender_names_cache
    
    # Find LEIs that need lookup
    leis_to_lookup = set()
    for item in data:
        lei = item.get('lender_id')
        if lei and not item.get('lender_name'):
            if lei not in _lender_names_cache:
                leis_to_lookup.add(lei)
    
    # Batch lookup from GLEIF table
    if leis_to_lookup:
        try:
            client = get_bigquery_client()
            leis_str = "', '".join(leis_to_lookup)
            query = f"""
                SELECT lei, display_name
                FROM `justdata-ncrc.shared.lender_names_gleif`
                WHERE lei IN ('{leis_str}')
            """
            results = client.query(query).result()
            for row in results:
                _lender_names_cache[row.lei] = row.display_name
            print(f"[INFO] Loaded {len(leis_to_lookup)} lender names from GLEIF")
        except Exception as e:
            print(f"[WARN] Could not load lender names from GLEIF: {e}")
    
    # Enrich the data
    for item in data:
        lei = item.get('lender_id')
        if lei and not item.get('lender_name'):
            item['lender_name'] = _lender_names_cache.get(lei)
    
    return data


def _enrich_lender_interest_with_coordinates(data: List[Dict]) -> List[Dict]:
    """
    Add latitude/longitude to lender interest data based on researcher county FIPS.

    Uses Census Bureau Gazetteer data for accurate centroids.

    Args:
        data: List of lender interest records with researcher_county_fips field

    Returns:
        Data enriched with latitude/longitude coordinates for map display
    """
    for item in data:
        fips = item.get('researcher_county_fips')
        county_name = item.get('researcher_city')
        state = item.get('researcher_state')
        
        # Normalize state to 2-letter code
        state_code = _normalize_state_to_code(state) if state else None

        centroid = lookup_county_centroid(
            county_fips=fips,
            county_name=county_name,
            state=state_code
        )

        if centroid:
            item['latitude'] = centroid['lat']
            item['longitude'] = centroid['lng']
        else:
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
        FROM `justdata-ncrc.shared.cbsa_to_county`
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

    # Process top lenders
    top_lenders = [dict(row) for row in results.get('top_lenders', [])]

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
            COUNT(*) AS total_reports,
            COUNT(DISTINCT county_fips) AS counties_researched,
            COUNT(DISTINCT lender_id) AS lenders_researched,
            MAX(event_timestamp) AS last_activity,
            MIN(event_timestamp) AS first_activity,
            ARRAY_AGG(DISTINCT event_name ORDER BY event_name) AS apps_used
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
            COALESCE(user_id, 'test_user') AS user_id,
            COUNT(*) AS report_count,
            MAX(event_timestamp) AS last_activity,
            MIN(event_timestamp) AS first_activity
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('{target_apps_str}')
            {entity_filter}
            {date_filter}
        GROUP BY COALESCE(user_id, 'test_user')
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


def _is_ga4_client_id(user_id: str) -> bool:
    """
    Check if a user_id is a GA4 client ID (format: number.number) vs Firebase Auth UID.
    GA4 client IDs look like: 2106917405.1769129344
    Firebase Auth UIDs are alphanumeric without periods.
    """
    if not user_id:
        return False
    # GA4 client IDs contain a period and are numeric on both sides
    if '.' in user_id:
        parts = user_id.split('.')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return True
    return False


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

        # Skip GA4 client IDs - they won't have Firestore profiles
        # GA4 client IDs look like: 2106917405.1769129344
        if _is_ga4_client_id(user_id):
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


def _lookup_single_lender_name(lender_id: str) -> Optional[str]:
    """Look up a single lender name from GLEIF table."""
    global _lender_names_cache
    
    if lender_id in _lender_names_cache:
        return _lender_names_cache.get(lender_id)
    
    try:
        client = get_bigquery_client()
        query = f"""
            SELECT display_name
            FROM `justdata-ncrc.shared.lender_names_gleif`
            WHERE lei = '{lender_id}'
            LIMIT 1
        """
        results = list(client.query(query).result())
        if results:
            name = results[0].display_name
            _lender_names_cache[lender_id] = name
            return name
    except Exception as e:
        print(f"[WARN] Could not look up lender name for {lender_id}: {e}")
    
    return None


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

    # Query the usage_log table for MergerMeter events for this lender
    # MergerMeter events store lender_id in parameters_json as acquirer_lei or target_lei
    summary_query = f"""
        SELECT
            '{lender_id}' AS lender_id,
            COUNT(*) AS total_reports,
            COUNT(DISTINCT COALESCE(user_id, user_email, CAST(timestamp AS STRING))) AS unique_researchers,
            MIN(timestamp) AS first_activity,
            MAX(timestamp) AS last_activity
        FROM `justdata-ncrc.cache.usage_log`
        WHERE app_name = 'mergermeter'
            AND error_message IS NULL
            AND (JSON_VALUE(parameters_json, '$.acquirer_lei') = '{lender_id}'
                 OR JSON_VALUE(parameters_json, '$.target_lei') = '{lender_id}')
            {date_filter}
    """

    # Get all reports for this lender with acquirer/target info from parameters
    reports_query = f"""
        SELECT
            timestamp AS event_timestamp,
            app_name AS report_type,
            JSON_VALUE(parameters_json, '$.acquirer_name') AS acquirer_name,
            JSON_VALUE(parameters_json, '$.target_name') AS target_name,
            JSON_VALUE(parameters_json, '$.acquirer_lei') AS acquirer_lei,
            JSON_VALUE(parameters_json, '$.target_lei') AS target_lei,
            COALESCE(user_id, user_email) AS user_id,
            user_email
        FROM `justdata-ncrc.cache.usage_log`
        WHERE app_name = 'mergermeter'
            AND error_message IS NULL
            AND (JSON_VALUE(parameters_json, '$.acquirer_lei') = '{lender_id}'
                 OR JSON_VALUE(parameters_json, '$.target_lei') = '{lender_id}')
            {date_filter}
        ORDER BY timestamp DESC
        LIMIT 500
    """

    # Get researchers for this lender
    researchers_query = f"""
        SELECT
            COALESCE(user_id, user_email) AS user_id,
            user_email,
            COUNT(*) AS report_count,
            MAX(timestamp) AS last_activity,
            MIN(timestamp) AS first_activity
        FROM `justdata-ncrc.cache.usage_log`
        WHERE app_name = 'mergermeter'
            AND error_message IS NULL
            AND (JSON_VALUE(parameters_json, '$.acquirer_lei') = '{lender_id}'
                 OR JSON_VALUE(parameters_json, '$.target_lei') = '{lender_id}')
            AND (user_id IS NOT NULL OR user_email IS NOT NULL)
            {date_filter}
        GROUP BY COALESCE(user_id, user_email), user_email
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


# =============================================================================
# COST MONITORING
# =============================================================================

def get_cost_summary(days: int = 30, project_id: str = None, skip_cache: bool = False) -> Dict[str, Any]:
    """
    Get BigQuery cost summary from INFORMATION_SCHEMA.

    Queries job history to calculate estimated costs by app.
    Cost calculation: $6.25 per TB processed (BigQuery on-demand pricing).

    Args:
        days: Number of days to look back (default 30)
        project_id: GCP project to query (default from config)
        skip_cache: If True, bypass cache and re-query

    Returns:
        Dictionary with:
        - total_bytes_processed: Total bytes across all queries
        - total_tb_processed: Total terabytes processed
        - estimated_cost_usd: Estimated cost in USD
        - query_count: Number of queries
        - cost_by_app: Dict mapping app names to their costs
        - daily_costs: List of daily cost records
    """
    cache_key = _cache_key('get_cost_summary', days=days, project_id=project_id)
    # Check cache first (unless skip_cache)
    if not skip_cache:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached
    
    client = get_bigquery_client()
    if project_id is None:
        project_id = config.BIGQUERY_PROJECT
    
    # Cost per TB in USD (BigQuery on-demand pricing)
    COST_PER_TB = 6.25
    
    # JustData service accounts to track (hdma1 legacy + justdata-ncrc)
    SERVICE_ACCOUNTS = [
        'apiclient@hdma1-242116.iam.gserviceaccount.com',
        'justdata@hdma1-242116.iam.gserviceaccount.com',
        'lendsight@justdata-ncrc.iam.gserviceaccount.com',
        'bizsight@justdata-ncrc.iam.gserviceaccount.com',
        'branchsight@justdata-ncrc.iam.gserviceaccount.com',
        'branchmapper@justdata-ncrc.iam.gserviceaccount.com',
        'mergermeter@justdata-ncrc.iam.gserviceaccount.com',
        'dataexplorer@justdata-ncrc.iam.gserviceaccount.com',
        'lenderprofile@justdata-ncrc.iam.gserviceaccount.com',
        'analytics@justdata-ncrc.iam.gserviceaccount.com',
        'electwatch@justdata-ncrc.iam.gserviceaccount.com',
        
    ]
    service_accounts_str = "', '".join(SERVICE_ACCOUNTS)
    
    # Query both projects in PARALLEL for job metadata:
    # - justdata-ncrc: new project (Jan 2026+)
    # - hdma1-242116: historical project (older data)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def query_project_costs(project: str, region: str) -> tuple:
        """Query a single project for cost data. Returns (project, app_results, daily_results) or (project, None, None) on error."""
        app_query = f"""
        SELECT
            CASE
                -- JustData Apps (order matters - most specific first)
                WHEN LOWER(query) LIKE '%de_hmda%' OR LOWER(query) LIKE '%lendsight%' OR user_email LIKE 'lendsight@%' THEN 'LendSight'
                WHEN LOWER(query) LIKE '%sb_%' OR LOWER(query) LIKE '%bizsight%' OR LOWER(query) LIKE '%disclosure%' OR user_email LIKE 'bizsight@%' THEN 'BizSight'
                WHEN LOWER(query) LIKE '%sod%' OR LOWER(query) LIKE '%branchsight%' OR LOWER(query) LIKE '%fdic%' OR user_email LIKE 'branchsight@%' THEN 'BranchSight'
                WHEN LOWER(query) LIKE '%mergermeter%' OR user_email LIKE 'mergermeter@%' THEN 'MergerMeter'
                WHEN LOWER(query) LIKE '%dataexplorer%' OR user_email LIKE 'dataexplorer@%' THEN 'DataExplorer'
                WHEN LOWER(query) LIKE '%lenderprofile%' OR user_email LIKE 'lenderprofile@%' THEN 'LenderProfile'
                WHEN LOWER(query) LIKE '%electwatch%' OR user_email LIKE 'electwatch@%' THEN 'ElectWatch'
                WHEN user_email LIKE 'branchmapper@%' THEN 'BranchMapper'
                
                -- Platform Services
                WHEN LOWER(query) LIKE '%analytics%' OR LOWER(query) LIKE '%all_events%' OR LOWER(query) LIKE '%backfilled%' OR user_email LIKE 'analytics@%' THEN 'Analytics'
                WHEN user_email LIKE 'firebase-admin@%' OR LOWER(query) LIKE '%firebase_analytics%' THEN 'Firebase'
                WHEN LOWER(query) LIKE '%usage_log%' OR LOWER(query) LIKE '%.cache.%' THEN 'Cache/Logging'
                
                -- Infrastructure / Metadata
                WHEN LOWER(query) LIKE '%information_schema%' THEN 'Metadata Queries'
                WHEN LOWER(query) LIKE '%__tables__%' OR LOWER(query) LIKE '%__partitions__%' THEN 'Metadata Queries'
                
                -- External Tools
                WHEN user_email LIKE '%@bigquery-public-data%' THEN 'Public Data'
                WHEN user_email LIKE '%looker%' OR LOWER(query) LIKE '%looker%' THEN 'Looker/Data Studio'
                WHEN user_email LIKE '%dataform%' OR LOWER(query) LIKE '%dataform%' THEN 'Dataform'
                WHEN user_email LIKE '%scheduled%' OR job_id LIKE 'scheduled_query%' THEN 'Scheduled Queries'
                
                -- Console / Manual queries (catch-all for known GCP service accounts)
                WHEN user_email LIKE '%gserviceaccount.com' THEN 'Service Accounts'
                
                ELSE 'Other/Manual'
            END as app_name,
            COUNT(*) as query_count,
            SUM(total_bytes_processed) as total_bytes,
            SUM(total_bytes_billed) as total_bytes_billed
        FROM `{project}`.`{region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
            AND job_type = 'QUERY' AND state = 'DONE' AND error_result IS NULL
        GROUP BY app_name
        """
        daily_query = f"""
        SELECT
            DATE(creation_time) as date,
            CASE
                -- JustData Apps (order matters - most specific first)
                WHEN LOWER(query) LIKE '%de_hmda%' OR LOWER(query) LIKE '%lendsight%' OR user_email LIKE 'lendsight@%' THEN 'LendSight'
                WHEN LOWER(query) LIKE '%sb_%' OR LOWER(query) LIKE '%bizsight%' OR LOWER(query) LIKE '%disclosure%' OR user_email LIKE 'bizsight@%' THEN 'BizSight'
                WHEN LOWER(query) LIKE '%sod%' OR LOWER(query) LIKE '%branchsight%' OR LOWER(query) LIKE '%fdic%' OR user_email LIKE 'branchsight@%' THEN 'BranchSight'
                WHEN LOWER(query) LIKE '%mergermeter%' OR user_email LIKE 'mergermeter@%' THEN 'MergerMeter'
                WHEN LOWER(query) LIKE '%dataexplorer%' OR user_email LIKE 'dataexplorer@%' THEN 'DataExplorer'
                WHEN LOWER(query) LIKE '%lenderprofile%' OR user_email LIKE 'lenderprofile@%' THEN 'LenderProfile'
                WHEN LOWER(query) LIKE '%electwatch%' OR user_email LIKE 'electwatch@%' THEN 'ElectWatch'
                WHEN user_email LIKE 'branchmapper@%' THEN 'BranchMapper'
                
                -- Platform Services
                WHEN LOWER(query) LIKE '%analytics%' OR LOWER(query) LIKE '%all_events%' OR LOWER(query) LIKE '%backfilled%' OR user_email LIKE 'analytics@%' THEN 'Analytics'
                WHEN user_email LIKE 'firebase-admin@%' OR LOWER(query) LIKE '%firebase_analytics%' THEN 'Firebase'
                WHEN LOWER(query) LIKE '%usage_log%' OR LOWER(query) LIKE '%.cache.%' THEN 'Cache/Logging'
                
                -- Infrastructure / Metadata
                WHEN LOWER(query) LIKE '%information_schema%' THEN 'Metadata Queries'
                WHEN LOWER(query) LIKE '%__tables__%' OR LOWER(query) LIKE '%__partitions__%' THEN 'Metadata Queries'
                
                -- External Tools
                WHEN user_email LIKE '%@bigquery-public-data%' THEN 'Public Data'
                WHEN user_email LIKE '%looker%' OR LOWER(query) LIKE '%looker%' THEN 'Looker/Data Studio'
                WHEN user_email LIKE '%dataform%' OR LOWER(query) LIKE '%dataform%' THEN 'Dataform'
                WHEN user_email LIKE '%scheduled%' OR job_id LIKE 'scheduled_query%' THEN 'Scheduled Queries'
                
                -- Console / Manual queries (catch-all for known GCP service accounts)
                WHEN user_email LIKE '%gserviceaccount.com' THEN 'Service Accounts'
                
                ELSE 'Other/Manual'
            END as app_name,
            COUNT(*) as query_count,
            SUM(total_bytes_processed) as total_bytes,
            SUM(total_bytes_billed) as total_bytes_billed
        FROM `{project}`.`{region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
            AND job_type = 'QUERY' AND state = 'DONE' AND error_result IS NULL
        GROUP BY date, app_name
        """
        try:
            app_results = list(client.query(app_query).result())
            daily_results = list(client.query(daily_query).result())
            return (project, app_results, daily_results)
        except Exception as e:
            print(f"[COST] {project} failed: {str(e)[:80]}")
            return (project, None, None)
    
    all_app_results = []
    all_daily_results = []
    successful_projects = []
    
    # Run both project queries in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(query_project_costs, 'justdata-ncrc', 'region-us'),
            executor.submit(query_project_costs, 'hdma1-242116', 'region-us'),
        ]
        for future in as_completed(futures):
            project, app_results, daily_results = future.result()
            if app_results is not None:
                all_app_results.extend(app_results)
                all_daily_results.extend(daily_results)
                successful_projects.append(project)

    # Use combined results from all successful projects
    if not successful_projects:
        print(f"BigQuery error in get_cost_summary: No projects succeeded")
        return {
            'error': "No projects returned data",
            'period_days': days,
            'total_bytes_processed': 0,
            'total_tb_processed': 0,
            'estimated_cost_usd': 0,
            'query_count': 0,
            'cost_by_app': {},
            'daily_costs': []
        }

    print(f"[COST] Combined results from {successful_projects}: {len(all_app_results)} app rows, {len(all_daily_results)} daily rows")
    
    # Categories to exclude from JustData costs (not attributable to apps)
    EXCLUDED_CATEGORIES = {'Other/Manual', 'Service Accounts', 'Metadata Queries', 'Public Data'}
    
    try:
        # Process cost by app results (aggregate across projects)
        cost_by_app = {}
        total_bytes = 0
        total_queries = 0
        
        for row in all_app_results:
            app_name = row.app_name
            
            # Skip non-JustData categories
            if app_name in EXCLUDED_CATEGORIES:
                continue
            
            bytes_processed = row.total_bytes or 0
            bytes_billed = row.total_bytes_billed or 0
            query_count = row.query_count or 0
            
            tb_processed = bytes_processed / (1024 ** 4)
            tb_billed = bytes_billed / (1024 ** 4)
            cost_usd = tb_billed * COST_PER_TB
            
            # Aggregate if app already exists (from multiple projects)
            if app_name in cost_by_app:
                cost_by_app[app_name]['query_count'] += query_count
                cost_by_app[app_name]['bytes_processed'] += bytes_processed
                cost_by_app[app_name]['tb_processed'] += round(tb_processed, 4)
                cost_by_app[app_name]['bytes_billed'] += bytes_billed
                cost_by_app[app_name]['tb_billed'] += round(tb_billed, 4)
                cost_by_app[app_name]['estimated_cost_usd'] += round(cost_usd, 2)
            else:
                cost_by_app[app_name] = {
                    'query_count': query_count,
                    'bytes_processed': bytes_processed,
                    'tb_processed': round(tb_processed, 4),
                    'bytes_billed': bytes_billed,
                    'tb_billed': round(tb_billed, 4),
                    'estimated_cost_usd': round(cost_usd, 2)
                }
            
            total_bytes += bytes_billed
            total_queries += query_count
        
        # Aggregate daily costs by date with app breakdown (across projects)
        daily_by_date = {}
        for row in all_daily_results:
            date_str = row.date.isoformat() if row.date else None
            if not date_str:
                continue
            
            app_name = row.app_name or 'Other/Manual'
            
            # Skip non-JustData categories from daily chart too
            if app_name in EXCLUDED_CATEGORIES:
                continue
            
            bytes_billed = row.total_bytes_billed or 0
            tb_billed = bytes_billed / (1024 ** 4)
            cost_usd = tb_billed * COST_PER_TB
            
            if date_str not in daily_by_date:
                daily_by_date[date_str] = {
                    'date': date_str,
                    'query_count': 0,
                    'bytes_processed': 0,
                    'bytes_billed': 0,
                    'tb_billed': 0,
                    'estimated_cost_usd': 0,
                    'by_app': {}
                }
            
            daily_by_date[date_str]['query_count'] += row.query_count or 0
            daily_by_date[date_str]['bytes_processed'] += row.total_bytes or 0
            daily_by_date[date_str]['bytes_billed'] += bytes_billed
            daily_by_date[date_str]['tb_billed'] += tb_billed
            daily_by_date[date_str]['estimated_cost_usd'] += cost_usd
            daily_by_date[date_str]['by_app'][app_name] = round(cost_usd, 4)
        
        # Convert to list and round values
        daily_costs = []
        for date_str in sorted(daily_by_date.keys(), reverse=True):
            day = daily_by_date[date_str]
            day['tb_billed'] = round(day['tb_billed'], 4)
            day['estimated_cost_usd'] = round(day['estimated_cost_usd'], 4)
            daily_costs.append(day)
        
        # Calculate totals
        total_tb = total_bytes / (1024 ** 4)
        total_cost = total_tb * COST_PER_TB
        
        result = {
            'period_days': days,
            'total_bytes_processed': total_bytes,
            'total_tb_processed': round(total_tb, 4),
            'estimated_cost_usd': round(total_cost, 2),
            'query_count': total_queries,
            'cost_per_tb_usd': COST_PER_TB,
            'cost_by_app': cost_by_app,
            'daily_costs': daily_costs
        }
        
        _set_cached(cache_key, result)
        return result
        
    except Exception as e:
        print(f"BigQuery error in get_cost_summary: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e),
            'period_days': days,
            'total_bytes_processed': 0,
            'total_tb_processed': 0,
            'estimated_cost_usd': 0,
            'query_count': 0,
            'cost_by_app': {},
            'daily_costs': []
        }
