"""
Workflow Update Script - January 26, 2026
Updates based on master to-do list reconciliation.

Changes:
1. Mark 6 items as COMPLETED
2. Merge I2 + I3 into single task
3. Add 6 NEW items
4. Update dependencies to match master list

Usage: python -m justdata.apps.workflow.schema.update_2026_01_26
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from justdata.shared.utils.unified_env import ensure_unified_env_loaded
from justdata.shared.utils.bigquery_client import get_bigquery_client

# Ensure environment is loaded
ensure_unified_env_loaded()

PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')
DATASET = 'justdata'
TASKS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_tasks'
POSITIONS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_positions'

# Canvas dimensions
CANVAS_WIDTH = 1100
CANVAS_HEIGHT = 750


def get_client():
    """Get BigQuery client."""
    client = get_bigquery_client(PROJECT_ID)
    if not client:
        raise Exception("Failed to connect to BigQuery")
    return client


def mark_tasks_completed(client, task_ids):
    """Mark multiple tasks as completed."""
    now = datetime.utcnow().isoformat()

    for task_id in task_ids:
        sql = f"""
        UPDATE `{TASKS_TABLE}`
        SET status = 'done',
            completed_at = TIMESTAMP('{now}'),
            completed_by = 'update_script_2026_01_26',
            updated_at = TIMESTAMP('{now}')
        WHERE id = '{task_id}'
        """
        try:
            client.query(sql).result()
            print(f"  [OK] Marked {task_id} as completed")
        except Exception as e:
            print(f"  [ERROR] Failed to mark {task_id}: {e}")


def merge_tasks(client, task_ids_to_delete, new_task):
    """Delete old tasks and create a merged task."""
    now = datetime.utcnow()

    # Delete old tasks
    for task_id in task_ids_to_delete:
        try:
            client.query(f"DELETE FROM `{TASKS_TABLE}` WHERE id = '{task_id}'").result()
            client.query(f"DELETE FROM `{POSITIONS_TABLE}` WHERE task_id = '{task_id}'").result()
            print(f"  [OK] Deleted {task_id}")
        except Exception as e:
            print(f"  [ERROR] Failed to delete {task_id}: {e}")

    # Create merged task
    task_row = {
        'id': new_task['id'],
        'title': new_task['title'],
        'type': new_task['type'],
        'priority': new_task['priority'],
        'status': 'open',
        'app': new_task.get('app', ''),
        'notes': new_task.get('notes', ''),
        'dependencies': new_task.get('dependencies', []),
        'is_collector': False,
        'is_goal': False,
        'collector_for': None,
        'created_at': now.isoformat(),
        'updated_at': now.isoformat(),
        'created_by': 'update_script_2026_01_26',
        'completed_at': None,
        'completed_by': None,
    }

    try:
        errors = client.insert_rows_json(TASKS_TABLE, [task_row])
        if errors:
            print(f"  [ERROR] Failed to create merged task: {errors}")
        else:
            # Add position
            position_row = {
                'task_id': new_task['id'],
                'x': new_task.get('x', CANVAS_WIDTH * 0.5),
                'y': new_task.get('y', CANVAS_HEIGHT * 0.1),
                'updated_at': now.isoformat(),
                'updated_by': 'update_script_2026_01_26',
            }
            client.insert_rows_json(POSITIONS_TABLE, [position_row])
            print(f"  [OK] Created merged task {new_task['id']}: {new_task['title']}")
    except Exception as e:
        print(f"  [ERROR] Failed to create merged task: {e}")


def add_new_tasks(client, tasks):
    """Add new tasks to the workflow."""
    now = datetime.utcnow()

    for task in tasks:
        task_row = {
            'id': task['id'],
            'title': task['title'],
            'type': task['type'],
            'priority': task['priority'],
            'status': 'open',
            'app': task.get('app', ''),
            'notes': task.get('notes', ''),
            'dependencies': task.get('dependencies', []),
            'is_collector': False,
            'is_goal': False,
            'collector_for': None,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'created_by': 'update_script_2026_01_26',
            'completed_at': None,
            'completed_by': None,
        }

        try:
            errors = client.insert_rows_json(TASKS_TABLE, [task_row])
            if errors:
                print(f"  [ERROR] Failed to create {task['id']}: {errors}")
            else:
                # Add position
                position_row = {
                    'task_id': task['id'],
                    'x': task.get('x', CANVAS_WIDTH * 0.5),
                    'y': task.get('y', CANVAS_HEIGHT * 0.5),
                    'updated_at': now.isoformat(),
                    'updated_by': 'update_script_2026_01_26',
                }
                client.insert_rows_json(POSITIONS_TABLE, [position_row])
                print(f"  [OK] Added {task['id']}: {task['title']}")
        except Exception as e:
            print(f"  [ERROR] Failed to create {task['id']}: {e}")


def update_task_dependencies(client, task_id, dependencies):
    """Update dependencies for a task."""
    now = datetime.utcnow().isoformat()
    deps_str = ', '.join([f'"{d}"' for d in dependencies])

    sql = f"""
    UPDATE `{TASKS_TABLE}`
    SET dependencies = [{deps_str}],
        updated_at = TIMESTAMP('{now}')
    WHERE id = '{task_id}'
    """

    try:
        client.query(sql).result()
        print(f"  [OK] Updated dependencies for {task_id}")
    except Exception as e:
        print(f"  [ERROR] Failed to update {task_id}: {e}")


def update_task_field(client, task_id, field, value):
    """Update a single field for a task."""
    now = datetime.utcnow().isoformat()

    if isinstance(value, str):
        escaped_value = value.replace("'", "\\'").replace('"', '\\"')
        sql = f"""
        UPDATE `{TASKS_TABLE}`
        SET {field} = '{escaped_value}',
            updated_at = TIMESTAMP('{now}')
        WHERE id = '{task_id}'
        """
    else:
        sql = f"""
        UPDATE `{TASKS_TABLE}`
        SET {field} = {value},
            updated_at = TIMESTAMP('{now}')
        WHERE id = '{task_id}'
        """

    try:
        client.query(sql).result()
        print(f"  [OK] Updated {field} for {task_id}")
    except Exception as e:
        print(f"  [ERROR] Failed to update {task_id}.{field}: {e}")


def main():
    print("=" * 60)
    print("Workflow Update - January 26, 2026")
    print("=" * 60)

    client = get_client()

    # =========================================================
    # 1. MARK COMPLETED ITEMS
    # =========================================================
    print("\n[1/4] Marking completed items...")

    completed_tasks = [
        'C5',   # Hamburger menu navigation links
        'I1',   # Add CENSUS_API_KEY to Cloud Run
        'C21',  # Lender search takes too long
        'C22',  # Bank Branch Analysis browser tab title
        'C23',  # BranchMapper missing footer
        'S6',   # Deploy interactive project map
    ]

    mark_tasks_completed(client, completed_tasks)

    # =========================================================
    # 2. MERGE I2 + I3
    # =========================================================
    print("\n[2/4] Merging I2 + I3...")

    merged_task = {
        'id': 'I2',  # Reuse I2 ID
        'title': 'Enable Cloud Run Admin API and grant BigQuery Data Viewer permission',
        'type': 'infrastructure',
        'priority': 'high',
        'app': '',
        'notes': 'Combined infrastructure setup task. Required for production deployment.',
        'dependencies': [],
        'x': CANVAS_WIDTH * 0.5,
        'y': CANVAS_HEIGHT * 0.08,
    }

    merge_tasks(client, ['I2', 'I3'], merged_task)

    # =========================================================
    # 3. ADD NEW ITEMS
    # =========================================================
    print("\n[3/4] Adding new items...")

    new_tasks = [
        {
            'id': 'C25',
            'title': 'Small Business Lending card redesign - remove $170.4M header, elevate LMI metrics',
            'type': 'styling',
            'priority': 'medium',
            'app': 'MergerMeter',
            'notes': 'Remove $170.4M total header, elevate LMI Census Tracts and Businesses <$1M Rev to primary display matching Mortgage Lending card styling',
            'dependencies': [],
            'x': CANVAS_WIDTH * 0.45,
            'y': CANVAS_HEIGHT * 0.92,
        },
        {
            'id': 'C26',
            'title': 'Fix report page footer to match LendSight and standardized formats',
            'type': 'styling',
            'priority': 'medium',
            'app': 'MergerMeter',
            'notes': 'MergerMeter report footer needs to match the standard footer used in LendSight and other apps',
            'dependencies': [],
            'x': CANVAS_WIDTH * 0.55,
            'y': CANVAS_HEIGHT * 0.92,
        },
        {
            'id': 'S15',
            'title': 'BranchMapper national footprint analysis feature',
            'type': 'feature',
            'priority': 'medium',
            'app': 'BranchMapper',
            'notes': 'Add capability to analyze national branch footprint',
            'dependencies': ['C7'],  # Depends on census layers fix
            'x': CANVAS_WIDTH * 0.92,
            'y': CANVAS_HEIGHT * 0.35,
        },
        {
            'id': 'I6',
            'title': 'Set up separate service accounts per application',
            'type': 'infrastructure',
            'priority': 'medium',
            'app': '',
            'notes': 'Infrastructure improvement for better security isolation',
            'dependencies': [],
            'x': CANVAS_WIDTH * 0.4,
            'y': CANVAS_HEIGHT * 0.08,
        },
        {
            'id': 'I7',
            'title': 'Stripe integration for paid tiers',
            'type': 'infrastructure',
            'priority': 'low',
            'app': '',
            'notes': 'Future: Payment processing for premium features',
            'dependencies': ['S4'],  # After early access launch
            'x': CANVAS_WIDTH * 0.6,
            'y': CANVAS_HEIGHT * 0.08,
        },
        {
            'id': 'I8',
            'title': 'HubSpot sync for membership tracking',
            'type': 'infrastructure',
            'priority': 'low',
            'app': '',
            'notes': 'Future: Sync user data with HubSpot CRM',
            'dependencies': ['I7'],  # After Stripe
            'x': CANVAS_WIDTH * 0.7,
            'y': CANVAS_HEIGHT * 0.08,
        },
    ]

    add_new_tasks(client, new_tasks)

    # =========================================================
    # 4. UPDATE DEPENDENCIES
    # =========================================================
    print("\n[4/4] Updating dependencies...")

    # Key dependency updates based on master list
    dependency_updates = {
        # Legal chain
        'S3': ['S1', 'S2'],  # Legal clearance depends on disclaimer + copyright
        'C13': ['S1', 'S3'],  # Disclaimer placement depends on disclaimer language + legal clearance

        # Early access launch dependencies
        'S4': ['S3'],  # Early access depends on legal clearance

        # Infrastructure chain
        'I4': ['S3', 'C1', 'C2', 'S5', 'I2'],  # Deploy depends on legal + key fixes + infra

        # Analytics chain
        'C1': ['I5'],  # Analytics dashboard depends on Firebase export
        'C19': ['C1'],  # Lender Interest map depends on Analytics dashboard

        # Content chain
        'S7': ['S4'],  # Videos depend on early access launch
        'S9': ['S4'],  # User testing depends on early access
        'S10': ['C14'],  # Tooltip content depends on guided tours
        'S11': ['S4'],  # Feature sheets depend on early access
        'S12': ['S4'],  # Launch announcement depends on early access
        'S13': ['S4', 'S7'],  # Training depends on early access + videos
        'S14': ['S9'],  # FAQ depends on user testing

        # Feature dependencies
        'S17': ['C1', 'I4'],  # Cross-app linking depends on analytics + deploy

        # BranchMapper chain
        'S15': ['C7'],  # National footprint depends on census layers fix

        # Update GOAL dependencies
        'GOAL': ['S4', 'I4', 'S9', 'BUG_COMPLETE', 'STYLE_COMPLETE', 'CONTENT_COMPLETE'],
    }

    for task_id, deps in dependency_updates.items():
        update_task_dependencies(client, task_id, deps)

    # =========================================================
    # 5. REFRESH COLLECTORS
    # =========================================================
    print("\n[5/5] Refreshing collector dependencies...")

    # Get all open bug tasks
    bug_sql = f"""
    SELECT id FROM `{TASKS_TABLE}`
    WHERE type = 'bug' AND status = 'open' AND is_collector = FALSE AND is_goal = FALSE
    """
    bug_ids = [row.id for row in client.query(bug_sql).result()]
    update_task_dependencies(client, 'BUG_COMPLETE', bug_ids)

    # Get all open styling tasks
    style_sql = f"""
    SELECT id FROM `{TASKS_TABLE}`
    WHERE type = 'styling' AND status = 'open' AND is_collector = FALSE AND is_goal = FALSE
    """
    style_ids = [row.id for row in client.query(style_sql).result()]
    update_task_dependencies(client, 'STYLE_COMPLETE', style_ids)

    # Get all open content tasks
    content_sql = f"""
    SELECT id FROM `{TASKS_TABLE}`
    WHERE type = 'content' AND status = 'open' AND is_collector = FALSE AND is_goal = FALSE
    """
    content_ids = [row.id for row in client.query(content_sql).result()]
    update_task_dependencies(client, 'CONTENT_COMPLETE', content_ids)

    print(f"  [OK] BUG_COMPLETE now has {len(bug_ids)} dependencies")
    print(f"  [OK] STYLE_COMPLETE now has {len(style_ids)} dependencies")
    print(f"  [OK] CONTENT_COMPLETE now has {len(content_ids)} dependencies")

    # =========================================================
    # SUMMARY
    # =========================================================
    print("\n" + "=" * 60)
    print("Update Complete!")
    print("=" * 60)
    print(f"  - Marked {len(completed_tasks)} tasks as completed")
    print(f"  - Merged I2 + I3 into single task")
    print(f"  - Added {len(new_tasks)} new tasks")
    print(f"  - Updated {len(dependency_updates)} task dependencies")
    print(f"  - Refreshed 3 collector dependencies")
    print("\nView changes at: https://justdata-test-892833260112.us-east1.run.app/workflow/")


if __name__ == '__main__':
    main()
