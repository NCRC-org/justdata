"""County and CBSA centroid lookup tables (loaded from BigQuery / local CSV)
plus coordinate validation helpers."""
import csv
import os
from typing import Any, Dict, Optional

from justdata.apps.analytics.bq.client import get_bigquery_client


# County and CBSA centroids cache - loaded once from Census Bureau Gazetteer data
_county_centroids = None
_cbsa_centroids = None

# BigQuery tables for centroids (created by Jay after CSV upload)
COUNTY_CENTROIDS_TABLE = 'justdata-ncrc.shared.county_centroids'
CBSA_CENTROIDS_TABLE = 'justdata-ncrc.shared.cbsa_centroids'

# Local CSV fallback paths (for development/testing before BigQuery upload)
LOCAL_COUNTY_CSV = os.path.join(os.path.dirname(__file__), '..', 'demo_data', 'county_centroids_2024.csv')
LOCAL_CBSA_CSV = os.path.join(os.path.dirname(__file__), '..', 'demo_data', 'cbsa_centroids_2024.csv')


def get_county_centroids() -> Dict[str, Dict[str, float]]:
    """
    Get county FIPS -> centroid coordinates mapping.

    Uses Census Bureau Gazetteer data (2024) for accurate centroids.
    First tries BigQuery table, falls back to local CSV if not available.

    Returns dict like {'01001': {'lat': 32.5, 'lng': -86.5}, ...}
    Also returns name lookup: {'01001': 'Autauga County', ...}
    """
    global _county_centroids

    if _county_centroids is not None:
        return _county_centroids

    _county_centroids = {'by_fips': {}, 'by_name': {}}

    # Try BigQuery first
    try:
        client = get_bigquery_client()
        query = f"""
            SELECT
                county_fips,
                state_code,
                county_name,
                county_name_normalized,
                latitude,
                longitude
            FROM `{COUNTY_CENTROIDS_TABLE}`
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """
        results = client.query(query).result()

        for row in results:
            fips = str(row.county_fips).zfill(5)
            _county_centroids['by_fips'][fips] = {
                'lat': float(row.latitude),
                'lng': float(row.longitude),
                'name': row.county_name,
                'state': row.state_code
            }
            # Also index by normalized name + state for flexible matching
            name_key = f"{row.county_name_normalized}|{row.state_code}".lower()
            _county_centroids['by_name'][name_key] = {
                'lat': float(row.latitude),
                'lng': float(row.longitude),
                'fips': fips,
                'name': row.county_name
            }

        print(f"[INFO] Loaded {len(_county_centroids['by_fips'])} county centroids from BigQuery")
        return _county_centroids

    except Exception as e:
        print(f"[WARN] Could not load county centroids from BigQuery: {e}")

    # Fall back to local CSV
    try:
        import pandas as pd
        if os.path.exists(LOCAL_COUNTY_CSV):
            df = pd.read_csv(LOCAL_COUNTY_CSV)
            for _, row in df.iterrows():
                fips = str(row['county_fips']).zfill(5)
                _county_centroids['by_fips'][fips] = {
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude']),
                    'name': row['county_name'],
                    'state': row['state_code']
                }
                name_key = f"{row['county_name_normalized']}|{row['state_code']}".lower()
                _county_centroids['by_name'][name_key] = {
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude']),
                    'fips': fips,
                    'name': row['county_name']
                }
            print(f"[INFO] Loaded {len(_county_centroids['by_fips'])} county centroids from local CSV")
        else:
            print(f"[WARN] Local county centroids CSV not found: {LOCAL_COUNTY_CSV}")
    except Exception as e:
        print(f"[ERROR] Failed to load county centroids from CSV: {e}")

    return _county_centroids


