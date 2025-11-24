"""
LendSight Blueprint for main JustData app.
Converts the standalone LendSight app into a blueprint with cache integration.
"""

from flask import Blueprint, render_template, request, jsonify, session, Response, make_response, send_file, url_for
import os
import tempfile
import uuid
import threading
import time
import json
from datetime import datetime

from justdata.main.auth import require_access, get_user_permissions, get_user_type
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker, store_analysis_result, get_analysis_result
from justdata.shared.utils.analysis_cache import get_cached_result, store_cached_result, log_usage, generate_cache_key
from justdata.core.config.app_config import LendSightConfig
from .core import run_analysis, parse_web_parameters

# Template and static directories (shared)
TEMPLATES_DIR = os.path.join(LendSightConfig.BASE_DIR, 'shared', 'web', 'templates')
STATIC_DIR = os.path.join(LendSightConfig.BASE_DIR, 'shared', 'web', 'static')

# Create blueprint
lendsight_bp = Blueprint(
    'lendsight',
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/lendsight/static'
)


@lendsight_bp.route('/')
@require_access('lendsight', 'partial')
def index():
    """Main page with the analysis form"""
    user_permissions = get_user_permissions()
    cache_buster = int(time.time())  # Timestamp for cache-busting
    # Set base URL for JavaScript API calls
    app_base_url = url_for('lendsight.index').rstrip('/')
    response = make_response(render_template('lendsight_template.html', 
                                           permissions=user_permissions, 
                                           cache_buster=cache_buster,
                                           app_base_url=app_base_url))
    # Add cache-busting headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@lendsight_bp.route('/progress/<job_id>')
