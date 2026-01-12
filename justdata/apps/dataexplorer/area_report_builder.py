#!/usr/bin/env python3
"""
Area Analysis Report Builder
Builds report data structures for area analysis reports.
Reuses LendSight's proven table building functions.
Mimics LendSight structure but without intro text or AI narrative.
"""

import pandas as pd
import numpy as np
import logging
import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Import LendSight's proven table building functions
from apps.lendsight.mortgage_report_builder import (
    create_demographic_overview_table,
    create_income_borrowers_table,
    create_income_tracts_table,
    create_minority_tracts_table,
    create_top_lenders_detailed_table,
    calculate_mortgage_hhi_for_year
)
from apps.lendsight.hud_processor import get_hud_data_for_counties


def create_loan_costs_table(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """
    Create Section 2 Loan Costs table with years as columns.
    
    Metrics:
    - Property Value (average)
    - Loan Amount (average)
    - Downpayment/Equity (average: property_value - loan_amount)
    - Interest Rate (average)
    - Closing Costs (average: total_loan_costs)
    - Origination Fees (average: origination_charges)
    
    Args:
        df: DataFrame with loan data
        years: List of years to include
        
    Returns:
        DataFrame with Metric column and year columns + Change column
    """
    if df.empty:
        return pd.DataFrame()
    
    # Required columns
    required_cols = ['year', 'avg_property_value', 'avg_loan_amount', 'avg_interest_rate', 
                     'avg_total_loan_costs', 'avg_origination_charges']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.warning(f"[DEBUG] Missing columns for loan costs table: {missing_cols}")
        return pd.DataFrame()
    
    # Filter to specified years
    df_years = df[df['year'].isin(years)].copy()
    if df_years.empty:
        return pd.DataFrame()
    
    # Identify exempt lenders (those with <1,000 total loans across all years)
    # Exempt lenders are not required to report property_value, total_loan_costs, origination_charges
    # We'll exclude their $0 values from calculations, but keep legitimate $0 values from non-exempt lenders
    exempt_lenders = set()
    if 'lei' in df_years.columns and 'total_originations' in df_years.columns:
        # Calculate total loans per lender across all years
        lender_totals = df_years.groupby('lei')['total_originations'].sum()
        # Lenders with <1,000 total loans are exempt
        exempt_lenders = set(lender_totals[lender_totals < 1000].index)
        logger.info(f"[DEBUG] Identified {len(exempt_lenders)} exempt lenders (total loans < 1,000)")
    elif 'lender_name' in df_years.columns and 'total_originations' in df_years.columns:
        # Fallback to lender_name if lei not available
        lender_totals = df_years.groupby('lender_name')['total_originations'].sum()
        exempt_lenders = set(lender_totals[lender_totals < 1000].index)
        logger.info(f"[DEBUG] Identified {len(exempt_lenders)} exempt lenders by name (total loans < 1,000)")
    
    # Aggregate by year
    year_data = {}
    for year in sorted(years):
        year_df = df_years[df_years['year'] == year]
        if year_df.empty:
            continue
        
        # Calculate averages (weighted by loan count if available, otherwise simple average)
        # For property_value, total_loan_costs, origination_charges: exclude $0 values from exempt lenders only
        # This preserves legitimate $0 values (e.g., home equity loans with $0 closing costs)
        if 'total_originations' in year_df.columns:
            total_loans = year_df['total_originations'].sum()
            if total_loans > 0:
                # Weighted average
                # For exempt lenders, exclude $0 values; for non-exempt lenders, include all values
                if exempt_lenders and ('lei' in year_df.columns or 'lender_name' in year_df.columns):
                    lender_col = 'lei' if 'lei' in year_df.columns else 'lender_name'
                    # Filter: exclude exempt lenders with $0 values, but keep non-exempt lenders (including $0)
                    property_value_df = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_property_value'] == 0) | (year_df['avg_property_value'].isna())))
                    ]
                    total_loan_costs_df = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_total_loan_costs'] == 0) | (year_df['avg_total_loan_costs'].isna())))
                    ]
                    origination_charges_df = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_origination_charges'] == 0) | (year_df['avg_origination_charges'].isna())))
                    ]
                else:
                    # No lender identifier available, fall back to excluding all $0 values
                    property_value_df = year_df[(year_df['avg_property_value'] > 0) & (year_df['avg_property_value'].notna())]
                    total_loan_costs_df = year_df[(year_df['avg_total_loan_costs'] > 0) & (year_df['avg_total_loan_costs'].notna())]
                    origination_charges_df = year_df[(year_df['avg_origination_charges'] > 0) & (year_df['avg_origination_charges'].notna())]
                
                # Calculate weighted averages
                property_value_total = property_value_df['total_originations'].sum()
                total_loan_costs_total = total_loan_costs_df['total_originations'].sum()
                origination_charges_total = origination_charges_df['total_originations'].sum()
                
                year_data[year] = {
                    'property_value': (property_value_df['avg_property_value'] * property_value_df['total_originations']).sum() / property_value_total if property_value_total > 0 else np.nan,
                    'loan_amount': (year_df['avg_loan_amount'] * year_df['total_originations']).sum() / total_loans,
                    'interest_rate': (year_df['avg_interest_rate'] * year_df['total_originations']).sum() / total_loans,
                    'total_loan_costs': (total_loan_costs_df['avg_total_loan_costs'] * total_loan_costs_df['total_originations']).sum() / total_loan_costs_total if total_loan_costs_total > 0 else np.nan,
                    'origination_charges': (origination_charges_df['avg_origination_charges'] * origination_charges_df['total_originations']).sum() / origination_charges_total if origination_charges_total > 0 else np.nan
                }
            else:
                # Simple average
                if exempt_lenders and ('lei' in year_df.columns or 'lender_name' in year_df.columns):
                    lender_col = 'lei' if 'lei' in year_df.columns else 'lender_name'
                    property_value_filtered = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_property_value'] == 0) | (year_df['avg_property_value'].isna())))
                    ]['avg_property_value']
                    total_loan_costs_filtered = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_total_loan_costs'] == 0) | (year_df['avg_total_loan_costs'].isna())))
                    ]['avg_total_loan_costs']
                    origination_charges_filtered = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_origination_charges'] == 0) | (year_df['avg_origination_charges'].isna())))
                    ]['avg_origination_charges']
                else:
                    property_value_filtered = year_df[(year_df['avg_property_value'] > 0) & (year_df['avg_property_value'].notna())]['avg_property_value']
                    total_loan_costs_filtered = year_df[(year_df['avg_total_loan_costs'] > 0) & (year_df['avg_total_loan_costs'].notna())]['avg_total_loan_costs']
                    origination_charges_filtered = year_df[(year_df['avg_origination_charges'] > 0) & (year_df['avg_origination_charges'].notna())]['avg_origination_charges']
                
                year_data[year] = {
                    'property_value': property_value_filtered.mean() if len(property_value_filtered) > 0 else np.nan,
                    'loan_amount': year_df['avg_loan_amount'].mean(),
                    'interest_rate': year_df['avg_interest_rate'].mean(),
                    'total_loan_costs': total_loan_costs_filtered.mean() if len(total_loan_costs_filtered) > 0 else np.nan,
                    'origination_charges': origination_charges_filtered.mean() if len(origination_charges_filtered) > 0 else np.nan
                }
        else:
            # Simple average
            if exempt_lenders and ('lei' in year_df.columns or 'lender_name' in year_df.columns):
                lender_col = 'lei' if 'lei' in year_df.columns else 'lender_name'
                property_value_filtered = year_df[
                    ~((year_df[lender_col].isin(exempt_lenders)) & 
                      ((year_df['avg_property_value'] == 0) | (year_df['avg_property_value'].isna())))
                ]['avg_property_value']
                total_loan_costs_filtered = year_df[
                    ~((year_df[lender_col].isin(exempt_lenders)) & 
                      ((year_df['avg_total_loan_costs'] == 0) | (year_df['avg_total_loan_costs'].isna())))
                ]['avg_total_loan_costs']
                origination_charges_filtered = year_df[
                    ~((year_df[lender_col].isin(exempt_lenders)) & 
                      ((year_df['avg_origination_charges'] == 0) | (year_df['avg_origination_charges'].isna())))
                ]['avg_origination_charges']
            else:
                property_value_filtered = year_df[(year_df['avg_property_value'] > 0) & (year_df['avg_property_value'].notna())]['avg_property_value']
                total_loan_costs_filtered = year_df[(year_df['avg_total_loan_costs'] > 0) & (year_df['avg_total_loan_costs'].notna())]['avg_total_loan_costs']
                origination_charges_filtered = year_df[(year_df['avg_origination_charges'] > 0) & (year_df['avg_origination_charges'].notna())]['avg_origination_charges']
            
            year_data[year] = {
                'property_value': property_value_filtered.mean() if len(property_value_filtered) > 0 else np.nan,
                'loan_amount': year_df['avg_loan_amount'].mean(),
                'interest_rate': year_df['avg_interest_rate'].mean(),
                'total_loan_costs': total_loan_costs_filtered.mean() if len(total_loan_costs_filtered) > 0 else np.nan,
                'origination_charges': origination_charges_filtered.mean() if len(origination_charges_filtered) > 0 else np.nan
            }
        
        # Calculate downpayment/equity
        year_data[year]['downpayment_equity'] = year_data[year]['property_value'] - year_data[year]['loan_amount']
    
    if not year_data:
        return pd.DataFrame()
    
    # Build table rows
    metrics = [
        ('Property Value', 'property_value', 'currency'),
        ('Loan Amount', 'loan_amount', 'currency'),
        ('Downpayment/Equity', 'downpayment_equity', 'currency'),
        ('Interest Rate', 'interest_rate', 'percentage'),
        ('Closing Costs', 'total_loan_costs', 'currency'),
        ('Origination Fees', 'origination_charges', 'currency')
    ]
    
    rows = []
    for metric_name, metric_key, format_type in metrics:
        row = {'Metric': metric_name}
        
        # Add year columns (ensure year is string for JSON serialization)
        for year in sorted(years):
            year_str = str(year)  # Convert to string for consistent column names
            if year in year_data:
                value = year_data[year][metric_key]
                if pd.isna(value) or value is None:
                    row[year_str] = 'N/A'
                elif format_type == 'currency':
                    row[year_str] = f"${value:,.0f}"
                elif format_type == 'percentage':
                    row[year_str] = f"{value:.2f}%"
                else:
                    row[year_str] = f"{value:,.0f}"
            else:
                row[year_str] = 'N/A'
        
        # Calculate change (first to last year)
        if len(years) >= 2 and years[0] in year_data and years[-1] in year_data:
            first_value = year_data[years[0]][metric_key]
            last_value = year_data[years[-1]][metric_key]
            if not pd.isna(first_value) and not pd.isna(last_value) and first_value != 0:
                if format_type == 'percentage':
                    change = last_value - first_value
                    row[f'Change Over Time ({years[0]}-{years[-1]})'] = f"{change:+.2f}pp"
                else:
                    change_pct = ((last_value - first_value) / first_value) * 100
                    row[f'Change Over Time ({years[0]}-{years[-1]})'] = f"{change_pct:+.1f}%"
            else:
                row[f'Change Over Time ({years[0]}-{years[-1]})'] = 'N/A'
        else:
            row[f'Change Over Time ({years[0]}-{years[-1]})'] = 'N/A'
        
        rows.append(row)
    
    result_df = pd.DataFrame(rows)
    return result_df


def create_lender_loan_costs_table(df: pd.DataFrame, latest_year: int, lender_type: str = None) -> pd.DataFrame:
    """
    Create Section 3 Loan Costs table with lenders as rows and most recent year metrics as columns.
    
    Metrics for most recent year:
    - Property Value (average)
    - Loan Amount (average)
    - Downpayment/Equity (average: property_value - loan_amount)
    - Interest Rate (average)
    - Closing Costs (average: total_loan_costs)
    - Origination Fees (average: origination_charges)
    
    Args:
        df: DataFrame with loan data
        latest_year: Most recent year to use for metrics
        lender_type: Optional filter by lender type ('Bank', 'Mortgage Company', 'Credit Union')
        
    Returns:
        DataFrame with Lender column and metric columns for most recent year
    """
    if df.empty:
        return pd.DataFrame()
    
    # Filter by lender type if specified
    if lender_type and 'lender_type' in df.columns:
        df = df[df['lender_type'] == lender_type].copy()
    
    # Filter to latest year
    df_latest = df[df['year'] == latest_year].copy()
    if df_latest.empty:
        return pd.DataFrame()
    
    # Required columns
    required_cols = ['lender_name', 'avg_property_value', 'avg_loan_amount', 'avg_interest_rate', 
                     'avg_total_loan_costs', 'avg_origination_charges', 'total_originations']
    missing_cols = [col for col in required_cols if col not in df_latest.columns]
    if missing_cols:
        logger.warning(f"[DEBUG] Missing columns for lender loan costs table: {missing_cols}")
        return pd.DataFrame()
    
    # Aggregate by lender (weighted averages)
    lender_data = []
    for lender_name in df_latest['lender_name'].unique():
        lender_df = df_latest[df_latest['lender_name'] == lender_name]
        total_loans = lender_df['total_originations'].sum()
        
        if total_loans > 0:
            # Weighted averages
            property_value = (lender_df['avg_property_value'] * lender_df['total_originations']).sum() / total_loans
            loan_amount = (lender_df['avg_loan_amount'] * lender_df['total_originations']).sum() / total_loans
            interest_rate = (lender_df['avg_interest_rate'] * lender_df['total_originations']).sum() / total_loans
            total_loan_costs = (lender_df['avg_total_loan_costs'] * lender_df['total_originations']).sum() / total_loans
            origination_charges = (lender_df['avg_origination_charges'] * lender_df['total_originations']).sum() / total_loans
            downpayment_equity = property_value - loan_amount
            
            lender_data.append({
                'Lender': lender_name,
                'Total Loans': f"{total_loans:,}",
                'Property Value': f"${property_value:,.0f}" if not pd.isna(property_value) else 'N/A',
                'Loan Amount': f"${loan_amount:,.0f}" if not pd.isna(loan_amount) else 'N/A',
                'Downpayment/Equity': f"${downpayment_equity:,.0f}" if not pd.isna(downpayment_equity) else 'N/A',
                'Interest Rate': f"{interest_rate:.2f}%" if not pd.isna(interest_rate) else 'N/A',
                'Closing Costs': f"${total_loan_costs:,.0f}" if not pd.isna(total_loan_costs) else 'N/A',
                'Origination Fees': f"${origination_charges:,.0f}" if not pd.isna(origination_charges) else 'N/A'
            })
    
    if not lender_data:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(lender_data)
    # Sort by Total Loans descending
    result_df['Total Loans Sort'] = result_df['Total Loans'].str.replace(',', '').astype(int)
    result_df = result_df.sort_values('Total Loans Sort', ascending=False).drop('Total Loans Sort', axis=1)
    
    return result_df


