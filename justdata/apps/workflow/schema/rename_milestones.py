"""
Rename Milestones to Simpler Names.

Updates milestone titles from "All X Complete" to just the type name:
- LEGAL_COMPLETE: "All Legal Tasks Complete" -> "Legal"
- INFRA_COMPLETE: "All Infrastructure Complete" -> "Infrastructure"
- FEATURE_COMPLETE: "All Features Complete" -> "Feature"
- BUG_COMPLETE: "All Bug Fixes Complete" -> "Bug"
- STYLE_COMPLETE: "All Styling Complete" -> "Styling"
- CONTENT_COMPLETE: "All Content Complete" -> "Content"

Run from JustData directory:
    python -m justdata.apps.workflow.schema.rename_milestones
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

# Milestone renames: id -> new_title
MILESTONE_RENAMES = {
    'LEGAL_COMPLETE': 'Legal',
    'INFRA_COMPLETE': 'Infrastructure',
    'FEATURE_COMPLETE': 'Feature',
    'BUG_COMPLETE': 'Bug',
    'STYLE_COMPLETE': 'Styling',
    'CONTENT_COMPLETE': 'Content',
}


def get_monday_api_key():
    """Get Monday.com API key from environment."""
    key = os.environ.get('MONDAY_API_KEY') or os.environ.get('MONDAY_API_TOKEN')
    return key


def update_monday_item_name(item_id: str, new_name: str):
    """Update a Monday item's name."""
    key = get_monday_api_key()
    if not key:
        return False

    headers = {
        "Authorization": key,
        "Content-Type": "application/json",
    }

    mutation = """
    mutation ($boardId: ID!, $itemId: ID!, $columnValues: JSON!) {
        change_multiple_column_values(
            board_id: $boardId,
            item_id: $itemId,
            column_values: $columnValues
        ) {
            id
            name
        }
    }
    """

    # Update the item name via the name column
    # Note: Monday.com uses 'name' column for item name
    payload = {
        "query": """
        mutation ($itemId: ID!, $newName: String!) {
            change_simple_column_value(
                item_id: $itemId,
                board_id: "18397384545",
                column_id: "name",
                value: $newName
            ) {
                id
                name
            }
        }
        """,
        "variables": {
            "itemId": str(item_id),
            "newName": new_name
        }
    }

    response = requests.post("https://api.monday.com/v2", json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print(f"    Monday API error: {data['errors']}")
            return False
        return True
    return False


def rename_milestones():
    """Rename milestones in BigQuery and Monday.com."""
    print("=" * 60)
    print("RENAME MILESTONES")
    print("=" * 60)

    client = get_bigquery_client(PROJECT_ID)
    now = datetime.utcnow().isoformat()

    renamed_bq = 0
    renamed_monday = 0
    errors = 0

    for milestone_id, new_title in MILESTONE_RENAMES.items():
        print(f"\n{milestone_id} -> {new_title}")

        # Check if milestone exists in BigQuery
        check_sql = f"""
        SELECT id, title, monday_item_id
        FROM `{TASKS_TABLE}`
        WHERE id = '{milestone_id}'
        """

        try:
            results = list(client.query(check_sql).result())

            if not results:
                print(f"  [SKIP] Not found in BigQuery")
                continue

            row = results[0]
            current_title = row.title
            monday_item_id = getattr(row, 'monday_item_id', None)

            if current_title == new_title:
                print(f"  [SKIP] Already named '{new_title}'")
                continue

            # Update in BigQuery
            update_sql = f"""
            UPDATE `{TASKS_TABLE}`
            SET title = '{new_title}',
                updated_at = TIMESTAMP('{now}')
            WHERE id = '{milestone_id}'
            """

            client.query(update_sql).result()
            print(f"  [OK] BigQuery: '{current_title}' -> '{new_title}'")
            renamed_bq += 1

            # Update in Monday.com if linked
            if monday_item_id:
                if update_monday_item_name(monday_item_id, new_title):
                    print(f"  [OK] Monday #{monday_item_id}: renamed")
                    renamed_monday += 1
                else:
                    print(f"  [WARN] Monday #{monday_item_id}: could not rename")

        except Exception as e:
            print(f"  [ERROR] {e}")
            errors += 1

    print()
    print("=" * 60)
    print(f"COMPLETE: {renamed_bq} BigQuery, {renamed_monday} Monday, {errors} errors")
    print("=" * 60)


if __name__ == '__main__':
    rename_milestones()
