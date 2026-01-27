"""
Monday.com ↔ BigQuery Two-Way Sync for JustData Workflow.

Syncs tasks between Monday.com board and BigQuery workflow tables.
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from justdata.shared.utils.bigquery_client import get_bigquery_client


# Monday.com Configuration
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_BOARD_ID = "18397384545"

# Column IDs on Monday board (mapped from board inspection)
MONDAY_COLUMNS = {
    'workflow_id': 'text_mm00btkz',      # T-001, T-002, etc.
    'status': 'color_mm0075cw',           # Open, In Progress, Blocked, Done
    'priority': 'color_mm001096',         # Critical, High, Medium, Low
    'type': 'dropdown_mm00e36c',          # Work Area: Legal, Infrastructure, etc.
    'app': 'dropdown_mm00nzts',           # App dropdown
    'dependencies': 'dependency_mm0082qq', # Dependencies (links to other items)
    'notes': 'long_text_mm00ff69',        # Long text notes
    'created_date': 'date_mm001ej7',      # Created date
    'completed_date': 'date_mm00exyd',    # Completed date
    'blocked_by': 'text_mm006jas',        # Blocked By (informational)
    'enables': 'text_mm00aa84',           # Enables (informational)
}

# Status mapping: Monday → BigQuery
STATUS_MONDAY_TO_BQ = {
    'Open': 'open',
    'In Progress': 'in_progress',
    'Blocked': 'blocked',
    'Done': 'done',
    '': 'open',  # Default
}

# Status mapping: BigQuery → Monday
STATUS_BQ_TO_MONDAY = {
    'open': 'Open',
    'in_progress': 'In Progress',
    'blocked': 'Blocked',
    'done': 'Done',
}

# Priority mapping: Monday → BigQuery
PRIORITY_MONDAY_TO_BQ = {
    'Critical': 'critical',
    'High': 'high',
    'Medium': 'medium',
    'Low': 'low',
    '': 'medium',  # Default
}

# Priority mapping: BigQuery → Monday
PRIORITY_BQ_TO_MONDAY = {
    'critical': 'Critical',
    'high': 'High',
    'medium': 'Medium',
    'low': 'Low',
}

# Type mapping: Monday → BigQuery
TYPE_MONDAY_TO_BQ = {
    'Legal': 'legal',
    'Infrastructure': 'infrastructure',
    'Feature': 'feature',
    'Bug': 'bug',           # Monday uses "Bug" not "Bug Fix"
    'Bug Fix': 'bug',       # Keep for backwards compatibility
    'Styling': 'styling',
    'Content': 'content',
    '': 'feature',  # Default
}

# Type mapping: BigQuery → Monday
TYPE_BQ_TO_MONDAY = {
    'legal': 'Legal',
    'infrastructure': 'Infrastructure',
    'feature': 'Feature',
    'bug': 'Bug',           # Monday uses "Bug" not "Bug Fix"
    'styling': 'Styling',
    'content': 'Content',
}

# BigQuery configuration
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')
DATASET = 'justdata'
TASKS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_tasks'
POSITIONS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_positions'
COUNTER_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_task_counter'
SYNC_LOG_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_sync_log'


def get_monday_api_key() -> str:
    """Get Monday.com API key from environment."""
    key = os.environ.get('MONDAY_API_KEY') or os.environ.get('MONDAY_API_TOKEN')
    if not key:
        raise ValueError("MONDAY_API_KEY or MONDAY_API_TOKEN environment variable not set")
    return key


def monday_query(query: str, variables: Optional[Dict] = None) -> Dict:
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


def get_monday_board_items() -> List[Dict]:
    """Fetch all items from the Monday board with their column values."""
    query = """
    query ($boardId: ID!) {
        boards(ids: [$boardId]) {
            items_page(limit: 500) {
                items {
                    id
                    name
                    state
                    group {
                        id
                        title
                    }
                    created_at
                    updated_at
                    column_values {
                        id
                        type
                        value
                        text
                    }
                }
            }
        }
    }
    """

    data = monday_query(query, {"boardId": MONDAY_BOARD_ID})
    boards = data.get("boards", [])

    if not boards:
        return []

    items = boards[0].get("items_page", {}).get("items", [])
    return items


def parse_monday_item(item: Dict) -> Dict:
    """Parse a Monday item into a standardized task dict."""
    columns = {cv['id']: cv for cv in item.get('column_values', [])}

    # Extract values from columns
    workflow_id = columns.get(MONDAY_COLUMNS['workflow_id'], {}).get('text', '')
    status_text = columns.get(MONDAY_COLUMNS['status'], {}).get('text', '')
    priority_text = columns.get(MONDAY_COLUMNS['priority'], {}).get('text', '')
    type_text = columns.get(MONDAY_COLUMNS['type'], {}).get('text', '')
    app_text = columns.get(MONDAY_COLUMNS['app'], {}).get('text', '')
    notes_text = columns.get(MONDAY_COLUMNS['notes'], {}).get('text', '')

    # Parse dependencies - Monday stores as JSON with linkedPulseIds
    deps_column = columns.get(MONDAY_COLUMNS['dependencies'], {})
    deps_value = deps_column.get('value')
    monday_dep_ids = []
    if deps_value:
        try:
            deps_json = json.loads(deps_value)
            monday_dep_ids = [str(d['linkedPulseId']) for d in deps_json.get('linkedPulseIds', [])]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Parse dates
    created_date = columns.get(MONDAY_COLUMNS['created_date'], {}).get('text', '')
    completed_date = columns.get(MONDAY_COLUMNS['completed_date'], {}).get('text', '')

    return {
        'monday_item_id': str(item['id']),
        'monday_name': item['name'],
        'workflow_id': workflow_id.strip() if workflow_id else None,
        'status': STATUS_MONDAY_TO_BQ.get(status_text, 'open'),
        'priority': PRIORITY_MONDAY_TO_BQ.get(priority_text, 'medium'),
        'type': TYPE_MONDAY_TO_BQ.get(type_text, 'feature'),
        'app': app_text.split(',')[0].strip() if app_text else '',  # Take first app if multiple
        'notes': notes_text or '',
        'monday_dep_ids': monday_dep_ids,
        'group_id': item.get('group', {}).get('id', 'topics'),
        'group_name': item.get('group', {}).get('title', ''),
        'created_at': item.get('created_at'),
        'updated_at': item.get('updated_at'),
        'created_date': created_date,
        'completed_date': completed_date,
    }


def get_bq_tasks_with_monday_ids() -> Dict[str, Dict]:
    """Get all BigQuery tasks indexed by monday_item_id."""
    client = get_bigquery_client(PROJECT_ID)

    sql = f"""
    SELECT
        t.*,
        p.x,
        p.y
    FROM `{TASKS_TABLE}` t
    LEFT JOIN `{POSITIONS_TABLE}` p ON t.id = p.task_id
    """

    try:
        results = client.query(sql).result()
        tasks = {}
        for row in results:
            task = {
                'id': row.id,
                'title': row.title,
                'type': row.type,
                'priority': row.priority,
                'status': row.status,
                'app': row.app or '',
                'notes': row.notes or '',
                'dependencies': list(row.dependencies) if row.dependencies else [],
                'is_collector': row.is_collector,
                'is_goal': row.is_goal,
                'monday_item_id': getattr(row, 'monday_item_id', None),
                'x': getattr(row, 'x', None),
                'y': getattr(row, 'y', None),
            }
            if task['monday_item_id']:
                tasks[task['monday_item_id']] = task
        return tasks
    except Exception as e:
        print(f"Error fetching BQ tasks: {e}")
        return {}


def get_bq_task_by_id(task_id: str) -> Optional[Dict]:
    """Get a single BigQuery task by workflow ID."""
    client = get_bigquery_client(PROJECT_ID)

    sql = f"SELECT * FROM `{TASKS_TABLE}` WHERE id = '{task_id}'"

    try:
        results = list(client.query(sql).result())
        if results:
            row = results[0]
            return {
                'id': row.id,
                'monday_item_id': getattr(row, 'monday_item_id', None),
                'status': row.status,
                'dependencies': list(row.dependencies) if row.dependencies else [],
            }
    except Exception:
        pass
    return None


def generate_next_task_id() -> str:
    """Generate the next task ID (T-001, T-002, etc.)."""
    client = get_bigquery_client(PROJECT_ID)

    # Atomically increment
    sql = f"""
    UPDATE `{COUNTER_TABLE}`
    SET current_value = current_value + 1
    WHERE counter_name = 'task_id'
    """
    client.query(sql).result()

    # Get new value
    sql = f"SELECT current_value FROM `{COUNTER_TABLE}` WHERE counter_name = 'task_id'"
    result = list(client.query(sql).result())
    new_value = result[0].current_value

    return f"T{new_value}"


def create_bq_task(task_data: Dict, user_email: str = 'monday_sync') -> str:
    """Create a new task in BigQuery. Returns the task ID."""
    client = get_bigquery_client(PROJECT_ID)

    task_id = generate_next_task_id()
    now = datetime.utcnow()

    task_row = {
        'id': task_id,
        'title': task_data['monday_name'],
        'type': task_data['type'],
        'priority': task_data['priority'],
        'status': task_data['status'],
        'app': task_data['app'],
        'notes': task_data['notes'],
        'dependencies': [],  # Will be updated after all items synced
        'is_collector': False,
        'is_goal': False,
        'collector_for': None,
        'created_at': now.isoformat(),
        'updated_at': now.isoformat(),
        'created_by': user_email,
        'completed_at': now.isoformat() if task_data['status'] == 'done' else None,
        'completed_by': user_email if task_data['status'] == 'done' else None,
        'monday_item_id': task_data['monday_item_id'],
    }

    errors = client.insert_rows_json(TASKS_TABLE, [task_row])
    if errors:
        raise Exception(f"Failed to create BQ task: {errors}")

    # Create default position
    position_row = {
        'task_id': task_id,
        'x': 550.0,
        'y': 375.0,
        'updated_at': now.isoformat(),
        'updated_by': user_email,
    }
    client.insert_rows_json(POSITIONS_TABLE, [position_row])

    return task_id


def update_bq_task(task_id: str, updates: Dict) -> None:
    """Update a task in BigQuery."""
    client = get_bigquery_client(PROJECT_ID)

    set_clauses = []
    for field, value in updates.items():
        if field == 'dependencies':
            deps_str = ', '.join([f'"{d}"' for d in value])
            set_clauses.append(f"dependencies = [{deps_str}]")
        elif value is None:
            set_clauses.append(f"{field} = NULL")
        else:
            escaped = str(value).replace("'", "\\'").replace('"', '\\"')
            set_clauses.append(f"{field} = '{escaped}'")

    set_clauses.append(f"updated_at = TIMESTAMP('{datetime.utcnow().isoformat()}')")

    sql = f"""
    UPDATE `{TASKS_TABLE}`
    SET {', '.join(set_clauses)}
    WHERE id = '{task_id}'
    """

    client.query(sql).result()


def update_monday_item(item_id: str, column_updates: Dict[str, Any]) -> None:
    """Update a Monday item's column values."""
    # Build column_values JSON
    column_values = {}

    for col_name, value in column_updates.items():
        col_id = MONDAY_COLUMNS.get(col_name)
        if not col_id:
            continue

        if col_name == 'status':
            column_values[col_id] = {"label": value}
        elif col_name == 'priority':
            column_values[col_id] = {"label": value}
        elif col_name == 'completed_date':
            if value:
                column_values[col_id] = {"date": value}
            else:
                column_values[col_id] = None
        elif col_name == 'workflow_id':
            column_values[col_id] = value
        elif col_name == 'dependencies':
            # value should be list of Monday item IDs
            if value:
                column_values[col_id] = {"item_ids": value}
            else:
                column_values[col_id] = {"item_ids": []}
        elif col_name in ('blocked_by', 'enables'):
            column_values[col_id] = value
        else:
            column_values[col_id] = value

    if not column_values:
        return

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

    monday_query(mutation, {
        "boardId": MONDAY_BOARD_ID,
        "itemId": str(item_id),
        "columnValues": json.dumps(column_values)
    })


