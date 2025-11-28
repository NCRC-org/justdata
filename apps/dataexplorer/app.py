#!/usr/bin/env python3
"""
DataExplorer Flask Web Application
Interactive dashboard for HMDA, Small Business, and Branch data.
"""

from flask import Flask, render_template, request, jsonify, make_response
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.dataexplorer.config import DataExplorerConfig, TEMPLATES_DIR_STR, STATIC_DIR_STR
from apps.dataexplorer.query_builders import build_hmda_query, build_small_business_query, build_branch_query
from apps.dataexplorer.demographic_queries import build_hmda_demographic_query, build_sb_demographic_query
from apps.dataexplorer.data_utils import (
    get_available_states, get_available_counties, get_available_metros,
    get_available_hmda_lenders, get_available_sb_lenders, get_available_branch_banks,
    execute_query, aggregate_hmda_data, aggregate_sb_data, aggregate_branch_data,
    expand_geoids, get_lender_target_counties, get_lender_counties_by_lending_activity
)

# Create Flask app
app = Flask(
    'dataexplorer',
    template_folder=TEMPLATES_DIR_STR,
    static_folder=STATIC_DIR_STR
)

# Enable request logging
import logging
# Set up file logging for area analysis debugging
file_handler = logging.FileHandler('dataexplorer_debug.log', mode='a')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[logging.StreamHandler(), file_handler]  # Both console and file
)
app.logger.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)  # Ensure app logger also writes to file
# Also enable werkzeug logging
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.DEBUG)

# Configure Flask - AGGRESSIVE CACHE BUSTING (using shared utility)
app.secret_key = DataExplorerConfig.SECRET_KEY

# Use shared cache-busting configuration
from shared.web.flask_cache_busting import configure_flask_cache_busting, add_cache_busting_headers
configure_flask_cache_busting(app)


@app.route('/')
def index():
    """Main dashboard page."""
    # Force template reload by clearing cache before rendering
    if hasattr(app, 'jinja_env'):
        app.jinja_env.bytecode_cache = None
        app.jinja_env.cache = {}
        try:
            if hasattr(app.jinja_env.cache, 'clear'):
                app.jinja_env.cache.clear()
        except:
            pass
        print(f"DEBUG: Rendering dashboard.html, bytecode_cache={app.jinja_env.bytecode_cache}", flush=True)
    
    import time
    timestamp = int(time.time())
    # Force a new timestamp every time to bust browser cache
    response = make_response(render_template('dashboard.html', version=DataExplorerConfig.APP_VERSION, timestamp=timestamp))
    response = add_cache_busting_headers(response)
    # Also add a unique ETag based on timestamp to force reload
    response.headers['ETag'] = f'"{timestamp}"'
    return response


@app.route('/api/states', methods=['GET'])
def api_states():
    """Get available states."""
    try:
        states = get_available_states()
        return jsonify({'success': True, 'data': states})
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"API /api/states error: {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500


@app.route('/api/counties', methods=['GET'])
def api_counties():
    """Get available counties, optionally filtered by state."""
    state_code = request.args.get('state_code')
    try:
        counties = get_available_counties(state_code=state_code)
        return jsonify({'success': True, 'data': counties})
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"API /api/counties error: {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500


@app.route('/api/metros', methods=['GET'])
def api_metros():
    """Get available metro areas."""
    try:
        metros = get_available_metros()
        return jsonify({'success': True, 'data': metros})
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"API /api/metros error: {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500


@app.route('/api/geography/counties', methods=['POST'])
def api_geography_counties():
    """Get counties for metro areas or states."""
    try:
        data = request.get_json()
        metro_codes = data.get('metro_codes', [])
        state_codes = data.get('state_codes', [])
        
        if not metro_codes and not state_codes:
            return jsonify({'success': False, 'error': 'metro_codes or state_codes required'}), 400
        
        # Use expand_geoids to get county codes
        geoids = []
        if metro_codes:
            geoids.extend(metro_codes)
        if state_codes:
            geoids.extend(state_codes)
        
        expanded = expand_geoids(geoids)
        
        # Get county details
        from apps.dataexplorer.data_utils import get_available_counties
        all_counties = get_available_counties()
        
        # Filter to only expanded counties
        county_details = [
            c for c in all_counties 
            if c['geoid5'] in expanded
        ]
        
        # Sort by state, then county name
        county_details.sort(key=lambda x: (x['state'], x['name']))
        
        return jsonify({'success': True, 'data': county_details})
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({'success': False, 'error': error_msg}), 500


@app.route('/api/lenders/hmda', methods=['GET'])
def api_hmda_lenders():
    """Get available HMDA lenders, optionally filtered by geography and years."""
    geoids = request.args.getlist('geoids')
    years = request.args.getlist('years')
    years = [int(y) for y in years] if years else None
    
    try:
        lenders = get_available_hmda_lenders(geoids=geoids if geoids else None, years=years)
        return jsonify({'success': True, 'data': lenders})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lenders/sb', methods=['GET'])
def api_sb_lenders():
    """Get available Small Business lenders, optionally filtered by geography and years."""
    geoids = request.args.getlist('geoids')
    years = request.args.getlist('years')
    years = [int(y) for y in years] if years else None
    
    try:
        lenders = get_available_sb_lenders(geoids=geoids if geoids else None, years=years)
        return jsonify({'success': True, 'data': lenders})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lenders/branches', methods=['GET'])
def api_branch_banks():
    """Get available banks with branches, optionally filtered by geography and years."""
    geoids = request.args.getlist('geoids')
    years = request.args.getlist('years')
    years = [int(y) for y in years] if years else None
    
    try:
        banks = get_available_branch_banks(geoids=geoids if geoids else None, years=years)
        return jsonify({'success': True, 'data': banks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lenders/hmda/names', methods=['GET'])
def api_hmda_lender_names():
    """Get all HMDA lender names from lenders18 table for dropdown selection."""
    try:
        from apps.dataexplorer.data_utils import get_hmda_lenders_from_lenders18
        lenders = get_hmda_lenders_from_lenders18()
        return jsonify({'success': True, 'data': lenders})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error fetching lender names: {str(e)}'
        }), 500


@app.route('/api/lender/identifiers/<lei>', methods=['GET'])
def api_lender_identifiers(lei):
    """Get all associated identifiers (RSSD, Business Respondent ID) for a given LEI."""
    try:
        from apps.dataexplorer.data_utils import get_lender_identifiers_by_lei
        identifiers = get_lender_identifiers_by_lei(lei)
        return jsonify({'success': True, 'data': identifiers})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error fetching lender identifiers: {str(e)}'
        }), 500


