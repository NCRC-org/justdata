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

from justdata.main.auth import require_access, get_user_permissions, get_user_type, login_required
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
@login_required
@require_access('lenderprofile', 'full')
def index():
    """Main LenderProfile page."""
    return render_template('index.html', version=__version__)


@lenderprofile_bp.route('/api/search-lender', methods=['POST'])
@require_access('lenderprofile', 'full')
def api_search_lender():
    """Search for lenders by name using FDIC and identifier resolution."""
    from .processors.identifier_resolver import IdentifierResolver
    try:
        data = request.get_json()
        # Accept both 'query' (from frontend) and 'search_term' for backwards compatibility
        query = data.get('query', data.get('search_term', '')).strip()
        excluded_lenders = data.get('exclude', [])

        if not query or len(query) < 2:
            return jsonify({'error': 'Search query must be at least 2 characters'}), 400

        logger.info(f"Searching for lender: '{query}'")

        # Check if a specific candidate was selected
        selected_candidate = data.get('selected_candidate')

        if selected_candidate:
            # User selected a specific candidate - resolve it directly
            logger.info(f"Resolving selected candidate: {selected_candidate.get('name')}")
            resolver = IdentifierResolver()

            # Build identifiers from selected candidate
            identifiers = {
                'name': selected_candidate.get('name', query),
                'lei': selected_candidate.get('lei'),
                'rssd_id': selected_candidate.get('rssd_id'),
                'fdic_cert': selected_candidate.get('fdic_cert'),
                'confidence': 1.0
            }

            # Get full details
            details = resolver.get_institution_details(identifiers)
            tax_id = identifiers.get('tax_id') or details.get('tax_id')

            result = {
                'success': True,
                'name': identifiers.get('name', query),
                'identifiers': identifiers,
                'details': details,
                'fdic_cert': identifiers.get('fdic_cert'),
                'rssd_id': identifiers.get('rssd_id'),
                'lei': identifiers.get('lei'),
                'tax_id': tax_id,
                'type': identifiers.get('type'),
                'confidence': identifiers.get('confidence', 0.0)
            }

            logger.info(f"Resolved selected lender: {result.get('name')}")
            return jsonify(result)

        # Resolve identifiers - get multiple candidates
        try:
            resolver = IdentifierResolver()
            candidates = resolver.get_candidates_with_location(query, exclude=excluded_lenders, limit=10)
            logger.info(f"Found {len(candidates)} candidates for '{query}'")
        except Exception as e:
            logger.error(f"Error in identifier resolution: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Error searching for lender: {str(e)}',
                'query': query
            }), 500

        if not candidates:
            logger.warning(f"No candidates found for '{query}'")
            return jsonify({
                'success': False,
                'message': f'No institution found matching "{query}"',
                'query': query
            }), 404

        # If only one candidate, return it directly
        if len(candidates) == 1:
            identifiers = candidates[0]
            details = resolver.get_institution_details(identifiers)
            tax_id = identifiers.get('tax_id') or details.get('tax_id')

            result = {
                'success': True,
                'name': identifiers.get('name', query),
                'identifiers': identifiers,
                'details': details,
                'fdic_cert': identifiers.get('fdic_cert'),
                'rssd_id': identifiers.get('rssd_id'),
                'lei': identifiers.get('lei'),
                'tax_id': tax_id,
                'type': identifiers.get('type'),
                'confidence': identifiers.get('confidence', 0.0)
            }

            logger.info(f"Found single lender: {result.get('name')}")
            return jsonify(result)

        # Multiple candidates - return them for user selection
        formatted_candidates = []
        for candidate in candidates:
            city = candidate.get('city', '')
            state = candidate.get('state', '')
            location = f"{city}, {state}".strip(', ') if city or state else 'Location unknown'

            formatted_candidates.append({
                'name': candidate.get('name', ''),
                'city': city,
                'state': state,
                'location': location,
                'fdic_cert': candidate.get('fdic_cert'),
                'rssd_id': candidate.get('rssd_id'),
                'lei': candidate.get('lei'),
                'type': candidate.get('type', ''),
                'confidence': candidate.get('confidence', 0.0)
            })

        logger.info(f"Returning {len(formatted_candidates)} candidates for user selection")
        return jsonify({
            'success': True,
            'multiple': True,
            'candidates': formatted_candidates,
            'query': query
        })

    except Exception as e:
        logger.error(f"Error searching lenders: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred searching lenders: {str(e)}'}), 500


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
def view_report(report_id: str):
    """View a generated report or show progress if still generating."""
    from justdata.shared.utils.progress_tracker import get_analysis_result, get_progress

    try:
        result = get_analysis_result(report_id)

        if not result:
            # Check if job is still in progress
            progress_data = get_progress(report_id)
            if progress_data and not progress_data.get('done', False):
                # Job is still running - show progress page
                return render_template('report_progress.html',
                                     job_id=report_id,
                                     version=__version__)

            # Job not found and not in progress - show error
            return f"""
            <html><body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2>Report Not Found</h2>
                <p>Report not found. The analysis may still be running or may have expired.</p>
                <p>Job ID: {report_id}</p>
                <a href="/">Return to Home</a>
            </body></html>
            """, 404

        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            return f"""
            <html><body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2>Report Generation Failed</h2>
                <p>{error_msg}</p>
                <p>Job ID: {report_id}</p>
                <a href="/">Return to Home</a>
            </body></html>
            """, 500

        # Report is ready - display it using the report_v2 template
        report = result.get('report', {})
        metadata = result.get('metadata', {})

        return render_template('report_v2.html',
                             report=report,
                             metadata=metadata,
                             report_id=report_id,
                             version=__version__)

    except Exception as e:
        logger.error(f"Error viewing report {report_id}: {e}", exc_info=True)
        return f"""
        <html><body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2>Error</h2>
            <p>An error occurred while loading the report.</p>
            <p>{str(e)}</p>
            <a href="/">Return to Home</a>
        </body></html>
        """, 500


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
