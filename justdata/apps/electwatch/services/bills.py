"""Key-bills route handlers (list / save / remove / detail).

Route-handler implementations extracted from blueprint.py. Each
function uses Flask's request context the same way it did inline
in the blueprint; the blueprint now contains thin wrappers that call
into here.
"""
import json
import logging
import threading
import uuid
from pathlib import Path
from urllib.parse import unquote

from flask import jsonify, render_template, request, Response, session

from justdata.main.auth import (
    admin_required,
    get_user_type,
    login_required,
    require_access,
    staff_required,
)
from justdata.shared.utils.progress_tracker import (
    create_progress_tracker,
    get_analysis_result,
    get_progress,
    store_analysis_result,
)

# Import version
try:
    from justdata.apps.electwatch.version import __version__
except ImportError:
    __version__ = '0.9.0'

# App directory (electwatch/) - parent of services/
APP_DIR = Path(__file__).parent.parent.absolute()

logger = logging.getLogger(__name__)


def bill_view(bill_id):
    """Bill view page."""
    breadcrumb_items = [
        {'name': 'ElectWatch', 'url': '/electwatch'},
        {'name': 'Bill', 'url': f'/electwatch/bill/{bill_id}'}
    ]
    return render_template(
        'bill_view.html',
        version=__version__,
        bill_id=bill_id,
        app_name='ElectWatch',
        breadcrumb_items=breadcrumb_items
    )


# =============================================================================
# API ROUTES
# =============================================================================

def api_key_bills():
    """Get the list of key finance bills."""
    key_bills_file = APP_DIR / 'data' / 'current' / 'key_bills.json'
    if key_bills_file.exists():
        try:
            with open(key_bills_file, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except Exception as e:
            logger.error(f"Error loading key_bills.json: {e}")
    return jsonify({'bills': []})

def api_save_key_bill():
    """Save a bill to the Key Finance Bills list (staff/admin only)."""
    from datetime import datetime

    user_type = get_user_type()
    if user_type not in ('staff', 'admin'):
        return jsonify({'success': False, 'error': 'Only staff/admin can save key bills'}), 403

    data = request.get_json()
    bill_id = data.get('bill_id')
    bill_title = data.get('title')
    bill_summary = data.get('summary', '')

    if not bill_id:
        return jsonify({'success': False, 'error': 'Bill ID required'}), 400

    # Ensure data directory exists
    data_dir = APP_DIR / 'data' / 'current'
    data_dir.mkdir(parents=True, exist_ok=True)

    # Load existing key bills
    key_bills_file = data_dir / 'key_bills.json'
    key_bills = []
    if key_bills_file.exists():
        try:
            with open(key_bills_file, 'r', encoding='utf-8') as f:
                key_bills = json.load(f).get('bills', [])
        except Exception as e:
            logger.warning(f"Could not load existing key_bills.json: {e}")

    # Check if already saved
    if any(b['id'] == bill_id for b in key_bills):
        return jsonify({'success': False, 'error': 'Bill already in key bills list'})

    # Add to list
    key_bills.append({
        'id': bill_id,
        'title': bill_title,
        'summary': bill_summary[:500] if bill_summary else '',  # Truncate summary
        'added_by': user_type,
        'added_at': datetime.now().isoformat()
    })

    # Save
    try:
        with open(key_bills_file, 'w', encoding='utf-8') as f:
            json.dump({'bills': key_bills, 'updated_at': datetime.now().isoformat()}, f, indent=2)
        return jsonify({'success': True, 'message': f'Bill {bill_id} added to Key Finance Bills'})
    except Exception as e:
        logger.error(f"Error saving key_bills.json: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def api_remove_key_bill():
    """Remove a bill from the Key Finance Bills list (staff/admin only)."""
    from datetime import datetime

    user_type = get_user_type()
    if user_type not in ('staff', 'admin'):
        return jsonify({'success': False, 'error': 'Only staff/admin can remove key bills'}), 403

    data = request.get_json()
    bill_id = data.get('bill_id')

    key_bills_file = APP_DIR / 'data' / 'current' / 'key_bills.json'
    if not key_bills_file.exists():
        return jsonify({'success': False, 'error': 'No key bills file'})

    try:
        with open(key_bills_file, 'r', encoding='utf-8') as f:
            key_bills = json.load(f).get('bills', [])

        key_bills = [b for b in key_bills if b['id'] != bill_id]

        with open(key_bills_file, 'w', encoding='utf-8') as f:
            json.dump({'bills': key_bills, 'updated_at': datetime.now().isoformat()}, f, indent=2)

        return jsonify({'success': True, 'message': f'Bill {bill_id} removed from Key Finance Bills'})
    except Exception as e:
        logger.error(f"Error removing key bill: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# ADMIN MAPPING API ROUTES
# =============================================================================

