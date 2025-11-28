"""
Flask routes for member map visualization.
Provides API endpoints for filtered member data and member details.
"""
from flask import Blueprint, jsonify, request
from data_utils import MemberDataLoader
from pathlib import Path
import logging
import pandas as pd
import json
import math

logger = logging.getLogger(__name__)

map_bp = Blueprint('map', __name__, url_prefix='/api/map')


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

# Initialize data loader lazily (only when needed)
data_loader = None

def get_data_loader():
    """Get or create data loader instance."""
    global data_loader
    if data_loader is None:
        data_loader = MemberDataLoader()
    return data_loader


@map_bp.route('/members', methods=['GET'])
def get_members():
    """
    Get filtered member data for map visualization.
    
    Query parameters:
        - state: Filter by state (optional)
        - metro: Filter by metro area (optional, not implemented yet)
        - status: Filter by member status - CURRENT, GRACE PERIOD, LAPSED (optional)
    
    Returns:
        JSON array of member objects with location and summary data
    """
    try:
        loader = get_data_loader()
        
        # Get query parameters
        state_filter = request.args.get('state', '').strip()
        metro_filter = request.args.get('metro', '').strip()  # Not implemented yet
        status_filter = request.args.get('status', '').strip()
        
        # Parse status filter
        statuses = None
        if status_filter:
            statuses = [s.strip().upper() for s in status_filter.split(',')]
            # Map common variations
            status_map = {
                'CURRENT': 'CURRENT',
                'ACTIVE': 'CURRENT',
                'GRACE': 'GRACE PERIOD',
                'GRACE PERIOD': 'GRACE PERIOD',
                'LAPSED': 'LAPSED',
            }
            statuses = [status_map.get(s, s) for s in statuses]
        
        # Get members
        members_df = loader.get_members(status_filter=statuses)
        
        if len(members_df) == 0:
            return jsonify([])
        
        # Find column names
        record_id_col = None
        name_col = None
        status_col = None
        city_col = None
        state_col = None
        address_col = None
        zip_col = None
        country_col = None
        
        # Prioritize exact matches first
        if 'State/Region' in members_df.columns:
            state_col = 'State/Region'
        elif 'State' in members_df.columns:
            state_col = 'State'
        
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
            elif not state_col and ('state' in col_lower or 'region' in col_lower) and 'country' not in col_lower:
                state_col = col
            elif 'address' in col_lower or 'street' in col_lower:
                address_col = col
            elif 'zip' in col_lower or 'postal' in col_lower:
                zip_col = col
            elif 'country' in col_lower and 'region' in col_lower:
                country_col = col
        
        # Apply state filter - normalize state name for matching
        if state_filter and state_col:
            from utils.state_utils import normalize_state_name
            normalized_filter = normalize_state_name(state_filter)
            # Try matching both the normalized name and original value
            state_filter_upper = normalized_filter.upper()
            original_upper = state_filter.upper()
            members_df = members_df[
                (members_df[state_col].astype(str).str.upper().str.contains(state_filter_upper, na=False)) |
                (members_df[state_col].astype(str).str.upper().str.contains(original_upper, na=False))
            ]
        
        # Load coordinates if available
        loader = get_data_loader()
        coordinates = loader.load_coordinates()
        
        # Get address data from deals table (company_address, company_zip)
        # Join deals to get address information for companies
        deals = loader.load_deals()
        company_id_col_deals = None
        for col in deals.columns:
            if 'associated_company_ids_(primary)' in col.lower() or ('associated company' in col.lower() and 'primary' in col.lower()):
                company_id_col_deals = col
                break
        
        # Create a mapping of company ID to address/zip from deals
        company_address_map = {}
        if company_id_col_deals and 'company_address' in deals.columns:
            for _, deal_row in deals.iterrows():
                company_id = str(deal_row[company_id_col_deals]).replace('.0', '').strip() if pd.notna(deal_row[company_id_col_deals]) else ''
                if not company_id:
                    continue
                
                # Get address and zip from deal
                deal_address = str(deal_row.get('company_address', '')).strip() if pd.notna(deal_row.get('company_address')) else ''
                deal_zip = str(deal_row.get('company_zip', '')).strip() if pd.notna(deal_row.get('company_zip')) else ''
                
                # Store if we have address data and haven't seen this company yet
                if company_id not in company_address_map and (deal_address or deal_zip):
                    company_address_map[company_id] = {
                        'address': deal_address,
                        'zip': deal_zip
                    }
        
        # Convert to list of dicts
        members_list = []
        for _, row in members_df.iterrows():
            # Get basic info
            member_id = str(row[record_id_col]) if record_id_col else ''
            member_name = str(row[name_col]) if name_col else ''
            member_status = str(row[status_col]) if status_col else ''
            city = str(row[city_col]) if city_col and pd.notna(row[city_col]) else ''
            state = str(row[state_col]) if state_col and pd.notna(row[state_col]) else ''
            country = str(row[country_col]) if country_col and pd.notna(row[country_col]) else 'USA'
            
            # Get address from deals table if available
            address = ''
            zip_code = ''
            if member_id in company_address_map:
                address = company_address_map[member_id].get('address', '')
                zip_code = company_address_map[member_id].get('zip', '')
            
            # Build full address string for geocoding (order: street address, city, state, zip, country)
            address_parts = []
            if address:
                address_parts.append(address)
            if city:
                address_parts.append(city)
            if state:
                address_parts.append(state)
            if zip_code:
                address_parts.append(zip_code)
            if country:
                address_parts.append(country)
            
            full_address = ', '.join(address_parts) if address_parts else None
            
            # Get coordinates - try cache first, then geocode if needed
            # Use full address as cache key if available, otherwise city|state
            if full_address:
                location_key = full_address.lower()
            else:
                location_key = f"{city}|{state}"
            lat = None
            lng = None
            if location_key in coordinates:
                coords = coordinates[location_key]
                if isinstance(coords, list) and len(coords) == 2:
                    lat, lng = coords[0], coords[1]
                elif isinstance(coords, dict):
                    lat = coords.get('lat')
                    lng = coords.get('lng')
            
            # If no coordinates, try to geocode using full address
            if (lat is None or lng is None) and (full_address or (city and state)):
                try:
                    from utils.geocoder import Geocoder
                    from pathlib import Path
                    
                    # Use cache file in data directory
                    cache_file = loader.data_dir / "geocoding_cache.json"
                    geocoder = Geocoder(cache_file=cache_file)
                    
                    # Geocode using full address if available, otherwise city/state
                    coords = geocoder.geocode(
                        city=city if city else None,
                        state=state if state else None,
                        country=country if country else 'USA',
                        address=full_address if full_address else None,
                        company_name=member_name if member_name else None
                    )
                    
                    if coords:
                        lat, lng = float(coords[0]), float(coords[1])
                        # Save to coordinates cache for next time
                        coordinates[location_key] = [lat, lng]
                        loader.save_coordinates(coordinates)
                        logger.info(f"Geocoded {full_address or f'{city}, {state}'} -> {lat}, {lng}")
                    else:
                        logger.debug(f"Geocoding returned no results for {full_address or f'{city}, {state}'}")
                except Exception as e:
                    logger.debug(f"Could not geocode {full_address or f'{city}, {state}'}: {e}")
            
            # Get summary data
            contacts = loader.get_member_with_contacts(member_id)
            deals = loader.get_member_deals(member_id, limit=1)
            
            # Calculate totals
            all_deals = loader.get_member_deals(member_id, limit=100)
            total_deal_amount = sum(d.get('amount', 0) for d in all_deals if isinstance(d.get('amount'), (int, float)))
            
            # Get Form 990 data (if available) - DISABLED
            form_990_data = None
            # if member_name:
            #     form_990_data = loader.get_form_990_data(
            #         company_name=member_name,
            #         city=city if city else None,
            #         state=state if state else None
            #     )
            
            # Ensure lat/lng are floats or None (not strings)
            if lat is not None:
                try:
                    lat = float(lat)
                except (ValueError, TypeError):
                    lat = None
            if lng is not None:
                try:
                    lng = float(lng)
                except (ValueError, TypeError):
                    lng = None
            
            member_dict = {
                'id': member_id,
                'name': member_name,
                'status': member_status,
                'location': {
                    'city': city,
                    'state': state,
                    'lat': lat,
                    'lng': lng,
                },
                'contacts_count': len(contacts),
                'deals_count': len(all_deals),
                'total_deal_amount': total_deal_amount,
                'last_deal': deals[0] if deals else None,
                'form_990': form_990_data,  # Include Form 990 data if found
            }
            
            members_list.append(member_dict)
        
        # Clean all NaN values before returning JSON
        members_list_clean = _clean_nan_values(members_list)
        
        return jsonify(members_list_clean)
    
    except Exception as e:
        logger.error(f"Error getting members: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@map_bp.route('/member/<member_id>', methods=['GET'])
def get_member_detail(member_id):
    """
    Get detailed member information including all contacts and deals.
    
    Args:
        member_id: Company record ID
    
    Returns:
        JSON object with full member details
    """
    try:
        loader = get_data_loader()
        summary = loader.create_member_summary(member_id)
        
        if not summary:
            return jsonify({'error': 'Member not found'}), 404
        
        # Clean NaN values from summary
        summary_clean = _clean_nan_values(summary)
        
        return jsonify(summary_clean)
    
    except Exception as e:
        logger.error(f"Error getting member detail: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@map_bp.route('/states', methods=['GET'])
def get_states():
    """
    Get list of unique states where members are located.
    Returns full state names (not abbreviations).
    
    Returns:
        JSON array of full state names
    """
    try:
        from utils.state_utils import normalize_state_name
        
        loader = get_data_loader()
        members_df = loader.get_members()
        
        # Find state column - prioritize "State/Region" over "Country/Region"
        state_col = None
        
        # First, try exact match for "State/Region"
        if 'State/Region' in members_df.columns:
            state_col = 'State/Region'
        elif 'State' in members_df.columns:
            state_col = 'State'
        else:
            # Fall back to pattern matching, but exclude "Country/Region"
            for col in members_df.columns:
                col_lower = col.lower()
                if ('state' in col_lower or 'region' in col_lower) and 'country' not in col_lower:
                    state_col = col
                    break
        
        if not state_col:
            return jsonify([])
        
        # Get unique states, filter out invalid values
        states = members_df[state_col].dropna().unique().tolist()
        states = [str(s).strip() for s in states if s]
        # Filter out common non-state values
        exclude_values = {'USA', 'United States', 'US', '', 'N/A', 'NaN', 'None'}
        states = [s for s in states if s and s not in exclude_values]
        
        # Normalize to full state names
        normalized_states = [normalize_state_name(s) for s in states]
        normalized_states = sorted(set(normalized_states))
        
        return jsonify(normalized_states)
    
    except Exception as e:
        logger.error(f"Error getting states: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