def get_cbsa_centroids() -> Dict[str, Dict[str, float]]:
    """
    Get CBSA code -> centroid coordinates mapping.

    Uses Census Bureau Gazetteer data (2024) for accurate CBSA centroids.
    First tries BigQuery table, falls back to local CSV if not available.

    Returns dict like {'47900': {'lat': 38.8, 'lng': -77.0, 'name': 'Washington-Arlington...'}, ...}
    """
    global _cbsa_centroids

    if _cbsa_centroids is not None:
        return _cbsa_centroids

    _cbsa_centroids = {}

    # Try BigQuery first
    try:
        client = get_bigquery_client()
        query = f"""
            SELECT
                cbsa_code,
                cbsa_name,
                principal_city,
                states,
                latitude,
                longitude
            FROM `{CBSA_CENTROIDS_TABLE}`
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """
        results = client.query(query).result()

        for row in results:
            _cbsa_centroids[str(row.cbsa_code)] = {
                'lat': float(row.latitude),
                'lng': float(row.longitude),
                'name': row.cbsa_name,
                'principal_city': row.principal_city,
                'states': row.states
            }

        print(f"[INFO] Loaded {len(_cbsa_centroids)} CBSA centroids from BigQuery")
        return _cbsa_centroids

    except Exception as e:
        print(f"[WARN] Could not load CBSA centroids from BigQuery: {e}")

    # Fall back to local CSV
    try:
        import pandas as pd
        if os.path.exists(LOCAL_CBSA_CSV):
            df = pd.read_csv(LOCAL_CBSA_CSV)
            for _, row in df.iterrows():
                _cbsa_centroids[str(row['cbsa_code'])] = {
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude']),
                    'name': row['cbsa_name'],
                    'principal_city': row['principal_city'],
                    'states': row['states']
                }
            print(f"[INFO] Loaded {len(_cbsa_centroids)} CBSA centroids from local CSV")
        else:
            print(f"[WARN] Local CBSA centroids CSV not found: {LOCAL_CBSA_CSV}")
    except Exception as e:
        print(f"[ERROR] Failed to load CBSA centroids from CSV: {e}")

    return _cbsa_centroids


def lookup_county_centroid(county_fips: str = None, county_name: str = None, state: str = None) -> Optional[Dict]:
    """
    Look up county centroid by FIPS code or by name+state.

    Args:
        county_fips: 5-digit FIPS code (preferred)
        county_name: County name (will be normalized)
        state: 2-letter state code (required if using county_name)

    Returns:
        Dict with 'lat', 'lng', 'name' or None if not found
    """
    centroids = get_county_centroids()

    # Try FIPS lookup first (most reliable)
    if county_fips:
        fips = str(county_fips).zfill(5)
        if fips in centroids['by_fips']:
            return centroids['by_fips'][fips]

    # Fall back to name+state lookup
    if county_name and state:
        # Lazy import to avoid circular dependency with transforms.py
        from justdata.apps.analytics.bq.transforms import normalize_county_name
        normalized = normalize_county_name(county_name)
        if normalized:
            name_key = f"{normalized}|{state}".lower()
            if name_key in centroids['by_name']:
                return centroids['by_name'][name_key]

            # Try without normalization (exact match)
            exact_key = f"{county_name.lower().strip()}|{state}".lower()
            if exact_key in centroids['by_name']:
                return centroids['by_name'][exact_key]

    return None


def lookup_cbsa_centroid(cbsa_code: str) -> Optional[Dict]:
    """
    Look up CBSA centroid by code.

    Args:
        cbsa_code: CBSA code (e.g., '47900')

    Returns:
        Dict with 'lat', 'lng', 'name', 'principal_city' or None if not found
    """
    if not cbsa_code:
        return None

    centroids = get_cbsa_centroids()
    return centroids.get(str(cbsa_code))


