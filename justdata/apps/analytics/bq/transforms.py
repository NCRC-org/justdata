"""Result transforms / enrichment for analytics queries.

IP geocoding, state-name normalization, county-name normalization,
date suffix formatting, and the various "_enrich_*" helpers that shape
raw BigQuery rows for the dashboards.
"""
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from justdata.apps.analytics.bq.client import get_bigquery_client
from justdata.apps.analytics.bq.centroids import (
    lookup_county_centroid,
    validate_coordinates,
)


# IP Geocoding cache to avoid repeated API calls
_ip_geo_cache: Dict[str, Dict] = {}

def geocode_ip(ip_address: str) -> Optional[Dict[str, Any]]:
    """
    Convert IP address to geographic location using ip-api.com (free tier).
    
    Args:
        ip_address: IP address to geocode
        
    Returns:
        Dict with 'state', 'city', 'lat', 'lng' or None if failed
    """
    if not ip_address or ip_address in ('127.0.0.1', 'localhost', '::1'):
        return None
    
    # Check cache first
    if ip_address in _ip_geo_cache:
        return _ip_geo_cache[ip_address]
    
    try:
        # ip-api.com free tier: 45 requests/minute, no API key needed
        response = requests.get(
            f'http://ip-api.com/json/{ip_address}',
            params={'fields': 'status,regionName,city,lat,lon'},
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                result = {
                    'state': data.get('regionName'),
                    'city': data.get('city'),
                    'lat': data.get('lat'),
                    'lng': data.get('lon')
                }
                _ip_geo_cache[ip_address] = result
                return result
    except Exception as e:
        print(f"[WARN] IP geocoding failed for {ip_address}: {e}")
    
    _ip_geo_cache[ip_address] = None
    return None


# State name to abbreviation mapping for coordinate lookups
STATE_NAME_TO_ABBREV = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'
}

# State FIPS codes to 2-letter abbreviation
STATE_FIPS_TO_ABBREV = {
    '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO',
    '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA', '15': 'HI',
    '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY',
    '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN',
    '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH',
    '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND', '39': 'OH',
    '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD',
    '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA',
    '54': 'WV', '55': 'WI', '56': 'WY'
}


def _normalize_state_to_code(state: str) -> str:
    """Convert full state name, FIPS code, or abbreviation to 2-letter code."""
    if not state:
        return state
    state = str(state).strip()
    # Already a 2-letter code
    if len(state) == 2 and state.upper() in [v for v in STATE_NAME_TO_ABBREV.values()]:
        return state.upper()
    # State FIPS code (2 digits)
    if len(state) == 2 and state in STATE_FIPS_TO_ABBREV:
        return STATE_FIPS_TO_ABBREV[state]
    # Try exact name match
    if state in STATE_NAME_TO_ABBREV:
        return STATE_NAME_TO_ABBREV[state]
    # Try case-insensitive match
    for name, code in STATE_NAME_TO_ABBREV.items():
        if name.lower() == state.lower():
            return code
    return state


def _format_date_suffix(days: int) -> str:
    """Get date suffix for BigQuery table partitions."""
    date = datetime.utcnow() - timedelta(days=days)
    return date.strftime('%Y%m%d')


def normalize_county_name(county_name: str) -> str:
    """
    Normalize county name for matching with centroid data.

    Handles:
    - Trailing FIPS codes: "Baltimore city, Maryland, 24" -> "Baltimore city"
    - State suffixes: "Alameda County, California" -> "Alameda County"
    - Extra whitespace

    Args:
        county_name: Raw county name from events table

    Returns:
        Normalized county name for centroid lookup
    """
    import re
    if not county_name:
        return None

    # Remove trailing FIPS codes (pattern: ", ##" at end)
    county_name = re.sub(r',\s*\d{2}$', '', county_name)

    # Remove state name if appended (pattern: ", StateName" at end)
    # But preserve suffixes like "city" in "Baltimore city"
    county_name = re.sub(r',\s*[A-Z][a-z]+(\s+[A-Z][a-z]+)*$', '', county_name)

    # Standardize spacing
    county_name = ' '.join(county_name.split())

    return county_name.strip()



def _enrich_with_coordinates(data: List[Dict], fips_field: str = 'county_fips') -> List[Dict]:
    """
    Add latitude/longitude to data records based on county FIPS code or name+state.

    Uses Census Bureau Gazetteer data for accurate centroids.
    Falls back to name+state lookup if FIPS doesn't match.
    Validates coordinates are within reasonable bounds.

    Args:
        data: List of data records
        fips_field: Field name containing county FIPS code

    Returns:
        Data enriched with latitude/longitude coordinates
    """
    for item in data:
        fips = item.get(fips_field)
        county_name = item.get('county_name') or item.get('city')
        state = item.get('state')
        
        # Normalize state to 2-letter code (centroids table uses codes)
        state_code = _normalize_state_to_code(state) if state else None

        # Try lookup by FIPS first, then by name+state
        centroid = lookup_county_centroid(
            county_fips=fips,
            county_name=county_name,
            state=state_code
        )

        if centroid:
            lat = centroid['lat']
            lng = centroid['lng']

            # Validate coordinates
            validation = validate_coordinates(lat, lng, state)
            if validation['valid']:
                item['latitude'] = lat
                item['longitude'] = lng
                # Also update county_name if we have a better one from centroids
                if not item.get('county_name') and centroid.get('name'):
                    item['county_name'] = centroid['name']
            else:
                # Invalid coordinates - log warning and skip
                print(f"[WARN] Invalid coordinates for {county_name}, {state}: {validation['reason']}")
                item['latitude'] = None
                item['longitude'] = None
        else:
            # Clear any existing bogus coordinates
            item['latitude'] = None
            item['longitude'] = None
            if fips or county_name:
                print(f"[WARN] No centroid found for: fips={fips}, name={county_name}, state={state}")

    return data


