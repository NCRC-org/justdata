#!/usr/bin/env python3
"""
LoanTrends Flask web application.
Uses the same routing patterns as LendSight and BizSight.
"""

from flask import render_template, request, jsonify, session, Response, make_response, send_from_directory
import os
import tempfile
import uuid
import threading
import time
import json
from werkzeug.middleware.proxy_fix import ProxyFix

from justdata.shared.web.app_factory import create_app, register_standard_routes
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker
from justdata.shared.utils.env_utils import is_local_development
from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from pathlib import Path
from justdata.apps.loantrends.config import TEMPLATES_DIR, STATIC_DIR
from justdata.apps.loantrends.core import run_analysis
from justdata.apps.loantrends.version import __version__

# Get repo root for shared static files
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()

# Load unified environment configuration (works for both local and Render)
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)

# Print environment summary
print(f"[ENV] Environment: {'LOCAL' if config['IS_LOCAL'] else 'PRODUCTION (Render)'}")
print(f"[ENV] Shared config loaded from: {config.get('SHARED_ENV_FILE', 'Environment variables')}")

# Create the Flask app
app = create_app(
    'loantrends',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

# Add ProxyFix for proper request handling behind Render's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Configure cache-busting
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['EXPLAIN_TEMPLATE_LOADING'] = True

# DISABLE Jinja2 bytecode cache completely
app.jinja_env.bytecode_cache = None

# Force reload templates on every request
@app.before_request
def clear_template_cache():
    """Clear Jinja2 template cache before each request."""
    if hasattr(app, 'jinja_env'):
        app.jinja_env.bytecode_cache = None
        app.jinja_env.cache = {}
        app.jinja_env.auto_reload = True
        try:
            if hasattr(app.jinja_env.cache, 'clear'):
                app.jinja_env.cache.clear()
        except:
            pass


@app.route('/static/img/ncrc-logo.png')
def serve_shared_logo():
    """Serve the shared NCRC logo from shared/web/static/img/"""
    shared_logo_path = REPO_ROOT / 'shared' / 'web' / 'static' / 'img' / 'ncrc-logo.png'
    if shared_logo_path.exists():
        return send_from_directory(str(shared_logo_path.parent), shared_logo_path.name)
    else:
        return send_from_directory(app.static_folder, 'img/ncrc-logo.png'), 404


@app.route('/')
def index():
    """Main dashboard page - loads all metrics automatically"""
    import time
    cache_buster = int(time.time())
    response = make_response(render_template('dashboard.html', version=__version__, cache_buster=cache_buster))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/dashboard-data', methods=['GET'])
def get_dashboard_data():
    """Get dashboard data for all endpoints"""
    try:
        from justdata.apps.loantrends.config import GRAPH_ENDPOINTS
        from justdata.apps.loantrends.data_utils import fetch_multiple_graphs
        from justdata.apps.loantrends.chart_builder import build_chart_data
        
        # Get all endpoints from config
        all_endpoints = []
        for category_endpoints in GRAPH_ENDPOINTS.values():
            all_endpoints.extend(category_endpoints)
        
        print(f"[DEBUG] Loading dashboard data for {len(all_endpoints)} endpoints")
        
        # Fetch all graph data
        graph_data = fetch_multiple_graphs(all_endpoints)
        
        # Build chart data (year-based)
        chart_data = build_chart_data(graph_data, time_period="all")
        
        # Get time period info
        from justdata.apps.loantrends.data_utils import get_recent_12_quarters
        start_quarter, end_quarter = get_recent_12_quarters()
        
        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'time_period': f"{start_quarter} to {end_quarter} (last 12 quarters)",
            'endpoints': all_endpoints,
            'categories': GRAPH_ENDPOINTS
        })
    except Exception as e:
        print(f"[ERROR] Error loading dashboard data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/progress/<job_id>')
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
                    print(f"Client disconnected from progress stream for {job_id}")
                    break
                except Exception as e:
                    print(f"Error in progress stream for {job_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    try:
                        yield f"data: {{\"percent\": {last_percent}, \"step\": \"Error reading progress...\", \"done\": false, \"error\": null}}\n\n"
                    except:
                        break
                    time.sleep(1)
        except GeneratorExit:
            print(f"Progress stream closed for {job_id}")
        except Exception as e:
            print(f"Fatal error in progress stream for {job_id}: {e}")
            import traceback
            traceback.print_exc()
            try:
                yield f"data: {{\"percent\": 0, \"step\": \"Connection error\", \"done\": true, \"error\": \"Progress tracking error: {str(e)}\"}}\n\n"
            except:
                pass
    
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
                'step': 'Job not found - may have completed',
                'done': False,
                'error': None
            })
        return jsonify(progress)
    except Exception as e:
        print(f"Error in progress_status endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'percent': 0,
            'step': 'Error checking progress',
            'done': False,
            'error': str(e)
        }), 500