# State bounding boxes for coordinate validation (approximate)
STATE_BOUNDS = {
    'AL': {'lat_min': 30.2, 'lat_max': 35.0, 'lng_min': -88.5, 'lng_max': -84.9},
    'AK': {'lat_min': 51.2, 'lat_max': 71.4, 'lng_min': -179.2, 'lng_max': -129.9},
    'AZ': {'lat_min': 31.3, 'lat_max': 37.0, 'lng_min': -114.8, 'lng_max': -109.0},
    'AR': {'lat_min': 33.0, 'lat_max': 36.5, 'lng_min': -94.6, 'lng_max': -89.6},
    'CA': {'lat_min': 32.5, 'lat_max': 42.0, 'lng_min': -124.5, 'lng_max': -114.1},
    'CO': {'lat_min': 36.9, 'lat_max': 41.0, 'lng_min': -109.1, 'lng_max': -102.0},
    'CT': {'lat_min': 40.9, 'lat_max': 42.1, 'lng_min': -73.7, 'lng_max': -71.8},
    'DE': {'lat_min': 38.5, 'lat_max': 39.8, 'lng_min': -75.8, 'lng_max': -75.0},
    'FL': {'lat_min': 24.4, 'lat_max': 31.0, 'lng_min': -87.6, 'lng_max': -80.0},
    'GA': {'lat_min': 30.4, 'lat_max': 35.0, 'lng_min': -85.6, 'lng_max': -80.8},
    'HI': {'lat_min': 18.9, 'lat_max': 22.2, 'lng_min': -160.2, 'lng_max': -154.8},
    'ID': {'lat_min': 42.0, 'lat_max': 49.0, 'lng_min': -117.2, 'lng_max': -111.0},
    'IL': {'lat_min': 36.9, 'lat_max': 42.5, 'lng_min': -91.5, 'lng_max': -87.0},
    'IN': {'lat_min': 37.8, 'lat_max': 41.8, 'lng_min': -88.1, 'lng_max': -84.8},
    'IA': {'lat_min': 40.4, 'lat_max': 43.5, 'lng_min': -96.6, 'lng_max': -90.1},
    'KS': {'lat_min': 37.0, 'lat_max': 40.0, 'lng_min': -102.1, 'lng_max': -94.6},
    'KY': {'lat_min': 36.5, 'lat_max': 39.1, 'lng_min': -89.6, 'lng_max': -81.9},
    'LA': {'lat_min': 28.9, 'lat_max': 33.0, 'lng_min': -94.0, 'lng_max': -88.8},
    'ME': {'lat_min': 43.0, 'lat_max': 47.5, 'lng_min': -71.1, 'lng_max': -66.9},
    'MD': {'lat_min': 37.9, 'lat_max': 39.7, 'lng_min': -79.5, 'lng_max': -75.0},
    'MA': {'lat_min': 41.2, 'lat_max': 42.9, 'lng_min': -73.5, 'lng_max': -69.9},
    'MI': {'lat_min': 41.7, 'lat_max': 48.3, 'lng_min': -90.4, 'lng_max': -82.4},
    'MN': {'lat_min': 43.5, 'lat_max': 49.4, 'lng_min': -97.2, 'lng_max': -89.5},
    'MS': {'lat_min': 30.2, 'lat_max': 35.0, 'lng_min': -91.7, 'lng_max': -88.1},
    'MO': {'lat_min': 36.0, 'lat_max': 40.6, 'lng_min': -95.8, 'lng_max': -89.1},
    'MT': {'lat_min': 44.4, 'lat_max': 49.0, 'lng_min': -116.1, 'lng_max': -104.0},
    'NE': {'lat_min': 40.0, 'lat_max': 43.0, 'lng_min': -104.1, 'lng_max': -95.3},
    'NV': {'lat_min': 35.0, 'lat_max': 42.0, 'lng_min': -120.0, 'lng_max': -114.0},
    'NH': {'lat_min': 42.7, 'lat_max': 45.3, 'lng_min': -72.6, 'lng_max': -70.7},
    'NJ': {'lat_min': 38.9, 'lat_max': 41.4, 'lng_min': -75.6, 'lng_max': -73.9},
    'NM': {'lat_min': 31.3, 'lat_max': 37.0, 'lng_min': -109.1, 'lng_max': -103.0},
    'NY': {'lat_min': 40.5, 'lat_max': 45.0, 'lng_min': -79.8, 'lng_max': -71.9},
    'NC': {'lat_min': 33.8, 'lat_max': 36.6, 'lng_min': -84.3, 'lng_max': -75.5},
    'ND': {'lat_min': 45.9, 'lat_max': 49.0, 'lng_min': -104.1, 'lng_max': -96.6},
    'OH': {'lat_min': 38.4, 'lat_max': 42.0, 'lng_min': -84.8, 'lng_max': -80.5},
    'OK': {'lat_min': 33.6, 'lat_max': 37.0, 'lng_min': -103.0, 'lng_max': -94.4},
    'OR': {'lat_min': 41.9, 'lat_max': 46.3, 'lng_min': -124.6, 'lng_max': -116.5},
    'PA': {'lat_min': 39.7, 'lat_max': 42.3, 'lng_min': -80.5, 'lng_max': -74.7},
    'RI': {'lat_min': 41.1, 'lat_max': 42.0, 'lng_min': -71.9, 'lng_max': -71.1},
    'SC': {'lat_min': 32.0, 'lat_max': 35.2, 'lng_min': -83.4, 'lng_max': -78.5},
    'SD': {'lat_min': 42.5, 'lat_max': 45.9, 'lng_min': -104.1, 'lng_max': -96.4},
    'TN': {'lat_min': 35.0, 'lat_max': 36.7, 'lng_min': -90.3, 'lng_max': -81.7},
    'TX': {'lat_min': 25.8, 'lat_max': 36.5, 'lng_min': -106.7, 'lng_max': -93.5},
    'UT': {'lat_min': 37.0, 'lat_max': 42.0, 'lng_min': -114.1, 'lng_max': -109.0},
    'VT': {'lat_min': 42.7, 'lat_max': 45.0, 'lng_min': -73.4, 'lng_max': -71.5},
    'VA': {'lat_min': 36.5, 'lat_max': 39.5, 'lng_min': -83.7, 'lng_max': -75.2},
    'WA': {'lat_min': 45.5, 'lat_max': 49.0, 'lng_min': -124.8, 'lng_max': -116.9},
    'WV': {'lat_min': 37.2, 'lat_max': 40.6, 'lng_min': -82.6, 'lng_max': -77.7},
    'WI': {'lat_min': 42.5, 'lat_max': 47.1, 'lng_min': -92.9, 'lng_max': -86.8},
    'WY': {'lat_min': 41.0, 'lat_max': 45.0, 'lng_min': -111.1, 'lng_max': -104.1},
    'DC': {'lat_min': 38.8, 'lat_max': 39.0, 'lng_min': -77.1, 'lng_max': -76.9},
    'PR': {'lat_min': 17.9, 'lat_max': 18.5, 'lng_min': -67.3, 'lng_max': -65.6},
}


