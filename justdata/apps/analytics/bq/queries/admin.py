"""Admin / sync operations: backfill from usage_log into backfilled_events."""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from justdata.apps.analytics.bq.client import (
    BACKFILL_DATASET,
    BACKFILL_PROJECT,
    BACKFILL_TARGET_DATASET,
    QUERY_PROJECT,
    SYNC_CHECK_INTERVAL_SECONDS,
    clear_analytics_cache,
    get_bigquery_client,
)


# Module-level rate limit tracking (mirrors original)
_last_sync_check = None


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
