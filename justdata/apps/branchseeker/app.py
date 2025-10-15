#!/usr/bin/env python3
"""
BranchSeeker Flask web application.
"""

from flask import render_template, request, jsonify, send_file, session, Response
import os
import tempfile
import zipfile
from datetime import datetime
import uuid
import threading
import time
import json

from justdata.shared.web.app_factory import create_app, register_standard_routes
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker
from .config import TEMPLATES_DIR, STATIC_DIR, OUTPUT_DIR
from .data_utils import get_available_counties
from .core import run_analysis


# Create the Flask app
app = create_app(
    'branchseeker',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)


def index():
    """Main page with the analysis form"""
    return render_template('analysis_template.html')


def report():
    """Report display page"""
    return render_template('report_template.html')


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
        counties = data.get('counties', '').strip()
        years = data.get('years', '').strip()
        job_id = str(uuid.uuid4())
        
        # Create progress tracker for this job
        progress_tracker = create_progress_tracker(job_id)
        
        if not counties or not years:
            return jsonify({'error': 'Please provide both counties and years'}), 400
        
        # Store in session for download
        session['counties'] = counties
        session['years'] = years
        session['job_id'] = job_id
        
        def run_job():
            try:
                # Run the analysis pipeline with progress tracking
                result = run_analysis(counties, years, job_id, progress_tracker)
                
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
            return jsonify({'error': 'No analysis session found'}), 400
        
        from justdata.shared.utils.progress_tracker import get_analysis_result
        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found'}), 400
        
        report_data = analysis_result.get('report_data', {})
        metadata = analysis_result.get('metadata', {})
        
        if format_type == 'excel':
            return download_excel(report_data, metadata)
        elif format_type == 'csv':
            return download_csv(report_data, metadata)
        elif format_type == 'json':
            return download_json(report_data, metadata)
        elif format_type == 'zip':
            return download_zip(report_data, metadata)
        else:
            return jsonify({'error': 'Invalid format specified'}), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }), 500


def download_excel(report_data, metadata):
    """Download Excel file"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            from justdata.shared.reporting.excel_builder import save_excel_report
            save_excel_report(report_data, tmp_file.name)
            
            return send_file(
                tmp_file.name,
                as_attachment=True,
                download_name=f'branchseeker_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
    except Exception as e:
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
                'Content-Disposition': f'attachment; filename=branchseeker_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
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
                'Content-Disposition': f'attachment; filename=branchseeker_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            }
        )
    except Exception as e:
        return jsonify({'error': f'JSON export failed: {str(e)}'}), 500


def download_zip(report_data, metadata):
    """Download ZIP file with multiple formats"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'branchseeker_reports.zip')
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Add Excel file
                excel_path = os.path.join(OUTPUT_DIR, 'fdic_branch_analysis.xlsx')
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
            
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=f'branchseeker_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
                mimetype='application/zip'
            )
    except Exception as e:
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
        
        for key, df in report_data.items():
            if hasattr(df, 'to_dict'):
                # Convert DataFrame to records format for easier frontend consumption
                # Replace NaN values with None to make it JSON serializable
                import numpy as np
                df_clean = df.replace({np.nan: None})
                serialized_data[key] = df_clean.to_dict('records')
            else:
                serialized_data[key] = df
        
        return jsonify({
            'success': True,
            'data': serialized_data,
            'metadata': {
                **analysis_result.get('metadata', {}),
                'ai_insights': analysis_result.get('ai_insights', {})
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
        print(f"✅ Successfully fetched {len(counties_list)} counties")
        return jsonify(counties_list)
    except Exception as e:
        print(f"❌ Error in counties endpoint: {e}")
        import traceback
        traceback.print_exc()
        # Return fallback list on error
        from .data_utils import get_fallback_counties
        return jsonify(get_fallback_counties())


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


# Add favicon routes to prevent 404 errors
@app.route('/favicon.ico')
@app.route('/assets/favicon.ico')
def favicon():
    """Serve favicon or return 204 No Content"""
    return '', 204


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)