def validate_coordinates(lat: float, lng: float, state: str = None) -> dict:
    """
    Validate that coordinates are within reasonable bounds.

    Args:
        lat: Latitude
        lng: Longitude
        state: Optional 2-letter state code for more specific validation

    Returns:
        Dict with 'valid' (bool) and 'reason' (str if invalid)
    """
    # Basic range check
    if lat is None or lng is None:
        return {'valid': False, 'reason': 'Missing coordinates'}

    if abs(lat) > 90:
        return {'valid': False, 'reason': f'Latitude {lat} out of range (-90 to 90)'}

    if abs(lng) > 180:
        return {'valid': False, 'reason': f'Longitude {lng} out of range (-180 to 180)'}

    # Check for null island (0, 0)
    if lat == 0 and lng == 0:
        return {'valid': False, 'reason': 'Coordinates are (0, 0) - null island'}

    # US mainland bounds (rough check)
    US_BOUNDS = {
        'lat_min': 24.0,  # Southern tip of Florida Keys
        'lat_max': 49.5,  # Northern border with Canada
        'lng_min': -125.0,  # West coast
        'lng_max': -66.0   # East coast
    }

    # Allow Alaska, Hawaii, Puerto Rico
    in_alaska = 51.0 <= lat <= 72.0 and -180.0 <= lng <= -129.0
    in_hawaii = 18.0 <= lat <= 23.0 and -161.0 <= lng <= -154.0
    in_puerto_rico = 17.5 <= lat <= 18.6 and -68.0 <= lng <= -65.0
    in_mainland = (US_BOUNDS['lat_min'] <= lat <= US_BOUNDS['lat_max'] and
                   US_BOUNDS['lng_min'] <= lng <= US_BOUNDS['lng_max'])

    if not (in_mainland or in_alaska or in_hawaii or in_puerto_rico):
        return {'valid': False, 'reason': f'Coordinates ({lat}, {lng}) outside US bounds'}

    # State-specific validation if state provided
    if state and state.upper() in STATE_BOUNDS:
        bounds = STATE_BOUNDS[state.upper()]
        if not (bounds['lat_min'] <= lat <= bounds['lat_max'] and
                bounds['lng_min'] <= lng <= bounds['lng_max']):
            return {
                'valid': False,
                'reason': f'Coordinates ({lat}, {lng}) outside {state} bounds'
            }

    return {'valid': True, 'reason': None}


