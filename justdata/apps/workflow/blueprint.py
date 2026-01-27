"""
Workflow Blueprint - Project management visualization for JustData.
Admin-only access. Tasks stored in BigQuery.
Two-way sync with Monday.com board.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, g
from jinja2 import ChoiceLoader, FileSystemLoader

from justdata.main.auth import admin_required, get_current_user
from justdata.shared.utils.bigquery_client import get_bigquery_client as get_shared_bq_client

# Monday sync functions (lazy import to avoid circular deps)
_monday_sync = None

def get_monday_sync():
    """Lazy import of monday_sync module."""
    global _monday_sync
    if _monday_sync is None:
        try:
            from justdata.apps.workflow import monday_sync
            _monday_sync = monday_sync
        except ImportError as e:
            print(f"Warning: Could not import monday_sync: {e}")
            _monday_sync = False
    return _monday_sync if _monday_sync else None

# Directory configuration
BLUEPRINT_DIR = Path(__file__).parent
TEMPLATES_DIR = BLUEPRINT_DIR / 'templates'
REPO_ROOT = BLUEPRINT_DIR.parent.parent
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# Create blueprint
workflow_bp = Blueprint(
    'workflow',
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(BLUEPRINT_DIR / 'static'),
    static_url_path='/workflow/static'
)


@workflow_bp.record_once
def configure_template_loader(state):
    """Configure Jinja2 to look in blueprint templates first, then shared."""
    app = state.app
    blueprint_loader = FileSystemLoader(str(TEMPLATES_DIR))
    app.jinja_loader = ChoiceLoader([
        blueprint_loader,
        app.jinja_loader
    ])


# BigQuery configuration
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')
DATASET = 'justdata'
TASKS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_tasks'
POSITIONS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_positions'
COUNTER_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_task_counter'

# BigQuery client (lazy initialization)
_bq_client = None


def get_bq_client():
    """Get or create BigQuery client using shared credentials."""
    global _bq_client
    if _bq_client is None:
        _bq_client = get_shared_bq_client(PROJECT_ID)
    return _bq_client


def get_current_user_email():
    """Get the current user's email from auth context."""
    user = get_current_user()
    if user:
        return user.get('email', 'unknown')
    return 'unknown'


def row_to_dict(row):
    """Convert a BigQuery Row to a dictionary."""
    return {
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
        'collector_for': row.collector_for,
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
        'completed_at': row.completed_at.isoformat() if row.completed_at else None,
        'x': getattr(row, 'x', None),
        'y': getattr(row, 'y', None),
        'monday_item_id': getattr(row, 'monday_item_id', None),
    }


def generate_task_id():
    """Generate the next task ID (T-001, T-002, etc.)."""
    client = get_bq_client()

    # Atomically increment and get the new value
    sql = f"""
    UPDATE `{COUNTER_TABLE}`
    SET current_value = current_value + 1
    WHERE counter_name = 'task_id'
    """
    client.query(sql).result()

    # Get the new value
    sql = f"SELECT current_value FROM `{COUNTER_TABLE}` WHERE counter_name = 'task_id'"
    result = list(client.query(sql).result())
    new_value = result[0].current_value

    return f"T{new_value}"


# ============================================================
# Page Routes
# ============================================================

@workflow_bp.route('/')
@admin_required
def index():
    """Serve the main workflow app."""
    return render_template('workflow.html')


@workflow_bp.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'app': 'workflow'})


# ============================================================
# API Routes
# ============================================================

