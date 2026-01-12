#!/usr/bin/env python3
"""
LenderProfile Flask Application
Comprehensive lender intelligence reporting platform.
"""

from flask import render_template, request, jsonify, send_from_directory
import os
import json
import logging
from pathlib import Path
from werkzeug.middleware.proxy_fix import ProxyFix

from shared.web.app_factory import create_app, register_standard_routes
from shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from apps.lenderprofile.config import TEMPLATES_DIR, STATIC_DIR
from apps.lenderprofile.version import __version__
from apps.lenderprofile.processors.identifier_resolver import IdentifierResolver
from apps.lenderprofile.processors.data_collector import DataCollector
from apps.lenderprofile.report_builder.report_builder import ReportBuilder

# Get repo root for shared static files
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()

# Load unified environment configuration
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)

# Configure logging - both console and file
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'lenderprofile.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file}")

# Create the Flask app
app = create_app(
    'lenderprofile',
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR)
)

# Add ProxyFix for proper request handling behind Render's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Configure cache-busting
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.jinja_env.bytecode_cache = None

# Log all registered routes on startup (moved to end of file)


@app.before_request
def log_request():
    """Log all incoming requests for debugging."""
    logger.info(f"=== INCOMING REQUEST ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"Path: {request.path}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Endpoint: {request.endpoint if hasattr(request, 'endpoint') else 'N/A'}")
    logger.info(f"========================")


@app.before_request
def clear_template_cache():
    """Clear Jinja2 template cache before each request."""
    if hasattr(app, 'jinja_env'):
        app.jinja_env.bytecode_cache = None
        app.jinja_env.cache = {}
        app.jinja_env.auto_reload = True


# Serve shared logo
@app.route('/static/img/ncrc-logo.png')
def serve_shared_logo():
    """Serve the shared NCRC logo."""
    shared_logo_path = REPO_ROOT / 'shared' / 'web' / 'static' / 'img' / 'ncrc-logo.png'
    if shared_logo_path.exists():
        return send_from_directory(str(shared_logo_path.parent), shared_logo_path.name)
    return send_from_directory(app.static_folder, 'img/ncrc-logo.png'), 404


@app.route('/')
def index():
    """Main search interface."""
    logger.info("Index page requested")
    return render_template('index.html', version=__version__)


@app.route('/api/test')
def test_api():
    """Test endpoint to verify API is working."""
    logger.info("Test API endpoint hit!")
    return jsonify({'status': 'ok', 'message': 'API is working'})


@app.route('/test-route')
def test_route():
    """Simple test route without /api prefix."""
    return jsonify({'status': 'ok', 'message': 'Test route works', 'all_routes': [str(r) for r in app.url_map.iter_rules()]})


@app.route('/report/<report_id>')
def view_report(report_id: str):
    """View a generated report or show progress if still generating."""
    from shared.utils.progress_tracker import get_analysis_result, get_progress
    
    try:
        result = get_analysis_result(report_id)
        
        if not result:
            # Check if job is still in progress
            progress = get_progress(report_id)
            if progress and not progress.get('done', False):
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
            return render_template('error_template.html',
                                 error=result.get('error', 'Unknown error'),
                                 job_id=report_id), 500
        
        # Report is ready - display it using the new v2 template
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


@app.route('/progress/<job_id>', methods=['GET'])
def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events."""
    from flask import Response
    from shared.utils.progress_tracker import get_progress
    import time
    import json
    import sys
    
    def event_stream():
        last_percent = -1
        last_step = ""
        keepalive_counter = 0
        max_keepalive = 4  # Send keepalive every 2 seconds (4 * 0.5s)
        max_iterations = 3600  # Max 30 minutes
        iteration_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        try:
            # Send initial progress data immediately
            try:
                initial_progress = get_progress(job_id)
                if initial_progress:
                    percent = initial_progress.get('percent', 0)
                    step = initial_progress.get('step', 'Initializing...')
                    done = initial_progress.get('done', False)
                    error = initial_progress.get('error')
                    
                    step_escaped = step.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                    message = f"data: {{\"percent\": {percent}, \"step\": \"{step_escaped}\", \"done\": {str(done).lower()}, \"error\": {json.dumps(error) if error else 'null'}}}\n\n"
                    yield message
                    sys.stdout.flush()
                    
                    last_percent = percent
                    last_step = step
                    
                    if done or error:
                        return
            except Exception as e:
                logger.warning(f"Error getting initial progress: {e}")
            
            # Poll for updates
            while iteration_count < max_iterations:
                time.sleep(0.5)  # Check every 0.5 seconds
                iteration_count += 1
                
                try:
                    progress = get_progress(job_id)
                    if not progress:
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            yield f"data: {{\"error\": \"Progress tracking lost\"}}\n\n"
                            break
                        continue
                    
                    consecutive_errors = 0
                    
                    percent = progress.get('percent', 0)
                    step = progress.get('step', 'Processing...')
                    done = progress.get('done', False)
                    error = progress.get('error')
                    
                    step_escaped = step.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                    
                    # Send update if changed, or send keepalive
                    if percent != last_percent or step != last_step or done or error:
                        message = f"data: {{\"percent\": {percent}, \"step\": \"{step_escaped}\", \"done\": {str(done).lower()}, \"error\": {json.dumps(error) if error else 'null'}}}\n\n"
                        yield message
                        sys.stdout.flush()
                        last_percent = percent
                        last_step = step
                        keepalive_counter = 0
                    elif keepalive_counter >= max_keepalive:
                        yield f": keepalive\n\n"
                        sys.stdout.flush()
                        keepalive_counter = 0
                    
                    if done or error:
                        time.sleep(0.1)
                        break
                    
                    keepalive_counter += 1
                    
                except Exception as e:
                    logger.error(f"Error in progress stream: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        yield f"data: {{\"error\": \"Progress tracking error\"}}\n\n"
                        break
                    time.sleep(1)
                    
        except GeneratorExit:
            logger.info(f"Progress stream closed for job {job_id}")
        except Exception as e:
            logger.error(f"Error in event_stream: {e}", exc_info=True)
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
    
    return Response(event_stream(), mimetype='text/event-stream')


# Health check is already provided by create_app/register_standard_routes
# No need to define it again


@app.route('/api/search-lender', methods=['POST'])
def search_lender():
    """Search for lenders by name using FDIC and identifier resolution."""
    logger.info("*** SEARCH_LENDER ROUTE HIT ***")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request path: {request.path}")
    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")
        query = data.get('query', '').strip()
        excluded_lenders = data.get('exclude', [])  # List of rejected lenders to exclude
        
        if not query or len(query) < 2:
            return jsonify({'error': 'Search query must be at least 2 characters'}), 400
        
        logger.info(f"Searching for lender: '{query}'")
        if excluded_lenders:
            logger.info(f"Excluding {len(excluded_lenders)} previously rejected lenders")
        
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
                'confidence': 1.0  # High confidence since user selected it
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
            
            fdic_data = details.get('fdic_data', {})
            assets = fdic_data.get('ASSET') if fdic_data else None
            logger.info(f"Resolved selected lender: {result.get('name')} (FDIC: {result.get('fdic_cert')}, LEI: {result.get('lei')})")
            return jsonify(result)
        
        # Resolve identifiers - get multiple candidates
        try:
            resolver = IdentifierResolver()
            # Get multiple candidates with location info
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
            
            fdic_data = details.get('fdic_data', {})
            assets = fdic_data.get('ASSET') if fdic_data else None
            logger.info(f"Found single lender: {result.get('name')} (FDIC: {result.get('fdic_cert')}, LEI: {result.get('lei')})")
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
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'An error occurred searching lenders: {str(e)}'}), 500


@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    """Generate a comprehensive lender intelligence report with progress tracking."""
    try:
        import uuid
        import threading
        from shared.utils.progress_tracker import create_progress_tracker, store_analysis_result
        
        data = request.get_json()
        institution_name = data.get('name', '').strip()
        institution_id = data.get('id')  # FDIC cert, RSSD, LEI, etc.
        identifiers = data.get('identifiers', {})
        report_focus = data.get('report_focus', '').strip()  # Optional focus field

        if not institution_name and not institution_id:
            return jsonify({'error': 'Institution name or ID is required'}), 400

        # If institution_id provided but identifiers is empty, try to use it
        if institution_id and not identifiers:
            institution_id = str(institution_id).strip()
            # Detect ID type and populate identifiers
            if len(institution_id) == 20 and institution_id.isalnum():
                # LEI is 20 alphanumeric characters
                identifiers = {'lei': institution_id}
                logger.info(f"Using provided ID as LEI: {institution_id}")
            elif institution_id.isdigit():
                # Numeric ID - could be RSSD or FDIC CERT
                # RSSD IDs are typically 6-10 digits, FDIC CERTs are typically 3-6 digits
                # Use as RSSD since that's more commonly used for branch data
                identifiers = {'rssd_id': institution_id}
                logger.info(f"Using provided ID as RSSD: {institution_id}")
            else:
                # Try as generic ID
                identifiers = {'id': institution_id}
                logger.info(f"Using provided ID as generic: {institution_id}")
        
        # Validate report focus length
        if report_focus and len(report_focus) > 250:
            return jsonify({'error': 'Report focus must be 250 characters or less'}), 400
        
        # Create job ID
        job_id = str(uuid.uuid4())
        
        try:
            progress_tracker = create_progress_tracker(job_id)
            progress_tracker.update_progress('initializing', 0, 'Initializing lender intelligence report...')
        except Exception as e:
            logger.error(f"Error creating progress tracker: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Failed to create progress tracker: {str(e)}'
            }), 500
        
        def run_job():
            """Run report generation in background thread."""
            try:
                # Update progress
                progress_tracker.update_progress('parsing_params', 5, 'Preparing analysis...')

                # CRITICAL: Resolve LEI if not provided - required for HMDA and GLEIF lookups
                nonlocal identifiers
                if not identifiers.get('lei'):
                    logger.info(f"No LEI provided, resolving from name: {institution_name}")
                    try:
                        resolver = IdentifierResolver()
                        candidates = resolver.get_candidates_with_location(institution_name, limit=1)
                        if candidates and candidates[0].get('lei'):
                            identifiers['lei'] = candidates[0]['lei']
                            logger.info(f"Resolved LEI: {identifiers['lei']}")
                            # Also fill in other identifiers if missing
                            if not identifiers.get('rssd_id') and candidates[0].get('rssd_id'):
                                identifiers['rssd_id'] = candidates[0]['rssd_id']
                            if not identifiers.get('fdic_cert') and candidates[0].get('fdic_cert'):
                                identifiers['fdic_cert'] = candidates[0]['fdic_cert']
                        else:
                            logger.warning(f"Could not resolve LEI for {institution_name}")
                    except Exception as e:
                        logger.error(f"Error resolving LEI: {e}")

                # Collect all data from APIs
                logger.info(f"Starting data collection for {institution_name}")
                logger.info(f"Using identifiers: LEI={identifiers.get('lei')}, RSSD={identifiers.get('rssd_id')}, FDIC={identifiers.get('fdic_cert')}")
                progress_tracker.update_progress('preparing_data', 15, 'Collecting data from regulatory sources...')
                
                collector = DataCollector()
                institution_data = collector.collect_all_data(identifiers, institution_name)
                
                # Build complete report
                logger.info(f"Building report for {institution_name}")
                progress_tracker.update_progress('building_report', 60, 'Building report sections...')
                
                report_builder = ReportBuilder(report_focus=report_focus if report_focus else None)
                report = report_builder.build_complete_report(institution_data, progress_tracker=progress_tracker)
                
                progress_tracker.update_progress('finalizing', 95, 'Finalizing report...')
                
                # Store report result
                store_analysis_result(job_id, {
                    'success': True,
                    'report': report,
                    'institution': institution_name,
                    'metadata': {
                        'institution_name': institution_name,
                        'generated_at': report.get('metadata', {}).get('generated_at'),
                        'report_focus': report_focus
                    }
                })
                
                progress_tracker.complete(success=True)
                logger.info(f"Report generation completed for {institution_name}")
                
            except Exception as e:
                logger.error(f"Error in report generation job: {e}", exc_info=True)
                progress_tracker.complete(success=False, error=str(e))
                store_analysis_result(job_id, {
                    'success': False,
                    'error': str(e)
                })
        
        # Start job in background thread
        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'report_id': job_id,
            'institution': institution_name
        })
        
    except Exception as e:
        logger.error(f"Error in generate_report: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# Export application for gunicorn (required for Docker/production)
# This must be at the END after all routes are defined
application = app

# Log all registered routes on startup
logger.info("=" * 50)
logger.info("Registered routes:")
for rule in app.url_map.iter_rules():
    logger.info(f"  {rule.rule} -> {rule.endpoint} ({', '.join(rule.methods)})")
logger.info("=" * 50)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8086))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

