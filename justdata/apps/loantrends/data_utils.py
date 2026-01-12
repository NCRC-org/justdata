#!/usr/bin/env python3
"""
Data utilities for fetching HMDA Quarterly Data Graph API data.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from justdata.apps.loantrends.config import QUARTERLY_API_BASE_URL, QUARTERLY_API_TIMEOUT

# Simple in-memory cache (quarterly data updates infrequently)
_cache = {}
_cache_timestamps = {}
CACHE_DURATION = 3600 * 24  # 24 hours in seconds


def fetch_available_graphs() -> Dict[str, Any]:
    """
    Fetch list of all available graphs from the Quarterly API.
    
    Returns:
        Dictionary with 'graphs' key containing list of graph metadata
    """
    cache_key = 'available_graphs'
    
    # Check cache first
    if cache_key in _cache:
        cache_age = time.time() - _cache_timestamps.get(cache_key, 0)
        if cache_age < CACHE_DURATION:
            return _cache[cache_key]
    
    try:
        url = f"{QUARTERLY_API_BASE_URL}"
        headers = {'Content-Type': 'application/json'}
        
        response = requests.get(url, headers=headers, timeout=QUARTERLY_API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Cache the result
        _cache[cache_key] = data
        _cache_timestamps[cache_key] = time.time()
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching available graphs: {e}")
        raise Exception(f"Failed to fetch available graphs from Quarterly API: {e}")


def fetch_graph_data(endpoint: str) -> Dict[str, Any]:
    """
    Fetch specific graph data from the Quarterly API.
    
    Args:
        endpoint: Graph endpoint name (e.g., 'applications', 'credit-scores')
    
    Returns:
        Dictionary with graph data (title, subtitle, series, etc.)
    """
    cache_key = f'graph_{endpoint}'
    
    # Check cache first
    if cache_key in _cache:
        cache_age = time.time() - _cache_timestamps.get(cache_key, 0)
        if cache_age < CACHE_DURATION:
            return _cache[cache_key]
    
    try:
        url = f"{QUARTERLY_API_BASE_URL}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        response = requests.get(url, headers=headers, timeout=QUARTERLY_API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Cache the result
        _cache[cache_key] = data
        _cache_timestamps[cache_key] = time.time()
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching graph data for endpoint '{endpoint}': {e}")
        raise Exception(f"Failed to fetch graph data for '{endpoint}': {e}")


def fetch_multiple_graphs(endpoints: List[str], progress_callback=None) -> Dict[str, Dict[str, Any]]:
    """
    Fetch multiple graph endpoints with error handling.
    
    Args:
        endpoints: List of endpoint names to fetch
        progress_callback: Optional callback function(status, endpoint) for progress updates
    
    Returns:
        Dictionary mapping endpoint names to their graph data
    """
    results = {}
    total = len(endpoints)
    
    for idx, endpoint in enumerate(endpoints, 1):
        if progress_callback:
            progress_callback(f"Fetching {endpoint}...", idx, total)
        
        try:
            data = fetch_graph_data(endpoint)
            results[endpoint] = data
        except Exception as e:
            print(f"Warning: Failed to fetch '{endpoint}': {e}")
            # Continue with other endpoints even if one fails
            results[endpoint] = None
    
    return results


def parse_quarterly_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and structure quarterly API response data.
    
    Args:
        data: Raw API response dictionary
    
    Returns:
        Structured dictionary with parsed data
    """
    if not data or 'series' not in data:
        return {
            'title': data.get('title', 'Unknown'),
            'subtitle': data.get('subtitle', ''),
            'xLabel': data.get('xLabel', 'Quarter'),
            'yLabel': data.get('yLabel', 'Value'),
            'series': [],
            'quarters': [],
            'parsed_series': {}
        }
    
    # Extract all unique quarters from all series
    all_quarters = set()
    for series in data['series']:
        for coord in series.get('coordinates', []):
            all_quarters.add(coord.get('x'))
    
    quarters = sorted(list(all_quarters))
    
    # Parse series data into structured format
    parsed_series = {}
    for series in data['series']:
        series_name = series.get('name', 'Unknown')
        parsed_series[series_name] = {}
        
        for coord in series.get('coordinates', []):
            quarter = coord.get('x')
            value = coord.get('y')
            parsed_series[series_name][quarter] = value
    
    return {
        'title': data.get('title', 'Unknown'),
        'subtitle': data.get('subtitle', ''),
        'xLabel': data.get('xLabel', 'Quarter'),
        'yLabel': data.get('yLabel', 'Value'),
        'series': data.get('series', []),
        'quarters': quarters,
        'parsed_series': parsed_series
    }


