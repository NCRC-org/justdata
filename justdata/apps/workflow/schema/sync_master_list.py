"""
Workflow Sync Script - Synchronize with Master To-Do List
Reconciles the workflow visualization with the master to-do list.

Key Changes:
1. Update C1 and C2 to CRITICAL priority (they block video filming)
2. Ensure all master list items are present
3. Fix any missing dependencies
4. Mark additional completed items

Usage: python -m justdata.apps.workflow.schema.sync_master_list
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


def get_existing_task_ids(client):
    """Get all existing task IDs."""
    sql = f"SELECT id FROM `{TASKS_TABLE}`"
    result = client.query(sql).result()
    return set(row.id for row in result)


def update_task_priority(client, task_id, new_priority):
    """Update a task's priority."""
    now = datetime.utcnow().isoformat()
    sql = f"""
    UPDATE `{TASKS_TABLE}`
    SET priority = '{new_priority}',
        updated_at = TIMESTAMP('{now}')
    WHERE id = '{task_id}'
    """
    try:
        client.query(sql).result()
        print(f"  [OK] Updated {task_id} priority to {new_priority}")
    except Exception as e:
        print(f"  [ERROR] Failed to update {task_id}: {e}")


def update_task_type(client, task_id, new_type):
    """Update a task's type."""
    now = datetime.utcnow().isoformat()
    sql = f"""
    UPDATE `{TASKS_TABLE}`
    SET type = '{new_type}',
        updated_at = TIMESTAMP('{now}')
    WHERE id = '{task_id}'
    """
    try:
        client.query(sql).result()
        print(f"  [OK] Updated {task_id} type to {new_type}")
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
        print(f"  [OK] Updated {task_id}.{field}")
    except Exception as e:
        print(f"  [ERROR] Failed to update {task_id}.{field}: {e}")


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


def mark_task_completed(client, task_id):
    """Mark a task as completed."""
    now = datetime.utcnow().isoformat()
    sql = f"""
    UPDATE `{TASKS_TABLE}`
    SET status = 'done',
        completed_at = TIMESTAMP('{now}'),
        completed_by = 'sync_master_list',
        updated_at = TIMESTAMP('{now}')
    WHERE id = '{task_id}'
    """
    try:
        client.query(sql).result()
        print(f"  [OK] Marked {task_id} as completed")
    except Exception as e:
        print(f"  [ERROR] Failed to mark {task_id}: {e}")


def add_task(client, task):
    """Add a new task."""
    now = datetime.utcnow()

    task_row = {
        'id': task['id'],
        'title': task['title'],
        'type': task['type'],
        'priority': task['priority'],
        'status': task.get('status', 'open'),
        'app': task.get('app', ''),
        'notes': task.get('notes', ''),
        'dependencies': task.get('dependencies', []),
        'is_collector': False,
        'is_goal': False,
        'collector_for': None,
        'created_at': now.isoformat(),
        'updated_at': now.isoformat(),
        'created_by': 'sync_master_list',
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
                'updated_by': 'sync_master_list',
            }
            client.insert_rows_json(POSITIONS_TABLE, [position_row])
            print(f"  [OK] Added {task['id']}: {task['title']}")
    except Exception as e:
        print(f"  [ERROR] Failed to create {task['id']}: {e}")


