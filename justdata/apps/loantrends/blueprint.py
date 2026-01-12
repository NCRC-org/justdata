"""
LoanTrends Blueprint for main JustData app.
Converts the standalone LoanTrends app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, Response
import json
import time
import logging
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, get_user_type
from .config import TEMPLATES_DIR, STATIC_DIR
from .version import __version__

# Get repo root for shared static files
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
loantrends_bp = Blueprint(
    'loantrends',
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='/loantrends/static'
)


@loantrends_bp.route('/')
@require_access('loantrends', 'full')
def index():
    """Main LoanTrends page."""
    return render_template('analysis_template.html', version=__version__)


@loantrends_bp.route('/api/dashboard-data', methods=['GET'])
@require_access('loantrends', 'full')
def api_dashboard_data():
    """Get dashboard data."""
    from .core import get_dashboard_data
    try:
        data = get_dashboard_data()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@loantrends_bp.route('/analyze', methods=['POST'])
@require_access('loantrends', 'full')
def analyze():
    """Run loan trends analysis."""
    from .core import run_analysis
    try:
        data = request.get_json()
        result = run_analysis(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@loantrends_bp.route('/progress/<job_id>')
def progress(job_id):
    """Get progress of analysis."""
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


@loantrends_bp.route('/results/<job_id>', methods=['GET'])
@require_access('loantrends', 'full')
def get_results(job_id):
    """Get analysis results."""
    from justdata.shared.utils.progress_tracker import get_analysis_result
    try:
        result = get_analysis_result(job_id)
        if result:
            return jsonify({'success': True, 'data': result})
        return jsonify({'success': False, 'error': 'Results not found'}), 404
    except Exception as e:
        logger.error(f"Error getting results: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@loantrends_bp.route('/report/<job_id>', methods=['GET'])
@require_access('loantrends', 'full')
def view_report(job_id):
    """View analysis report."""
    return render_template('report_template.html', job_id=job_id, version=__version__)


@loantrends_bp.route('/api/available-graphs', methods=['GET'])
@require_access('loantrends', 'full')
def api_available_graphs():
    """Get available graph types."""
    graphs = [
        {'id': 'loan_volume', 'name': 'Loan Volume Trends'},
        {'id': 'approval_rates', 'name': 'Approval Rate Trends'},
        {'id': 'demographics', 'name': 'Demographic Trends'},
        {'id': 'geographic', 'name': 'Geographic Trends'}
    ]
    return jsonify({'success': True, 'graphs': graphs})
