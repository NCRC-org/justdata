#!/usr/bin/env python3
"""
LendSight Flask web application.
Uses the same routing patterns as BranchSeeker and BizSight.
"""

from flask import render_template, request, jsonify, session, Response, make_response
import os
import tempfile
import uuid
import threading
import time
import json
from werkzeug.middleware.proxy_fix import ProxyFix

from shared.web.app_factory import create_app, register_standard_routes
from shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker
from .config import TEMPLATES_DIR, STATIC_DIR
from .core import run_analysis

# Create the Flask app
app = create_app(
    'lendsight',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

# Add ProxyFix for proper request handling behind Render's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Configure cache-busting (same as BizSight)
app.config['DEBUG'] = True  # Always True for development
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Force template reload on every request
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable static file caching
app.config['EXPLAIN_TEMPLATE_LOADING'] = True  # Debug template loading

# DISABLE Jinja2 bytecode cache completely - prevents cached templates
app.jinja_env.bytecode_cache = None

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


@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return {'status': 'ok', 'app': 'lendsight'}, 200


def index():
    """Main page with the analysis form"""
    from . import __version__
    import time
    cache_buster = int(time.time())  # Timestamp for cache-busting
    response = make_response(render_template('analysis_template.html', version=__version__, cache_buster=cache_buster))
    # Add cache-busting headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


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
            print(f"[DEBUG] analyze endpoint - state_code: {state_code}, type: {type(state_code)}")
            print(f"[DEBUG] analyze endpoint - counties_data type: {type(counties_data)}, sample: {counties_data[:1] if isinstance(counties_data, list) and len(counties_data) > 0 else counties_data}")
            
            # Validate inputs - state is optional, then up to 3 counties
            # State code can be None or empty string - it's optional
            
            job_id = str(uuid.uuid4())
            print(f"[DEBUG] analyze endpoint - created job_id: {job_id}")
            
            # Create progress tracker for this job
            progress_tracker = create_progress_tracker(job_id)
            print(f"[DEBUG] analyze endpoint - created progress tracker")
            
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
            
            print(f"[DEBUG] Parsed counties: {counties_list}, count: {len(counties_list)}")
            print(f"[DEBUG] Counties with FIPS: {len(counties_with_fips)} out of {len(counties_list)}")
            
            if len(counties_list) > 3:
                return jsonify({'success': False, 'error': f'Please select a maximum of 3 counties. You selected {len(counties_list)} counties: {", ".join(counties_list)}'}), 400
            if len(counties_list) == 0:
                return jsonify({'success': False, 'error': 'Please select at least one county'}), 400
            
            if not years:
                return jsonify({'success': False, 'error': 'Please provide years'}), 400
            
            # Convert counties list back to string format for parse_web_parameters
            counties_str = ';'.join(counties_list)
            
            # Parse parameters (this will expand state to counties if needed, but we already have counties)
            from .core import parse_web_parameters
            try:
                print(f"[DEBUG] Calling parse_web_parameters with counties_str={counties_str}, years={years}, selection_type={selection_type}, state_code={state_code}")
                counties_list, years_list = parse_web_parameters(
                    counties_str, years, selection_type, state_code, None
                )
                print(f"[DEBUG] parse_web_parameters returned {len(counties_list)} counties and {len(years_list)} years")
            except Exception as e:
                print(f"[ERROR] Error parsing parameters: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'error': f'Error parsing parameters: {str(e)}'}), 400
            
            # Store in session for download
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
                        return
                    
                    # Store the analysis results in a global store instead of session
                    # (session can't be accessed from background thread)
                    from shared.utils.progress_tracker import store_analysis_result
                    store_analysis_result(job_id, result)
                    
                    # Mark analysis as completed
                    progress_tracker.complete(success=True)
                    
                except Exception as e:
                    error_msg = str(e)
                    progress_tracker.complete(success=False, error=error_msg)
            
            print(f"[DEBUG] Starting background thread for job {job_id}")
            threading.Thread(target=run_job, daemon=True).start()
            
            print(f"[DEBUG] Returning success response with job_id: {job_id}")
            response = jsonify({'success': True, 'job_id': job_id})
            print(f"[DEBUG] Response created, returning...")
            return response
                
        except Exception as e:
            print(f"[ERROR] Exception in analyze endpoint: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'An error occurred: {str(e)}'
            }), 500


def report():
    """Report display page"""
    from . import __version__
    return render_template('report_template.html', version=__version__)


def download():
    """Download the generated reports"""
    try:
        format_type = request.args.get('format', 'excel').lower()
        # Check for job_id in URL parameters first, then session
        job_id = request.args.get('job_id') or session.get('job_id')
        
        if not job_id:
            return jsonify({'error': 'No analysis session found. Please run an analysis first.'}), 400
        
        from shared.utils.progress_tracker import get_analysis_result
        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found. The analysis may have expired or failed.'}), 400
        
        report_data = analysis_result.get('report_data', {})
        metadata = analysis_result.get('metadata', {})
        
        if not report_data:
            return jsonify({'error': 'No report data available for export.'}), 400
        
        if format_type == 'excel':
            return download_excel(report_data, metadata)
        elif format_type == 'pdf':
            return download_pdf(report_data, metadata)
        else:
            return jsonify({'error': f'Invalid format specified: {format_type}. Valid formats are: excel (for data export), pdf (for report export)'}), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }), 500


