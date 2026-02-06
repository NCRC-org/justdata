"""
BranchSight Blueprint for main JustData app.
Converts the standalone BranchSight app into a blueprint for the unified platform.
"""

from flask import Blueprint, render_template, request, jsonify, session, Response, make_response, send_file, url_for, send_from_directory
from jinja2 import ChoiceLoader, FileSystemLoader
import os
import tempfile
import uuid
import threading
import time
import json
import zipfile
from datetime import datetime
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, get_user_type, login_required
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker, store_analysis_result, get_analysis_result
from .core import run_analysis, parse_web_parameters
from .config import TEMPLATES_DIR, STATIC_DIR, PROJECT_ID
from .data_utils import get_available_counties, get_available_states, get_available_metro_areas, find_exact_county_match, get_fallback_states, get_fallback_counties
from .version import __version__

# Get shared templates directory
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# Convert TEMPLATES_DIR and STATIC_DIR to Path objects if they're strings
TEMPLATES_DIR_PATH = Path(TEMPLATES_DIR) if isinstance(TEMPLATES_DIR, str) else TEMPLATES_DIR
STATIC_DIR_PATH = Path(STATIC_DIR) if isinstance(STATIC_DIR, str) else STATIC_DIR

# Create blueprint
branchsight_bp = Blueprint(
    'branchsight',
    __name__,
    template_folder=str(TEMPLATES_DIR_PATH),
    static_folder=str(STATIC_DIR_PATH),
    static_url_path='/branchsight/static'
)


@branchsight_bp.record_once
def configure_template_loader(state):
    """Configure Jinja2 to search blueprint templates first, then shared templates.

    IMPORTANT: Blueprint templates must come FIRST in the ChoiceLoader so that
    app-specific templates (like report_template.html) are found before shared
    templates or other blueprints' templates with the same name.
    """
    app = state.app
    blueprint_loader = FileSystemLoader(str(TEMPLATES_DIR_PATH))
    shared_loader = FileSystemLoader(str(SHARED_TEMPLATES_DIR))
    app.jinja_loader = ChoiceLoader([
        blueprint_loader,  # Blueprint templates first (highest priority)
        shared_loader,     # Shared templates (for report_interstitial.html, etc.)
        app.jinja_loader   # Main app loader (fallback)
    ])


@branchsight_bp.route('/')
@login_required
@require_access('branchsight', 'partial')
def index():
    """Main page with the analysis form"""
    user_permissions = get_user_permissions()
    user_type = get_user_type()
    # Staff and admin users can see the "clear cache" checkbox
    is_staff = (user_type in ('staff', 'admin'))
    cache_buster = int(time.time())
    app_base_url = url_for('branchsight.index').rstrip('/')
    response = make_response(render_template('branchsight_analysis.html',
                                           permissions=user_permissions,
                                           is_staff=is_staff,
                                           cache_buster=cache_buster,
                                           app_base_url=app_base_url,
                                           version=__version__))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@branchsight_bp.route('/progress/<job_id>')
@login_required
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


@branchsight_bp.route('/analyze', methods=['POST'])
@require_access('branchsight', 'partial')
def analyze():
    """Handle analysis request"""
    try:
        data = request.get_json()
        selection_type = data.get('selection_type', 'county')
        counties_str = data.get('counties', '').strip()
        years = data.get('years', '').strip()
        state_code = data.get('state_code', None)
        metro_code = data.get('metro_code', None)
        job_id = str(uuid.uuid4())

        # Create progress tracker for this job
        progress_tracker = create_progress_tracker(job_id)

        # Validate inputs based on selection type
        if selection_type == 'county':
            if not state_code:
                return jsonify({'error': 'Please select a state'}), 400
            if not counties_str:
                return jsonify({'error': 'Please select a county'}), 400
            # Check if multiple counties were selected
            counties_list_check = [c.strip() for c in counties_str.split(';') if c.strip()]
            if len(counties_list_check) > 1:
                return jsonify({'error': 'Please select only one county at a time'}), 400
        elif selection_type == 'state' and not state_code:
            return jsonify({'error': 'Please select a state'}), 400
        elif selection_type == 'metro' and not metro_code:
            return jsonify({'error': 'Please select a metro area'}), 400

        if not years:
            return jsonify({'error': 'Please provide years'}), 400

        # Parse parameters
        try:
            counties_list, years_list = parse_web_parameters(
                counties_str, years, selection_type, state_code, metro_code
            )
        except Exception as e:
            return jsonify({'error': f'Error parsing parameters: {str(e)}'}), 400

        # Store in session for download
        session['counties'] = ';'.join(counties_list) if counties_list else counties_str
        session['years'] = years
        session['job_id'] = job_id
        session['selection_type'] = selection_type

        def run_job():
            try:
                result = run_analysis(';'.join(counties_list), ','.join(map(str, years_list)), job_id, progress_tracker,
                                       selection_type, state_code, metro_code)

                if not result.get('success'):
                    error_msg = result.get('error', 'Unknown error')
                    progress_tracker.update_progress('error', error_msg)
                    return

                # Store the analysis results
                store_analysis_result(job_id, result)

                # Mark analysis as completed
                progress_tracker.complete(success=True)

            except Exception as e:
                error_msg = str(e)
                progress_tracker.complete(success=False, error=error_msg)

        threading.Thread(target=run_job, daemon=True).start()

        return jsonify({'success': True, 'job_id': job_id})

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500


