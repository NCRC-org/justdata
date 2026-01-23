"""
Analytics Aggregation Service

Performs daily aggregation of Firebase Analytics events.
Triggered by first visitor after midnight ET each day.
"""

import threading
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Eastern timezone
ET = ZoneInfo("America/New_York")

# In-memory lock to prevent concurrent aggregation
_aggregation_lock = threading.Lock()
_aggregation_in_progress = False
_table_checked = False


def ensure_aggregates_table_exists():
    """
    Ensure the daily_aggregates table exists in BigQuery.
    Creates it if it doesn't exist.
    """
    global _table_checked
    if _table_checked:
        return True

    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from google.cloud import bigquery

        client = get_bigquery_client()
        if not client:
            return False

        table_id = "hdma1-242116.justdata_analytics.daily_aggregates"

        # Check if table exists
        try:
            client.get_table(table_id)
            _table_checked = True
            return True
        except Exception:
            pass

        # Create table
        schema = [
            bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("total_events", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("unique_users", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("reports_generated", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("reports_by_app", "STRING", mode="NULLABLE"),  # JSON
            bigquery.SchemaField("reports_by_state", "STRING", mode="NULLABLE"),  # JSON
            bigquery.SchemaField("top_lenders", "STRING", mode="NULLABLE"),  # JSON
            bigquery.SchemaField("top_counties", "STRING", mode="NULLABLE"),  # JSON
            bigquery.SchemaField("aggregated_at", "STRING", mode="NULLABLE"),
        ]

        table = bigquery.Table(table_id, schema=schema)
        table = client.create_table(table)
        logger.info(f"Created daily_aggregates table: {table_id}")
        _table_checked = True
        return True

    except Exception as e:
        logger.error(f"Error ensuring aggregates table exists: {e}")
        return False


def get_today_midnight_et() -> datetime:
    """Get today's midnight in Eastern Time as UTC datetime."""
    now_et = datetime.now(ET)
    midnight_et = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_et


def check_and_trigger_aggregation():
    """
    Check if daily aggregation is needed and trigger it if so.

    This should be called on page loads. It checks Firestore for the
    last aggregation run time and triggers a background job if needed.

    Returns immediately - aggregation runs in background thread.
    """
    global _aggregation_in_progress

    # Quick check to avoid hitting Firestore on every request
    if _aggregation_in_progress:
        return

    try:
        from justdata.main.auth import get_firestore_client
        db = get_firestore_client()
        if not db:
            logger.warning("Firestore not available for analytics check")
            return

        # Get analytics status document
        status_ref = db.collection('system').document('analytics_status')
        status_doc = status_ref.get()

        today_midnight = get_today_midnight_et()

        if status_doc.exists:
            data = status_doc.to_dict()
            last_run = data.get('last_run')

            # Check if last_run is before today's midnight ET
            if last_run:
                # Handle both datetime and Firestore Timestamp
                if hasattr(last_run, 'timestamp'):
                    last_run_dt = datetime.fromtimestamp(last_run.timestamp(), tz=ET)
                else:
                    last_run_dt = last_run.replace(tzinfo=ET) if last_run.tzinfo is None else last_run.astimezone(ET)

                if last_run_dt >= today_midnight:
                    # Already ran today
                    return

        # Need to run aggregation - try to acquire lock
        if not _aggregation_lock.acquire(blocking=False):
            # Another thread is handling it
            return

        try:
            _aggregation_in_progress = True

            # Update status immediately to prevent other requests from triggering
            status_ref.set({
                'last_run': datetime.now(ET),
                'status': 'in_progress',
                'triggered_at': datetime.now(ET)
            }, merge=True)

            # Start background aggregation
            thread = threading.Thread(
                target=_run_aggregation_job,
                args=(status_ref,),
                daemon=True
            )
            thread.start()
            logger.info("Analytics aggregation triggered by first visitor of the day")

        finally:
            _aggregation_lock.release()

    except Exception as e:
        logger.error(f"Error checking analytics aggregation status: {e}")


def _run_aggregation_job(status_ref):
    """
    Background job that performs the actual aggregation.

    Queries Firebase Analytics events from the previous day,
    computes summary metrics, and stores in BigQuery.
    """
    global _aggregation_in_progress

    try:
        logger.info("Starting daily analytics aggregation...")

        # Get yesterday's date range (ET)
        now_et = datetime.now(ET)
        yesterday = now_et - timedelta(days=1)
        start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Aggregate metrics
        metrics = _aggregate_daily_metrics(start_of_yesterday, end_of_yesterday)

        # Store aggregated results
        _store_aggregated_metrics(yesterday.date(), metrics)

        # Update status to complete
        status_ref.set({
            'last_run': datetime.now(ET),
            'status': 'complete',
            'completed_at': datetime.now(ET),
            'metrics_date': yesterday.strftime('%Y-%m-%d'),
            'metrics_summary': {
                'total_events': metrics.get('total_events', 0),
                'unique_users': metrics.get('unique_users', 0),
                'reports_generated': metrics.get('reports_generated', 0)
            }
        }, merge=True)

        logger.info(f"Analytics aggregation complete for {yesterday.strftime('%Y-%m-%d')}")

    except Exception as e:
        logger.error(f"Error during analytics aggregation: {e}")
        try:
            status_ref.set({
                'status': 'error',
                'error': str(e),
                'error_at': datetime.now(ET)
            }, merge=True)
        except:
            pass
    finally:
        _aggregation_in_progress = False


def _aggregate_daily_metrics(start_dt: datetime, end_dt: datetime) -> dict:
    """
    Query BigQuery for events in the given date range and compute metrics.

    Returns dict with aggregated metrics.
    """
    metrics = {
        'total_events': 0,
        'unique_users': 0,
        'reports_generated': 0,
        'reports_by_app': {},
        'reports_by_state': {},
        'lenders_researched': {},
        'counties_researched': {}
    }

    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        client = get_bigquery_client()
        if not client:
            logger.warning("BigQuery client not available for aggregation")
            return metrics

        # Format dates for BigQuery
        start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')

        # Query for daily summary
        summary_query = f"""
            SELECT
                COUNT(*) as total_events,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(CASE WHEN event_name LIKE '%_report' THEN 1 END) as reports_generated
            FROM `hdma1-242116.justdata_analytics.all_events`
            WHERE event_timestamp >= TIMESTAMP('{start_str}')
              AND event_timestamp < TIMESTAMP('{end_str}')
        """

        result = client.query(summary_query).result()
        for row in result:
            metrics['total_events'] = row.total_events or 0
            metrics['unique_users'] = row.unique_users or 0
            metrics['reports_generated'] = row.reports_generated or 0
            break

        # Query for reports by app
        app_query = f"""
            SELECT
                event_name,
                COUNT(*) as count
            FROM `hdma1-242116.justdata_analytics.all_events`
            WHERE event_timestamp >= TIMESTAMP('{start_str}')
              AND event_timestamp < TIMESTAMP('{end_str}')
              AND event_name LIKE '%_report'
            GROUP BY event_name
        """

        result = client.query(app_query).result()
        for row in result:
            app_name = row.event_name.replace('_report', '')
            metrics['reports_by_app'][app_name] = row.count

        # Query for reports by state (user's state)
        state_query = f"""
            SELECT
                user_state,
                COUNT(*) as count
            FROM `hdma1-242116.justdata_analytics.all_events`
            WHERE event_timestamp >= TIMESTAMP('{start_str}')
              AND event_timestamp < TIMESTAMP('{end_str}')
              AND event_name LIKE '%_report'
              AND user_state IS NOT NULL
            GROUP BY user_state
        """

        result = client.query(state_query).result()
        for row in result:
            if row.user_state:
                metrics['reports_by_state'][row.user_state] = row.count

        # Query for top lenders researched
        lender_query = f"""
            SELECT
                lender_lei,
                lender_name,
                COUNT(*) as count,
                COUNT(DISTINCT user_id) as unique_users
            FROM `hdma1-242116.justdata_analytics.all_events`
            WHERE event_timestamp >= TIMESTAMP('{start_str}')
              AND event_timestamp < TIMESTAMP('{end_str}')
              AND lender_lei IS NOT NULL
            GROUP BY lender_lei, lender_name
            ORDER BY count DESC
            LIMIT 50
        """

        result = client.query(lender_query).result()
        for row in result:
            metrics['lenders_researched'][row.lender_lei] = {
                'name': row.lender_name,
                'count': row.count,
                'unique_users': row.unique_users
            }

        # Query for top counties researched
        county_query = f"""
            SELECT
                county_fips,
                county_name,
                state_code,
                COUNT(*) as count,
                COUNT(DISTINCT user_id) as unique_users
            FROM `hdma1-242116.justdata_analytics.all_events`
            WHERE event_timestamp >= TIMESTAMP('{start_str}')
              AND event_timestamp < TIMESTAMP('{end_str}')
              AND county_fips IS NOT NULL
            GROUP BY county_fips, county_name, state_code
            ORDER BY count DESC
            LIMIT 100
        """

        result = client.query(county_query).result()
        for row in result:
            metrics['counties_researched'][row.county_fips] = {
                'name': row.county_name,
                'state': row.state_code,
                'count': row.count,
                'unique_users': row.unique_users
            }

    except Exception as e:
        logger.error(f"Error querying BigQuery for aggregation: {e}")

    return metrics


def _store_aggregated_metrics(date, metrics: dict):
    """
    Store aggregated metrics in BigQuery for historical analysis.
    """
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        import json

        client = get_bigquery_client()
        if not client:
            logger.warning("BigQuery client not available for storing metrics")
            return

        # Store in daily_aggregates table
        table_id = "hdma1-242116.justdata_analytics.daily_aggregates"

        row = {
            'date': date.isoformat(),
            'total_events': metrics.get('total_events', 0),
            'unique_users': metrics.get('unique_users', 0),
            'reports_generated': metrics.get('reports_generated', 0),
            'reports_by_app': json.dumps(metrics.get('reports_by_app', {})),
            'reports_by_state': json.dumps(metrics.get('reports_by_state', {})),
            'top_lenders': json.dumps(dict(list(metrics.get('lenders_researched', {}).items())[:20])),
            'top_counties': json.dumps(dict(list(metrics.get('counties_researched', {}).items())[:50])),
            'aggregated_at': datetime.now(ET).isoformat()
        }

        # Use MERGE to upsert (in case of re-runs)
        merge_query = f"""
            MERGE `{table_id}` T
            USING (SELECT @date as date) S
            ON T.date = S.date
            WHEN MATCHED THEN
                UPDATE SET
                    total_events = @total_events,
                    unique_users = @unique_users,
                    reports_generated = @reports_generated,
                    reports_by_app = @reports_by_app,
                    reports_by_state = @reports_by_state,
                    top_lenders = @top_lenders,
                    top_counties = @top_counties,
                    aggregated_at = @aggregated_at
            WHEN NOT MATCHED THEN
                INSERT (date, total_events, unique_users, reports_generated,
                        reports_by_app, reports_by_state, top_lenders, top_counties, aggregated_at)
                VALUES (@date, @total_events, @unique_users, @reports_generated,
                        @reports_by_app, @reports_by_state, @top_lenders, @top_counties, @aggregated_at)
        """

        from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("date", "DATE", date),
                ScalarQueryParameter("total_events", "INT64", row['total_events']),
                ScalarQueryParameter("unique_users", "INT64", row['unique_users']),
                ScalarQueryParameter("reports_generated", "INT64", row['reports_generated']),
                ScalarQueryParameter("reports_by_app", "STRING", row['reports_by_app']),
                ScalarQueryParameter("reports_by_state", "STRING", row['reports_by_state']),
                ScalarQueryParameter("top_lenders", "STRING", row['top_lenders']),
                ScalarQueryParameter("top_counties", "STRING", row['top_counties']),
                ScalarQueryParameter("aggregated_at", "STRING", row['aggregated_at']),
            ]
        )

        client.query(merge_query, job_config=job_config).result()
        logger.info(f"Stored aggregated metrics for {date}")

    except Exception as e:
        logger.error(f"Error storing aggregated metrics: {e}")
        # Also store in Firestore as backup
        try:
            from justdata.main.auth import get_firestore_client
            db = get_firestore_client()
            if db:
                db.collection('analytics_daily').document(date.isoformat()).set({
                    **metrics,
                    'aggregated_at': datetime.now(ET)
                })
                logger.info(f"Stored aggregated metrics in Firestore for {date}")
        except Exception as fe:
            logger.error(f"Error storing metrics in Firestore backup: {fe}")


def get_aggregation_status() -> dict:
    """
    Get the current aggregation status from Firestore.

    Returns dict with status info or None if not available.
    """
    try:
        from justdata.main.auth import get_firestore_client
        db = get_firestore_client()
        if not db:
            return None

        status_doc = db.collection('system').document('analytics_status').get()
        if status_doc.exists:
            return status_doc.to_dict()
        return None
    except Exception as e:
        logger.error(f"Error getting aggregation status: {e}")
        return None