def generate_filename(metadata, extension='.xlsx'):
    """Generate a filename for downloads with NCRC, LendSight, county, and state"""
    import re
    from datetime import datetime
    
    # Get first county from metadata
    counties = metadata.get('counties', [])
    if not counties or len(counties) == 0:
        # Fallback if no counties
        return f'NCRC_LendSight_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}{extension}'
    
    # Parse first county (format: "County Name, State")
    first_county = counties[0]
    if ',' in first_county:
        county_name, state_name = [part.strip() for part in first_county.rsplit(',', 1)]
    else:
        # Fallback if format is unexpected
        county_name = first_county
        state_name = ''
    
    # Clean up names for filename (remove special characters, spaces become underscores, remove commas)
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
    
    # Build filename: NCRC_LendSight_[County]_[State]_[timestamp]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if state_clean:
        filename = f'NCRC_LendSight_{county_clean}_{state_clean}_{timestamp}{extension}'
    else:
        filename = f'NCRC_LendSight_{county_clean}_{timestamp}{extension}'
    
    # Remove "hmda" if it appears (case-insensitive)
    filename = re.sub(r'hmda', '', filename, flags=re.IGNORECASE)
    filename = re.sub(r'__+', '_', filename)  # Clean up double underscores
    
    return filename


def download_excel(report_data, metadata):
    """Download Excel file"""
    try:
        import tempfile
        import os
        from datetime import datetime
        from flask import send_file
        
        # Create a temporary file that won't be deleted immediately
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(tmp_fd)  # Close the file descriptor, we'll use the path
        
        from apps.lendsight.mortgage_report_builder import save_mortgage_excel_report
        save_mortgage_excel_report(report_data, tmp_path, metadata=metadata)
        
        # Generate filename with NCRC, LendSight, county, and state
        filename = generate_filename(metadata, '.xlsx')
        
        # Send the file and schedule cleanup
        response = send_file(
            tmp_path,
            as_attachment=True,
            download_name=filename,
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


def download_pdf(report_data, metadata):
    """Download PDF file with proper formatting, page breaks, and page numbers"""
    try:
        import tempfile
        import os
        from flask import send_file, url_for
        from playwright.sync_api import sync_playwright
        import json
        
        # Get AI insights from the analysis result
        from shared.utils.progress_tracker import get_analysis_result
        job_id = request.args.get('job_id') or session.get('job_id')
        analysis_result = get_analysis_result(job_id) if job_id else {}
        ai_insights = analysis_result.get('ai_insights', {})
        
        # Serialize report data for template
        serialized_data = {}
        for key, df in report_data.items():
            if hasattr(df, 'to_dict'):
                import numpy as np
                df_clean = df.replace({np.nan: None})
                serialized_data[key] = df_clean.to_dict('records')
            else:
                serialized_data[key] = df
        
        # Create temporary file for PDF
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(tmp_fd)
        
        # Use Playwright to render the page with JavaScript executed
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Build the report URL with job_id
            base_url = request.url_root.rstrip('/')
            report_url = f"{base_url}/report"
            if job_id:
                report_url += f"?job_id={job_id}"
            
            # Navigate to the report page
            page.goto(report_url, wait_until='networkidle', timeout=60000)
            
            # Wait for the report to be fully loaded (check for report content visibility)
            page.wait_for_selector('#reportContent', state='visible', timeout=30000)
            # Additional wait for tables to populate
            page.wait_for_timeout(2000)
            
            # Generate PDF with optimized margins and formatting
            page.pdf(
                path=tmp_path,
                format='Letter',
                margin={
                    'top': '0.5in',      # Reduced from 0.75in for more content
                    'right': '0.6in',   # Reduced from 0.75in
                    'bottom': '0.75in', # Reduced from 1in (footer is smaller)
                    'left': '0.6in'     # Reduced from 0.75in
                },
                print_background=True,
                display_header_footer=True,
                header_template='<div></div>',
                footer_template='<div style="font-size: 9pt; color: #666; text-align: center; width: 100%; font-family: Inter, Arial, sans-serif; padding-top: 5px;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
                prefer_css_page_size=True,
                scale=0.95  # Slight scale to ensure content fits better
            )
            
            browser.close()
        
        # Generate filename with NCRC, LendSight, county, and state
        filename = generate_filename(metadata, '.pdf')
        
        # Send the file and schedule cleanup
        response = send_file(
            tmp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
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
        return jsonify({'error': f'PDF export failed: {str(e)}. Make sure Playwright browsers are installed: python -m playwright install chromium'}), 500


def report_data():
    """Return the analysis report data for web display"""
    try:
        # Check for job_id in URL parameters first, then session
        job_id = request.args.get('job_id') or session.get('job_id')
        if not job_id:
            return jsonify({'error': 'No analysis session found'}), 404
        
        from shared.utils.progress_tracker import get_analysis_result
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
        
        # Get metadata and ensure census_data is properly included
        metadata = analysis_result.get('metadata', {}).copy()
        ai_insights = analysis_result.get('ai_insights', {})
        
        # Debug: Check AI insights
        print(f"[DEBUG] AI insights keys: {list(ai_insights.keys()) if ai_insights else 'None'}")
        print(f"[DEBUG] Has demographic_overview_discussion: {'demographic_overview_discussion' in ai_insights if ai_insights else False}")
        print(f"[DEBUG] Has income_neighborhood_discussion: {'income_neighborhood_discussion' in ai_insights if ai_insights else False}")
        print(f"[DEBUG] Has top_lenders_detailed_discussion: {'top_lenders_detailed_discussion' in ai_insights if ai_insights else False}")
        if ai_insights and 'demographic_overview_discussion' in ai_insights:
            discussion = ai_insights['demographic_overview_discussion']
            print(f"[DEBUG] demographic_overview_discussion length: {len(discussion) if discussion else 0}")
            print(f"[DEBUG] demographic_overview_discussion preview: {discussion[:200] if discussion else 'None'}")
        
        # Debug: Check what's in metadata
        print(f"[DEBUG] Metadata keys: {list(metadata.keys())}")
        print(f"[DEBUG] Census data in metadata: {metadata.get('census_data') is not None}, type: {type(metadata.get('census_data'))}")
        if metadata.get('census_data'):
            print(f"[DEBUG] Census data keys: {list(metadata.get('census_data', {}).keys())}")
        
        # Ensure census_data is included and properly formatted
        census_data = metadata.get('census_data', {})
        print(f"[DEBUG] report_data: census_data from metadata: type={type(census_data)}, len={len(census_data) if census_data else 0}")
        if not census_data:
            print(f"[WARNING] No census_data in metadata, checking analysis_result directly")
            census_data = analysis_result.get('metadata', {}).get('census_data', {})
            print(f"[DEBUG] report_data: census_data from analysis_result: type={type(census_data)}, len={len(census_data) if census_data else 0}")
        
        # Convert census_data to ensure it's JSON serializable
        if census_data:
            from shared.analysis.ai_provider import convert_numpy_types
            print(f"[DEBUG] Before convert_numpy_types: {len(census_data)} counties, type={type(census_data)}")
            # Debug: print sample before conversion
            if len(census_data) > 0:
                sample_county = list(census_data.keys())[0]
                sample_data = census_data[sample_county]
                print(f"[DEBUG] Sample county '{sample_county}' before conversion: keys={list(sample_data.keys())}")
            
            census_data = convert_numpy_types(census_data)
            metadata['census_data'] = census_data
            print(f"[DEBUG] Census data after conversion: {len(census_data)} counties")
            
            # Debug: print sample after conversion
            if len(census_data) > 0:
                sample_county = list(census_data.keys())[0]
                sample_data = census_data[sample_county]
                print(f"[DEBUG] Sample county '{sample_county}' after conversion: keys={list(sample_data.keys())}")
        else:
            print(f"[WARNING] Still no census_data after conversion attempt")
            print(f"[DEBUG] metadata keys: {list(metadata.keys())}")
            print(f"[DEBUG] analysis_result keys: {list(analysis_result.keys())}")
            metadata['census_data'] = {}
        
        return jsonify({
            'success': True,
            'data': serialized_data,
            'metadata': {
                **metadata,
                'ai_insights': ai_insights
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve report data: {str(e)}'
        }), 500


def data():
    """Return data for the application"""
    # To be implemented
    return jsonify([])


@app.route('/states')
def states():
    """Return a list of all available states"""
    try:
        from .data_utils import get_available_states
        states_list = get_available_states()
        print(f"States endpoint: Returning {len(states_list)} states")
        return jsonify(states_list)
    except Exception as e:
        print(f"Error in states endpoint: {e}")
        import traceback
        traceback.print_exc()
        # Use fallback on error
        try:
            from .data_utils import get_available_states
            # The function already has fallback logic
            states_list = get_available_states()
            print(f"Using fallback: Returning {len(states_list)} states")
            return jsonify(states_list)
        except:
            return jsonify([])


@app.route('/counties')
def counties():
    """Return a list of all available counties"""
    try:
        from .data_utils import get_available_counties
        counties_list = get_available_counties()
        print(f"Counties endpoint: Returning {len(counties_list)} counties")
        return jsonify(counties_list)
    except Exception as e:
        print(f"Error in counties endpoint: {e}")
        import traceback
        traceback.print_exc()
        from .data_utils import get_fallback_counties
        return jsonify(get_fallback_counties())


# Track recent requests to block automatic polling
_county_request_tracker = {}
import time

@app.route('/counties-by-state/<state_identifier>')
def counties_by_state(state_identifier):
    """Get list of counties for a specific state using geoid5 for exact matching.
    
    Args:
        state_identifier: State name (e.g., "Delaware") or state FIPS code (e.g., "10")
    """
    try:
        from urllib.parse import unquote
        from shared.utils.bigquery_client import get_bigquery_client
        from .config import PROJECT_ID
        
        state_identifier = unquote(state_identifier)
        
        # BLOCK repeated automatic Arizona requests (likely from cached JavaScript)
        global _county_request_tracker
        client_ip = request.remote_addr
        request_key = f"{client_ip}:{state_identifier}"
        current_time = time.time()
        
        # Check if this is a repeated request within 5 seconds
        if request_key in _county_request_tracker:
            last_time, count = _county_request_tracker[request_key]
            if current_time - last_time < 5:  # Within 5 seconds
                count += 1
                if count > 2:  # More than 2 requests in 5 seconds = automatic polling
                    print(f"[DEBUG] BLOCKED automatic polling request for {state_identifier} from {client_ip} (count: {count})")
                    return jsonify({'error': 'Too many requests. Please select a state from the dropdown.'}), 429
                _county_request_tracker[request_key] = (current_time, count)
            else:
                # Reset if more than 5 seconds passed
                _county_request_tracker[request_key] = (current_time, 1)
        else:
            _county_request_tracker[request_key] = (current_time, 1)
        
        # Clean up old entries (older than 60 seconds)
        _county_request_tracker = {k: v for k, v in _county_request_tracker.items() if current_time - v[0] < 60}
        
        print(f"[DEBUG] counties_by_state called with: {state_identifier} from {client_ip}")
        
        client = get_bigquery_client(PROJECT_ID)
        
        # Check if state_identifier is a numeric state code (2 digits) or a state name
        is_numeric_code = state_identifier.isdigit() and len(state_identifier) <= 2
        
        if is_numeric_code:
            # Use geoid5 to match by state FIPS code (first 2 digits of geoid5)
            # GEOID5 format: SSCCC where SS = state FIPS (2 digits), CCC = county FIPS (3 digits)
            state_code_padded = state_identifier.zfill(2)
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
            print(f"[DEBUG] Using state name: {state_identifier}")
            query = f"""
            SELECT DISTINCT county_state, geoid5
            FROM geo.cbsa_to_county 
            WHERE LOWER(TRIM(SPLIT(county_state, ',')[SAFE_OFFSET(1)])) = LOWER('{state_identifier}')
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
                
                counties.append({
                    'name': row.county_state,
                    'geoid5': geoid5,
                    'state_fips': state_fips,
                    'county_fips': county_fips
                })
            
            if counties:
                print(f"[DEBUG] Found {len(counties)} counties for state identifier: {state_identifier}")
                # Debug: show first few counties
                if len(counties) > 0:
                    print(f"[DEBUG] Sample counties: {counties[:3]}")
                return jsonify(counties)
            else:
                print(f"[WARNING] No counties found for state identifier: {state_identifier}")
                return jsonify([])
        except Exception as bq_error:
            print(f"[ERROR] BigQuery query failed: {bq_error}")
            import traceback
            traceback.print_exc()
            # Fall back to filtering available counties
            pass
        
        # Fallback: filter from available counties
        from .data_utils import get_available_counties
        all_counties = get_available_counties()
        filtered = []
        for county in all_counties:
            if ',' in county:
                county_name, state_name = county.split(',', 1)
                state_name = state_name.strip()
                # Match by state name (case-insensitive) or check if it's a code match
                if is_numeric_code:
                    # For numeric codes, we'd need to look up the state name first
                    # This is a simplified fallback - just return empty for now
                    pass
                else:
                    if state_name.lower() == state_identifier.lower():
                        filtered.append(county)
        print(f"[DEBUG] Fallback: Found {len(filtered)} counties for state: {state_identifier}")
        return jsonify(filtered)
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"[ERROR] counties_by_state error: {error_msg}")
        return jsonify({'error': error_msg}), 500


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

@app.route('/debug-census-data')
def debug_census_data():
    """Debug endpoint to inspect stored Census data"""
    try:
        job_id = request.args.get('job_id') or session.get('job_id')
        if not job_id:
            return jsonify({'error': 'No job_id provided'}), 400
        
        from shared.utils.progress_tracker import get_analysis_result
        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis result found'}), 404
        
        metadata = analysis_result.get('metadata', {})
        census_data = metadata.get('census_data', {})
        
        debug_info = {
            'job_id': job_id,
            'has_analysis_result': analysis_result is not None,
            'metadata_keys': list(metadata.keys()) if metadata else [],
            'has_census_data_in_metadata': 'census_data' in metadata,
            'census_data_type': str(type(census_data)),
            'census_data_length': len(census_data) if census_data else 0,
            'census_data_keys': list(census_data.keys()) if census_data else [],
        }
        
        # Sample first county if available
        if census_data and len(census_data) > 0:
            first_county = list(census_data.keys())[0]
            first_county_data = census_data[first_county]
            debug_info['sample_county'] = first_county
            debug_info['sample_county_keys'] = list(first_county_data.keys()) if first_county_data else []
            if 'time_periods' in first_county_data:
                debug_info['sample_county_time_periods'] = list(first_county_data['time_periods'].keys()) if first_county_data.get('time_periods') else []
            if 'demographics' in first_county_data:
                debug_info['sample_county_has_demographics'] = True
        
        return jsonify(debug_info)
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    app.run(debug=True, host='0.0.0.0', port=port)