def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events"""
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


@lendsight_bp.route('/analyze', methods=['POST'])
@require_access('lendsight', 'partial')
def analyze():
    """Handle analysis request with caching"""
    import time as time_module
    start_time = time_module.time()
    request_id = str(uuid.uuid4())
    
    try:
        data = request.get_json()
        print(f"[DEBUG] analyze endpoint - received data: {data}")
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        selection_type = data.get('selection_type', 'county')  # Always 'county' now
        # Try to get counties_data (new format with FIPS codes) first, fallback to counties (old format)
        counties_data = data.get('counties_data', None)
        if not counties_data:
            # Old format: parse county names from string
            counties_data = data.get('counties', [])
        years = data.get('years', '').strip()
        state_code = data.get('state_code', None)
        loan_purpose = data.get('loan_purpose', ['purchase'])  # Default to purchase only
        
        # Get user type for logging
        user_type = get_user_type()
        
        # Parse counties - handle both new format (objects with FIPS) and old format (strings)
        counties_list = []
        counties_with_fips = []
        
        if isinstance(counties_data, list):
            for c in counties_data:
                if isinstance(c, dict) and c.get('name'):
                    # New format: county object with FIPS codes
                    counties_list.append(c['name'])  # Use name for backward compatibility
                    counties_with_fips.append(c)  # Store full object with FIPS codes
                elif isinstance(c, str):
                    # Old format: just county name string
                    counties_list.append(c.strip())
        else:
            # Handle string format (comma or semicolon separated)
            counties_str = str(counties_data).strip()
            if ',' in counties_str:
                counties_list = [c.strip() for c in counties_str.split(',') if c.strip()]
            else:
                counties_list = [c.strip() for c in counties_str.split(';') if c.strip()]
        
        # Remove duplicates (in case same county appears multiple times)
        counties_list = list(dict.fromkeys(counties_list))  # Preserves order while removing duplicates
        
        if len(counties_list) > 3:
            return jsonify({'success': False, 'error': f'Please select a maximum of 3 counties. You selected {len(counties_list)} counties: {", ".join(counties_list)}'}), 400
        if len(counties_list) == 0:
            return jsonify({'success': False, 'error': 'Please select at least one county'}), 400
        
        # Years are now automatically determined - no validation needed
        # Convert counties list back to string format for parse_web_parameters
        counties_str = ';'.join(counties_list)
        
        # Years will be automatically determined from last 5 years in parse_web_parameters
        # For cache key, use 'auto' if years not provided (will be normalized)
        years_str = data.get('years', '').strip() if 'years' in data else ''
        cache_params = {
            'counties': counties_str,
            'years': years_str if years_str else 'auto',  # Use 'auto' to indicate automatic selection
            'selection_type': selection_type,
            'state_code': state_code,
            'loan_purpose': loan_purpose
        }
        
        # Check cache first
        cached_result = get_cached_result('lendsight', cache_params, user_type)
        
        if cached_result:
            # Cache hit - use cached result
            job_id = cached_result['job_id']
            result_data = cached_result['result_data']
            
            # Store in progress tracker for compatibility
            store_analysis_result(job_id, result_data)
            update_progress(job_id, {
                'percent': 100,
                'step': 'Analysis complete (from cache)',
                'done': True,
                'cached': True
            })
            
            # Store in session
            session['counties'] = counties_str
            session['years'] = years
            session['job_id'] = job_id
            session['selection_type'] = selection_type
            session['loan_purpose'] = loan_purpose
            
            # Log usage (cache hit)
            response_time_ms = int((time_module.time() - start_time) * 1000)
            cache_key = cached_result['cache_key']
            log_usage(
                user_type=user_type,
                app_name='lendsight',
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
        
        # Create progress tracker for this job
        progress_tracker = create_progress_tracker(job_id)
        
        # Parse parameters (this will expand state to counties if needed and get last 5 years automatically)
        try:
            # Pass empty string for years to trigger automatic last 5 years
            years_param = ''  # Will be auto-determined in parse_web_parameters
            print(f"[DEBUG] Calling parse_web_parameters with counties_str={counties_str}, years=auto (last 5), selection_type={selection_type}, state_code={state_code}")
            counties_list, years_list = parse_web_parameters(
                counties_str, years_param, selection_type, state_code, None
            )
            print(f"[DEBUG] parse_web_parameters returned {len(counties_list)} counties and {len(years_list)} years")
        except Exception as e:
            print(f"[ERROR] Error parsing parameters: {e}")
            import traceback
            traceback.print_exc()
            # Log failed request
            response_time_ms = int((time_module.time() - start_time) * 1000)
            cache_key = generate_cache_key('lendsight', cache_params)
            log_usage(
                user_type=user_type,
                app_name='lendsight',
                params=cache_params,
                cache_key=cache_key,
                cache_hit=False,
                job_id=job_id,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_id=request_id
            )
            return jsonify({'success': False, 'error': f'Error parsing parameters: {str(e)}'}), 400
        
        # Store in session
        session['counties'] = ';'.join(counties_list) if counties_list else counties_str
        session['years'] = years
        session['job_id'] = job_id
        session['selection_type'] = selection_type
        session['loan_purpose'] = loan_purpose
        
        def run_job():
            try:
                # Run the analysis pipeline with progress tracking
                # Pass counties_with_fips if available, otherwise use counties_list
                result = run_analysis(
                    ';'.join(counties_list), 
                    ','.join(map(str, years_list)), 
                    job_id, 
                    progress_tracker,
                    selection_type, 
                    state_code, 
                    None,  # metro_code
                    loan_purpose,
                    counties_with_fips if counties_with_fips else None  # Pass FIPS codes if available
                )
                
                if not result.get('success'):
                    error_msg = result.get('error', 'Unknown error')
                    progress_tracker.update_progress('error', error_msg)
                    
                    # Log failed request
                    response_time_ms = int((time_module.time() - start_time) * 1000)
                    cache_key = generate_cache_key('lendsight', cache_params)
                    log_usage(
                        user_type=user_type,
                        app_name='lendsight',
                        params=cache_params,
                        cache_key=cache_key,
                        cache_hit=False,
                        job_id=job_id,
                        response_time_ms=response_time_ms,
                        error_message=error_msg,
                        request_id=request_id
                    )
                    return
                
                # Store the analysis results
                store_analysis_result(job_id, result)
                
                # Store in cache if successful
                try:
                    metadata = {
                        'counties': counties_list,
                        'years': years_list,
                        'duration_seconds': time_module.time() - start_time
                    }
                    
                    store_cached_result(
                        app_name='lendsight',
                        params=cache_params,
                        job_id=job_id,
                        result_data=result,
                        user_type=user_type,
                        metadata=metadata
                    )
                except Exception as cache_error:
                    print(f"Warning: Failed to store in cache: {cache_error}")
                
                # Mark analysis as completed
                progress_tracker.complete(success=True)
                
                # Log usage (cache miss, new analysis)
                response_time_ms = int((time_module.time() - start_time) * 1000)
                cache_key = generate_cache_key('lendsight', cache_params)
                log_usage(
                    user_type=user_type,
                    app_name='lendsight',
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
                cache_key = generate_cache_key('lendsight', cache_params)
                log_usage(
                    user_type=user_type,
                    app_name='lendsight',
                    params=cache_params,
                    cache_key=cache_key,
                    cache_hit=False,
                    job_id=job_id,
                    response_time_ms=response_time_ms,
                    error_message=error_msg,
                    request_id=request_id
                )
        
        print(f"[DEBUG] Starting background thread for job {job_id}")
        threading.Thread(target=run_job, daemon=True).start()
        
        print(f"[DEBUG] Returning success response with job_id: {job_id}")
        return jsonify({'success': True, 'job_id': job_id})
            
    except Exception as e:
        print(f"[ERROR] Exception in analyze endpoint: {e}")
        import traceback
        traceback.print_exc()
        # Log error
        try:
            response_time_ms = int((time_module.time() - start_time) * 1000)
            log_usage(
                user_type=get_user_type(),
                app_name='lendsight',
                params=cache_params if 'cache_params' in locals() else {},
                cache_key=generate_cache_key('lendsight', cache_params) if 'cache_params' in locals() else '',
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


@lendsight_bp.route('/report')
@require_access('lendsight', 'partial')
def report():
    """Report display page"""
    app_base_url = url_for('lendsight.index').rstrip('/')
    return render_template('report_template.html', app_base_url=app_base_url)


@lendsight_bp.route('/download')
@require_access('lendsight', 'partial')
def download():
    """Download the generated reports"""
    try:
        format_type = request.args.get('format', 'excel').lower()
        # Check for job_id in URL parameters first, then session
        job_id = request.args.get('job_id') or session.get('job_id')
        
        if not job_id:
            return jsonify({'error': 'No analysis session found. Please run an analysis first.'}), 400
        
        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found. The analysis may have expired or failed.'}), 400
        
        report_data = analysis_result.get('report_data', {})
        metadata = analysis_result.get('metadata', {})
        
        if not report_data:
            return jsonify({'error': 'No report data available for export.'}), 400
        
        # Check user permissions for export
        user_permissions = get_user_permissions()
        if not user_permissions.get('can_export', False):
            return jsonify({
                'error': 'Export functionality is not available for your account type.'
            }), 403
        
        if format_type == 'excel':
            from .mortgage_report_builder import save_mortgage_excel_report
            import tempfile
            import os
            
            # Create temporary file
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            tmp_path = tmp_file.name
            tmp_file.close()
            
            # Generate Excel report
            save_mortgage_excel_report(report_data, tmp_path, metadata=metadata)
            
            # Generate filename
            from datetime import datetime
            counties = metadata.get('counties', [])
            if counties and len(counties) > 0:
                first_county = counties[0]
                if ',' in first_county:
                    county_name, state_name = [part.strip() for part in first_county.rsplit(',', 1)]
                    filename = f'NCRC_LendSight_{county_name}_{state_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                else:
                    filename = f'NCRC_LendSight_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            else:
                filename = f'NCRC_LendSight_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
            return send_file(
                tmp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        elif format_type == 'pdf':
            return jsonify({'error': 'PDF export not yet implemented'}), 501
        else:
            return jsonify({'error': f'Invalid format specified: {format_type}. Valid formats are: excel, pdf'}), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }), 500


@lendsight_bp.route('/data')
def data():
    """Return data for the application"""
    # To be implemented
    return jsonify([])


@lendsight_bp.route('/counties')
def counties():
    """Return a list of available counties for lending analysis"""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        
        client = get_bigquery_client(LendSightConfig.PROJECT_ID)
        query = """
        SELECT DISTINCT county_state 
        FROM geo.cbsa_to_county 
        ORDER BY county_state
        """
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        return jsonify(counties)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify([])


@lendsight_bp.route('/states')
def states():
    """Return a list of available states for lending analysis"""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        
        client = get_bigquery_client(LendSightConfig.PROJECT_ID)
        query = """
        SELECT DISTINCT 
            s.state_abbrv as code,
            s.state_name as name
        FROM geo.states s
        INNER JOIN geo.cbsa_to_county c ON s.state_name = c.state
        WHERE s.state_abbrv IS NOT NULL AND s.state_name IS NOT NULL
        ORDER BY s.state_name
        """
        query_job = client.query(query)
        results = query_job.result()
        states = [{"code": row.code, "name": row.name} for row in results if row.code and row.name]
        return jsonify(states)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fallback to shared states
        from justdata.shared.utils.geo_data import get_us_states
        return jsonify(get_us_states())


@lendsight_bp.route('/metro-areas')
def metro_areas():
    """Return a list of available metro areas for lending analysis"""
    # TODO: Implement HMDA metro area data lookup
    return jsonify([])


@lendsight_bp.route('/counties-by-state/<state_code>')
def counties_by_state(state_code):
    """Return a list of counties for a specific state"""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        
        client = get_bigquery_client(LendSightConfig.PROJECT_ID)
        
        # Resolve state_code to state name
        if len(state_code) == 2:
            state_name_query = f"""
            SELECT state_name
            FROM geo.states
            WHERE LOWER(state_abbrv) = LOWER('{state_code}')
            LIMIT 1
            """
        else:
            state_name_query = f"""
            SELECT state_name
            FROM geo.states
            WHERE LOWER(state_name) = LOWER('{state_code}')
            LIMIT 1
            """
        
        state_job = client.query(state_name_query)
        state_result = list(state_job.result())
        
        if state_result:
            state_name = state_result[0].state_name
        else:
            state_name = state_code
        
        # Query counties by state name
        query = f"""
        SELECT DISTINCT county_state
        FROM geo.cbsa_to_county 
        WHERE LOWER(state) = LOWER('{state_name}')
        ORDER BY county_state
        """
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        return jsonify(counties)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify([])


@lendsight_bp.route('/years')
def years():
    """Return available years dynamically from HMDA data"""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        
        client = get_bigquery_client(LendSightConfig.PROJECT_ID)
        # Query HMDA table for available years (using activity_year field)
        query = """
        SELECT DISTINCT CAST(activity_year AS INT64) as year
        FROM `hdma1-242116.hmda.hmda`
        WHERE activity_year IS NOT NULL
        ORDER BY year ASC
        """
        query_job = client.query(query)
        results = query_job.result()
        years = [row.year for row in results]
        if not years:
            years = list(range(2017, 2025))
        return jsonify(years)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fallback
        return jsonify(list(range(2017, 2025)))


@lendsight_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'lendsight'
    })
