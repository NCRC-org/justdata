"""
Cloud Function for per-table sync from hdma1 to justdata-ncrc.

This function is triggered by Pub/Sub messages when source tables are modified.
It refreshes the corresponding destination table and sends Slack notifications.
"""

import os
import json
import logging
from datetime import datetime
from google.cloud import bigquery
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SOURCE_PROJECT = 'hdma1-242116'
DEST_PROJECT = 'justdata-ncrc'
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', '#justdata-alerts')

# Table sync mapping: source_table -> (dest_table, sync_type, dependencies)
TABLE_MAPPING = {
    'sb.lenders': ('bizsight.sb_lenders', 'full_copy', []),
    'sb.disclosure': ('bizsight.sb_county_summary', 'aggregated', []),
    'hmda.lenders18': ('lendsight.lenders18', 'full_copy', ['shared.de_hmda']),
    'hmda.lender_names_gleif': ('shared.lender_names_gleif', 'full_copy', []),
    'hmda.hmda': ('shared.de_hmda', 'derived', ['lendsight.de_hmda_county_summary', 'lendsight.de_hmda_tract_summary']),
    'branches.sod': ('branchsight.sod', 'full_copy', ['branchsight.branch_hhi_summary']),
    'credit_unions.cu_branches': ('lenderprofile.cu_branches', 'full_copy', []),
    'credit_unions.cu_call_reports': ('lenderprofile.cu_call_reports', 'full_copy', []),
}

