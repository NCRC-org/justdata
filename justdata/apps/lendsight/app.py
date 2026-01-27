#!/usr/bin/env python3
"""
LendSight Flask web application.
Uses the same routing patterns as BranchSight and BizSight.
"""

from flask import render_template, request, jsonify, session, Response, make_response, send_from_directory
import os
import tempfile
import uuid
import threading
import time
import json
from werkzeug.middleware.proxy_fix import ProxyFix

from justdata.shared.core.app_factory import create_app, register_standard_routes
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker
from justdata.shared.utils.env_utils import is_local_development
from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from pathlib import Path

from justdata.apps.lendsight.config import TEMPLATES_DIR, STATIC_DIR
from justdata.apps.lendsight.core import run_analysis
from justdata.apps.lendsight.version import __version__

# Get package root for shared static files
PACKAGE_ROOT = Path(__file__).parent.parent.parent.absolute()

# Load unified environment configuration
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)

# Print environment summary
print(f"[ENV] Environment: {'LOCAL' if config['IS_LOCAL'] else 'PRODUCTION'}")
print(f"[ENV] Shared config loaded from: {config.get('SHARED_ENV_FILE', 'Environment variables')}")

# Create the Flask app
app = create_app(
    'lendsight',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

# Add ProxyFix for proper request handling behind proxies
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Configure cache-busting
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# DISABLE Jinja2 bytecode cache
app.jinja_env.bytecode_cache = None

# Force reload templates on every request
@app.before_request
def clear_template_cache():
    """Clear Jinja2 template cache before each request."""
    if hasattr(app, 'jinja_env'):
        app.jinja_env.bytecode_cache = None
        app.jinja_env.cache = {}
        app.jinja_env.auto_reload = True


@app.route('/shared/population_demographics.js')
def shared_population_demographics_js():
    """Serve shared population demographics JavaScript module"""
    shared_static_dir = PACKAGE_ROOT / 'shared' / 'web' / 'static' / 'js'
    js_path = shared_static_dir / 'population_demographics.js'
    if js_path.exists():
        return send_from_directory(str(shared_static_dir), 'population_demographics.js', mimetype='application/javascript')
    return '', 404


def index():
    """Main page with the analysis form"""
    cache_buster = int(time.time())
    breadcrumb_items = [{'name': 'LendSight', 'url': '/lendsight'}]
    response = make_response(render_template(
        'analysis_template.html',
        version=__version__,
        cache_buster=cache_buster,
        app_name='LendSight',
        breadcrumb_items=breadcrumb_items
    ))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events"""
    def event_stream():
        last_percent = -1
        last_step = ""
        keepalive_counter = 0
        max_keepalive = 20

        try:
            yield f": connected\n\n"

            while True:
                try:
                    progress = get_progress(job_id)
                    if not progress:
                        progress = {'percent': 0, 'step': 'Starting...', 'done': False, 'error': None}

                    percent = progress.get("percent", 0)
                    step = progress.get("step", "Starting...")
                    done = progress.get("done", False)
                    error = progress.get("error", None)

                    step_escaped = step.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')

                    if percent != last_percent or step != last_step or done or error:
                        yield f"data: {{\"percent\": {percent}, \"step\": \"{step_escaped}\", \"done\": {str(done).lower()}, \"error\": {json.dumps(error) if error else 'null'}}}\n\n"
                        last_percent = percent
                        last_step = step
                        keepalive_counter = 0

                    if done or error:
                        time.sleep(0.2)
                        break

                    keepalive_counter += 1
                    if keepalive_counter >= max_keepalive:
                        yield f": keepalive\n\n"
                        keepalive_counter = 0

                    time.sleep(0.5)

                except GeneratorExit:
                    break
                except Exception as e:
                    print(f"Error in progress stream for {job_id}: {e}")
                    break
        except Exception as e:
            print(f"Fatal error in progress stream for {job_id}: {e}")

    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response


@app.route('/progress', methods=['GET'])
def progress_status():
    """JSON endpoint to check progress status"""
    try:
        job_id = request.args.get('job_id')
        if not job_id:
            return jsonify({'error': 'job_id parameter required'}), 400

        progress = get_progress(job_id)
        if not progress:
            return jsonify({
                'percent': 0,
                'step': 'Job not found',
                'done': False,
                'error': None
            })
        return jsonify(progress)
    except Exception as e:
        return jsonify({
            'percent': 0,
            'step': 'Error checking progress',
            'done': False,
            'error': str(e)
        }), 500


def analyze():
    """Handle analysis request"""
    try:
        data = request.get_json()
        print(f"[DEBUG] analyze endpoint - received data: {data}")
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400

        selection_type = data.get('selection_type', 'county')
        counties_data = data.get('counties_data', None)
        if not counties_data:
            counties_data = data.get('counties', [])
        years = data.get('years', '').strip()
        state_code = data.get('state_code', None)
        loan_purpose = data.get('loan_purpose', ['purchase'])

        job_id = str(uuid.uuid4())
        progress_tracker = create_progress_tracker(job_id)

        # Parse counties
        counties_list = []
        counties_with_fips = []

        if isinstance(counties_data, list):
            for c in counties_data:
                if isinstance(c, dict) and c.get('name'):
                    counties_list.append(c['name'])
                    counties_with_fips.append(c)
                elif isinstance(c, str):
                    counties_list.append(c.strip())
        else:
            counties_str = str(counties_data).strip()
            if ',' in counties_str:
                counties_list = [c.strip() for c in counties_str.split(',') if c.strip()]
            else:
                counties_list = [c.strip() for c in counties_str.split(';') if c.strip()]

        counties_list = list(dict.fromkeys(counties_list))

        if len(counties_list) > 3:
            return jsonify({'success': False, 'error': f'Please select a maximum of 3 counties. You selected {len(counties_list)} counties.'}), 400
        if len(counties_list) == 0:
            return jsonify({'success': False, 'error': 'Please select at least one county'}), 400
        if not years:
            return jsonify({'success': False, 'error': 'Please provide years'}), 400

        counties_str = ';'.join(counties_list)

        from justdata.apps.lendsight.core import parse_web_parameters
        counties_list, years_list = parse_web_parameters(
            counties_str, years, selection_type, state_code, None
        )

        session['counties'] = ';'.join(counties_list) if counties_list else counties_str
        session['years'] = years
        session['job_id'] = job_id
        session['selection_type'] = selection_type
        session['loan_purpose'] = loan_purpose

        def run_job():
            try:
                result = run_analysis(
                    ';'.join(counties_list),
                    ','.join(map(str, years_list)),
                    job_id,
                    progress_tracker,
                    selection_type,
                    state_code,
                    None,
                    loan_purpose,
                    counties_with_fips if counties_with_fips else None
                )

                if not result.get('success'):
                    error_msg = result.get('error', 'Unknown error')
                    progress_tracker.update_progress('error', error_msg)
                    return

                from justdata.shared.utils.progress_tracker import store_analysis_result
                store_analysis_result(job_id, result)
                progress_tracker.complete(success=True)

            except Exception as e:
                error_msg = str(e)
                progress_tracker.complete(success=False, error=error_msg)

        threading.Thread(target=run_job, daemon=True).start()
        return jsonify({'success': True, 'job_id': job_id})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500


def report():
    """Report display page"""
    breadcrumb_items = [
        {'name': 'LendSight', 'url': '/lendsight'},
        {'name': 'Report', 'url': '/lendsight/report'}
    ]
    return render_template(
        'report_template.html',
        version=__version__,
        app_name='LendSight',
        breadcrumb_items=breadcrumb_items
    )


def download():
    """Download the generated reports"""
    try:
        format_type = request.args.get('format', 'excel').lower()
        job_id = request.args.get('job_id') or session.get('job_id')

        if not job_id:
            return jsonify({'error': 'No analysis session found.'}), 400

        from justdata.shared.utils.progress_tracker import get_analysis_result
        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found.'}), 400

        report_data = analysis_result.get('report_data', {})
        metadata = analysis_result.get('metadata', {})

        if not report_data:
            return jsonify({'error': 'No report data available.'}), 400

        if format_type == 'excel':
            return download_excel(report_data, metadata)
        elif format_type == 'pdf':
            return download_pdf(report_data, metadata)
        else:
            return jsonify({'error': f'Invalid format: {format_type}'}), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }), 500


def generate_filename(metadata, extension='.xlsx'):
    """Generate a filename for downloads"""
    import re
    from datetime import datetime

    counties = metadata.get('counties', [])
    if isinstance(counties, dict):
        counties = list(counties.values()) if counties.values() else list(counties.keys())
    elif not isinstance(counties, (list, tuple)):
        counties = [counties] if counties else []

    if not counties:
        return f'NCRC_LendSight_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}{extension}'

    first_county = str(counties[0])
    if ',' in first_county:
        county_name, state_name = [part.strip() for part in first_county.rsplit(',', 1)]
    else:
        county_name = first_county
        state_name = ''

    def clean_name(name):
        name = re.sub(r'\s+County\s*$', '', name, flags=re.IGNORECASE)
        name = name.replace(',', '')
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[\s-]+', '_', name)
        return name

    county_clean = clean_name(county_name)
    state_clean = clean_name(state_name) if state_name else ''
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if state_clean:
        filename = f'NCRC_LendSight_{county_clean}_{state_clean}_{timestamp}{extension}'
    else:
        filename = f'NCRC_LendSight_{county_clean}_{timestamp}{extension}'

    return filename


def download_excel(report_data, metadata):
    """Download Excel file"""
    try:
        from flask import send_file

        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(tmp_fd)

        from justdata.apps.lendsight.mortgage_report_builder import save_mortgage_excel_report
        save_mortgage_excel_report(report_data, tmp_path, metadata=metadata)

        filename = generate_filename(metadata, '.xlsx')

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


def download_pdf(report_data, metadata):
    """Download PDF file"""
    try:
        from flask import send_file
        from weasyprint import HTML, CSS

        from justdata.shared.utils.progress_tracker import get_analysis_result
        job_id = request.args.get('job_id') or session.get('job_id')
        analysis_result = get_analysis_result(job_id) if job_id else {}
        ai_insights = analysis_result.get('ai_insights', {})

        # Serialize report data
        serialized_data = {}
        for key, df in report_data.items():
            if hasattr(df, 'to_dict'):
                import numpy as np
                df_clean = df.replace({np.nan: None})
                serialized_data[key] = df_clean.to_dict('records')
            else:
                serialized_data[key] = df

        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(tmp_fd)

        html_content = render_template(
            'pdf_report_template.html',
            report_data=serialized_data,
            metadata=metadata,
            ai_insights=ai_insights
        )

        pdf_css = CSS(string='''
            @page { size: letter; margin: 0.5in 0.6in 0.75in 0.6in; }
            body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; }
            table { width: 100%; border-collapse: collapse; font-size: 9pt; }
            th, td { border: 1px solid #ddd; padding: 6px 8px; }
            th { background-color: #f5f5f5 !important; }
        ''')

        html_doc = HTML(string=html_content, base_url=request.url_root)
        html_doc.write_pdf(tmp_path, stylesheets=[pdf_css])

        filename = generate_filename(metadata, '.pdf')

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


def report_data():
    """Return the analysis report data for web display"""
    try:
        job_id = request.args.get('job_id') or session.get('job_id')
        if not job_id:
            return jsonify({'error': 'No analysis session found'}), 404

        from justdata.shared.utils.progress_tracker import get_analysis_result
        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found'}), 404

        from justdata.shared.utils.json_utils import ensure_json_serializable, serialize_dataframes

        report_data_raw = analysis_result.get('report_data', {})

        # Debug: Log what we're serializing
        print(f"[DEBUG] report_data_raw keys: {list(report_data_raw.keys())}")
        for key in report_data_raw.keys():
            val = report_data_raw[key]
            if hasattr(val, 'to_dict'):
                print(f"[DEBUG] report_data_raw['{key}'] is DataFrame with {len(val)} rows")
            elif isinstance(val, list):
                print(f"[DEBUG] report_data_raw['{key}'] is list with {len(val)} items")
            elif isinstance(val, dict):
                print(f"[DEBUG] report_data_raw['{key}'] is dict")
            else:
                print(f"[DEBUG] report_data_raw['{key}'] is {type(val)}")

        serialized_data = serialize_dataframes(report_data_raw)

        # Debug: Log serialized data
        print(f"[DEBUG] serialized_data keys: {list(serialized_data.keys())}")
        for key in serialized_data.keys():
            val = serialized_data[key]
            if isinstance(val, list):
                print(f"[DEBUG] serialized_data['{key}'] is list with {len(val)} items")
            else:
                print(f"[DEBUG] serialized_data['{key}'] is {type(val)}")

        metadata = analysis_result.get('metadata', {})
        ai_insights = analysis_result.get('ai_insights', {})

        return jsonify({
            'success': True,
            'data': ensure_json_serializable(serialized_data),
            'metadata': {
                **ensure_json_serializable(metadata),
                'ai_insights': ensure_json_serializable(ai_insights)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve report data: {str(e)}'
        }), 500


def data():
    """Return data for the application"""
    return jsonify([])


@app.route('/states')
def states():
    """Return a list of all available states"""
    try:
        from justdata.apps.lendsight.data_utils import get_available_states
        states_list = get_available_states()
        return jsonify(states_list)
    except Exception as e:
        print(f"Error in states endpoint: {e}")
        return jsonify([])


@app.route('/counties')
def counties():
    """Return a list of all available counties"""
    try:
        from justdata.apps.lendsight.data_utils import get_available_counties
        counties_list = get_available_counties()
        return jsonify(counties_list)
    except Exception as e:
        print(f"Error in counties endpoint: {e}")
        return jsonify([])


@app.route('/counties-by-state/<state_identifier>')
def counties_by_state(state_identifier):
    """Get list of counties for a specific state"""
    try:
        from urllib.parse import unquote
        from justdata.shared.utils.bigquery_client import get_bigquery_client, escape_sql_string
        from justdata.apps.lendsight.config import PROJECT_ID

        state_identifier = unquote(state_identifier)
        client = get_bigquery_client(PROJECT_ID)

        is_numeric_code = state_identifier.isdigit() and len(state_identifier) <= 2

        if is_numeric_code:
            state_code_padded = state_identifier.zfill(2)
            query = f"""
            SELECT DISTINCT
                county_state,
                geoid5,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as county_fips
            FROM geo.cbsa_to_county
            WHERE geoid5 IS NOT NULL
                AND SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) = '{state_code_padded}'
            ORDER BY county_state
            """
        else:
            query = f"""
            SELECT DISTINCT county_state, geoid5
            FROM geo.cbsa_to_county
            WHERE LOWER(TRIM(SPLIT(county_state, ',')[SAFE_OFFSET(1)])) = LOWER('{escape_sql_string(state_identifier)}')
            ORDER BY county_state
            """

        query_job = client.query(query)
        results = list(query_job.result())

        counties = []
        seen_geoids = set()

        for row in results:
            geoid5 = str(row.geoid5).zfill(5) if row.geoid5 else None
            if geoid5 and geoid5 in seen_geoids:
                continue
            if geoid5:
                seen_geoids.add(geoid5)

            state_fips = geoid5[:2] if geoid5 and len(geoid5) >= 2 else None
            county_fips = geoid5[2:] if geoid5 and len(geoid5) >= 5 else None

            counties.append({
                'name': row.county_state,
                'geoid5': geoid5,
                'state_fips': state_fips,
                'county_fips': county_fips
            })

        return jsonify(counties)
    except Exception as e:
        print(f"Error in counties_by_state: {e}")
        return jsonify([])


# Register standard routes
register_standard_routes(
    app,
    index_handler=index,
    analyze_handler=analyze,
    progress_handler=progress_handler,
    download_handler=download,
    data_handler=data
)

# Add report routes
@app.route('/report')
def report_route():
    """Display the analysis report"""
    return report()

@app.route('/report-data')
def report_data_route():
    """Return the analysis report data for web display"""
    return report_data()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    app.run(debug=True, host='0.0.0.0', port=port)
