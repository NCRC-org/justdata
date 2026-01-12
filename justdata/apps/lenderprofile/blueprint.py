"""
LenderProfile Blueprint for main JustData app.
Converts the standalone LenderProfile app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, Response, current_app
from jinja2 import ChoiceLoader, FileSystemLoader
import json
import time
import logging
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, get_user_type
from .config import TEMPLATES_DIR, STATIC_DIR
from .version import __version__

# Get repo root for shared static files
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
lenderprofile_bp = Blueprint(
    'lenderprofile',
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='/lenderprofile/static'
)


@lenderprofile_bp.record_once
def configure_template_loader(state):
    """Configure Jinja2 to search both blueprint templates and shared templates."""
    app = state.app
    # Add shared templates to the loader
    blueprint_loader = FileSystemLoader(str(TEMPLATES_DIR))
    shared_loader = FileSystemLoader(str(SHARED_TEMPLATES_DIR))
    # Create a choice loader that searches blueprint templates first, then shared
    app.jinja_loader = ChoiceLoader([
        app.jinja_loader,
        blueprint_loader,
        shared_loader
    ])


@lenderprofile_bp.route('/')
@require_access('lenderprofile', 'full')
def index():
    """Main LenderProfile page."""
    return render_template('index.html', version=__version__)


@lenderprofile_bp.route('/api/search-lender', methods=['POST'])
@require_access('lenderprofile', 'full')
def api_search_lender():
    """Search for lenders."""
    from .lender_search import search_lenders
    try:
        data = request.get_json()
        search_term = data.get('search_term', '')
        results = search_lenders(search_term)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        logger.error(f"Error in lender search: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@lenderprofile_bp.route('/api/generate-report', methods=['POST'])
@require_access('lenderprofile', 'full')
def api_generate_report():
    """Generate lender profile report."""
    from .report_generator import generate_report
    try:
        data = request.get_json()
        result = generate_report(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@lenderprofile_bp.route('/report/<report_id>')
@require_access('lenderprofile', 'full')
def view_report(report_id):
    """View generated report."""
    return render_template('report_template.html', report_id=report_id, version=__version__)


@lenderprofile_bp.route('/progress/<job_id>', methods=['GET'])
def progress(job_id):
    """Get progress of report generation."""
    from justdata.shared.utils.progress_tracker import get_progress
    
    def event_stream():
        last_percent = -1
        while True:
            progress = get_progress(job_id)
            percent = progress.get("percent", 0)
            step = progress.get("step", "Starting...")
            done = progress.get("done", False)
            error = progress.get("error", None)
            if percent != last_percent or done or error:
                yield f"data: {{\"percent\": {percent}, \"step\": \"{step}\", \"done\": {str(done).lower()}, \"error\": {json.dumps(error) if error else 'null'}}}\n\n"
                last_percent = percent
            if done or error:
                break
            time.sleep(0.5)
    return Response(event_stream(), mimetype="text/event-stream")
