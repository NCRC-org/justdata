"""
BizSight Blueprint for main JustData app.
Converts the standalone BizSight app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, session, Response, send_file, make_response, url_for
from jinja2 import ChoiceLoader, FileSystemLoader
import os
import time
from pathlib import Path
from datetime import datetime

from justdata.main.auth import require_access, get_user_permissions, get_user_type, login_required, is_privileged_user
from justdata.backend import (
    new_job_id, run_in_background, sse_response,
    identify_caller, lookup_cached_analysis, record_cache_hit, record_completion,
)
from justdata.shared.utils.analysis_cache import store_cached_result, get_analysis_result_by_job_id
from justdata.shared.utils.bigquery_client import escape_sql_string
from justdata.apps.bizsight.config import BizSightConfig, TEMPLATES_DIR_STR, STATIC_DIR_STR
from justdata.apps.bizsight.core import run_analysis
from justdata.apps.bizsight.data_utils import get_available_counties, get_available_years
from justdata.shared.utils.progress_tracker import create_progress_tracker, get_progress

# In-memory fallback for when BigQuery cache storage fails
_result_fallback = {}

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
    """Configure Jinja2 to search blueprint templates first.

    IMPORTANT: Blueprint templates must come FIRST in the ChoiceLoader so that
    app-specific templates (like report_template.html) are found before shared
    templates with the same name.

    NOTE: We do NOT add shared_loader here because the main app already includes
    shared templates. Adding it again would cause shared templates to be searched
    BEFORE other blueprint templates, leading to wrong template being rendered
    (e.g., BranchSight's report_template.html instead of BizSight's).
    """
    app = state.app
    blueprint_loader = FileSystemLoader(TEMPLATES_DIR_STR)
    app.jinja_loader = ChoiceLoader([
        blueprint_loader,  # Blueprint templates first (highest priority)
        app.jinja_loader   # Main app loader (already includes shared templates)
    ])


@bizsight_bp.route('/')
@login_required
@require_access('bizsight', 'limited')
def index():
    """Main page with the US map for county selection."""
    user_permissions = get_user_permissions()
    user_type = get_user_type()
    # Privileged users (staff, senior_executive, admin) see the "clear cache" checkbox
    is_staff = is_privileged_user(user_type)
    app_base_url = url_for('bizsight.index').rstrip('/')

    # Breadcrumb for main page
    breadcrumb_items = [{'name': 'BizSight', 'url': '/bizsight'}]

    # Force template reload by clearing cache before rendering
    response = make_response(render_template(
        'bizsight_analysis.html',
        version=BizSightConfig.APP_VERSION,
        permissions=user_permissions,
        is_staff=is_staff,
        app_base_url=app_base_url,
        app_name='BizSight',
        breadcrumb_items=breadcrumb_items
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
@login_required
def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events."""
    return sse_response(job_id)