@app.route('/analyze', methods=['POST'])
def analyze():
    """Handle analysis request"""
    try:
        data = request.get_json()
        print(f"[DEBUG] analyze endpoint - received data: {data}")
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        selected_endpoints = data.get('selected_endpoints', [])
        time_period = data.get('time_period', 'all')
        start_quarter = data.get('start_quarter', None)
        end_quarter = data.get('end_quarter', None)
        
        print(f"[DEBUG] analyze endpoint - selected_endpoints: {selected_endpoints}")
        print(f"[DEBUG] analyze endpoint - time_period: {time_period}")
        
        if not selected_endpoints:
            return jsonify({'success': False, 'error': 'Please select at least one metric to analyze'}), 400
        
        if time_period == 'custom' and (not start_quarter or not end_quarter):
            return jsonify({'success': False, 'error': 'Please specify start and end quarters for custom time period'}), 400
        
        job_id = str(uuid.uuid4())
        print(f"[DEBUG] analyze endpoint - created job_id: {job_id}")
        
        # Create progress tracker for this job
        progress_tracker = create_progress_tracker(job_id)
        print(f"[DEBUG] analyze endpoint - created progress tracker")
        
        # Store in session
        session['selected_endpoints'] = selected_endpoints
        session['time_period'] = time_period
        session['job_id'] = job_id
        
        def run_job():
            try:
                # Run the analysis pipeline with progress tracking
                result = run_analysis(
                    selected_endpoints,
                    time_period,
                    start_quarter,
                    end_quarter,
                    job_id,
                    progress_tracker
                )
                
                if not result.get('success'):
                    error_msg = result.get('error', 'Unknown error')
                    progress_tracker.update_progress('error', error_msg)
                    return
                
                # Store the analysis results
                from justdata.shared.utils.progress_tracker import store_analysis_result
                store_analysis_result(job_id, result)
                
                # Mark analysis as completed
                progress_tracker.complete(success=True)
                
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Error in analysis job: {error_msg}")
                import traceback
                traceback.print_exc()
                progress_tracker.complete(success=False, error=error_msg)
        
        print(f"[DEBUG] Starting background thread for job {job_id}")
        threading.Thread(target=run_job, daemon=True).start()
        
        print(f"[DEBUG] Returning success response with job_id: {job_id}")
        response = jsonify({'success': True, 'job_id': job_id})
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
        
    except Exception as e:
        print(f"[ERROR] Error in analyze endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """Get analysis results"""
    try:
        from justdata.shared.utils.progress_tracker import get_analysis_result
        result = get_analysis_result(job_id)
        
        if not result:
            return jsonify({'success': False, 'error': 'Results not found. The analysis may still be running or may have expired.'}), 404
        
        return jsonify(result)
    except Exception as e:
        print(f"[ERROR] Error getting results: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/report/<job_id>', methods=['GET'])
def show_report(job_id):
    """Display the full report"""
    try:
        print(f"[DEBUG show_report] Loading report for job_id: {job_id}")
        from justdata.shared.utils.progress_tracker import get_analysis_result
        result = get_analysis_result(job_id)
        
        print(f"[DEBUG show_report] Result retrieved: {result is not None}")
        if result:
            print(f"[DEBUG show_report] Result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            print(f"[DEBUG show_report] Result success: {result.get('success')}")
            print(f"[DEBUG show_report] Result metadata: {result.get('metadata')}")
            print(f"[DEBUG show_report] Result tables keys: {list(result.get('tables', {}).keys())}")
            print(f"[DEBUG show_report] Result ai_insights keys: {list(result.get('ai_insights', {}).keys())}")
        
        if not result:
            print(f"[DEBUG show_report] ERROR: Result is None")
            return f"""
            <html><body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2>Report Not Found</h2>
                <p>Report not found. The analysis may still be running or may have expired.</p>
                <p>Job ID: {job_id}</p>
                <a href="/">Return to Home</a>
            </body></html>
            """, 404
        
        if not result.get('success'):
            print(f"[DEBUG show_report] ERROR: Result success is False")
            print(f"[DEBUG show_report] Error message: {result.get('error')}")
            return render_template('error_template.html',
                                 error=result.get('error', 'Unknown error'),
                                 job_id=job_id), 500
        
        print(f"[DEBUG show_report] Rendering template with result data")
        print(f"[DEBUG show_report]   - result['tables'] count: {len(result.get('tables', {}))}")
        print(f"[DEBUG show_report]   - result['ai_insights'] count: {len(result.get('ai_insights', {}))}")
        
        import time
        cache_buster = int(time.time())
        response = make_response(render_template('report_template.html',
                                                result=result,
                                                version=__version__,
                                                cache_buster=cache_buster))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        print(f"[DEBUG show_report] Template rendered successfully")
        return response
        
    except Exception as e:
        print(f"[ERROR] Error showing report: {e}")
        import traceback
        traceback.print_exc()
        return f"""
        <html><body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2>Error</h2>
            <p>{str(e)}</p>
            <p>Job ID: {job_id}</p>
            <a href="/">Return to Home</a>
        </body></html>
        """, 500


@app.route('/api/available-graphs', methods=['GET'])
def get_available_graphs():
    """Get list of available graphs from Quarterly API"""
    try:
        from justdata.apps.loantrends.data_utils import fetch_available_graphs
        graphs_data = fetch_available_graphs()
        return jsonify(graphs_data)
    except Exception as e:
        print(f"[ERROR] Error fetching available graphs: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def download():
    """Download handler (placeholder - not currently used for LoanTrends)"""
    return jsonify({'error': 'Download functionality not yet implemented'}), 501


# Register standard routes
register_standard_routes(
    app,
    index_handler=index,
    analyze_handler=analyze,
    progress_handler=progress_handler,
    download_handler=download,
    data_handler=None
)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8083))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting LoanTrends on {host}:{port}")
    app.run(host=host, port=port, debug=debug)