# SQL templates for different sync types
SYNC_SQL = {
    'full_copy': """
        CREATE OR REPLACE TABLE `{dest_project}.{dest_table}` AS
        SELECT * FROM `{source_project}.{source_table}`
    """,
    'sb_county_summary': """
        CREATE OR REPLACE TABLE `{dest_project}.bizsight.sb_county_summary` AS
        SELECT
            CAST(d.year AS INT64) as year,
            d.geoid5,
            d.respondent_id,
            COALESCE(l.sb_lender, 'Unknown') as lender_name,
            SUM(d.num_under_100k) as num_under_100k,
            SUM(d.num_100k_250k) as num_100k_250k,
            SUM(d.num_250k_1m) as num_250k_1m,
            SUM(d.num_under_100k + d.num_100k_250k + d.num_250k_1m) as total_loans,
            SUM(d.amt_under_100k) as amt_under_100k,
            SUM(d.amt_100k_250k) as amt_100k_250k,
            SUM(d.amt_250k_1m) as amt_250k_1m,
            SUM(d.numsbrev_under_1m) as numsbrev_under_1m,
            SUM(d.amtsbrev_under_1m) as amtsbrev_under_1m,
            SUM(CASE WHEN d.income_group_total IN ('1', '2') THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as lmi_tract_loans,
            SUM(CASE WHEN d.income_group_total = '1' THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as low_income_loans,
            SUM(CASE WHEN d.income_group_total = '2' THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as moderate_income_loans,
            SUM(CASE WHEN d.income_group_total IN ('3', '4') THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as midu_income_loans,
            SUM(CASE WHEN d.income_group_total IN ('1', '2') THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as lmi_tract_amount,
            SUM(CASE WHEN d.income_group_total = '1' THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as low_income_amount,
            SUM(CASE WHEN d.income_group_total = '2' THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as moderate_income_amount,
            SUM(CASE WHEN d.income_group_total IN ('3', '4') THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as midu_income_amount
        FROM `{source_project}.sb.disclosure` d
        LEFT JOIN `{source_project}.sb.lenders` l 
            ON d.respondent_id = l.sb_resid AND d.year = l.sb_year
        WHERE d.geoid5 IS NOT NULL
        GROUP BY d.year, d.geoid5, d.respondent_id, l.sb_lender
    """,
    'de_hmda': """
        CREATE OR REPLACE TABLE `{dest_project}.shared.de_hmda` AS
        SELECT * FROM `{source_project}.justdata.de_hmda`
    """,
    'branch_hhi_summary': """
        CREATE OR REPLACE TABLE `{dest_project}.branchsight.branch_hhi_summary`
        CLUSTER BY year, geoid5 AS
        SELECT
            CAST(year AS INT64) as year,
            geoid5,
            rssd,
            bank_name,
            COUNT(*) as branch_count,
            SUM(CAST(deposits_000s AS FLOAT64) * 1000) as total_deposits,
            COUNTIF(br_lmi = 1) as lmict_branches,
            COUNTIF(br_minority = 1) as mmct_branches,
            MIN(CAST(deposits_000s AS FLOAT64) * 1000) as min_branch_deposits,
            MAX(CAST(deposits_000s AS FLOAT64) * 1000) as max_branch_deposits,
            AVG(CAST(deposits_000s AS FLOAT64) * 1000) as avg_branch_deposits
        FROM `{dest_project}.branchsight.sod`
        WHERE geoid5 IS NOT NULL
        GROUP BY year, geoid5, rssd, bank_name
    """,
    # LendSight summary rollups. Schema/logic kept in lockstep with the canonical
    # builders scripts/migration/05_create_hmda_county_summary.sql and
    # 06_create_hmda_tract_summary.sql (NOT 24, which is stale and does not match the
    # live tables). Originations only (LendSight scope); partitioned + clustered to
    # match the deployed tables so refresh_dependent_table's DROP+CREATE preserves spec.
    'de_hmda_county_summary': """
        CREATE OR REPLACE TABLE `{dest_project}.lendsight.de_hmda_county_summary`
        PARTITION BY RANGE_BUCKET(year, GENERATE_ARRAY(2018, 2030, 1))
        CLUSTER BY geoid5, lei AS
        SELECT
            lei,
            activity_year as year,
            LPAD(CAST(geoid5 AS STRING), 5, '0') as geoid5,
            county_state,
            loan_purpose,
            MAX(lender_name) as lender_name,
            COUNT(*) as total_originations,
            COUNTIF(is_hispanic) as hispanic_originations,
            COUNTIF(is_black) as black_originations,
            COUNTIF(is_asian) as asian_originations,
            COUNTIF(is_white) as white_originations,
            COUNTIF(is_native_american) as native_american_originations,
            COUNTIF(is_hopi) as hopi_originations,
            COUNTIF(is_multi_racial) as multi_racial_originations,
            COUNTIF(is_lmib) as lmib_originations,
            COUNTIF(is_low_income_borrower) as low_income_borrower_originations,
            COUNTIF(is_moderate_income_borrower) as moderate_income_borrower_originations,
            COUNTIF(is_middle_income_borrower) as middle_income_borrower_originations,
            COUNTIF(is_upper_income_borrower) as upper_income_borrower_originations,
            COUNTIF(is_lmict) as lmict_originations,
            COUNTIF(is_mmct) as mmct_originations,
            SUM(loan_amount) as total_loan_amount,
            AVG(loan_amount) as avg_loan_amount,
            AVG(SAFE_CAST(property_value AS FLOAT64)) as avg_property_value,
            AVG(SAFE_CAST(interest_rate AS FLOAT64)) as avg_interest_rate,
            AVG(SAFE_CAST(total_loan_costs AS FLOAT64)) as avg_total_loan_costs,
            AVG(SAFE_CAST(origination_charges AS FLOAT64)) as avg_origination_charges,
            COUNTIF(has_demographic_data) as loans_with_demographic_data
        FROM `{dest_project}.shared.de_hmda`
        WHERE action_taken = '1' AND occupancy_type = '1' AND total_units IN ('1','2','3','4')
          AND construction_method = '1' AND (reverse_mortgage IS NULL OR reverse_mortgage != '1')
        GROUP BY lei, activity_year, geoid5, county_state, loan_purpose
    """,
    'de_hmda_tract_summary': """
        CREATE OR REPLACE TABLE `{dest_project}.lendsight.de_hmda_tract_summary`
        PARTITION BY RANGE_BUCKET(year, GENERATE_ARRAY(2018, 2030, 1))
        CLUSTER BY geoid5, lei AS
        SELECT
            lei,
            activity_year as year,
            LPAD(CAST(geoid5 AS STRING), 5, '0') as geoid5,
            county_state,
            tract_code,
            tract_minority_population_percent,
            tract_to_msa_income_percentage,
            loan_purpose,
            MAX(lender_name) as lender_name,
            COUNT(*) as total_originations,
            COUNTIF(is_hispanic) as hispanic_originations,
            COUNTIF(is_black) as black_originations,
            COUNTIF(is_asian) as asian_originations,
            COUNTIF(is_white) as white_originations,
            COUNTIF(is_lmict) as lmict_originations,
            COUNTIF(is_low_income_tract) as low_income_tract_originations,
            COUNTIF(is_moderate_income_tract) as moderate_income_tract_originations,
            COUNTIF(is_middle_income_tract) as middle_income_tract_originations,
            COUNTIF(is_upper_income_tract) as upper_income_tract_originations,
            COUNTIF(is_mmct) as mmct_originations,
            SUM(loan_amount) as total_loan_amount
        FROM `{dest_project}.shared.de_hmda`
        WHERE action_taken = '1' AND occupancy_type = '1' AND total_units IN ('1','2','3','4')
          AND construction_method = '1' AND (reverse_mortgage IS NULL OR reverse_mortgage != '1')
        GROUP BY lei, activity_year, geoid5, county_state, tract_code,
            tract_minority_population_percent, tract_to_msa_income_percentage, loan_purpose
    """,
}


