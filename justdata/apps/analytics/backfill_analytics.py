"""
Analytics Backfill Script

Populates analytics data from existing JustData usage logs and analysis results.
This allows analytics to show historical data before Firebase Analytics was enabled.

DATA SOURCES:
  - justdata-ncrc.cache.usage_log - Every API request with app, params, user_type
  - justdata-ncrc.cache.analysis_results - Completed jobs with county/lender details

TARGET:
  - justdata-ncrc.firebase_analytics.backfilled_events - Historical events table

USAGE:
  python -m justdata.apps.analytics.backfill_analytics

# =============================================================================
# HUBSPOT INTEGRATION NOTE
# =============================================================================
#
# Currently, the usage_log stores user_type but NOT individual user identity.
# To enable coalition building with organization context, we need to:
#
# 1. Add user_id (Firebase UID) to usage_log going forward
# 2. Backfill user_id where possible from session data or Firestore
# 3. Link user_id to HubSpot contact_id (see hubspot_integration.py)
#
# Without user identity, we can still show:
# - Which counties are being researched (from parameters)
# - Which lenders are being researched (from parameters)
# - Total report counts by app
# - Geographic distribution of research activity
#
# With user identity + HubSpot, we can additionally show:
# - Which ORGANIZATIONS are researching the same entities
# - Coalition opportunities between specific orgs
# - Researcher contact info for outreach
# =============================================================================
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.cloud import bigquery

# Source project (JustData app data)
SOURCE_PROJECT = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
SOURCE_DATASET = 'cache'

# Target project/dataset for backfilled analytics
# Using same project as source since credentials work there
# All analytics data goes to firebase_analytics dataset for unified queries
TARGET_PROJECT = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
TARGET_DATASET = 'firebase_analytics'


def get_client(project_id: str) -> bigquery.Client:
    """Get BigQuery client for a project."""
    from justdata.shared.utils.bigquery_client import get_bigquery_client
    return get_bigquery_client(project_id)


def create_dataset_if_not_exists(client: bigquery.Client, project_id: str, dataset_id: str) -> None:
    """Create the dataset if it doesn't exist."""
    dataset_ref = f"{project_id}.{dataset_id}"

    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset already exists: {dataset_ref}")
    except Exception:
        # Dataset doesn't exist, create it
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        dataset.description = "JustData Analytics - User activity and coalition building data"

        client.create_dataset(dataset)
        print(f"Created dataset: {dataset_ref}")