@app.route('/api/lender/lookup', methods=['POST'])
def api_lender_lookup():
    """Look up lender information by name, LEI, RSSD, or Business Respondent ID."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip() if data.get('name') else None
        lei = data.get('lei', '').strip() if data.get('lei') else None
        rssd = data.get('rssd', '').strip() if data.get('rssd') else None
        respondent_id = data.get('respondent_id', '').strip() if data.get('respondent_id') else None
        
        if not any([name, lei, rssd, respondent_id]):
            return jsonify({
                'success': False,
                'error': 'Please provide at least one identifier (name, LEI, RSSD, or Business Respondent ID)'
            }), 400
        
        from apps.dataexplorer.data_utils import lookup_lender
        lender_info = lookup_lender(name=name, lei=lei, rssd=rssd, respondent_id=respondent_id)
        
        if lender_info:
            return jsonify({
                'success': True,
                'data': lender_info
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Lender not found. Please verify the identifier(s) and try again.'
            }), 404
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error looking up lender: {str(e)}'
        }), 500


@app.route('/api/lender/target-counties', methods=['POST'])
def api_lender_target_counties():
    """Get target counties for a lender based on 1% threshold (branches or lending)."""
    # Write to file as backup
    import os
    from pathlib import Path
    debug_file = Path(__file__).parent.parent.parent / 'dataexplorer_debug.log'
    with open(debug_file, 'a') as f:
        f.write("=" * 80 + "\n")
        f.write("[DEBUG] /api/lender/target-counties endpoint called\n")
        f.write("=" * 80 + "\n")
        f.flush()
    
    try:
        data = request.get_json()
        lender_id = data.get('lender_id')
        data_type = data.get('data_type', 'hmda')  # 'hmda', 'sb', or 'branches'
        years = data.get('years', None)
        selection_method = data.get('selection_method', 'threshold')  # 'threshold', 'lending_activity', or 'branches'
        action_taken = data.get('action_taken', None)  # For lending_activity method
        
        with open(debug_file, 'a') as f:
            f.write(f"[DEBUG] Request data: {data}\n")
            f.write(f"[DEBUG] Parsed: lender_id={lender_id}, data_type={data_type}, years={years}, selection_method={selection_method}\n")
            f.flush()
        
        if not lender_id:
            return jsonify({'success': False, 'error': 'Lender ID is required'}), 400
        
        if years:
            years = [int(y) for y in years]
        
        if selection_method == 'lending_activity' and data_type == 'hmda':
            # Get counties by lending activity (action_taken 1-5)
            counties = get_lender_counties_by_lending_activity(
                lender_id=lender_id,
                years=years,
                action_taken=action_taken
            )
        elif selection_method == 'branches':
            # Get counties by branch locations - use branches data type and RSSD
            # The lender_id should be RSSD when selection_method is 'branches'
            with open(debug_file, 'a') as f:
                f.write(f"[DEBUG] Calling get_lender_target_counties with lender_id={lender_id}, data_type='branches', years={years}\n")
                f.flush()
            counties = get_lender_target_counties(
                lender_id=lender_id,
                data_type='branches',
                years=years
            )
            with open(debug_file, 'a') as f:
                f.write(f"[DEBUG] get_lender_target_counties returned {len(counties)} counties\n")
                f.flush()
        else:
            # Default: 1% threshold
            counties = get_lender_target_counties(
                lender_id=lender_id,
                data_type=data_type,
                years=years
            )
        
        with open(debug_file, 'a') as f:
            f.write(f"[DEBUG] Returning {len(counties)} counties to frontend\n")
            f.write("=" * 80 + "\n\n")
            f.flush()
        return jsonify({'success': True, 'data': counties})
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"API /api/lender/target-counties error: {error_msg}", flush=True)
        error_response = jsonify({'success': False, 'error': error_msg})
        return add_cache_busting_headers(error_response), 500


@app.route('/api/lender/generate-assessment-areas-from-branches', methods=['POST'])
def api_generate_assessment_areas_from_branches():
    """Generate assessment areas from branch locations using MergerMeter logic."""
    try:
        data = request.get_json()
        rssd = data.get('rssd')
        year = data.get('year', 2025)
        min_deposit_share = data.get('min_deposit_share', 0.01)
        
        if not rssd:
            error_response = jsonify({'success': False, 'error': 'RSSD is required'})
            return add_cache_busting_headers(error_response), 400
        
        # Import MergerMeter function
        from apps.mergermeter.branch_assessment_area_generator import generate_assessment_areas_from_branches
        
        assessment_areas = generate_assessment_areas_from_branches(
            rssd=rssd,
            year=year,
            min_deposit_share=min_deposit_share
        )
        
        # Convert assessment areas to counties list for frontend
        counties = []
        geoid5_list = []
        for aa in assessment_areas:
            for county in aa.get('counties', []):
                if isinstance(county, dict):
                    state_code = county.get('state_code', '')
                    county_code = county.get('county_code', '')
                    if state_code and county_code:
                        geoid5 = str(state_code).zfill(2) + str(county_code).zfill(3)
                        geoid5_list.append(geoid5)
                        counties.append({
                            'geoid5': geoid5,
                            'state_code': state_code,
                            'county_code': county_code,
                            'cbsa_name': aa.get('cbsa_name', ''),
                            'assessment_area': aa.get('cbsa_name', '')
                        })
        
        # Look up county and state names from geo.cbsa_to_county table
        if geoid5_list:
            # Use execute_query from data_utils (already imported at top)
            # Normalize geoid5 values to 5-digit strings
            normalized_geoids = [str(g).zfill(5) for g in geoid5_list]
            geoid5_list_str = "', '".join(normalized_geoids)
            
            lookup_query = f"""
            SELECT DISTINCT
                LPAD(CAST(geoid5 AS STRING), 5, '0') as geoid5,
                County as county_name,
                State as state_name
            FROM `{DataExplorerConfig.GCP_PROJECT_ID}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
            WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') IN ('{geoid5_list_str}')
            """
            
            try:
                lookup_results = execute_query(lookup_query)
                if lookup_results:
                    # Create a map of geoid5 to county/state names
                    geoid_to_names = {}
                    for row in lookup_results:
                        geoid = str(row.get('geoid5', '')).zfill(5)
                        geoid_to_names[geoid] = {
                            'county_name': row.get('county_name', ''),
                            'state_name': row.get('state_name', '')
                        }
                    
                    # Update counties with names
                    for county in counties:
                        geoid = str(county['geoid5']).zfill(5)
                        if geoid in geoid_to_names:
                            county['county_name'] = geoid_to_names[geoid]['county_name']
                            county['state_name'] = geoid_to_names[geoid]['state_name']
                        else:
                            # Fallback: use geoid5 if name not found
                            county['county_name'] = county.get('county_name', f"County {geoid[2:]}")
                            county['state_name'] = county.get('state_name', '')
            except Exception as e:
                print(f"Warning: Could not look up county names: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        result = {
            'success': True,
            'assessment_areas': assessment_areas,
            'counties': counties,
            'count': len(assessment_areas)
        }
        
        response = jsonify(result)
        return add_cache_busting_headers(response)
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"API /api/lender/generate-assessment-areas-from-branches error: {error_msg}", flush=True)
        error_response = jsonify({'success': False, 'error': error_msg})
        return add_cache_busting_headers(error_response), 500


@app.route('/api/data/hmda', methods=['POST'])
def api_hmda_data():
    """Get HMDA data with filters."""
    try:
        data = request.get_json()
        
        # Parse filters
        geoids = data.get('geoids', [])
        # Expand geoids (metros/states to counties)
        geoids = expand_geoids(geoids)
        print(f"[DEBUG] Expanded geoids: {geoids}")
        years = [int(y) for y in data.get('years', [])]
        leis = data.get('leis', [])
        loan_purpose = data.get('loan_purpose', DataExplorerConfig.DEFAULT_HMDA_LOAN_PURPOSE)
        action_taken = data.get('action_taken', DataExplorerConfig.DEFAULT_HMDA_ACTION_TAKEN)
        occupancy_type = data.get('occupancy_type', DataExplorerConfig.DEFAULT_HMDA_OCCUPANCY)
        total_units = data.get('total_units', DataExplorerConfig.DEFAULT_HMDA_UNITS)
        construction_method = data.get('construction_method', DataExplorerConfig.DEFAULT_HMDA_CONSTRUCTION)
        exclude_reverse_mortgages = data.get('exclude_reverse_mortgages', DataExplorerConfig.DEFAULT_HMDA_EXCLUDE_REVERSE)
        include_peer_comparison = data.get('include_peer_comparison', False)
        subject_lei = data.get('subject_lei')
        aggregate = data.get('aggregate', True)
        group_by = data.get('group_by', ['activity_year', 'lei'])
        
        if not geoids or not years:
            return jsonify({'success': False, 'error': 'Geography and years are required'}), 400
        
        # Build and execute query
        try:
            query = build_hmda_query(
                geoids=geoids,
                years=years,
                leis=leis if leis else None,
                loan_purpose=loan_purpose if loan_purpose else None,
                action_taken=action_taken if action_taken else None,
                occupancy_type=occupancy_type if occupancy_type else None,
                total_units=total_units if total_units else None,
                construction_method=construction_method if construction_method else None,
                exclude_reverse_mortgages=exclude_reverse_mortgages,
                include_peer_comparison=include_peer_comparison,
                subject_lei=subject_lei
            )
        except Exception as query_build_error:
            import traceback
            error_msg = f"Error building query: {str(query_build_error)}"
            traceback.print_exc()
            print(f"API /api/data/hmda query build error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
        
        try:
            print(f"[DEBUG] Executing HMDA query for {len(geoids)} geoids, {len(years)} years...")
            print(f"[DEBUG] Geoids: {geoids}")
            print(f"[DEBUG] Years: {years}")
            print(f"[DEBUG] Filters: loan_purpose={loan_purpose}, action_taken={action_taken}, occupancy={occupancy_type}, units={total_units}, construction={construction_method}, exclude_reverse={exclude_reverse_mortgages}")
            results = execute_query(query)
            print(f"[DEBUG] Query returned {len(results)} rows")
            if len(results) == 0:
                print(f"[DEBUG] No data found. This could mean:")
                print(f"  - No HMDA data exists for the selected geography/years")
                print(f"  - The filters are too restrictive")
                print(f"  - The geoid format doesn't match the data")
        except Exception as query_exec_error:
            import traceback
            error_msg = f"Error executing query: {str(query_exec_error)}"
            traceback.print_exc()
            print(f"API /api/data/hmda query execution error: {error_msg}")
            print(f"Query was: {query[:1000]}...")  # Print first 1000 chars of query
            return jsonify({'success': False, 'error': error_msg}), 500
        
        # Aggregate if requested
        try:
            if aggregate:
                print(f"[DEBUG] Aggregating {len(results)} rows by {group_by}...")
                aggregated = aggregate_hmda_data(results, group_by=group_by)
                print(f"[DEBUG] Aggregation complete: {len(aggregated.get('data', []))} groups")
                return jsonify({'success': True, 'data': aggregated['data'], 'total_rows': aggregated['total_rows']})
            else:
                return jsonify({'success': True, 'data': results, 'total_rows': len(results)})
        except Exception as agg_error:
            import traceback
            error_msg = f"Error aggregating data: {str(agg_error)}"
            traceback.print_exc()
            print(f"API /api/data/hmda aggregation error: {error_msg}")
            print(f"First row sample: {results[0] if results else 'No results'}")
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"API /api/data/hmda general error: {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500


@app.route('/api/data/sb', methods=['POST'])
def api_sb_data():
    """Get Small Business data with filters."""
    try:
        data = request.get_json()
        
        # Parse filters
        geoids = data.get('geoids', [])
        # Expand geoids (metros/states to counties)
        geoids = expand_geoids(geoids)
        years = [int(y) for y in data.get('years', [])]
        respondent_ids = data.get('respondent_ids', [])
        include_peer_comparison = data.get('include_peer_comparison', False)
        subject_respondent_id = data.get('subject_respondent_id')
        aggregate = data.get('aggregate', True)
        group_by = data.get('group_by', ['year', 'sb_resid'])
        
        if not geoids or not years:
            return jsonify({'success': False, 'error': 'Geography and years are required'}), 400
        
        # Build and execute query
        query = build_small_business_query(
            geoids=geoids,
            years=years,
            respondent_ids=respondent_ids if respondent_ids else None,
            include_peer_comparison=include_peer_comparison,
            subject_respondent_id=subject_respondent_id
        )
        
        results = execute_query(query)
        
        # Aggregate if requested
        if aggregate:
            aggregated = aggregate_sb_data(results, group_by=group_by)
            return jsonify({'success': True, 'data': aggregated['data'], 'total_rows': aggregated['total_rows']})
        else:
            return jsonify({'success': True, 'data': results, 'total_rows': len(results)})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/data/branches', methods=['POST'])
def api_branch_data():
    """Get Branch data with filters."""
    try:
        data = request.get_json()
        
        # Parse filters
        geoids = data.get('geoids', [])
        # Expand geoids (metros/states to counties)
        geoids = expand_geoids(geoids)
        years = [int(y) for y in data.get('years', [])]
        rssd_ids = data.get('rssd_ids', [])
        include_peer_comparison = data.get('include_peer_comparison', False)
        subject_rssd = data.get('subject_rssd')
        aggregate = data.get('aggregate', True)
        group_by = data.get('group_by', ['year', 'rssd'])
        
        if not geoids or not years:
            return jsonify({'success': False, 'error': 'Geography and years are required'}), 400
        
        # Build and execute query
        query = build_branch_query(
            geoids=geoids,
            years=years,
            rssd_ids=rssd_ids if rssd_ids else None,
            include_peer_comparison=include_peer_comparison,
            subject_rssd=subject_rssd
        )
        
        results = execute_query(query)
        
        # Aggregate if requested
        if aggregate:
            aggregated = aggregate_branch_data(results, group_by=group_by)
            return jsonify({'success': True, 'data': aggregated['data'], 'total_rows': aggregated['total_rows']})
        else:
            return jsonify({'success': True, 'data': results, 'total_rows': len(results)})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/data/hmda/demographic', methods=['POST'])
def api_hmda_demographic():
    """Get HMDA data broken down by demographics, income, and neighborhood for all lenders."""
    try:
        data = request.get_json()
        
        geoids = data.get('geoids', [])
        # Expand geoids (metros/states to counties)
        geoids = expand_geoids(geoids)
        years = [int(y) for y in data.get('years', [])]
        loan_purpose = data.get('loan_purpose', DataExplorerConfig.DEFAULT_HMDA_LOAN_PURPOSE)
        action_taken = data.get('action_taken', DataExplorerConfig.DEFAULT_HMDA_ACTION_TAKEN)
        occupancy_type = data.get('occupancy_type', DataExplorerConfig.DEFAULT_HMDA_OCCUPANCY)
        total_units = data.get('total_units', DataExplorerConfig.DEFAULT_HMDA_UNITS)
        construction_method = data.get('construction_method', DataExplorerConfig.DEFAULT_HMDA_CONSTRUCTION)
        exclude_reverse_mortgages = data.get('exclude_reverse_mortgages', DataExplorerConfig.DEFAULT_HMDA_EXCLUDE_REVERSE)
        metric_type = data.get('metric_type', 'count')  # 'count' or 'amount'
        
        if not geoids or not years:
            return jsonify({'success': False, 'error': 'Geography and years are required'}), 400
        
        query = build_hmda_demographic_query(
            geoids=geoids,
            years=years,
            loan_purpose=loan_purpose if loan_purpose else None,
            action_taken=action_taken if action_taken else None,
            occupancy_type=occupancy_type if occupancy_type else None,
            total_units=total_units if total_units else None,
            construction_method=construction_method if construction_method else None,
            exclude_reverse_mortgages=exclude_reverse_mortgages,
            metric_type=metric_type
        )
        
        results = execute_query(query)
        return jsonify({'success': True, 'data': results, 'total_rows': len(results)})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/data/sb/demographic', methods=['POST'])
def api_sb_demographic():
    """Get Small Business data broken down by demographics, income, and loan size for all lenders."""
    try:
        data = request.get_json()
        
        geoids = data.get('geoids', [])
        # Expand geoids (metros/states to counties)
        geoids = expand_geoids(geoids)
        years = [int(y) for y in data.get('years', [])]
        metric_type = data.get('metric_type', 'count')  # 'count' or 'amount'
        
        if not geoids or not years:
            return jsonify({'success': False, 'error': 'Geography and years are required'}), 400
        
        query = build_sb_demographic_query(
            geoids=geoids,
            years=years,
            metric_type=metric_type
        )
        
        results = execute_query(query)
        return jsonify({'success': True, 'data': results, 'total_rows': len(results)})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/branches/locations', methods=['POST'])
def api_branch_locations():
    """Get branch locations for one or more banks."""
    try:
        data = request.get_json()
        
        rssd_ids = data.get('rssd_ids', [])
        year = data.get('year', 2025)
        
        if not rssd_ids:
            return jsonify({'success': False, 'error': 'At least one RSSD ID is required'}), 400
        
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        
        rssd_list = "', '".join(rssd_ids)
        
        query = f"""
        SELECT 
            CAST(b.rssd AS STRING) as rssd,
            b.bank_name,
            b.branch_name,
            b.address,
            b.city,
            b.state,
            b.zip,
            CAST(b.latitude AS FLOAT64) as latitude,
            CAST(b.longitude AS FLOAT64) as longitude,
            CAST(b.deposits_000s AS FLOAT64) * 1000 as deposits,
            CAST(b.geoid5 AS STRING) as geoid5,
            b.uninumbr
        FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}` b
        WHERE CAST(b.year AS STRING) = '{year}'
            AND CAST(b.rssd AS STRING) IN ('{rssd_list}')
            AND b.latitude IS NOT NULL
            AND b.longitude IS NOT NULL
        ORDER BY b.bank_name, b.city, b.address
        """
        
        results = execute_query(query)
        
        return jsonify({'success': True, 'data': results, 'total_rows': len(results)})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/area/hmda/analysis', methods=['POST'])
def api_area_hmda_analysis():
    """
    Get comprehensive Area Analysis data for HMDA.
    Returns all tables needed for the Area Analysis dashboard:
    - Summary table (yearly totals)
    - Demographic overview (race/ethnicity by year)
    - Income & neighborhood indicators (LMI/MMCT)
    - Top lenders (with demographics)
    - HHI (market concentration)
    - Trends (year-over-year changes)
    """
    try:
        # FORCE RELOAD modules to pick up code changes (development only)
        import importlib
        import sys
        modules_to_reload = [
            'apps.dataexplorer.demographic_queries',
            'apps.dataexplorer.area_analysis_processor',
            'apps.dataexplorer.query_builders',
            'apps.dataexplorer.config'
        ]
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                print(f"DEBUG: Reloaded module {module_name}", flush=True)
        
        # Re-import after reload
        from apps.dataexplorer.demographic_queries import build_hmda_demographic_query
        
        data = request.get_json()
        
        geoids = data.get('geoids', [])
        geoids = expand_geoids(geoids)
        years = sorted([int(y) for y in data.get('years', [])])
        loan_purpose = data.get('loan_purpose', DataExplorerConfig.DEFAULT_HMDA_LOAN_PURPOSE)
        action_taken = data.get('action_taken', DataExplorerConfig.DEFAULT_HMDA_ACTION_TAKEN)
        occupancy_type = data.get('occupancy_type', DataExplorerConfig.DEFAULT_HMDA_OCCUPANCY)
        total_units = data.get('total_units', DataExplorerConfig.DEFAULT_HMDA_UNITS)
        construction_method = data.get('construction_method', DataExplorerConfig.DEFAULT_HMDA_CONSTRUCTION)
        exclude_reverse_mortgages = data.get('exclude_reverse_mortgages', DataExplorerConfig.DEFAULT_HMDA_EXCLUDE_REVERSE)
        
        if not geoids or not years:
            return jsonify({'success': False, 'error': 'Geography and years are required'}), 400
        
        # Get detailed demographic data
        query = build_hmda_demographic_query(
            geoids=geoids,
            years=years,
            loan_purpose=loan_purpose if loan_purpose else None,
            action_taken=action_taken if action_taken else None,
            occupancy_type=occupancy_type if occupancy_type else None,
            total_units=total_units if total_units else None,
            construction_method=construction_method if construction_method else None,
            exclude_reverse_mortgages=exclude_reverse_mortgages,
            metric_type='count'
        )
        
        # Debug: Log the FULL query to a file for inspection
        query_log_file = REPO_ROOT / 'dataexplorer_query_log.sql'
        with open(query_log_file, 'w', encoding='utf-8') as f:
            f.write("-- Full Query Generated for Area Analysis\n")
            f.write(f"-- Generated at: {datetime.now().isoformat()}\n")
            f.write(f"-- Geoids: {geoids[:10]}... (total: {len(geoids)})\n")
            f.write(f"-- Years: {years}\n")
            f.write(f"-- Loan Purpose: {loan_purpose}\n")
            f.write(f"-- Action Taken: {action_taken}\n")
            f.write(f"-- Occupancy: {occupancy_type}\n")
            f.write(f"-- Units: {total_units}\n")
            f.write(f"-- Construction: {construction_method}\n")
            f.write(f"-- Exclude Reverse Mortgages: {exclude_reverse_mortgages}\n")
            f.write("\n")
            f.write(query)
            f.write("\n\n-- END OF QUERY --\n")
        app.logger.error(f"[AREA ANALYSIS HMDA] Full query saved to: {query_log_file}")
        app.logger.error(f"[AREA ANALYSIS HMDA] Query geoids (first 5): {geoids[:5]}")
        app.logger.error(f"[AREA ANALYSIS HMDA] Query geoids count: {len(geoids)}")
        app.logger.error(f"[AREA ANALYSIS HMDA] Query years: {years}")
        app.logger.error(f"[AREA ANALYSIS HMDA] Exclude reverse mortgages: {exclude_reverse_mortgages}")
        
        # Test with simpler queries to diagnose the issue
        if len(geoids) > 0:
            # Test 1: Check if data exists for these years at all
            test_query1 = f"""
            SELECT COUNT(*) as row_count
            FROM `{DataExplorerConfig.GCP_PROJECT_ID}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
            WHERE CAST(h.activity_year AS STRING) IN ('{"', '".join([str(y) for y in years])}')
              AND h.state_code IS NOT NULL
              AND h.county_code IS NOT NULL
            LIMIT 1
            """
            try:
                test_result1 = execute_query(test_query1)
                app.logger.error(f"[AREA ANALYSIS HMDA] Test 1 - Data for years {years} (any county): {test_result1}")
            except Exception as e:
                app.logger.error(f"[AREA ANALYSIS HMDA] Test 1 failed: {e}")
            
            # Test 2: Check if data exists for first geoid
            # Note: county_code is already the full 5-digit GEOID5
            test_query2 = f"""
            SELECT COUNT(*) as row_count
            FROM `{DataExplorerConfig.GCP_PROJECT_ID}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
            WHERE CAST(h.activity_year AS STRING) IN ('{"', '".join([str(y) for y in years])}')
              AND h.state_code IS NOT NULL
              AND h.county_code IS NOT NULL
              AND LPAD(CAST(h.county_code AS STRING), 5, '0') = '{str(geoids[0]).zfill(5)}'
            LIMIT 1
            """
            try:
                test_result2 = execute_query(test_query2)
                app.logger.error(f"[AREA ANALYSIS HMDA] Test 2 - Data for geoid {geoids[0]} and years {years}: {test_result2}")
            except Exception as e:
                app.logger.error(f"[AREA ANALYSIS HMDA] Test 2 failed: {e}")
            
            # Test 3: Check what the actual geoid format looks like in the table
            test_query3 = f"""
            SELECT 
                CAST(h.activity_year AS STRING) as activity_year,
                h.state_code,
                h.county_code,
                CONCAT(LPAD(CAST(h.state_code AS STRING), 2, '0'), LPAD(CAST(h.county_code AS STRING), 3, '0')) as geoid5,
                COUNT(*) as row_count
            FROM `{DataExplorerConfig.GCP_PROJECT_ID}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
            WHERE CAST(h.activity_year AS STRING) IN ('{"', '".join([str(y) for y in years])}')
              AND h.state_code IS NOT NULL
              AND h.county_code IS NOT NULL
            GROUP BY activity_year, state_code, county_code, geoid5
            ORDER BY row_count DESC
            LIMIT 5
            """
            try:
                test_result3 = execute_query(test_query3)
                app.logger.error(f"[AREA ANALYSIS HMDA] Test 3 - Sample geoids from table: {test_result3}")
            except Exception as e:
                app.logger.error(f"[AREA ANALYSIS HMDA] Test 3 failed: {e}")
        
        raw_data = execute_query(query)
        row_count = len(raw_data) if raw_data else 0
        log_msg = f"\n{'='*80}\n[AREA ANALYSIS HMDA] Query returned {row_count} rows\n[AREA ANALYSIS HMDA] Years requested: {years}\n[AREA ANALYSIS HMDA] Geoids count: {len(geoids)}"
        print(log_msg, flush=True)
        app.logger.error(log_msg)
        
        # Get loan-level data with census tracts for tract race matching
        # This query gets individual loans (not aggregated by lender) with census tract info
        from apps.dataexplorer.query_builders import build_hmda_query
        loan_level_query = build_hmda_query(
            geoids=geoids,
            years=years,
            loan_purpose=loan_purpose if loan_purpose else None,
            action_taken=action_taken if action_taken else None,
            occupancy_type=occupancy_type if occupancy_type else None,
            total_units=total_units if total_units else None,
            construction_method=construction_method if construction_method else None,
            exclude_reverse_mortgages=exclude_reverse_mortgages
        )
        # Modify the query to return loan-level data with census tracts
        # Replace the aggregation with individual loan records
        loan_level_query = loan_level_query.replace(
            "GROUP BY f.activity_year, f.lei, f.loan_purpose",
            "GROUP BY f.activity_year, f.lei, f.loan_purpose, f.census_tract, f.geoid5"
        )
        # Actually, we need a simpler query - just get loans with census tracts
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        geoid_list = "', '".join([str(g).zfill(5) for g in geoids])
        year_list = "', '".join([str(y) for y in years])
        where_conditions = [f"LPAD(CAST(h.county_code AS STRING), 5, '0') IN ('{geoid_list}')"]
        where_conditions.append(f"CAST(h.activity_year AS STRING) IN ('{year_list}')")
        if loan_purpose:
            purpose_list = "', '".join(loan_purpose)
            where_conditions.append(f"h.loan_purpose IN ('{purpose_list}')")
        if action_taken:
            action_list = "', '".join(action_taken)
            where_conditions.append(f"h.action_taken IN ('{action_list}')")
        if occupancy_type:
            occupancy_list = "', '".join(occupancy_type)
            where_conditions.append(f"h.occupancy_type IN ('{occupancy_list}')")
        if total_units:
            units_list = "', '".join(total_units)
            where_conditions.append(f"h.total_units IN ('{units_list}')")
        if construction_method:
            construction_list = "', '".join(construction_method)
            where_conditions.append(f"h.construction_method IN ('{construction_list}')")
        if exclude_reverse_mortgages:
            where_conditions.append("h.reverse_mortgage != '1'")
        where_clause = " AND ".join(where_conditions)
        
        # Optimize: Aggregate at tract level instead of fetching individual loans
        # This dramatically reduces the number of rows (from potentially millions to thousands)
        loan_level_query = f"""
        SELECT 
            CAST(h.activity_year AS STRING) as activity_year,
            LPAD(CAST(h.county_code AS STRING), 5, '0') as geoid5,
            h.census_tract,
            h.loan_purpose,
            COUNT(*) as loan_count,
            SUM(COALESCE(h.loan_amount, 0)) as loan_amount
        FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
        WHERE {where_clause}
          AND h.census_tract IS NOT NULL
        GROUP BY activity_year, geoid5, census_tract, loan_purpose
        """
        loan_level_data = execute_query(loan_level_query)
        app.logger.info(f"[AREA ANALYSIS HMDA] Loan-level query returned {len(loan_level_data) if loan_level_data else 0} rows for tract race matching")
        
        if raw_data and len(raw_data) > 0:
            sample_keys = list(raw_data[0].keys())
            first_row_sample = dict(list(raw_data[0].items())[:5])
            # Check activity_year values
            activity_years = set()
            for row in raw_data[:10]:  # Check first 10 rows
                year_val = row.get('activity_year', row.get('year'))
                activity_years.add(year_val)
            
            log_msg = f"[AREA ANALYSIS HMDA] Sample row keys: {sample_keys}\n[AREA ANALYSIS HMDA] First row sample: {first_row_sample}\n[AREA ANALYSIS HMDA] Unique activity_year values (first 10 rows): {activity_years}"
            print(log_msg, flush=True)
            app.logger.error(log_msg)
            app.logger.error(f"[AREA ANALYSIS HMDA] Full first row: {raw_data[0]}")
        else:
            log_msg = f"[AREA ANALYSIS HMDA] WARNING: No raw data returned from query!\n[AREA ANALYSIS HMDA] This could mean:\n  - No HMDA data for the selected geoids/years\n  - Query filters are too restrictive\n  - Query execution failed silently"
            print(log_msg, flush=True)
            app.logger.error(log_msg)
        
        # Get separate query for summary_by_purpose that includes ALL loan purposes
        # This ensures we always show Home Purchase, Refinance, and Home Equity
        query_all_purposes = build_hmda_demographic_query(
            geoids=geoids,
            years=years,
            loan_purpose=['1', '2', '4', '31', '32'],  # Always include all purposes for summary (1=Home Purchase, 2=Home Improvement, 4=Other, 31=Refinance, 32=Cash-out Refi)
            action_taken=action_taken if action_taken else None,  # Use same action_taken filter
            occupancy_type=occupancy_type if occupancy_type else None,
            total_units=total_units if total_units else None,
            construction_method=construction_method if construction_method else None,
            exclude_reverse_mortgages=exclude_reverse_mortgages,
            metric_type='count'
        )
        raw_data_all_purposes = execute_query(query_all_purposes)
        app.logger.error(f"[AREA ANALYSIS HMDA] Query for all purposes returned {len(raw_data_all_purposes) if raw_data_all_purposes else 0} rows")
        
        if not raw_data:
            return jsonify({
                'success': True,
                'data': {
                    'summary': [],
                    'demographics': [],
                    'income_neighborhood': [],
                    'top_lenders': [],
                    'hhi': None,
                    'hhi_by_year': [],
                    'trends': []
                }
            })
        
        # Process data into table formats
        from apps.dataexplorer.area_analysis_processor import process_hmda_area_analysis
        
        # Pass both filtered data and all-purposes data
        # Note: tract_race_data will be added after fetching, so we'll update demographics later
        analysis_data = process_hmda_area_analysis(raw_data, years, geoids, raw_data_all_purposes=raw_data_all_purposes)
        app.logger.info(f"[AREA ANALYSIS] Processed data - summary rows: {len(analysis_data.get('summary', []))}")
        app.logger.info(f"[AREA ANALYSIS] Summary by purpose rows: {len(analysis_data.get('summary_by_purpose', []))}")
        
        # Fetch 2024 ACS data for the selected geography
        try:
            from apps.dataexplorer.acs_utils import get_acs_data_for_geoids, get_household_income_distribution_for_geoids, get_tract_household_distributions_for_geoids, get_tract_race_data_for_geoids
            from apps.dataexplorer.area_analysis_processor import create_demographics_table_by_tract_race, create_demographics_by_purpose_table_by_tract_race
            acs_data = get_acs_data_for_geoids(geoids)
            household_income_data = get_household_income_distribution_for_geoids(geoids)
            # Fetch race data by census tract for matching with lending data
            tract_race_data = get_tract_race_data_for_geoids(geoids)
            analysis_data['acs_data'] = acs_data
            analysis_data['household_income_data'] = household_income_data
            analysis_data['tract_race_data'] = tract_race_data
            
            # Recreate demographics table using tract race data if available
            if tract_race_data and len(tract_race_data) > 0 and loan_level_data:
                app.logger.info(f"[AREA ANALYSIS] Recreating demographics table using tract race data ({len(tract_race_data)} tracts, {len(loan_level_data)} loans)")
                analysis_data['demographics'] = create_demographics_table_by_tract_race(loan_level_data, years, tract_race_data)
                # For by-purpose, filter loan_level_data by purpose
                demographics_by_purpose = {'all': analysis_data['demographics']}
                for purpose_name in ['Home Purchase', 'Refinance', 'Home Equity']:
                    if purpose_name == 'Home Purchase':
                        filtered_loans = [r for r in loan_level_data if str(r.get('loan_purpose', '')) == '1']
                    elif purpose_name == 'Refinance':
                        # Combine 31 and 32
                        filtered_loans = [r for r in loan_level_data if str(r.get('loan_purpose', '')) in ['31', '32']]
                    elif purpose_name == 'Home Equity':
                        filtered_loans = [r for r in loan_level_data if str(r.get('loan_purpose', '')) == '2']
                    else:
                        filtered_loans = []
                    
                    if filtered_loans:
                        demographics_by_purpose[purpose_name] = create_demographics_table_by_tract_race(filtered_loans, years, tract_race_data)
                    else:
                        demographics_by_purpose[purpose_name] = []
                analysis_data['demographics_by_purpose'] = demographics_by_purpose
                app.logger.info(f"[AREA ANALYSIS] Demographics by purpose created: {list(demographics_by_purpose.keys())}")
        except Exception as e:
            app.logger.warning(f"[AREA ANALYSIS] Could not fetch ACS data: {e}")
            import traceback
            app.logger.warning(f"[AREA ANALYSIS] ACS data error traceback: {traceback.format_exc()}")
            analysis_data['acs_data'] = {'total_population': 0, 'demographics': {}}
            analysis_data['household_income_data'] = {'total_households': 0, 'household_income_distribution': {}, 'metro_ami': None}
            analysis_data['tract_race_data'] = {}
        
        # Log what ACS data was fetched
        app.logger.info(f"[AREA ANALYSIS] ACS data fetched - total_population: {analysis_data.get('acs_data', {}).get('total_population', 0)}, "
                       f"demographics keys: {list(analysis_data.get('acs_data', {}).get('demographics', {}).keys())}")
        app.logger.info(f"[AREA ANALYSIS] Household income data fetched - total_households: {analysis_data.get('household_income_data', {}).get('total_households', 0)}, "
                       f"distribution keys: {list(analysis_data.get('household_income_data', {}).get('household_income_distribution', {}).keys())}")
        
        # Calculate MMCT breakdowns using standard deviation method
        try:
            from apps.dataexplorer.mmct_utils import calculate_mmct_breakdowns_from_query, get_average_minority_percentage
            mmct_breakdowns = calculate_mmct_breakdowns_from_query(
                geoids=geoids,
                years=years,
                loan_purpose=loan_purpose if loan_purpose else None,
                action_taken=action_taken if action_taken else None
            )
            # Calculate average minority percentage for the geography (used in table caption)
            avg_minority_pct = get_average_minority_percentage(geoids, years)
            analysis_data['avg_minority_percentage'] = avg_minority_pct
            
            # Get mean and stddev from mmct_breakdowns for percentage ranges
            mmct_stats = {}
            for year in years:
                year_str = str(year)
                year_data = mmct_breakdowns.get(year_str, {})
                mmct_stats[year_str] = {
                    'mean_minority': year_data.get('mean_minority', 0),
                    'stddev_minority': year_data.get('stddev_minority', 0)
                }
            analysis_data['mmct_stats'] = mmct_stats
            
            # Get tract-level household distributions for ACS column
            from apps.dataexplorer.acs_utils import get_tract_household_distributions_for_geoids
            tract_distributions = get_tract_household_distributions_for_geoids(geoids, avg_minority_pct)
            analysis_data['tract_distributions'] = tract_distributions
            app.logger.info(f"[AREA ANALYSIS] Tract distributions fetched - income: {tract_distributions.get('tract_income_distribution', {})}, minority: {tract_distributions.get('tract_minority_distribution', {})}, MMCT: {tract_distributions.get('mmct_percentage')}")
            if not tract_distributions.get('tract_income_distribution') and not tract_distributions.get('tract_minority_distribution'):
                app.logger.warning(f"[AREA ANALYSIS] No tract distribution data returned - check Census API key and tract matching logic")
            if tract_distributions.get('mmct_percentage') is None:
                app.logger.warning(f"[AREA ANALYSIS] MMCT percentage is None - check MMCT calculation logic")
            
            # Update income_neighborhood table with MMCT breakdowns
            for row in analysis_data.get('income_neighborhood', []):
                if row.get('indicator') == 'Majority-Minority Census Tracts (MMCT)':
                    # Calculate MMCT percentage from breakdowns (middle + upper = tracts with >=50% minority)
                    # MMCT is strictly >=50% minority, so we use middle + upper categories
                    for year in years:
                        year_str = str(year)
                        middle = mmct_breakdowns.get(year_str, {}).get('mmct_middle', {'count': 0, 'percent': 0})
                        upper = mmct_breakdowns.get(year_str, {}).get('mmct_upper', {'count': 0, 'percent': 0})
                        mmct_count = middle.get('count', 0) + upper.get('count', 0)
                        mmct_percent = middle.get('percent', 0) + upper.get('percent', 0)
                        row[year_str] = {'count': mmct_count, 'percent': round(mmct_percent, 2)}
                elif row.get('indicator') == 'Low Minority Tracts':
                    for year in years:
                        year_str = str(year)
                        breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_low', {'count': 0, 'percent': 0})
                        row[year_str] = {'count': breakdown['count'], 'percent': breakdown['percent']}
                elif row.get('indicator') == 'Moderate Minority Tracts':
                    for year in years:
                        year_str = str(year)
                        breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_moderate', {'count': 0, 'percent': 0})
                        row[year_str] = {'count': breakdown['count'], 'percent': breakdown['percent']}
                elif row.get('indicator') == 'Middle Minority Tracts':
                    for year in years:
                        year_str = str(year)
                        breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_middle', {'count': 0, 'percent': 0})
                        row[year_str] = {'count': breakdown['count'], 'percent': breakdown['percent']}
                elif row.get('indicator') == 'High Minority Tracts':
                    for year in years:
                        year_str = str(year)
                        breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_upper', {'count': 0, 'percent': 0})
                        row[year_str] = {'count': breakdown['count'], 'percent': breakdown['percent']}
            
            # Also update income_neighborhood_by_purpose
            for purpose_key in ['all', 'Home Purchase', 'Refinance', 'Home Equity']:
                purpose_table = analysis_data.get('income_neighborhood_by_purpose', {}).get(purpose_key, [])
                for row in purpose_table:
                    if row.get('indicator') == 'Majority-Minority Census Tracts (MMCT)':
                        # Calculate MMCT percentage from breakdowns (middle + upper = tracts with >=50% minority)
                        for year in years:
                            year_str = str(year)
                            middle = mmct_breakdowns.get(year_str, {}).get('mmct_middle', {'count': 0, 'percent': 0})
                            upper = mmct_breakdowns.get(year_str, {}).get('mmct_upper', {'count': 0, 'percent': 0})
                            mmct_count = middle.get('count', 0) + upper.get('count', 0)
                            mmct_percent = middle.get('percent', 0) + upper.get('percent', 0)
                            row[year_str] = {'count': mmct_count, 'percent': round(mmct_percent, 2)}
                    elif row.get('indicator') == 'Low Minority Tracts':
                        for year in years:
                            year_str = str(year)
                            breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_low', {'count': 0, 'percent': 0})
                            row[year_str] = {'count': breakdown['count'], 'percent': breakdown['percent']}
                    elif row.get('indicator') == 'Moderate Minority Tracts':
                        for year in years:
                            year_str = str(year)
                            breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_moderate', {'count': 0, 'percent': 0})
                            row[year_str] = {'count': breakdown['count'], 'percent': breakdown['percent']}
                    elif row.get('indicator') == 'Middle Minority Tracts':
                        for year in years:
                            year_str = str(year)
                            breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_middle', {'count': 0, 'percent': 0})
                            row[year_str] = {'count': breakdown['count'], 'percent': breakdown['percent']}
                    elif row.get('indicator') == 'High Minority Tracts':
                        for year in years:
                            year_str = str(year)
                            breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_upper', {'count': 0, 'percent': 0})
                            row[year_str] = {'count': breakdown['count'], 'percent': breakdown['percent']}
        except Exception as e:
            app.logger.warning(f"[AREA ANALYSIS] Could not calculate MMCT data: {e}")
            analysis_data['avg_minority_percentage'] = None
        
        # Add top lenders by year for Excel export (2020-2024)
        try:
            from apps.dataexplorer.area_analysis_processor import get_top_lenders_by_year
            export_years = [y for y in years if 2020 <= y <= 2024]
            if export_years:
                top_lenders_by_year = get_top_lenders_by_year(raw_data, export_years, top_n=10)
                analysis_data['top_lenders_by_year'] = top_lenders_by_year
        except Exception as e:
            app.logger.warning(f"[AREA ANALYSIS HMDA] Could not calculate top lenders by year: {e}")
            analysis_data['top_lenders_by_year'] = {}
        
        response = jsonify({'success': True, 'data': analysis_data})
        return add_cache_busting_headers(response)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_response = jsonify({'success': False, 'error': str(e)})
        return add_cache_busting_headers(error_response), 500


@app.route('/api/area/sb/analysis', methods=['POST'])
def api_area_sb_analysis():
    """
    Get comprehensive Area Analysis data for Small Business.
    Returns all tables needed for the Area Analysis dashboard.
    """
    try:
        data = request.get_json()
        
        geoids = data.get('geoids', [])
        geoids = expand_geoids(geoids)
        years = sorted([int(y) for y in data.get('years', [])])
        
        if not geoids or not years:
            return jsonify({'success': False, 'error': 'Geography and years are required'}), 400
        
        # Get Small Business demographic data
        query = build_sb_demographic_query(
            geoids=geoids,
            years=years,
            metric_type='count'
        )
        
        raw_data = execute_query(query)
        
        # Also need loan amounts for summary table
        amount_query = build_sb_demographic_query(
            geoids=geoids,
            years=years,
            metric_type='amount'
        )
        amount_data = execute_query(amount_query)
        
        # Merge amount data into raw_data by year and respondent_id
        # When metric_type is 'amount', the metric fields contain amounts
        amount_by_key = {}
        for row in amount_data:
            key = (str(row.get('year', '')), row.get('sb_resid', row.get('respondent_id', '')))
            amount_by_key[key] = {
                'sb_loans_amount': row.get('total_metric', 0),  # total_metric is amount when metric_type='amount'
                'lmict_metric': row.get('lmict_metric', 0),  # Amount for LMICT
                'low_income_metric': row.get('low_income_metric', 0),  # Amount for low income tracts
                'moderate_income_metric': row.get('moderate_income_metric', 0),  # Amount for moderate income tracts
                'middle_income_metric': row.get('middle_income_metric', 0),  # Amount for middle income tracts
                'upper_income_metric': row.get('upper_income_metric', 0),  # Amount for upper income tracts
                'amt_under_100k': row.get('loans_under_100k_metric', 0),  # This is amount when metric_type='amount'
                'amt_100k_250k': row.get('loans_100k_250k_metric', 0),
                'amt_250k_1m': row.get('loans_250k_1m_metric', 0),
                'amtsbrev_under_1m': row.get('rev_under_1m_metric', 0)  # Amount for revenue under $1M
            }
        
        for row in raw_data:
            key = (str(row.get('year', '')), row.get('sb_resid', row.get('respondent_id', '')))
            # Add revenue fields from count query
            row['numsbrev_under_1m'] = row.get('rev_under_1m_metric', 0)  # Count for revenue under $1M
            if key in amount_by_key:
                amount_data_row = amount_by_key[key]
                row['sb_loans_amount'] = amount_data_row.get('sb_loans_amount', 0)
                row['amt_under_100k'] = amount_data_row.get('amt_under_100k', 0)
                row['amt_100k_250k'] = amount_data_row.get('amt_100k_250k', 0)
                row['amt_250k_1m'] = amount_data_row.get('amt_250k_1m', 0)
                # Store income tract amounts separately (they're already amounts in the amount query)
                row['low_income_tract_amount'] = amount_data_row.get('low_income_metric', 0)
                row['moderate_income_tract_amount'] = amount_data_row.get('moderate_income_metric', 0)
                row['middle_income_tract_amount'] = amount_data_row.get('middle_income_metric', 0)
                row['upper_income_tract_amount'] = amount_data_row.get('upper_income_metric', 0)
                row['lmict_amount'] = amount_data_row.get('lmict_metric', 0)
                row['amt_under_100k'] = amount_by_key[key]['amt_under_100k']
                row['amt_100k_250k'] = amount_by_key[key]['amt_100k_250k']
                row['amt_250k_1m'] = amount_by_key[key]['amt_250k_1m']
                row['amtsbrev_under_1m'] = amount_data_row.get('amtsbrev_under_1m', 0)  # Amount for revenue under $1M
        
        if not raw_data:
            return jsonify({
                'success': True,
                'data': {
                    'summary': [],
                    'demographics': [],
                    'income_neighborhood': [],
                    'top_lenders': [],
                    'hhi': None,
                    'trends': []
                }
            })
        
        # Process data into table formats
        from apps.dataexplorer.area_analysis_processor import process_sb_area_analysis
        
        analysis_data = process_sb_area_analysis(raw_data, years, geoids)
        
        # Add top lenders by year for Excel export (2020-2024)
        try:
            from apps.dataexplorer.area_analysis_processor import get_sb_top_lenders_by_year
            export_years = [y for y in years if 2020 <= y <= 2024]
            if export_years:
                # For SB, we need to process raw_data differently
                top_lenders_by_year = get_sb_top_lenders_by_year(raw_data, export_years, top_n=10)
                analysis_data['top_lenders_by_year'] = top_lenders_by_year
        except Exception as e:
            app.logger.warning(f"[AREA ANALYSIS SB] Could not calculate top lenders by year: {e}")
            analysis_data['top_lenders_by_year'] = {}
        
        # Fetch ACS data for household income distribution (for demographics table)
        try:
            from apps.dataexplorer.acs_utils import get_household_income_distribution_for_geoids
            household_income_data = get_household_income_distribution_for_geoids(geoids)
            analysis_data['household_income_data'] = household_income_data
            # Also add to acs_data for consistency
            if 'acs_data' not in analysis_data:
                analysis_data['acs_data'] = {}
            analysis_data['acs_data']['household_income_distribution'] = household_income_data.get('household_income_distribution', {})
        except Exception as e:
            app.logger.warning(f"[AREA ANALYSIS SB] Could not fetch household income data: {e}")
            analysis_data['household_income_data'] = {'household_income_distribution': {}}
            if 'acs_data' not in analysis_data:
                analysis_data['acs_data'] = {}
            analysis_data['acs_data']['household_income_distribution'] = {}
        
        # Calculate MMCT breakdowns using standard deviation method (same as mortgage)
        mmct_breakdowns = {}
        try:
            from apps.dataexplorer.mmct_utils import calculate_sb_mmct_breakdowns_from_query, get_average_minority_percentage
            app.logger.info(f"[AREA ANALYSIS SB] Calculating MMCT breakdowns for geoids={geoids}, years={years}")
            mmct_breakdowns = calculate_sb_mmct_breakdowns_from_query(
                geoids=geoids,
                years=years
            )
            app.logger.info(f"[AREA ANALYSIS SB] MMCT breakdowns calculated: {list(mmct_breakdowns.keys())}")
            if not mmct_breakdowns:
                app.logger.warning(f"[AREA ANALYSIS SB] MMCT breakdowns is empty - check query results")
            
            # Calculate average minority percentage for the geography (used in table caption)
            avg_minority_pct = get_average_minority_percentage(geoids, years)
            analysis_data['avg_minority_percentage'] = avg_minority_pct
            app.logger.info(f"[AREA ANALYSIS SB] Average minority percentage: {avg_minority_pct}%")
            
            # Get mean and stddev from mmct_breakdowns for percentage ranges
            mmct_stats = {}
            for year in years:
                year_str = str(year)
                year_data = mmct_breakdowns.get(year_str, {})
                mmct_stats[year_str] = {
                    'mean_minority': year_data.get('mean_minority', 0),
                    'stddev_minority': year_data.get('stddev_minority', 0)
                }
            analysis_data['mmct_stats'] = mmct_stats
            app.logger.info(f"[AREA ANALYSIS SB] MMCT stats: {mmct_stats}")
            
            # Get tract-level household distributions for ACS column (same as HMDA - uses geographic tract data)
            from apps.dataexplorer.acs_utils import get_tract_household_distributions_for_geoids
            tract_distributions = get_tract_household_distributions_for_geoids(geoids, avg_minority_pct)
            analysis_data['tract_distributions'] = tract_distributions
            app.logger.info(f"[AREA ANALYSIS SB] Tract distributions fetched - income: {tract_distributions.get('tract_income_distribution', {})}, minority: {tract_distributions.get('tract_minority_distribution', {})}, MMCT: {tract_distributions.get('mmct_percentage')}")
            if not tract_distributions.get('tract_income_distribution') and not tract_distributions.get('tract_minority_distribution'):
                app.logger.warning(f"[AREA ANALYSIS SB] No tract distribution data returned - check Census API key and tract matching logic")
            
            # Get total amounts for MMCT calculations (need to query aggregate table)
            # For now, we'll calculate amounts from the raw_data we already have
            # Calculate total amount by year for MMCT percentage calculations
            total_amounts_by_year = {}
            total_counts_by_year = {}
            for row in raw_data:
                year_str = str(row.get('year', ''))
                if year_str in [str(y) for y in years]:
                    if year_str not in total_amounts_by_year:
                        total_amounts_by_year[year_str] = 0
                        total_counts_by_year[year_str] = 0
                    total_amounts_by_year[year_str] += float(row.get('sb_loans_amount', 0) or 0)
                    total_counts_by_year[year_str] += int(row.get('sb_loans_count', row.get('total_metric', 0)) or 0)
            
            # Update income_neighborhood table with MMCT breakdowns
            if 'income_neighborhood' in analysis_data:
                app.logger.info(f"[AREA ANALYSIS SB] Updating income_neighborhood table with MMCT data")
                # First, ensure MMCT row exists - if not, create it
                mmct_row = None
                for row in analysis_data['income_neighborhood']:
                    if row.get('indicator') == 'Majority-Minority Census Tracts (MMCT)':
                        mmct_row = row
                        break
                
                # If MMCT row doesn't exist, create it
                if not mmct_row:
                    app.logger.info(f"[AREA ANALYSIS SB] Creating MMCT row (not found in table)")
                    mmct_row = {'indicator': 'Majority-Minority Census Tracts (MMCT)'}
                    for year in years:
                        mmct_row[str(year)] = {'count': 0, 'percent': 0, 'amount': 0, 'amount_percent': 0}
                    analysis_data['income_neighborhood'].append(mmct_row)
                
                # Now update all MMCT-related rows
                for row in analysis_data['income_neighborhood']:
                    if row.get('indicator') == 'Majority-Minority Census Tracts (MMCT)':
                        # MMCT = percentage of loans in tracts with >=50% minority population
                        # Calculate from breakdowns (middle + upper = tracts with >=50% minority)
                        # OR use mmct_percentage if available (from calculate_sb_mmct_breakdowns_from_query)
                        for year in years:
                            year_str = str(year)
                            year_breakdown = mmct_breakdowns.get(year_str, {})
                            
                            # Try to use mmct_percentage first (calculated directly from >=50% threshold)
                            if 'mmct_percentage' in year_breakdown:
                                mmct_data = year_breakdown['mmct_percentage']
                                mmct_count = mmct_data.get('count', 0)
                                mmct_percent = mmct_data.get('percent', 0)
                            else:
                                # Fallback: calculate from middle + upper categories
                                middle = year_breakdown.get('mmct_middle', {'count': 0, 'percent': 0})
                                upper = year_breakdown.get('mmct_upper', {'count': 0, 'percent': 0})
                                mmct_count = middle.get('count', 0) + upper.get('count', 0)
                                mmct_percent = middle.get('percent', 0) + upper.get('percent', 0)
                            
                            total_amount = total_amounts_by_year.get(year_str, 0)
                            total_count = total_counts_by_year.get(year_str, 0)
                            
                            # If mmct_count is 0 but we have total loans, recalculate percent from count
                            if mmct_count == 0 and total_count > 0 and mmct_percent == 0:
                                # Try to get mmct_percent from the breakdown data
                                if 'mmct_percentage' in year_breakdown:
                                    mmct_percent = year_breakdown['mmct_percentage'].get('percent', 0)
                                    mmct_count = year_breakdown['mmct_percentage'].get('count', 0)
                            
                            row[year_str] = {
                                'count': mmct_count,
                                'percent': round(mmct_percent, 2),
                                'amount': round(total_amount * (mmct_percent / 100), 2),
                                'amount_percent': round(mmct_percent, 2)
                            }
                        app.logger.info(f"[AREA ANALYSIS SB] Updated MMCT row for year {year_str}: count={mmct_count}, percent={mmct_percent}%")
                    elif row.get('indicator') == 'Low Minority Tracts':
                        for year in years:
                            year_str = str(year)
                            breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_low', {'count': 0, 'percent': 0})
                            total_amount = total_amounts_by_year.get(year_str, 0)
                            row[year_str] = {
                                'count': breakdown.get('count', 0), 
                                'percent': breakdown.get('percent', 0),
                                'amount': round(total_amount * (breakdown.get('percent', 0) / 100), 2),
                                'amount_percent': breakdown.get('percent', 0)
                            }
                        app.logger.info(f"[AREA ANALYSIS SB] Updated Low Minority Tracts row: {row}")
                    elif row.get('indicator') == 'Moderate Minority Tracts':
                        for year in years:
                            year_str = str(year)
                            breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_moderate', {'count': 0, 'percent': 0})
                            total_amount = total_amounts_by_year.get(year_str, 0)
                            row[year_str] = {
                                'count': breakdown.get('count', 0), 
                                'percent': breakdown.get('percent', 0),
                                'amount': round(total_amount * (breakdown.get('percent', 0) / 100), 2),
                                'amount_percent': breakdown.get('percent', 0)
                            }
                        app.logger.info(f"[AREA ANALYSIS SB] Updated Moderate Minority Tracts row: {row}")
                    elif row.get('indicator') == 'Middle Minority Tracts':
                        for year in years:
                            year_str = str(year)
                            breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_middle', {'count': 0, 'percent': 0})
                            total_amount = total_amounts_by_year.get(year_str, 0)
                            row[year_str] = {
                                'count': breakdown.get('count', 0), 
                                'percent': breakdown.get('percent', 0),
                                'amount': round(total_amount * (breakdown.get('percent', 0) / 100), 2),
                                'amount_percent': breakdown.get('percent', 0)
                            }
                        app.logger.info(f"[AREA ANALYSIS SB] Updated Middle Minority Tracts row: {row}")
                    elif row.get('indicator') == 'High Minority Tracts':
                        for year in years:
                            year_str = str(year)
                            breakdown = mmct_breakdowns.get(year_str, {}).get('mmct_upper', {'count': 0, 'percent': 0})
                            total_amount = total_amounts_by_year.get(year_str, 0)
                            row[year_str] = {
                                'count': breakdown.get('count', 0), 
                                'percent': breakdown.get('percent', 0),
                                'amount': round(total_amount * (breakdown.get('percent', 0) / 100), 2),
                                'amount_percent': breakdown.get('percent', 0)
                            }
                        app.logger.info(f"[AREA ANALYSIS SB] Updated High Minority Tracts row: {row}")
                
                # Ensure MMCT breakdown rows exist even if they weren't found
                mmct_breakdown_indicators = ['Low Minority Tracts', 'Moderate Minority Tracts', 'Middle Minority Tracts', 'High Minority Tracts']
                for breakdown_indicator in mmct_breakdown_indicators:
                    breakdown_row = None
                    for row in analysis_data['income_neighborhood']:
                        if row.get('indicator') == breakdown_indicator:
                            breakdown_row = row
                            break
                    
                    # If breakdown row doesn't exist, create it
                    if not breakdown_row:
                        breakdown_row = {'indicator': breakdown_indicator}
                        for year in years:
                            breakdown_row[str(year)] = {'count': 0, 'percent': 0, 'amount': 0, 'amount_percent': 0}
                        analysis_data['income_neighborhood'].append(breakdown_row)
                        
                        # Now populate it with data from mmct_breakdowns
                        mmct_key_map = {
                            'Low Minority Tracts': 'mmct_low',
                            'Moderate Minority Tracts': 'mmct_moderate',
                            'Middle Minority Tracts': 'mmct_middle',
                            'High Minority Tracts': 'mmct_upper'
                        }
                        mmct_key = mmct_key_map.get(breakdown_indicator)
                        if mmct_key:
                            for year in years:
                                year_str = str(year)
                                breakdown = mmct_breakdowns.get(year_str, {}).get(mmct_key, {'count': 0, 'percent': 0})
                                total_amount = total_amounts_by_year.get(year_str, 0)
                                breakdown_row[year_str] = {
                                    'count': breakdown.get('count', 0), 
                                    'percent': breakdown.get('percent', 0),
                                    'amount': round(total_amount * (breakdown.get('percent', 0) / 100), 2),
                                    'amount_percent': breakdown.get('percent', 0)
                                }
                            app.logger.info(f"[AREA ANALYSIS SB] Created and populated {breakdown_indicator} row: {breakdown_row}")
        except Exception as e:
            app.logger.warning(f"[AREA ANALYSIS SB] Could not calculate MMCT data: {e}")
            import traceback
            traceback.print_exc()
            analysis_data['avg_minority_percentage'] = None
            analysis_data['mmct_stats'] = {}
            # Ensure MMCT row exists even if calculation failed
            if 'income_neighborhood' in analysis_data:
                mmct_row = None
                for row in analysis_data['income_neighborhood']:
                    if row.get('indicator') == 'Majority-Minority Census Tracts (MMCT)':
                        mmct_row = row
                        break
                if not mmct_row:
                    mmct_row = {'indicator': 'Majority-Minority Census Tracts (MMCT)'}
                    for year in years:
                        mmct_row[str(year)] = {'count': 0, 'percent': 0, 'amount': 0, 'amount_percent': 0}
                    analysis_data['income_neighborhood'].append(mmct_row)
        
        # Add top lenders by year for Excel export (2020-2024)
        try:
            from apps.dataexplorer.area_analysis_processor import get_sb_top_lenders_by_year
            export_years = [y for y in years if 2020 <= y <= 2024]
            if export_years:
                top_lenders_by_year = get_sb_top_lenders_by_year(raw_data, export_years, top_n=10)
                analysis_data['top_lenders_by_year'] = top_lenders_by_year
        except Exception as e:
            app.logger.warning(f"[AREA ANALYSIS SB] Could not calculate top lenders by year: {e}")
            analysis_data['top_lenders_by_year'] = {}
        
        response = jsonify({'success': True, 'data': analysis_data})
        return add_cache_busting_headers(response)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_response = jsonify({'success': False, 'error': str(e)})
        return add_cache_busting_headers(error_response), 500


@app.route('/api/area/branches/analysis', methods=['POST'])
def api_area_branches_analysis():
    """
    Get comprehensive Area Analysis data for Branch locations.
    Returns all tables needed for the Area Analysis dashboard.
    """
    try:
        data = request.get_json()
        
        geoids = data.get('geoids', [])
        geoids = expand_geoids(geoids)
        years = sorted([int(y) for y in data.get('years', [])])
        
        if not geoids or not years:
            return jsonify({'success': False, 'error': 'Geography and years are required'}), 400
        
        # Get Branch data - use sod25 table for all years (2021-2025)
        from apps.dataexplorer.data_utils import get_bigquery_client
        from google.cloud.bigquery import QueryJobConfig
        
        client = get_bigquery_client()
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        
        geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
        years_list = "', '".join([str(y) for y in years])
        
        # Determine which tables to use - sod_legacy for 2021-2024, sod25 for 2025
        legacy_years = [y for y in years if y < 2025]
        sod25_years = [y for y in years if y >= 2025]
        
        # Build query with UNION ALL for both tables
        branch_table_queries = []
        
        if legacy_years:
            branch_table_queries.append(f"""
                SELECT 
                    year, geoid5, rssd, bank_name, branch_name, deposits_000s, 
                    br_lmi, br_minority as cr_minority, 
                    -- Handle geoid: if it's a number, cast to string and pad; if it's already a string, ensure it's 11 digits
                    LPAD(TRIM(CAST(geoid AS STRING)), 11, '0') as census_tract
                FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.sod_legacy`
                WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') IN ('{geoid5_list}')
                    AND CAST(year AS STRING) IN ('{"', '".join([str(y) for y in legacy_years])}')
                    AND geoid IS NOT NULL
            """)
        
        if sod25_years:
            branch_table_queries.append(f"""
                SELECT 
                    year, geoid5, rssd, bank_name, branch_name, deposits_000s, 
                    br_lmi, br_minority as cr_minority, 
                    LPAD(CAST(geoid AS STRING), 11, '0') as census_tract
                FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}`
                WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') IN ('{geoid5_list}')
                    AND CAST(year AS STRING) IN ('{"', '".join([str(y) for y in sod25_years])}')
            """)
        
        if not branch_table_queries:
            # No years match - return empty response
            response = jsonify({
                'success': True,
                'data': {
                    'summary': [],
                    'demographics': [],
                    'income_neighborhood': [],
                    'top_lenders': [],
                    'hhi': None,
                    'trends': []
                }
            })
            return add_cache_busting_headers(response)
        
        query = f"""
            WITH branch_data AS (
                {' UNION ALL '.join(branch_table_queries)}
            )
            SELECT 
                CAST(b.year AS STRING) as year,
                CAST(b.geoid5 AS STRING) as geoid5,
                CAST(b.rssd AS STRING) as rssd,
                b.bank_name,
                b.branch_name,
                CAST(b.deposits_000s AS FLOAT64) * 1000 as deposits,
                -- Income tract flags - MUST use census data (income_level from geo.census table)
                -- income_level: 1=low (<=50% AMI), 2=moderate (<=80% AMI), 3=middle (<=120% AMI), 4=upper (>120% AMI)
                COALESCE(CAST(b.br_lmi AS INT64), 
                    CASE WHEN c.income_level IN (1, 2) THEN 1 ELSE 0 END, 0) as is_lmi_tract,
                -- Individual income tract flags - use census income_level directly (percentages must come from census)
                CASE WHEN c.income_level = 1 THEN 1 ELSE 0 END as is_low_income_tract,
                CASE WHEN c.income_level = 2 THEN 1 ELSE 0 END as is_moderate_income_tract,
                CASE WHEN c.income_level = 3 THEN 1 ELSE 0 END as is_middle_income_tract,
                CASE WHEN c.income_level = 4 THEN 1 ELSE 0 END as is_upper_income_tract,
                -- MMCT flag - use census data for minority percentage
                COALESCE(CAST(b.cr_minority AS INT64),
                    CASE WHEN SAFE_DIVIDE(
                        COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
                        NULLIF(COALESCE(c.total_persons, 0), 0)
                    ) * 100 > 50 THEN 1 ELSE 0 END, 0) as is_mmct_tract,
                -- Minority population percentage for breakdowns - MUST come from census
                SAFE_DIVIDE(
                    COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
                    NULLIF(COALESCE(c.total_persons, 0), 0)
                ) * 100 as tract_minority_population_percent
            FROM branch_data b
            LEFT JOIN (
                SELECT 
                    geoid,
                    income_level,
                    total_persons,
                    total_white,
                    ROW_NUMBER() OVER (PARTITION BY geoid ORDER BY CAST(year AS INT64) DESC) as rn
                FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CENSUS_TABLE}`
            ) c
                ON b.census_tract = LPAD(CAST(c.geoid AS STRING), 11, '0')
                AND c.rn = 1
            ORDER BY b.year, b.rssd, b.bank_name
            """
        
        raw_data = execute_query(query)
        
        if not raw_data:
            response = jsonify({
                'success': True,
                'data': {
                    'summary': [],
                    'demographics': [],
                    'income_neighborhood': [],
                    'top_lenders': [],
                    'hhi': None,
                    'trends': []
                }
            })
            return add_cache_busting_headers(response)
        
        # Process data into table formats
        from apps.dataexplorer.area_analysis_processor import process_branch_area_analysis
        
        analysis_data = process_branch_area_analysis(raw_data, years, geoids)
        
        # Get tract-level household distributions for ACS column (same as small business)
        from apps.dataexplorer.acs_utils import get_tract_household_distributions_for_geoids
        # Calculate average minority percentage for tract distributions
        avg_minority_pct = None
        if raw_data:
            minority_pcts = [float(row.get('tract_minority_population_percent', 0)) 
                           for row in raw_data if row.get('tract_minority_population_percent') is not None]
            if minority_pcts:
                avg_minority_pct = sum(minority_pcts) / len(minority_pcts)
        tract_distributions = get_tract_household_distributions_for_geoids(geoids, avg_minority_pct)
        analysis_data['tract_distributions'] = tract_distributions
        app.logger.info(f"[BRANCH ANALYSIS] Tract distributions fetched - income: {tract_distributions.get('tract_income_distribution', {})}, minority: {tract_distributions.get('tract_minority_distribution', {})}")
        
        # Include raw_data for Excel export
        analysis_data['raw_data'] = raw_data
        
        response = jsonify({'success': True, 'data': analysis_data})
        return add_cache_busting_headers(response)
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("=" * 80, flush=True)
        print("ERROR in api_area_branches_analysis:", flush=True)
        print("=" * 80, flush=True)
        print(f"Error type: {type(e).__name__}", flush=True)
        print(f"Error message: {str(e)}", flush=True)
        print("\nFull traceback:", flush=True)
        print(error_trace, flush=True)
        print("=" * 80, flush=True)
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': error_trace if app.config.get('DEBUG') else None
        }), 500


@app.route('/favicon.ico')
def favicon():
    """Favicon endpoint - return 204 No Content."""
    return '', 204


@app.route('/api/test/query', methods=['GET'])
def api_test_query():
    """Test endpoint to verify BigQuery connection and simple query."""
    try:
        from apps.dataexplorer.data_utils import get_bigquery_client, execute_query
        from apps.dataexplorer.config import DataExplorerConfig
        
        # Simple test query
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        query = f"""
        SELECT COUNT(*) as total_rows
        FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}`
        WHERE CAST(activity_year AS STRING) = '2024'
        LIMIT 1
        """
        
        results = execute_query(query)
        return jsonify({
            'success': True, 
            'message': 'BigQuery connection successful',
            'test_result': results[0] if results else None
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': error_msg,
            'type': type(e).__name__
        }), 500


@app.route('/api/debug/query', methods=['GET'])
def api_debug_query():
    """Get the last generated query for debugging."""
    import os
    query_log_file = os.path.join(REPO_ROOT, 'dataexplorer_query_log.sql')
    if os.path.exists(query_log_file):
        with open(query_log_file, 'r', encoding='utf-8') as f:
            query_text = f.read()
        return jsonify({
            'success': True,
            'query': query_text,
            'file': query_log_file
        })
    else:
        return jsonify({
            'success': False,
            'error': 'No query log file found. Run an analysis first.',
            'file': query_log_file
        }), 404

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'app': 'dataexplorer',
        'version': DataExplorerConfig.APP_VERSION,
        'timestamp': datetime.now().isoformat()
    })


# Add route to serve static files with cache-busting
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files with cache-busting headers."""
    from flask import send_from_directory
    response = send_from_directory(app.static_folder, filename)
    # Add cache-busting headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/lender/peers', methods=['POST'])
def api_lender_peers():
    """Identify automatic peers for a subject lender across all data types."""
    try:
        data = request.get_json()
        subject_lender_id = data.get('subject_lender_id')
        data_type = data.get('data_type', 'hmda')  # 'hmda', 'sb', or 'branches'
        geoids = data.get('geoids', [])
        years = data.get('years', [])
        
        if not subject_lender_id or not geoids:
            error_response = jsonify({'success': False, 'error': 'Subject lender ID and geography are required'})
            return add_cache_busting_headers(error_response), 400
        
        # Expand geoids
        geoids = expand_geoids(geoids)
        years = [int(y) for y in years] if years else []
        
        peers = []
        
        if data_type == 'hmda':
            # Query to identify peers based on volume (50%-200% of subject)
            from apps.dataexplorer.query_builders import build_lender_hmda_peer_query
            # First get subject volume
            subject_query = build_lender_hmda_subject_query(
                subject_lei=subject_lender_id,
                geoids=geoids,
                years=years,
                loan_purpose=data.get('loan_purpose'),
                action_taken=data.get('action_taken', ['1', '2', '3', '4', '5']),
                occupancy_type=data.get('occupancy_type', ['1']),
                total_units=data.get('total_units', ['1', '2', '3', '4']),
                construction_method=data.get('construction_method', ['1']),
                exclude_reverse_mortgages=data.get('exclude_reverse_mortgages', True)
            )
            # TODO: Execute query and identify peers
            # For now, return empty list
        elif data_type == 'sb':
            # Similar logic for SB
            pass
        elif data_type == 'branches':
            # Similar logic for branches
            pass
        
        response = jsonify({'success': True, 'peers': peers})
        return add_cache_busting_headers(response)
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"API /api/lender/peers error: {error_msg}", flush=True)
        error_response = jsonify({'success': False, 'error': error_msg})
        return add_cache_busting_headers(error_response), 500


@app.route('/api/lender/analysis', methods=['POST'])
def api_lender_analysis():
    """Main lender analysis endpoint - queries all three data types and returns combined results."""
    try:
        data = request.get_json()
        subject_lender_id = data.get('subject_lender_id')
        data_type = data.get('data_type', 'hmda')  # Primary data type
        geoids = data.get('geoids', [])
        years = data.get('years', [])
        enable_peer_comparison = data.get('enable_peer_comparison', True)
        custom_peers = data.get('custom_peers', [])  # List of custom peer IDs
        
        # HMDA filters
        loan_purpose = data.get('loan_purpose', [])
        action_taken = data.get('action_taken', ['1', '2', '3', '4', '5'])
        occupancy_type = data.get('occupancy_type', ['1'])
        total_units = data.get('total_units', ['1', '2', '3', '4'])
        construction_method = data.get('construction_method', ['1'])
        exclude_reverse_mortgages = data.get('exclude_reverse_mortgages', True)
        
        if not subject_lender_id or not geoids:
            error_response = jsonify({'success': False, 'error': 'Subject lender ID and geography are required'})
            return add_cache_busting_headers(error_response), 400
        
        # Expand geoids
        geoids = expand_geoids(geoids)
        years = [int(y) for y in years] if years else []
        
        # Default years if not provided
        if not years:
            if data_type == 'hmda':
                years = DataExplorerConfig.HMDA_YEARS
            elif data_type == 'sb':
                years = DataExplorerConfig.SB_YEARS
            else:
                years = DataExplorerConfig.BRANCH_YEARS
        
        results = {
            'hmda': {'subject': [], 'peer': []},
            'sb': {'subject': [], 'peer': []},
            'branches': {'subject': [], 'peer': []}
        }
        
        # Query HMDA data if subject has LEI
        if data_type == 'hmda' or (data.get('include_all_data_types', False)):
            try:
                from apps.dataexplorer.query_builders import (
                    build_lender_hmda_subject_query, build_lender_hmda_peer_query
                )
                
                # Subject HMDA query
                hmda_subject_query = build_lender_hmda_subject_query(
                    subject_lei=subject_lender_id,
                    geoids=geoids,
                    years=years,
                    loan_purpose=loan_purpose,
                    action_taken=action_taken,
                    occupancy_type=occupancy_type,
                    total_units=total_units,
                    construction_method=construction_method,
                    exclude_reverse_mortgages=exclude_reverse_mortgages
                )
                hmda_subject_results = execute_query(hmda_subject_query)
                if hmda_subject_results:
                    results['hmda']['subject'] = [dict(row) for row in hmda_subject_results]
                
                # Peer HMDA query
                if enable_peer_comparison:
                    custom_peer_leis = [p.get('lei') for p in custom_peers if p.get('data_type') == 'hmda'] if custom_peers else None
                    hmda_peer_query = build_lender_hmda_peer_query(
                        subject_lei=subject_lender_id,
                        geoids=geoids,
                        years=years,
                        loan_purpose=loan_purpose,
                        action_taken=action_taken,
                        occupancy_type=occupancy_type,
                        total_units=total_units,
                        construction_method=construction_method,
                        exclude_reverse_mortgages=exclude_reverse_mortgages,
                        custom_peer_leis=custom_peer_leis
                    )
                    hmda_peer_results = execute_query(hmda_peer_query)
                    if hmda_peer_results:
                        results['hmda']['peer'] = [dict(row) for row in hmda_peer_results]
            except Exception as e:
                print(f"Error querying HMDA data: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        # Query Small Business data if subject has SB Respondent ID
        if data_type == 'sb' or (data.get('include_all_data_types', False)):
            try:
                from apps.dataexplorer.query_builders import (
                    build_lender_sb_subject_query, build_lender_sb_peer_query
                )
                
                # Subject SB query
                sb_subject_query = build_lender_sb_subject_query(
                    subject_respondent_id=subject_lender_id,
                    geoids=geoids,
                    years=years
                )
                sb_subject_results = execute_query(sb_subject_query)
                if sb_subject_results:
                    results['sb']['subject'] = [dict(row) for row in sb_subject_results]
                
                # Peer SB query
                if enable_peer_comparison:
                    custom_peer_ids = [p.get('respondent_id') for p in custom_peers if p.get('data_type') == 'sb'] if custom_peers else None
                    sb_peer_query = build_lender_sb_peer_query(
                        subject_respondent_id=subject_lender_id,
                        geoids=geoids,
                        years=years,
                        custom_peer_ids=custom_peer_ids
                    )
                    sb_peer_results = execute_query(sb_peer_query)
                    if sb_peer_results:
                        results['sb']['peer'] = [dict(row) for row in sb_peer_results]
            except Exception as e:
                print(f"Error querying Small Business data: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        # Query Branch data if subject has RSSD
        if data_type == 'branches' or (data.get('include_all_data_types', False)):
            try:
                from apps.dataexplorer.query_builders import (
                    build_lender_branch_subject_query, build_lender_branch_peer_query
                )
                
                # Use latest year for branches (2025)
                branch_year = max(years) if years else 2025
                
                # Subject Branch query
                branch_subject_query = build_lender_branch_subject_query(
                    subject_rssd=subject_lender_id,
                    geoids=geoids,
                    year=branch_year
                )
                branch_subject_results = execute_query(branch_subject_query)
                if branch_subject_results:
                    results['branches']['subject'] = [dict(row) for row in branch_subject_results]
                
                # Peer Branch query
                if enable_peer_comparison:
                    custom_peer_rssds = [p.get('rssd') for p in custom_peers if p.get('data_type') == 'branches'] if custom_peers else None
                    branch_peer_query = build_lender_branch_peer_query(
                        subject_rssd=subject_lender_id,
                        geoids=geoids,
                        year=branch_year,
                        custom_peer_rssds=custom_peer_rssds
                    )
                    branch_peer_results = execute_query(branch_peer_query)
                    if branch_peer_results:
                        results['branches']['peer'] = [dict(row) for row in branch_peer_results]
            except Exception as e:
                print(f"Error querying Branch data: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        # Process results using lender analysis processor
        from apps.dataexplorer.lender_analysis_processor import process_lender_analysis
        
        processed_results = process_lender_analysis(
            results=results,
            years=years,
            geoids=geoids,
            subject_lender_id=subject_lender_id,
            data_type=data_type
        )
        
        response = jsonify({
            'success': True,
            'data': processed_results,
            'raw_results': results  # Include raw results for debugging
        })
        return add_cache_busting_headers(response)
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"API /api/lender/analysis error: {error_msg}", flush=True)
        error_response = jsonify({'success': False, 'error': error_msg})
        return add_cache_busting_headers(error_response), 500


@app.route('/api/lender/export-excel', methods=['POST'])
def api_lender_export_excel():
    """
    Export lender analysis to Excel file (MergerMeter-style format with CBSA/county breakdown).
    """
    try:
        from flask import send_file
        import tempfile
        from pathlib import Path
        from datetime import datetime
        from apps.dataexplorer.lender_excel_generator import create_lender_analysis_excel
        
        data = request.get_json()
        subject_lender_id = data.get('subjectLenderId')
        subject_lender_name = data.get('subjectLenderName', 'Subject Lender')
        geoids = data.get('geoids', [])
        years = data.get('years', [2020, 2021, 2022, 2023, 2024])
        data_type = data.get('dataType', 'hmda')
        enable_peer_comparison = data.get('enablePeerComparison', True)
        custom_peers = data.get('customPeers', [])
        assessment_areas = data.get('assessmentAreas', {})
        
        # Get raw results (same logic as api_lender_analysis)
        results = {
            'hmda': {'subject': [], 'peer': []},
            'sb': {'subject': [], 'peer': []},
            'branches': {'subject': [], 'peer': []}
        }
        
        # Query HMDA data
        if data_type == 'hmda' or data.get('includeAllDataTypes', False):
            try:
                from apps.dataexplorer.query_builders import (
                    build_lender_hmda_subject_query, build_lender_hmda_peer_query
                )
                
                # Subject HMDA query
                hmda_subject_query = build_lender_hmda_subject_query(
                    subject_lei=subject_lender_id,
                    geoids=geoids,
                    years=years
                )
                hmda_subject_results = execute_query(hmda_subject_query)
                if hmda_subject_results:
                    results['hmda']['subject'] = [dict(row) for row in hmda_subject_results]
                
                # Peer HMDA query
                if enable_peer_comparison:
                    custom_peer_leis = [p.get('lei') for p in custom_peers if p.get('data_type') == 'hmda'] if custom_peers else None
                    hmda_peer_query = build_lender_hmda_peer_query(
                        subject_lei=subject_lender_id,
                        geoids=geoids,
                        years=years,
                        custom_peer_leis=custom_peer_leis
                    )
                    hmda_peer_results = execute_query(hmda_peer_query)
                    if hmda_peer_results:
                        results['hmda']['peer'] = [dict(row) for row in hmda_peer_results]
            except Exception as e:
                print(f"Error querying HMDA data: {e}", flush=True)
        
        # Query Small Business data
        if data_type == 'sb' or data.get('includeAllDataTypes', False):
            try:
                from apps.dataexplorer.query_builders import (
                    build_lender_sb_subject_query, build_lender_sb_peer_query
                )
                
                # Subject SB query
                sb_subject_query = build_lender_sb_subject_query(
                    subject_respondent_id=subject_lender_id,
                    geoids=geoids,
                    years=years
                )
                sb_subject_results = execute_query(sb_subject_query)
                if sb_subject_results:
                    results['sb']['subject'] = [dict(row) for row in sb_subject_results]
                
                # Peer SB query
                if enable_peer_comparison:
                    custom_peer_ids = [p.get('respondent_id') for p in custom_peers if p.get('data_type') == 'sb'] if custom_peers else None
                    sb_peer_query = build_lender_sb_peer_query(
                        subject_respondent_id=subject_lender_id,
                        geoids=geoids,
                        years=years,
                        custom_peer_ids=custom_peer_ids
                    )
                    sb_peer_results = execute_query(sb_peer_query)
                    if sb_peer_results:
                        results['sb']['peer'] = [dict(row) for row in sb_peer_results]
            except Exception as e:
                print(f"Error querying Small Business data: {e}", flush=True)
        
        # Query Branch data
        if data_type == 'branches' or data.get('includeAllDataTypes', False):
            try:
                from apps.dataexplorer.query_builders import (
                    build_lender_branch_subject_query, build_lender_branch_peer_query
                )
                
                # Use latest year for branches (2025)
                branch_year = max(years) if years else 2025
                
                # Subject Branch query
                branch_subject_query = build_lender_branch_subject_query(
                    subject_rssd=subject_lender_id,
                    geoids=geoids,
                    year=branch_year
                )
                branch_subject_results = execute_query(branch_subject_query)
                if branch_subject_results:
                    results['branches']['subject'] = [dict(row) for row in branch_subject_results]
                
                # Peer Branch query
                if enable_peer_comparison:
                    custom_peer_rssds = [p.get('rssd') for p in custom_peers if p.get('data_type') == 'branches'] if custom_peers else None
                    branch_peer_query = build_lender_branch_peer_query(
                        subject_rssd=subject_lender_id,
                        geoids=geoids,
                        year=branch_year,
                        custom_peer_rssds=custom_peer_rssds
                    )
                    branch_peer_results = execute_query(branch_peer_query)
                    if branch_peer_results:
                        results['branches']['peer'] = [dict(row) for row in branch_peer_results]
            except Exception as e:
                print(f"Error querying Branch data: {e}", flush=True)
        
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_path = Path(tmp_file.name)
            
            # Prepare metadata
            metadata = {
                'hmda_years': years if (data_type == 'hmda' or data.get('includeAllDataTypes', False)) else [],
                'sb_years': years if (data_type == 'sb' or data.get('includeAllDataTypes', False)) else [],
                'filters': data.get('filters', {})
            }
            
            # Generate Excel file
            create_lender_analysis_excel(
                output_path=tmp_path,
                subject_lender_name=subject_lender_name,
                raw_results=results,
                assessment_areas=assessment_areas,
                metadata=metadata
            )
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_lender_name = subject_lender_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            filename = f'{safe_lender_name}_Lender_Analysis_{timestamp}.xlsx'
            
            # Send file as download
            return send_file(
                str(tmp_path),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"API /api/lender/export-excel error: {error_msg}", flush=True)
        error_response = jsonify({'success': False, 'error': error_msg})
        return add_cache_busting_headers(error_response), 500


@app.route('/api/test/census', methods=['GET'])
def test_census_api():
    """
    Test endpoint to verify Census API is working.
    Tests demographic and income data for a sample county (Harris County, TX - 48201).
    """
    try:
        import os
        from apps.dataexplorer.acs_utils import get_acs_data_for_geoids, get_household_income_distribution_for_geoids
        
        # Check if API key is set
        api_key = os.getenv('CENSUS_API_KEY')
        api_key_status = {
            'present': api_key is not None,
            'length': len(api_key) if api_key else 0,
            'first_10_chars': api_key[:10] + '...' if api_key and len(api_key) > 10 else 'N/A'
        }
        
        # Test with a sample county (Harris County, TX - GEOID 48201)
        test_geoid = '48201'
        
        # Test demographic data
        demo_result = get_acs_data_for_geoids([test_geoid])
        
        # Test household income data
        income_result = get_household_income_distribution_for_geoids([test_geoid])
        
        return jsonify({
            'success': True,
            'api_key_status': api_key_status,
            'test_geoid': test_geoid,
            'demographic_data': demo_result,
            'household_income_data': income_result,
            'message': 'Census API test completed. Check the data fields to verify results.'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

if __name__ == '__main__':
    port = DataExplorerConfig.PORT
    # Use use_reloader=True to ensure code changes are picked up
    app.run(host='127.0.0.1', port=port, debug=True, use_reloader=True, use_debugger=True)

