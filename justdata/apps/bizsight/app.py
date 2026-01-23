#!/usr/bin/env python3
"""
BizSight Flask Web Application
Main application file for BizSight.
"""

from flask import render_template, request, jsonify, session, Response, send_file, make_response, send_from_directory
import os
import sys
import uuid
import threading
import time
import json
from pathlib import Path
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from justdata.shared.web.app_factory import create_app
from justdata.apps.bizsight.config import BizSightConfig, TEMPLATES_DIR_STR, STATIC_DIR_STR
from justdata.apps.bizsight.core import run_analysis
from justdata.apps.bizsight.data_utils import get_available_counties, get_available_years
from justdata.apps.bizsight.utils.progress_tracker import (
    get_progress, update_progress, create_progress_tracker,
    store_analysis_result, get_analysis_result
)
from justdata.apps.bizsight.utils.bigquery_client import BigQueryClient
from justdata.apps.bizsight.version import __version__
from justdata.shared.services.export_service import ExportService
from justdata.shared.utils.env_utils import is_local_development
from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config

# Load unified environment configuration (works for both local and Render)
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)

# Print environment summary
print(f"[ENV] Environment: {'LOCAL' if config['IS_LOCAL'] else 'PRODUCTION (Render)'}")
print(f"[ENV] Shared config loaded from: {config.get('SHARED_ENV_FILE', 'Environment variables')}")

# Create Flask app using shared factory for consistent session handling
app = create_app(
    'bizsight',
    template_folder=TEMPLATES_DIR_STR,
    static_folder=STATIC_DIR_STR,
    config={
        'DEBUG': BizSightConfig.DEBUG,
        'TEMPLATES_AUTO_RELOAD': True,  # Force template reload on every request
        'SEND_FILE_MAX_AGE_DEFAULT': 0,  # Disable static file caching
        'EXPLAIN_TEMPLATE_LOADING': True,  # Debug template loading
    }
)

# Add ProxyFix for proper request handling behind Render's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# DISABLE Jinja2 bytecode cache completely - this is the key fix
# Jinja2 compiles templates to .pyc files which persist on disk
# Setting bytecode_cache to None disables this completely
print("=" * 80, flush=True)
print("INITIALIZING FLASK APP - DISABLING JINJA2 BYTECODE CACHE", flush=True)
print("=" * 80, flush=True)
app.jinja_env.bytecode_cache = None
print(f"[OK] Jinja2 bytecode_cache disabled: {app.jinja_env.bytecode_cache}", flush=True)
print(f"[OK] Template folder: {TEMPLATES_DIR_STR}", flush=True)
print(f"[OK] Static folder: {STATIC_DIR_STR}", flush=True)
print("=" * 80, flush=True)

# Force reload templates on every request
@app.before_request
def clear_template_cache():
    """Clear Jinja2 template cache before each request."""
    if hasattr(app, 'jinja_env'):
        # Completely disable bytecode cache
        app.jinja_env.bytecode_cache = None
        # Completely clear the in-memory cache
        app.jinja_env.cache = {}
        # Force reload of all templates
        app.jinja_env.auto_reload = True
        # Also try to reload the environment
        try:
            if hasattr(app.jinja_env.cache, 'clear'):
                app.jinja_env.cache.clear()
        except:
            pass
        # Debug: Log cache clearing on first request only
        if not hasattr(clear_template_cache, '_logged'):
            print(f"DEBUG: Template cache cleared, bytecode_cache={app.jinja_env.bytecode_cache}, auto_reload={app.jinja_env.auto_reload}", flush=True)
            clear_template_cache._logged = True


@app.route('/shared/population_demographics.js')
def shared_population_demographics_js():
    """Serve shared population demographics JavaScript module"""
    from flask import send_from_directory
    from pathlib import Path
    shared_static_dir = Path(__file__).parent.parent.parent / 'shared' / 'web' / 'static' / 'js'
    js_path = shared_static_dir / 'population_demographics.js'
    if js_path.exists():
        return send_from_directory(str(shared_static_dir), 'population_demographics.js', mimetype='application/javascript')
    return '', 404

