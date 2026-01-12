#!/usr/bin/env python3
"""
Script to show all available variables and sample data for each.
"""

import json
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from justdata.apps.loantrends.config import GRAPH_ENDPOINTS
from justdata.apps.loantrends.data_utils import fetch_graph_data, parse_quarterly_data

def show_variable_info():
    """Display all variables and sample data."""
    
    print("=" * 80)
    print("LOANTRENDS VARIABLES AND SAMPLE DATA")
    print("=" * 80)
    print()
    
    all_endpoints = []
    for category, endpoints in GRAPH_ENDPOINTS.items():
        all_endpoints.extend(endpoints)
    
    for endpoint in all_endpoints:
        print(f"\n{'=' * 80}")
        print(f"ENDPOINT: {endpoint}")
        print(f"{'=' * 80}")
        
        try:
            # Fetch raw data
            raw_data = fetch_graph_data(endpoint)
            
            # Parse the data
            parsed = parse_quarterly_data(raw_data)
            
            print(f"\nTitle: {parsed.get('title', 'N/A')}")
            print(f"Subtitle: {parsed.get('subtitle', 'N/A')}")
            print(f"X-Axis Label: {parsed.get('xLabel', 'N/A')}")
            print(f"Y-Axis Label: {parsed.get('yLabel', 'N/A')}")
            
            # Show series (variables) in this endpoint
            parsed_series = parsed.get('parsed_series', {})
            quarters = parsed.get('quarters', [])
            
            print(f"\nNumber of Series (Variables): {len(parsed_series)}")
            print(f"Number of Quarters: {len(quarters)}")
            print(f"Quarter Range: {quarters[0] if quarters else 'N/A'} to {quarters[-1] if quarters else 'N/A'}")
            
            print(f"\nSeries Names (Variables):")
            for i, series_name in enumerate(parsed_series.keys(), 1):
                print(f"  {i}. {series_name}")
            
            # Show sample data for first 3 series
            print(f"\nSample Data (first 5 quarters for first 3 series):")
            sample_quarters = quarters[:5] if len(quarters) >= 5 else quarters
            
            for series_name in list(parsed_series.keys())[:3]:
                print(f"\n  {series_name}:")
                series_data = parsed_series[series_name]
                for quarter in sample_quarters:
                    value = series_data.get(quarter)
                    if value is not None:
                        print(f"    {quarter}: {value}")
                    else:
                        print(f"    {quarter}: N/A")
            
            # Show full structure of first series
            if parsed_series:
                first_series = list(parsed_series.keys())[0]
                first_series_data = parsed_series[first_series]
                print(f"\n  Full data structure for '{first_series}' (first 10 quarters):")
                for quarter in quarters[:10]:
                    value = first_series_data.get(quarter)
                    print(f"    {quarter}: {value}")
            
        except Exception as e:
            print(f"ERROR fetching data for {endpoint}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"\nTotal Endpoints: {len(all_endpoints)}")
    print(f"\nCategories:")
    for category, endpoints in GRAPH_ENDPOINTS.items():
        print(f"  {category}: {len(endpoints)} endpoints")
        for endpoint in endpoints:
            print(f"    - {endpoint}")

if __name__ == '__main__':
    show_variable_info()