def create_monday_item(task: Dict, group_id: str = 'topics') -> Optional[str]:
    """
    Create a new item in Monday.com from a BigQuery task.

    Returns the Monday item ID if successful, None otherwise.
    """
    mutation = """
    mutation ($boardId: ID!, $groupId: String!, $itemName: String!, $columnValues: JSON!) {
        create_item(
            board_id: $boardId,
            group_id: $groupId,
            item_name: $itemName,
            column_values: $columnValues
        ) {
            id
        }
    }
    """

    # Build column values
    column_values = {
        MONDAY_COLUMNS['workflow_id']: task['id'],
        MONDAY_COLUMNS['status']: {"label": STATUS_BQ_TO_MONDAY.get(task.get('status', 'open'), 'Open')},
        MONDAY_COLUMNS['priority']: {"label": PRIORITY_BQ_TO_MONDAY.get(task.get('priority', 'medium'), 'Medium')},
    }

    # Add type if present
    if task.get('type'):
        type_label = TYPE_BQ_TO_MONDAY.get(task['type'])
        if type_label:
            column_values[MONDAY_COLUMNS['type']] = {"labels": [type_label]}

    # Add app if present
    if task.get('app'):
        column_values[MONDAY_COLUMNS['app']] = {"labels": [task['app']]}

    # Add notes if present
    if task.get('notes'):
        column_values[MONDAY_COLUMNS['notes']] = {"text": task['notes']}

    try:
        data = monday_query(mutation, {
            "boardId": MONDAY_BOARD_ID,
            "groupId": group_id,
            "itemName": task.get('title', 'Untitled Task'),
            "columnValues": json.dumps(column_values)
        })

        return data.get('create_item', {}).get('id')
    except Exception as e:
        print(f"Error creating Monday item for {task.get('id')}: {e}")
        return None