def filter_quarters(data: Dict[str, Any], start_quarter: Optional[str] = None, 
                   end_quarter: Optional[str] = None) -> Dict[str, Any]:
    """
    Filter quarterly data to a specific time range.
    
    Args:
        data: Parsed quarterly data dictionary
        start_quarter: Start quarter (e.g., '2020-Q1') or None for all
        end_quarter: End quarter (e.g., '2024-Q4') or None for all
    
    Returns:
        Filtered data dictionary
    """
    if not start_quarter and not end_quarter:
        return data
    
    filtered_data = data.copy()
    filtered_quarters = []
    
    for quarter in data.get('quarters', []):
        if start_quarter and quarter < start_quarter:
            continue
        if end_quarter and quarter > end_quarter:
            continue
        filtered_quarters.append(quarter)
    
    filtered_data['quarters'] = filtered_quarters
    
    # Filter series coordinates
    filtered_series = []
    for series in data.get('series', []):
        filtered_coords = []
        for coord in series.get('coordinates', []):
            quarter = coord.get('x')
            if quarter in filtered_quarters:
                filtered_coords.append(coord)
        
        filtered_series.append({
            **series,
            'coordinates': filtered_coords
        })
    
    filtered_data['series'] = filtered_series
    
    # Filter parsed_series
    filtered_parsed = {}
    for series_name, quarter_data in data.get('parsed_series', {}).items():
        filtered_parsed[series_name] = {
            q: v for q, v in quarter_data.items() 
            if q in filtered_quarters
        }
    
    filtered_data['parsed_series'] = filtered_parsed
    
    return filtered_data


def get_recent_complete_quarter() -> tuple:
    """
    Get the most recent complete quarter based on current date.
    
    Returns:
        Tuple of (year, quarter) integers
    """
    from datetime import datetime
    
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Determine the most recent complete quarter
    if current_month <= 3:
        # We're in Q1 (Jan-Mar), use previous year Q4
        return (current_year - 1, 4)
    elif current_month <= 6:
        # We're in Q2 (Apr-Jun), use Q1 of current year
        return (current_year, 1)
    elif current_month <= 9:
        # We're in Q3 (Jul-Sep), use Q2 of current year
        return (current_year, 2)
    else:
        # We're in Q4 (Oct-Dec), use Q3 of current year
        return (current_year, 3)


def get_recent_12_quarters() -> tuple:
    """
    Calculate the start and end quarters for the most recent 12 quarters (3 years).
    Uses the most recent complete quarter as the end point, then goes back 12 quarters.
    Updates automatically each quarter as new data becomes available.
    
    Returns:
        Tuple of (start_quarter, end_quarter) strings
    """
    end_year, end_quarter = get_recent_complete_quarter()
    
    # Calculate start quarter: go back 11 quarters (12 quarters total, inclusive)
    start_year = end_year
    start_quarter = end_quarter
    
    # Go back 11 quarters
    for _ in range(11):
        start_quarter -= 1
        if start_quarter < 1:
            start_quarter = 4
            start_year -= 1
    
    start_quarter_str = f"{start_year}-Q{start_quarter}"
    end_quarter_str = f"{end_year}-Q{end_quarter}"
    
    return (start_quarter_str, end_quarter_str)


def get_recent_5_years_quarters() -> tuple:
    """
    Calculate the start and end quarters for the most recent 5 years (20 quarters).
    DEPRECATED: Use get_recent_12_quarters() instead.
    Kept for backward compatibility.
    
    Returns:
        Tuple of (start_quarter, end_quarter) strings
    """
    # Use 12 quarters instead of 20
    return get_recent_12_quarters()


def clear_cache():
    """Clear the API response cache."""
    global _cache, _cache_timestamps
    _cache = {}
    _cache_timestamps = {}




