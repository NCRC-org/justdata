"""
BranchSeeker Blueprint for main JustData app.
Converts the standalone BranchSeeker app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, send_file, Response, session, url_for
from jinja2 import ChoiceLoader, FileSystemLoader
import os
import tempfile
import zipfile
from datetime import datetime
import uuid
import threading
import time
import json
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, get_user_type, login_required
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker
from justdata.shared.utils.analysis_cache import get_cached_result, store_cached_result, log_usage, generate_cache_key, get_analysis_result_by_job_id
from .config import TEMPLATES_DIR, STATIC_DIR, OUTPUT_DIR
from .data_utils import get_available_counties
from .core import run_analysis, parse_web_parameters
from .version import __version__

# Get shared templates directory
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# Create blueprint
branchseeker_bp = Blueprint(
    'branchseeker',
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/branchseeker/static'
)


@branchseeker_bp.record_once
def configure_template_loader(state):
    """Configure Jinja2 to search both blueprint templates and shared templates."""
    app = state.app
    blueprint_loader = FileSystemLoader(str(TEMPLATES_DIR))
    shared_loader = FileSystemLoader(str(SHARED_TEMPLATES_DIR))
    app.jinja_loader = ChoiceLoader([
        app.jinja_loader,
        blueprint_loader,
        shared_loader
    ])


@branchseeker_bp.route('/')
@login_required
@require_access('branchseeker', 'partial')
def index():
    """Main page with the analysis form"""
    user_permissions = get_user_permissions()
    user_type = get_user_type()
    is_staff = (user_type in ('staff', 'admin'))
    app_base_url = url_for('branchseeker.index').rstrip('/')
    return render_template('branchseeker_template.html',
                         version=__version__,
                         permissions=user_permissions,
                         is_staff=is_staff,
                         app_base_url=app_base_url)


@branchseeker_bp.route('/branch-mapper')
@require_access('branchseeker', 'partial')
def branch_mapper():
    """BranchMapper - Interactive map of bank branch locations"""
    return render_template('branch_mapper_template.html', version=__version__)


@branchseeker_bp.route('/report')
@require_access('branchseeker', 'partial')
def report():
    """Report display page"""
    return render_template('report_template.html', version=__version__)


@branchseeker_bp.route('/progress/<job_id>')
def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events"""
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