# Cache for lender names
_lender_names_cache: Dict[str, str] = {}

def _enrich_lender_names(data: List[Dict]) -> List[Dict]:
    """
    Look up lender names from the GLEIF reference table for any records missing lender_name.
    
    Args:
        data: List of records with lender_id (LEI) field
        
    Returns:
        Data enriched with lender_name from GLEIF data
    """
    global _lender_names_cache
    
    # Find LEIs that need lookup
    leis_to_lookup = set()
    for item in data:
        lei = item.get('lender_id')
        if lei and not item.get('lender_name'):
            if lei not in _lender_names_cache:
                leis_to_lookup.add(lei)
    
    # Batch lookup from GLEIF table
    if leis_to_lookup:
        try:
            client = get_bigquery_client()
            leis_str = "', '".join(leis_to_lookup)
            query = f"""
                SELECT lei, display_name
                FROM `justdata-ncrc.shared.lender_names_gleif`
                WHERE lei IN ('{leis_str}')
            """
            results = client.query(query).result()
            for row in results:
                _lender_names_cache[row.lei] = row.display_name
            print(f"[INFO] Loaded {len(leis_to_lookup)} lender names from GLEIF")
        except Exception as e:
            print(f"[WARN] Could not load lender names from GLEIF: {e}")
    
    # Enrich the data
    for item in data:
        lei = item.get('lender_id')
        if lei and not item.get('lender_name'):
            item['lender_name'] = _lender_names_cache.get(lei)
    
    return data


def _enrich_lender_interest_with_coordinates(data: List[Dict]) -> List[Dict]:
    """
    Add latitude/longitude to lender interest data based on researcher county FIPS.

    Uses Census Bureau Gazetteer data for accurate centroids.

    Args:
        data: List of lender interest records with researcher_county_fips field

    Returns:
        Data enriched with latitude/longitude coordinates for map display
    """
    for item in data:
        fips = item.get('researcher_county_fips')
        county_name = item.get('researcher_city')
        state = item.get('researcher_state')
        
        # Normalize state to 2-letter code
        state_code = _normalize_state_to_code(state) if state else None

        centroid = lookup_county_centroid(
            county_fips=fips,
            county_name=county_name,
            state=state_code
        )

        if centroid:
            item['latitude'] = centroid['lat']
            item['longitude'] = centroid['lng']
        else:
            item['latitude'] = None
            item['longitude'] = None

    return data




def _enrich_with_county_names(client, data: List[Dict]) -> List[Dict]:
    """Add county names to data using shared.cbsa_to_county table."""
    fips_list = [d['county_fips'] for d in data if d.get('county_fips')]
    if not fips_list:
        return data

    fips_str = "', '".join(fips_list)
    query = f"""
        SELECT DISTINCT geoid5 AS county_fips, County AS county_name
        FROM `justdata-ncrc.shared.cbsa_to_county`
        WHERE geoid5 IN ('{fips_str}')
    """

    try:
        results = client.query(query).result()
        name_lookup = {row['county_fips']: row['county_name'] for row in results}

        for item in data:
            fips = item.get('county_fips')
            if fips and fips in name_lookup:
                item['county_name'] = name_lookup[fips]
            else:
                item['county_name'] = None

        return data
    except Exception as e:
        print(f"Error enriching county names: {e}")
        return data




def _is_ga4_client_id(user_id: str) -> bool:
    """
    Check if a user_id is a GA4 client ID (format: number.number) vs Firebase Auth UID.
    GA4 client IDs look like: 2106917405.1769129344
    Firebase Auth UIDs are alphanumeric without periods.
    """
    if not user_id:
        return False
    # GA4 client IDs contain a period and are numeric on both sides
    if '.' in user_id:
        parts = user_id.split('.')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return True
    return False


def _enrich_users_from_firestore(users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich user records with profile data from Firestore.

    Args:
        users: List of user records with at least user_id

    Returns:
        Users enriched with user_email, user_type, organization_name, user_name
    """
    try:
        from firebase_admin import firestore
        db = firestore.client()
    except Exception as e:
        print(f"Could not connect to Firestore: {e}")
        return users

    for user in users:
        user_id = user.get('user_id')
        if not user_id:
            continue

        # Skip GA4 client IDs - they won't have Firestore profiles
        # GA4 client IDs look like: 2106917405.1769129344
        if _is_ga4_client_id(user_id):
            continue

        try:
            # Get user profile from Firestore
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                profile = user_doc.to_dict()
                user['user_email'] = profile.get('email', '')
                user['user_name'] = profile.get('displayName', profile.get('email', ''))
                user['user_type'] = profile.get('userType', '')
                user['organization_name'] = profile.get('organizationName', '')
        except Exception as e:
            # Continue even if one user fails
            print(f"Failed to get Firestore profile for {user_id}: {e}")
            continue

    return users


def _lookup_single_lender_name(lender_id: str) -> Optional[str]:
    """Look up a single lender name from GLEIF table."""
    global _lender_names_cache
    
    if lender_id in _lender_names_cache:
        return _lender_names_cache.get(lender_id)
    
    try:
        client = get_bigquery_client()
        query = f"""
            SELECT display_name
            FROM `justdata-ncrc.shared.lender_names_gleif`
            WHERE lei = '{lender_id}'
            LIMIT 1
        """
        results = list(client.query(query).result())
        if results:
            name = results[0].display_name
            _lender_names_cache[lender_id] = name
            return name
    except Exception as e:
        print(f"[WARN] Could not look up lender name for {lender_id}: {e}")
    
    return None


