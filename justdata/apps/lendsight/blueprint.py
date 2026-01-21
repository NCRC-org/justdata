"""
LendSight Blueprint for main JustData app.
Converts the standalone LendSight app into a blueprint with cache integration.
"""

from flask import Blueprint, render_template, request, jsonify, session, Response, make_response, send_file, url_for
from jinja2 import ChoiceLoader, FileSystemLoader
import os
import tempfile
import uuid
import threading
import time
import json
from datetime import datetime
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, get_user_type, login_required
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker
from justdata.shared.utils.analysis_cache import get_cached_result, store_cached_result, log_usage, generate_cache_key, get_analysis_result_by_job_id
from justdata.shared.utils.bigquery_client import escape_sql_string
from justdata.core.config.app_config import LendSightConfig
from .core import run_analysis, parse_web_parameters
from .config import TEMPLATES_DIR, STATIC_DIR

# Get shared templates directory
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# State abbreviations mapping
STATE_ABBREVIATIONS = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'District of Columbia': 'DC', 'Puerto Rico': 'PR', 'Guam': 'GU', 'Virgin Islands': 'VI'
}


def generate_export_filename(metadata: dict, extension: str = 'xlsx') -> str:
    """
    Generate a descriptive filename for LendSight exports.

    Format: LendSight_MortgageMarket_{CountyName}_{StateAbbrev}_{YYYYMMDD}_{HHMMSS}.{ext}

    Examples:
    - LendSight_MortgageMarket_MontgomeryCounty_MD_20250118_143022.xlsx
    - LendSight_MortgageMarket_MultipleCounties_MD_20250118_143022.pdf
    """
    import re

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    counties = metadata.get('counties', [])

    if not counties:
        return f'LendSight_MortgageMarket_Report_{timestamp}.{extension}'

    # Parse first county to get state
    first_county = counties[0] if isinstance(counties[0], str) else str(counties[0])

    # Extract state from "County Name, State" format
    state_abbrev = 'XX'
    county_name_clean = first_county

    if ',' in first_county:
        parts = first_county.rsplit(',', 1)
        county_name_raw = parts[0].strip()
        state_name = parts[1].strip()

        # Get state abbreviation
        state_abbrev = STATE_ABBREVIATIONS.get(state_name, state_name[:2].upper())

        # Clean county name: remove special chars, spaces, and "County" suffix
        county_name_clean = re.sub(r'[^\w\s]', '', county_name_raw)  # Remove special chars
        county_name_clean = county_name_clean.replace(' ', '')  # Remove spaces
        # Keep "County" in the name for clarity
    else:
        county_name_clean = re.sub(r'[^\w\s]', '', first_county).replace(' ', '')

    # Truncate if too long (max 40 chars for county name)
    if len(county_name_clean) > 40:
        county_name_clean = county_name_clean[:40]

    # Handle single vs multiple counties
    if len(counties) == 1:
        filename = f'LendSight_MortgageMarket_{county_name_clean}_{state_abbrev}_{timestamp}.{extension}'
    else:
        filename = f'LendSight_MortgageMarket_MultipleCounties_{state_abbrev}_{timestamp}.{extension}'

    return filename


# Create blueprint
lendsight_bp = Blueprint(
    'lendsight',
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/lendsight/static'
)


@lendsight_bp.record_once
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