def sync_bigquery_to_monday(group_id: str = 'topics', user_email: str = 'bq_sync') -> Dict:
    """
    Push unlinked BigQuery tasks to Monday.com.

    Creates Monday items for tasks that don't have a monday_item_id,
    then updates BigQuery with the new Monday item IDs.

    Args:
        group_id: Monday group to create items in ('topics' for Launch, 'group_mm00hgb4' for Roadmap)
        user_email: Email to log as the sync user

    Returns a summary of the sync operation.
    """
    results = {
        'created': [],
        'skipped': [],
        'errors': [],
        'timestamp': datetime.utcnow().isoformat(),
    }

    client = get_bigquery_client(PROJECT_ID)

    # Get all tasks without monday_item_id (excluding collectors and goal)
    sql = f"""
    SELECT id, title, type, priority, status, app, notes, dependencies
    FROM `{TASKS_TABLE}`
    WHERE (monday_item_id IS NULL OR monday_item_id = '')
      AND is_collector = FALSE
      AND is_goal = FALSE
    ORDER BY created_at
    """

    try:
        rows = list(client.query(sql).result())
        print(f"Found {len(rows)} tasks to push to Monday")

        for row in rows:
            task = {
                'id': row.id,
                'title': row.title,
                'type': row.type,
                'priority': row.priority,
                'status': row.status,
                'app': row.app or '',
                'notes': row.notes or '',
                'dependencies': list(row.dependencies) if row.dependencies else [],
            }

            try:
                # Create item in Monday
                monday_item_id = create_monday_item(task, group_id)

                if monday_item_id:
                    # Update BigQuery with the Monday item ID
                    update_sql = f"""
                    UPDATE `{TASKS_TABLE}`
                    SET monday_item_id = '{monday_item_id}',
                        updated_at = TIMESTAMP('{datetime.utcnow().isoformat()}')
                    WHERE id = '{task['id']}'
                    """
                    client.query(update_sql).result()

                    results['created'].append({
                        'workflow_id': task['id'],
                        'monday_item_id': monday_item_id,
                        'title': task['title']
                    })
                    print(f"  Created: {task['id']} -> Monday #{monday_item_id}")
                else:
                    results['errors'].append({
                        'workflow_id': task['id'],
                        'error': 'Failed to create Monday item'
                    })

            except Exception as e:
                results['errors'].append({
                    'workflow_id': task['id'],
                    'error': str(e)
                })
                print(f"  Error: {task['id']} - {e}")

    except Exception as e:
        results['errors'].append({'error': str(e), 'type': 'general'})

    return results


