#!/usr/bin/env python3
"""
BranchSight Flask web application.
"""

from flask import render_template, request, jsonify, send_file, session, Response, send_from_directory
import os
import sys
import tempfile
import zipfile
from datetime import datetime
import uuid
import threading
import time
import json
from pathlib import Path
from werkzeug.middleware.proxy_fix import ProxyFix

# Add repo root to path for shared modules
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from justdata.shared.web.app_factory import create_app, register_standard_routes
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker

# Use absolute imports from repo root (like bizsight)
from justdata.apps.branchsight.config import TEMPLATES_DIR, STATIC_DIR, OUTPUT_DIR
from justdata.apps.branchsight.data_utils import get_available_counties
from justdata.apps.branchsight.core import run_analysis
from justdata.apps.branchsight.version import __version__


# Create the Flask app
app = create_app(
    'branchsight',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

# Add ProxyFix for proper request handling behind Render's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Note: /health endpoint is already added by create_app() in shared/web/app_factory.py


@app.route('/static/img/ncrc-logo.png')
def serve_shared_logo():
    """Serve the shared NCRC logo from shared/web/static/img/"""
    shared_logo_path = REPO_ROOT / 'shared' / 'web' / 'static' / 'img' / 'ncrc-logo.png'
    if shared_logo_path.exists():
        return send_from_directory(str(shared_logo_path.parent), shared_logo_path.name)
    else:
        # Fallback to local static if shared logo doesn't exist
        local_logo_path = STATIC_DIR / 'img' / 'ncrc-logo.png'
        if local_logo_path.exists():
            return send_from_directory(str(local_logo_path.parent), local_logo_path.name)
        return '', 404

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


def index():
    """Main page with the analysis form"""
    return render_template('analysis_template.html', version=__version__)


def report():
    """Report display page"""
    return render_template('report_template.html', version=__version__)


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


def analyze():
    """Handle analysis request"""
    try:
        data = request.get_json()
        selection_type = data.get('selection_type', 'county')  # 'county', 'state', or 'metro'
        counties_str = data.get('counties', '').strip()
        years = data.get('years', '').strip()
        state_code = data.get('state_code', None)
        metro_code = data.get('metro_code', None)
        job_id = str(uuid.uuid4())
        
        # Create progress tracker for this job
        progress_tracker = create_progress_tracker(job_id)
        
        # Validate inputs based on selection type
        # For BranchSight: state is required and only one county allowed
        if selection_type == 'county':
            if not state_code:
                return jsonify({'error': 'Please select a state'}), 400
            if not counties_str:
                return jsonify({'error': 'Please select a county'}), 400
            # Check if multiple counties were selected (split by semicolon)
            counties_list_check = [c.strip() for c in counties_str.split(';') if c.strip()]
            if len(counties_list_check) > 1:
                return jsonify({'error': 'Please select only one county at a time'}), 400
        elif selection_type == 'state' and not state_code:
            return jsonify({'error': 'Please select a state'}), 400
        elif selection_type == 'metro' and not metro_code:
            return jsonify({'error': 'Please select a metro area'}), 400
        
        if not years:
            return jsonify({'error': 'Please provide years'}), 400
        
        # Parse parameters (this will expand state/metro to counties if needed)
        from justdata.apps.branchsight.core import parse_web_parameters
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
                # Run the analysis pipeline with progress tracking
                # Pass selection context to run_analysis
                result = run_analysis(';'.join(counties_list), ','.join(map(str, years_list)), job_id, progress_tracker,
                                       selection_type, state_code, metro_code)
                
                if not result.get('success'):
                    error_msg = result.get('error', 'Unknown error')
                    progress_tracker.update_progress('error', error_msg)
                    return
                
                # Store the analysis results in a global store instead of session
                # (session can't be accessed from background thread)
                from justdata.shared.utils.progress_tracker import store_analysis_result
                store_analysis_result(job_id, result)
                
                # Mark analysis as completed
                progress_tracker.complete(success=True)
                
            except Exception as e:
                error_msg = str(e)
                progress_tracker.complete(success=False, error=error_msg)
        
        threading.Thread(target=run_job).start()
        
        return jsonify({'success': True, 'job_id': job_id})
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500


def download():
    """Download the generated reports in various formats"""
    try:
        format_type = request.args.get('format', 'excel').lower()
        job_id = session.get('job_id')
        
        if not job_id:
            return jsonify({'error': 'No analysis session found. Please run an analysis first.'}), 400
        
        from justdata.shared.utils.progress_tracker import get_analysis_result
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
        import tempfile
        import os
        
        # Create a temporary file that won't be deleted immediately
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(tmp_fd)  # Close the file descriptor, we'll use the path
        
        from justdata.shared.reporting.report_builder import save_excel_report
        save_excel_report(report_data, tmp_path, metadata=metadata)
        
        # Send the file and schedule cleanup
        response = send_file(
            tmp_path,
            as_attachment=True,
            download_name=f'branchsight_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Schedule file deletion after response is sent
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
        
        # Write summary data
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
        import json
        
        # Convert DataFrames to JSON-serializable format
        serialized_data = {}
        for key, df in report_data.items():
            if hasattr(df, 'to_dict'):
                # Replace NaN values with None to make it JSON serializable
                import numpy as np
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
        import tempfile
        import os
        
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
                        # Replace NaN values with None to make it JSON serializable
                        import numpy as np
                        df_clean = df.replace({np.nan: None})
                        json_data[key] = df_clean.to_dict('records')
                    else:
                        json_data[key] = df
                
                json_content = json.dumps({
                    'metadata': metadata,
                    'data': json_data
                }, indent=2)
                zipf.writestr('analysis_data.json', json_content)
            
            # Read the zip file into memory before temp directory is deleted
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


def report_data():
    """Return the analysis report data for web display"""
    try:
        job_id = session.get('job_id')
        if not job_id:
            return jsonify({'error': 'No analysis session found'}), 404
        
        from justdata.shared.utils.progress_tracker import get_analysis_result
        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found'}), 404
        
        # Convert pandas DataFrames to JSON-serializable format
        report_data = analysis_result.get('report_data', {})
        serialized_data = {}

        # Debug: Log what we're serializing
        print(f"[DEBUG] report_data keys: {list(report_data.keys())}")
        for key in report_data.keys():
            val = report_data[key]
            if hasattr(val, 'to_dict'):
                print(f"[DEBUG] report_data['{key}'] is DataFrame with {len(val)} rows")
            elif isinstance(val, list):
                print(f"[DEBUG] report_data['{key}'] is list with {len(val)} items")
            elif isinstance(val, dict):
                print(f"[DEBUG] report_data['{key}'] is dict with keys: {list(val.keys())}")
            else:
                print(f"[DEBUG] report_data['{key}'] is {type(val)}")

        for key, df in report_data.items():
            if key == 'hhi_by_year':
                # hhi_by_year is already a list, just include it directly
                serialized_data[key] = df if isinstance(df, list) else []
            elif hasattr(df, 'to_dict'):
                # Convert DataFrame to records format for easier frontend consumption
                # Replace NaN values with None to make it JSON serializable
                import numpy as np
                df_clean = df.replace({np.nan: None})
                serialized_data[key] = df_clean.to_dict('records')
            else:
                serialized_data[key] = df

        # Debug: Log serialized data
        print(f"[DEBUG] serialized_data keys: {list(serialized_data.keys())}")
        for key in serialized_data.keys():
            val = serialized_data[key]
            if isinstance(val, list):
                print(f"[DEBUG] serialized_data['{key}'] is list with {len(val)} items")
                if len(val) > 0:
                    print(f"[DEBUG]   First item keys: {list(val[0].keys()) if isinstance(val[0], dict) else 'not a dict'}")
            elif isinstance(val, dict):
                print(f"[DEBUG] serialized_data['{key}'] is dict with keys: {list(val.keys())}")
            else:
                print(f"[DEBUG] serialized_data['{key}'] is {type(val)}")

        # Debug: Check what we're returning
        ai_insights = analysis_result.get('ai_insights', {})
        print(f"[DEBUG] report_data endpoint - ai_insights keys: {list(ai_insights.keys())}")
        if 'table_narratives' in ai_insights:
            print(f"[DEBUG] table_narratives keys: {list(ai_insights.get('table_narratives', {}).keys())}")
            for key, value in ai_insights.get('table_narratives', {}).items():
                if value:
                    print(f"[DEBUG]   {key}: {len(str(value))} characters")
                else:
                    print(f"[DEBUG]   {key}: EMPTY or None")
        
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
        # Return fallback list on error
        from data_utils import get_fallback_counties
        return jsonify(get_fallback_counties())


def states():
    """Return a list of all available states"""
    try:
        from data_utils import get_available_states
        states_list = get_available_states()
        print(f"States endpoint: Returning {len(states_list)} states")
        return jsonify(states_list)
    except Exception as e:
        print(f"Error in states endpoint: {e}")
        import traceback
        traceback.print_exc()
        # Use fallback on error
        try:
            from data_utils import get_fallback_states
            states_list = get_fallback_states()
            print(f"Using fallback: Returning {len(states_list)} states")
            return jsonify(states_list)
        except:
            return jsonify([])


def metro_areas():
    """Return a list of all available metro areas (CBSAs)"""
    try:
        from data_utils import get_available_metro_areas
        metros_list = get_available_metro_areas()
        print(f"metro_areas endpoint returning {len(metros_list)} metro areas")
        if len(metros_list) == 0:
            print("WARNING: No metro areas returned. Check BigQuery table and query.")
        return jsonify(metros_list)
    except Exception as e:
        print(f"Error in metro_areas endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Register standard routes
register_standard_routes(
    app,
    index_handler=index,
    analyze_handler=analyze,
    progress_handler=progress_handler,
    download_handler=download,
    data_handler=None  # We'll add counties route manually below
)

# Add the /counties route manually to match branch_ai routing
@app.route('/counties')
def counties_route():
    """Return a list of all available counties"""
    return counties()

# Add routes for states and metro areas
@app.route('/states')
def states_route():
    """Return a list of all available states"""
    return states()

@app.route('/metro-areas')
def metro_areas_route():
    """Return a list of all available metro areas (CBSAs)"""
    return metro_areas()


# Add the /report-data route for web report display
@app.route('/report-data')
def report_data_route():
    """Return the analysis report data for web display"""
    return report_data()

# Add the /report route for displaying the report
@app.route('/report')
def report_route():
    """Display the analysis report"""
    return report()


# Add data endpoints for frontend
@app.route('/counties')
def counties_endpoint():
    """Get list of available counties"""
    try:
        counties = get_available_counties()
        return jsonify(counties)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/counties-by-state/<state_code>')
def counties_by_state_endpoint(state_code):
    """Get list of counties for a specific state"""
    try:
        # URL decode the state code
        from urllib.parse import unquote
        state_code = unquote(state_code)
        
        # Try to query BigQuery directly for counties in this state
        try:
            from justdata.shared.utils.bigquery_client import get_bigquery_client
            from justdata.apps.branchsight.config import PROJECT_ID
            client = get_bigquery_client(PROJECT_ID)
            query = f"""
            SELECT DISTINCT county_state 
            FROM geo.cbsa_to_county 
            WHERE LOWER(SPLIT(county_state, ',')[SAFE_OFFSET(1)]) = LOWER('{state_code}')
            ORDER BY county_state
            """
            query_job = client.query(query)
            results = query_job.result()
            counties = [row.county_state for row in results]
            if counties:
                return jsonify(counties)
        except Exception as bq_error:
            # If BigQuery fails, fall back to filtering available counties
            pass
        
        # Fallback: filter from available counties
        all_counties = get_available_counties()
        filtered = []
        for county in all_counties:
            # Handle both dict format (new) and string format (old/fallback)
            if isinstance(county, dict):
                county_name = county.get('name', '')
                state_fips = county.get('state_fips', '')
                # Check if state_code is a FIPS code (2 digits) or state name
                if state_code.isdigit() and len(state_code) <= 2:
                    # Match by state FIPS code
                    state_code_padded = state_code.zfill(2)
                    if state_fips and state_fips == state_code_padded:
                        filtered.append(county)
                else:
                    # Match by state name
                    if ',' in county_name:
                        _, state_name = county_name.split(',', 1)
                        state_name = state_name.strip()
                        if state_name.lower() == state_code.lower():
                            filtered.append(county)
            else:
                # Old format: string
                if ',' in county:
                    county_name, state_name = county.split(',', 1)
                    state_name = state_name.strip()
                    if state_name.lower() == state_code.lower():
                        filtered.append(county)
        return jsonify(filtered)
    except Exception as e:
        import traceback
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')  # Avoid encoding issues
        try:
            traceback.print_exc()
        except:
            pass
        return jsonify({'error': error_msg}), 500


# Note: Favicon routes are already added by create_app() in shared/web/app_factory.py
# No need to add them here to avoid duplicate endpoint errors


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)