@bizsight_bp.route('/analyze', methods=['POST'])
@login_required
@require_access('bizsight', 'limited')
def analyze():
    """Handle analysis request with caching."""
    start_time = time.time()
    request_id = new_job_id()
    
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
        
        caller = identify_caller()
        user_type = caller.user_type
        if not caller.user_id and not caller.user_email:
            print(f"[WARN] BizSight analyze: No user identity captured despite @login_required")

        # Prepare parameters for cache lookup
        cache_params = {
            'county_data': county_data,
            'startYear': start_year,
            'endYear': end_year,
            'years': years_str
        }

        def remember_in_session(active_job_id):
            session['county_data'] = county_data
            session['years'] = years_str
            session['job_id'] = active_job_id

        cached = lookup_cached_analysis(
            'bizsight', cache_params, caller,
            force_refresh_requested=bool(data.get('force_refresh', False)),
        )

        if cached:
            # Reuse the stored result instead of re-running BigQuery and Claude
            remember_in_session(cached.job_id)
            record_cache_hit('bizsight', cache_params, caller, cached,
                             start_time, request_id)
            return jsonify({
                'success': True,
                'job_id': cached.job_id,
                'cached': True
            })

        # Cache miss - run new analysis
        job_id = new_job_id()
        progress_tracker = create_progress_tracker(job_id)
        remember_in_session(job_id)

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
                    record_completion('bizsight', cache_params, caller, job_id,
                                      start_time, request_id, error_message=error_msg)
                    return
                
                # Store in BigQuery cache BEFORE marking as complete
                # This ensures report-data can retrieve the data
                print(f"[DEBUG] Starting storage for job_id: {job_id}")
                try:
                    metadata = {
                        'counties': [county_data] if not isinstance(county_data, list) else county_data,
                        'years': years,
                        'duration_seconds': time.time() - start_time,
                        'total_records': result.get('metadata', {}).get('total_records', 0) if isinstance(result.get('metadata'), dict) else 0,
                        'loan_purpose': result.get('metadata', {}).get('loan_purpose', ['purchase']) if isinstance(result.get('metadata'), dict) else ['purchase'],
                        'census_data': result.get('metadata', {}).get('census_data', None) if isinstance(result.get('metadata'), dict) else None,
                        'generated_at': datetime.now().isoformat()
                    }

                    store_cached_result(
                        app_name='bizsight',
                        params=cache_params,
                        job_id=job_id,
                        result_data=result,
                        user_type=user_type,
                        metadata=metadata
                    )
                    print(f"[DEBUG] Storage completed successfully for job_id: {job_id}")
                    progress_tracker.complete(success=True)
                except Exception as cache_error:
                    print(f"WARNING: Failed to store in BigQuery cache: {cache_error}")
                    import traceback
                    traceback.print_exc()
                    # Store result in-memory fallback so user can still see results
                    _result_fallback[job_id] = result
                    progress_tracker.complete(success=True)

                print(f"[DEBUG] Progress marked complete for job_id: {job_id}")

                record_completion('bizsight', cache_params, caller, job_id,
                                  start_time, request_id,
                                  costs={'bigquery': 2.0, 'ai': 0.3, 'total': 2.3})

            except Exception as e:
                error_msg = str(e)
                progress_tracker.complete(success=False, error=error_msg)
                record_completion('bizsight', cache_params, caller, job_id,
                                  start_time, request_id, error_message=error_msg)

        run_in_background(run_job)

        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        # The failure may predate caller/cache_params being set, so fall back.
        record_completion(
            'bizsight',
            cache_params if 'cache_params' in locals() else {},
            caller if 'caller' in locals() else identify_caller(),
            job_id if 'job_id' in locals() else new_job_id(),
            start_time, request_id, error_message=str(e),
        )
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500


@bizsight_bp.route('/data', methods=['GET'])
@login_required
@require_access('bizsight', 'limited')
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
@login_required
@require_access('bizsight', 'limited')
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


@bizsight_bp.route('/api/planning-regions', methods=['GET'])
@login_required
@require_access('bizsight', 'limited')
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


