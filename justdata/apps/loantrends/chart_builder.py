#!/usr/bin/env python3
"""
Chart builder module for creating quarterly line chart data from quarterly data.
"""

from typing import Dict, List, Any
from justdata.apps.loantrends.data_utils import parse_quarterly_data, filter_quarters, get_recent_5_years_quarters


def prepare_quarterly_chart_data(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare quarterly data for charting, preserving all quarterly data points.
    
    Args:
        parsed_data: Parsed quarterly data dictionary with 'quarters' and 'parsed_series'
    
    Returns:
        Dictionary with 'quarters' (list of quarter strings) and 'series_data' (dict mapping series names to quarter-value dicts)
    """
    if not parsed_data or not parsed_data.get('parsed_series'):
        return {
            'quarters': [],
            'series_data': {},
            'title': parsed_data.get('title', '') if parsed_data else '',
            'subtitle': parsed_data.get('subtitle', '') if parsed_data else '',
            'yLabel': parsed_data.get('yLabel', 'Value') if parsed_data else 'Value'
        }
    
    quarters = parsed_data.get('quarters', [])
    parsed_series = parsed_data.get('parsed_series', {})
    
    # Sort quarters chronologically
    def quarter_sort_key(q):
        parts = q.split('-Q')
        return (int(parts[0]), int(parts[1]))
    
    sorted_quarters = sorted(quarters, key=quarter_sort_key)
    
    # Prepare series data with quarterly values (no aggregation)
    series_data = {}
    for series_name, quarter_data in parsed_series.items():
        series_data[series_name] = {}
        for quarter in sorted_quarters:
            value = quarter_data.get(quarter)
            if value is not None:
                series_data[series_name][quarter] = round(value, 2)
            else:
                series_data[series_name][quarter] = None
    
    return {
        'quarters': sorted_quarters,
        'series_data': series_data,
        'title': parsed_data.get('title', ''),
        'subtitle': parsed_data.get('subtitle', ''),
        'yLabel': parsed_data.get('yLabel', 'Value')
    }


def aggregate_quarters_by_year(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregate quarterly data by year, averaging values for each series.
    (Kept for backward compatibility if needed)
    
    Args:
        parsed_data: Parsed quarterly data dictionary with 'quarters' and 'parsed_series'
    
    Returns:
        Dictionary with 'years' (list of years) and 'series_data' (dict mapping series names to year-value dicts)
    """
    if not parsed_data or not parsed_data.get('parsed_series'):
        return {
            'years': [],
            'series_data': {}
        }
    
    quarters = parsed_data.get('quarters', [])
    parsed_series = parsed_data.get('parsed_series', {})
    
    # Extract years from quarters and group quarters by year
    year_quarters = {}  # {year: [quarters]}
    for quarter in quarters:
        year = int(quarter.split('-Q')[0])
        if year not in year_quarters:
            year_quarters[year] = []
        year_quarters[year].append(quarter)
    
    years = sorted(year_quarters.keys())
    
    # Aggregate each series by year (average the quarterly values)
    series_data = {}
    for series_name, quarter_data in parsed_series.items():
        series_data[series_name] = {}
        for year in years:
            year_quarter_values = []
            for quarter in year_quarters[year]:
                value = quarter_data.get(quarter)
                if value is not None:
                    year_quarter_values.append(value)
            
            if year_quarter_values:
                # Calculate average for the year
                avg_value = sum(year_quarter_values) / len(year_quarter_values)
                series_data[series_name][year] = round(avg_value, 2)
            else:
                series_data[series_name][year] = None
    
    return {
        'years': years,
        'series_data': series_data,
        'title': parsed_data.get('title', ''),
        'subtitle': parsed_data.get('subtitle', ''),
        'yLabel': parsed_data.get('yLabel', 'Value')
    }


def build_chart_data(graph_data: Dict[str, Dict[str, Any]], time_period: str = "all") -> Dict[str, Any]:
    """
    Build chart data for all endpoints, preserving quarterly data points.
    
    Args:
        graph_data: Dictionary mapping endpoint names to their graph data
        time_period: Time period selection ("all", "recent", or "custom")
    
    Returns:
        Dictionary containing chart data for each endpoint with quarterly data
    """
    from justdata.apps.loantrends.data_utils import get_recent_12_quarters, get_recent_complete_quarter
    
    # Determine filter params
    filter_params = None
    if time_period == "all":
        start_12q, end_12q = get_recent_12_quarters()
        filter_params = {
            'start_quarter': start_12q,
            'end_quarter': end_12q
        }
    elif time_period == "recent":
        # Recent period - use same as "all" (12 quarters)
        start_12q, end_12q = get_recent_12_quarters()
        filter_params = {
            'start_quarter': start_12q,
            'end_quarter': end_12q
        }
    
    chart_data = {}
    
    for endpoint, data in graph_data.items():
        if data is None:
            print(f"[DEBUG chart_builder] Skipping {endpoint} - data is None")
            continue
        
        try:
            # Parse and filter quarterly data
            parsed = parse_quarterly_data(data)
            if filter_params:
                parsed = filter_quarters(parsed, filter_params['start_quarter'], filter_params['end_quarter'])
            
            # Use quarterly data (not aggregated by year)
            chart_data[endpoint] = prepare_quarterly_chart_data(parsed)
            print(f"[DEBUG chart_builder] Created chart data for {endpoint}: {len(chart_data[endpoint].get('quarters', []))} quarters, {len(chart_data[endpoint].get('series_data', {}))} series")
        except Exception as e:
            print(f"[ERROR chart_builder] Error processing {endpoint}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return chart_data