def sync_monday_to_bigquery(user_email: str = 'monday_sync') -> Dict:
    """
    Sync items from Monday.com to BigQuery.

    Returns a summary of the sync operation.
    """
    results = {
        'created': [],
        'updated': [],
        'skipped': [],
        'errors': [],
        'timestamp': datetime.utcnow().isoformat(),
    }

    try:
        # Fetch Monday items
        monday_items = get_monday_board_items()

        # Get existing BQ tasks by monday_item_id
        bq_tasks_by_monday_id = get_bq_tasks_with_monday_ids()

        # Also build a map of workflow_id -> monday_item_id for dependency resolution
        workflow_to_monday = {}
        monday_to_workflow = {}

        for task in bq_tasks_by_monday_id.values():
            if task.get('monday_item_id'):
                monday_to_workflow[task['monday_item_id']] = task['id']
                workflow_to_monday[task['id']] = task['monday_item_id']

        # First pass: create/update tasks
        for item in monday_items:
            try:
                parsed = parse_monday_item(item)
                monday_id = parsed['monday_item_id']

                # Skip items that are deleted/archived
                if item.get('state') != 'active':
                    results['skipped'].append({
                        'monday_id': monday_id,
                        'name': parsed['monday_name'],
                        'reason': 'Item not active'
                    })
                    continue

                existing_task = bq_tasks_by_monday_id.get(monday_id)

                if existing_task:
                    # Update existing task
                    updates = {}

                    if parsed['monday_name'] != existing_task.get('title'):
                        updates['title'] = parsed['monday_name']
                    if parsed['status'] != existing_task.get('status'):
                        updates['status'] = parsed['status']
                    if parsed['priority'] != existing_task.get('priority'):
                        updates['priority'] = parsed['priority']
                    if parsed['type'] != existing_task.get('type'):
                        updates['type'] = parsed['type']
                    if parsed['app'] != existing_task.get('app'):
                        updates['app'] = parsed['app']
                    if parsed['notes'] != existing_task.get('notes'):
                        updates['notes'] = parsed['notes']

                    if updates:
                        update_bq_task(existing_task['id'], updates)
                        results['updated'].append({
                            'workflow_id': existing_task['id'],
                            'monday_id': monday_id,
                            'name': parsed['monday_name'],
                            'updates': list(updates.keys())
                        })
                    else:
                        results['skipped'].append({
                            'workflow_id': existing_task['id'],
                            'monday_id': monday_id,
                            'name': parsed['monday_name'],
                            'reason': 'No changes'
                        })
                else:
                    # Check if item already has a workflow_id assigned
                    if parsed['workflow_id']:
                        # Item was created before but we lost the monday_item_id link
                        # Try to link it
                        results['skipped'].append({
                            'monday_id': monday_id,
                            'name': parsed['monday_name'],
                            'reason': f'Has workflow_id {parsed["workflow_id"]} but not linked in BQ'
                        })
                        continue

                    # Create new task
                    task_id = create_bq_task(parsed, user_email)

                    # Update Monday item with workflow_id
                    update_monday_item(monday_id, {'workflow_id': task_id})

                    # Track for dependency resolution
                    monday_to_workflow[monday_id] = task_id
                    workflow_to_monday[task_id] = monday_id

                    results['created'].append({
                        'workflow_id': task_id,
                        'monday_id': monday_id,
                        'name': parsed['monday_name']
                    })

            except Exception as e:
                results['errors'].append({
                    'monday_id': item.get('id'),
                    'name': item.get('name'),
                    'error': str(e)
                })

        # Second pass: resolve dependencies
        for item in monday_items:
            try:
                parsed = parse_monday_item(item)
                monday_id = parsed['monday_item_id']

                if not parsed['monday_dep_ids']:
                    continue

                # Convert Monday item IDs to workflow IDs
                workflow_deps = []
                for dep_monday_id in parsed['monday_dep_ids']:
                    if dep_monday_id in monday_to_workflow:
                        workflow_deps.append(monday_to_workflow[dep_monday_id])

                if workflow_deps:
                    task_workflow_id = monday_to_workflow.get(monday_id)
                    if task_workflow_id:
                        update_bq_task(task_workflow_id, {'dependencies': workflow_deps})

            except Exception as e:
                # Log but don't fail
                print(f"Error updating dependencies for {item.get('id')}: {e}")

    except Exception as e:
        results['errors'].append({'error': str(e), 'type': 'general'})

    return results


