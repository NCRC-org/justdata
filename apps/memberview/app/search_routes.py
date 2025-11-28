"""
Routes for member search and filtering.
"""
from flask import Blueprint, jsonify, request, render_template
import pandas as pd
import logging
from typing import Optional, List, Dict, Any
import math

import sys
from pathlib import Path

# Add parent directory to path for imports
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# Import data_utils - try multiple paths
try:
    from data_utils import MemberDataLoader
except ImportError:
    try:
        from app.data_utils import MemberDataLoader
    except ImportError:
        # Last resort: direct import
        import importlib.util
        data_utils_path = BASE_DIR / 'data_utils.py'
        if data_utils_path.exists():
            spec = importlib.util.spec_from_file_location("data_utils", data_utils_path)
            data_utils = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(data_utils)
            MemberDataLoader = data_utils.MemberDataLoader
        else:
            raise ImportError("Could not find data_utils module")

# Import utility functions
import importlib.util

# Import metro utils
metro_utils_path = BASE_DIR / 'utils' / 'metro_utils.py'
if metro_utils_path.exists():
    spec = importlib.util.spec_from_file_location("metro_utils", metro_utils_path)
    metro_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metro_utils)
    get_cbsa_for_county = metro_utils.get_cbsa_for_county
    get_metros_by_state = metro_utils.get_metros_by_state
    get_counties_by_metro = metro_utils.get_counties_by_metro
else:
    # Fallback functions
    def get_cbsa_for_county(*args, **kwargs):
        return None
    def get_metros_by_state(*args, **kwargs):
        return []
    def get_counties_by_metro(*args, **kwargs):
        return []

# Import state utils
state_utils_path = BASE_DIR / 'utils' / 'state_utils.py'
if state_utils_path.exists():
    spec = importlib.util.spec_from_file_location("state_utils", state_utils_path)
    state_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state_utils)
    get_full_state_name = getattr(state_utils, 'get_full_state_name', lambda x: x)
    normalize_state_name = getattr(state_utils, 'normalize_state_name', lambda x: x)
    # Import state abbreviation map
    STATE_ABBREV_TO_NAME = getattr(state_utils, 'STATE_ABBREV_TO_NAME', {})
else:
    # Fallback functions
    def get_full_state_name(state):
        return state if state else ""
    def normalize_state_name(state):
        return state if state else ""
    STATE_ABBREV_TO_NAME = {}

logger = logging.getLogger(__name__)

# Get template and static folder paths for blueprint
from pathlib import Path
SEARCH_BASE_DIR = Path(__file__).parent.parent
if (SEARCH_BASE_DIR / 'web' / 'templates').exists():
    SEARCH_TEMPLATE_FOLDER = str(SEARCH_BASE_DIR / 'web' / 'templates')
    SEARCH_STATIC_FOLDER = str(SEARCH_BASE_DIR / 'web' / 'static')
else:
    SEARCH_TEMPLATE_FOLDER = str(SEARCH_BASE_DIR / 'templates')
    SEARCH_STATIC_FOLDER = str(SEARCH_BASE_DIR / 'static')

search_bp = Blueprint('search', __name__, 
                      url_prefix='/search', 
                      template_folder=SEARCH_TEMPLATE_FOLDER,
                      static_folder=SEARCH_STATIC_FOLDER,
                      static_url_path='/static')

# Global data loader (lazy loaded)
_data_loader = None

def get_data_loader():
    """Get or create data loader instance."""
    global _data_loader
    if _data_loader is None:
        _data_loader = MemberDataLoader()
    return _data_loader


