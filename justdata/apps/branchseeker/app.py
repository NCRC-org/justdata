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
from .version import __version__


# Create the Flask app
app = create_app(
    'branchseeker',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)


def index():
    """Main page with the analysis form"""
    return render_template('analysis_template.html', version=__version__)


@app.route('/branch-mapper')
def branch_mapper():
    """BranchMapper - Interactive map of bank branch locations"""
    return render_template('branch_mapper_template.html', version=__version__)


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
        if selection_type == 'state' and not state_code:
            return jsonify({'error': 'Please select a state'}), 400
        elif selection_type == 'metro' and not metro_code:
            return jsonify({'error': 'Please select a metro area'}), 400
        elif selection_type == 'county' and not counties_str:
            return jsonify({'error': 'Please provide counties'}), 400
        
        if not years:
            return jsonify({'error': 'Please provide years'}), 400
        
        # Parse parameters (this will expand state/metro to counties if needed)
        from .core import parse_web_parameters
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
            download_name=f'branchseeker_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
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
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'branchseeker_reports.zip')
            
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
                    'Content-Disposition': f'attachment; filename=branchseeker_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
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
        print(f"Successfully fetched {len(counties_list)} counties")
        return jsonify(counties_list)
    except Exception as e:
        print(f"Error in counties endpoint: {e}")
        import traceback
        traceback.print_exc()
        # Return fallback list on error
        from .data_utils import get_fallback_counties
        return jsonify(get_fallback_counties())


def states():
    """Return a list of all available states"""
    try:
        from .data_utils import get_available_states
        states_list = get_available_states()
        return jsonify(states_list)
    except Exception as e:
        print(f"Error in states endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


def metro_areas():
    """Return a list of all available metro areas (CBSAs)"""
    try:
        from .data_utils import get_available_metro_areas
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

@app.route('/counties-by-state/<state_code>')
def counties_by_state_route(state_code):
    """Return a list of counties for a specific state"""
    try:
        from .data_utils import expand_state_to_counties
        print(f"Fetching counties for state code: {state_code}")
        counties_list = expand_state_to_counties(state_code)
        print(f"Found {len(counties_list)} counties for state {state_code}")
        if len(counties_list) == 0:
            print(f"WARNING: No counties found for state code {state_code}")
        return jsonify(counties_list)
    except Exception as e:
        print(f"Error in counties-by-state endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'counties': []
        }), 500