@branchsight_bp.route('/report')
@require_access('branchsight', 'partial')
def report():
    """Report display page"""
    from jinja2 import Environment, ChoiceLoader, FileSystemLoader, select_autoescape
    app_base_url = url_for('branchsight.index').rstrip('/')
    # Create a custom Environment that searches branchsight templates FIRST,
    # then shared templates. This prevents loading wrong template when multiple
    # blueprints have templates with the same name (e.g., report_template.html)
    env = Environment(
        loader=ChoiceLoader([
            FileSystemLoader(str(TEMPLATES_DIR_PATH)),  # BranchSight templates first
            FileSystemLoader(str(SHARED_TEMPLATES_DIR))  # Shared templates (for shared_header.html)
        ]),
        autoescape=select_autoescape(['html', 'xml'])
    )
    env.globals['url_for'] = url_for
    template = env.get_template('report_template.html')
    return template.render(app_base_url=app_base_url, version=__version__)


@branchsight_bp.route('/report-data')
@require_access('branchsight', 'partial')
def report_data():
    """Return the analysis report data for web display"""
    try:
        job_id = request.args.get('job_id') or session.get('job_id')
        if not job_id:
            return jsonify({'error': 'No analysis session found'}), 404

        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found'}), 404

        # Convert pandas DataFrames to JSON-serializable format
        report_data = analysis_result.get('report_data', {})
        serialized_data = {}

        import numpy as np
        import pandas as pd

        for key, df in report_data.items():
            if key == 'hhi_by_year':
                serialized_data[key] = df if isinstance(df, list) else []
            elif hasattr(df, 'to_dict'):
                df_clean = df.replace({np.nan: None})
                serialized_data[key] = df_clean.to_dict('records')
            else:
                serialized_data[key] = df

        ai_insights = analysis_result.get('ai_insights', {})

        return jsonify({
            'success': True,
            'data': serialized_data,
            'metadata': {
                **analysis_result.get('metadata', {}),
                'ai_insights': ai_insights
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve report data: {str(e)}'
        }), 500


@branchsight_bp.route('/download')
@require_access('branchsight', 'partial')
def download():
    """Download the generated reports in various formats"""
    try:
        format_type = request.args.get('format', 'excel').lower()
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

        if format_type == 'excel':
            return download_excel(report_data, metadata)
        elif format_type == 'csv':
            return download_csv(report_data, metadata)
        elif format_type == 'json':
            return download_json(report_data, metadata)
        elif format_type == 'zip':
            return download_zip(report_data, metadata)
        else:
            return jsonify({'error': f'Invalid format specified: {format_type}. Valid formats are: excel, csv, json, zip'}), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }), 500


