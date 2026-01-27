"""
Workflow Blueprint - Project management visualization for JustData.
Admin-only access. Tasks stored in BigQuery.
"""
import os
from datetime import datetime
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, g
from jinja2 import ChoiceLoader, FileSystemLoader

from justdata.main.auth import admin_required, get_current_user
from justdata.shared.utils.bigquery_client import get_bigquery_client as get_shared_bq_client

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
    """Update a task's fields (not status - use toggle for that)."""
    client = get_bq_client()
    data = request.json

    # Build SET clause dynamically based on provided fields
    allowed_fields = ['title', 'type', 'priority', 'app', 'notes', 'dependencies']
    set_clauses = []

    for field in allowed_fields:
        if field in data:
            if field == 'dependencies':
                # Handle array field - escape each value
                deps = data[field] if data[field] else []
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
        return jsonify({'success': True})
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
    """Toggle a task's status between open and done."""
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

        return jsonify({'success': True, 'new_status': new_status})

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