def send_slack_notification(message: str, status: str = 'info'):
    """Send a notification to Slack."""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured, skipping notification")
        return
    
    emoji = {
        'info': ':information_source:',
        'success': ':white_check_mark:',
        'error': ':x:',
        'warning': ':warning:',
        'started': ':arrows_counterclockwise:'
    }.get(status, ':information_source:')
    
    payload = {
        'channel': SLACK_CHANNEL,
        'text': f"{emoji} {message}",
        'username': 'JustData Sync Bot',
        'icon_emoji': ':robot_face:'
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")


def refresh_table(source_table: str, client: bigquery.Client) -> dict:
    """Refresh a destination table from its source."""
    if source_table not in TABLE_MAPPING:
        return {'error': f'Unknown source table: {source_table}'}
    
    dest_table, sync_type, dependencies = TABLE_MAPPING[source_table]
    start_time = datetime.now()
    
    # Send start notification
    send_slack_notification(
        f"[SYNC STARTED] Refreshing `{dest_table}` from `{source_table}`",
        'started'
    )
    
    try:
        # Determine SQL template
        if sync_type == 'full_copy':
            sql = SYNC_SQL['full_copy'].format(
                dest_project=DEST_PROJECT,
                dest_table=dest_table,
                source_project=SOURCE_PROJECT,
                source_table=source_table
            )
        elif source_table == 'sb.disclosure':
            sql = SYNC_SQL['sb_county_summary'].format(
                dest_project=DEST_PROJECT,
                source_project=SOURCE_PROJECT
            )
        elif source_table == 'hmda.hmda':
            sql = SYNC_SQL['de_hmda'].format(
                dest_project=DEST_PROJECT,
                source_project=SOURCE_PROJECT
            )
        else:
            sql = SYNC_SQL['full_copy'].format(
                dest_project=DEST_PROJECT,
                dest_table=dest_table,
                source_project=SOURCE_PROJECT,
                source_table=source_table
            )
        
        # Execute sync
        job = client.query(sql)
        job.result()

        # Get row count
        count_sql = f"SELECT COUNT(*) as cnt FROM `{DEST_PROJECT}.{dest_table}`"
        count_result = list(client.query(count_sql).result())[0]
        row_count = count_result.cnt
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Send success notification
        send_slack_notification(
            f"[SYNC COMPLETE] `{dest_table}` refreshed in {duration:.1f}s ({row_count:,} rows)",
            'success'
        )
        
        # Refresh dependencies
        for dep_table in dependencies:
            logger.info(f"Refreshing dependent table: {dep_table}")
            refresh_dependent_table(dep_table, client)
        
        return {
            'status': 'success',
            'dest_table': dest_table,
            'row_count': row_count,
            'duration_seconds': duration,
            'dependencies_refreshed': dependencies
        }
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)
        
        # Send error notification
        send_slack_notification(
            f"[SYNC FAILED] `{dest_table}` failed after {duration:.1f}s: {error_msg[:200]}",
            'error'
        )
        
        logger.error(f"Sync failed for {source_table}: {e}")
        return {
            'status': 'error',
            'dest_table': dest_table,
            'error': error_msg,
            'duration_seconds': duration
        }


def refresh_dependent_table(table: str, client: bigquery.Client):
    """Refresh a dependent table (e.g., summary tables)."""
    try:
        if table == 'branchsight.branch_hhi_summary':
            sql = SYNC_SQL['branch_hhi_summary'].format(dest_project=DEST_PROJECT)
            # Drop first to avoid clustering conflict
            client.query(f"DROP TABLE IF EXISTS `{DEST_PROJECT}.{table}`").result()
            client.query(sql).result()
            logger.info(f"Refreshed dependent table: {table}")
            send_slack_notification(f"[SYNC] Cascaded refresh of `{table}` complete", 'success')
        elif table in ('lendsight.de_hmda_county_summary', 'lendsight.de_hmda_tract_summary'):
            # Rebuild the LendSight summary rollup from the freshly-synced shared.de_hmda
            template = ('de_hmda_county_summary'
                        if table.endswith('county_summary') else 'de_hmda_tract_summary')
            sql = SYNC_SQL[template].format(dest_project=DEST_PROJECT)
            # Drop first to avoid clustering conflict on re-create
            client.query(f"DROP TABLE IF EXISTS `{DEST_PROJECT}.{table}`").result()
            client.query(sql).result()
            logger.info(f"Refreshed dependent table: {table}")
            send_slack_notification(f"[SYNC] Cascaded refresh of `{table}` complete", 'success')
    except Exception as e:
        logger.error(f"Failed to refresh dependent table {table}: {e}")
        send_slack_notification(f"[SYNC WARNING] Failed to refresh dependent `{table}`: {str(e)[:100]}", 'warning')


def main(event, context):
    """Cloud Function entry point - triggered by Pub/Sub."""
    import base64
    
    # Parse the Pub/Sub message
    if 'data' in event:
        message_data = base64.b64decode(event['data']).decode('utf-8')
        try:
            data = json.loads(message_data)
            source_table = data.get('source_table')
        except json.JSONDecodeError:
            source_table = message_data
    else:
        logger.error("No data in Pub/Sub message")
        return {'error': 'No data in message'}
    
    logger.info(f"Received sync request for: {source_table}")
    
    # Initialize BigQuery client
    client = bigquery.Client(project=DEST_PROJECT)
    
    # Refresh the table
    result = refresh_table(source_table, client)
    
    logger.info(f"Sync result: {result}")
    return result


# For local testing
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        table = sys.argv[1]
        print(f"Testing sync for: {table}")
        client = bigquery.Client(project=DEST_PROJECT)
        result = refresh_table(table, client)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python table_sync_function.py <source_table>")
        print("Example: python table_sync_function.py sb.lenders")