def download_excel(report_data, metadata):
    """Download Excel file"""
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(tmp_fd)

        from justdata.shared.reporting.report_builder import save_excel_report
        save_excel_report(report_data, tmp_path, metadata=metadata)

        response = send_file(
            tmp_path,
            as_attachment=True,
            download_name=f'branchsight_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
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


def download_csv(report_data, metadata):
    """Download CSV file (summary data only)"""
    try:
        import io
        import csv

        output = io.StringIO()
        writer = csv.writer(output)

        if 'summary' in report_data and not report_data['summary'].empty:
            df = report_data['summary']
            writer.writerow(df.columns.tolist())
            for _, row in df.iterrows():
                writer.writerow(row.tolist())

        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=branchsight_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
    except Exception as e:
        return jsonify({'error': f'CSV export failed: {str(e)}'}), 500


def download_json(report_data, metadata):
    """Download JSON file"""
    try:
        import numpy as np

        serialized_data = {}
        for key, df in report_data.items():
            if hasattr(df, 'to_dict'):
                df_clean = df.replace({np.nan: None})
                serialized_data[key] = df_clean.to_dict('records')
            else:
                serialized_data[key] = df

        export_data = {
            'metadata': metadata,
            'data': serialized_data
        }

        return Response(
            json.dumps(export_data, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=branchsight_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            }
        )
    except Exception as e:
        return jsonify({'error': f'JSON export failed: {str(e)}'}), 500


def download_zip(report_data, metadata):
    """Download ZIP file with multiple formats"""
    try:
        import numpy as np

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'branchsight_reports.zip')

            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Generate and add Excel file
                excel_path = os.path.join(temp_dir, 'fdic_branch_analysis.xlsx')
                from justdata.shared.reporting.report_builder import save_excel_report
                save_excel_report(report_data, excel_path, metadata=metadata)
                if os.path.exists(excel_path):
                    zipf.write(excel_path, 'fdic_branch_analysis.xlsx')

                # Add JSON file
                json_data = {}
                for key, df in report_data.items():
                    if hasattr(df, 'to_dict'):
                        df_clean = df.replace({np.nan: None})
                        json_data[key] = df_clean.to_dict('records')
                    else:
                        json_data[key] = df

                json_content = json.dumps({
                    'metadata': metadata,
                    'data': json_data
                }, indent=2)
                zipf.writestr('analysis_data.json', json_content)

            with open(zip_path, 'rb') as f:
                zip_content = f.read()

            return Response(
                zip_content,
                mimetype='application/zip',
                headers={
                    'Content-Disposition': f'attachment; filename=branchsight_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
                }
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'ZIP export failed: {str(e)}'}), 500


@branchsight_bp.route('/counties')
@login_required
@require_access('branchsight', 'partial')
def counties():
    """Return a list of all available counties"""
    try:
        counties_list = get_available_counties()
        print(f"Successfully fetched {len(counties_list)} counties")
        return jsonify(counties_list)
    except Exception as e:
        print(f"Error in counties endpoint: {e}")
        import traceback
        traceback.print_exc()
        from .data_utils import get_fallback_counties
        return jsonify(get_fallback_counties())


@branchsight_bp.route('/states')
@login_required
@require_access('branchsight', 'partial')
def states():
    """Return a list of all available states"""
    try:
        states_list = get_available_states()
        print(f"States endpoint: Returning {len(states_list)} states")
        return jsonify(states_list)
    except Exception as e:
        print(f"Error in states endpoint: {e}")
        import traceback
        traceback.print_exc()
        from .data_utils import get_fallback_states
        return jsonify(get_fallback_states())


@branchsight_bp.route('/metro-areas')
@login_required
@require_access('branchsight', 'partial')
def metro_areas():
    """Return a list of all available metro areas (CBSAs)"""
    try:
        metros_list = get_available_metro_areas()
        print(f"Metro areas endpoint: Returning {len(metros_list)} metro areas")
        return jsonify(metros_list)
    except Exception as e:
        print(f"Error in metro_areas endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@branchsight_bp.route('/counties-by-state/<state_code>')
@login_required
@require_access('branchsight', 'partial')
def counties_by_state(state_code):
    """Get list of counties for a specific state.

    Handles both FIPS codes (e.g., '11' for DC) and state names.
    """
    try:
        from urllib.parse import unquote
        from justdata.shared.utils.bigquery_client import get_bigquery_client

        state_code = unquote(str(state_code)).strip()
        print(f"[DEBUG] branchsight/counties-by-state called with state_code: '{state_code}'")

        client = get_bigquery_client(PROJECT_ID)

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
            FROM `justdata-ncrc.shared.cbsa_to_county`
            WHERE geoid5 IS NOT NULL
                AND SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) = '{state_code_padded}'
                AND county_state IS NOT NULL
                AND TRIM(county_state) != ''
            ORDER BY county_state
            """
        else:
            # Use state name to match
            print(f"[DEBUG] Using state name: {state_code}")
            escaped_state_code = state_code.replace("'", "''")
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

        print(f"[DEBUG] branchsight/counties-by-state: Found {len(counties)} counties for state_code: {state_code}")
        return jsonify(counties)
    except Exception as e:
        import traceback
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"[ERROR] branchsight/counties-by-state error: {error_msg}")
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


@branchsight_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'branchsight',
        'version': __version__
    })