def _clean_nan_values(obj):
    """
    Recursively clean NaN and Inf values from dictionaries and lists.
    Converts them to None which JSON can handle.
    """
    if isinstance(obj, dict):
        return {k: _clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_nan_values(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif pd.isna(obj):
        return None
    else:
        return obj


@search_bp.route('/')
@search_bp.route('')  # Also handle /search without trailing slash
def search_page():
    """Render the member search page."""
    try:
        # Try web/templates first, then templates
        from pathlib import Path
        BASE_DIR = Path(__file__).parent.parent
        if (BASE_DIR / 'web' / 'templates' / 'member_search.html').exists():
            return render_template('member_search.html')
        elif (BASE_DIR / 'templates' / 'member_search.html').exists():
            return render_template('member_search.html')
        else:
            return f"Template not found. Checked: {BASE_DIR / 'web' / 'templates' / 'member_search.html'} and {BASE_DIR / 'templates' / 'member_search.html'}", 500
    except Exception as e:
        logger.error(f"Error rendering search template: {e}", exc_info=True)
        import traceback
        return f"Error loading search page: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500


@search_bp.route('/api/states')
def get_states():
    """Get list of all states with members."""
    try:
        loader = get_data_loader()
        members_df = loader.get_members()
        
        # Find state column
        state_col = None
        for col in members_df.columns:
            col_lower = col.lower()
            if col_lower == 'state/region' or (col_lower == 'state' and 'country' not in col_lower):
                state_col = col
                break
        
        if not state_col:
            return jsonify({'error': 'State column not found'}), 500
        
        # Get unique states
        states = members_df[state_col].dropna().unique().tolist()
        states = [s for s in states if s and str(s).strip()]
        
        # Filter out invalid values
        exclude_values = {'USA', 'United States', 'US', '', 'N/A', 'NaN', 'None', 'nan'}
        states = [s for s in states if str(s).strip() not in exclude_values]
        
        # Normalize to full state names
        normalized_states = []
        for state in states:
            state_str = str(state).strip()
            full_name = get_full_state_name(state_str)
            if full_name and full_name not in normalized_states:
                normalized_states.append(full_name)
        
        normalized_states.sort()
        
        logger.info(f"Returning {len(normalized_states)} states")
        return jsonify(normalized_states)
    except Exception as e:
        logger.error(f"Error getting states: {e}")
        return jsonify({'error': str(e)}), 500


@search_bp.route('/api/metros/<state>')
def get_metros(state: str):
    """Get list of metro areas for a state."""
    try:
        # Normalize state name
        state_normalized = normalize_state_name(state)
        
        # Get metros from BigQuery
        metros = get_metros_by_state(state_normalized)
        
        # Format for frontend
        metro_list = []
        for metro in metros:
            metro_list.append({
                'code': metro['cbsa_code'],
                'name': metro['cbsa_name']
            })
        
        return jsonify(metro_list)
    except Exception as e:
        logger.error(f"Error getting metros for {state}: {e}")
        return jsonify({'error': str(e)}), 500


@search_bp.route('/api/member/<member_id>')
def get_member_detail(member_id: str):
    """
    Get detailed information for a specific member.
    
    Returns:
        Member details including address, contacts (up to 5), and deals (last 5)
    """
    try:
        loader = get_data_loader()
        
        # Get member basic info
        members_df = loader.get_members()
        
        # Find columns
        record_id_col = None
        name_col = None
        status_col = None
        city_col = None
        state_col = None
        county_col = None
        
        for col in members_df.columns:
            col_lower = col.lower()
            if 'record id' in col_lower:
                record_id_col = col
            elif 'company' in col_lower and 'name' in col_lower:
                name_col = col
            elif 'membership' in col_lower and 'status' in col_lower:
                status_col = col
            elif col_lower == 'city':
                city_col = col
            elif col_lower == 'state/region' or (col_lower == 'state' and 'country' not in col_lower):
                state_col = col
            elif col_lower == 'county':
                county_col = col
        
        if not record_id_col:
            return jsonify({'error': 'Record ID column not found'}), 500
        
        # Find the member
        member_row = members_df[members_df[record_id_col].astype(str).str.strip() == str(member_id).strip()]
        
        if len(member_row) == 0:
            return jsonify({'error': 'Member not found'}), 404
        
        member_row = member_row.iloc[0]
        
        # Get basic member info
        member_name = str(member_row[name_col]) if name_col and pd.notna(member_row[name_col]) else ''
        member_status = str(member_row[status_col]) if status_col and pd.notna(member_row[status_col]) else ''
        city = str(member_row[city_col]) if city_col and pd.notna(member_row[city_col]) else ''
        state = str(member_row[state_col]) if state_col and pd.notna(member_row[state_col]) else ''
        county = str(member_row[county_col]) if county_col and pd.notna(member_row[county_col]) else ''
        
        # Get address from deals table
        deals = loader.load_deals()
        company_id_col_deals = None
        for col in deals.columns:
            if 'associated_company_ids_(primary)' in col.lower() or ('associated company' in col.lower() and 'primary' in col.lower()):
                company_id_col_deals = col
                break
        
        address = ''
        zip_code = ''
        if company_id_col_deals and 'company_address' in deals.columns:
            company_id_str = str(member_id).replace('.0', '').strip()
            member_deals = deals[deals[company_id_col_deals].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == company_id_str]
            if len(member_deals) > 0:
                deal_row = member_deals.iloc[0]
                address = str(deal_row.get('company_address', '')).strip() if pd.notna(deal_row.get('company_address')) else ''
                zip_code = str(deal_row.get('company_zip', '')).strip() if pd.notna(deal_row.get('company_zip')) else ''
        
        # Build full address
        address_parts = []
        if address:
            address_parts.append(address)
        if city:
            address_parts.append(city)
        if state:
            address_parts.append(state)
        if zip_code:
            address_parts.append(zip_code)
        full_address = ', '.join(address_parts) if address_parts else None
        
        # Get contacts (up to 5)
        contacts = loader.get_member_with_contacts(member_id)[:5]
        
        # Get deals (last 5)
        member_deals = loader.get_member_deals(member_id, limit=5)
        
        # Get metro info
        metro_info = None
        if county and state:
            cbsa_data = get_cbsa_for_county(county, state)
            if cbsa_data:
                metro_info = {
                    'code': cbsa_data['cbsa_code'],
                    'name': cbsa_data['cbsa_name']
                }
        
        member_detail = {
            'id': member_id,
            'name': member_name,
            'status': member_status,
            'address': full_address,
            'city': city,
            'state': get_full_state_name(state) if state else '',
            'county': county,
            'zip': zip_code,
            'metro': metro_info,
            'contacts': contacts,
            'deals': member_deals
        }
        
        return jsonify(_clean_nan_values(member_detail))
        
    except Exception as e:
        logger.error(f"Error getting member detail: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@search_bp.route('/api/members')
def search_members():
    """
    Search and filter members.
    
    Query parameters:
    - state: State name (optional)
    - metro: CBSA code (optional)
    - status: Membership status (optional, comma-separated)
    - page: Page number (default: 1)
    - per_page: Results per page (default: 50)
    """
    try:
        loader = get_data_loader()
        
        # Get filter parameters
        state_filter = request.args.get('state', '').strip()
        metro_filter = request.args.get('metro', '').strip()
        status_filter = request.args.get('status', '').strip()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Get all members
        members_df = loader.get_members()
        
        # Find columns
        record_id_col = None
        name_col = None
        status_col = None
        city_col = None
        state_col = None
        county_col = None
        
        for col in members_df.columns:
            col_lower = col.lower()
            if 'record id' in col_lower:
                record_id_col = col
            elif 'company' in col_lower and 'name' in col_lower:
                name_col = col
            elif 'membership' in col_lower and 'status' in col_lower:
                status_col = col
            elif col_lower == 'city':
                city_col = col
            elif col_lower == 'state/region' or (col_lower == 'state' and 'country' not in col_lower):
                state_col = col
            elif col_lower == 'county':
                county_col = col
        
        if not record_id_col or not name_col:
            return jsonify({'error': 'Required columns not found'}), 500
        
        # Apply status filter
        if status_filter:
            statuses = [s.strip() for s in status_filter.split(',')]
            if status_col:
                statuses_upper = [s.upper() for s in statuses]
                members_df = members_df[
                    members_df[status_col].astype(str).str.upper().isin(statuses_upper)
                ].copy()
        
        # Apply state filter
        if state_filter:
            state_normalized = normalize_state_name(state_filter)
            if state_col:
                # Get both full name and abbreviation for matching
                state_full_upper = state_normalized.upper()
                # Find abbreviation for the state
                state_abbrev = None
                for abbr, name in STATE_ABBREV_TO_NAME.items():
                    if name.upper() == state_full_upper:
                        state_abbrev = abbr.upper()
                        break
                
                # Also check if the filter itself is an abbreviation
                if not state_abbrev and state_filter.upper() in STATE_ABBREV_TO_NAME:
                    state_abbrev = state_filter.upper()
                    state_full_upper = STATE_ABBREV_TO_NAME[state_abbrev].upper()
                
                # Match by full state name, abbreviation, or any variation
                # The data has abbreviations like "CA", so we need to match against those
                if state_abbrev:
                    # Match against abbreviation directly (most common case)
                    members_df = members_df[
                        members_df[state_col].astype(str).str.strip().str.upper() == state_abbrev
                    ].copy()
                else:
                    # Fallback: try matching against full name
                    members_df = members_df[
                        members_df[state_col].astype(str).str.strip().str.upper() == state_full_upper
                    ].copy()
        
        # Apply metro filter
        if metro_filter:
            # Get counties in this metro
            counties_in_metro = get_counties_by_metro(metro_filter)
            
            if counties_in_metro:
                # Filter members by county
                if county_col and state_col:
                    # Create county_state column for matching
                    members_df['_county_state'] = (
                        members_df[county_col].astype(str).str.strip() + ', ' +
                        members_df[state_col].astype(str).str.strip()
                    )
                    members_df = members_df[
                        members_df['_county_state'].isin(counties_in_metro)
                    ].copy()
                    members_df = members_df.drop(columns=['_county_state'])
        
        # Get total count
        total_count = len(members_df)
        
        # Convert to list of dicts (show all results - no pagination)
        # Use vectorized operations instead of iterrows() for much better performance
        members_list = []
        
        # Extract columns as Series (vectorized - much faster)
        member_ids = members_df[record_id_col].astype(str) if record_id_col else pd.Series([''] * len(members_df))
        member_names = members_df[name_col].astype(str) if name_col else pd.Series([''] * len(members_df))
        member_statuses = members_df[status_col].fillna('').astype(str) if status_col else pd.Series([''] * len(members_df))
        cities = members_df[city_col].fillna('').astype(str) if city_col else pd.Series([''] * len(members_df))
        states = members_df[state_col].fillna('').astype(str) if state_col else pd.Series([''] * len(members_df))
        counties = members_df[county_col].fillna('').astype(str) if county_col else pd.Series([''] * len(members_df))
        
        # Convert to list and process (still faster than iterrows)
        for i in range(len(members_df)):
            state_val = states.iloc[i] if states.iloc[i] else ''
            member_dict = {
                'id': member_ids.iloc[i] if record_id_col else '',
                'name': member_names.iloc[i] if name_col else '',
                'status': member_statuses.iloc[i] if status_col else '',
                'city': cities.iloc[i] if city_col else '',
                'state': get_full_state_name(state_val) if state_val else '',
                'county': counties.iloc[i] if county_col else '',
                'metro': None  # Skip metro lookup for performance
            }
            members_list.append(_clean_nan_values(member_dict))
        
        return jsonify({
            'members': members_list,
            'total': total_count
        })
        
    except Exception as e:
        logger.error(f"Error searching members: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

