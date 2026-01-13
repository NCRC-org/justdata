#!/usr/bin/env python3
"""
Census Tract Boundary Utilities for BizSight
Fetches tract boundaries from Census TIGERweb service.
"""

import requests
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


def get_tract_boundaries_geojson(state_fips: str, county_fips: str) -> Optional[Dict]:
    """
    Fetch census tract boundaries as GeoJSON from Census TIGER/Line files.
    
    Uses the Census Bureau's TIGERweb service to get tract boundaries.
    
    Args:
        state_fips: 2-digit state FIPS code (e.g., "19" for Iowa)
        county_fips: 3-digit county FIPS code (e.g., "163" for Polk County)
    
    Returns:
        GeoJSON dictionary with tract boundaries, or None if unavailable
    """
    try:
        # Census TIGERweb REST API endpoint
        # MapServer/8 is for 2020 Census Tracts
        url = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/8/query"
        
        # Ensure FIPS codes are zero-padded
        state_fips = str(state_fips).zfill(2)
        county_fips = str(county_fips).zfill(3)
        
        # Create query for specific county
        params = {
            'where': f"STATE='{state_fips}' AND COUNTY='{county_fips}'",
            'outFields': 'GEOID,NAME,STATE,COUNTY,TRACT',
            'f': 'geojson',
            'outSR': '4326'  # WGS84 coordinate system
        }
        
        logger.info(f"Fetching tract boundaries for State: {state_fips}, County: {county_fips}")
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        geojson = response.json()
        
        if 'features' in geojson and len(geojson['features']) > 0:
            logger.info(f"Fetched {len(geojson['features'])} tract boundaries")
            return geojson
        
        logger.warning(f"No tract boundaries found for State: {state_fips}, County: {county_fips}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching tract boundaries: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching tract boundaries: {e}")
        import traceback
        traceback.print_exc()
        return None

