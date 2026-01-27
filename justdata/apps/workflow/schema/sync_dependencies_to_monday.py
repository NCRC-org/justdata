"""
Sync Blocked By Text → Monday Dependencies Column.

This script reads the Blocked By text field for all items and creates
actual Monday dependency links in the Dependencies column.

Run from JustData directory:
    python -m justdata.apps.workflow.schema.sync_dependencies_to_monday
"""
import os
import sys
import json
import requests
from datetime import datetime

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from justdata.shared.utils.bigquery_client import get_bigquery_client


# Configuration
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')
DATASET = 'justdata'
TASKS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_tasks'
MONDAY_BOARD_ID = "18397384545"
MONDAY_API_URL = "https://api.monday.com/v2"

# Column IDs
DEPENDENCIES_COL = 'dependency_mm0082qq'
BLOCKED_BY_COL = 'text_mm006jas'


def get_monday_api_key():
    """Get Monday.com API key from environment."""
    key = os.environ.get('MONDAY_API_KEY') or os.environ.get('MONDAY_API_TOKEN')
    if not key:
        raise ValueError("MONDAY_API_KEY not set")
    return key


def monday_query(query: str, variables: dict = None) -> dict:
    """Execute a GraphQL query against Monday.com API."""
    headers = {
        "Authorization": get_monday_api_key(),
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = requests.post(MONDAY_API_URL, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        raise Exception(f"Monday API error: {data['errors']}")
    return data.get("data", {})


def get_monday_items_with_blocked_by():
    """Fetch all items with their Blocked By and current Dependencies."""
    query = """
    query ($boardId: ID!) {
        boards(ids: [$boardId]) {
            items_page(limit: 500) {
                items {
                    id
                    name
                    column_values {
                        id
                        text
                        value
                    }
                }
            }
        }
    }
    """
    data = monday_query(query, {"boardId": MONDAY_BOARD_ID})
    return data.get("boards", [{}])[0].get("items_page", {}).get("items", [])


def get_workflow_to_monday_map():
    """Get mapping of workflow IDs to Monday item IDs from BigQuery."""
    client = get_bigquery_client(PROJECT_ID)
    sql = f"""
    SELECT id, monday_item_id
    FROM `{TASKS_TABLE}`
    WHERE monday_item_id IS NOT NULL AND monday_item_id != ''
    """
    results = client.query(sql).result()
    return {row.id: row.monday_item_id for row in results}


def parse_blocked_by(blocked_by_text: str) -> list:
    """Parse comma-separated workflow IDs from Blocked By text."""
    if not blocked_by_text:
        return []
    # Handle various formats: "I5", "S1, S3", "I4,S2"
    ids = []
    for part in blocked_by_text.replace(',', ' ').split():
        part = part.strip()
        if part:
            ids.append(part)
    return ids


def update_monday_dependencies(item_id: str, dependency_item_ids: list):
    """Update Monday Dependencies column with item links."""
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

    # Monday expects item_ids as integers
    column_values = {
        DEPENDENCIES_COL: {"item_ids": [int(id) for id in dependency_item_ids]}
    }

    monday_query(mutation, {
        "boardId": MONDAY_BOARD_ID,
        "itemId": str(item_id),
        "columnValues": json.dumps(column_values)
    })


def sync_all_dependencies():
    """Sync all Blocked By text fields to Monday Dependencies column."""
    print("=" * 60)
    print("SYNC BLOCKED BY TEXT -> MONDAY DEPENDENCIES")
    print("=" * 60)

    # Get workflow ID to Monday ID mapping
    print("\nFetching workflow ID mappings from BigQuery...")
    workflow_to_monday = get_workflow_to_monday_map()
    print(f"  Found {len(workflow_to_monday)} linked items")

    # Get all Monday items
    print("\nFetching items from Monday...")
    items = get_monday_items_with_blocked_by()
    print(f"  Found {len(items)} items")

    # Build Monday item ID to workflow ID reverse map
    monday_to_workflow = {v: k for k, v in workflow_to_monday.items()}

    updated = 0
    skipped = 0
    errors = 0

    print("\nProcessing items...")
    for item in items:
        monday_id = item['id']
        item_name = item['name']

        # Get column values
        columns = {cv['id']: cv for cv in item.get('column_values', [])}

        # Get Blocked By text
        blocked_by_text = columns.get(BLOCKED_BY_COL, {}).get('text', '')

        if not blocked_by_text:
            skipped += 1
            continue

        # Parse workflow IDs from Blocked By
        blocked_by_ids = parse_blocked_by(blocked_by_text)

        if not blocked_by_ids:
            skipped += 1
            continue

        # Convert workflow IDs to Monday item IDs
        monday_dep_ids = []
        missing_ids = []
        for wf_id in blocked_by_ids:
            if wf_id in workflow_to_monday:
                monday_dep_ids.append(workflow_to_monday[wf_id])
            else:
                missing_ids.append(wf_id)

        if not monday_dep_ids:
            print(f"  {item_name}: No valid dependencies found for {blocked_by_ids}")
            skipped += 1
            continue

        # Update Monday Dependencies column
        try:
            update_monday_dependencies(monday_id, monday_dep_ids)
            print(f"  {item_name}: Linked to {len(monday_dep_ids)} dependencies")
            if missing_ids:
                print(f"    (Could not find Monday IDs for: {missing_ids})")
            updated += 1
        except Exception as e:
            print(f"  {item_name}: ERROR - {e}")
            errors += 1

    print()
    print("=" * 60)
    print(f"COMPLETE: {updated} updated, {skipped} skipped, {errors} errors")
    print("=" * 60)


if __name__ == '__main__':
    sync_all_dependencies()