@app.route('/')
def index():
    """Main page with the US map for county selection."""
    from justdata.apps.bizsight.config import BizSightConfig

    # Force template reload by clearing cache before rendering
    if hasattr(app, 'jinja_env'):
        app.jinja_env.bytecode_cache = None
        app.jinja_env.cache = {}
        try:
            if hasattr(app.jinja_env.cache, 'clear'):
                app.jinja_env.cache.clear()
        except:
            pass
        print(f"DEBUG: Rendering analysis_template.html, bytecode_cache={app.jinja_env.bytecode_cache}", flush=True)

    # Breadcrumb for main page
    breadcrumb_items = [{'name': 'BizSight', 'url': '/bizsight'}]

    response = make_response(render_template(
        'analysis_template.html',
        version=__version__,
        app_name='BizSight',
        breadcrumb_items=breadcrumb_items
    ))
    # Add aggressive cache-busting headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # Add ETag with timestamp to force browser to revalidate
    import time
    response.headers['ETag'] = f'"{int(time.time())}"'
    response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response


@app.route('/static/img/ncrc-logo.png')
def serve_shared_logo():
    """Serve the shared NCRC logo from shared/web/static/img/"""
    shared_logo_path = REPO_ROOT / 'shared' / 'web' / 'static' / 'img' / 'ncrc-logo.png'
    if shared_logo_path.exists():
        return send_from_directory(str(shared_logo_path.parent), shared_logo_path.name)
    else:
        # Fallback to local static if shared logo doesn't exist
        return send_from_directory(app.static_folder, 'img/ncrc-logo.png'), 404


@app.route('/favicon.ico')
def favicon():
    """Serve favicon.ico from shared static folder"""
    shared_static_dir = REPO_ROOT / 'shared' / 'web' / 'static'
    favicon_path = shared_static_dir / 'favicon.ico'
    if favicon_path.exists():
        return send_from_directory(str(shared_static_dir), 'favicon.ico', mimetype='image/x-icon')
    return '', 204  # No Content if file doesn't exist


@app.route('/favicon-32x32.png')
def favicon_32x32():
    """Serve favicon-32x32.png from shared static folder"""
    shared_static_dir = REPO_ROOT / 'shared' / 'web' / 'static'
    favicon_path = shared_static_dir / 'favicon-32x32.png'
    if favicon_path.exists():
        return send_from_directory(str(shared_static_dir), 'favicon-32x32.png', mimetype='image/png')
    return '', 204  # No Content if file doesn't exist


@app.route('/favicon-16x16.png')
def favicon_16x16():
    """Serve favicon-16x16.png from shared static folder"""
    shared_static_dir = REPO_ROOT / 'shared' / 'web' / 'static'
    favicon_path = shared_static_dir / 'favicon-16x16.png'
    if favicon_path.exists():
        return send_from_directory(str(shared_static_dir), 'favicon-16x16.png', mimetype='image/png')
    return '', 204  # No Content if file doesn't exist


@app.route('/progress/<job_id>')
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