@workflow_bp.route('/api/tasks', methods=['GET'])
@admin_required
def get_tasks():
    """Get all tasks with their positions."""
    client = get_bq_client()

    sql = f"""
    SELECT
        t.*,
        p.x,
        p.y
    FROM `{TASKS_TABLE}` t
    LEFT JOIN `{POSITIONS_TABLE}` p ON t.id = p.task_id
    ORDER BY t.created_at
    """

    try:
        results = client.query(sql).result()
        tasks = [row_to_dict(row) for row in results]
        return jsonify({'tasks': tasks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workflow_bp.route('/api/tasks', methods=['POST'])
@admin_required
def create_task():
    """Create a new task."""
    client = get_bq_client()
    data = request.json

    # Validate required fields
    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    if not data.get('type'):
        return jsonify({'error': 'Type is required'}), 400
    if not data.get('priority'):
        return jsonify({'error': 'Priority is required'}), 400

    # Validate type and priority
    valid_types = ['legal', 'infrastructure', 'feature', 'bug', 'styling', 'content']
    valid_priorities = ['critical', 'high', 'medium', 'low']

    if data['type'] not in valid_types:
        return jsonify({'error': f'Invalid type. Must be one of: {valid_types}'}), 400
    if data['priority'] not in valid_priorities:
        return jsonify({'error': f'Invalid priority. Must be one of: {valid_priorities}'}), 400

    # Generate ID
    task_id = generate_task_id()
    now = datetime.utcnow()
    user_email = get_current_user_email()

    # Insert task
    task_row = {
        'id': task_id,
        'title': data['title'],
        'type': data['type'],
        'priority': data['priority'],
        'status': 'open',
        'app': data.get('app', ''),
        'notes': data.get('notes', ''),
        'dependencies': data.get('dependencies', []),
        'is_collector': False,
        'is_goal': False,
        'collector_for': None,
        'created_at': now.isoformat(),
        'updated_at': now.isoformat(),
        'created_by': user_email,
        'completed_at': None,
        'completed_by': None,
    }

    try:
        errors = client.insert_rows_json(TASKS_TABLE, [task_row])
        if errors:
            return jsonify({'error': f'Failed to create task: {errors}'}), 500

        # Insert default position (center of canvas)
        position_row = {
            'task_id': task_id,
            'x': 550.0,  # Center X
            'y': 375.0,  # Center Y
            'updated_at': now.isoformat(),
            'updated_by': user_email,
        }

        client.insert_rows_json(POSITIONS_TABLE, [position_row])

        # Return the created task with position
        task_row['x'] = position_row['x']
        task_row['y'] = position_row['y']

        return jsonify({'task': task_row}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workflow_bp.route('/api/tasks/<task_id>', methods=['PUT'])
@admin_required
def update_task(task_id):
    """Update a task's fields (not status - use toggle for that). Syncs dependencies to Monday.com."""
    client = get_bq_client()
    data = request.json

    # Build SET clause dynamically based on provided fields
    allowed_fields = ['title', 'type', 'priority', 'app', 'notes', 'dependencies']
    set_clauses = []
    deps_updated = False
    new_deps = []

    for field in allowed_fields:
        if field in data:
            if field == 'dependencies':
                # Handle array field - escape each value
                deps = data[field] if data[field] else []
                new_deps = deps
                deps_updated = True
                deps_str = ', '.join([f'"{d}"' for d in deps])
                set_clauses.append(f"dependencies = [{deps_str}]")
            else:
                # Escape string values
                escaped_value = str(data[field]).replace("'", "\\'").replace('"', '\\"')
                set_clauses.append(f"{field} = '{escaped_value}'")

    if not set_clauses:
        return jsonify({'error': 'No valid fields to update'}), 400

    set_clauses.append(f"updated_at = TIMESTAMP('{datetime.utcnow().isoformat()}')")

    sql = f"""
    UPDATE `{TASKS_TABLE}`
    SET {', '.join(set_clauses)}
    WHERE id = '{task_id}'
    """

    try:
        client.query(sql).result()

        # Sync dependencies to Monday.com if they were updated
        monday_synced = False
        if deps_updated:
            monday_sync = get_monday_sync()
            if monday_sync:
                try:
                    monday_synced = monday_sync.sync_dependencies_to_monday(task_id, new_deps)
                except Exception as e:
                    print(f"Warning: Failed to sync dependencies to Monday: {e}")

        return jsonify({'success': True, 'monday_synced': monday_synced})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workflow_bp.route('/api/tasks/<task_id>', methods=['DELETE'])
@admin_required
def delete_task(task_id):
    """Delete a task."""
    client = get_bq_client()

    # Don't allow deleting collectors or goal
    check_sql = f"SELECT is_collector, is_goal FROM `{TASKS_TABLE}` WHERE id = '{task_id}'"
    try:
        result = list(client.query(check_sql).result())

        if not result:
            return jsonify({'error': 'Task not found'}), 404

        if result[0].is_collector or result[0].is_goal:
            return jsonify({'error': 'Cannot delete collectors or goal'}), 400

        # Delete task
        client.query(f"DELETE FROM `{TASKS_TABLE}` WHERE id = '{task_id}'").result()

        # Delete position
        client.query(f"DELETE FROM `{POSITIONS_TABLE}` WHERE task_id = '{task_id}'").result()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workflow_bp.route('/api/tasks/<task_id>/toggle', methods=['PUT'])
@admin_required
def toggle_task(task_id):
    """Toggle a task's status between open and done. Syncs to Monday.com."""
    client = get_bq_client()
    user_email = get_current_user_email()
    now = datetime.utcnow()

    # Get current status
    sql = f"SELECT status, is_goal FROM `{TASKS_TABLE}` WHERE id = '{task_id}'"
    try:
        result = list(client.query(sql).result())

        if not result:
            return jsonify({'error': 'Task not found'}), 404

        if result[0].is_goal:
            return jsonify({'error': 'Cannot toggle goal status'}), 400

        current_status = result[0].status
        new_status = 'done' if current_status == 'open' else 'open'

        if new_status == 'done':
            sql = f"""
            UPDATE `{TASKS_TABLE}`
            SET status = 'done',
                completed_at = TIMESTAMP('{now.isoformat()}'),
                completed_by = '{user_email}',
                updated_at = TIMESTAMP('{now.isoformat()}')
            WHERE id = '{task_id}'
            """
        else:
            sql = f"""
            UPDATE `{TASKS_TABLE}`
            SET status = 'open',
                completed_at = NULL,
                completed_by = NULL,
                updated_at = TIMESTAMP('{now.isoformat()}')
            WHERE id = '{task_id}'
            """

        client.query(sql).result()

        # Sync status change to Monday.com
        monday_synced = False
        monday_sync = get_monday_sync()
        if monday_sync:
            try:
                monday_synced = monday_sync.sync_task_status_to_monday(task_id, new_status)
            except Exception as e:
                print(f"Warning: Failed to sync status to Monday: {e}")

        return jsonify({
            'success': True,
            'new_status': new_status,
            'monday_synced': monday_synced
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workflow_bp.route('/api/positions', methods=['POST'])
@admin_required
def update_positions():
    """Batch update positions for multiple tasks using MERGE for reliable upsert."""
    client = get_bq_client()
    data = request.json

    positions = data.get('positions', [])
    if not positions:
        return jsonify({'error': 'No positions provided'}), 400

    user_email = get_current_user_email()
    now = datetime.utcnow().isoformat()

    try:
        # Use MERGE for each position (BigQuery's upsert)
        for pos in positions:
            task_id = pos['task_id']
            x = float(pos['x'])
            y = float(pos['y'])

            sql = f"""
            MERGE `{POSITIONS_TABLE}` T
            USING (SELECT '{task_id}' as task_id, {x} as x, {y} as y) S
            ON T.task_id = S.task_id
            WHEN MATCHED THEN
                UPDATE SET x = S.x, y = S.y, updated_at = TIMESTAMP('{now}'), updated_by = '{user_email}'
            WHEN NOT MATCHED THEN
                INSERT (task_id, x, y, updated_at, updated_by)
                VALUES (S.task_id, S.x, S.y, TIMESTAMP('{now}'), '{user_email}')
            """
            client.query(sql).result()

        return jsonify({'success': True, 'updated': len(positions)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workflow_bp.route('/api/collectors/refresh', methods=['POST'])
@admin_required
def refresh_collectors():
    """Refresh collector dependencies based on current task types."""
    client = get_bq_client()

    try:
        # Get all open task IDs by type
        sql = f"""
        SELECT type, ARRAY_AGG(id) as task_ids
        FROM `{TASKS_TABLE}`
        WHERE type IN ('bug', 'styling', 'content')
          AND is_collector = FALSE
          AND is_goal = FALSE
          AND status = 'open'
        GROUP BY type
        """

        result = client.query(sql).result()
        type_tasks = {row.type: list(row.task_ids) for row in result}

        # Update each collector
        collector_mapping = {
            'BUG_COMPLETE': 'bug',
            'STYLE_COMPLETE': 'styling',
            'CONTENT_COMPLETE': 'content',
        }

        for collector_id, task_type in collector_mapping.items():
            task_ids = type_tasks.get(task_type, [])
            deps_str = ', '.join([f'"{id}"' for id in task_ids])

            sql = f"""
            UPDATE `{TASKS_TABLE}`
            SET dependencies = [{deps_str}],
                updated_at = TIMESTAMP('{datetime.utcnow().isoformat()}')
            WHERE id = '{collector_id}'
            """
            client.query(sql).result()

        return jsonify({'success': True, 'collectors_updated': list(collector_mapping.keys())})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workflow_bp.route('/api/stats', methods=['GET'])
@admin_required
def get_stats():
    """Get workflow statistics."""
    client = get_bq_client()

    try:
        sql = f"""
        SELECT
            COUNT(*) as total,
            COUNTIF(status = 'open' AND NOT is_goal AND NOT is_collector) as open_tasks,
            COUNTIF(status = 'done') as done_tasks,
            COUNTIF(priority = 'critical' AND status = 'open') as critical,
            COUNTIF(priority = 'high' AND status = 'open') as high
        FROM `{TASKS_TABLE}`
        """

        result = list(client.query(sql).result())
        row = result[0]

        return jsonify({
            'total': row.total,
            'open': row.open_tasks,
            'done': row.done_tasks,
            'critical': row.critical,
            'high': row.high
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# Monday.com Sync API Routes
# ============================================================

@workflow_bp.route('/api/sync/from-monday', methods=['POST'])
@admin_required
def sync_from_monday():
    """
    Sync tasks from Monday.com to BigQuery.

    Fetches all items from the Monday board, creates new tasks in BigQuery
    for items without a workflow_id, and updates existing tasks.
    """
    user_email = get_current_user_email()

    monday_sync = get_monday_sync()
    if not monday_sync:
        return jsonify({
            'error': 'Monday sync module not available. Check MONDAY_API_KEY.'
        }), 500

    try:
        result = monday_sync.sync_monday_to_bigquery(user_email)

        # Log the sync
        client = get_bq_client()
        sync_id = str(uuid.uuid4())
        errors_json = str(result.get('errors', []))[:1000]  # Truncate for storage

        try:
            log_sql = f"""
            INSERT INTO `{PROJECT_ID}.{DATASET}.workflow_sync_log`
            (sync_id, sync_time, direction, items_created, items_updated, items_skipped, user_email, details)
            VALUES (
                '{sync_id}',
                CURRENT_TIMESTAMP(),
                'monday_to_bq',
                {len(result.get('created', []))},
                {len(result.get('updated', []))},
                {len(result.get('skipped', []))},
                '{user_email}',
                '{errors_json.replace("'", "''")}'
            )
            """
            client.query(log_sql).result()
        except Exception as log_error:
            print(f"Warning: Failed to log sync: {log_error}")

        return jsonify({
            'success': True,
            'sync_id': sync_id,
            'created': len(result.get('created', [])),
            'updated': len(result.get('updated', [])),
            'skipped': len(result.get('skipped', [])),
            'errors': len(result.get('errors', [])),
            'details': result
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workflow_bp.route('/api/sync/status', methods=['GET'])
@admin_required
def get_sync_status():
    """Get the status of the last sync operation."""
    client = get_bq_client()

    try:
        sql = f"""
        SELECT
            sync_id,
            sync_time,
            direction,
            items_created,
            items_updated,
            items_skipped,
            user_email
        FROM `{PROJECT_ID}.{DATASET}.workflow_sync_log`
        ORDER BY sync_time DESC
        LIMIT 5
        """

        results = list(client.query(sql).result())

        syncs = [{
            'sync_id': row.sync_id,
            'sync_time': row.sync_time.isoformat() if row.sync_time else None,
            'direction': row.direction,
            'items_created': row.items_created,
            'items_updated': row.items_updated,
            'items_skipped': row.items_skipped,
            'user_email': row.user_email,
        } for row in results]

        return jsonify({
            'syncs': syncs,
            'last_sync': syncs[0] if syncs else None,
            'monday_configured': bool(get_monday_sync())
        })

    except Exception as e:
        # Table might not exist yet
        return jsonify({
            'syncs': [],
            'last_sync': None,
            'monday_configured': bool(get_monday_sync()),
            'note': 'Sync log table may not exist yet. Run migration first.'
        })


@workflow_bp.route('/api/sync/to-monday/<task_id>', methods=['POST'])
@admin_required
def sync_task_to_monday(task_id):
    """
    Manually sync a specific task to Monday.com.

    Useful for syncing tasks that were created in the workflow UI.
    """
    monday_sync = get_monday_sync()
    if not monday_sync:
        return jsonify({
            'error': 'Monday sync module not available.'
        }), 500

    try:
        # Get the task
        client = get_bq_client()
        sql = f"SELECT * FROM `{TASKS_TABLE}` WHERE id = '{task_id}'"
        results = list(client.query(sql).result())

        if not results:
            return jsonify({'error': 'Task not found'}), 404

        task = results[0]

        if task.monday_item_id:
            # Task already linked to Monday, just sync status and deps
            status_synced = monday_sync.sync_task_status_to_monday(
                task_id,
                task.status
            )
            deps = list(task.dependencies) if task.dependencies else []
            deps_synced = monday_sync.sync_dependencies_to_monday(task_id, deps)

            return jsonify({
                'success': True,
                'status_synced': status_synced,
                'deps_synced': deps_synced,
                'monday_item_id': task.monday_item_id
            })
        else:
            # Task not linked to Monday - would need to create in Monday
            # For now, return info that task isn't linked
            return jsonify({
                'success': False,
                'error': 'Task not linked to Monday.com. Sync from Monday first to link items.'
            }), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