@lendsight_bp.route('/')
@login_required
@require_access('lendsight', 'partial')
def index():
    """Main page with the analysis form"""
    user_permissions = get_user_permissions()
    user_type = get_user_type()
    # Staff and admin users can see the "clear cache" checkbox
    is_staff = (user_type in ('staff', 'admin'))
    cache_buster = int(time.time())  # Timestamp for cache-busting
    # Set base URL for JavaScript API calls
    app_base_url = url_for('lendsight.index').rstrip('/')
    response = make_response(render_template('lendsight_analysis.html',
                                           permissions=user_permissions,
                                           is_staff=is_staff,
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
@login_required
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

        # Check for force_refresh parameter to bypass cache
        force_refresh = data.get('force_refresh', False)

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
        
        # Check cache first (unless force_refresh is True)
        cached_result = None
        if not force_refresh:
            cached_result = get_cached_result('lendsight', cache_params, user_type)
        else:
            print(f"[INFO] Force refresh requested - bypassing cache")

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
                
                # Store in BigQuery only (no in-memory storage)
                # store_cached_result stores everything in BigQuery
                try:
                    # Include all metadata from result, especially census_data
                    metadata = {
                        'counties': counties_list,
                        'years': years_list,
                        'duration_seconds': time_module.time() - start_time,
                        'total_records': result.get('metadata', {}).get('total_records', 0),
                        'loan_purpose': result.get('metadata', {}).get('loan_purpose', ['purchase']),
                        'census_data': result.get('metadata', {}).get('census_data', None),
                        'generated_at': datetime.now().isoformat()
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
@login_required
@require_access('lendsight', 'partial')
def report():
    """Report display page"""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    app_base_url = url_for('lendsight.index').rstrip('/')
    # Explicitly load from LendSight templates directory to avoid template resolution conflicts
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(['html', 'xml'])
    )
    # Add Flask's url_for to the template globals
    env.globals['url_for'] = url_for
    template = env.get_template('report_template.html')
    return template.render(app_base_url=app_base_url)


@lendsight_bp.route('/report-data', methods=['GET'])
@login_required
@require_access('lendsight', 'partial')
def report_data():
    """Return the analysis report data for web display"""
    try:
        # Check for job_id in URL parameters first, then session
        job_id = request.args.get('job_id') or session.get('job_id')
        
        if not job_id:
            return jsonify({
                'success': False,
                'error': 'No analysis session found. Please run an analysis first.'
            }), 400
        
        # Retrieve from BigQuery only (no in-memory storage)
        analysis_result = get_analysis_result_by_job_id(job_id)
        if not analysis_result:
            # Check progress to see if analysis is still running
            progress = get_progress(job_id)
            if not progress.get('done', False):
                return jsonify({
                    'success': False,
                    'error': 'Analysis still in progress',
                    'progress': progress
                }), 202  # 202 Accepted - still processing
            
            return jsonify({
                'success': False,
                'error': 'No analysis data found. The analysis may have expired or failed.',
                'progress': progress
            }), 404
        
        # Extract report data and metadata
        report_data = analysis_result.get('report_data', {})
        metadata = analysis_result.get('metadata', {})
        ai_insights = analysis_result.get('ai_insights', {})
        
        # Debug logging
        print(f"[DEBUG] report_data keys: {list(report_data.keys()) if report_data else 'None'}")
        print(f"[DEBUG] metadata keys: {list(metadata.keys()) if metadata else 'None'}")
        print(f"[DEBUG] ai_insights keys: {list(ai_insights.keys()) if ai_insights else 'None'}")
        print(f"[DEBUG] ai_insights type: {type(ai_insights)}, value: {ai_insights}")
        
        # Convert pandas DataFrames to JSON-serializable format
        import pandas as pd
        import numpy as np
        
        def convert_dataframe(df):
            """Convert DataFrame to dict format"""
            if isinstance(df, pd.DataFrame):
                if df.empty:
                    return []
                # Convert to records format
                return df.replace({np.nan: None}).to_dict('records')
            return df
        
        # Convert all DataFrames in report_data
        converted_report_data = {}
        for key, value in report_data.items():
            if isinstance(value, pd.DataFrame):
                converted_report_data[key] = convert_dataframe(value)
            elif isinstance(value, dict):
                # Handle nested dicts that might contain DataFrames
                converted_report_data[key] = {
                    k: convert_dataframe(v) if isinstance(v, pd.DataFrame) else v
                    for k, v in value.items()
                }
            else:
                converted_report_data[key] = value
        
        # Include ai_insights in metadata for frontend compatibility
        metadata_with_ai = metadata.copy()
        metadata_with_ai['ai_insights'] = ai_insights
        
        return jsonify({
            'success': True,
            'data': converted_report_data,
            'metadata': metadata_with_ai,
            'ai_insights': ai_insights  # Also include at top level for backward compatibility
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'An error occurred while loading report data: {str(e)}'
        }), 500


@lendsight_bp.route('/download')
@login_required
@require_access('lendsight', 'partial')
def download():
    """Download the generated reports"""
    try:
        format_type = request.args.get('format', 'excel').lower()
        # Check for job_id in URL parameters first, then session
        job_id = request.args.get('job_id') or session.get('job_id')
        
        if not job_id:
            return jsonify({'error': 'No analysis session found. Please run an analysis first.'}), 400
        
        # Retrieve from BigQuery only (no in-memory storage)
        analysis_result = get_analysis_result_by_job_id(job_id)
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
            import re

            # Create temporary file
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            tmp_path = tmp_file.name
            tmp_file.close()

            # Generate Excel report
            save_mortgage_excel_report(report_data, tmp_path, metadata=metadata)

            # Generate descriptive filename
            filename = generate_export_filename(metadata, 'xlsx')

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
        
        # Add debug logging
        print(f"[DEBUG] /lendsight/counties endpoint: Returning {len(counties)} counties")
        if len(counties) > 0:
            print(f"[DEBUG] First county example: {counties[0]}")
        else:
            print("[WARNING] /lendsight/counties endpoint: No counties returned from query!")
        
        return jsonify(counties)
    except Exception as e:
        import traceback
        print(f"[ERROR] /lendsight/counties endpoint failed: {e}")
        traceback.print_exc()
        return jsonify([])


@lendsight_bp.route('/states')
def states():
    """Return a list of available states for lending analysis"""
    try:
        from .data_utils import get_available_states
        states_list = get_available_states()
        print(f"[DEBUG] /lendsight/states endpoint: Returning {len(states_list)} states")
        return jsonify(states_list)
    except Exception as e:
        import traceback
        print(f"[ERROR] /lendsight/states endpoint failed: {e}")
        traceback.print_exc()
        return jsonify([])


@lendsight_bp.route('/metro-areas')
def metro_areas():
    """Return a list of available metro areas for lending analysis"""
    # TODO: Implement HMDA metro area data lookup
    return jsonify([])


@lendsight_bp.route('/counties-by-state/<state_code>')
def counties_by_state(state_code):
    """Return a list of counties for a specific state.

    Handles both FIPS codes (e.g., '02' for Alaska) and state names.
    """
    try:
        from urllib.parse import unquote
        from justdata.shared.utils.bigquery_client import get_bigquery_client

        # URL decode the state code
        state_code = unquote(str(state_code)).strip()
        print(f"[DEBUG] lendsight/counties-by-state called with state_code: '{state_code}'")

        client = get_bigquery_client(LendSightConfig.PROJECT_ID)

        # Check if state_code is a numeric FIPS code (2 digits) or a state name
        is_numeric_code = state_code.isdigit() and len(state_code) <= 2

        if is_numeric_code:
            # Use geoid5 to match by state FIPS code (first 2 digits of geoid5)
            state_code_padded = state_code.zfill(2)
            print(f"[DEBUG] Using state FIPS code: {state_code_padded}")
            query = f"""
            SELECT DISTINCT
                county_state,
                geoid5,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as county_fips
            FROM `{LendSightConfig.PROJECT_ID}.geo.cbsa_to_county`
            WHERE geoid5 IS NOT NULL
                AND SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) = '{state_code_padded}'
                AND county_state IS NOT NULL
                AND TRIM(county_state) != ''
            ORDER BY county_state
            """
        else:
            # Use state name to match
            print(f"[DEBUG] Using state name: {state_code}")
            escaped_state_code = escape_sql_string(state_code)
            query = f"""
            SELECT DISTINCT
                county_state,
                geoid5,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as county_fips
            FROM `{LendSightConfig.PROJECT_ID}.geo.cbsa_to_county`
            WHERE LOWER(TRIM(SPLIT(county_state, ',')[SAFE_OFFSET(1)])) = LOWER('{escaped_state_code}')
                AND county_state IS NOT NULL
                AND TRIM(county_state) != ''
            ORDER BY county_state
            """

        query_job = client.query(query)
        results = list(query_job.result())

        # Return counties with proper structure
        counties = []
        seen_geoids = set()

        for row in results:
            geoid5 = str(row.geoid5).zfill(5) if row.geoid5 else None

            if geoid5 and geoid5 in seen_geoids:
                continue
            if geoid5:
                seen_geoids.add(geoid5)

            state_fips = row.state_fips if hasattr(row, 'state_fips') else (geoid5[:2] if geoid5 and len(geoid5) >= 2 else None)
            county_fips = row.county_fips if hasattr(row, 'county_fips') else (geoid5[2:] if geoid5 and len(geoid5) >= 5 else None)

            county_name = ''
            state_name = ''
            if row.county_state and ',' in row.county_state:
                parts = row.county_state.split(',', 1)
                county_name = parts[0].strip()
                state_name = parts[1].strip() if len(parts) > 1 else ''

            counties.append({
                'geoid5': geoid5,
                'name': row.county_state,
                'county_name': county_name,
                'state_name': state_name,
                'state_fips': state_fips,
                'county_fips': county_fips
            })

        print(f"[DEBUG] lendsight/counties-by-state: Found {len(counties)} counties for state_code: {state_code}")
        if counties:
            print(f"[DEBUG] Sample counties: {counties[:3]}")

        return jsonify(counties)
    except Exception as e:
        import traceback
        print(f"[ERROR] /lendsight/counties-by-state endpoint failed: {e}")
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
