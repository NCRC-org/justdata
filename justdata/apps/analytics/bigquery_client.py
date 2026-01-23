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
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.oauth2 import service_account

from .config import config


# Initialize BigQuery client
_client = None

# Use backfilled data from hdma1-242116 project
ANALYTICS_PROJECT = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')
ANALYTICS_DATASET = 'justdata_analytics'
EVENTS_TABLE = f'{ANALYTICS_PROJECT}.{ANALYTICS_DATASET}.all_events'


def get_bigquery_client():
    """Get or create BigQuery client."""
    global _client
    if _client is None:
        # Try to get credentials from environment
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            import json
            creds_dict = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            _client = bigquery.Client(
                project=ANALYTICS_PROJECT,
                credentials=credentials
            )
        else:
            # Fall back to default credentials
            _client = bigquery.Client(project=ANALYTICS_PROJECT)
    return _client


def _format_date_suffix(days: int) -> str:
    """Get date suffix for BigQuery table partitions."""
    date = datetime.utcnow() - timedelta(days=days)
    return date.strftime('%Y%m%d')


def get_user_locations(days: int = 90, state: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get user clusters by city/state with coordinates.

    Args:
        days: Number of days to look back
        state: Optional state filter (2-letter code)

    Returns:
        List of location records with user counts
    """
    client = get_bigquery_client()

    query = f"""
        SELECT
            state,
            county_name AS city,
            COUNT(DISTINCT COALESCE(user_id, event_id)) AS unique_users,
            COUNT(*) AS total_events,
            MAX(event_timestamp) AS last_activity,
            hubspot_contact_id,
            hubspot_company_id,
            organization_name
        FROM `{EVENTS_TABLE}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
            AND state IS NOT NULL
    """

    if state:
        query += f" AND state = '{state}'"

    query += """
        GROUP BY state, county_name, hubspot_contact_id, hubspot_company_id, organization_name
        ORDER BY unique_users DESC
        LIMIT 500
    """

    try:
        results = client.query(query).result()
        return [dict(row) for row in results]
    except Exception as e:
        print(f"BigQuery error in get_user_locations: {e}")
        return []


def get_research_activity(
    days: int = 90,
    app: Optional[str] = None,
    state: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get counties being researched with report counts.

    Args:
        days: Number of days to look back
        app: Optional app filter (e.g., 'lendsight_report')
        state: Optional state filter

    Returns:
        List of county research records
    """
    client = get_bigquery_client()

    query = f"""
        SELECT
            county_fips,
            state,
            county_name,
            event_name AS app_name,
            COUNT(DISTINCT COALESCE(user_id, event_id)) AS unique_users,
            COUNT(*) AS report_count,
            MAX(event_timestamp) AS last_activity
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('lendsight_report', 'bizsight_report', 'branchsight_report', 'branchmapper_report')
            AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
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


def get_lender_interest(days: int = 90, min_users: int = 1) -> List[Dict[str, Any]]:
    """
    Get lenders being researched with researcher locations.

    Args:
        days: Number of days to look back
        min_users: Minimum unique users to include

    Returns:
        List of lender interest records
    """
    client = get_bigquery_client()

    query = f"""
        SELECT
            lender_id,
            lender_name,
            state AS researcher_state,
            county_name AS researcher_city,
            COUNT(DISTINCT COALESCE(user_id, event_id)) AS unique_users,
            COUNT(*) AS event_count,
            MAX(event_timestamp) AS last_activity
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('mergermeter_report', 'dataexplorer_lender_report', 'lenderprofile_view')
            AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY lender_id, lender_name, researcher_state, researcher_city
        HAVING lender_id IS NOT NULL AND COUNT(DISTINCT COALESCE(user_id, event_id)) >= {min_users}
        ORDER BY unique_users DESC, event_count DESC
        LIMIT 500
    """

    try:
        results = client.query(query).result()
        return [dict(row) for row in results]
    except Exception as e:
        print(f"BigQuery error in get_lender_interest: {e}")
        return []


def get_coalition_opportunities(
    days: int = 90,
    min_users: int = 3,
    entity_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get entities (counties or lenders) with multiple researchers.
    Useful for identifying coalition-building opportunities.

    Args:
        days: Number of days to look back
        min_users: Minimum unique users researching same entity
        entity_type: Filter by 'county' or 'lender'

    Returns:
        List of coalition opportunity records
    """
    client = get_bigquery_client()

    query = f"""
        WITH all_research AS (
            -- Lender research
            SELECT
                'lender' AS entity_type,
                lender_id AS entity_id,
                lender_name AS entity_name,
                COALESCE(user_id, event_id) AS user_id,
                organization_name AS user_organization,
                state AS researcher_state,
                event_timestamp
            FROM `{EVENTS_TABLE}`
            WHERE event_name IN ('mergermeter_report', 'dataexplorer_lender_report', 'lenderprofile_view')
                AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
                AND lender_id IS NOT NULL

            UNION ALL

            -- County research
            SELECT
                'county' AS entity_type,
                county_fips AS entity_id,
                county_name AS entity_name,
                COALESCE(user_id, event_id) AS user_id,
                organization_name AS user_organization,
                state AS researcher_state,
                event_timestamp
            FROM `{EVENTS_TABLE}`
            WHERE event_name IN ('lendsight_report', 'bizsight_report', 'branchsight_report', 'branchmapper_report')
                AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
                AND county_fips IS NOT NULL
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

        return data
    except Exception as e:
        print(f"BigQuery error in get_coalition_opportunities: {e}")
        return []


def get_summary(days: int = 90) -> Dict[str, Any]:
    """
    Get summary metrics for the dashboard.

    Args:
        days: Number of days to look back

    Returns:
        Summary dict with total_users, total_events, top_counties, top_lenders
    """
    client = get_bigquery_client()

    # Total users and events
    totals_query = f"""
        SELECT
            COUNT(DISTINCT COALESCE(user_id, event_id)) AS total_users,
            COUNT(*) AS total_events
        FROM `{EVENTS_TABLE}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    """

    try:
        totals_result = list(client.query(totals_query).result())
        if totals_result:
            total_users = totals_result[0].get('total_users', 0)
            total_events = totals_result[0].get('total_events', 0)
        else:
            total_users = 0
            total_events = 0
    except Exception as e:
        print(f"BigQuery error getting totals: {e}")
        total_users = 0
        total_events = 0

    # Top researched counties
    top_counties_query = f"""
        SELECT
            county_fips,
            state,
            county_name,
            COUNT(*) AS total_reports
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('lendsight_report', 'bizsight_report', 'branchsight_report', 'branchmapper_report')
            AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
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

    # Top researched lenders
    top_lenders_query = f"""
        SELECT
            lender_id,
            lender_name,
            COUNT(*) AS total_events
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN ('mergermeter_report', 'dataexplorer_lender_report', 'lenderprofile_view')
            AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
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

    # App usage breakdown
    app_usage_query = f"""
        SELECT
            event_name,
            COUNT(*) AS event_count,
            COUNT(DISTINCT COALESCE(user_id, event_id)) AS unique_users
        FROM `{EVENTS_TABLE}`
        WHERE event_name IN (
            'lendsight_report', 'bizsight_report', 'branchsight_report',
            'branchmapper_report', 'mergermeter_report',
            'dataexplorer_area_report', 'dataexplorer_lender_report', 'lenderprofile_view'
        )
            AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY event_name
        ORDER BY event_count DESC
    """

    try:
        app_usage = [dict(row) for row in client.query(app_usage_query).result()]
    except Exception as e:
        print(f"BigQuery error getting app usage: {e}")
        app_usage = []

    return {
        'total_users': total_users,
        'total_events': total_events,
        'top_counties': top_counties,
        'top_lenders': top_lenders,
        'app_usage': app_usage,
        'days': days
    }


def get_user_activity_timeline(days: int = 30) -> List[Dict[str, Any]]:
    """
    Get daily activity counts for timeline chart.

    Args:
        days: Number of days to look back

    Returns:
        List of daily activity records
    """
    client = get_bigquery_client()

    query = f"""
        SELECT
            DATE(event_timestamp) AS date,
            COUNT(*) AS event_count,
            COUNT(DISTINCT COALESCE(user_id, event_id)) AS unique_users
        FROM `{EVENTS_TABLE}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY date
        ORDER BY date ASC
    """

    try:
        results = client.query(query).result()
        return [dict(row) for row in results]
    except Exception as e:
        print(f"BigQuery error in get_user_activity_timeline: {e}")
        return []