def main():
    print("=" * 60)
    print("Workflow Sync - Master To-Do List Reconciliation")
    print("=" * 60)

    client = get_client()
    existing_ids = get_existing_task_ids(client)
    print(f"\nFound {len(existing_ids)} existing tasks")

    # =========================================================
    # 1. UPDATE C1 AND C2 TO CRITICAL PRIORITY
    # These are the 2 critical bugs blocking video filming
    # =========================================================
    print("\n[1/5] Upgrading C1 and C2 to CRITICAL priority...")

    # C1: Analytics Dashboard - blocks #21 (videos) and #29
    if 'C1' in existing_ids:
        update_task_priority(client, 'C1', 'critical')
        update_task_type(client, 'C1', 'bug')  # Reclassify as bug
        update_task_field(client, 'C1', 'notes',
            'CRITICAL: Still displaying mock data instead of real BigQuery data. '
            'Infrastructure exists with 284 backfilled events and API endpoints, but frontend not connected. '
            'BLOCKS: Video filming (#21), Lender Interest map (#29)')

    # C2: DataExplorer HUD Low-Mod - blocks #21 (videos)
    if 'C2' in existing_ids:
        update_task_priority(client, 'C2', 'critical')
        update_task_type(client, 'C2', 'bug')  # Reclassify as bug
        update_task_field(client, 'C2', 'notes',
            'CRITICAL: Area Analysis missing HUD Low-Mod population data. '
            'Section 2, Table 2.5 (Income & Neighborhood Indicators) is missing Low-to-Moderate Income population data from HUD file. '
            'BLOCKS: Video filming (#21)')

    # =========================================================
    # 2. ADD MISSING TASKS FROM MASTER LIST
    # =========================================================
    print("\n[2/5] Adding missing tasks...")

    # Tasks that might be missing based on master list
    missing_tasks = [
        # #14 - AI Narratives tone (maps to C10 which exists but may need update)
        # #15 - National trend data (maps to C11 which exists)
        # #17 - User workflow documentation (maps to C14 which exists)
        # #18 - Mobile responsiveness (maps to C15 which exists)
        # #22 - AI narrative style guide (maps to S8 which exists)
        # #23 - User testing (maps to S9 which exists)
        # #24 - Tooltip content (maps to S10 which exists)

        # Marketing items that may be missing
        {
            'id': 'S16',
            'title': 'Create one-page feature sheets for each app',
            'type': 'content',
            'priority': 'low',
            'app': '',
            'notes': 'Marketing materials for member outreach. Master list #32.',
            'dependencies': ['S4'],
            'x': CANVAS_WIDTH * 0.95,
            'y': CANVAS_HEIGHT * 0.88,
        },
        {
            'id': 'S18',
            'title': 'Draft launch announcement for JustData 1.0',
            'type': 'content',
            'priority': 'low',
            'app': '',
            'notes': 'Internal announcement to NCRC network. Master list #33.',
            'dependencies': ['S4'],
            'x': CANVAS_WIDTH * 0.95,
            'y': CANVAS_HEIGHT * 0.78,
        },
    ]

    for task in missing_tasks:
        if task['id'] not in existing_ids:
            add_task(client, task)
        else:
            print(f"  [SKIP] {task['id']} already exists")

    # =========================================================
    # 3. UPDATE DEPENDENCIES TO MATCH MASTER LIST
    # =========================================================
    print("\n[3/5] Updating dependencies to match master list...")

    # Key dependency mappings from master list
    # Master #1 (C1) blocks #21 (S7 videos), #29 (C19 map markers)
    # Master #2 (C2) blocks #21 (S7 videos)
    # Master #3 (S1) blocks #6, #16, #21
    # etc.

    dependency_updates = {
        # Videos now depend on C1, C2 being fixed (critical bugs)
        'S7': ['S4', 'C1', 'C2', 'S1', 'S2', 'C13'],  # Videos blocked by analytics, HUD data, legal

        # Lender Interest map depends on Analytics being fixed
        'C19': ['C1'],

        # User testing depends on legal clearance and early access
        'S9': ['S3', 'S4'],

        # FAQ depends on user testing
        'S14': ['S9'],

        # Training depends on videos
        'S13': ['S4', 'S7'],

        # BranchMapper national depends on census layers fix
        'S15': ['C7'],
    }

    for task_id, deps in dependency_updates.items():
        if task_id in existing_ids:
            update_task_dependencies(client, task_id, deps)

    # =========================================================
    # 4. ENSURE CORRECT TASK TYPES
    # =========================================================
    print("\n[4/5] Ensuring correct task types...")

    # Fix any type mismatches based on master list
    type_updates = {
        'C10': 'feature',  # AI narrative tone is a feature improvement
        'C11': 'feature',  # National trend data is a feature
        'C14': 'styling',  # User workflow documentation is UX/styling
        'C15': 'styling',  # Mobile responsiveness is styling
        'S8': 'styling',   # AI narrative style guide is styling
    }

    for task_id, task_type in type_updates.items():
        if task_id in existing_ids:
            update_task_type(client, task_id, task_type)

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

    print(f"  [OK] BUG_COMPLETE now has {len(bug_ids)} dependencies (including 2 CRITICAL)")
    print(f"  [OK] STYLE_COMPLETE now has {len(style_ids)} dependencies")
    print(f"  [OK] CONTENT_COMPLETE now has {len(content_ids)} dependencies")

    # =========================================================
    # SUMMARY
    # =========================================================
    print("\n" + "=" * 60)
    print("Sync Complete!")
    print("=" * 60)
    print("\nKey Changes:")
    print("  - C1 (Analytics Dashboard) upgraded to CRITICAL BUG")
    print("  - C2 (HUD Low-Mod Data) upgraded to CRITICAL BUG")
    print("  - Dependencies updated to match master list blocking chains")
    print("  - Collector dependencies refreshed")
    print("\nView changes at: https://justdata-test-892833260112.us-east1.run.app/workflow/")


if __name__ == '__main__':
    main()