@bizsight_bp.route('/api/counties-by-state/<state_code>', methods=['GET'])
@login_required
@require_access('bizsight', 'limited')
def get_counties_by_state(state_code):
    """Get counties for a specific state.

    Uses the shared BigQuery client directly (like LendSight and the working app.py).
    This fixes the issue where counties were returning empty results.
    """
    try:
        from urllib.parse import unquote
        from justdata.shared.utils.bigquery_client import get_bigquery_client

        # URL decode the state code
        state_code = unquote(str(state_code)).strip()
        print(f"[DEBUG] bizsight/api/counties-by-state called with state_code: '{state_code}'")

        # Use justdata-ncrc for shared tables (cbsa_to_county is always in justdata-ncrc)
        client = get_bigquery_client(project_id='justdata-ncrc', app_name='bizsight')

        # Check if state_code is a numeric FIPS code (2 digits) or a state name
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
            FROM `justdata-ncrc.shared.cbsa_to_county`
            WHERE geoid5 IS NOT NULL
                AND SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) = '{state_code_padded}'
                AND county_state IS NOT NULL
                AND TRIM(county_state) != ''
            ORDER BY county_state
            """
        else:
            # Use state name to match (extract from county_state)
            print(f"[DEBUG] Using state name: {state_code}")
            escaped_state_code = escape_sql_string(state_code)
            query = f"""
            SELECT DISTINCT
                county_state,
                geoid5,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as county_fips
            FROM `justdata-ncrc.shared.cbsa_to_county`
            WHERE LOWER(TRIM(SPLIT(county_state, ',')[SAFE_OFFSET(1)])) = LOWER('{escaped_state_code}')
                AND county_state IS NOT NULL
                AND TRIM(county_state) != ''
            ORDER BY county_state
            """

        query_job = client.query(query)
        results = list(query_job.result())

        # Return counties with proper structure
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
            state_fips = row.state_fips if hasattr(row, 'state_fips') else (geoid5[:2] if geoid5 and len(geoid5) >= 2 else None)
            county_fips = row.county_fips if hasattr(row, 'county_fips') else (geoid5[2:] if geoid5 and len(geoid5) >= 5 else None)

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

        print(f"[DEBUG] bizsight/api/counties-by-state: Found {len(counties)} counties for state_code: {state_code}")
        if counties:
            print(f"[DEBUG] Sample counties: {counties[:3]}")
        else:
            print(f"[WARNING] No counties found for state_code: {state_code}")

        return jsonify(counties)
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"[ERROR] bizsight/api/counties-by-state error: {error_msg}")
        return jsonify({'error': error_msg}), 500


@bizsight_bp.route('/api/county-boundaries', methods=['GET'])
@login_required
@require_access('bizsight', 'limited')
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
@login_required
@require_access('bizsight', 'limited')
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
@login_required
@require_access('bizsight', 'limited')
def get_tract_boundaries_endpoint(geoid5):
    """Get census tract boundaries for a county."""
    try:
        from justdata.apps.bizsight.utils.tract_boundaries import get_tract_boundaries
        boundaries = get_tract_boundaries(geoid5)
        if boundaries is None:
            return jsonify({'success': False, 'error': 'No tract boundaries found', 'geojson': None}), 404
        return jsonify({'success': True, 'geojson': boundaries})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'geojson': None}), 500


@bizsight_bp.route('/report', methods=['GET'])
@login_required
@require_access('bizsight', 'limited')
def report():
    """Report display page."""
    job_id = request.args.get('job_id')
    if not job_id:
        return jsonify({'error': 'Job ID required'}), 400

    # Pass app_base_url so template can correctly construct API URLs
    app_base_url = url_for('bizsight.index').rstrip('/')

    # Breadcrumb for report page
    breadcrumb_items = [
        {'name': 'BizSight', 'url': '/bizsight'},
        {'name': 'Report', 'url': '/bizsight/report'}
    ]

    return render_template(
        'bizsight_report.html',
        job_id=job_id,
        app_base_url=app_base_url,
        app_name='BizSight',
        breadcrumb_items=breadcrumb_items
    )


@bizsight_bp.route('/report-data', methods=['GET'])
@login_required
@require_access('bizsight', 'limited')
def report_data():
    """Return the analysis report data for web display."""
    try:
        # Check for job_id in URL parameters first, then session
        job_id = request.args.get('job_id') or session.get('job_id')

        if not job_id:
            return jsonify({
                'success': False,
                'error': 'No analysis session found. Please run an analysis first.'
            }), 400

        # Retrieve from BigQuery cache, with in-memory fallback
        analysis_result = get_analysis_result_by_job_id(job_id)
        if not analysis_result and job_id in _result_fallback:
            analysis_result = _result_fallback.pop(job_id)
            print(f"[INFO] Using in-memory fallback for job_id={job_id}")
        if not analysis_result:
            # Check progress to see if analysis is still running
            progress = get_progress(job_id)
            if not progress.get('done', False):
                response = jsonify({
                    'success': False,
                    'error': 'Analysis still in progress',
                    'progress': progress
                })
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                return response, 202  # 202 Accepted - still processing

            response = jsonify({
                'success': False,
                'error': 'No analysis data found. The analysis may have expired or failed.',
                'progress': progress
            })
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response, 404

        # BizSight result structure is already flattened by get_analysis_result_by_job_id
        # Extract the relevant data fields
        import pandas as pd
        import numpy as np
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
            elif hasattr(obj, 'to_dict'):
                # Handle pandas DataFrames
                return obj.replace({np.nan: None}).to_dict('records')
            else:
                return obj

        # Clean all data for JSON serialization
        cleaned_result = clean_for_json(analysis_result)

        # Ensure success flag is present
        cleaned_result['success'] = True

        # Return with cache-control headers to prevent browser caching
        response = jsonify(cleaned_result)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'An error occurred while loading report data: {str(e)}'
        }), 500


@bizsight_bp.route('/download', methods=['GET'])
@login_required
@require_access('bizsight', 'full')
def download():
    """Download analysis results."""
    try:
        # Check for job_id in URL parameters first, then session
        job_id = request.args.get('job_id') or session.get('job_id')
        format_type = request.args.get('format', 'excel')  # excel, pdf, powerpoint

        if not job_id:
            return jsonify({'error': 'No analysis session found. Please run an analysis first.'}), 400
        
        # Check user permissions for export
        user_permissions = get_user_permissions()
        if not user_permissions.get('can_export', False):
            return jsonify({
                'error': 'Export functionality is not available for your account type.'
            }), 403
        
        # Check if format is allowed (zip requires excel permission)
        allowed_formats = user_permissions.get('export_formats', [])
        check_format = 'excel' if format_type == 'zip' else format_type
        if check_format not in allowed_formats:
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
        if format_type in ('zip', 'excel'):
            from justdata.apps.bizsight.excel_export import save_bizsight_excel_report
            from justdata.apps.bizsight.pdf_report import generate_bizsight_pdf
            import tempfile
            import zipfile
            import io
            import re

            # Generate Excel
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
            os.close(tmp_fd)
            save_bizsight_excel_report(result, tmp_path, metadata=metadata)

            # Generate PDF
            pdf_buf = generate_bizsight_pdf(result, metadata)

            # Build filenames
            county_data = metadata.get('county_data', {})
            county_name = county_data.get('name', 'County') if isinstance(county_data, dict) else str(county_data) if county_data else 'County'
            safe_name = re.sub(r'[^\w\s-]', '', county_name).replace(' ', '_')[:50]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            xlsx_filename = f'BizSight_{safe_name}_{timestamp}.xlsx'
            pdf_filename = f'BizSight_{safe_name}_{timestamp}.pdf'
            zip_filename = f'BizSight_{safe_name}_{timestamp}.zip'

            # Bundle into ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(tmp_path, xlsx_filename)
                zf.writestr(pdf_filename, pdf_buf.getvalue())
            zip_buffer.seek(0)

            try:
                os.unlink(tmp_path)
            except OSError:
                pass

            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )
        elif format_type == 'pdf':
            from justdata.apps.bizsight.pdf_report import generate_bizsight_pdf
            pdf_buf = generate_bizsight_pdf(result, metadata)
            county_data = metadata.get('county_data', {})
            county_name = county_data.get('name', 'County') if isinstance(county_data, dict) else str(county_data) if county_data else 'County'
            safe_name = county_name.replace(',', '').replace(' ', '_')[:50]
            filename = f'BizSight_{safe_name}.pdf'
            return Response(
                pdf_buf.getvalue(),
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
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