@app.route('/analyze', methods=['POST'])
def analyze():
    """Handle analysis request."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        # Get county selection (single county only)
        county_data = data.get('county_data')
        if not county_data:
            return jsonify({'success': False, 'error': 'Please select a county'}), 400
        
        # Get year range
        start_year = data.get('startYear')
        end_year = data.get('endYear')
        
        if not start_year or not end_year:
            return jsonify({'success': False, 'error': 'Please select start and end years'}), 400
        
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
        
        # Create job ID
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
                    return
                
                # Store analysis result
                print(f"\n{'='*80}")
                print(f"DEBUG: ========== STORING ANALYSIS RESULT ==========")
                print(f"{'='*80}")
                print(f"DEBUG: Storing analysis result for job_id: {job_id}")
                print(f"DEBUG: Result keys: {list(result.keys())}")
                print(f"DEBUG: comparison_table in result: {'comparison_table' in result}")
                print(f"DEBUG: hhi in result: {'hhi' in result}")
                if 'comparison_table' in result:
                    print(f"DEBUG: comparison_table length: {len(result['comparison_table']) if isinstance(result['comparison_table'], list) else 'not a list'}")
                if 'hhi' in result:
                    print(f"DEBUG: hhi value: {result['hhi']}")
                store_analysis_result(job_id, result)
                print(f"DEBUG: Result stored. Verifying...")
                stored = get_analysis_result(job_id)
                print(f"DEBUG: Verification - stored result exists: {stored is not None}")
                if stored:
                    print(f"DEBUG: Stored result has comparison_table: {'comparison_table' in stored}")
                    print(f"DEBUG: Stored result has hhi: {'hhi' in stored}")
                print(f"{'='*80}\n")
                progress_tracker.complete(success=True)
                
            except Exception as e:
                error_msg = str(e)
                progress_tracker.complete(success=False, error=error_msg)
        
        # Start background job
        threading.Thread(target=run_job, daemon=True).start()
        
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500


@app.route('/data', methods=['GET'])
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


@app.route('/api/states', methods=['GET'])
def get_states():
    """Get list of available states."""
    try:
        from justdata.apps.bizsight.data_utils import get_available_states
        states = get_available_states()
        if not states:
            # Log for debugging
            print("WARNING: No states returned from get_available_states()")
        return jsonify(states)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/planning-regions', methods=['GET'])
def get_planning_regions():
    """Get Connecticut planning regions for 2024 data."""
    planning_regions = [
        {'code': '09110', 'name': 'Capitol Planning Region', 'geoid5': '09110'},
        {'code': '09120', 'name': 'Greater Bridgeport Planning Region', 'geoid5': '09120'},
        {'code': '09130', 'name': 'Lower Connecticut River Valley Planning Region', 'geoid5': '09130'},
        {'code': '09140', 'name': 'Naugatuck Valley Planning Region', 'geoid5': '09140'},
        {'code': '09150', 'name': 'Northeastern Connecticut Planning Region', 'geoid5': '09150'},
        {'code': '09160', 'name': 'Northwest Hills Planning Region', 'geoid5': '09160'},
        {'code': '09170', 'name': 'South Central Connecticut Planning Region', 'geoid5': '09170'},
        {'code': '09180', 'name': 'Southeastern Connecticut Planning Region', 'geoid5': '09180'},
        {'code': '09190', 'name': 'Western Connecticut Planning Region', 'geoid5': '09190'},
    ]
    return jsonify(planning_regions)

@app.route('/api/counties-by-state/<state_code>', methods=['GET'])
def get_counties_by_state(state_code):
    """Get counties for a specific state - matching LendSight's working implementation.
    
    Updated Dec 11, 2025: Fixed to query BigQuery directly like LendSight.
    This fixes the issue where counties were not loading after selecting a state."""
    try:
        from urllib.parse import unquote
        from justdata.shared.utils.bigquery_client import get_bigquery_client, escape_sql_string
        from justdata.apps.bizsight.config import BizSightConfig
        
        # URL decode the state code
        state_code = unquote(str(state_code)).strip()
        print(f"[DEBUG] get_counties_by_state called with state_code: '{state_code}'")
        
        client = get_bigquery_client(BizSightConfig.GCP_PROJECT_ID)
        
        # Check if state_code is a numeric state code (2 digits) or a state name
        is_numeric_code = state_code.isdigit() and len(state_code) <= 2
        
        if is_numeric_code:
            # Use geoid5 to match by state FIPS code (first 2 digits of geoid5)
            # GEOID5 format: SSCCC where SS = state FIPS (2 digits), CCC = county FIPS (3 digits)
            state_code_padded = state_code.zfill(2)
            print(f"[DEBUG] Using state FIPS code: {state_code_padded}")
            query = f"""
            SELECT DISTINCT 
                county_state,
                geoid5,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as county_fips
            FROM geo.cbsa_to_county 
            WHERE geoid5 IS NOT NULL
                AND SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) = '{state_code_padded}'
                AND county_state IS NOT NULL
                AND TRIM(county_state) != ''
            ORDER BY county_state
            """
        else:
            # Use state name to match (extract from county_state)
            print(f"[DEBUG] Using state name: {state_code}")
            query = f"""
            SELECT DISTINCT county_state, geoid5
            FROM geo.cbsa_to_county 
            WHERE LOWER(TRIM(SPLIT(county_state, ',')[SAFE_OFFSET(1)])) = LOWER('{escape_sql_string(state_code)}')
            ORDER BY county_state
            """
        
        try:
            query_job = client.query(query)
            results = list(query_job.result())
            # Return both county_state and geoid5 so frontend can use FIPS codes
            # GEOID5 = SSCCC where SS = state FIPS, CCC = county FIPS
            counties = []
            seen_geoids = set()  # Track unique GEOIDs to avoid duplicates
            
            for row in results:
                # Ensure geoid5 is properly formatted as 5-digit string
                geoid5 = str(row.geoid5).zfill(5) if row.geoid5 else None
                
                # Skip if we've already seen this GEOID
                if geoid5 and geoid5 in seen_geoids:
                    continue
                    
                if geoid5:
                    seen_geoids.add(geoid5)
                
                # Extract state and county FIPS from GEOID5
                state_fips = geoid5[:2] if geoid5 and len(geoid5) >= 2 else None
                county_fips = geoid5[2:] if geoid5 and len(geoid5) >= 5 else None
                
                # Parse county_name and state_name from county_state
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
            
            if counties:
                print(f"[DEBUG] Found {len(counties)} counties for state_code: {state_code}")
                # Debug: show first few counties
                if len(counties) > 0:
                    print(f"[DEBUG] Sample counties: {counties[:3]}")
                return jsonify(counties)
            else:
                print(f"[WARNING] No counties found for state_code: {state_code}")
                return jsonify([])
        except Exception as bq_error:
            print(f"[ERROR] BigQuery query failed: {bq_error}")
            import traceback
            traceback.print_exc()
            # Fall back to using data_utils
            from justdata.apps.bizsight.data_utils import get_available_counties
            state_code_padded = state_code.zfill(2) if state_code.isdigit() else state_code
            counties = get_available_counties(state_code=state_code_padded if state_code.isdigit() else None)
            print(f"[DEBUG] Fallback: Found {len(counties)} counties")
            return jsonify(counties)
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"[ERROR] get_counties_by_state error: {error_msg}")
        return jsonify({'error': error_msg}), 500


@app.route('/api/county-boundaries', methods=['GET'])
def county_boundaries():
    """Get county boundaries GeoJSON for the map."""
    try:
        # Use US Census TIGER/Line REST API to get county boundaries
        # This endpoint will be called on-demand as user zooms in
        # For now, return empty - boundaries will be loaded via JavaScript using Census API
        
        # We'll use the Census TIGERweb service directly from the frontend
        # to avoid loading all 3,100 counties at once
        return jsonify({
            'message': 'County boundaries loaded on-demand via Census TIGERweb API',
            'api_url': 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/84/query'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/state-boundaries', methods=['GET'])
def state_boundaries():
    """Get state boundaries GeoJSON for the map."""
    try:
        # Use US Census TIGER/Line REST API to get state boundaries
        # This will be loaded once and shown at lower zoom levels
        return jsonify({
            'message': 'State boundaries loaded on-demand via Census TIGERweb API',
            'api_url': 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/86/query'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tract-boundaries/<geoid5>', methods=['GET'])
def get_tract_boundaries(geoid5):
    """Return census tract boundaries as GeoJSON for a county."""
    try:
        from justdata.apps.bizsight.utils.tract_boundaries import get_tract_boundaries_geojson
        
        # Extract state and county FIPS from GEOID5 (first 2 digits = state, next 3 = county)
        geoid5_str = str(geoid5).zfill(5)
        state_fips = geoid5_str[:2]
        county_fips = geoid5_str[2:5]
        
        print(f"Fetching tract boundaries for GEOID5: {geoid5_str} (State: {state_fips}, County: {county_fips})")
        
        geojson = get_tract_boundaries_geojson(state_fips, county_fips)
        
        if not geojson:
            return jsonify({
                'success': False,
                'error': 'Could not fetch census tract boundaries'
            }), 500
        
        return jsonify({
            'success': True,
            'geojson': geojson
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/report', methods=['GET'])
def report():
    """Report display page."""
    job_id = request.args.get('job_id')
    if not job_id:
        return "Error: No job ID provided", 400

    # Force template reload by clearing cache before rendering
    if hasattr(app, 'jinja_env'):
        app.jinja_env.bytecode_cache = None
        app.jinja_env.cache = {}
        try:
            if hasattr(app.jinja_env.cache, 'clear'):
                app.jinja_env.cache.clear()
        except:
            pass
        print(f"DEBUG: Rendering report_template.html for job_id={job_id}, bytecode_cache={app.jinja_env.bytecode_cache}", flush=True)

    # Breadcrumb for report page
    breadcrumb_items = [
        {'name': 'BizSight', 'url': '/bizsight'},
        {'name': 'Report', 'url': '/bizsight/report'}
    ]

    response = make_response(render_template(
        'report_template.html',
        job_id=job_id,
        version=__version__,
        app_base_url='',
        app_name='BizSight',
        breadcrumb_items=breadcrumb_items
    ))
    # Add aggressive cache-busting headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # Add ETag with timestamp to force browser to revalidate
    import time
    response.headers['ETag'] = f'"{int(time.time())}"'
    response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response


@app.route('/report-data', methods=['GET'])
def report_data():
    """Return the analysis report data for web display."""
    job_id = request.args.get('job_id') or session.get('job_id')
    if not job_id:
        return jsonify({'error': 'No analysis session found'}), 404
    
    # Debug: Check what's in the store
    from justdata.apps.bizsight.utils.progress_tracker import analysis_results_store
    print(f"DEBUG: Looking for job_id: {job_id}")
    print(f"DEBUG: Available job_ids in store: {list(analysis_results_store.keys())}")
    
    analysis_result = get_analysis_result(job_id)
    if not analysis_result:
        # Check progress to see if analysis is still running
        progress = get_progress(job_id)
        if not progress.get('done', False):
            return jsonify({
                'error': 'Analysis still in progress',
                'progress': progress
            }), 202  # 202 Accepted - still processing
        return jsonify({
            'error': 'No analysis data found',
            'progress': progress,
            'available_jobs': list(analysis_results_store.keys())
        }), 404
    
    # Convert pandas DataFrames to JSON-serializable format
    import numpy as np
    import pandas as pd
    import math
    
    def clean_for_json(obj):
        """Recursively clean data structure for JSON serialization."""
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    report_data = analysis_result.get('report_data', {})
    serialized_data = {}
    
    for key, df in report_data.items():
        if hasattr(df, 'to_dict'):
            df_clean = df.replace({np.nan: None, np.inf: None, -np.inf: None})
            serialized_data[key] = clean_for_json(df_clean.to_dict('records'))
        else:
            serialized_data[key] = clean_for_json(df)
    
    metadata = clean_for_json(analysis_result.get('metadata', {}))
    summary_table = clean_for_json(analysis_result.get('summary_table', {}))
    county_summary_table = clean_for_json(analysis_result.get('county_summary_table', []))
    tract_data_for_map = clean_for_json(analysis_result.get('tract_data_for_map', []))
    top_lenders_table = clean_for_json(analysis_result.get('top_lenders_table', []))
    comparison_table = clean_for_json(analysis_result.get('comparison_table', []))
    hhi = clean_for_json(analysis_result.get('hhi', None))
    hhi_by_year = clean_for_json(analysis_result.get('hhi_by_year', []))
    ai_insights = clean_for_json(analysis_result.get('ai_insights', {}))
    
    # Debug logging for AI insights
    print(f"DEBUG: ai_insights type: {type(ai_insights)}")
    print(f"DEBUG: ai_insights keys: {list(ai_insights.keys()) if isinstance(ai_insights, dict) else 'not a dict'}")
    print(f"DEBUG: metadata ai_insights_enabled: {metadata.get('ai_insights_enabled') if isinstance(metadata, dict) else 'metadata not a dict'}")
    if isinstance(ai_insights, dict):
        for key, value in ai_insights.items():
            if value:
                print(f"DEBUG: ai_insights['{key}']: length={len(str(value))}")
            else:
                print(f"DEBUG: ai_insights['{key}']: empty")
    
    # Debug logging
    print(f"DEBUG: county_summary_table length: {len(county_summary_table) if isinstance(county_summary_table, list) else 'not a list'}")
    print(f"DEBUG: top_lenders_table length: {len(top_lenders_table) if isinstance(top_lenders_table, list) else 'not a list'}")
    print(f"DEBUG: comparison_table length: {len(comparison_table) if isinstance(comparison_table, list) else 'not a list'}")
    print(f"DEBUG: comparison_table type: {type(comparison_table)}")
    print(f"DEBUG: hhi: {hhi}")
    print(f"DEBUG: hhi type: {type(hhi)}")
    print(f"DEBUG: hhi_by_year length: {len(hhi_by_year) if isinstance(hhi_by_year, list) else 'not a list'}")
    print(f"DEBUG: hhi_by_year: {hhi_by_year}")
    if county_summary_table:
        print(f"DEBUG: county_summary_table sample: {county_summary_table[0] if len(county_summary_table) > 0 else 'empty'}")
    if top_lenders_table:
        print(f"DEBUG: top_lenders_table sample: {top_lenders_table[0] if len(top_lenders_table) > 0 else 'empty'}")
    if comparison_table:
        print(f"DEBUG: comparison_table has {len(comparison_table)} items")
        print(f"DEBUG: comparison_table sample: {comparison_table[0] if len(comparison_table) > 0 else 'empty'}")
    else:
        print(f"DEBUG: WARNING - comparison_table is empty or None!")
        print(f"DEBUG: analysis_result keys: {list(analysis_result.keys()) if isinstance(analysis_result, dict) else 'not a dict'}")
        if isinstance(analysis_result, dict):
            print(f"DEBUG: analysis_result has 'comparison_table': {'comparison_table' in analysis_result}")
            if 'comparison_table' in analysis_result:
                print(f"DEBUG: analysis_result['comparison_table'] type: {type(analysis_result['comparison_table'])}")
                print(f"DEBUG: analysis_result['comparison_table'] value: {analysis_result['comparison_table']}")
    
    response = jsonify({
        'success': True,
        'data': serialized_data,
        'metadata': metadata,
        'summary_table': summary_table,
        'tract_data_for_map': tract_data_for_map,
        'county_summary_table': county_summary_table,
        'top_lenders_table': top_lenders_table,
        'comparison_table': comparison_table,
        'hhi': hhi,
        'hhi_by_year': hhi_by_year,
        'ai_insights': ai_insights
    })
    # Add aggressive cache-busting headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # Add ETag with timestamp to force browser to revalidate
    import time
    response.headers['ETag'] = f'"{int(time.time())}"'
    response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response


@app.route('/download', methods=['GET'])
def download():
    """Download report in various formats."""
    try:
        format_type = request.args.get('format', 'excel')
        job_id = request.args.get('job_id') or session.get('job_id')
        
        if not job_id:
            return jsonify({'error': 'No analysis session found'}), 404
        
        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found'}), 404
        
        report_data = analysis_result.get('report_data', {})
        metadata = analysis_result.get('metadata', {})
        
        if format_type == 'excel':
            return download_excel(analysis_result, metadata)
        elif format_type == 'pdf':
            return download_pdf_report(report_data, metadata, job_id)
        elif format_type == 'pdf-maps':
            return download_map_pdfs(report_data, metadata, job_id)
        else:
            return jsonify({'error': f'Unsupported format: {format_type}'}), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Download failed: {str(e)}'
        }), 500


def generate_filename(metadata, extension='.xlsx'):
    """Generate a filename for downloads with NCRC, BizSight, county, and state"""
    import re
    from datetime import datetime
    
    county_name = metadata.get('county_name', 'Unknown County')
    state_name = metadata.get('state_name', '')
    
    def clean_name(name):
        # Remove "County" suffix if present
        name = re.sub(r'\s+County\s*$', '', name, flags=re.IGNORECASE)
        # Remove commas
        name = name.replace(',', '')
        # Replace spaces and special characters with underscores
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[\s-]+', '_', name)
        return name
    
    county_clean = clean_name(county_name)
    state_clean = clean_name(state_name) if state_name else ''
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if state_clean:
        filename = f'NCRC_BizSight_{county_clean}_{state_clean}_{timestamp}{extension}'
    else:
        filename = f'NCRC_BizSight_{county_clean}_{timestamp}{extension}'
    
    filename = re.sub(r'__+', '_', filename)  # Clean up double underscores
    return filename


def download_excel(analysis_result, metadata):
    """Download Excel file with multiple sheets."""
    try:
        import tempfile
        from justdata.apps.bizsight.excel_export import save_bizsight_excel_report
        
        # Create a temporary file
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(tmp_fd)
        
        save_bizsight_excel_report(analysis_result, tmp_path, metadata=metadata)
        
        # Generate filename
        filename = generate_filename(metadata, '.xlsx')
        
        # Send the file and schedule cleanup
        response = send_file(
            tmp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except:
                pass
        
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Excel export failed: {str(e)}'}), 500


def download_pdf_report(report_data, metadata, job_id):
    """Download PDF file with written portions of the report using WeasyPrint.

    Args:
        report_data: Either a dict with 'report_data' and 'ai_insights' keys (full analysis result),
                     or just the report_data dict itself.
        metadata: Report metadata dict
        job_id: The job ID for this analysis
    """
    try:
        import tempfile
        from weasyprint import HTML, CSS
        from flask import render_template

        # Handle both full analysis result and just report_data
        # When called from blueprint.py, report_data is actually the full analysis result
        if isinstance(report_data, dict) and 'ai_insights' in report_data:
            # Full analysis result passed
            ai_insights = report_data.get('ai_insights', {})
            actual_report_data = report_data.get('report_data', report_data)
        else:
            # Just report_data passed, try to get AI insights from local progress tracker
            try:
                from justdata.apps.bizsight.utils.progress_tracker import get_analysis_result
                analysis_result = get_analysis_result(job_id) if job_id else {}
                ai_insights = analysis_result.get('ai_insights', {}) if analysis_result else {}
            except:
                ai_insights = {}
            actual_report_data = report_data

        # Serialize report data for template
        serialized_data = {}
        for key, value in actual_report_data.items():
            if hasattr(value, 'to_dict'):
                import numpy as np
                df_clean = value.replace({np.nan: None})
                serialized_data[key] = df_clean.to_dict('records')
            else:
                serialized_data[key] = value

        # Create temporary file for PDF
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(tmp_fd)

        # Render the PDF-specific template (server-side rendered, no JavaScript needed)
        html_content = render_template(
            'pdf_report_template.html',
            report_data=serialized_data,
            metadata=metadata,
            ai_insights=ai_insights
        )

        # PDF-specific CSS for better print formatting
        pdf_css = CSS(string='''
            @page {
                size: letter;
                margin: 0.5in 0.6in 0.75in 0.6in;
                @bottom-center {
                    content: counter(page) " / " counter(pages);
                    font-size: 9pt;
                    color: #666;
                }
            }
            body {
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10pt;
                line-height: 1.4;
            }
            .no-print, .sidebar, nav, .export-btn, button, #map, .leaflet-container {
                display: none !important;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                page-break-inside: auto;
                font-size: 9pt;
            }
            tr {
                page-break-inside: avoid;
                page-break-after: auto;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 6px 8px;
                text-align: left;
            }
            th {
                background-color: #f5f5f5 !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            .section-card {
                page-break-inside: avoid;
                margin-bottom: 20px;
            }
            h1, h2, h3 {
                page-break-after: avoid;
            }
            .header {
                background-color: #003366 !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                color: white !important;
                padding: 15px;
                margin-bottom: 20px;
            }
        ''')

        # Generate PDF using WeasyPrint
        html_doc = HTML(string=html_content, base_url=request.url_root)
        html_doc.write_pdf(tmp_path, stylesheets=[pdf_css])

        # Generate filename
        filename = generate_filename(metadata, '.pdf')

        # Send the file and schedule cleanup
        response = send_file(
            tmp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except:
                pass

        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'PDF export failed: {str(e)}'}), 500


def download_map_pdfs(report_data, metadata, job_id):
    """Download ZIP file with PDF maps for each layer (race, income, lending units, lending dollars)."""
    try:
        import tempfile
        import zipfile
        import shutil
        from playwright.sync_api import sync_playwright
        
        # Create temporary directory for maps
        tmp_dir = tempfile.mkdtemp()
        map_files = []
        
        # Map layer configurations
        layers = [
            {'name': 'race', 'title': 'Race and Minority Distribution'},
            {'name': 'income', 'title': 'Income Distribution'},
            {'name': 'lending_units', 'title': 'Number of Loans (Quartiles)'},
            {'name': 'lending_dollars', 'title': 'Amount of Loans (Quartiles)'}
        ]
        
        # Use Playwright to capture map screenshots
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Build the report URL with job_id and layer parameter
            base_url = request.url_root.rstrip('/')
            
            for layer in layers:
                try:
                    # Navigate to report with specific layer
                    report_url = f"{base_url}/report?job_id={job_id}&map_layer={layer['name']}"
                    page.goto(report_url, wait_until='networkidle', timeout=60000)
                    
                    # Wait for map to load
                    page.wait_for_selector('#tractMap', state='visible', timeout=30000)
                    page.wait_for_timeout(3000)  # Wait for map tiles to load
                    
                    # Take screenshot of map area
                    map_element = page.query_selector('#tractMap')
                    if not map_element:
                        map_element = page.query_selector('#map')  # Fallback
                    if map_element:
                        screenshot_bytes = map_element.screenshot(type='png')
                        
                        # Convert screenshot to PDF with NCRC colors
                        pdf_path = os.path.join(tmp_dir, f"map_{layer['name']}.pdf")
                        create_map_pdf(screenshot_bytes, pdf_path, layer['title'], metadata)
                        map_files.append(pdf_path)
                except Exception as e:
                    print(f"Error creating map PDF for {layer['name']}: {e}")
                    continue
            
            browser.close()
        
        # Create ZIP file with all map PDFs
        zip_fd, zip_path = tempfile.mkstemp(suffix='.zip')
        os.close(zip_fd)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pdf_file in map_files:
                if os.path.exists(pdf_file):
                    zipf.write(pdf_file, os.path.basename(pdf_file))
        
        # Generate filename
        filename = generate_filename(metadata, '_maps.zip')
        
        # Send the file and schedule cleanup
        response = send_file(
            zip_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
        
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(zip_path):
                    os.unlink(zip_path)
                # Clean up temporary directory
                import shutil
                if os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)
            except:
                pass
        
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Map PDF export failed: {str(e)}'}), 500


def create_map_pdf(screenshot_bytes, output_path, title, metadata):
    """Create a PDF from a map screenshot with NCRC branding."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.colors import HexColor
        from PIL import Image
        import io
        
        # NCRC colors
        ncrc_blue = HexColor('#003366')
        
        # Open screenshot
        img = Image.open(io.BytesIO(screenshot_bytes))
        
        # Create PDF in landscape orientation
        c = canvas.Canvas(output_path, pagesize=landscape(letter))
        width, height = landscape(letter)
        
        # Add title with NCRC blue
        c.setFillColor(ncrc_blue)
        c.setFont("Helvetica-Bold", 16)
        county_name = metadata.get('county_name', 'Unknown County')
        state_name = metadata.get('state_name', '')
        title_text = f"{title} - {county_name}"
        if state_name:
            title_text += f", {state_name}"
        c.drawString(50, height - 40, title_text)
        
        # Add NCRC branding
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor('#666666'))
        c.drawString(50, height - 60, "National Community Reinvestment Coalition - BizSight")
        
        # Calculate image dimensions to fit page
        img_width, img_height = img.size
        page_width = width - 100  # Margins
        page_height = height - 100  # Margins for title
        
        # Scale image to fit
        scale = min(page_width / img_width, page_height / img_height)
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        
        # Center image
        x = (width - scaled_width) / 2
        y = (height - scaled_height) / 2 - 30  # Offset for title
        
        # Draw image
        img_reader = ImageReader(io.BytesIO(screenshot_bytes))
        c.drawImage(img_reader, x, y, width=scaled_width, height=scaled_height)
        
        # Add footer
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor('#666666'))
        c.drawString(50, 30, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        c.save()
    except Exception as e:
        print(f"Error creating map PDF: {e}")
        import traceback
        traceback.print_exc()
        raise


# Health check
@app.route('/health')
def health():
    """Health check endpoint."""
    from datetime import datetime
    return jsonify({
        'status': 'healthy',
        'app': 'bizsight',
        'version': __version__,
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', BizSightConfig.PORT))
    print("\n" + "=" * 80, flush=True)
    print("STARTING BIZSIGHT FLASK SERVER", flush=True)
    print("=" * 80, flush=True)
    print(f"Port: {port}", flush=True)
    print(f"Host: {BizSightConfig.HOST}", flush=True)
    print(f"DEBUG mode: {BizSightConfig.DEBUG}", flush=True)
    print(f"TEMPLATES_AUTO_RELOAD: {app.config.get('TEMPLATES_AUTO_RELOAD')}", flush=True)
    print(f"Jinja2 bytecode_cache: {app.jinja_env.bytecode_cache}", flush=True)
    print(f"Template folder: {app.template_folder}", flush=True)
    print(f"Static folder: {app.static_folder}", flush=True)
    print("=" * 80, flush=True)
    print(f"\nServer starting at http://{BizSightConfig.HOST}:{port}", flush=True)
    print("Press Ctrl+C to stop\n", flush=True)
    app.run(debug=BizSightConfig.DEBUG, host=BizSightConfig.HOST, port=port, use_reloader=True)