@branchseeker_bp.route('/analyze', methods=['POST'])
@require_access('branchseeker', 'partial')
def analyze():
    """Handle analysis request with caching"""
    import time as time_module
    start_time = time_module.time()
    request_id = str(uuid.uuid4())
    
    try:
        data = request.get_json()
        selection_type = data.get('selection_type', 'county')  # 'county', 'state', or 'metro'
        counties_str = data.get('counties', '').strip()
        years = data.get('years', '').strip()  # May be empty - will be auto-determined
        state_code = data.get('state_code', None)
        metro_code = data.get('metro_code', None)
        
        # Get user type for logging
        user_type = get_user_type()
        
        # Years will be automatically determined from last 5 years in parse_web_parameters
        # For cache key, use empty string if years not provided (will be normalized)
        cache_params = {
            'counties': counties_str,
            'years': years if years else 'auto',  # Use 'auto' to indicate automatic selection
            'selection_type': selection_type,
            'state_code': state_code,
            'metro_code': metro_code
        }
        
        # Check cache first
        cached_result = get_cached_result('branchseeker', cache_params, user_type)
        
        if cached_result:
            # Cache hit - use cached result
            job_id = cached_result['job_id']
            result_data = cached_result['result_data']
            
            # Result is already stored in BigQuery via store_cached_result
            # No need for in-memory storage - BigQuery-only approach
            update_progress(job_id, {
                'percent': 100,
                'step': 'Analysis complete (from cache)',
                'done': True,
                'cached': True
            })
            
            # Log usage (cache hit)
            response_time_ms = int((time_module.time() - start_time) * 1000)
            cache_key = cached_result['cache_key']
            log_usage(
                user_type=user_type,
                app_name='branchseeker',
                params=cache_params,
                cache_key=cache_key,
                cache_hit=True,
                job_id=job_id,
                response_time_ms=response_time_ms,
                costs={'bigquery': 0.01, 'ai': 0.0, 'total': 0.01},
                request_id=request_id
            )
            
            return jsonify({
                'success': True,
                'job_id': job_id,
                'message': 'Analysis complete (from cache)',
                'cached': True
            })
        
        # Cache miss - run new analysis
        job_id = str(uuid.uuid4())
        
        # Create progress tracker for this job
        progress_tracker = create_progress_tracker(job_id)
        
        # Validate inputs based on selection type
        if selection_type == 'state' and not state_code:
            return jsonify({'error': 'Please select a state'}), 400
        elif selection_type == 'metro' and not metro_code:
            return jsonify({'error': 'Please select a metro area'}), 400
        elif selection_type == 'county' and not counties_str:
            return jsonify({'error': 'Please provide counties'}), 400
        
        # Years are now automatically determined - no validation needed
        # Parse parameters (this will expand state/metro to counties if needed and get last 5 years)
        try:
            counties_list, years_list = parse_web_parameters(
                counties_str, years, selection_type, state_code, metro_code
            )
        except Exception as e:
            # Log failed request
            response_time_ms = int((time_module.time() - start_time) * 1000)
            cache_key = generate_cache_key('branchseeker', cache_params)
            log_usage(
                user_type=user_type,
                app_name='branchseeker',
                params=cache_params,
                cache_key=cache_key,
                cache_hit=False,
                job_id=job_id,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_id=request_id
            )
            return jsonify({'error': f'Error parsing parameters: {str(e)}'}), 400
        
        # Check user permissions for geographic limits
        user_permissions = get_user_permissions()
        geographic_limit = user_permissions.get('geographic_limit', 'unlimited')
        
        # Enforce geographic limits based on user type
        if geographic_limit == 'own_county_only':
            # For public/economy users, limit to single county
            if len(counties_list) > 1:
                return jsonify({
                    'error': 'Your account type allows analysis of only one county at a time. Please select a single county.'
                }), 403
        elif geographic_limit == 'multiple_counties':
            # Members and partners can select multiple counties
            pass  # No limit
        # 'unlimited' means no restrictions
        
        # Run analysis in background thread
        def run_analysis_thread():
            try:
                result = run_analysis(
                    counties_list, 
                    years_list, 
                    progress_tracker=progress_tracker,
                    job_id=job_id
                )
                
                # Store result in cache if successful
                if result.get('success'):
                    try:
                        # Extract metadata for cache storage
                        metadata = {
                            'counties': counties_list,
                            'years': years_list,
                            'duration_seconds': time_module.time() - start_time
                        }
                        
                        # Store in BigQuery cache
                        store_cached_result(
                            app_name='branchseeker',
                            params=cache_params,
                            job_id=job_id,
                            result_data=result,
                            user_type=user_type,
                            metadata=metadata
                        )
                    except Exception as cache_error:
                        print(f"Warning: Failed to store in cache: {cache_error}")
                
                # Log usage (cache miss, new analysis)
                response_time_ms = int((time_module.time() - start_time) * 1000)
                cache_key = generate_cache_key('branchseeker', cache_params)
                log_usage(
                    user_type=user_type,
                    app_name='branchseeker',
                    params=cache_params,
                    cache_key=cache_key,
                    cache_hit=False,
                    job_id=job_id,
                    response_time_ms=response_time_ms,
                    costs={'bigquery': 2.0, 'ai': 0.3, 'total': 2.3},  # Estimated costs
                    request_id=request_id
                )
                
            except Exception as e:
                update_progress(job_id, {
                    'percent': 100,
                    'step': f'Error: {str(e)}',
                    'done': True,
                    'error': str(e)
                })
                
                # Log failed request
                response_time_ms = int((time_module.time() - start_time) * 1000)
                cache_key = generate_cache_key('branchseeker', cache_params)
                log_usage(
                    user_type=user_type,
                    app_name='branchseeker',
                    params=cache_params,
                    cache_key=cache_key,
                    cache_hit=False,
                    job_id=job_id,
                    response_time_ms=response_time_ms,
                    error_message=str(e),
                    request_id=request_id
                )
        
        thread = threading.Thread(target=run_analysis_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Analysis started'
        })
        
    except Exception as e:
        # Log error
        response_time_ms = int((time_module.time() - start_time) * 1000)
        try:
            log_usage(
                user_type=get_user_type(),
                app_name='branchseeker',
                params=cache_params if 'cache_params' in locals() else {},
                cache_key=generate_cache_key('branchseeker', cache_params) if 'cache_params' in locals() else '',
                cache_hit=False,
                job_id=job_id if 'job_id' in locals() else str(uuid.uuid4()),
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_id=request_id
            )
        except:
            pass
        return jsonify({'error': str(e)}), 500


@branchseeker_bp.route('/download')
@require_access('branchseeker', 'partial')
def download():
    """Download analysis results"""
    try:
        job_id = request.args.get('job_id')
        if not job_id:
            return jsonify({'error': 'Job ID required'}), 400
        
        progress = get_progress(job_id)
        if not progress.get('done'):
            return jsonify({'error': 'Analysis not complete'}), 400
        
        result_path = progress.get('result_path')
        if not result_path or not os.path.exists(result_path):
            return jsonify({'error': 'Result file not found'}), 404
        
        # Check if user has export permission
        user_permissions = get_user_permissions()
        if not user_permissions.get('can_export', False):
            return jsonify({
                'error': 'Export functionality is not available for your account type.'
            }), 403
        
        return send_file(
            result_path,
            as_attachment=True,
            download_name=f'branchseeker_report_{job_id}.zip'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@branchseeker_bp.route('/counties')
def counties():
    """Return a list of all available counties"""
    try:
        counties_list = get_available_counties()
        return jsonify(counties_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@branchseeker_bp.route('/states')
def states():
    """Return a list of all available states"""
    try:
        from .data_utils import get_available_states
        states_list = get_available_states()
        return jsonify(states_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@branchseeker_bp.route('/metro-areas')
def metro_areas():
    """Return a list of all available metro areas (CBSAs)"""
    try:
        from .data_utils import get_available_metro_areas
        metros_list = get_available_metro_areas()
        return jsonify(metros_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@branchseeker_bp.route('/counties-by-state/<state_code>')
def counties_by_state(state_code):
    """Return a list of counties for a specific state"""
    try:
        from .data_utils import expand_state_to_counties
        counties_list = expand_state_to_counties(state_code)
        return jsonify(counties_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@branchseeker_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'branchseeker',
        'version': __version__
    })

