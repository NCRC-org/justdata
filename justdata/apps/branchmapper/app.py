#!/usr/bin/env python3
"""
BranchMapper Flask web application - Interactive map of bank branch locations.
"""

from flask import render_template, request, jsonify
import os
import sys
import re
import numpy as np
from pathlib import Path
from werkzeug.middleware.proxy_fix import ProxyFix

# Add repo root to path for shared modules
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from justdata.shared.web.app_factory import create_app

# Use absolute imports from repo root (like bizsight)
from justdata.apps.branchmapper.config import TEMPLATES_DIR, STATIC_DIR
from justdata.apps.branchmapper.data_utils import (
    get_available_counties, 
    get_available_states, 
    get_available_metro_areas,
    execute_branch_query
)
from justdata.apps.branchmapper.core import load_sql_template
from justdata.apps.branchmapper.census_tract_utils import (
    extract_fips_from_county_state,
    get_county_median_family_income,
    get_county_minority_percentage,
    get_tract_income_data,
    get_tract_minority_data,
    get_tract_boundaries_geojson,
    categorize_income_level,
    categorize_minority_level,
    get_census_api_key
)
from justdata.apps.branchmapper.version import __version__


# Create the Flask app
app = create_app(
    'branchmapper',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

# Add ProxyFix for proper request handling behind Render's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Health check endpoint is already added by create_app() in shared/web/app_factory.py


@app.route('/')
def index():
    """Main page with the interactive branch map"""
    return render_template('branch_mapper_template.html', version=__version__)


@app.route('/counties')
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
        from data_utils import get_fallback_counties
        return jsonify(get_fallback_counties())


@app.route('/states')
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
        from data_utils import get_fallback_states
        states_list = get_fallback_states()
        print(f"Using fallback: Returning {len(states_list)} states")
        return jsonify(states_list)


@app.route('/metro-areas')
def metro_areas():
    """Return a list of all available metro areas (CBSAs)"""
    try:
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


@app.route('/counties-by-state/<state_code>')
def counties_by_state(state_code):
    """Get list of counties for a specific state"""
    try:
        # URL decode the state code
        from urllib.parse import unquote
        state_code = unquote(state_code)
        
        # Try to query BigQuery directly for counties in this state
        try:
            from justdata.shared.utils.bigquery_client import get_bigquery_client, escape_sql_string
            from justdata.apps.branchmapper.config import PROJECT_ID
            client = get_bigquery_client(PROJECT_ID)
            # Escape state code for SQL safety
            state_code_escaped = escape_sql_string(state_code)
            query = f"""
            SELECT DISTINCT county_state 
            FROM geo.cbsa_to_county 
            WHERE LOWER(SPLIT(county_state, ',')[SAFE_OFFSET(1)]) = LOWER('{state_code_escaped}')
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
            if ',' in county:
                county_name, state_name = county.split(',', 1)
                state_name = state_name.strip()
                # Match by state name (case-insensitive)
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


@app.route('/api/census-tracts/<path:county>')
def api_census_tracts(county):
    """Return census tract boundaries with income and/or minority data for a county"""
    try:
        # URL decode the county name (handles apostrophes and special characters)
        from urllib.parse import unquote
        county = unquote(county)
        
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
        baseline_income = None
        if include_income:
            api_key = get_census_api_key()
            if not api_key:
                print(f"WARNING: CENSUS_API_KEY not set. Cannot fetch income data.")
                return jsonify({
                    'success': False,
                    'error': 'CENSUS_API_KEY environment variable is not set. Please configure it to use income layers.'
                }), 500
            
            baseline_income = get_county_median_family_income(state_fips, county_fips)
            if baseline_income:
                print(f"[OK] Using county median income: ${baseline_income:,.0f} for {county}")
            else:
                print(f"[ERROR] Failed to fetch county median income for {county}")
            
            if baseline_income:
                tract_income_data = get_tract_income_data(state_fips, county_fips)
                print(f"Fetched {len(tract_income_data)} tracts with income data")
                
                for tract in tract_income_data:
                    geoid = tract['tract_geoid']
                    geoid_normalized = str(geoid).zfill(11)
                    income_lookup[geoid_normalized] = tract
                    income_lookup[geoid] = tract
                print(f"Created income lookup with {len(income_lookup)} entries")
        
        # Get minority data if requested
        county_minority_pct = None
        minority_quartiles = None  # Will store Q1, Q2 (median), Q3 quartile values
        if include_minority:
            api_key = get_census_api_key()
            if not api_key:
                print(f"WARNING: CENSUS_API_KEY not set. Cannot fetch minority data.")
                return jsonify({
                    'success': False,
                    'error': 'CENSUS_API_KEY environment variable is not set. Please configure it to use minority layers.'
                }), 500
            
            county_minority_pct = get_county_minority_percentage(state_fips, county_fips)
            if county_minority_pct is not None:
                print(f"[OK] Using county minority percentage: {county_minority_pct:.1f}% for {county}")
            else:
                print(f"[ERROR] Failed to fetch county minority percentage for {county}")
            
            tract_minority_data = get_tract_minority_data(state_fips, county_fips)
            print(f"Fetched {len(tract_minority_data)} tracts with minority data")
            
            for tract in tract_minority_data:
                geoid = tract['tract_geoid']
                geoid_normalized = str(geoid).zfill(11)
                minority_lookup[geoid_normalized] = tract
                minority_lookup[geoid] = tract
            print(f"Created minority lookup with {len(minority_lookup)} entries")
            
            # Calculate quartiles for minority percentage
            minority_percentages = []
            for tract in tract_minority_data:
                minority_pct = tract.get('minority_percentage')
                if minority_pct is not None and minority_pct >= 0 and minority_pct <= 100:
                    minority_percentages.append(minority_pct)
            
            if minority_percentages:
                # Use numpy for accurate quartile calculation
                try:
                    q1 = np.percentile(minority_percentages, 25)
                    q2 = np.percentile(minority_percentages, 50)  # Median
                    q3 = np.percentile(minority_percentages, 75)
                    minority_quartiles = {'q1': float(q1), 'q2': float(q2), 'q3': float(q3)}
                    print(f"[OK] Calculated minority quartiles: Q1={q1:.1f}%, Q2={q2:.1f}%, Q3={q3:.1f}% (n={len(minority_percentages)} tracts)")
                except Exception as e:
                    # Fallback to manual calculation if numpy fails
                    print(f"[WARNING] Error using numpy for quartiles: {e}, using manual calculation")
                    minority_percentages.sort()
                    n = len(minority_percentages)
                    q1_idx = int(n * 0.25)
                    q2_idx = int(n * 0.50)
                    q3_idx = int(n * 0.75)
                    q1 = minority_percentages[q1_idx] if q1_idx < n else minority_percentages[-1]
                    q2 = minority_percentages[q2_idx] if q2_idx < n else minority_percentages[-1]
                    q3 = minority_percentages[q3_idx] if q3_idx < n else minority_percentages[-1]
                    minority_quartiles = {'q1': q1, 'q2': q2, 'q3': q3}
                    print(f"[OK] Calculated minority quartiles (manual): Q1={q1:.1f}%, Q2={q2:.1f}%, Q3={q3:.1f}% (n={n} tracts)")
            else:
                print(f"[WARNING] No valid minority percentages found to calculate quartiles")
        
        # Merge data with boundaries
        valid_features = []
        matched_count = 0
        filtered_count = 0
        
        for feature in tract_boundaries['features']:
            geoid = feature['properties'].get('GEOID')
            
            if geoid:
                geoid_str = str(geoid).strip()
                geoid_normalized = geoid_str.zfill(11)
            else:
                geoid_str = None
                geoid_normalized = None
            
            # Add income data
            if include_income:
                tract_data = income_lookup.get(geoid_normalized) or income_lookup.get(geoid_str) or income_lookup.get(geoid)
                
                if tract_data:
                    median_income = tract_data.get('median_family_income')
                    
                    if median_income is not None and median_income > 0:
                        income_category = categorize_income_level(median_income, baseline_income) if baseline_income else 'Unknown'
                        
                        feature['properties']['median_family_income'] = median_income
                        feature['properties']['income_category'] = income_category
                        feature['properties']['baseline_median_income'] = baseline_income
                        feature['properties']['baseline_type'] = 'county'
                        feature['properties']['income_ratio'] = (median_income / baseline_income) if median_income and baseline_income and baseline_income > 0 else None
                        matched_count += 1
                    else:
                        # Invalid income data - still include tract with Unknown category
                        if geoid:
                            print(f"Tract {geoid}: Invalid income data: {median_income}, marking as Unknown")
                        feature['properties']['median_family_income'] = None
                        feature['properties']['income_category'] = 'Unknown'
                        feature['properties']['baseline_median_income'] = baseline_income
                        feature['properties']['baseline_type'] = 'county'
                        feature['properties']['income_ratio'] = None
                else:
                    # No income data found - still include tract with Unknown category
                    if geoid:
                        print(f"Tract {geoid}: No income data found, marking as Unknown")
                    feature['properties']['median_family_income'] = None
                    feature['properties']['income_category'] = 'Unknown'
                    feature['properties']['baseline_median_income'] = baseline_income
                    feature['properties']['baseline_type'] = 'county'
                    feature['properties']['income_ratio'] = None
            
            # Add minority data
            if include_minority:
                tract_data = minority_lookup.get(geoid_normalized) or minority_lookup.get(geoid_str) or minority_lookup.get(geoid)
                
                if tract_data:
                    minority_pct = tract_data.get('minority_percentage')
                    total_pop = tract_data.get('total_population')
                    minority_pop = tract_data.get('minority_population')
                    
                    if minority_pct is not None and minority_pct >= 0 and minority_pct <= 100 and total_pop is not None and total_pop > 0:
                        # Categorize by quartile instead of ratio
                        if minority_quartiles:
                            if minority_pct < minority_quartiles['q1']:
                                minority_category = 'Q1 (Lowest 25%)'
                            elif minority_pct < minority_quartiles['q2']:
                                minority_category = 'Q2 (25-50%)'
                            elif minority_pct < minority_quartiles['q3']:
                                minority_category = 'Q3 (50-75%)'
                            else:
                                minority_category = 'Q4 (Highest 25%)'
                            minority_ratio = None  # Not using ratio for quartile-based categorization
                        else:
                            # Fallback to old method if quartiles not available
                            minority_category, minority_ratio = categorize_minority_level(minority_pct, county_minority_pct) if county_minority_pct else ('Unknown', None)
                        
                        feature['properties']['minority_percentage'] = minority_pct
                        feature['properties']['minority_category'] = minority_category
                        feature['properties']['county_minority_percentage'] = county_minority_pct
                        feature['properties']['minority_ratio'] = minority_ratio
                        feature['properties']['total_population'] = total_pop
                        feature['properties']['minority_population'] = minority_pop
                    else:
                        # Invalid minority data - still include tract with Unknown category
                        if geoid:
                            print(f"Tract {geoid}: Invalid minority data (pct: {minority_pct}, pop: {total_pop}), marking as Unknown")
                        feature['properties']['minority_percentage'] = None
                        feature['properties']['minority_category'] = 'Unknown'
                        feature['properties']['county_minority_percentage'] = county_minority_pct
                        feature['properties']['minority_ratio'] = None
                        feature['properties']['total_population'] = None
                        feature['properties']['minority_population'] = None
                else:
                    # No minority data found - still include tract with Unknown category
                    if geoid:
                        print(f"Tract {geoid}: No minority data found, marking as Unknown")
                    feature['properties']['minority_percentage'] = None
                    feature['properties']['minority_category'] = 'Unknown'
                    feature['properties']['county_minority_percentage'] = county_minority_pct
                    feature['properties']['minority_ratio'] = None
                    feature['properties']['total_population'] = None
                    feature['properties']['minority_population'] = None
            
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
        
        result = {
            'success': True,
            'county': county,
            'tract_count': len(tract_boundaries['features']),
            'geojson': tract_boundaries
        }
        
        if include_income:
            result['baseline_median_family_income'] = baseline_income
            result['baseline_type'] = 'county'
        
        if include_minority:
            result['county_minority_percentage'] = county_minority_pct
        
        return jsonify(result)
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in api_census_tracts endpoint for county '{county}': {error_msg}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': error_msg,
            'county': county,
            'message': f'Failed to load census tract data for {county}: {error_msg}'
        }), 500


@app.route('/api/branches')
def api_branches():
    """Return branch data with coordinates for map display"""
    try:
        county = request.args.get('county', '').strip()
        year_str = request.args.get('year', '').strip()
        
        if not county or not year_str:
            return jsonify({'error': 'County and year parameters are required'}), 400
        
        # URL decode the county name (handles apostrophes and special characters)
        from urllib.parse import unquote
        county = unquote(county)
        
        try:
            year = int(year_str)
        except ValueError:
            return jsonify({'error': 'Year must be a valid integer'}), 400
        
        # Load SQL template and execute query
        sql_template = load_sql_template()
        branches = execute_branch_query(sql_template, county, year)
        
        # Convert to JSON-serializable format
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
            
            # Clean bank name - remove common suffixes and everything after comma
            if 'bank_name' in branch_dict and branch_dict['bank_name']:
                original_bank_name = str(branch_dict['bank_name']).strip()
                bank_name = original_bank_name
                
                # Remove everything after the first comma (including the comma)
                bank_name = bank_name.split(',')[0].strip()
                
                # Remove "THE" from the beginning
                bank_name = re.sub(r'^THE\s+', '', bank_name, flags=re.IGNORECASE).strip()
                bank_name = re.sub(r'^The\s+', '', bank_name, flags=re.IGNORECASE).strip()
                
                # Remove common suffixes at the end
                patterns = [
                    r'\s+NATIONAL\s+ASSOCIATION\s*$',
                    r'\s+National\s+Association\s*$',
                    r'\s+N\.?\s*A\.?\s*$',
                    r'\s+NA\s*$',
                    r'\s+FEDERAL\s+SAVINGS\s+BANK\s*$',
                    r'\s+Federal\s+Savings\s+Bank\s*$',
                    r'\s+FSB\s*$',
                    r'\s+FEDERAL\s+CREDIT\s+UNION\s*$',
                    r'\s+Federal\s+Credit\s+Union\s*$',
                    r'\s+FCU\s*$',
                    r'\s+STATE\s+BANK\s*$',
                    r'\s+State\s+Bank\s*$',
                    r'\s+SAVINGS\s+BANK\s*$',
                    r'\s+Savings\s+Bank\s*$',
                    r'\s+SAVINGS\s+AND\s+LOAN\s*$',
                    r'\s+Savings\s+and\s+Loan\s*$',
                    r'\s+S&L\s*$',
                    r'\s+INC\.?\s*$',
                    r'\s+LLC\.?\s*$',
                    r'\s+CORPORATION\s*$',
                    r'\s+Corporation\s*$',
                    r'\s+CORP\.?\s*$',
                    r'\s+Corp\.?\s*$',
                    r'\s+THE\s*$',
                    r'\s+The\s*$',
                ]
                
                # Apply patterns repeatedly until no more matches
                changed = True
                iterations = 0
                max_iterations = 10
                
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
                
                branch_dict['bank_name'] = bank_name
            
            # Map service_type to branch_type for popup compatibility
            if 'service_type' in branch_dict and branch_dict['service_type']:
                service_type = branch_dict['service_type']
                service_type_str = str(service_type).strip()
                
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
                    'Full Service': 'Full Service Branch',
                    'Limited Service': 'Limited Service Branch',
                    'Loan Production': 'Loan Production Office',
                    'Consumer Credit': 'Consumer Credit Office',
                    'Other': 'Other Office',
                    'ATM': 'Automated Teller Machine',
                    'Mobile': 'Mobile Branch'
                }
                
                if service_type_str in service_type_map:
                    branch_dict['branch_type'] = service_type_map[service_type_str]
                elif service_type_str.isdigit():
                    branch_dict['branch_type'] = f'Service Type {service_type_str}'
                else:
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