def sync_task_status_to_monday(task_id: str, new_status: str) -> bool:
    """
    Sync a task's status change from BigQuery to Monday.

    Called when user toggles status in the workflow UI.
    Returns True if sync was successful.
    """
    try:
        task = get_bq_task_by_id(task_id)
        if not task or not task.get('monday_item_id'):
            return False

        monday_status = STATUS_BQ_TO_MONDAY.get(new_status, 'Open')

        updates = {'status': monday_status}

        # If marking as done, set completed date
        if new_status == 'done':
            updates['completed_date'] = datetime.utcnow().strftime('%Y-%m-%d')
        else:
            updates['completed_date'] = None

        update_monday_item(task['monday_item_id'], updates)
        return True

    except Exception as e:
        print(f"Error syncing status to Monday: {e}")
        return False


def sync_dependencies_to_monday(task_id: str, workflow_deps: List[str]) -> bool:
    """
    Sync a task's dependencies from BigQuery to Monday.

    Called when user links tasks in the workflow UI.
    Returns True if sync was successful.
    """
    try:
        task = get_bq_task_by_id(task_id)
        if not task or not task.get('monday_item_id'):
            return False

        # Convert workflow IDs to Monday item IDs
        client = get_bigquery_client(PROJECT_ID)

        if workflow_deps:
            deps_str = ', '.join([f"'{d}'" for d in workflow_deps])
            sql = f"""
            SELECT id, monday_item_id
            FROM `{TASKS_TABLE}`
            WHERE id IN ({deps_str}) AND monday_item_id IS NOT NULL
            """
            results = list(client.query(sql).result())
            monday_dep_ids = [int(row.monday_item_id) for row in results if row.monday_item_id]
        else:
            monday_dep_ids = []

        # Also update the informational "Blocked By" text column
        blocked_by_text = ', '.join(workflow_deps) if workflow_deps else ''

        update_monday_item(task['monday_item_id'], {
            'dependencies': monday_dep_ids,
            'blocked_by': blocked_by_text,
        })

        # Update the "Enables" field for the dependency tasks
        for dep_id in workflow_deps:
            dep_task = get_bq_task_by_id(dep_id)
            if dep_task and dep_task.get('monday_item_id'):
                # Get all tasks that depend on this dep
                sql = f"""
                SELECT id FROM `{TASKS_TABLE}`
                WHERE '{dep_id}' IN UNNEST(dependencies)
                """
                dependents = [row.id for row in client.query(sql).result()]
                enables_text = ', '.join(dependents)

                update_monday_item(dep_task['monday_item_id'], {
                    'enables': enables_text,
                })

        return True

    except Exception as e:
        print(f"Error syncing dependencies to Monday: {e}")
        return False


def get_sync_status() -> Dict:
    """Get the status of the last sync operation."""
    # For now, return a simple status
    # Could be enhanced to read from a sync_log table
    return {
        'last_sync': None,
        'items_synced': 0,
        'status': 'ready'
    }