def filter_df_by_loan_purpose(df: pd.DataFrame, purpose: str) -> pd.DataFrame:
    """
    Filter DataFrame by loan purpose.
    
    Args:
        df: DataFrame with 'loan_purpose' column
        purpose: One of 'all', 'purchase', 'refinance', 'equity'
    
    Returns:
        Filtered DataFrame
    """
    if purpose == 'all':
        return df.copy()
    
    # HMDA loan purpose codes
    purpose_codes = {
        'purchase': ['1'],
        'refinance': ['31', '32'],
        'equity': ['2', '4']
    }
    
    if purpose not in purpose_codes:
        logger.warning(f"Unknown loan purpose: {purpose}, returning all data")
        return df.copy()
    
    codes = purpose_codes[purpose]
    # Convert loan_purpose to string for comparison
    filtered = df[df['loan_purpose'].astype(str).isin(codes)].copy()
    logger.info(f"[DEBUG] Filtered DataFrame for {purpose}: {len(filtered)} rows from {len(df)} rows")
    return filtered


def fetch_acs_housing_data(geoids: List[str], api_key: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Fetch ACS housing data for multiple counties.
    
    Fetches:
    - Median home value (B25077_001E)
    - Median selected monthly owner costs (B25088_001E)
    - Median gross rent (B25064_001E)
    - Owner cost burden (B25091_001E - median selected monthly owner costs as % of income)
    - Rental burden (B25070_001E - gross rent as % of income)
    - Owner occupied units (B25003_002E)
    - Total occupied units (B25003_001E)
    - Total housing units (B25001_001E)
    - 1-unit detached (B25024_002E)
    - 1-unit attached (B25024_003E)
    - 2 units (B25024_004E)
    - 3-4 units (B25024_005E)
    - Mobile home (B25024_010E)
    - Owner occupied by race/ethnicity (B25003B_002E, B25003C_002E, B25003D_002E, B25003E_002E, B25003F_002E, B25003G_002E, B25003H_002E, B25003I_002E)
    
    Args:
        geoids: List of 5-digit GEOID5 codes (counties)
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Dictionary mapping geoid5 to housing data with structure:
        {
            'geoid5': {
                'time_periods': {
                    'acs_2006_2010': {...},
                    'acs_2016_2020': {...},
                    'acs_recent': {...}
                }
            }
        }
    """
    if api_key is None:
        api_key = os.getenv('CENSUS_API_KEY') or os.getenv('census_api_key')
    
    if not api_key:
        logger.error("[CRITICAL] CENSUS_API_KEY not set - cannot fetch housing data")
        return {}
    
    if not geoids:
        return {}
    
    # Group geoids by state for efficient processing
    counties_by_state = {}
    for geoid in geoids:
        if len(geoid) != 5:
            continue
        state_fips = geoid[:2]
        county_fips = geoid[2:]
        if state_fips not in counties_by_state:
            counties_by_state[state_fips] = []
        counties_by_state[state_fips].append({
            'geoid5': geoid,
            'county_fips': county_fips
        })
    
    result = {}
    
    # Housing variables to fetch (split into two groups to avoid API issues)
    # Basic housing variables
    housing_vars = [
        'NAME',
        'B25077_001E',  # Median value (dollars) - Owner-occupied housing units
        'B25088_001E',  # Median selected monthly owner costs (dollars) - Owner-occupied housing units
        'B25064_001E',  # Median gross rent (dollars)
        'B19013_001E',  # Median household income (dollars)
        'B25003_001E',  # Total occupied housing units
        'B25003_002E',  # Owner-occupied housing units
        'B25001_001E',  # Total housing units
        'B25024_002E',  # 1-unit, detached
        'B25024_003E',  # 1-unit, attached
        'B25024_004E',  # 2 units
        'B25024_005E',  # 3-4 units
        'B25024_010E',  # Mobile home
        # Owner occupied by race/ethnicity
        'B25003B_002E',  # Black or African American alone - Owner-occupied
        'B25003C_002E',  # American Indian and Alaska Native alone - Owner-occupied
        'B25003D_002E',  # Asian alone - Owner-occupied
        'B25003E_002E',  # Native Hawaiian and Other Pacific Islander alone - Owner-occupied
        'B25003F_002E',  # Some other race alone - Owner-occupied
        'B25003G_002E',  # Two or more races - Owner-occupied
        'B25003H_002E',  # White alone, not Hispanic or Latino - Owner-occupied
        'B25003I_002E',  # Hispanic or Latino - Owner-occupied
        # Total occupied by race/ethnicity (for calculating percentages)
        'B25003B_001E',  # Black or African American alone - Total occupied
        'B25003C_001E',  # American Indian and Alaska Native alone - Total occupied
        'B25003D_001E',  # Asian alone - Total occupied
        'B25003E_001E',  # Native Hawaiian and Other Pacific Islander alone - Total occupied
        'B25003F_001E',  # Some other race alone - Total occupied
        'B25003G_001E',  # Two or more races - Total occupied
        'B25003H_001E',  # White alone, not Hispanic or Latino - Total occupied
        'B25003I_001E',  # Hispanic or Latino - Total occupied
        # NOTE: B25032 variables temporarily removed - may not exist for all ACS years
        # Will add back after testing if they cause API failures
        # NOTE: B25070 and B25091 burden variables removed - will fetch separately
    ]
    
    # Rent burden variables (B25070): Gross rent as percentage of income
    # We need categories to calculate % of renters who are burdened (30%+)
    rent_burden_vars = [
        'B25070_001E',  # Total renters
        'B25070_007E',  # 30.0 to 34.9 percent
        'B25070_008E',  # 35.0 to 39.9 percent
        'B25070_009E',  # 40.0 to 49.9 percent
        'B25070_010E',  # 50.0 percent or more
    ]
    
    # Owner cost burden variables (B25091): Selected monthly owner costs as percentage of income
    # We need categories to calculate % of owners who are burdened (30%+)
    owner_burden_vars = [
        'B25091_001E',  # Total owners
        'B25091_007E',  # 30.0 to 34.9 percent
        'B25091_008E',  # 35.0 to 39.9 percent
        'B25091_009E',  # 40.0 to 49.9 percent
        'B25091_010E',  # 50.0 percent or more
    ]
    
    
    # Time periods to fetch: 2006-2010, 2016-2020, most recent
    acs_years = [
        (2010, 'acs5', 'acs_2006_2010'),
        (2020, 'acs5', 'acs_2016_2020'),
        (2023, 'acs5', 'acs_recent')  # Will try 2023, 2022, etc. if needed
    ]
    
    # Process each state
    for state_fips, counties in counties_by_state.items():
        for county_info in counties:
            geoid5 = county_info['geoid5']
            county_fips = county_info['county_fips']
            
            county_data = {
                'geoid5': geoid5,
                'time_periods': {}
            }
            
            # Fetch data for each time period
            for year, acs_type, period_key in acs_years:
                if period_key == 'acs_recent':
                    # Try most recent years first
                    attempts = [(2023, 'acs5'), (2022, 'acs5'), (2021, 'acs5')]
                else:
                    attempts = [(year, acs_type)]
                
                data_fetched = False
                for attempt_year, attempt_type in attempts:
                    try:
                        url = f"https://api.census.gov/data/{attempt_year}/acs/{attempt_type}"
                        params = {
                            'get': ','.join(housing_vars),
                            'for': f'county:{county_fips}',
                            'in': f'state:{state_fips}',
                            'key': api_key
                        }
                        
                        logger.info(f"[DEBUG] Fetching ACS {attempt_year} housing data for {geoid5} (state={state_fips}, county={county_fips})")
                        response = requests.get(url, params=params, timeout=10)
                        if response.status_code == 503:
                            logger.warning(f"ACS {attempt_year} housing API returned 503 for {geoid5}")
                            continue
                        if response.status_code != 200:
                            logger.error(f"ACS {attempt_year} housing API returned {response.status_code} for {geoid5}: {response.text[:200]}")
                            continue
                        response.raise_for_status()
                        data = response.json()
                        
                        if data and len(data) > 1:
                            headers = data[0]
                            row = data[1]
                            record = dict(zip(headers, row))
                            
                            # Extract values
                            def safe_int(v):
                                try:
                                    return int(float(v)) if v and v != 'null' else 0
                                except (ValueError, TypeError):
                                    return 0
                            
                            def safe_float(v):
                                try:
                                    return float(v) if v and v != 'null' else 0.0
                                except (ValueError, TypeError):
                                    return 0.0
                            
                            period_data = {
                                'year': f"{attempt_year} ACS",
                                'median_home_value': safe_int(record.get('B25077_001E', 0)),
                                'median_owner_costs': safe_int(record.get('B25088_001E', 0)),
                                'median_rent': safe_int(record.get('B25064_001E', 0)),
                                # Burden percentages will be calculated from burden category variables
                                'owner_cost_burden_pct': 0.0,  # Will be calculated from B25091 categories
                                'rental_burden_pct': 0.0,  # Will be calculated from B25070 categories
                                'median_household_income': safe_int(record.get('B19013_001E', 0)),
                                'total_occupied_units': safe_int(record.get('B25003_001E', 0)),
                                'owner_occupied_units': safe_int(record.get('B25003_002E', 0)),
                                'total_housing_units': safe_int(record.get('B25001_001E', 0)),
                                'units_1_detached': safe_int(record.get('B25024_002E', 0)),
                                'units_1_attached': safe_int(record.get('B25024_003E', 0)),
                                'units_2': safe_int(record.get('B25024_004E', 0)),
                                'units_3_4': safe_int(record.get('B25024_005E', 0)),
                                'units_mobile': safe_int(record.get('B25024_010E', 0)),
                                # Owner-occupied by structure type (from B25032) - will be 0 if not fetched
                                'owner_occupied_1_detached': 0,  # Will fetch separately if needed
                                'owner_occupied_1_attached': 0,
                                'owner_occupied_2': 0,
                                'owner_occupied_3_4': 0,
                                # Total occupied by structure type (for denominator) - will be 0 if not fetched
                                'occupied_1_detached': 0,
                                'occupied_1_attached': 0,
                                'occupied_2': 0,
                                'occupied_3_4': 0,
                                # Owner occupied by race
                                'owner_occupied_black': safe_int(record.get('B25003B_002E', 0)),
                                'owner_occupied_native': safe_int(record.get('B25003C_002E', 0)),
                                'owner_occupied_asian': safe_int(record.get('B25003D_002E', 0)),
                                'owner_occupied_pacific': safe_int(record.get('B25003E_002E', 0)),
                                'owner_occupied_other': safe_int(record.get('B25003F_002E', 0)),
                                'owner_occupied_multi': safe_int(record.get('B25003G_002E', 0)),
                                'owner_occupied_white': safe_int(record.get('B25003H_002E', 0)),
                                'owner_occupied_hispanic': safe_int(record.get('B25003I_002E', 0)),
                                # Total occupied by race (for percentages)
                                'total_occupied_black': safe_int(record.get('B25003B_001E', 0)),
                                'total_occupied_native': safe_int(record.get('B25003C_001E', 0)),
                                'total_occupied_asian': safe_int(record.get('B25003D_001E', 0)),
                                'total_occupied_pacific': safe_int(record.get('B25003E_001E', 0)),
                                'total_occupied_other': safe_int(record.get('B25003F_001E', 0)),
                                'total_occupied_multi': safe_int(record.get('B25003G_001E', 0)),
                                'total_occupied_white': safe_int(record.get('B25003H_001E', 0)),
                                'total_occupied_hispanic': safe_int(record.get('B25003I_001E', 0)),
                            }
                            
                            # Fetch B25032 variables separately (occupied units by structure type)
                            # These are needed for calculating % of 1-4 units that are owner-occupied
                            b25032_vars = [
                                'B25032_001E',  # Total occupied: 1-unit, detached
                                'B25032_002E',  # Owner-occupied: 1-unit, detached
                                'B25032_004E',  # Total occupied: 1-unit, attached
                                'B25032_005E',  # Owner-occupied: 1-unit, attached
                                'B25032_007E',  # Total occupied: 2 units
                                'B25032_008E',  # Owner-occupied: 2 units
                                'B25032_010E',  # Total occupied: 3-4 units
                                'B25032_011E',  # Owner-occupied: 3-4 units
                            ]
                            
                            try:
                                b25032_url = f"https://api.census.gov/data/{attempt_year}/acs/{attempt_type}"
                                b25032_params = {
                                    'get': ','.join(b25032_vars),
                                    'for': f'county:{county_fips}',
                                    'in': f'state:{state_fips}',
                                    'key': api_key
                                }
                                b25032_response = requests.get(b25032_url, params=b25032_params, timeout=10)
                                if b25032_response.status_code == 200:
                                    b25032_data = b25032_response.json()
                                    if b25032_data and len(b25032_data) > 1:
                                        b25032_headers = b25032_data[0]
                                        b25032_row = b25032_data[1]
                                        b25032_record = dict(zip(b25032_headers, b25032_row))
                                        
                                        period_data.update({
                                            'owner_occupied_1_detached': safe_int(b25032_record.get('B25032_002E', 0)),
                                            'owner_occupied_1_attached': safe_int(b25032_record.get('B25032_005E', 0)),
                                            'owner_occupied_2': safe_int(b25032_record.get('B25032_008E', 0)),
                                            'owner_occupied_3_4': safe_int(b25032_record.get('B25032_011E', 0)),
                                            'occupied_1_detached': safe_int(b25032_record.get('B25032_001E', 0)),
                                            'occupied_1_attached': safe_int(b25032_record.get('B25032_004E', 0)),
                                            'occupied_2': safe_int(b25032_record.get('B25032_007E', 0)),
                                            'occupied_3_4': safe_int(b25032_record.get('B25032_010E', 0)),
                                        })
                                        logger.info(f"Successfully fetched B25032 data for {geoid5} ({attempt_year})")
                            except Exception as e:
                                logger.warning(f"Could not fetch B25032 data for {geoid5} ({attempt_year}): {e}")
                            
                            # Fetch rent burden categories (B25070) to calculate % of renters who are burdened
                            try:
                                rent_burden_url = f"https://api.census.gov/data/{attempt_year}/acs/{attempt_type}"
                                rent_burden_params = {
                                    'get': ','.join(rent_burden_vars),
                                    'for': f'county:{county_fips}',
                                    'in': f'state:{state_fips}',
                                    'key': api_key
                                }
                                rent_burden_response = requests.get(rent_burden_url, params=rent_burden_params, timeout=10)
                                if rent_burden_response.status_code == 200:
                                    rent_burden_data = rent_burden_response.json()
                                    if rent_burden_data and len(rent_burden_data) > 1:
                                        rent_burden_headers = rent_burden_data[0]
                                        rent_burden_row = rent_burden_data[1]
                                        rent_burden_record = dict(zip(rent_burden_headers, rent_burden_row))
                                        
                                        total_renters = safe_int(rent_burden_record.get('B25070_001E', 0))
                                        burdened_renters = (
                                            safe_int(rent_burden_record.get('B25070_007E', 0)) +  # 30.0-34.9%
                                            safe_int(rent_burden_record.get('B25070_008E', 0)) +  # 35.0-39.9%
                                            safe_int(rent_burden_record.get('B25070_009E', 0)) +  # 40.0-49.9%
                                            safe_int(rent_burden_record.get('B25070_010E', 0))    # 50.0%+
                                        )
                                        
                                        if total_renters > 0:
                                            period_data['rental_burden_pct'] = (burdened_renters / total_renters) * 100
                                        logger.info(f"Calculated rental burden for {geoid5} ({attempt_year}): {period_data['rental_burden_pct']:.1f}%")
                            except Exception as e:
                                logger.warning(f"Could not fetch B25070 rent burden data for {geoid5} ({attempt_year}): {e}")
                            
                            # Fetch owner cost burden categories (B25091) to calculate % of owners who are burdened
                            try:
                                owner_burden_url = f"https://api.census.gov/data/{attempt_year}/acs/{attempt_type}"
                                owner_burden_params = {
                                    'get': ','.join(owner_burden_vars),
                                    'for': f'county:{county_fips}',
                                    'in': f'state:{state_fips}',
                                    'key': api_key
                                }
                                owner_burden_response = requests.get(owner_burden_url, params=owner_burden_params, timeout=10)
                                if owner_burden_response.status_code == 200:
                                    owner_burden_data = owner_burden_response.json()
                                    if owner_burden_data and len(owner_burden_data) > 1:
                                        owner_burden_headers = owner_burden_data[0]
                                        owner_burden_row = owner_burden_data[1]
                                        owner_burden_record = dict(zip(owner_burden_headers, owner_burden_row))
                                        
                                        total_owners = safe_int(owner_burden_record.get('B25091_001E', 0))
                                        burdened_owners = (
                                            safe_int(owner_burden_record.get('B25091_007E', 0)) +  # 30.0-34.9%
                                            safe_int(owner_burden_record.get('B25091_008E', 0)) +  # 35.0-39.9%
                                            safe_int(owner_burden_record.get('B25091_009E', 0)) +  # 40.0-49.9%
                                            safe_int(owner_burden_record.get('B25091_010E', 0))    # 50.0%+
                                        )
                                        
                                        if total_owners > 0:
                                            period_data['owner_cost_burden_pct'] = (burdened_owners / total_owners) * 100
                                        logger.info(f"Calculated owner cost burden for {geoid5} ({attempt_year}): {period_data['owner_cost_burden_pct']:.1f}%")
                            except Exception as e:
                                logger.warning(f"Could not fetch B25091 owner burden data for {geoid5} ({attempt_year}): {e}")
                            
                            county_data['time_periods'][period_key] = period_data
                            data_fetched = True
                            logger.info(f"Successfully fetched ACS {attempt_year} housing data for {geoid5}")
                            break
                            
                    except Exception as e:
                        logger.warning(f"Failed to fetch ACS {attempt_year} housing data for {geoid5}: {e}")
                        continue
                
                if not data_fetched and period_key != 'acs_recent':
                    logger.warning(f"Could not fetch {period_key} housing data for {geoid5}")
            
            if county_data['time_periods']:
                result[geoid5] = county_data
    
    return result


def create_housing_costs_table(housing_data: Dict[str, Dict[str, Any]], geoids: List[str]) -> List[Dict[str, Any]]:
    """
    Create Table 4: Home value, owner costs, owner cost burden, rent, rental burden.
    
    Args:
        housing_data: Dictionary from fetch_acs_housing_data
        geoids: List of GEOID5 codes
    
    Returns:
        List of dictionaries with time period data
    """
    if not housing_data:
        return []
    
    # Aggregate data across all counties for each time period
    time_periods = ['acs_2006_2010', 'acs_2016_2020', 'acs_recent']
    result = []
    
    for period_key in time_periods:
        period_data = {
            'time_period': period_key,
            'year': None,
            'median_home_value': 0,
            'median_owner_costs': 0,
            'owner_cost_burden_pct': 0.0,
            'median_rent': 0,
            'rental_burden_pct': 0.0,
            'median_household_income': 0
        }
        
        counties_with_data = 0
        # Use weighted medians - weight by number of households/units
        home_values_weighted = []  # (value, weight) tuples
        owner_costs_weighted = []
        owner_burdens_weighted = []  # For burden percentages, weight by number of owners
        rents_weighted = []
        rental_burdens_weighted = []  # For burden percentages, weight by number of renters
        household_incomes_weighted = []  # Weight by total occupied units (households)
        
        for geoid in geoids:
            if geoid not in housing_data:
                continue
            county_periods = housing_data[geoid].get('time_periods', {})
            if period_key not in county_periods:
                continue
            
            county_data = county_periods[period_key]
            if not period_data['year']:
                period_data['year'] = county_data.get('year', period_key)
            
            # Get weights (number of households/units)
            total_occupied = county_data.get('total_occupied_units', 0)  # Total households
            owner_occupied = county_data.get('owner_occupied_units', 0)
            renter_occupied = total_occupied - owner_occupied if total_occupied > 0 else 0
            
            # Collect values with weights for weighted median calculation
            if county_data.get('median_home_value', 0) > 0 and owner_occupied > 0:
                home_values_weighted.append((county_data['median_home_value'], owner_occupied))
            if county_data.get('median_owner_costs', 0) > 0 and owner_occupied > 0:
                owner_costs_weighted.append((county_data['median_owner_costs'], owner_occupied))
            # For burden, accept any value and weight by number of owners/renters
            owner_burden_val = county_data.get('owner_cost_burden_pct', 0)
            if owner_burden_val != 0 and owner_occupied > 0:
                owner_burdens_weighted.append((owner_burden_val, owner_occupied))
            if county_data.get('median_rent', 0) > 0 and renter_occupied > 0:
                rents_weighted.append((county_data['median_rent'], renter_occupied))
            rental_burden_val = county_data.get('rental_burden_pct', 0)
            if rental_burden_val != 0 and renter_occupied > 0:
                rental_burdens_weighted.append((rental_burden_val, renter_occupied))
            if county_data.get('median_household_income', 0) > 0 and total_occupied > 0:
                household_incomes_weighted.append((county_data['median_household_income'], total_occupied))
            
            counties_with_data += 1
        
        # Calculate weighted medians
        def weighted_median(values_weights):
            """Calculate weighted median from list of (value, weight) tuples."""
            if not values_weights:
                return None
            # Sort by value
            sorted_vw = sorted(values_weights, key=lambda x: x[0])
            total_weight = sum(w for _, w in sorted_vw)
            cumsum = 0
            target = total_weight / 2
            for value, weight in sorted_vw:
                cumsum += weight
                if cumsum >= target:
                    return value
            # Fallback to last value
            return sorted_vw[-1][0]
        
        if home_values_weighted:
            period_data['median_home_value'] = int(weighted_median(home_values_weighted))
        if owner_costs_weighted:
            period_data['median_owner_costs'] = int(weighted_median(owner_costs_weighted))
        if owner_burdens_weighted:
            period_data['owner_cost_burden_pct'] = float(weighted_median(owner_burdens_weighted))
        if rents_weighted:
            period_data['median_rent'] = int(weighted_median(rents_weighted))
        if rental_burdens_weighted:
            period_data['rental_burden_pct'] = float(weighted_median(rental_burdens_weighted))
        if household_incomes_weighted:
            period_data['median_household_income'] = int(weighted_median(household_incomes_weighted))
        
        if counties_with_data > 0:
            result.append(period_data)
    
    return result


def create_owner_occupancy_table(housing_data: Dict[str, Dict[str, Any]], geoids: List[str], 
                                  population_data: Dict[str, Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Create Table 5: Owner occupied % overall, then by race (limit to races with 1%+ of population).
    
    Args:
        housing_data: Dictionary from fetch_acs_housing_data
        geoids: List of GEOID5 codes
        population_data: Optional historical census data to determine which races have 1%+ population
    
    Returns:
        List of dictionaries with time period data
    """
    if not housing_data:
        return []
    
    # Determine which races have 1%+ of population (use most recent ACS data)
    race_threshold = 0.01  # 1%
    races_to_include = set()
    
    if population_data:
        # Check most recent ACS data for each county
        for geoid in geoids:
            if geoid not in population_data:
                continue
            county_data = population_data[geoid]
            time_periods = county_data.get('time_periods', {})
            acs_data = time_periods.get('acs', {})
            demographics = acs_data.get('demographics', {})
            
            total_pop = demographics.get('total_population', 0)
            if total_pop > 0:
                if demographics.get('white_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('white')
                if demographics.get('black_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('black')
                if demographics.get('asian_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('asian')
                if demographics.get('native_american_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('native')
                if demographics.get('hopi_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('pacific')
                if demographics.get('multi_racial_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('multi')
                if demographics.get('hispanic_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('hispanic')
    else:
        # If no population data, include all races
        races_to_include = {'white', 'black', 'asian', 'native', 'pacific', 'multi', 'hispanic'}
    
    time_periods = ['acs_2006_2010', 'acs_2016_2020', 'acs_recent']
    result = []
    
    for period_key in time_periods:
        period_data = {
            'time_period': period_key,
            'year': None,
            'owner_occupied_pct_overall': 0.0,
            'owner_occupied_by_race': {}
        }
        
        total_occupied = 0
        total_owner_occupied = 0
        race_totals = {}
        race_owner_occupied = {}
        
        for geoid in geoids:
            if geoid not in housing_data:
                continue
            county_periods = housing_data[geoid].get('time_periods', {})
            if period_key not in county_periods:
                continue
            
            county_data = county_periods[period_key]
            if not period_data['year']:
                period_data['year'] = county_data.get('year', period_key)
            
            # Aggregate overall
            total_occupied += county_data.get('total_occupied_units', 0)
            total_owner_occupied += county_data.get('owner_occupied_units', 0)
            
            # Aggregate by race
            race_mapping = {
                'white': ('total_occupied_white', 'owner_occupied_white'),
                'black': ('total_occupied_black', 'owner_occupied_black'),
                'asian': ('total_occupied_asian', 'owner_occupied_asian'),
                'native': ('total_occupied_native', 'owner_occupied_native'),
                'pacific': ('total_occupied_pacific', 'owner_occupied_pacific'),
                'multi': ('total_occupied_multi', 'owner_occupied_multi'),
                'hispanic': ('total_occupied_hispanic', 'owner_occupied_hispanic'),
            }
            
            for race, (total_key, owner_key) in race_mapping.items():
                if race not in races_to_include:
                    continue
                
                if race not in race_totals:
                    race_totals[race] = 0
                    race_owner_occupied[race] = 0
                
                race_totals[race] += county_data.get(total_key, 0)
                race_owner_occupied[race] += county_data.get(owner_key, 0)
        
        # Calculate percentages
        if total_occupied > 0:
            period_data['owner_occupied_pct_overall'] = (total_owner_occupied / total_occupied) * 100
        
        # Store population shares for sorting (calculate for all periods, but use most recent for sorting)
        period_data['population_shares'] = {}
        for race in races_to_include:
            if race in race_totals and race_totals[race] > 0:
                period_data['owner_occupied_by_race'][race] = (race_owner_occupied[race] / race_totals[race]) * 100
                # Calculate population share (% of total occupied units)
                if total_occupied > 0:
                    period_data['population_shares'][race] = (race_totals[race] / total_occupied) * 100
        
        result.append(period_data)
    
    return result


def create_housing_units_table(housing_data: Dict[str, Dict[str, Any]], geoids: List[str]) -> List[Dict[str, Any]]:
    """
    Create Table 6: Number of units, % that are 1-4 units, % of those that are manufactured/mobile.
    
    Args:
        housing_data: Dictionary from fetch_acs_housing_data
        geoids: List of GEOID5 codes
    
    Returns:
        List of dictionaries with time period data
    """
    if not housing_data:
        return []
    
    time_periods = ['acs_2006_2010', 'acs_2016_2020', 'acs_recent']
    result = []
    
    for period_key in time_periods:
        period_data = {
            'time_period': period_key,
            'year': None,
            'total_units': 0,
            'pct_1_4_units': 0.0,
            'pct_manufactured_mobile': 0.0,
            'pct_5_plus_units': 0.0,
            'pct_1_4_owner_occupied': 0.0
        }
        
        total_units = 0
        units_1_4 = 0
        units_mobile = 0
        owner_occupied_1_4 = 0
        occupied_1_4 = 0  # Total occupied 1-4 units (for denominator)
        
        for geoid in geoids:
            if geoid not in housing_data:
                continue
            county_periods = housing_data[geoid].get('time_periods', {})
            if period_key not in county_periods:
                continue
            
            county_data = county_periods[period_key]
            if not period_data['year']:
                period_data['year'] = county_data.get('year', period_key)
            
            # Aggregate
            county_total = county_data.get('total_housing_units', 0)
            total_units += county_total
            
            # 1-4 units = 1 detached + 1 attached + 2 units + 3-4 units
            county_1_4 = (
                county_data.get('units_1_detached', 0) +
                county_data.get('units_1_attached', 0) +
                county_data.get('units_2', 0) +
                county_data.get('units_3_4', 0)
            )
            units_1_4 += county_1_4
            
            # Owner-occupied 1-4 units (from B25032 - occupied units only)
            county_owner_occupied_1_4 = (
                county_data.get('owner_occupied_1_detached', 0) +
                county_data.get('owner_occupied_1_attached', 0) +
                county_data.get('owner_occupied_2', 0) +
                county_data.get('owner_occupied_3_4', 0)
            )
            owner_occupied_1_4 += county_owner_occupied_1_4
            
            # Total occupied 1-4 units (for denominator - should use B25032, not B25024)
            # B25024 counts all units (occupied + vacant), B25032 counts only occupied
            county_occupied_1_4 = (
                county_data.get('occupied_1_detached', 0) +
                county_data.get('occupied_1_attached', 0) +
                county_data.get('occupied_2', 0) +
                county_data.get('occupied_3_4', 0)
            )
            # If B25032 data not available, fall back to using B25024 (total units) as approximation
            if county_occupied_1_4 == 0:
                county_occupied_1_4 = county_1_4
            
            occupied_1_4 += county_occupied_1_4
            units_mobile += county_data.get('units_mobile', 0)
        
        period_data['total_units'] = total_units
        
        if total_units > 0:
            period_data['pct_1_4_units'] = (units_1_4 / total_units) * 100
            period_data['pct_manufactured_mobile'] = (units_mobile / total_units) * 100
            # 5+ units = total - 1-4 units - mobile (approximate, as mobile might be included in 1-4)
            # Actually, mobile is separate, so 5+ = total - 1-4 - mobile
            units_5_plus = total_units - units_1_4 - units_mobile
            period_data['pct_5_plus_units'] = (units_5_plus / total_units) * 100
        
        # Calculate % of 1-4 units that are owner-occupied
        # Use occupied_1_4 as denominator (occupied units only), not total units_1_4
        if occupied_1_4 > 0:
            period_data['pct_1_4_owner_occupied'] = (owner_occupied_1_4 / occupied_1_4) * 100
        elif units_1_4 > 0:
            # Fallback: if we don't have occupied data, use total units (less accurate)
            period_data['pct_1_4_owner_occupied'] = (owner_occupied_1_4 / units_1_4) * 100
        
        result.append(period_data)
    
    return result


def build_area_report(
    hmda_data: List[Dict[str, Any]],  # Changed: Now expects list of dicts, just like LendSight
    geoids: List[str],
    years: List[int],
    census_data: Dict = None,
    historical_census_data: Dict = None,
    progress_tracker=None,
    action_taken: List[str] = None  # Track whether this is originations or applications
) -> Dict[str, Any]:
    """
    Build area analysis report data structure.
    
    Uses the same structure as LendSight's build_mortgage_report:
    - Takes raw_data (list of dicts from BigQuery) as input
    - Converts to DataFrame internally
    - Uses exact same column names and structure as LendSight
    
    Note: Column names use "_originations" suffix for compatibility with LendSight functions,
    but when action_taken includes applications (not just '1'), these columns actually
    represent applications, not just originations. The data is correct regardless of the label.
    
    Report Structure:
    - Section 1: Population Demographics (shared utility)
    - Section 2 (most recent 5 years): 
      - Table 1: Loans by Race and Ethnicity
      - Table 2: Loans by Borrower Income
      - Table 3: Loans by Neighborhood Income
      - Table 4: Loans by Neighborhood Demographics
    - Section 3 (top lenders - show top 10, expandable):
      - Table 1: Loans by Race and Ethnicity
      - Table 2: Loans by Borrower Income
      - Table 3: Loans by Neighborhood Income
      - Table 4: Loans by Neighborhood Demographics
    - Section 4:
      - Table 1: HHI Market Concentration
    
    Args:
        hmda_data: List of dictionaries from BigQuery results (same as LendSight raw_data)
        geoids: List of county GEOIDs
        years: List of years
        census_data: Optional census demographics data
        historical_census_data: Optional historical census data for chart
        progress_tracker: Optional progress tracker
        action_taken: Optional list of action_taken codes to track data type
        
    Returns:
        Dictionary with report data organized by sections
    """
    if not hmda_data:
        raise ValueError("No data provided for report building")
    
    # Initialize report_data dictionary
    report_data = {}
    
    # Track whether this is applications or originations for metadata
    is_applications = action_taken and set(action_taken) != {'1'}
    report_data['data_type'] = 'applications' if is_applications else 'originations'
    
    # Convert to DataFrame - exactly like LendSight does
    # Memory optimization: Use more efficient dtypes where possible
    df = pd.DataFrame(hmda_data)
    
    # Clean and prepare data - use LendSight's cleaning function
    from apps.lendsight.mortgage_report_builder import clean_mortgage_data
    df = clean_mortgage_data(df)
    
    # Split geoid5 into state_fips and county_fips for tract population data functions
    # geoid5 is a 5-digit code: first 2 digits = state FIPS, last 3 digits = county FIPS
    if 'geoid5' in df.columns and ('state_fips' not in df.columns or 'county_fips' not in df.columns):
        df['state_fips'] = df['geoid5'].astype(str).str[:2].astype(int)
        df['county_fips'] = df['geoid5'].astype(str).str[2:].astype(int)
        logger.info(f"[DEBUG] Split geoid5 into state_fips and county_fips")
    
    # Memory optimization: Delete original data after DataFrame creation
    del hmda_data
    import gc
    gc.collect()
    
    # Ensure required columns exist (same as LendSight)
    required_columns = ['lei', 'year', 'county_code', 'county_state', 'total_originations', 'lmict_originations', 'mmct_originations']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.warning(f"Missing required columns: {missing_columns}")
        # Don't raise error, just log warning - some columns might be optional
    
    logger.info(f"[DEBUG] DataFrame created. Shape: {df.shape}, Columns: {list(df.columns)}")
    if not df.empty:
        logger.info(f"[DEBUG] DataFrame sample: {df.head(1).to_dict('records')}")
        logger.info(f"[DEBUG] Years in DataFrame: {sorted(df['year'].unique()) if 'year' in df.columns else 'NO YEAR COLUMN'}")
        
        # Check for required race/ethnicity columns (same names as LendSight)
        race_columns = ['hispanic_originations', 'black_originations', 'white_originations', 
                       'asian_originations', 'native_american_originations', 'hopi_originations',
                       'multi_racial_originations']
        missing_race_cols = [col for col in race_columns if col not in df.columns]
        if missing_race_cols:
            logger.warning(f"[DEBUG] Missing race/ethnicity columns: {missing_race_cols}")
        else:
            logger.info(f"[DEBUG] All race/ethnicity columns present")
        
        # Check for lender column (same name as LendSight)
        lender_cols = [col for col in df.columns if 'lender' in col.lower() or 'respondent' in col.lower() or 'name' in col.lower()]
        logger.info(f"[DEBUG] Potential lender columns: {lender_cols}")
        if 'lender_name' not in df.columns:
            logger.warning(f"[DEBUG] 'lender_name' column NOT found. Available columns with 'name': {[col for col in df.columns if 'name' in col.lower()]}")
        
        # Check for required income columns
        income_cols = ['lmib_originations', 'low_income_borrower_originations', 'moderate_income_borrower_originations',
                      'middle_income_borrower_originations', 'upper_income_borrower_originations']
        missing_income_cols = [col for col in income_cols if col not in df.columns]
        if missing_income_cols:
            logger.warning(f"[DEBUG] Missing income columns: {missing_income_cols}")
        
        # Check for tract columns
        tract_cols = [col for col in df.columns if 'tract' in col.lower() or 'lmict' in col.lower() or 'mmct' in col.lower()]
        logger.info(f"[DEBUG] Tract-related columns: {tract_cols}")
    else:
        logger.warning(f"[DEBUG] DataFrame is EMPTY!")
    
    # Section 1: Population Demographics
    # This will be handled by the shared population demographics utility
    report_data['population_demographics'] = {
        'census_data': census_data,
        'historical_census_data': historical_census_data,
        'geoids': geoids
    }
    
    # Section 1: Table 2 - Loans by Loan Purpose Over Time
    # Aggregate loans by year and loan purpose
    if 'loan_purpose' in df.columns and not df.empty:
        loan_purpose_data = []
        for year in sorted(years):
            year_df = df[df['year'] == year]
            if not year_df.empty:
                # Map loan purpose codes to readable names
                # HMDA codes: 1=purchase, 31/32=refinance, 2/4=home equity
                purpose_map = {
                    '1': 'Home Purchase',
                    '31': 'Refinance',  # HMDA code 31 is refinance
                    '32': 'Refinance',  # HMDA code 32 is cash-out refinance
                    'purchase': 'Home Purchase',
                    'refinance': 'Refinance',
                    '2': 'Home Equity',  # HMDA code 2 is home equity
                    '4': 'Home Equity',  # HMDA code 4 is also home equity
                    'equity': 'Home Equity',
                    '3': 'Home Improvement',  # HMDA code 3 is home improvement
                    '33': 'Home Improvement',
                    '34': 'Home Improvement',
                    '5': 'Other',
                    '35': 'Other'
                }
                
                # Group by loan purpose
                purpose_totals = {}
                for purpose_code in year_df['loan_purpose'].unique():
                    purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
                    total = int(purpose_df['total_originations'].sum())
                    purpose_name = purpose_map.get(str(purpose_code), 'Other')
                    if purpose_name in purpose_totals:
                        purpose_totals[purpose_name] += total
                    else:
                        purpose_totals[purpose_name] = total
                
                # Only include the three main purposes
                loan_purpose_data.append({
                    'year': year,
                    'Home Purchase': purpose_totals.get('Home Purchase', 0),
                    'Refinance': purpose_totals.get('Refinance', 0),
                    'Home Equity': purpose_totals.get('Home Equity', 0)
                })
        
        report_data['loan_purpose_over_time'] = loan_purpose_data
    else:
        report_data['loan_purpose_over_time'] = []
    
    # Section 1: Table 3 - Loan Amounts by Loan Purpose Over Time
    # Aggregate loan amounts by year and loan purpose
    if 'loan_purpose' in df.columns and 'total_loan_amount' in df.columns and not df.empty:
        loan_amount_purpose_data = []
        for year in sorted(years):
            year_df = df[df['year'] == year]
            if not year_df.empty:
                # Map loan purpose codes to readable names (same as above)
                purpose_map = {
                    '1': 'Home Purchase',
                    '31': 'Refinance',
                    '32': 'Refinance',
                    'purchase': 'Home Purchase',
                    'refinance': 'Refinance',
                    '2': 'Home Equity',
                    '4': 'Home Equity',
                    'equity': 'Home Equity',
                    '3': 'Home Improvement',
                    '33': 'Home Improvement',
                    '34': 'Home Improvement',
                    '5': 'Other',
                    '35': 'Other'
                }
                
                # Group by loan purpose and sum loan amounts
                purpose_amounts = {}
                for purpose_code in year_df['loan_purpose'].unique():
                    purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
                    # Sum total_loan_amount (convert to int if needed)
                    total_amount = purpose_df['total_loan_amount'].sum()
                    if pd.notna(total_amount):
                        total_amount = int(total_amount)
                    else:
                        total_amount = 0
                    purpose_name = purpose_map.get(str(purpose_code), 'Other')
                    if purpose_name in purpose_amounts:
                        purpose_amounts[purpose_name] += total_amount
                    else:
                        purpose_amounts[purpose_name] = total_amount
                
                # Only include the three main purposes
                loan_amount_purpose_data.append({
                    'year': year,
                    'Home Purchase': purpose_amounts.get('Home Purchase', 0),
                    'Refinance': purpose_amounts.get('Refinance', 0),
                    'Home Equity': purpose_amounts.get('Home Equity', 0)
                })
        
        report_data['loan_amount_purpose_over_time'] = loan_amount_purpose_data
    else:
        report_data['loan_amount_purpose_over_time'] = []
    
    # Section 1: Tables 4-6 - Housing Data
    if progress_tracker:
        progress_tracker.update_progress('building_report', 65, 'Fetching housing data...')
    
    try:
        logger.info(f"[DEBUG] Starting housing data fetch for {len(geoids)} geoids: {geoids[:3]}...")
        housing_data = fetch_acs_housing_data(geoids)
        logger.info(f"[DEBUG] Fetched housing data for {len(housing_data)} counties")
        logger.info(f"[DEBUG] Housing data keys: {list(housing_data.keys())}")
        if housing_data:
            sample_geoid = list(housing_data.keys())[0]
            sample_data = housing_data[sample_geoid]
            logger.info(f"[DEBUG] Sample housing data for {sample_geoid}: time_periods keys = {list(sample_data.get('time_periods', {}).keys())}")
            for period_key, period_data in sample_data.get('time_periods', {}).items():
                logger.info(f"[DEBUG]   {period_key}: has {len(period_data)} fields")
        else:
            logger.warning(f"[DEBUG] No housing data returned from fetch_acs_housing_data!")
        
        # Table 4: Housing Costs
        logger.info(f"[DEBUG] Creating housing costs table with {len(housing_data)} counties...")
        report_data['housing_costs'] = create_housing_costs_table(housing_data, geoids)
        logger.info(f"[DEBUG] Housing costs table: {len(report_data['housing_costs'])} periods")
        if report_data['housing_costs']:
            logger.info(f"[DEBUG] Housing costs sample: {report_data['housing_costs'][0]}")
        
        # Table 5: Owner Occupancy
        logger.info(f"[DEBUG] Creating owner occupancy table...")
        report_data['owner_occupancy'] = create_owner_occupancy_table(
            housing_data, geoids, historical_census_data
        )
        logger.info(f"[DEBUG] Owner occupancy table: {len(report_data['owner_occupancy'])} periods")
        
        # Table 6: Housing Units
        logger.info(f"[DEBUG] Creating housing units table...")
        report_data['housing_units'] = create_housing_units_table(housing_data, geoids)
        logger.info(f"[DEBUG] Housing units table: {len(report_data['housing_units'])} periods")
        
        logger.info(f"Built housing tables: costs={len(report_data['housing_costs'])}, "
                   f"occupancy={len(report_data['owner_occupancy'])}, "
                   f"units={len(report_data['housing_units'])}")
    except Exception as e:
        logger.error(f"Error fetching/building housing tables: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        report_data['housing_costs'] = []
        report_data['owner_occupancy'] = []
        report_data['housing_units'] = []
    
    if progress_tracker:
        progress_tracker.update_progress('building_report', 70, 'Building Section 2 tables...')
    
    # Get HUD data for benchmark figures (check cache first)
    from apps.dataexplorer.cache_utils import load_hud_data, save_hud_data
    
    hud_data = load_hud_data(geoids)
    
    if hud_data is None:
        # Cache miss - fetch from HUD processor
        try:
            # get_hud_data_for_counties expects a list of GEOID5 strings
            hud_data = get_hud_data_for_counties(geoids)
            save_hud_data(geoids, hud_data)
            logger.info("Cached HUD data")
        except Exception as e:
            logger.warning(f"Error fetching HUD data: {e}")
            hud_data = {}
    
    # Section 2: Most recent 5 years - aggregate tables
    # Get most recent 5 years (already filtered in years list)
    recent_years = sorted(years)[-5:] if len(years) > 5 else years
    
    # Debug: Check DataFrame structure
    logger.info(f"[DEBUG] Building Section 2 tables")
    logger.info(f"[DEBUG] DataFrame shape: {df.shape}")
    logger.info(f"[DEBUG] DataFrame columns: {list(df.columns)}")
    logger.info(f"[DEBUG] Recent years: {recent_years}")
    recent_years_df = df[df['year'].isin(recent_years)]
    logger.info(f"[DEBUG] Recent years DataFrame shape: {recent_years_df.shape}")
    
    # Calculate quartile_shares once using full dataset (all loans) for Table 4
    # This ensures Population Share doesn't change when switching loan purpose tabs
    from apps.lendsight.mortgage_report_builder import (
        calculate_minority_quartiles, 
        classify_tract_minority_quartile,
        get_tract_population_data_for_counties
    )
    
    fixed_quartile_shares = {}
    fixed_tract_income_shares = {}  # For Table 3
    if not recent_years_df.empty and 'tract_minority_population_percent' in recent_years_df.columns:
        # Calculate quartiles from full dataset
        quartiles = calculate_minority_quartiles(recent_years_df)
        recent_years_df_copy = recent_years_df.copy()
        recent_years_df_copy['minority_quartile'] = recent_years_df_copy['tract_minority_population_percent'].apply(
            lambda x: classify_tract_minority_quartile(x, quartiles)
        )
        
        # Get tract population data
        tract_pop_data = get_tract_population_data_for_counties(recent_years_df_copy)
        
        # Calculate population shares from full dataset
        unique_tracts = recent_years_df_copy[['tract_code', 'minority_quartile', 'tract_minority_population_percent']].drop_duplicates()
        total_tracts = len(unique_tracts)
        
        if tract_pop_data and len(tract_pop_data) > 0:
            total_population = 0
            mmct_population = 0
            quartile_populations = {'low': 0, 'moderate': 0, 'middle': 0, 'high': 0}
            
            if 'state_fips' in recent_years_df_copy.columns and 'county_fips' in recent_years_df_copy.columns:
                tract_to_fips = recent_years_df_copy[['tract_code', 'state_fips', 'county_fips']].drop_duplicates()
                tract_fips_map = {}
                for _, row in tract_to_fips.iterrows():
                    tract_code_short = str(row['tract_code']).zfill(6)
                    state_fips = str(int(row['state_fips'])).zfill(2)
                    county_fips = str(int(row['county_fips'])).zfill(3)
                    full_tract_code = f"{state_fips}{county_fips}{tract_code_short}"
                    tract_fips_map[tract_code_short] = full_tract_code
                
                for _, tract_row in unique_tracts.iterrows():
                    tract_code_short = str(tract_row['tract_code']).zfill(6)
                    tract_minority_pct = tract_row['tract_minority_population_percent']
                    quartile = tract_row['minority_quartile']
                    
                    full_tract_code = tract_fips_map.get(tract_code_short)
                    if full_tract_code and full_tract_code in tract_pop_data:
                        pop = tract_pop_data[full_tract_code]['total_population']
                        total_population += pop
                        
                        if tract_minority_pct >= 50:
                            mmct_population += pop
                        
                        if quartile in quartile_populations:
                            quartile_populations[quartile] += pop
            
            if total_population > 0:
                fixed_quartile_shares['mmct'] = (mmct_population / total_population) * 100
                fixed_quartile_shares['low'] = (quartile_populations['low'] / total_population) * 100
                fixed_quartile_shares['moderate'] = (quartile_populations['moderate'] / total_population) * 100
                fixed_quartile_shares['middle'] = (quartile_populations['middle'] / total_population) * 100
                fixed_quartile_shares['high'] = (quartile_populations['high'] / total_population) * 100
            elif total_tracts > 0:
                # Fallback to tract distribution
                mmct_tracts = unique_tracts[unique_tracts['tract_minority_population_percent'] >= 50]
                fixed_quartile_shares['mmct'] = (len(mmct_tracts) / total_tracts * 100) if total_tracts > 0 else 0
                fixed_quartile_shares['low'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'low']) / total_tracts * 100
                fixed_quartile_shares['moderate'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'moderate']) / total_tracts * 100
                fixed_quartile_shares['middle'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'middle']) / total_tracts * 100
                fixed_quartile_shares['high'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'high']) / total_tracts * 100
        
        logger.info(f"[DEBUG] Calculated fixed quartile shares from full dataset: {fixed_quartile_shares}")
    
    # Calculate tract income shares once using full dataset (all loans) for Table 3
    # This ensures Population Share doesn't change when switching loan purpose tabs
    if not recent_years_df.empty and 'tract_to_msa_income_percentage' in recent_years_df.columns:
        # Get unique tracts with their income percentages
        unique_tracts_income = recent_years_df[['tract_code', 'tract_to_msa_income_percentage']].drop_duplicates()
        unique_tracts_income_clean = unique_tracts_income.dropna(subset=['tract_to_msa_income_percentage'])
        total_valid_tracts = len(unique_tracts_income_clean)
        
        if total_valid_tracts > 0:
            # Classify tracts by income level
            low_tracts = len(unique_tracts_income_clean[unique_tracts_income_clean['tract_to_msa_income_percentage'] <= 50])
            moderate_tracts = len(unique_tracts_income_clean[
                (unique_tracts_income_clean['tract_to_msa_income_percentage'] > 50) &
                (unique_tracts_income_clean['tract_to_msa_income_percentage'] <= 80)
            ])
            middle_tracts = len(unique_tracts_income_clean[
                (unique_tracts_income_clean['tract_to_msa_income_percentage'] > 80) &
                (unique_tracts_income_clean['tract_to_msa_income_percentage'] <= 120)
            ])
            upper_tracts = len(unique_tracts_income_clean[unique_tracts_income_clean['tract_to_msa_income_percentage'] > 120])
            
            # Calculate shares as percentage of total tracts
            fixed_tract_income_shares['low'] = (low_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
            fixed_tract_income_shares['moderate'] = (moderate_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
            fixed_tract_income_shares['lmict'] = fixed_tract_income_shares['low'] + fixed_tract_income_shares['moderate']
            fixed_tract_income_shares['middle'] = (middle_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
            fixed_tract_income_shares['upper'] = (upper_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
            
            logger.info(f"[DEBUG] Calculated fixed tract income shares from full dataset: {fixed_tract_income_shares}")
    
    # Generate tables for each loan purpose: all, purchase, refinance, equity
    loan_purposes = ['all', 'purchase', 'refinance', 'equity']
    section2_tables = {}
    
    for purpose in loan_purposes:
        logger.info(f"[DEBUG] Building Section 2 tables for loan purpose: {purpose}")
        purpose_df = filter_df_by_loan_purpose(recent_years_df, purpose)
        
        if purpose_df.empty:
            logger.warning(f"[DEBUG] No data for loan purpose: {purpose}")
            section2_tables[purpose] = {
                'loans_by_race_ethnicity': pd.DataFrame(),
                'loans_by_borrower_income': pd.DataFrame(),
                'loans_by_neighborhood_income': pd.DataFrame(),
                'loans_by_neighborhood_demographics': pd.DataFrame()
            }
            continue
        
        # Table 1: Loans by Race and Ethnicity
        race_columns = ['hispanic_originations', 'black_originations', 'white_originations', 
                       'asian_originations', 'native_american_originations', 'hopi_originations',
                       'multi_racial_originations']
        missing_race = [col for col in race_columns if col not in purpose_df.columns]
        if missing_race:
            logger.error(f"[DEBUG] CANNOT create demographic table for {purpose} - missing columns: {missing_race}")
            loans_by_race_ethnicity = pd.DataFrame()
        else:
            # Use historical_census_data if available, otherwise fall back to census_data
            # Both formats are supported by create_demographic_overview_table
            census_data_for_table = historical_census_data if historical_census_data else census_data
            if not census_data_for_table:
                logger.warning(f"[DEBUG] No census data available for demographic table (historical_census_data: {bool(historical_census_data)}, census_data: {bool(census_data)})")
            
            loans_by_race_ethnicity = create_demographic_overview_table(
                purpose_df, 
                recent_years, 
                census_data=census_data_for_table
            )
        
        # Table 2: Loans by Borrower Income
        loans_by_borrower_income = create_income_borrowers_table(
            purpose_df, 
            recent_years, 
            hud_data=hud_data
        )
        
        # Add income ranges to borrower income table labels
        if isinstance(loans_by_borrower_income, pd.DataFrame) and not loans_by_borrower_income.empty and 'Metric' in loans_by_borrower_income.columns:
            income_range_map = {
                'Low Income Borrowers': 'Low Income Borrowers (≤50% of AMFI)',
                'Moderate Income Borrowers': 'Moderate Income Borrowers (>50% and ≤80% of AMFI)',
                'Middle Income Borrowers': 'Middle Income Borrowers (>80% and ≤120% of AMFI)',
                'Upper Income Borrowers': 'Upper Income Borrowers (>120% of AMFI)',
                'Low to Moderate Income Borrowers': 'Low to Moderate Income Borrowers (≤80% of AMFI)'
            }
            loans_by_borrower_income['Metric'] = loans_by_borrower_income['Metric'].replace(income_range_map)
        
        # Table 3: Loans by Neighborhood Income
        loans_by_neighborhood_income = create_income_tracts_table(
            purpose_df, 
            recent_years, 
            hud_data=hud_data,
            census_data=census_data
        )
        
        # Add income ranges to neighborhood income table labels
        if isinstance(loans_by_neighborhood_income, pd.DataFrame) and not loans_by_neighborhood_income.empty and 'Metric' in loans_by_neighborhood_income.columns:
            tract_income_range_map = {
                'Low Income Census Tracts': 'Low Income Census Tracts (≤50% of AMFI)',
                'Moderate Income Census Tracts': 'Moderate Income Census Tracts (>50% and ≤80% of AMFI)',
                'Middle Income Census Tracts': 'Middle Income Census Tracts (>80% and ≤120% of AMFI)',
                'Upper Income Census Tracts': 'Upper Income Census Tracts (>120% of AMFI)',
                'Low to Moderate Income Census Tracts': 'Low to Moderate Income Census Tracts (≤80% of AMFI)'
            }
            loans_by_neighborhood_income['Metric'] = loans_by_neighborhood_income['Metric'].replace(tract_income_range_map)
        
        # Override Population Share column with fixed values from full dataset
        # This ensures Population Share doesn't change when switching loan purpose tabs
        if isinstance(loans_by_neighborhood_income, pd.DataFrame) and not loans_by_neighborhood_income.empty:
            if 'Population Share (%)' in loans_by_neighborhood_income.columns and fixed_tract_income_shares:
                # Map metric names to income share keys
                for idx, row in loans_by_neighborhood_income.iterrows():
                    metric = row['Metric']
                    # Extract income category from metric label
                    if 'Low to Moderate Income' in metric or 'LMI' in metric:
                        share_key = 'lmict'
                    elif 'Low Income' in metric and 'Moderate' not in metric:
                        share_key = 'low'
                    elif 'Moderate Income' in metric:
                        share_key = 'moderate'
                    elif 'Middle Income' in metric:
                        share_key = 'middle'
                    elif 'Upper Income' in metric:
                        share_key = 'upper'
                    else:
                        share_key = None
                    
                    if share_key and share_key in fixed_tract_income_shares:
                        loans_by_neighborhood_income.at[idx, 'Population Share (%)'] = f"{fixed_tract_income_shares[share_key]:.1f}%"
        
        # Table 4: Loans by Neighborhood Demographics
        # Use historical_census_data if available, otherwise fall back to census_data
        census_data_for_minority = historical_census_data if historical_census_data else census_data
        loans_by_neighborhood_demographics = create_minority_tracts_table(
            purpose_df, 
            recent_years, 
            census_data=census_data_for_minority
        )
        
        # Override Population Share column with fixed values from full dataset
        # This ensures Population Share doesn't change when switching loan purpose tabs
        if isinstance(loans_by_neighborhood_demographics, pd.DataFrame) and not loans_by_neighborhood_demographics.empty:
            if 'Population Share (%)' in loans_by_neighborhood_demographics.columns and fixed_quartile_shares:
                logger.info(f"[DEBUG] Overriding Population Share for Table 4 with fixed values: {fixed_quartile_shares}")
                # Map metric names to quartile share keys
                # Get quartile ranges for labels (from the table itself)
                for idx, row in loans_by_neighborhood_demographics.iterrows():
                    metric = row['Metric']
                    # Extract quartile from metric label (handle various formats)
                    share_key = None
                    if 'Low Minority' in metric:
                        share_key = 'low'
                    elif 'Moderate Minority' in metric:
                        share_key = 'moderate'
                    elif 'Middle Minority' in metric:
                        share_key = 'middle'
                    elif 'High Minority' in metric:
                        share_key = 'high'
                    elif 'Majority Minority' in metric:
                        share_key = 'mmct'
                    
                    if share_key and share_key in fixed_quartile_shares:
                        old_value = loans_by_neighborhood_demographics.at[idx, 'Population Share (%)']
                        new_value = f"{fixed_quartile_shares[share_key]:.1f}%"
                        loans_by_neighborhood_demographics.at[idx, 'Population Share (%)'] = new_value
                        logger.info(f"[DEBUG] Overrode Population Share for '{metric}': {old_value} -> {new_value}")
                    else:
                        logger.warning(f"[DEBUG] Could not find share_key for metric '{metric}' or share_key '{share_key}' not in fixed_quartile_shares")
        
        # Table 5: Loan Costs (new)
        loans_by_loan_costs = create_loan_costs_table(purpose_df, recent_years)
        
        section2_tables[purpose] = {
            'loans_by_race_ethnicity': loans_by_race_ethnicity,
            'loans_by_borrower_income': loans_by_borrower_income,
            'loans_by_neighborhood_income': loans_by_neighborhood_income,
            'loans_by_neighborhood_demographics': loans_by_neighborhood_demographics,
            'loans_by_loan_costs': loans_by_loan_costs
        }
    
    report_data['section2'] = {
        'years': recent_years,
        'by_purpose': section2_tables
    }
    
    if progress_tracker:
        progress_tracker.update_progress('building_report', 80, 'Building Section 3 (top lenders)...')
    
    # Section 3: Top lenders (top 10, expandable) - by loan purpose
    # Structure: Rows = Lenders, Columns = Metrics
    # Same 4 tables as Section 2, but transposed:
    # - Table 1: Loans by Race and Ethnicity (lenders as rows, race/ethnicity % as columns)
    # - Table 2: Loans by Borrower Income (lenders as rows, Low/Mod/Middle/Upper % as columns)
    # - Table 3: Loans by Neighborhood Income (lenders as rows, Low/Mod/Middle/Upper tract % as columns)
    # - Table 4: Loans by Neighborhood Demographics (lenders as rows, Low/Mod/Middle/High minority % as columns)
    
    # Generate tables for each loan purpose (top lenders may differ per purpose)
    logger.info(f"[DEBUG] Building Section 3 tables")
    latest_year = max(years)
    latest_year_df = df[df['year'] == latest_year].copy()
    
    # Check if lender_name column exists
    lender_col = None
    if 'lender_name' in latest_year_df.columns:
        lender_col = 'lender_name'
    else:
        for col in ['lender', 'name', 'respondent_name', 'respondent_name_clean']:
            if col in latest_year_df.columns:
                lender_col = col
                break
    
    if not lender_col:
        logger.error(f"[DEBUG] No lender column found. Cannot build Section 3 tables.")
        section3_tables = {}
        for purpose in loan_purposes:
            section3_tables[purpose] = {
                'top_lender_names': [],
                'loans_by_race_ethnicity': pd.DataFrame(),
                'loans_by_borrower_income': pd.DataFrame(),
                'loans_by_neighborhood_income': pd.DataFrame(),
                'loans_by_neighborhood_demographics': pd.DataFrame()
            }
    else:
        section3_tables = {}
        
        for purpose in loan_purposes:
            logger.info(f"[DEBUG] Building Section 3 tables for loan purpose: {purpose}")
            
            # Filter latest year data by loan purpose to get top lenders for this purpose
            purpose_latest_df = filter_df_by_loan_purpose(latest_year_df, purpose)
            
            if purpose_latest_df.empty or purpose_latest_df[lender_col].notna().sum() == 0:
                logger.warning(f"[DEBUG] No lender data for loan purpose: {purpose}")
                section3_tables[purpose] = {
                    'top_lender_names': [],
                    'loans_by_race_ethnicity': pd.DataFrame(),
                    'loans_by_borrower_income': pd.DataFrame(),
                    'loans_by_neighborhood_income': pd.DataFrame(),
                    'loans_by_neighborhood_demographics': pd.DataFrame(),
                    'loans_by_loan_costs': {}
                }
                continue
            
            # Get top 10 lenders for this loan purpose
            purpose_latest_df_clean = purpose_latest_df[purpose_latest_df[lender_col].notna()].copy()
            lender_totals = purpose_latest_df_clean.groupby(lender_col)['total_originations'].sum().reset_index()
            lender_totals = lender_totals.sort_values('total_originations', ascending=False)
            top_lender_names = lender_totals.head(10)[lender_col].tolist()
            logger.info(f"[DEBUG] Top {len(top_lender_names)} lenders for {purpose}: {top_lender_names[:3]}...")
            
            # Filter full DataFrame (all years) for these top lenders and this loan purpose
            purpose_df = filter_df_by_loan_purpose(df, purpose)
            if lender_col == 'lender_name':
                top_lenders_df = purpose_df[purpose_df['lender_name'].isin(top_lender_names)] if top_lender_names else pd.DataFrame()
            else:
                top_lenders_df = purpose_df[purpose_df[lender_col].isin(top_lender_names)] if top_lender_names else pd.DataFrame()
                if not top_lenders_df.empty and lender_col != 'lender_name':
                    top_lenders_df = top_lenders_df.rename(columns={lender_col: 'lender_name'})
            
            # Create lender-focused tables
            if top_lenders_df.empty:
                loans_by_race_ethnicity_lenders = pd.DataFrame()
                loans_by_borrower_income_lenders = pd.DataFrame()
                loans_by_neighborhood_income_lenders = pd.DataFrame()
                loans_by_neighborhood_demographics_lenders = pd.DataFrame()
                loans_by_loan_costs_lenders = {}
            else:
                # Use historical_census_data if available, otherwise fall back to census_data
                census_data_for_lenders = historical_census_data if historical_census_data else census_data
                loans_by_race_ethnicity_lenders = create_lender_race_ethnicity_table(
                    top_lenders_df, years, census_data=census_data_for_lenders
                )
                loans_by_borrower_income_lenders = create_lender_borrower_income_table(
                    top_lenders_df, years, hud_data=hud_data
                )
                loans_by_neighborhood_income_lenders = create_lender_neighborhood_income_table(
                    top_lenders_df, years, hud_data=hud_data, census_data=census_data_for_lenders
                )
                loans_by_neighborhood_demographics_lenders = create_lender_neighborhood_demographics_table(
                    top_lenders_df, years, census_data=census_data_for_lenders
                )
                
                # Table 5: Loan Costs by lender type (new)
                # Get top 10 lenders WITHIN each lender type for this loan purpose
                loans_by_loan_costs_lenders = {}
                if 'lender_type' in purpose_df.columns:
                    # Normalize lender_type values to match expected categories
                    # Map values like "Bank or Affiliate" -> "Bank", "Mortgage Company" -> "Mortgage Company", etc.
                    from apps.lendsight.mortgage_report_builder import map_lender_type
                    purpose_df_normalized = purpose_df.copy()
                    purpose_df_normalized['lender_type_normalized'] = purpose_df_normalized['lender_type'].apply(
                        lambda x: map_lender_type(x) if pd.notna(x) else ''
                    )
                    
                    # Map normalized values to display names
                    def normalize_to_display(normalized_type):
                        if normalized_type == 'Bank':
                            return 'Bank'
                        elif normalized_type == 'Mortgage':
                            return 'Mortgage Company'
                        elif normalized_type == 'Credit Union':
                            return 'Credit Union'
                        else:
                            return normalized_type
                    
                    purpose_df_normalized['lender_type_display'] = purpose_df_normalized['lender_type_normalized'].apply(normalize_to_display)
                    
                    # First, create "All Lenders" table with top 10 overall
                    purpose_latest_df = purpose_df_normalized[purpose_df_normalized['year'] == latest_year].copy()
                    if not purpose_latest_df.empty:
                        all_lender_totals = purpose_latest_df.groupby('lender_name')['total_originations'].sum().reset_index()
                        all_lender_totals = all_lender_totals.sort_values('total_originations', ascending=False)
                        top_all_lender_names = all_lender_totals.head(10)['lender_name'].tolist()
                        top_all_df = purpose_df_normalized[purpose_df_normalized['lender_name'].isin(top_all_lender_names)].copy()
                        # Drop normalized columns before passing to create_lender_loan_costs_table
                        top_all_df_clean = top_all_df.drop(columns=['lender_type_normalized', 'lender_type_display'], errors='ignore')
                        loans_by_loan_costs_lenders['All'] = create_lender_loan_costs_table(
                            top_all_df_clean, latest_year, lender_type=None
                        )
                    else:
                        loans_by_loan_costs_lenders['All'] = pd.DataFrame()
                    
                    # Then, get top 10 within each lender type
                    for lender_type_display in ['Bank', 'Mortgage Company', 'Credit Union']:
                        # Filter to this lender type for this loan purpose using normalized display name
                        type_df = purpose_df_normalized[purpose_df_normalized['lender_type_display'] == lender_type_display].copy()
                        
                        if not type_df.empty:
                            # Get top 10 lenders within this type for this loan purpose
                            type_latest_df = type_df[type_df['year'] == latest_year].copy()
                            if not type_latest_df.empty:
                                type_lender_totals = type_latest_df.groupby('lender_name')['total_originations'].sum().reset_index()
                                type_lender_totals = type_lender_totals.sort_values('total_originations', ascending=False)
                                top_type_lender_names = type_lender_totals.head(10)['lender_name'].tolist()
                                
                                # Filter to top 10 lenders within this type
                                top_type_df = type_df[type_df['lender_name'].isin(top_type_lender_names)].copy()
                                # Drop normalized columns before passing to create_lender_loan_costs_table
                                top_type_df_clean = top_type_df.drop(columns=['lender_type_normalized', 'lender_type_display'], errors='ignore')
                                
                                # Create table with top 10 lenders within this type
                                loans_by_loan_costs_lenders[lender_type_display] = create_lender_loan_costs_table(
                                    top_type_df_clean, latest_year, lender_type=None  # Already filtered by type
                                )
                            else:
                                loans_by_loan_costs_lenders[lender_type_display] = pd.DataFrame()
                        else:
                            loans_by_loan_costs_lenders[lender_type_display] = pd.DataFrame()
                else:
                    # If lender_type not available, get top 10 overall
                    if not purpose_df.empty:
                        purpose_latest_df = purpose_df[purpose_df['year'] == latest_year].copy()
                        if not purpose_latest_df.empty:
                            lender_totals = purpose_latest_df.groupby('lender_name')['total_originations'].sum().reset_index()
                            lender_totals = lender_totals.sort_values('total_originations', ascending=False)
                            top_lender_names = lender_totals.head(10)['lender_name'].tolist()
                            top_lenders_df = purpose_df[purpose_df['lender_name'].isin(top_lender_names)].copy()
                            loans_by_loan_costs_lenders['All'] = create_lender_loan_costs_table(
                                top_lenders_df, latest_year
                            )
                        else:
                            loans_by_loan_costs_lenders['All'] = pd.DataFrame()
                    else:
                        loans_by_loan_costs_lenders['All'] = pd.DataFrame()
            
            section3_tables[purpose] = {
                'top_lender_names': top_lender_names,
                'loans_by_race_ethnicity': loans_by_race_ethnicity_lenders,
                'loans_by_borrower_income': loans_by_borrower_income_lenders,
                'loans_by_neighborhood_income': loans_by_neighborhood_income_lenders,
                'loans_by_neighborhood_demographics': loans_by_neighborhood_demographics_lenders,
                'loans_by_loan_costs': loans_by_loan_costs_lenders
            }
    
    report_data['section3'] = {
        'years': years,
        'by_purpose': section3_tables
    }
    
    # Section 4: HHI Market Concentration by Loan Purpose
    # Calculate HHI separately for each loan purpose
    if progress_tracker:
        progress_tracker.update_progress('building_report', 90, 'Building Section 4 (HHI)...')
    
    hhi_by_year_purpose = []
    loan_purpose_map = {
        '1': 'Home Purchase',
        '31': 'Refinance',
        '32': 'Refinance',
        '2': 'Home Equity',
        '4': 'Home Equity'
    }
    
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        year_data = {'year': year}
        
        # Calculate HHI for each loan purpose
        for purpose_code, purpose_name in loan_purpose_map.items():
            purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
            if not purpose_df.empty:
                hhi_result = calculate_mortgage_hhi_for_year(purpose_df, year)
                year_data[purpose_name] = hhi_result['hhi'] if hhi_result['hhi'] is not None else None
            else:
                year_data[purpose_name] = None
        
        hhi_by_year_purpose.append(year_data)
    
    report_data['section4'] = {
        'hhi_by_year_purpose': hhi_by_year_purpose
    }
    
    logger.info(f"[DEBUG] Created section4 with {len(hhi_by_year_purpose)} years of HHI data")
    logger.info(f"[DEBUG] Section4 keys: {list(report_data['section4'].keys())}")
    logger.info(f"[DEBUG] Sample HHI data: {hhi_by_year_purpose[0] if hhi_by_year_purpose else 'None'}")
    
    return report_data


def build_area_report_all_lenders(
    hmda_data: List[Dict[str, Any]],
    geoids: List[str],
    years: List[int],
    census_data: Dict = None,
    historical_census_data: Dict = None,
    hud_data: Dict = None,
    progress_tracker=None,
    action_taken: List[str] = None
) -> Dict[str, Any]:
    """
    Build area analysis report with ALL lenders (not just top 10) for Excel export.
    
    This is identical to build_area_report except Section 3 includes all lenders.
    """
    # Reuse the main build_area_report function but override Section 3
    report_data = build_area_report(
        hmda_data=hmda_data,
        geoids=geoids,
        years=years,
        census_data=census_data,
        historical_census_data=historical_census_data,
        progress_tracker=progress_tracker,
        action_taken=action_taken
    )
    
    # Now rebuild Section 3 with ALL lenders
    import pandas as pd
    from apps.lendsight.mortgage_report_builder import clean_mortgage_data
    
    # Convert to DataFrame
    df = pd.DataFrame(hmda_data)
    if df.empty:
        return report_data
    
    # Clean data
    df = clean_mortgage_data(df)
    
    # Get HUD data if not provided
    if hud_data is None:
        from apps.lendsight.hud_processor import get_hud_data_for_counties
        from apps.dataexplorer.cache_utils import load_hud_data, save_hud_data
        hud_data = load_hud_data(geoids)
        if hud_data is None:
            try:
                hud_data = get_hud_data_for_counties(geoids)
                save_hud_data(geoids, hud_data)
            except Exception as e:
                logger.warning(f"Error fetching HUD data: {e}")
                hud_data = {}
    
    # Rebuild Section 3 with ALL lenders (not just top 10)
    logger.info(f"[DEBUG] Building Section 3 tables with ALL lenders for Excel export")
    latest_year = max(years)
    latest_year_df = df[df['year'] == latest_year].copy()
    
    # Check if lender_name column exists
    lender_col = None
    if 'lender_name' in latest_year_df.columns:
        lender_col = 'lender_name'
    else:
        for col in ['lender', 'name', 'respondent_name', 'respondent_name_clean']:
            if col in latest_year_df.columns:
                lender_col = col
                break
    
    if not lender_col:
        logger.error(f"[DEBUG] No lender column found. Cannot build Section 3 tables with all lenders.")
        return report_data
    
    # Generate tables for each loan purpose with ALL lenders
    loan_purposes = ['all', 'purchase', 'refinance', 'equity']
    section3_tables_all = {}
    
    for purpose in loan_purposes:
        logger.info(f"[DEBUG] Building Section 3 tables for loan purpose: {purpose} (ALL lenders)")
        
        # Filter latest year data by loan purpose
        purpose_latest_df = filter_df_by_loan_purpose(latest_year_df, purpose)
        
        if purpose_latest_df.empty or purpose_latest_df[lender_col].notna().sum() == 0:
            logger.warning(f"[DEBUG] No lender data for loan purpose: {purpose}")
            section3_tables_all[purpose] = {
                'top_lender_names': [],
                'loans_by_race_ethnicity': pd.DataFrame(),
                'loans_by_borrower_income': pd.DataFrame(),
                'loans_by_neighborhood_income': pd.DataFrame(),
                'loans_by_neighborhood_demographics': pd.DataFrame()
            }
            continue
        
        # Get ALL lenders for this loan purpose (not just top 10)
        purpose_latest_df_clean = purpose_latest_df[purpose_latest_df[lender_col].notna()].copy()
        lender_totals = purpose_latest_df_clean.groupby(lender_col)['total_originations'].sum().reset_index()
        lender_totals = lender_totals.sort_values('total_originations', ascending=False)
        all_lender_names = lender_totals[lender_col].tolist()  # ALL lenders, not just top 10
        logger.info(f"[DEBUG] Found {len(all_lender_names)} total lenders for {purpose}")
        
        # Filter full DataFrame (all years) for ALL lenders and this loan purpose
        purpose_df = filter_df_by_loan_purpose(df, purpose)
        if lender_col == 'lender_name':
            all_lenders_df = purpose_df[purpose_df['lender_name'].isin(all_lender_names)] if all_lender_names else pd.DataFrame()
        else:
            all_lenders_df = purpose_df[purpose_df[lender_col].isin(all_lender_names)] if all_lender_names else pd.DataFrame()
            if not all_lenders_df.empty and lender_col != 'lender_name':
                all_lenders_df = all_lenders_df.rename(columns={lender_col: 'lender_name'})
        
        # Create lender-focused tables with ALL lenders
        if all_lenders_df.empty:
            loans_by_race_ethnicity_lenders = pd.DataFrame()
            loans_by_borrower_income_lenders = pd.DataFrame()
            loans_by_neighborhood_income_lenders = pd.DataFrame()
            loans_by_neighborhood_demographics_lenders = pd.DataFrame()
        else:
            loans_by_race_ethnicity_lenders = create_lender_race_ethnicity_table(
                all_lenders_df, years, census_data=census_data
            )
            loans_by_borrower_income_lenders = create_lender_borrower_income_table(
                all_lenders_df, years, hud_data=hud_data
            )
            loans_by_neighborhood_income_lenders = create_lender_neighborhood_income_table(
                all_lenders_df, years, hud_data=hud_data, census_data=census_data
            )
            loans_by_neighborhood_demographics_lenders = create_lender_neighborhood_demographics_table(
                all_lenders_df, years, census_data=census_data
            )
        
        section3_tables_all[purpose] = {
            'top_lender_names': all_lender_names,  # All lender names
            'loans_by_race_ethnicity': loans_by_race_ethnicity_lenders,
            'loans_by_borrower_income': loans_by_borrower_income_lenders,
            'loans_by_neighborhood_income': loans_by_neighborhood_income_lenders,
            'loans_by_neighborhood_demographics': loans_by_neighborhood_demographics_lenders
        }
    
    # Replace Section 3 with all lenders data
    report_data['section3'] = {
        'years': years,
        'by_purpose': section3_tables_all
    }
    
    # Section 4: HHI Market Concentration by Loan Purpose
    # Calculate HHI separately for each loan purpose
    if progress_tracker:
        progress_tracker.update_progress('building_report', 90, 'Building Section 4 (HHI)...')
    
    hhi_by_year_purpose = []
    loan_purpose_map = {
        '1': 'Home Purchase',
        '31': 'Refinance',
        '32': 'Refinance',
        '2': 'Home Equity',
        '4': 'Home Equity'
    }
    
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        year_data = {'year': year}
        
        # Calculate HHI for each loan purpose
        for purpose_code, purpose_name in loan_purpose_map.items():
            purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
            if not purpose_df.empty:
                hhi_result = calculate_mortgage_hhi_for_year(purpose_df, year)
                year_data[purpose_name] = hhi_result['hhi'] if hhi_result['hhi'] is not None else None
            else:
                year_data[purpose_name] = None
        
        hhi_by_year_purpose.append(year_data)
    
    report_data['section4'] = {
        'hhi_by_year_purpose': hhi_by_year_purpose
    }
    
    logger.info(f"[DEBUG] Created section4 with {len(hhi_by_year_purpose)} years of HHI data")
    logger.info(f"[DEBUG] Section4 keys: {list(report_data['section4'].keys())}")
    logger.info(f"[DEBUG] Sample HHI data: {hhi_by_year_purpose[0] if hhi_by_year_purpose else 'None'}")
    
    return report_data
    
    # Convert DataFrames to JSON-serializable format for template rendering
    import numpy as np
    
    def convert_numpy_types(obj):
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    # Convert Section 2 tables (nested by loan purpose)
    if 'section2' in report_data and 'by_purpose' in report_data['section2']:
        section2 = report_data['section2']
        for purpose, tables in section2['by_purpose'].items():
            for table_name in ['loans_by_race_ethnicity', 'loans_by_borrower_income', 
                              'loans_by_neighborhood_income', 'loans_by_neighborhood_demographics']:
                if isinstance(tables.get(table_name), pd.DataFrame):
                    tables[table_name] = convert_numpy_types(
                        tables[table_name].to_dict('records')
                        if not tables[table_name].empty else []
                    )
    
    # Convert Section 3 tables (nested by loan purpose)
    if 'section3' in report_data and 'by_purpose' in report_data['section3']:
        section3 = report_data['section3']
        for purpose, tables in section3['by_purpose'].items():
            for table_name in ['loans_by_race_ethnicity', 'loans_by_borrower_income', 
                              'loans_by_neighborhood_income', 'loans_by_neighborhood_demographics']:
                if isinstance(tables.get(table_name), pd.DataFrame):
                    tables[table_name] = convert_numpy_types(
                        tables[table_name].to_dict('records')
                        if not tables[table_name].empty else []
                    )
    
    # Convert Section 4 HHI data
    if 'section4' in report_data and 'hhi_by_year_purpose' in report_data['section4']:
        report_data['section4']['hhi_by_year_purpose'] = convert_numpy_types(report_data['section4']['hhi_by_year_purpose'])
        logger.info(f"[DEBUG] Converted section4 HHI data, {len(report_data['section4']['hhi_by_year_purpose'])} years")
    else:
        logger.warning(f"[DEBUG] Section4 not found or missing hhi_by_year_purpose! report_data keys: {list(report_data.keys())}")
        if 'section4' in report_data:
            logger.warning(f"[DEBUG] Section4 keys: {list(report_data['section4'].keys())}")
    
    logger.info(f"[DEBUG] Final report_data keys before return: {list(report_data.keys())}")
    return report_data


def create_lender_race_ethnicity_table(df: pd.DataFrame, years: List[int], census_data: Dict = None) -> pd.DataFrame:
    """
    Create loans by race and ethnicity table with lenders as rows.
    
    Structure: Rows = Lenders, Columns = Race/Ethnicity percentages
    Only includes race/ethnicity categories that are >= 1% of total loans across all lenders.
    """
    if df.empty or 'lender_name' not in df.columns:
        return pd.DataFrame()
    
    # First, calculate total loans across all lenders to determine which races are >= 1%
    # Threshold uses total_originations (which contains applications when action_taken includes 1-5,
    # or originations when action_taken is just '1')
    total_all_loans = int(df['total_originations'].sum())
    
    # Calculate total for each race category across all lenders
    total_hispanic = int(df['hispanic_originations'].sum())
    total_black = int(df['black_originations'].sum())
    total_white = int(df['white_originations'].sum())
    total_asian = int(df['asian_originations'].sum())
    total_native_american = int(df['native_american_originations'].sum())
    total_hopi = int(df['hopi_originations'].sum())
    total_multi_racial = int(df['multi_racial_originations'].sum()) if 'multi_racial_originations' in df.columns else 0
    
    # Calculate percentages for threshold check (1% of all applications/originations)
    race_percentages = {
        'White (%)': (total_white / total_all_loans * 100) if total_all_loans > 0 else 0,
        'Hispanic (%)': (total_hispanic / total_all_loans * 100) if total_all_loans > 0 else 0,
        'Black (%)': (total_black / total_all_loans * 100) if total_all_loans > 0 else 0,
        'Asian (%)': (total_asian / total_all_loans * 100) if total_all_loans > 0 else 0,
        'Native American (%)': (total_native_american / total_all_loans * 100) if total_all_loans > 0 else 0,
        'Hawaiian/Pacific Islander (%)': (total_hopi / total_all_loans * 100) if total_all_loans > 0 else 0,
        'Multi-Racial (non-Hispanic and two or more races) (%)': (total_multi_racial / total_all_loans * 100) if total_all_loans > 0 else 0
    }
    
    # Filter to only include races >= 1%
    included_races = {k: v for k, v in race_percentages.items() if v >= 1.0}
    
    # Aggregate across all years for each lender
    lender_data = []
    for lender_name in df['lender_name'].unique():
        lender_df = df[df['lender_name'] == lender_name]
        
        total = int(lender_df['total_originations'].sum())
        loans_with_demo = int(lender_df['loans_with_demographic_data'].sum()) if 'loans_with_demographic_data' in lender_df.columns else total
        
        hispanic = int(lender_df['hispanic_originations'].sum())
        black = int(lender_df['black_originations'].sum())
        white = int(lender_df['white_originations'].sum())
        asian = int(lender_df['asian_originations'].sum())
        native_american = int(lender_df['native_american_originations'].sum())
        hopi = int(lender_df['hopi_originations'].sum())
        multi_racial = int(lender_df['multi_racial_originations'].sum()) if 'multi_racial_originations' in lender_df.columns else 0
        
        denominator = loans_with_demo if loans_with_demo > 0 else total
        
        # Get lender type if available
        lender_type = ''
        if 'lender_type' in lender_df.columns:
            lender_type_values = lender_df['lender_type'].dropna().unique()
            if len(lender_type_values) > 0:
                # Use the most common lender type for this lender
                from apps.lendsight.mortgage_report_builder import map_lender_type
                lender_type_mapped = map_lender_type(lender_type_values[0]) if pd.notna(lender_type_values[0]) else ''
                # Normalize to display name
                if lender_type_mapped in ['Bank', 'Credit Union', 'Mortgage Company']:
                    lender_type = lender_type_mapped
                elif lender_type_mapped:
                    lender_type = 'Other'
        
        # Build lender row with only included races
        lender_row = {
            'Lender': lender_name,
            'Total Loans': f"{total:,}",
            'Lender Type': lender_type
        }
        
        # Add only races that are >= 1% of total loans
        if 'White (%)' in included_races:
            lender_row['White (%)'] = f"{(white / denominator * 100) if denominator > 0 else 0:.1f}"
        if 'Hispanic (%)' in included_races:
            lender_row['Hispanic (%)'] = f"{(hispanic / denominator * 100) if denominator > 0 else 0:.1f}"
        if 'Black (%)' in included_races:
            lender_row['Black (%)'] = f"{(black / denominator * 100) if denominator > 0 else 0:.1f}"
        if 'Asian (%)' in included_races:
            lender_row['Asian (%)'] = f"{(asian / denominator * 100) if denominator > 0 else 0:.1f}"
        if 'Native American (%)' in included_races:
            lender_row['Native American (%)'] = f"{(native_american / denominator * 100) if denominator > 0 else 0:.1f}"
        if 'Hawaiian/Pacific Islander (%)' in included_races:
            lender_row['Hawaiian/Pacific Islander (%)'] = f"{(hopi / denominator * 100) if denominator > 0 else 0:.1f}"
        if 'Multi-Racial (non-Hispanic and two or more races) (%)' in included_races:
            lender_row['Multi-Racial (non-Hispanic and two or more races) (%)'] = f"{(multi_racial / denominator * 100) if denominator > 0 else 0:.1f}"
        
        lender_data.append(lender_row)
    
    # Sort by total loans descending
    lender_data.sort(key=lambda x: int(x['Total Loans'].replace(',', '')), reverse=True)
    
    return pd.DataFrame(lender_data)


def create_lender_borrower_income_table(df: pd.DataFrame, years: List[int], hud_data: Dict = None) -> pd.DataFrame:
    """
    Create loans by borrower income table with lenders as rows.
    
    Structure: Rows = Lenders, Columns = Income category percentages (Low/Mod/Middle/Upper)
    """
    if df.empty or 'lender_name' not in df.columns:
        return pd.DataFrame()
    
    required_cols = ['lender_name', 'total_originations', 'lmib_originations', 
                     'low_income_borrower_originations', 'moderate_income_borrower_originations',
                     'middle_income_borrower_originations', 'upper_income_borrower_originations']
    
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()
    
    lender_data = []
    for lender_name in df['lender_name'].unique():
        lender_df = df[df['lender_name'] == lender_name]
        
        total = int(lender_df['total_originations'].sum())
        lmib = int(lender_df['lmib_originations'].sum())
        low = int(lender_df['low_income_borrower_originations'].sum())
        moderate = int(lender_df['moderate_income_borrower_originations'].sum())
        middle = int(lender_df['middle_income_borrower_originations'].sum())
        upper = int(lender_df['upper_income_borrower_originations'].sum())
        
        denominator = total if total > 0 else 1
        
        # Low & Mod (LMI) should equal Low + Moderate
        # Calculate it as the sum to ensure mathematical consistency
        lmib_calculated = low + moderate
        
        # Log if there's a discrepancy (for debugging)
        if abs(lmib_calculated - lmib) > 1:  # Allow 1 loan difference for rounding
            logger.warning(f"Lender {lender_name}: LMI calculation mismatch - SQL lmib={lmib}, calculated (Low+Mod)={lmib_calculated}. Using calculated value.")
        
        # Get lender type if available
        lender_type = ''
        if 'lender_type' in lender_df.columns:
            lender_type_values = lender_df['lender_type'].dropna().unique()
            if len(lender_type_values) > 0:
                from apps.lendsight.mortgage_report_builder import map_lender_type
                lender_type_mapped = map_lender_type(lender_type_values[0]) if pd.notna(lender_type_values[0]) else ''
                if lender_type_mapped in ['Bank', 'Credit Union', 'Mortgage Company']:
                    lender_type = lender_type_mapped
                elif lender_type_mapped:
                    lender_type = 'Other'
        
        # Use calculated value (Low + Mod) for Low & Mod to ensure math is correct
        lender_data.append({
            'Lender': lender_name,
            'Total Loans': f"{total:,}",
            'Lender Type': lender_type,
            'Low to Moderate Income Borrowers (%) (≤80% of AMFI)': f"{(lmib_calculated / denominator * 100) if denominator > 0 else 0:.1f}",
            'Low Income Borrowers (%) (≤50% of AMFI)': f"{(low / denominator * 100) if denominator > 0 else 0:.1f}",
            'Moderate Income Borrowers (%) (>50% and ≤80% of AMFI)': f"{(moderate / denominator * 100) if denominator > 0 else 0:.1f}",
            'Middle Income Borrowers (%) (>80% and ≤120% of AMFI)': f"{(middle / denominator * 100) if denominator > 0 else 0:.1f}",
            'Upper Income Borrowers (%) (>120% of AMFI)': f"{(upper / denominator * 100) if denominator > 0 else 0:.1f}"
        })
    
    lender_data.sort(key=lambda x: int(x['Total Loans'].replace(',', '')), reverse=True)
    
    return pd.DataFrame(lender_data)


def create_lender_neighborhood_income_table(df: pd.DataFrame, years: List[int], 
                                           hud_data: Dict = None, census_data: Dict = None) -> pd.DataFrame:
    """
    Create loans by neighborhood income table with lenders as rows.
    
    Structure: Rows = Lenders, Columns = Tract income category percentages (Low/Mod/Middle/Upper)
    """
    if df.empty or 'lender_name' not in df.columns:
        return pd.DataFrame()
    
    required_cols = ['lender_name', 'total_originations', 'lmict_originations',
                     'low_income_tract_originations', 'moderate_income_tract_originations',
                     'middle_income_tract_originations', 'upper_income_tract_originations']
    
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()
    
    lender_data = []
    for lender_name in df['lender_name'].unique():
        lender_df = df[df['lender_name'] == lender_name]
        
        total = int(lender_df['total_originations'].sum())
        lmict = int(lender_df['lmict_originations'].sum())
        low_tract = int(lender_df['low_income_tract_originations'].sum())
        moderate_tract = int(lender_df['moderate_income_tract_originations'].sum())
        middle_tract = int(lender_df['middle_income_tract_originations'].sum())
        upper_tract = int(lender_df['upper_income_tract_originations'].sum())
        
        denominator = total if total > 0 else 1
        
        # Low & Mod (LMI) should equal Low + Moderate
        # Calculate it as the sum to ensure mathematical consistency
        lmict_calculated = low_tract + moderate_tract
        
        # Log if there's a discrepancy (for debugging)
        if abs(lmict_calculated - lmict) > 1:  # Allow 1 loan difference for rounding
            logger.warning(f"Lender {lender_name}: LMICT calculation mismatch - SQL lmict={lmict}, calculated (Low+Mod)={lmict_calculated}. Using calculated value.")
        
        # Get lender type if available
        lender_type = ''
        if 'lender_type' in lender_df.columns:
            lender_type_values = lender_df['lender_type'].dropna().unique()
            if len(lender_type_values) > 0:
                from apps.lendsight.mortgage_report_builder import map_lender_type
                lender_type_mapped = map_lender_type(lender_type_values[0]) if pd.notna(lender_type_values[0]) else ''
                if lender_type_mapped in ['Bank', 'Credit Union', 'Mortgage Company']:
                    lender_type = lender_type_mapped
                elif lender_type_mapped:
                    lender_type = 'Other'
        
        # Use calculated value (Low + Mod) for Low & Mod to ensure math is correct
        lender_data.append({
            'Lender': lender_name,
            'Total Loans': f"{total:,}",
            'Lender Type': lender_type,
            'Low to Moderate Income Census Tracts (%) (≤80% of AMFI)': f"{(lmict_calculated / denominator * 100) if denominator > 0 else 0:.1f}",
            'Low Income Census Tracts (%) (≤50% of AMFI)': f"{(low_tract / denominator * 100) if denominator > 0 else 0:.1f}",
            'Moderate Income Census Tracts (%) (>50% and ≤80% of AMFI)': f"{(moderate_tract / denominator * 100) if denominator > 0 else 0:.1f}",
            'Middle Income Census Tracts (%) (>80% and ≤120% of AMFI)': f"{(middle_tract / denominator * 100) if denominator > 0 else 0:.1f}",
            'Upper Income Census Tracts (%) (>120% of AMFI)': f"{(upper_tract / denominator * 100) if denominator > 0 else 0:.1f}"
        })
    
    lender_data.sort(key=lambda x: int(x['Total Loans'].replace(',', '')), reverse=True)
    
    return pd.DataFrame(lender_data)


def create_lender_neighborhood_demographics_table(df: pd.DataFrame, years: List[int], 
                                                  census_data: Dict = None) -> pd.DataFrame:
    """
    Create loans by neighborhood demographics table with lenders as rows.
    
    Structure: Rows = Lenders, Columns = Minority quartile percentages (Low/Mod/Middle/High, MMCT)
    """
    if df.empty or 'lender_name' not in df.columns:
        return pd.DataFrame()
    
    required_cols = ['lender_name', 'total_originations', 'mmct_originations',
                     'tract_minority_population_percent', 'tract_code']
    
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()
    
    # Calculate minority quartiles (same as create_minority_tracts_table)
    from apps.lendsight.mortgage_report_builder import calculate_minority_quartiles, classify_tract_minority_quartile
    
    quartiles = calculate_minority_quartiles(df)
    df['minority_quartile'] = df['tract_minority_population_percent'].apply(
        lambda x: classify_tract_minority_quartile(x, quartiles)
    )
    
    lender_data = []
    for lender_name in df['lender_name'].unique():
        lender_df = df[df['lender_name'] == lender_name]
        
        total = int(lender_df['total_originations'].sum())
        mmct = int(lender_df['mmct_originations'].sum())
        
        low_minority = int(lender_df[lender_df['minority_quartile'] == 'low']['total_originations'].sum())
        moderate_minority = int(lender_df[lender_df['minority_quartile'] == 'moderate']['total_originations'].sum())
        middle_minority = int(lender_df[lender_df['minority_quartile'] == 'middle']['total_originations'].sum())
        high_minority = int(lender_df[lender_df['minority_quartile'] == 'high']['total_originations'].sum())
        
        denominator = total if total > 0 else 1
        
        # Format quartile ranges
        q25_str = f"{quartiles['q25']:.1f}%"
        q50_str = f"{quartiles['q50']:.1f}%"
        q75_str = f"{quartiles['q75']:.1f}%"
        
        # Get lender type if available
        lender_type = ''
        if 'lender_type' in lender_df.columns:
            lender_type_values = lender_df['lender_type'].dropna().unique()
            if len(lender_type_values) > 0:
                from apps.lendsight.mortgage_report_builder import map_lender_type
                lender_type_mapped = map_lender_type(lender_type_values[0]) if pd.notna(lender_type_values[0]) else ''
                if lender_type_mapped in ['Bank', 'Credit Union', 'Mortgage Company']:
                    lender_type = lender_type_mapped
                elif lender_type_mapped:
                    lender_type = 'Other'
        
        # Order: Majority Minority first, then Low, Moderate, Middle, High Minority
        # Remove "Census Tracts" from column names (will be added as grouped header in frontend)
        lender_data.append({
            'Lender': lender_name,
            'Total Loans': f"{total:,}",
            'Lender Type': lender_type,
            'Majority Minority (%)': f"{(mmct / denominator * 100):.1f}",
            f'Low Minority (0-{q25_str}) (%)': f"{(low_minority / denominator * 100):.1f}",
            f'Moderate Minority ({q25_str}-{q50_str}) (%)': f"{(moderate_minority / denominator * 100):.1f}",
            f'Middle Minority ({q50_str}-{q75_str}) (%)': f"{(middle_minority / denominator * 100):.1f}",
            f'High Minority ({q75_str}-100%) (%)': f"{(high_minority / denominator * 100):.1f}"
        })
    
    lender_data.sort(key=lambda x: int(x['Total Loans'].replace(',', '')), reverse=True)
    
    return pd.DataFrame(lender_data)

