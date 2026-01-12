#!/usr/bin/env python3
"""
Report builder module for creating data tables from Quarterly API data.
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from apps.loantrends.data_utils import parse_quarterly_data


def build_trends_report(graph_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build comprehensive trends report from graph data.
    
    Args:
        graph_data: Dictionary mapping endpoint names to their graph data
    
    Returns:
        Dictionary containing all report tables
    """
    print(f"[DEBUG build_trends_report] Starting with {len(graph_data)} endpoints")
    report_tables = {}
    
    for endpoint, data in graph_data.items():
        print(f"[DEBUG build_trends_report] Processing endpoint: {endpoint}")
        print(f"[DEBUG build_trends_report]   - data is None: {data is None}")
        if data is None:
            print(f"[DEBUG build_trends_report]   - Skipping {endpoint} (data is None)")
            continue
        
        print(f"[DEBUG build_trends_report]   - data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
        print(f"[DEBUG build_trends_report]   - data has 'series': {'series' in data if isinstance(data, dict) else False}")
        
        parsed = parse_quarterly_data(data)
        print(f"[DEBUG build_trends_report]   - Parsed data keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'not a dict'}")
        print(f"[DEBUG build_trends_report]   - Parsed quarters: {len(parsed.get('quarters', []))}")
        print(f"[DEBUG build_trends_report]   - Parsed series count: {len(parsed.get('series', []))}")
        
        # Create table based on endpoint type
        if endpoint == 'applications':
            print(f"[DEBUG build_trends_report]   - Creating applications table")
            report_tables['applications'] = create_applications_table(parsed)
            print(f"[DEBUG build_trends_report]   - Applications table created: {len(report_tables['applications']) if report_tables['applications'] else 0} rows")
        elif endpoint == 'loans':
            print(f"[DEBUG build_trends_report]   - Creating loans table")
            report_tables['loans'] = create_loans_table(parsed)
            print(f"[DEBUG build_trends_report]   - Loans table created: {len(report_tables['loans']) if report_tables['loans'] else 0} rows")
        elif endpoint.startswith('credit-scores'):
            report_tables[endpoint] = create_credit_scores_table(parsed, endpoint)
        elif endpoint.startswith('interest-rates'):
            report_tables[endpoint] = create_interest_rates_table(parsed, endpoint)
        elif endpoint.startswith('denials'):
            report_tables[endpoint] = create_denial_rates_table(parsed, endpoint)
        elif endpoint.startswith('ltv'):
            report_tables[endpoint] = create_ltv_table(parsed, endpoint)
        elif endpoint.startswith('dti'):
            report_tables[endpoint] = create_dti_table(parsed, endpoint)
        elif endpoint.startswith('tlc'):
            report_tables[endpoint] = create_tlc_table(parsed, endpoint)
        else:
            # Generic table for any other endpoint
            report_tables[endpoint] = create_generic_table(parsed, endpoint)
    
    return report_tables


def create_applications_table(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create applications count table."""
    return create_generic_table(data, 'applications')


def create_loans_table(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create loans count table."""
    return create_generic_table(data, 'loans')


def create_all_applications_table(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create all-applications table."""
    return create_generic_table(data, 'all-applications')


def create_credit_scores_table(data: Dict[str, Any], endpoint: str) -> List[Dict[str, Any]]:
    """Create credit scores table."""
    return create_generic_table(data, endpoint)


def create_interest_rates_table(data: Dict[str, Any], endpoint: str) -> List[Dict[str, Any]]:
    """Create interest rates table."""
    return create_generic_table(data, endpoint)


def create_denial_rates_table(data: Dict[str, Any], endpoint: str) -> List[Dict[str, Any]]:
    """Create denial rates table."""
    return create_generic_table(data, endpoint)


def create_ltv_table(data: Dict[str, Any], endpoint: str) -> List[Dict[str, Any]]:
    """Create loan-to-value table."""
    return create_generic_table(data, endpoint)


def create_dti_table(data: Dict[str, Any], endpoint: str) -> List[Dict[str, Any]]:
    """Create debt-to-income table."""
    return create_generic_table(data, endpoint)


def create_tlc_table(data: Dict[str, Any], endpoint: str) -> List[Dict[str, Any]]:
    """Create total loan costs table."""
    return create_generic_table(data, endpoint)


def create_generic_table(data: Dict[str, Any], endpoint: str) -> List[Dict[str, Any]]:
    """
    Create a generic table from parsed quarterly data.
    
    Args:
        data: Parsed quarterly data dictionary
        endpoint: Endpoint name for context
    
    Returns:
        List of dictionaries representing table rows
    """
    print(f"[DEBUG create_generic_table] Creating table for endpoint: {endpoint}")
    print(f"[DEBUG create_generic_table]   - data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
    print(f"[DEBUG create_generic_table]   - quarters: {data.get('quarters', [])}")
    print(f"[DEBUG create_generic_table]   - parsed_series keys: {list(data.get('parsed_series', {}).keys())}")
    
    if not data or not data.get('parsed_series'):
        print(f"[DEBUG create_generic_table]   - WARNING: No data or parsed_series, returning empty list")
        return []
    
    quarters = data.get('quarters', [])
    parsed_series = data.get('parsed_series', {})
    
    print(f"[DEBUG create_generic_table]   - Processing {len(quarters)} quarters")
    print(f"[DEBUG create_generic_table]   - Processing {len(parsed_series)} series")
    
    # Build table: each row is a quarter, columns are series names
    table_data = []
    
    for quarter in quarters:
        row = {'Quarter': quarter}
        
        # Add value for each series
        for series_name, quarter_data in parsed_series.items():
            value = quarter_data.get(quarter)
            # Format value appropriately
            if value is not None:
                if isinstance(value, float):
                    # Round to 2 decimal places for display
                    row[series_name] = round(value, 2)
                else:
                    row[series_name] = value
            else:
                row[series_name] = None
        
        table_data.append(row)
    
    print(f"[DEBUG create_generic_table]   - Created {len(table_data)} rows")
    print(f"[DEBUG create_generic_table]   - First row keys: {list(table_data[0].keys()) if table_data else 'N/A'}")
    return table_data


def create_race_ethnicity_tables(graph_data: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Create race/ethnicity breakdown tables from race/ethnicity endpoints.
    
    Args:
        graph_data: Dictionary of graph data including race/ethnicity endpoints
    
    Returns:
        Dictionary mapping endpoint names to their tables
    """
    race_ethnicity_endpoints = [
        'credit-scores-cc-re', 'credit-scores-fha-re',
        'ltv-cc-re', 'ltv-fha-re',
        'dti-cc-re', 'dti-fha-re',
        'denials-cc-re', 'denials-fha-re',
        'interest-rates-cc-re', 'interest-rates-fha-re',
        'tlc-cc-re', 'tlc-fha-re'
    ]
    
    tables = {}
    
    for endpoint in race_ethnicity_endpoints:
        if endpoint in graph_data and graph_data[endpoint] is not None:
            parsed = parse_quarterly_data(graph_data[endpoint])
            tables[endpoint] = create_generic_table(parsed, endpoint)
    
    return tables


def get_table_summary(table_data: List[Dict[str, Any]], series_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get summary statistics for a table.
    
    Args:
        table_data: List of table row dictionaries
        series_name: Optional series name to summarize (if None, summarizes all numeric columns)
    
    Returns:
        Dictionary with summary statistics
    """
    if not table_data:
        return {}
    
    df = pd.DataFrame(table_data)
    
    if series_name and series_name in df.columns:
        series = df[series_name].dropna()
        if len(series) > 0:
            return {
                'min': float(series.min()),
                'max': float(series.max()),
                'mean': float(series.mean()),
                'median': float(series.median()),
                'count': len(series)
            }
    
    # Summarize all numeric columns
    summary = {}
    numeric_cols = df.select_dtypes(include=['number']).columns
    
    for col in numeric_cols:
        if col == 'Quarter':
            continue
        series = df[col].dropna()
        if len(series) > 0:
            summary[col] = {
                'min': float(series.min()),
                'max': float(series.max()),
                'mean': float(series.mean()),
                'median': float(series.median()),
                'count': len(series)
            }
    
    return summary




