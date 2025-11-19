#!/usr/bin/env python3
"""
BranchMapper Flask web application - Interactive map of bank branch locations.
"""

from flask import render_template, request, jsonify, Response
import os

from justdata.shared.web.app_factory import create_app
from .config import TEMPLATES_DIR, STATIC_DIR
from .version import __version__

# Import utilities from branchseeker (shared functionality)
from justdata.apps.branchseeker.data_utils import (
    get_available_counties
)
from justdata.apps.branchseeker.core import load_sql_template
from justdata.apps.branchseeker.data_utils import execute_branch_query

# Create the Flask app
app = create_app(
    'branchmapper',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)


@app.route('/')
def index():
    """Main page with the interactive map"""
    return render_template('branch_mapper_template.html', version=__version__)


# Health check endpoint is automatically registered by app_factory


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
        # Return empty list - BigQuery should always be available
        return jsonify([])


@app.route('/states')
def states():
    """Return a list of all available states"""
    try:
        from justdata.apps.branchseeker.data_utils import get_available_states
        states_list = get_available_states()
        return jsonify(states_list)
    except Exception as e:
        print(f"Error in states endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@app.route('/metro-areas')
def metro_areas():
    """Return a list of all available metro areas (CBSAs)"""
    try:
        from justdata.apps.branchseeker.data_utils import get_available_metro_areas
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
    """Return a list of counties for a specific state"""
    try:
        from justdata.apps.branchseeker.data_utils import expand_state_to_counties
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
        from justdata.apps.branchseeker.census_tract_utils import (
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
                
                for tract in tract_income_data:
                    geoid = tract['tract_geoid']
                    geoid_normalized = str(geoid).zfill(11)
                    income_lookup[geoid_normalized] = tract
                    income_lookup[geoid] = tract
                print(f"Created income lookup with {len(income_lookup)} entries")
        
        # Get minority data if requested
        county_minority_pct = None
        if include_minority:
            api_key = get_census_api_key()
            if not api_key:
                print(f"WARNING: CENSUS_API_KEY not set. Cannot fetch minority data.")
                return jsonify({
                    'success': False,
                    'error': 'CENSUS_API_KEY environment variable is not set. Please configure it to use minority layers.'
                }), 500
            
            print(f"Attempting to fetch county minority percentage for state FIPS: {state_fips}, county FIPS: {county_fips}")
            county_minority_pct = get_county_minority_percentage(state_fips, county_fips)
            if county_minority_pct is not None:
                print(f"[OK] Using county minority percentage: {county_minority_pct:.1f}% for {county}")
            else:
                print(f"[ERROR] Failed to fetch county minority percentage for {county}")
            
            print(f"Fetching tract-level minority data for state FIPS: {state_fips}, county FIPS: {county_fips}")
            tract_minority_data = get_tract_minority_data(state_fips, county_fips)
            print(f"Fetched {len(tract_minority_data)} tracts with minority data")
            
            for tract in tract_minority_data:
                geoid = tract['tract_geoid']
                geoid_normalized = str(geoid).zfill(11)
                minority_lookup[geoid_normalized] = tract
                minority_lookup[geoid] = tract
            print(f"Created minority lookup with {len(minority_lookup)} entries")
        
        # Merge data with boundaries
        valid_features = []
        matched_count = 0
        filtered_count = 0
        
        for i, feature in enumerate(tract_boundaries['features']):
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
                        if geoid:
                            print(f"Filtering out tract {geoid}: Invalid income data: {median_income}")
                        filtered_count += 1
                        continue
                else:
                    if geoid:
                        print(f"Filtering out tract {geoid}: No income data found")
                    filtered_count += 1
                    continue
            
            # Add minority data
            if include_minority:
                tract_data = minority_lookup.get(geoid_normalized) or minority_lookup.get(geoid_str) or minority_lookup.get(geoid)
                
                if tract_data:
                    minority_pct = tract_data.get('minority_percentage')
                    total_pop = tract_data.get('total_population')
                    minority_pop = tract_data.get('minority_population')
                    
                    if minority_pct is not None and minority_pct >= 0 and minority_pct <= 100 and total_pop is not None and total_pop > 0:
                        minority_category, minority_ratio = categorize_minority_level(minority_pct, county_minority_pct) if county_minority_pct else ('Unknown', None)
                        
                        feature['properties']['minority_percentage'] = minority_pct
                        feature['properties']['minority_category'] = minority_category
                        feature['properties']['county_minority_percentage'] = county_minority_pct
                        feature['properties']['minority_ratio'] = minority_ratio
                        feature['properties']['total_population'] = total_pop
                        feature['properties']['minority_population'] = minority_pop
                    else:
                        if not include_income:
                            filtered_count += 1
                            continue
                        feature['properties']['minority_percentage'] = None
                        feature['properties']['minority_category'] = 'Unknown'
                        feature['properties']['county_minority_percentage'] = county_minority_pct
                        feature['properties']['minority_ratio'] = None
                        feature['properties']['total_population'] = None
                        feature['properties']['minority_population'] = None
                else:
                    if not include_income:
                        filtered_count += 1
                        continue
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
        sql_template = load_sql_template()
        branches = execute_branch_query(sql_template, county, year)
        
        # Convert to JSON-serializable format
        import numpy as np
        import re
        result = []
        for branch in branches:
            branch_dict = {}
            for key, value in branch.items():
                # Handle numpy types and NaN values
                if hasattr(value, 'item'):
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
                
                # Remove "THE" from the beginning
                bank_name = re.sub(r'^THE\s+', '', bank_name, flags=re.IGNORECASE).strip()
                bank_name = re.sub(r'^The\s+', '', bank_name, flags=re.IGNORECASE).strip()
                
                # Remove common suffixes
                patterns = [
                    r',?\s*NATIONAL\s+ASSOCIATION\s*$',
                    r',?\s*N\.?\s*A\.?\s*$',
                    r',?\s*NA\s*$',
                    r',?\s*FEDERAL\s+SAVINGS\s+BANK\s*$',
                    r',?\s*FSB\s*$',
                    r',?\s*FEDERAL\s+CREDIT\s+UNION\s*$',
                    r',?\s*FCU\s*$',
                    r',?\s*STATE\s+BANK\s*$',
                    r',?\s*SAVINGS\s+BANK\s*$',
                    r',?\s*SAVINGS\s+AND\s+LOAN\s*$',
                    r',?\s*S&L\s*$',
                    r',?\s*INC\.?\s*$',
                    r',?\s*LLC\.?\s*$',
                    r',?\s*CORPORATION\s*$',
                    r',?\s*CORP\.?\s*$',
                ]
                
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
                
                bank_name = re.sub(r'[,.\s]+$', '', bank_name).strip()
                branch_dict['bank_name'] = bank_name
            
            # Map service_type to branch_type
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


# Add favicon routes to prevent 404 errors
@app.route('/favicon.ico')
@app.route('/assets/favicon.ico')
def favicon():
    """Serve favicon or return 204 No Content"""
    return '', 204


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8084))
    app.run(debug=True, host='0.0.0.0', port=port)

