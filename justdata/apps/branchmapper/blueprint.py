"""
BranchMapper Blueprint for main JustData app.
Converts the standalone BranchMapper app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, url_for
from jinja2 import ChoiceLoader, FileSystemLoader
import os
import numpy as np
import re
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, login_required
from .config import TEMPLATES_DIR, STATIC_DIR
from .version import __version__

# Import utilities from branchmapper's own modules
from .data_utils import (
    get_available_counties, get_available_states, 
    get_available_metro_areas, execute_branch_query
)
from .core import load_sql_template
# Import from branchsight for shared functionality
from justdata.apps.branchsight.data_utils import expand_state_to_counties

# Get shared templates directory
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# Create blueprint
branchmapper_bp = Blueprint(
    'branchmapper',
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/branchmapper/static'
)


@branchmapper_bp.record_once
def configure_template_loader(state):
    """Configure Jinja2 to search both blueprint templates and shared templates."""
    app = state.app
    blueprint_loader = FileSystemLoader(str(TEMPLATES_DIR))
    shared_loader = FileSystemLoader(str(SHARED_TEMPLATES_DIR))
    app.jinja_loader = ChoiceLoader([
        app.jinja_loader,
        blueprint_loader,
        shared_loader
    ])


@branchmapper_bp.route('/')
@login_required
@require_access('branchmapper', 'partial')
def index():
    """Main page with the interactive map"""
    user_permissions = get_user_permissions()
    app_base_url = url_for('branchmapper.index').rstrip('/')
    breadcrumb_items = [{'name': 'BranchMapper', 'url': '/branchmapper'}]
    return render_template('branch_mapper_template.html',
                         version=__version__,
                         permissions=user_permissions,
                         app_base_url=app_base_url,
                         app_name='BranchMapper',
                         breadcrumb_items=breadcrumb_items)


@branchmapper_bp.route('/counties')
def counties():
    """Return a list of all available counties"""
    try:
        counties_list = get_available_counties()
        return jsonify(counties_list)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify([])


@branchmapper_bp.route('/states')
def states():
    """Return a list of all available states"""
    try:
        states_list = get_available_states()
        return jsonify(states_list)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify([])


@branchmapper_bp.route('/metro-areas')
def metro_areas():
    """Return a list of all available metro areas (CBSAs)"""
    try:
        metros_list = get_available_metro_areas()
        return jsonify(metros_list)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@branchmapper_bp.route('/counties-by-state/<state_code>')
def counties_by_state(state_code):
    """Return a list of counties for a specific state"""
    try:
        counties_list = expand_state_to_counties(state_code)
        return jsonify(counties_list)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'counties': []}), 500


@branchmapper_bp.route('/api/census-tracts/<county>')
def api_census_tracts(county):
    """Return census tract boundaries with income and/or minority data for a county"""
    try:
        from justdata.apps.branchsight.census_tract_utils import (
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
        
        # Get tract boundaries first
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
                return jsonify({
                    'success': False,
                    'error': 'CENSUS_API_KEY environment variable is not set.'
                }), 500
            
            baseline_income = get_county_median_family_income(state_fips, county_fips)
            if baseline_income:
                tract_income_data = get_tract_income_data(state_fips, county_fips)
                for tract in tract_income_data:
                    geoid = tract['tract_geoid']
                    geoid_normalized = str(geoid).zfill(11)
                    income_lookup[geoid_normalized] = tract
                    income_lookup[geoid] = tract
        
        # Get minority data if requested
        county_minority_pct = None
        if include_minority:
            api_key = get_census_api_key()
            if not api_key:
                return jsonify({
                    'success': False,
                    'error': 'CENSUS_API_KEY environment variable is not set.'
                }), 500
            
            county_minority_pct = get_county_minority_percentage(state_fips, county_fips)
            tract_minority_data = get_tract_minority_data(state_fips, county_fips)
            
            for tract in tract_minority_data:
                geoid = tract['tract_geoid']
                geoid_normalized = str(geoid).zfill(11)
                minority_lookup[geoid_normalized] = tract
                minority_lookup[geoid] = tract
        
        # Merge data with boundaries
        valid_features = []
        
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
                    else:
                        continue
                else:
                    continue
            
            # Add minority data
            if include_minority:
                tract_data = minority_lookup.get(geoid_normalized) or minority_lookup.get(geoid_str) or minority_lookup.get(geoid)
                
                if tract_data:
                    minority_pct = tract_data.get('minority_percentage')
                    total_pop = tract_data.get('total_population')
                    
                    if minority_pct is not None and minority_pct >= 0 and minority_pct <= 100 and total_pop is not None and total_pop > 0:
                        minority_category, minority_ratio = categorize_minority_level(minority_pct, county_minority_pct) if county_minority_pct else ('Unknown', None)
                        
                        feature['properties']['minority_percentage'] = minority_pct
                        feature['properties']['minority_category'] = minority_category
                        feature['properties']['county_minority_percentage'] = county_minority_pct
                        feature['properties']['minority_ratio'] = minority_ratio
                        feature['properties']['total_population'] = total_pop
                    else:
                        if not include_income:
                            continue
                        feature['properties']['minority_percentage'] = None
                        feature['properties']['minority_category'] = 'Unknown'
                else:
                    if not include_income:
                        continue
                    feature['properties']['minority_percentage'] = None
                    feature['properties']['minority_category'] = 'Unknown'
            
            if include_income or include_minority:
                valid_features.append(feature)
        
        # Update GeoJSON
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
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@branchmapper_bp.route('/api/branches')
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
            
            # Clean bank name
            if 'bank_name' in branch_dict and branch_dict['bank_name']:
                bank_name = str(branch_dict['bank_name']).strip()
                bank_name = re.sub(r'^THE\s+', '', bank_name, flags=re.IGNORECASE).strip()
                
                patterns = [
                    r',?\s*NATIONAL\s+ASSOCIATION\s*$',
                    r',?\s*N\.?\s*A\.?\s*$',
                    r',?\s*NA\s*$',
                    r',?\s*FEDERAL\s+SAVINGS\s+BANK\s*$',
                    r',?\s*FSB\s*$',
                ]
                
                for pattern in patterns:
                    bank_name = re.sub(pattern, '', bank_name, flags=re.IGNORECASE).strip()
                
                bank_name = re.sub(r'[,.\s]+$', '', bank_name).strip()
                branch_dict['bank_name'] = bank_name
            
            # Map service_type to branch_type
            if 'service_type' in branch_dict and branch_dict['service_type']:
                service_type = str(branch_dict['service_type']).strip()
                service_type_map = {
                    '11': 'Full Service, brick and mortar office',
                    '12': 'Full Service, retail office',
                    '13': 'Full Service, cyber office',
                }
                branch_dict['branch_type'] = service_type_map.get(service_type, f'Service Type {service_type}')
            
            result.append(branch_dict)
        
        return jsonify({
            'success': True,
            'branches': result,
            'count': len(result)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@branchmapper_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'branchmapper',
        'version': __version__
    })

