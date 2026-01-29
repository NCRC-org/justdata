"""
BigQuery utility functions for JustData Slack bot.
"""

import os
import logging
from datetime import datetime
from google.cloud import bigquery

logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
SOURCE_PROJECT = 'hdma1-242116'

# Global client cache
_client = None


def get_client() -> bigquery.Client:
    """Get or create BigQuery client."""
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT_ID)
    return _client


def get_table_info(client: bigquery.Client, table_id: str) -> dict:
    """Get information about a table."""
    try:
        table = client.get_table(table_id)
        return {
            'num_rows': table.num_rows,
            'size_bytes': table.num_bytes,
            'size_mb': table.num_bytes / (1024 * 1024) if table.num_bytes else 0,
            'created': table.created.strftime('%Y-%m-%d %H:%M') if table.created else None,
            'modified': table.modified.strftime('%Y-%m-%d %H:%M') if table.modified else None,
        }
    except Exception as e:
        logger.error(f"Error getting table info for {table_id}: {e}")
        return None


def get_sync_history(client: bigquery.Client, limit: int = 10) -> list:
    """Get recent sync history from logs."""
    # In a real implementation, this would query a sync_history table
    # For now, return placeholder data
    return []


def refresh_table(client: bigquery.Client, source_table: str) -> dict:
    """Refresh a table from its source."""
    from scripts.sync.table_sync_function import refresh_table as do_refresh
    return do_refresh(source_table, client)


def execute_query(client: bigquery.Client, query: str) -> list:
    """Execute a query and return results."""
    try:
        job = client.query(query)
        return list(job.result())
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise
