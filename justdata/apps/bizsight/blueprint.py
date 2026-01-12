"""
BizSight Blueprint for main JustData app.
Converts the standalone BizSight app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, session, Response, send_file, make_response, url_for
from jinja2 import ChoiceLoader, FileSystemLoader
import os
import sys
import uuid
import threading
import time
import json
from pathlib import Path
from datetime import datetime

from justdata.main.auth import require_access, get_user_permissions, get_user_type
from justdata.shared.utils.analysis_cache import get_cached_result, store_cached_result, log_usage, generate_cache_key, get_analysis_result_by_job_id
from justdata.apps.bizsight.config import BizSightConfig, TEMPLATES_DIR_STR, STATIC_DIR_STR
from justdata.apps.bizsight.core import run_analysis
from justdata.apps.bizsight.data_utils import get_available_counties, get_available_years
from justdata.apps.bizsight.utils.progress_tracker import (
    get_progress, update_progress, create_progress_tracker
)

# Get shared templates directory
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# Create blueprint
bizsight_bp = Blueprint(
    'bizsight',
    __name__,
    template_folder=TEMPLATES_DIR_STR,
    static_folder=STATIC_DIR_STR,
    static_url_path='/bizsight/static'
)


@bizsight_bp.record_once
def configure_template_loader(state):
    """Configure Jinja2 to search both blueprint templates and shared templates."""
    app = state.app
    blueprint_loader = FileSystemLoader(TEMPLATES_DIR_STR)
    shared_loader = FileSystemLoader(str(SHARED_TEMPLATES_DIR))
    app.jinja_loader = ChoiceLoader([
        app.jinja_loader,
        blueprint_loader,
        shared_loader
    ])


@bizsight_bp.route('/')
@require_access('bizsight', 'partial')
def index():
    """Main page with the US map for county selection."""
    user_permissions = get_user_permissions()
    app_base_url = url_for('bizsight.index').rstrip('/')
    
    # Force template reload by clearing cache before rendering
    response = make_response(render_template(
        'bizsight_analysis.html', 
        version=BizSightConfig.APP_VERSION,
        permissions=user_permissions,
        app_base_url=app_base_url
    ))
    # Add aggressive cache-busting headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    import time
    response.headers['ETag'] = f'"{int(time.time())}"'
    response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response


@bizsight_bp.route('/progress/<job_id>')
def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events."""
    def event_stream():
        last_percent = -1
        while True:
            try:
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
            except Exception as e:
                yield f"data: {{\"percent\": 0, \"step\": \"Error: {str(e)}\", \"done\": true, \"error\": \"{str(e)}\"}}\n\n"
                break
    
    return Response(event_stream(), mimetype="text/event-stream")


@bizsight_bp.route('/analyze', methods=['POST'])
@require_access('bizsight', 'partial')
def analyze():
    """Handle analysis request with caching."""
    import time as time_module
    start_time = time_module.time()
    request_id = str(uuid.uuid4())
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        # Get county selection
        county_data = data.get('county_data')
        if not county_data:
            return jsonify({'success': False, 'error': 'Please select a county'}), 400
        
        # Check user permissions for geographic limits
        user_permissions = get_user_permissions()
        geographic_limit = user_permissions.get('geographic_limit', 'unlimited')
        
        # Enforce geographic limits
        if isinstance(county_data, list):
            if geographic_limit == 'own_county_only' and len(county_data) > 1:
                return jsonify({
                    'success': False,
                    'error': 'Your account type allows analysis of only one county at a time. Please select a single county.'
                }), 403
        
        # Get year range - if not provided, automatically use last 5 years
        start_year = data.get('startYear')
        end_year = data.get('endYear')
        
        if not start_year or not end_year:
            # Automatically get last 5 years from SB disclosure data
            from justdata.apps.bizsight.data_utils import get_last_5_years_sb
            years_list = get_last_5_years_sb()
            if years_list:
                start_year = min(years_list)
                end_year = max(years_list)
                years = sorted(years_list)
                years_str = ','.join(map(str, years))
                print(f"✅ Automatically using last 5 SB disclosure years: {years}")
            else:
                # Fallback
                years = list(range(2020, 2025))
                start_year = 2020
                end_year = 2024
                years_str = ','.join(map(str, years))
        else:
            start_year = int(start_year)
            end_year = int(end_year)
            
            # Validate year range
            from justdata.apps.bizsight.data_utils import validate_year_range
            is_valid, error_msg = validate_year_range(start_year, end_year)
            if not is_valid:
                return jsonify({'success': False, 'error': error_msg}), 400
            
            # Build years string
            years = list(range(start_year, end_year + 1))
            years_str = ','.join(map(str, years))
        
        # Get user type for logging
        user_type = get_user_type()
        
        # Prepare parameters for cache lookup
        cache_params = {
            'county_data': county_data,
            'startYear': start_year,
            'endYear': end_year,
            'years': years_str
        }
        
        # Check cache first
        cached_result = get_cached_result('bizsight', cache_params, user_type)
        
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
            
            # Store in session
            session['county_data'] = county_data
            session['years'] = years_str
            session['job_id'] = job_id
            
            # Log usage (cache hit)
            response_time_ms = int((time_module.time() - start_time) * 1000)
            cache_key = cached_result['cache_key']
            log_usage(
                user_type=user_type,
                app_name='bizsight',
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
                'cached': True
            })
        
        # Cache miss - run new analysis
        job_id = str(uuid.uuid4())
        
        # Create progress tracker
        progress_tracker = create_progress_tracker(job_id)
        
        # Store in session
        session['county_data'] = county_data
        session['years'] = years_str
        session['job_id'] = job_id
        
        def run_job():
            try:
                result = run_analysis(
                    county_data,
                    years_str,
                    job_id,
                    progress_tracker
                )
                
                if not result.get('success'):
                    error_msg = result.get('error', 'Unknown error')
                    progress_tracker.complete(success=False, error=error_msg)
                    
                    # Log failed request
                    response_time_ms = int((time_module.time() - start_time) * 1000)
                    cache_key = generate_cache_key('bizsight', cache_params)
                    log_usage(
                        user_type=user_type,
                        app_name='bizsight',
                        params=cache_params,
                        cache_key=cache_key,
                        cache_hit=False,
                        job_id=job_id,
                        response_time_ms=response_time_ms,
                        error_message=error_msg,
                        request_id=request_id
                    )
                    return
                
                # Store in BigQuery only (no in-memory storage)
                # store_cached_result stores everything in BigQuery
                progress_tracker.complete(success=True)
                
                # Store in BigQuery cache
                try:
                    metadata = {
                        'counties': [county_data] if not isinstance(county_data, list) else county_data,
                        'years': years,
                        'duration_seconds': time_module.time() - start_time
                    }
                    
                    store_cached_result(
                        app_name='bizsight',
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
                cache_key = generate_cache_key('bizsight', cache_params)
                log_usage(
                    user_type=user_type,
                    app_name='bizsight',
                    params=cache_params,
                    cache_key=cache_key,
                    cache_hit=False,
                    job_id=job_id,
                    response_time_ms=response_time_ms,
                    costs={'bigquery': 2.0, 'ai': 0.3, 'total': 2.3},  # Estimated costs
                    request_id=request_id
                )
                
            except Exception as e:
                error_msg = str(e)
                progress_tracker.complete(success=False, error=error_msg)
                
                # Log failed request
                response_time_ms = int((time_module.time() - start_time) * 1000)
                cache_key = generate_cache_key('bizsight', cache_params)
                log_usage(
                    user_type=user_type,
                    app_name='bizsight',
                    params=cache_params,
                    cache_key=cache_key,
                    cache_hit=False,
                    job_id=job_id,
                    response_time_ms=response_time_ms,
                    error_message=error_msg,
                    request_id=request_id
                )
        
        # Start background job
        threading.Thread(target=run_job, daemon=True).start()
        
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        # Log error
        response_time_ms = int((time_module.time() - start_time) * 1000)
        try:
            log_usage(
                user_type=get_user_type(),
                app_name='bizsight',
                params=cache_params if 'cache_params' in locals() else {},
                cache_key=generate_cache_key('bizsight', cache_params) if 'cache_params' in locals() else '',
                cache_hit=False,
                job_id=job_id if 'job_id' in locals() else str(uuid.uuid4()),
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_id=request_id
            )
        except:
            pass
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500


@bizsight_bp.route('/data', methods=['GET'])
def data():
    """Return data for the application (counties, years)."""
    try:
        counties = get_available_counties()
        years = get_available_years()
        
        return jsonify({
            'counties': counties,
            'years': years
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bizsight_bp.route('/api/states', methods=['GET'])
def get_states():
    """Get list of available states."""
    try:
        from justdata.apps.bizsight.data_utils import get_available_states
        states = get_available_states()
        return jsonify(states)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bizsight_bp.route('/api/counties-by-state/<state_code>', methods=['GET'])
def get_counties_by_state(state_code):
    """Get counties for a specific state."""
    try:
        counties = get_available_counties(state_code=state_code)
        return jsonify(counties)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bizsight_bp.route('/api/county-boundaries', methods=['GET'])
def get_county_boundaries():
    """Get county boundaries for mapping."""
    try:
        from justdata.apps.bizsight.utils.tract_boundaries import get_county_boundaries
        geoid5 = request.args.get('geoid5')
        if not geoid5:
            return jsonify({'error': 'geoid5 parameter required'}), 400
        boundaries = get_county_boundaries(geoid5)
        return jsonify(boundaries)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bizsight_bp.route('/api/state-boundaries', methods=['GET'])
def get_state_boundaries():
    """Get state boundaries for mapping."""
    try:
        from justdata.apps.bizsight.utils.tract_boundaries import get_state_boundaries
        state_code = request.args.get('state_code')
        if not state_code:
            return jsonify({'error': 'state_code parameter required'}), 400
        boundaries = get_state_boundaries(state_code)
        return jsonify(boundaries)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bizsight_bp.route('/api/tract-boundaries/<geoid5>', methods=['GET'])
def get_tract_boundaries(geoid5):
    """Get census tract boundaries for a county."""
    try:
        from justdata.apps.bizsight.utils.tract_boundaries import get_tract_boundaries
        boundaries = get_tract_boundaries(geoid5)
        return jsonify(boundaries)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bizsight_bp.route('/report', methods=['GET'])
@require_access('bizsight', 'partial')
def report():
    """Report display page."""
    job_id = request.args.get('job_id')
    if not job_id:
        return jsonify({'error': 'Job ID required'}), 400
    
    return render_template('report_template.html', job_id=job_id)


@bizsight_bp.route('/report-data', methods=['GET'])
@require_access('bizsight', 'partial')
def report_data():
    """Get report data for a job."""
    try:
        job_id = request.args.get('job_id')
        if not job_id:
            return jsonify({'error': 'Job ID required'}), 400
        
        # Retrieve from BigQuery only (no in-memory storage)
        result = get_analysis_result_by_job_id(job_id)
        if not result:
            return jsonify({'error': 'Report not found'}), 404
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bizsight_bp.route('/download', methods=['GET'])
@require_access('bizsight', 'partial')
def download():
    """Download analysis results."""
    try:
        job_id = request.args.get('job_id')
        format_type = request.args.get('format', 'excel')  # excel, pdf, powerpoint
        
        if not job_id:
            return jsonify({'error': 'Job ID required'}), 400
        
        # Check user permissions for export
        user_permissions = get_user_permissions()
        if not user_permissions.get('can_export', False):
            return jsonify({
                'error': 'Export functionality is not available for your account type.'
            }), 403
        
        # Check if format is allowed
        allowed_formats = user_permissions.get('export_formats', [])
        if format_type not in allowed_formats:
            return jsonify({
                'error': f'Export format "{format_type}" is not available for your account type.'
            }), 403
        
        progress = get_progress(job_id)
        if not progress.get('done'):
            return jsonify({'error': 'Analysis not complete'}), 400
        
        # Retrieve from BigQuery only (no in-memory storage)
        result = get_analysis_result_by_job_id(job_id)
        if not result:
            return jsonify({'error': 'Result not found'}), 404
        
        # Get metadata
        metadata = {
            'county_data': session.get('county_data'),
            'years': session.get('years'),
            'job_id': job_id
        }
        
        # Download based on format
        if format_type == 'excel':
            from justdata.apps.bizsight.excel_export import download_excel
            return download_excel(result, metadata)
        elif format_type == 'pdf':
            from justdata.apps.bizsight.app import download_pdf_report
            return download_pdf_report(result, metadata, job_id)
        elif format_type == 'powerpoint':
            # PowerPoint export would go here
            return jsonify({'error': 'PowerPoint export not yet implemented'}), 501
        else:
            return jsonify({'error': f'Unknown format: {format_type}'}), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bizsight_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'bizsight',
        'version': BizSightConfig.APP_VERSION
    })

