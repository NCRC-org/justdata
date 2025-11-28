"""
Geocoding utility for converting city/state to lat/lng coordinates.
Uses Nominatim (OpenStreetMap) for free geocoding.
"""
import requests
import time
import json
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class Geocoder:
    """Geocodes locations using Nominatim (OpenStreetMap)."""
    
    def __init__(self, cache_file: Optional[Path] = None):
        """
        Initialize geocoder.
        
        Args:
            cache_file: Path to JSON file to cache geocoding results
        """
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.cache_file = cache_file
        self.cache = self._load_cache() if cache_file else {}
        self.rate_limit_delay = 1.0  # 1 second between requests (Nominatim requirement)
        self.last_request_time = 0
    
    def _load_cache(self) -> Dict[str, Dict]:
        """Load geocoding cache from file."""
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load geocoding cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save geocoding cache to file."""
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, 'w') as f:
                    json.dump(self.cache, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not save geocoding cache: {e}")
    
    def _rate_limit(self):
        """Enforce rate limiting for Nominatim API."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def geocode(self, city: str = None, state: str = None, country: str = "USA", 
                address: str = None, company_name: str = None) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to lat/lng coordinates.
        
        Args:
            city: City name (optional if address provided)
            state: State name or abbreviation (optional if address provided)
            country: Country name (default: USA)
            address: Full address string (preferred - more accurate)
            company_name: Company name to include in query for better matching
        
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        # If full address provided, use it
        if address:
            query = address
            if country and country not in address:
                query = f"{address}, {country}"
            cache_key = query.lower()
        elif city and state:
            # Build query from components
            if company_name:
                query = f"{company_name}, {city}, {state}, {country}"
            else:
                query = f"{city}, {state}, {country}"
            cache_key = f"{city}, {state}, {country}".lower()
        else:
            return None
        
        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if cached.get('lat') and cached.get('lng'):
                return (cached['lat'], cached['lng'])
        
        # Rate limit
        self._rate_limit()
        
        try:
            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'MemberView/1.0 (NCRC)'  # Required by Nominatim
            }
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                result = data[0]
                lat = float(result.get('lat', 0))
                lng = float(result.get('lon', 0))
                
                if lat and lng:
                    # Cache result
                    self.cache[cache_key] = {'lat': lat, 'lng': lng}
                    self._save_cache()
                    
                    return (lat, lng)
        
        except Exception as e:
            logger.warning(f"Geocoding failed for {query}: {e}")
        
        return None
    
    def batch_geocode(self, locations: list) -> Dict[str, Tuple[float, float]]:
        """
        Geocode multiple locations with caching and rate limiting.
        
        Args:
            locations: List of dicts with 'city' and 'state' keys
        
        Returns:
            Dictionary mapping location strings to (lat, lng) tuples
        """
        results = {}
        
        for loc in locations:
            city = loc.get('city', '')
            state = loc.get('state', '')
            
            if not city or not state:
                continue
            
            coords = self.geocode(city, state)
            if coords:
                key = f"{city}, {state}".lower()
                results[key] = coords
        
        return results


def geocode_member_locations(members_df, cache_file: Optional[Path] = None):
    import pandas as pd
    """
    Add lat/lng coordinates to members dataframe.
    
    Args:
        members_df: DataFrame with 'city' and 'state' columns
        cache_file: Path to cache file for geocoding results
    
    Returns:
        DataFrame with 'lat' and 'lng' columns added
    """
    import pandas as pd
    
    geocoder = Geocoder(cache_file=cache_file)
    
    # Find city and state columns
    city_col = None
    state_col = None
    
    for col in members_df.columns:
        col_lower = col.lower()
        if col_lower == 'city':
            city_col = col
        elif 'state' in col_lower or 'region' in col_lower:
            state_col = col
    
    if not city_col or not state_col:
        logger.warning("Could not find city or state columns")
        return members_df
    
    # Add lat/lng columns
    members_df = members_df.copy()
    members_df['lat'] = None
    members_df['lng'] = None
    
    # Get unique locations
    unique_locations = members_df[[city_col, state_col]].drop_duplicates()
    
    # Geocode unique locations
    location_coords = {}
    for _, row in unique_locations.iterrows():
        city = str(row[city_col]) if pd.notna(row[city_col]) else ''
        state = str(row[state_col]) if pd.notna(row[state_col]) else ''
        
        if city and state:
            coords = geocoder.geocode(city, state)
            if coords:
                location_coords[f"{city}|{state}"] = coords
    
    # Apply coordinates to dataframe
    for idx, row in members_df.iterrows():
        city = str(row[city_col]) if pd.notna(row[city_col]) else ''
        state = str(row[state_col]) if pd.notna(row[state_col]) else ''
        
        key = f"{city}|{state}"
        if key in location_coords:
            lat, lng = location_coords[key]
            members_df.at[idx, 'lat'] = lat
            members_df.at[idx, 'lng'] = lng
    
    return members_df

