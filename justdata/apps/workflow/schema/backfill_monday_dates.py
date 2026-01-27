"""
Backfill Migration: Populate Created Date and Completed Date on Monday items.

This script updates existing Monday.com items with:
1. Created Date - from BigQuery created_at timestamp
2. Completed Date - from BigQuery completed_at timestamp (if status is done)

Run from JustData directory:
    python -m justdata.apps.workflow.schema.backfill_monday_dates
"""
import os
import sys
from datetime import datetime

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from justdata.shared.utils.bigquery_client import get_bigquery_client


# Configuration
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')
DATASET = 'justdata'
TASKS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_tasks'


def get_monday_api_key():
    """Get Monday.com API key from environment."""
    key = os.environ.get('MONDAY_API_KEY') or os.environ.get('MONDAY_API_TOKEN')
    if not key:
        raise ValueError("MONDAY_API_KEY or MONDAY_API_TOKEN environment variable not set")
    return key


def update_monday_item_dates(item_id: str, created_date: str, completed_date: str = None):
    """Update a Monday item's date columns."""
    import json
    import requests

    headers = {
        "Authorization": get_monday_api_key(),
        "Content-Type": "application/json",
    }

    # Column IDs for dates
    CREATED_DATE_COL = 'date_mm001ej7'
    COMPLETED_DATE_COL = 'date_mm00exyd'

    column_values = {}

    if created_date:
        column_values[CREATED_DATE_COL] = {"date": created_date}

    if completed_date:
        column_values[COMPLETED_DATE_COL] = {"date": completed_date}

    if not column_values:
        return True

    mutation = """
    mutation ($boardId: ID!, $itemId: ID!, $columnValues: JSON!) {
        change_multiple_column_values(
            board_id: $boardId,
            item_id: $itemId,
            column_values: $columnValues
        ) {
            id
        }
    }
    """

    payload = {
        "query": mutation,
        "variables": {
            "boardId": "18397384545",
            "itemId": str(item_id),
            "columnValues": json.dumps(column_values)
        }
    }

    response = requests.post("https://api.monday.com/v2", json=payload, headers=headers)
    response.raise_for_status()

    data = response.json()
    if "errors" in data:
        print(f"  Error updating {item_id}: {data['errors']}")
        return False

    return True


def backfill_dates():
    """Backfill Created Date and Completed Date for all Monday-linked tasks."""
    print("=" * 60)
    print("BACKFILL MONDAY DATES")
    print("=" * 60)

    client = get_bigquery_client(PROJECT_ID)

    # Get all tasks with Monday item IDs
    sql = f"""
    SELECT id, monday_item_id, created_at, completed_at, status
    FROM `{TASKS_TABLE}`
    WHERE monday_item_id IS NOT NULL AND monday_item_id != ''
    ORDER BY id
    """

    results = list(client.query(sql).result())
    print(f"Found {len(results)} tasks with Monday item IDs")
    print()

    updated = 0
    errors = 0

    for row in results:
        task_id = row.id
        monday_id = row.monday_item_id
        created_at = row.created_at
        completed_at = row.completed_at
        status = row.status

        # Format dates for Monday (YYYY-MM-DD)
        created_date = None
        completed_date = None

        if created_at:
            if hasattr(created_at, 'strftime'):
                created_date = created_at.strftime('%Y-%m-%d')
            elif isinstance(created_at, str):
                # Parse ISO format
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_date = dt.strftime('%Y-%m-%d')
                except:
                    pass

        if completed_at and status == 'done':
            if hasattr(completed_at, 'strftime'):
                completed_date = completed_at.strftime('%Y-%m-%d')
            elif isinstance(completed_at, str):
                try:
                    dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                    completed_date = dt.strftime('%Y-%m-%d')
                except:
                    pass

        if created_date or completed_date:
            print(f"  {task_id} (Monday #{monday_id}): created={created_date}, completed={completed_date}")

            try:
                if update_monday_item_dates(monday_id, created_date, completed_date):
                    updated += 1
                else:
                    errors += 1
            except Exception as e:
                print(f"    Error: {e}")
                errors += 1

    print()
    print("=" * 60)
    print(f"COMPLETE: {updated} updated, {errors} errors")
    print("=" * 60)


if __name__ == '__main__':
    backfill_dates()
