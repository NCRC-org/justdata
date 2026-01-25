"""
DataExplorer Blueprint for main JustData app.
Converts the standalone DataExplorer app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, send_from_directory, Response
from jinja2 import ChoiceLoader, FileSystemLoader
import os
import json
import logging
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, get_user_type, login_required
from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from .config import TEMPLATES_DIR, STATIC_DIR
from .version import __version__
from .data_utils import validate_years, validate_geoids, lookup_lender
from .cache_utils import clear_cache
from .area_analysis_processor import (
    process_hmda_area_analysis, process_sb_area_analysis, process_branch_area_analysis
)
from .lender_analysis_processor import process_lender_analysis

# Get repo root for shared static files
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
dataexplorer_bp = Blueprint(
    'dataexplorer',
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='/static'
)


@dataexplorer_bp.record_once
def configure_template_loader(state):
    """Configure Jinja2 to search blueprint templates first.

    IMPORTANT: Blueprint templates must come FIRST in the ChoiceLoader so that
    app-specific templates are found before shared templates.

    NOTE: We do NOT add shared_loader here because the main app already includes
    shared templates. Adding it again would cause shared templates to be searched
    BEFORE other blueprint templates, leading to wrong template being rendered.
    """
    app = state.app
    blueprint_loader = FileSystemLoader(str(TEMPLATES_DIR))
    app.jinja_loader = ChoiceLoader([
        blueprint_loader,  # Blueprint templates first (highest priority)
        app.jinja_loader   # Main app loader (already includes shared templates)
    ])


@dataexplorer_bp.route('/')
@login_required
@require_access('dataexplorer', 'full')
def index():
    """Main DataExplorer page - renders wizard."""
    breadcrumb_items = [{'name': 'DataExplorer', 'url': '/dataexplorer'}]
    return render_template('wizard.html', version=__version__, app_name='DataExplorer', breadcrumb_items=breadcrumb_items)


@dataexplorer_bp.route('/dashboard')
@require_access('dataexplorer', 'full')
def dashboard():
    """Dashboard page."""
    breadcrumb_items = [
        {'name': 'DataExplorer', 'url': '/dataexplorer'},
        {'name': 'Dashboard', 'url': '/dataexplorer/dashboard'}
    ]
    return render_template('dashboard.html', version=__version__, app_name='DataExplorer', breadcrumb_items=breadcrumb_items)


@dataexplorer_bp.route('/wizard')
@require_access('dataexplorer', 'full')
def wizard():
    """Wizard page for guided analysis."""
    breadcrumb_items = [{'name': 'DataExplorer', 'url': '/dataexplorer'}]
    return render_template('wizard.html', version=__version__, app_name='DataExplorer', breadcrumb_items=breadcrumb_items)


@dataexplorer_bp.route('/api/states', methods=['GET'])
@require_access('dataexplorer', 'full')
def api_states():
    """Get list of states."""
    from .data_utils import get_states
    try:
        states = get_states()
        return jsonify({'success': True, 'states': states})
    except Exception as e:
        logger.error(f"Error getting states: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/metros', methods=['GET'])
@require_access('dataexplorer', 'full')
def api_metros():
    """Get list of metro areas."""
    from .data_utils import get_metros
    try:
        metros = get_metros()
        return jsonify({'success': True, 'metros': metros})
    except Exception as e:
        logger.error(f"Error getting metros: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/get-counties', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_get_counties():
    """Get counties for a state or metro."""
    from .data_utils import get_counties_for_state, get_counties_for_metro
    try:
        data = request.get_json()
        selection_type = data.get('type', 'state')

        if selection_type == 'state':
            state_fips = data.get('state_fips')
            counties = get_counties_for_state(state_fips)
        else:
            cbsa_code = data.get('cbsa_code')
            counties = get_counties_for_metro(cbsa_code)

        return jsonify({'success': True, 'counties': counties})
    except Exception as e:
        logger.error(f"Error getting counties: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/metros/<cbsa_code>/counties', methods=['GET'])
@require_access('dataexplorer', 'full')
def api_metros_counties(cbsa_code):
    """Get counties for a specific metro area (CBSA)."""
    from .data_utils import get_counties_for_metro
    try:
        counties = get_counties_for_metro(cbsa_code)
        return jsonify({'success': True, 'counties': counties})
    except Exception as e:
        logger.error(f"Error getting counties for metro {cbsa_code}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/area/hmda/analysis', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_hmda_analysis():
    """Run HMDA area analysis."""
    try:
        data = request.get_json()
        result = process_hmda_area_analysis(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in HMDA analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/area/sb/analysis', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_sb_analysis():
    """Run Small Business area analysis."""
    try:
        data = request.get_json()
        result = process_sb_area_analysis(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in SB analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/area/branches/analysis', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_branch_analysis():
    """Run Branch area analysis."""
    try:
        data = request.get_json()
        result = process_branch_area_analysis(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in Branch analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/lender/analysis', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_lender_analysis():
    """Run lender analysis."""
    try:
        data = request.get_json()
        result = process_lender_analysis(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in lender analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/lender/lookup', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_lender_lookup():
    """Lookup lender by name or LEI."""
    try:
        data = request.get_json()
        search_term = data.get('search_term', '')
        results = lookup_lender(search_term)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        logger.error(f"Error in lender lookup: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/lenders', methods=['GET'])
@require_access('dataexplorer', 'full')
def get_all_lenders():
    """Get all lenders from Lenders18 table."""
    try:
        from .data_utils import load_all_lenders18
        lenders = load_all_lenders18()
        logger.info(f"Returning {len(lenders)} lenders")
        return jsonify({
            'success': True,
            'lenders': lenders
        })
    except Exception as e:
        logger.error(f"Error loading lenders: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred loading lenders: {str(e)}'}), 500


@dataexplorer_bp.route('/api/lender/lookup-by-lei', methods=['POST'])
@require_access('dataexplorer', 'full')
def lookup_lender_by_lei():
    """Look up lender RSSD and SB_RESID by LEI."""
    try:
        data = request.get_json()
        lei = data.get('lei', '').strip()

        if not lei:
            return jsonify({'error': 'LEI is required'}), 400

        from .data_utils import get_lender_details_by_lei
        lender_info = get_lender_details_by_lei(lei)

        if lender_info:
            return jsonify({
                'success': True,
                'rssd': lender_info.get('rssd'),
                'sb_resid': lender_info.get('sb_resid'),
                'name': lender_info.get('name'),
                'type': lender_info.get('type')
            })
        else:
            return jsonify({
                'success': True,
                'rssd': None,
                'sb_resid': None,
                'message': 'Lender not found for this LEI'
            })
    except Exception as e:
        logger.error(f"Error looking up lender by LEI: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@dataexplorer_bp.route('/api/lender/gleif-data', methods=['POST'])
@require_access('dataexplorer', 'full')
def get_lender_gleif_data():
    """Get GLEIF data (legal/hq addresses, parent/child relationships) by LEI."""
    try:
        data = request.get_json()
        lei = data.get('lei', '').strip()

        if not lei:
            return jsonify({'error': 'LEI is required'}), 400

        from .data_utils import get_gleif_data_by_lei
        gleif_data = get_gleif_data_by_lei(lei)

        if gleif_data:
            return jsonify({
                'success': True,
                'data': gleif_data
            })
        else:
            return jsonify({
                'success': True,
                'data': None,
                'message': 'No GLEIF data found for this LEI'
            })
    except Exception as e:
        logger.error(f"Error fetching GLEIF data: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@dataexplorer_bp.route('/api/lender/verify-gleif', methods=['POST'])
@require_access('dataexplorer', 'full')
def verify_lender_gleif():
    """Verify lender with GLEIF API and return enriched data."""
    try:
        data = request.get_json()
        lei = data.get('lei', '').strip()

        if not lei:
            return jsonify({'error': 'LEI is required'}), 400

        from .data_utils import get_gleif_data_by_lei, verify_lender_with_external_sources

        # Get GLEIF data from our table
        gleif_data = get_gleif_data_by_lei(lei)

        # Also try external verification
        name = data.get('name', '')
        city = data.get('city', '')
        state = data.get('state', '')

        verification = None
        if name:
            try:
                verification = verify_lender_with_external_sources(lei, name, city, state)
            except Exception as e:
                logger.warning(f"External verification failed: {e}")

        return jsonify({
            'success': True,
            'gleif_data': gleif_data,
            'verification': verification
        })
    except Exception as e:
        logger.error(f"Error verifying GLEIF: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@dataexplorer_bp.route('/api/clear-cache', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_clear_cache():
    """Clear analysis cache."""
    try:
        clear_cache()
        return jsonify({'success': True, 'message': 'Cache cleared'})
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/generate-area-report', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_generate_area_report():
    """Generate area analysis report from wizard data."""
    import uuid
    import threading
    from justdata.shared.utils.progress_tracker import create_progress_tracker, store_analysis_result
    from justdata.apps.dataexplorer.core import run_area_analysis

    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Validate required fields
        geography = data.get('geography', {})
        counties = geography.get('counties', [])
        if not counties:
            return jsonify({'success': False, 'error': 'At least one county is required'}), 400

        # Create job ID
        job_id = str(uuid.uuid4())
        try:
            progress_tracker = create_progress_tracker(job_id)
            progress_tracker.update_progress('initializing', 0, 'Initializing area analysis...')
        except Exception as e:
            logger.error(f"Error creating progress tracker: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Failed to create progress tracker: {str(e)}',
                'error_type': type(e).__name__
            }), 500

        def run_job():
            try:
                result = run_area_analysis(
                    wizard_data=data,
                    job_id=job_id,
                    progress_tracker=progress_tracker
                )

                if result.get('success'):
                    store_analysis_result(job_id, result)
                    logger.info(f"Area analysis completed successfully for job {job_id}")
                else:
                    logger.error(f"Area analysis failed for job {job_id}: {result.get('error')}")
                    if progress_tracker:
                        progress_tracker.complete(success=False, error=result.get('error', 'Unknown error'))

            except Exception as e:
                logger.error(f"Error in area analysis job {job_id}: {e}", exc_info=True)
                if progress_tracker:
                    progress_tracker.complete(success=False, error=str(e))

        threading.Thread(target=run_job, daemon=True).start()
        return jsonify({'success': True, 'report_id': job_id})

    except Exception as e:
        logger.error(f"Error in generate area report: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


@dataexplorer_bp.route('/api/generate-lender-report', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_generate_lender_report():
    """Generate lender analysis report from wizard data."""
    import uuid
    import threading
    from justdata.shared.utils.progress_tracker import create_progress_tracker, store_analysis_result
    from justdata.apps.dataexplorer.lender_analysis_core import run_lender_analysis

    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Validate required fields
        lender = data.get('lender', {})
        if not lender.get('lei'):
            return jsonify({'success': False, 'error': 'Lender LEI is required'}), 400

        # Create job ID
        job_id = str(uuid.uuid4())
        try:
            progress_tracker = create_progress_tracker(job_id)
            progress_tracker.update_progress('initializing', 0, 'Initializing lender analysis...')
        except Exception as e:
            logger.error(f"Error creating progress tracker: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Failed to create progress tracker: {str(e)}',
                'error_type': type(e).__name__
            }), 500

        def run_job():
            try:
                result = run_lender_analysis(
                    wizard_data=data,
                    job_id=job_id,
                    progress_tracker=progress_tracker
                )

                if result.get('success'):
                    logger.info(f"Lender analysis completed successfully for job {job_id}")
                else:
                    logger.error(f"Lender analysis failed for job {job_id}: {result.get('error')}")

            except Exception as e:
                logger.error(f"Error in lender analysis job {job_id}: {e}", exc_info=True)
                if progress_tracker:
                    progress_tracker.complete(success=False, error=str(e))

        threading.Thread(target=run_job, daemon=True).start()
        return jsonify({'success': True, 'report_id': job_id})

    except Exception as e:
        logger.error(f"Error in generate lender report: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


@dataexplorer_bp.route('/progress/<job_id>', methods=['GET'])
def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events."""
    from justdata.shared.utils.progress_tracker import get_progress
    import time
    import sys

    def event_stream():
        last_percent = -1
        last_step = ""
        keepalive_counter = 0
        max_keepalive = 4
        max_iterations = 3600
        iteration_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 10

        try:
            # Send initial progress data
            try:
                initial_progress = get_progress(job_id)
                if not initial_progress:
                    initial_progress = {'percent': 0, 'step': 'Processing...', 'done': False, 'error': None}

                percent = initial_progress.get("percent", 0)
                step = initial_progress.get("step", "Processing...")
                done = initial_progress.get("done", False)
                error = initial_progress.get("error", None)

                try:
                    step_escaped = step.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                except:
                    step_escaped = "Processing..."

                initial_message = f"data: {{\"percent\": {percent}, \"step\": \"{step_escaped}\", \"done\": {str(done).lower()}, \"error\": {json.dumps(error) if error else 'null'}}}\n\n"
                yield initial_message
                sys.stdout.flush()

                last_percent = percent
                last_step = step
            except Exception as e:
                logger.error(f"Error sending initial progress: {e}")
                yield f"data: {{\"percent\": 0, \"step\": \"Processing...\", \"done\": false, \"error\": null}}\n\n"
                sys.stdout.flush()

            while iteration_count < max_iterations:
                try:
                    iteration_count += 1

                    try:
                        progress = get_progress(job_id)
                        if not progress:
                            progress = {'percent': max(0, last_percent), 'step': 'Processing...', 'done': False, 'error': None}
                        consecutive_errors = 0
                    except Exception as e:
                        consecutive_errors += 1
                        progress = {'percent': max(0, last_percent), 'step': 'Processing...', 'done': False, 'error': None}
                        if consecutive_errors >= max_consecutive_errors:
                            yield f"data: {{\"percent\": {max(0, last_percent)}, \"step\": \"Connection issue - please refresh\", \"done\": false, \"error\": null}}\n\n"
                            break

                    percent = progress.get("percent", 0)
                    step = progress.get("step", "Processing...")
                    done = progress.get("done", False)
                    error = progress.get("error", None)

                    if percent != last_percent or step != last_step or done:
                        try:
                            step_escaped = step.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                        except:
                            step_escaped = "Processing..."

                        message = f"data: {{\"percent\": {percent}, \"step\": \"{step_escaped}\", \"done\": {str(done).lower()}, \"error\": {json.dumps(error) if error else 'null'}}}\n\n"
                        yield message
                        sys.stdout.flush()

                        last_percent = percent
                        last_step = step

                        if done:
                            break
                    else:
                        keepalive_counter += 1
                        if keepalive_counter >= max_keepalive:
                            yield ": keepalive\n\n"
                            sys.stdout.flush()
                            keepalive_counter = 0

                    time.sleep(0.5)

                except GeneratorExit:
                    break
                except Exception as e:
                    logger.error(f"Error in progress stream: {e}")
                    time.sleep(1)

        except GeneratorExit:
            pass

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@dataexplorer_bp.route('/report/<job_id>', methods=['GET'])
@require_access('dataexplorer', 'full')
def show_report(job_id):
    """Display the analysis report (area or lender)."""
    from justdata.shared.utils.progress_tracker import get_analysis_result, get_progress

    try:
        result = get_analysis_result(job_id)

        if not result:
            progress = get_progress(job_id)
            if progress and not progress.get('done', False):
                return render_template('area_report_progress.html',
                                     job_id=job_id,
                                     version=__version__)

            return f"""
            <html><body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2>Report Not Found</h2>
                <p>Report not found. The analysis may still be running or may have expired.</p>
                <p>Job ID: {job_id}</p>
                <a href="/">Return to Home</a>
            </body></html>
            """, 404

        if not result.get('success'):
            return render_template('error_template.html',
                                 error=result.get('error', 'Unknown error'),
                                 job_id=job_id), 500

        metadata = result.get('metadata', {})
        report_data = result.get('report_data', {})

        if metadata.get('lender'):
            breadcrumb_items = [
                {'name': 'DataExplorer', 'url': '/dataexplorer'},
                {'name': 'Lender Analysis', 'url': f'/dataexplorer/report/{job_id}'}
            ]
            return render_template('lender_report_template.html',
                                 report_data=report_data,
                                 metadata=metadata,
                                 version=__version__,
                                 app_name='DataExplorer',
                                 breadcrumb_items=breadcrumb_items)
        else:
            breadcrumb_items = [
                {'name': 'DataExplorer', 'url': '/dataexplorer'},
                {'name': 'Area Analysis', 'url': f'/dataexplorer/report/{job_id}'}
            ]
            historical_census_data = result.get('historical_census_data', {})
            return render_template('area_report_template.html',
                                 report_data=report_data,
                                 metadata=metadata,
                                 census_data=result.get('census_data', {}),
                                 historical_census_data=historical_census_data,
                                 version=__version__,
                                 app_name='DataExplorer',
                                 breadcrumb_items=breadcrumb_items)

    except Exception as e:
        logger.error(f"Error displaying report {job_id}: {e}", exc_info=True)
        return f"""
        <html><body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2>Error</h2>
            <p>An error occurred displaying the report: {str(e)}</p>
            <a href="/">Return to Home</a>
        </body></html>
        """, 500


@dataexplorer_bp.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'app': 'dataexplorer',
        'version': __version__
    })