def create_backfill_table(client: bigquery.Client) -> None:
    """
    Create the backfilled_events table if it doesn't exist.

    This table mirrors the structure of Firebase Analytics events
    so it can be unioned with live data.
    """
    # First ensure the dataset exists
    create_dataset_if_not_exists(client, TARGET_PROJECT, TARGET_DATASET)

    schema = [
        bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("event_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("event_timestamp", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("user_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("user_type", "STRING", mode="NULLABLE"),

        # Event parameters (flattened for easier querying)
        bigquery.SchemaField("county_fips", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("county_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("state", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("lender_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("lender_id", "STRING", mode="NULLABLE"),  # LEI or RSSD
        bigquery.SchemaField("year_range", "STRING", mode="NULLABLE"),

        # Source metadata
        bigquery.SchemaField("source", "STRING", mode="REQUIRED"),  # 'backfill' or 'live'
        bigquery.SchemaField("source_job_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("source_cache_key", "STRING", mode="NULLABLE"),

        # For HubSpot integration (to be populated later)
        bigquery.SchemaField("hubspot_contact_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("hubspot_company_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("organization_name", "STRING", mode="NULLABLE"),

        bigquery.SchemaField("backfill_timestamp", "TIMESTAMP", mode="REQUIRED"),
    ]

    table_id = f"{TARGET_PROJECT}.{TARGET_DATASET}.backfilled_events"
    table = bigquery.Table(table_id, schema=schema)

    try:
        client.create_table(table)
        print(f"Created table: {table_id}")
    except Exception as e:
        if "Already Exists" in str(e):
            print(f"Table already exists: {table_id}")
        else:
            raise


def extract_county_from_params(params: Dict) -> tuple:
    """
    Extract county FIPS and state from various parameter formats.

    Returns: (county_fips, county_name, state)
    """
    county_fips = None
    county_name = None
    state = None

    # Try counties_data format (LendSight, BranchSight)
    counties_data = params.get('counties_data', [])
    if counties_data and isinstance(counties_data, list) and len(counties_data) > 0:
        first_county = counties_data[0]
        if isinstance(first_county, dict):
            county_fips = first_county.get('geoid5') or first_county.get('GEOID5')
            county_name = first_county.get('name')
            state = first_county.get('state_name') or first_county.get('state')

    # Try county_data format (BizSight)
    county_data = params.get('county_data', {})
    if isinstance(county_data, dict):
        county_fips = county_fips or county_data.get('geoid5') or county_data.get('GEOID5')
        county_name = county_name or county_data.get('name')
        state = state or county_data.get('state_name')

    # Try direct parameters
    county_fips = county_fips or params.get('geoid5') or params.get('county_fips')
    state = state or params.get('state') or params.get('state_code')

    # Try counties string format
    counties_str = params.get('counties', '')
    if not county_name and counties_str:
        county_name = counties_str.split(';')[0] if ';' in counties_str else counties_str

    return county_fips, county_name, state


def extract_lender_from_params(params: Dict) -> tuple:
    """
    Extract lender info from various parameter formats.

    Returns: (lender_name, lender_id)
    """
    lender_name = params.get('lender_name') or params.get('institution_name')
    lender_id = (
        params.get('lei') or
        params.get('rssd') or
        params.get('rssd_id') or
        params.get('acquirer_lei') or
        params.get('acquirer_rssd')
    )

    # For merger reports, use acquirer as primary
    if not lender_name:
        lender_name = params.get('acquirer_name')

    return lender_name, lender_id


def map_app_to_event_name(app_name: str) -> str:
    """Map app name to Firebase Analytics event name."""
    mapping = {
        'lendsight': 'lendsight_report',
        'bizsight': 'bizsight_report',
        'branchsight': 'branchsight_report',
        'branchsight': 'branchsight_report',
        'branchmapper': 'branchmapper_report',
        'mergermeter': 'mergermeter_report',
        'dataexplorer': 'dataexplorer_area_report',  # Default, may vary
        'lenderprofile': 'lenderprofile_view',
    }
    return mapping.get(app_name.lower(), f'{app_name.lower()}_event')


def backfill_from_usage_log(
    source_client: bigquery.Client,
    target_client: bigquery.Client,
    days_back: int = 365,
    batch_size: int = 1000
) -> int:
    """
    Backfill analytics events from the usage_log table.

    Args:
        source_client: BigQuery client for source project
        target_client: BigQuery client for target project
        days_back: Number of days to backfill
        batch_size: Number of rows per insert batch

    Returns:
        Number of events backfilled
    """
    # Query usage_log
    query = f"""
    SELECT
        request_id,
        timestamp,
        app_name,
        user_type,
        parameters_json,
        job_id,
        cache_key,
        cache_hit
    FROM `{SOURCE_PROJECT}.{SOURCE_DATASET}.usage_log`
    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days_back} DAY)
        AND app_name IN ('lendsight', 'bizsight', 'branchsight', 'branchsight',
                         'branchmapper', 'mergermeter', 'dataexplorer', 'lenderprofile')
    ORDER BY timestamp ASC
    """

    print(f"Querying usage_log for last {days_back} days...")
    results = source_client.query(query).result()

    rows_to_insert = []
    total_inserted = 0

    for row in results:
        try:
            # Parse parameters
            params = {}
            if row.parameters_json:
                if isinstance(row.parameters_json, str):
                    params = json.loads(row.parameters_json)
                else:
                    params = dict(row.parameters_json)

            # Extract county and lender info
            county_fips, county_name, state = extract_county_from_params(params)
            lender_name, lender_id = extract_lender_from_params(params)

            # Extract year range
            year_range = params.get('years', '') or params.get('year_range', '')
            if isinstance(year_range, list):
                year_range = ','.join(map(str, year_range))

            # Create event record
            event = {
                'event_id': row.request_id or f"backfill_{row.job_id}_{datetime.now().timestamp()}",
                'event_name': map_app_to_event_name(row.app_name),
                'event_timestamp': row.timestamp.isoformat() if row.timestamp else datetime.now().isoformat(),
                'user_id': None,  # Not available in usage_log - needs HubSpot integration
                'user_type': row.user_type,
                'county_fips': county_fips,
                'county_name': county_name,
                'state': state,
                'lender_name': lender_name,
                'lender_id': lender_id,
                'year_range': year_range,
                'source': 'backfill_usage_log',
                'source_job_id': row.job_id,
                'source_cache_key': row.cache_key,
                'hubspot_contact_id': None,  # To be populated via HubSpot integration
                'hubspot_company_id': None,
                'organization_name': None,
                'backfill_timestamp': datetime.now().isoformat(),
            }

            rows_to_insert.append(event)

            # Insert in batches
            if len(rows_to_insert) >= batch_size:
                insert_events(target_client, rows_to_insert)
                total_inserted += len(rows_to_insert)
                print(f"  Inserted {total_inserted} events...")
                rows_to_insert = []

        except Exception as e:
            print(f"  Warning: Error processing row {row.request_id}: {e}")
            continue

    # Insert remaining rows
    if rows_to_insert:
        insert_events(target_client, rows_to_insert)
        total_inserted += len(rows_to_insert)

    print(f"Backfill complete: {total_inserted} events inserted")
    return total_inserted


def insert_events(client: bigquery.Client, events: List[Dict]) -> None:
    """Insert events into the backfilled_events table."""
    table_id = f"{TARGET_PROJECT}.{TARGET_DATASET}.backfilled_events"

    errors = client.insert_rows_json(table_id, events)
    if errors:
        print(f"  Errors inserting rows: {errors[:5]}")  # Show first 5 errors


def create_unified_view(client: bigquery.Client) -> None:
    """
    Create a unified view that combines backfilled events with live Firebase data.

    This view can be used by the analytics dashboard to query all historical
    and live data in one place.
    """
    # For now, just create a simple view of backfilled events
    # Firebase Analytics will be added later once export is enabled
    view_sql = f"""
    CREATE OR REPLACE VIEW `{TARGET_PROJECT}.{TARGET_DATASET}.all_events` AS

    -- Backfilled events from usage_log
    SELECT
        event_id,
        event_name,
        event_timestamp,
        user_id,
        user_type,
        county_fips,
        county_name,
        state,
        lender_name,
        lender_id,
        year_range,
        source,
        hubspot_contact_id,
        hubspot_company_id,
        organization_name
    FROM `{TARGET_PROJECT}.{TARGET_DATASET}.backfilled_events`

    -- TODO: Add UNION ALL with Firebase Analytics events once export is enabled
    -- The Firebase data will be in justdata-f7da7.analytics_*.events_*
    -- You'll need cross-project access or copy the data to this project
    """

    try:
        client.query(view_sql).result()
        print(f"Created unified view: {TARGET_PROJECT}.{TARGET_DATASET}.all_events")
    except Exception as e:
        print(f"Warning: Could not create unified view: {e}")


def get_backfill_summary(client: bigquery.Client) -> Dict[str, Any]:
    """Get summary of backfilled data for verification."""
    query = f"""
    SELECT
        event_name,
        COUNT(*) AS event_count,
        COUNT(DISTINCT county_fips) AS unique_counties,
        COUNT(DISTINCT lender_id) AS unique_lenders,
        MIN(event_timestamp) AS earliest_event,
        MAX(event_timestamp) AS latest_event
    FROM `{TARGET_PROJECT}.{TARGET_DATASET}.backfilled_events`
    GROUP BY event_name
    ORDER BY event_count DESC
    """

    results = client.query(query).result()
    summary = []
    for row in results:
        summary.append({
            'event_name': row.event_name,
            'event_count': row.event_count,
            'unique_counties': row.unique_counties,
            'unique_lenders': row.unique_lenders,
            'earliest_event': str(row.earliest_event),
            'latest_event': str(row.latest_event),
        })

    return {'events_by_type': summary}


def main():
    """Run the backfill process."""
    print("=" * 60)
    print("JustData Analytics Backfill")
    print("=" * 60)
    print()

    print(f"Source: {SOURCE_PROJECT}.{SOURCE_DATASET}.usage_log")
    print(f"Target: {TARGET_PROJECT}.{TARGET_DATASET}.backfilled_events")
    print()

    # Get clients
    print("Connecting to BigQuery...")
    source_client = get_client(SOURCE_PROJECT)
    target_client = get_client(TARGET_PROJECT)

    # Create target table
    print("\n1. Creating backfilled_events table...")
    create_backfill_table(target_client)

    # Run backfill
    print("\n2. Backfilling from usage_log...")
    events_inserted = backfill_from_usage_log(
        source_client,
        target_client,
        days_back=365,  # Last year
        batch_size=500
    )

    # Create unified view
    print("\n3. Creating unified view...")
    create_unified_view(target_client)

    # Show summary
    print("\n4. Backfill Summary:")
    print("-" * 40)
    summary = get_backfill_summary(target_client)
    for event in summary.get('events_by_type', []):
        print(f"  {event['event_name']}:")
        print(f"    - Events: {event['event_count']}")
        print(f"    - Unique counties: {event['unique_counties']}")
        print(f"    - Unique lenders: {event['unique_lenders']}")
        print(f"    - Date range: {event['earliest_event']} to {event['latest_event']}")

    print("\n" + "=" * 60)
    print("Backfill complete!")
    print()
    print("Next steps:")
    print("  1. Enable Firebase -> BigQuery export for live data")
    print("  2. Update bigquery_client.py to query from 'all_events' view")
    print("  3. Implement HubSpot integration for organization context")
    print("=" * 60)


if __name__ == '__main__':
    main()