@app.route('/api/census-tracts/<county>')
def api_census_tracts(county):
    """Return census tract boundaries with income and/or minority data for a county"""
    try:
        from .census_tract_utils import (
            extract_fips_from_county_state,
            get_county_median_family_income,
            get_county_minority_percentage,
            get_tract_income_data,
            get_tract_minority_data,
            get_tract_boundaries_geojson,
            categorize_income_level,
            categorize_minority_level
        )
        
        # Check which data types to include
        include_income = request.args.get('income', 'true').lower() == 'true'
        include_minority = request.args.get('minority', 'true').lower() == 'true'
        
        # Extract FIPS codes
        fips_data = extract_fips_from_county_state(county)
        if not fips_data:
            return jsonify({
                'success': False,
                'error': f'Could not find FIPS codes for {county}'
            }), 400
        
        state_fips = fips_data['state_fips']
        county_fips = fips_data['county_fips']
        
        print(f"Using county-level baselines for {county} (State FIPS: {state_fips}, County FIPS: {county_fips})")
        
        # Get tract boundaries first (needed for all data types)
        tract_boundaries = get_tract_boundaries_geojson(state_fips, county_fips)
        if not tract_boundaries:
            return jsonify({
                'success': False,
                'error': f'Could not fetch census tract boundaries'
            }), 500
        
        # Initialize lookup dictionaries
        income_lookup = {}
        minority_lookup = {}
        
        # Get income data if requested
        baseline_income = None  # Will be county median
        if include_income:
            # Check if Census API key is available
            from .census_tract_utils import get_census_api_key
            api_key = get_census_api_key()
            if not api_key:
                print(f"WARNING: CENSUS_API_KEY not set. Cannot fetch income data.")
                return jsonify({
                    'success': False,
                    'error': 'CENSUS_API_KEY environment variable is not set. Please configure it to use income layers.'
                }), 500
            
            # Use county median income
            print(f"Attempting to fetch county median income for state FIPS: {state_fips}, county FIPS: {county_fips}")
            baseline_income = get_county_median_family_income(state_fips, county_fips)
            if baseline_income:
                print(f"[OK] Using county median income: ${baseline_income:,.0f} for {county}")
            else:
                print(f"[ERROR] Failed to fetch county median income for {county}")
            
            if baseline_income:
                print(f"Fetching tract-level income data for state FIPS: {state_fips}, county FIPS: {county_fips}")
                tract_income_data = get_tract_income_data(state_fips, county_fips)
                print(f"Fetched {len(tract_income_data)} tracts with income data")
                
                if len(tract_income_data) == 0:
                    print(f"WARNING: No tract income data returned from Census API")
                else:
                    # Show sample of first few GEOIDs
                    sample_geoids = [t['tract_geoid'] for t in tract_income_data[:3]]
                    print(f"Sample tract GEOIDs from income data: {sample_geoids}")
                
                for tract in tract_income_data:
                    geoid = tract['tract_geoid']
                    # Normalize GEOID to ensure consistent format (11 digits)
                    geoid_normalized = str(geoid).zfill(11)
                    income_lookup[geoid_normalized] = tract
                    # Also store with original format for flexibility
                    income_lookup[geoid] = tract
                print(f"Created income lookup with {len(income_lookup)} entries")
            else:
                print(f"ERROR: Cannot fetch tract income data - baseline income (CBSA or state) not available")
        
        # Get minority data if requested
        county_minority_pct = None
        if include_minority:
            # Check if Census API key is available
            from .census_tract_utils import get_census_api_key
            api_key = get_census_api_key()
            if not api_key:
                print(f"WARNING: CENSUS_API_KEY not set. Cannot fetch minority data.")
                return jsonify({
                    'success': False,
                    'error': 'CENSUS_API_KEY environment variable is not set. Please configure it to use minority layers.'
                }), 500
            
            # Use county minority percentage
            print(f"Attempting to fetch county minority percentage for state FIPS: {state_fips}, county FIPS: {county_fips}")
            county_minority_pct = get_county_minority_percentage(state_fips, county_fips)
            if county_minority_pct is not None:
                print(f"[OK] Using county minority percentage: {county_minority_pct:.1f}% for {county}")
            else:
                print(f"[ERROR] Failed to fetch county minority percentage for {county}")
            
            print(f"Fetching tract-level minority data for state FIPS: {state_fips}, county FIPS: {county_fips}")
            tract_minority_data = get_tract_minority_data(state_fips, county_fips)
            print(f"Fetched {len(tract_minority_data)} tracts with minority data")
            
            if len(tract_minority_data) == 0:
                print(f"WARNING: No tract minority data returned from Census API")
            else:
                # Show sample of first few GEOIDs
                sample_geoids = [t['tract_geoid'] for t in tract_minority_data[:3]]
                print(f"Sample tract GEOIDs from minority data: {sample_geoids}")
            
            for tract in tract_minority_data:
                geoid = tract['tract_geoid']
                # Normalize GEOID to ensure consistent format (11 digits)
                geoid_normalized = str(geoid).zfill(11)
                minority_lookup[geoid_normalized] = tract
                # Also store with original format for flexibility
                minority_lookup[geoid] = tract
            print(f"Created minority lookup with {len(minority_lookup)} entries")
        
        # Merge data with boundaries
        # Filter out features with invalid income data
        valid_features = []
        matched_count = 0
        unmatched_geoids = []
        sample_boundary_geoids = []
        filtered_count = 0
        
        for i, feature in enumerate(tract_boundaries['features']):
            geoid = feature['properties'].get('GEOID')
            
            # Collect sample GEOIDs from boundaries
            if i < 3:
                sample_boundary_geoids.append(geoid)
            
            # Normalize GEOID for matching (ensure it's a string and properly formatted)
            if geoid:
                geoid_str = str(geoid).strip()
                geoid_normalized = geoid_str.zfill(11)  # Ensure 11 digits
            else:
                geoid_str = None
                geoid_normalized = None
            
            # Add income data
            if include_income:
                # Try normalized first, then original
                tract_data = income_lookup.get(geoid_normalized) or income_lookup.get(geoid_str) or income_lookup.get(geoid)
                
                if tract_data:
                    median_income = tract_data.get('median_family_income')
                    
                    # Validate income value before using it
                    if median_income is not None and median_income > 0:
                        income_category = categorize_income_level(median_income, baseline_income) if baseline_income else 'Unknown'
                        
                        feature['properties']['median_family_income'] = median_income
                        feature['properties']['income_category'] = income_category
                        feature['properties']['baseline_median_income'] = baseline_income
                        feature['properties']['baseline_type'] = 'county'  # Always use county baseline
                        feature['properties']['income_ratio'] = (median_income / baseline_income) if median_income and baseline_income and baseline_income > 0 else None
                        matched_count += 1
                        # Feature has valid income - will be added to valid_features at end
                    else:
                        # Invalid income data - filter out from layer (don't include this tract)
                        if geoid:
                            print(f"Filtering out tract {geoid}: Invalid income data: {median_income}")
                        filtered_count += 1
                        continue  # Skip to next feature - don't add to valid_features
                else:
                    # No matching income data found - also filter out
                    if geoid:
                        print(f"Filtering out tract {geoid}: No income data found")
                    filtered_count += 1
                    continue  # Skip to next feature - don't add to valid_features
            
            # Add minority data
            if include_minority:
                # Try normalized first, then original
                tract_data = minority_lookup.get(geoid_normalized) or minority_lookup.get(geoid_str) or minority_lookup.get(geoid)
                
                if tract_data:
                    minority_pct = tract_data.get('minority_percentage')
                    total_pop = tract_data.get('total_population')
                    minority_pop = tract_data.get('minority_population')
                    
                    # Validate minority data before using it
                    if minority_pct is not None and minority_pct >= 0 and minority_pct <= 100 and total_pop is not None and total_pop > 0:
                        minority_category, minority_ratio = categorize_minority_level(minority_pct, county_minority_pct) if county_minority_pct else ('Unknown', None)
                        
                        feature['properties']['minority_percentage'] = minority_pct
                        feature['properties']['minority_category'] = minority_category
                        feature['properties']['county_minority_percentage'] = county_minority_pct
                        feature['properties']['minority_ratio'] = minority_ratio
                        feature['properties']['total_population'] = total_pop
                        feature['properties']['minority_population'] = minority_pop
                        # Feature has valid minority data - will be added to valid_features at end
                    else:
                        # Invalid minority data - filter out from layer
                        if geoid:
                            print(f"Filtering out tract {geoid}: Invalid minority data (pct: {minority_pct}, pop: {total_pop})")
                        if not include_income:
                            # If only minority was requested, filter it out completely
                            filtered_count += 1
                            continue
                        # If income was also requested and is valid, keep the feature but mark minority as unknown
                        feature['properties']['minority_percentage'] = None
                        feature['properties']['minority_category'] = 'Unknown'
                        feature['properties']['county_minority_percentage'] = county_minority_pct
                        feature['properties']['minority_ratio'] = None
                        feature['properties']['total_population'] = None
                        feature['properties']['minority_population'] = None
                else:
                    # No matching minority data found
                    if geoid:
                        print(f"Filtering out tract {geoid}: No minority data found")
                    if not include_income:
                        # If only minority was requested, filter it out completely
                        filtered_count += 1
                        continue
                    # If income was also requested and is valid, keep the feature but mark minority as unknown
                    feature['properties']['minority_percentage'] = None
                    feature['properties']['minority_category'] = 'Unknown'
                    feature['properties']['county_minority_percentage'] = county_minority_pct
                    feature['properties']['minority_ratio'] = None
                    feature['properties']['total_population'] = None
                    feature['properties']['minority_population'] = None
            
            # If we get here:
            # - If income was requested, the feature has valid income data (already validated above)
            # - If only minority was requested, the feature has valid minority data (already validated above)
            # - If both were requested, at least one is valid
            # - If neither was requested (shouldn't happen, but handle gracefully)
            if include_income or include_minority:
                valid_features.append(feature)
        
        # Update GeoJSON to only include features with valid data
        if include_income or include_minority:
            tract_boundaries['features'] = valid_features
            if include_income:
                print(f"Income layer: {matched_count} valid tracts, {filtered_count} invalid/water tracts filtered out")
            if include_minority:
                minority_matched = sum(1 for f in valid_features if f['properties'].get('minority_percentage') is not None and f['properties'].get('minority_percentage') >= 0)
                print(f"Minority layer: {minority_matched} valid tracts with minority data, {filtered_count} invalid/water tracts filtered out")
        
        if include_income:
            print(f"Matched {matched_count} out of {len(valid_features)} valid tracts with income data")
        
        result = {
            'success': True,
            'county': county,
            'tract_count': len(tract_boundaries['features']),
            'geojson': tract_boundaries
        }
        
        if include_income:
            result['baseline_median_family_income'] = baseline_income
            result['baseline_type'] = 'county'  # Always use county baseline
        
        if include_minority:
            result['county_minority_percentage'] = county_minority_pct
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in api_census_tracts endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/branches')
def api_branches():
    """Return branch data with coordinates for map display"""
    try:
        county = request.args.get('county', '').strip()
        year_str = request.args.get('year', '').strip()
        
        if not county or not year_str:
            return jsonify({'error': 'County and year parameters are required'}), 400
        
        try:
            year = int(year_str)
        except ValueError:
            return jsonify({'error': 'Year must be a valid integer'}), 400
        
        # Load SQL template and execute query
        from .core import load_sql_template
        from .data_utils import execute_branch_query
        
        sql_template = load_sql_template()
        branches = execute_branch_query(sql_template, county, year)
        
        # Log raw bank names before cleaning for debugging
        raw_bank_names = [b.get('bank_name', '') for b in branches if b.get('bank_name')]
        unique_raw_banks = sorted(set(raw_bank_names))
        print(f"[DEBUG] Raw bank names from SQL query ({len(unique_raw_banks)} unique): {unique_raw_banks[:20]}")  # Log first 20
        if any('tampa' in name.lower() for name in unique_raw_banks):
            tampa_banks = [name for name in unique_raw_banks if 'tampa' in name.lower()]
            print(f"[DEBUG] Banks containing 'Tampa' in raw data: {tampa_banks}")
        
        # Convert to JSON-serializable format
        import numpy as np
        result = []
        for branch in branches:
            branch_dict = {}
            for key, value in branch.items():
                # Handle numpy types and NaN values
                if hasattr(value, 'item'):  # numpy scalar
                    branch_dict[key] = value.item() if not np.isnan(value) else None
                elif isinstance(value, (np.integer, np.floating)):
                    branch_dict[key] = float(value) if not np.isnan(value) else None
                elif value is None or (isinstance(value, float) and np.isnan(value)):
                    branch_dict[key] = None
                else:
                    branch_dict[key] = value
            
            # Clean bank name - remove common suffixes
            if 'bank_name' in branch_dict and branch_dict['bank_name']:
                original_bank_name = str(branch_dict['bank_name']).strip()
                bank_name = original_bank_name
                
                # Remove common bank name suffixes using regex for better matching
                import re
                
                # Patterns to remove (case-insensitive, with optional comma/space)
                # First, remove "THE" from the beginning
                bank_name = re.sub(r'^THE\s+', '', bank_name, flags=re.IGNORECASE).strip()
                bank_name = re.sub(r'^The\s+', '', bank_name, flags=re.IGNORECASE).strip()
                
                # Then remove common suffixes at the end
                patterns = [
                    r',?\s*NATIONAL\s+ASSOCIATION\s*$',
                    r',?\s*National\s+Association\s*$',
                    r',?\s*N\.?\s*A\.?\s*$',
                    r',?\s*NA\s*$',
                    r',?\s*FEDERAL\s+SAVINGS\s+BANK\s*$',
                    r',?\s*Federal\s+Savings\s+Bank\s*$',
                    r',?\s*FSB\s*$',
                    r',?\s*FEDERAL\s+CREDIT\s+UNION\s*$',
                    r',?\s*Federal\s+Credit\s+Union\s*$',
                    r',?\s*FCU\s*$',
                    r',?\s*STATE\s+BANK\s*$',
                    r',?\s*State\s+Bank\s*$',
                    r',?\s*SAVINGS\s+BANK\s*$',
                    r',?\s*Savings\s+Bank\s*$',
                    r',?\s*SAVINGS\s+AND\s+LOAN\s*$',
                    r',?\s*Savings\s+and\s+Loan\s*$',
                    r',?\s*S&L\s*$',
                    r',?\s*INC\.?\s*$',
                    r',?\s*LLC\.?\s*$',
                    r',?\s*CORPORATION\s*$',
                    r',?\s*Corporation\s*$',
                    r',?\s*CORP\.?\s*$',
                    r',?\s*Corp\.?\s*$',
                    r',?\s*THE\s*$',
                    r',?\s*The\s*$',
                ]
                
                # Apply patterns repeatedly until no more matches
                changed = True
                iterations = 0
                max_iterations = 10  # Safety limit
                
                while changed and iterations < max_iterations:
                    changed = False
                    original_name = bank_name
                    
                    for pattern in patterns:
                        bank_name = re.sub(pattern, '', bank_name, flags=re.IGNORECASE).strip()
                        if bank_name != original_name:
                            changed = True
                            break
                    
                    iterations += 1
                
                # Final cleanup: remove trailing commas, spaces, and periods
                bank_name = re.sub(r'[,.\s]+$', '', bank_name).strip()
                
                # Log if this was a Tampa bank (for debugging)
                if 'tampa' in original_bank_name.lower() or 'tampa' in bank_name.lower():
                    print(f"[DEBUG] Tampa bank found - Original: '{original_bank_name}', Cleaned: '{bank_name}'")
                
                branch_dict['bank_name'] = bank_name
            
            # Map service_type to branch_type for popup compatibility
            # FDIC service type codes: 11=Full Service, 12=Limited Service, 13=Loan Production, etc.
            if 'service_type' in branch_dict and branch_dict['service_type']:
                service_type = branch_dict['service_type']
                
                # Handle numeric codes (convert to string for comparison)
                service_type_str = str(service_type).strip()
                
                # Map numeric codes to plain English descriptions
                # Based on FDIC Summary of Deposits service type definitions
                service_type_map = {
                    '11': 'Full Service, brick and mortar office',
                    '12': 'Full Service, retail office',
                    '13': 'Full Service, cyber office',
                    '21': 'Limited Service, administrative office',
                    '22': 'Limited Service, military facility',
                    '23': 'Limited Service, drive-through facility',
                    '24': 'Limited Service, loan production office',
                    '25': 'Limited Service, consumer credit office',
                    '26': 'Limited Service, contractual office',
                    '27': 'Limited Service, messenger office',
                    '28': 'Limited Service, retail office',
                    '29': 'Limited Service, mobile/seasonal office',
                    '30': 'Limited Service, trust office',
                    # Also handle text values for backward compatibility
                    'Full Service': 'Full Service Branch',
                    'Limited Service': 'Limited Service Branch',
                    'Loan Production': 'Loan Production Office',
                    'Consumer Credit': 'Consumer Credit Office',
                    'Other': 'Other Office',
                    'ATM': 'Automated Teller Machine',
                    'Mobile': 'Mobile Branch'
                }
                
                # Check if it's a known code or text
                if service_type_str in service_type_map:
                    branch_dict['branch_type'] = service_type_map[service_type_str]
                elif service_type_str.isdigit():
                    # Unknown numeric code - use generic description
                    branch_dict['branch_type'] = f'Service Type {service_type_str}'
                else:
                    # Unknown text - try to format it nicely
                    branch_dict['branch_type'] = f'{service_type_str} Branch' if not service_type_str.endswith('Branch') else service_type_str
            
            result.append(branch_dict)
        
        return jsonify({
            'success': True,
            'branches': result,
            'count': len(result)
        })
        
    except Exception as e:
        print(f"Error in api_branches endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

