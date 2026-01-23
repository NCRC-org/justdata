 #!/usr/bin/env python3
"""
BizSight Report Builder
Creates formatted tables for BizSight reports.
"""

import pandas as pd
from typing import List, Dict, Optional
import numpy as np


def safe_int(value, default=0):
    """Safely convert value to int, handling pd.NA and None."""
    if pd.isna(value) or value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """Safely convert value to float, handling pd.NA and None."""
    if pd.isna(value) or value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def create_county_summary_table(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """
    Create county-level summary table for Section 2 (2018-2024).
    
    Shows aggregate data for the whole county across all years.
    
    Args:
        df: DataFrame from aggregate table query (tract-level data)
        years: List of years to aggregate
    
    Returns:
        DataFrame with one row per variable showing county totals by year
    """
    if df.empty:
        return pd.DataFrame()
    
    # Filter to specified years - handle both string and int year values
    if 'year' in df.columns:
        # Convert year column to string for consistent comparison
        df_year_str = df['year'].astype(str)
        year_df = df[df_year_str.isin([str(y) for y in years])].copy()
    else:
        year_df = pd.DataFrame()
    
    if year_df.empty:
        print(f"DEBUG: create_county_summary_table: No data for years {years}")
        return pd.DataFrame()
    
    # Create table rows - one row per variable, with columns for each year
    table_rows = []
    year_data_dict = {}  # Use local dict instead of function attribute
    
    for year in sorted(years):
        # Handle both string and int year values
        year_str = str(year)
        if df['year'].dtype in ['int64', 'int32', 'int']:
            year_data = year_df[year_df['year'] == year].copy()
        else:
            year_df_year_str = year_df['year'].astype(str)
            year_data = year_df[year_df_year_str == year_str].copy()
        
        if year_data.empty:
            print(f"DEBUG: create_county_summary_table: No data for year {year}")
            continue
        
        # Sum numeric fields for this year
        num_under_100k = safe_int(year_data.get('num_under_100k', pd.Series([0])).sum())
        num_100k_250k = safe_int(year_data.get('num_100k_250k', pd.Series([0])).sum())
        num_250k_1m = safe_int(year_data.get('num_250k_1m', pd.Series([0])).sum())
        
        amt_under_100k = safe_float(year_data.get('amt_under_100k', pd.Series([0.0])).sum())
        amt_100k_250k = safe_float(year_data.get('amt_100k_250k', pd.Series([0.0])).sum())
        amt_250k_1m = safe_float(year_data.get('amt_250k_1m', pd.Series([0.0])).sum())
        
        numsb_col = 'numsbrev_under_1m' if 'numsbrev_under_1m' in year_data.columns else 'numsb_under_1m'
        amtsb_col = 'amtsbrev_under_1m' if 'amtsbrev_under_1m' in year_data.columns else 'amtsb_under_1m'
        numsbrev_under_1m = safe_int(year_data.get(numsb_col, pd.Series([0])).sum())
        amtsbrev_under_1m = safe_float(year_data.get(amtsb_col, pd.Series([0.0])).sum())
        
        # Calculate totals
        num_total = num_under_100k + num_100k_250k + num_250k_1m
        amt_total = amt_under_100k + amt_100k_250k + amt_250k_1m
        
        # Calculate LMI Tract percentage
        if 'is_lmi_tract' in year_data.columns:
            lmi_mask = (year_data['is_lmi_tract'] == 1) | (year_data['is_lmi_tract'] == True) | (year_data['is_lmi_tract'].astype(str) == '1')
            lmi_tract_loans = safe_int(year_data[lmi_mask].get('loan_count', pd.Series([0])).sum())
            lmi_tract_amount = safe_float(year_data[lmi_mask].get('loan_amount', pd.Series([0.0])).sum())
        else:
            lmi_tract_loans = 0
            lmi_tract_amount = 0.0
        
        lmi_tract_pct = (lmi_tract_loans / num_total * 100) if num_total > 0 else 0.0
        amt_lmi_tract_pct = (lmi_tract_amount / amt_total * 100) if amt_total > 0 else 0.0
        
        # Calculate percentages
        num_under_100k_pct = (num_under_100k / num_total * 100) if num_total > 0 else 0.0
        num_100k_250k_pct = (num_100k_250k / num_total * 100) if num_total > 0 else 0.0
        num_250k_1m_pct = (num_250k_1m / num_total * 100) if num_total > 0 else 0.0
        numsb_under_1m_pct = (numsbrev_under_1m / num_total * 100) if num_total > 0 else 0.0
        
        amt_under_100k_pct = (amt_under_100k / amt_total * 100) if amt_total > 0 else 0.0
        amt_100k_250k_pct = (amt_100k_250k / amt_total * 100) if amt_total > 0 else 0.0
        amt_250k_1m_pct = (amt_250k_1m / amt_total * 100) if amt_total > 0 else 0.0
        amtsb_under_1m_pct = (amtsbrev_under_1m / amt_total * 100) if amt_total > 0 else 0.0
        
        # Store year data in local dict
        year_data_dict[year] = {
            'num_total': num_total,
            'num_under_100k': num_under_100k,
            'num_100k_250k': num_100k_250k,
            'num_250k_1m': num_250k_1m,
            'numsb_under_1m': numsbrev_under_1m,
            'lmi_tract_pct': lmi_tract_pct,
            'amt_total': amt_total,
            'amt_under_100k': amt_under_100k,
            'amt_100k_250k': amt_100k_250k,
            'amt_250k_1m': amt_250k_1m,
            'amtsb_under_1m': amtsbrev_under_1m,
            'num_under_100k_pct': num_under_100k_pct,
            'num_100k_250k_pct': num_100k_250k_pct,
            'num_250k_1m_pct': num_250k_1m_pct,
            'numsb_under_1m_pct': numsb_under_1m_pct,
            'amt_under_100k_pct': amt_under_100k_pct,
            'amt_100k_250k_pct': amt_100k_250k_pct,
            'amt_250k_1m_pct': amt_250k_1m_pct,
            'amtsb_under_1m_pct': amtsb_under_1m_pct,
            'amt_lmi_tract_pct': amt_lmi_tract_pct
        }
    
    # Build table rows
    variables = [
        ('Total Loans', 'num_total', False),
        ('Loans Under $100K (% of Total)', 'num_under_100k_pct', True),
        ('Loans $100K-$250K (% of Total)', 'num_100k_250k_pct', True),
        ('Loans $250K-$1M (% of Total)', 'num_250k_1m_pct', True),
        ('Loans to Businesses Under $1M Revenue (% of Total)', 'numsb_under_1m_pct', True),
        ('Loans to LMI Tracts (% of Total)', 'lmi_tract_pct', True),
        ('Total Loan Amount (in millions)', 'amt_total', False),
        ('Amount Under $100K (% of Total)', 'amt_under_100k_pct', True),
        ('Amount $100K-$250K (% of Total)', 'amt_100k_250k_pct', True),
        ('Amount $250K-$1M (% of Total)', 'amt_250k_1m_pct', True),
        ('Amount to Businesses Under $1M Revenue (% of Total)', 'amtsb_under_1m_pct', True),
        ('Amount to LMI Tracts (% of Total)', 'amt_lmi_tract_pct', True)
    ]
    
    for var_name, var_key, is_pct in variables:
        row = {'Variable': var_name}
        for year in sorted(years):
            if year in year_data_dict:
                value = year_data_dict[year].get(var_key, 0)
                row[str(year)] = value
            else:
                row[str(year)] = 0
        table_rows.append(row)
    
    result_df = pd.DataFrame(table_rows)
    print(f"DEBUG: create_county_summary_table: Created {len(result_df)} rows, {len(result_df.columns)} columns")
    if not result_df.empty:
        print(f"DEBUG: create_county_summary_table: First row: {result_df.iloc[0].to_dict()}")
    return result_df


def create_comparison_table(county_df: pd.DataFrame, state_benchmarks: Dict, national_benchmarks: Dict, 
                           county_2020_data: Optional[Dict] = None) -> pd.DataFrame:
    """
    Create County, State, and National Comparison table for Section 3 (2024).
    
    Args:
        county_df: DataFrame with county data for all years (from aggregate table)
        state_benchmarks: Dictionary with state-level benchmark data for 2024
        national_benchmarks: Dictionary with national-level benchmark data for 2024
        county_2020_data: Optional dictionary with county 2020 data for % change calculation (baseline year)
    
    Returns:
        DataFrame with metrics as rows and County/State/National/% Change as columns
    """
    if county_df.empty:
        print("DEBUG: create_comparison_table: county_df is empty")
        return pd.DataFrame()
    
    # Check if benchmarks are provided - use empty dict defaults if missing
    if not state_benchmarks:
        print("DEBUG: create_comparison_table: WARNING - state_benchmarks is empty or None, using defaults")
        state_benchmarks = {}
    if not national_benchmarks:
        print("DEBUG: create_comparison_table: WARNING - national_benchmarks is empty or None, using defaults")
        national_benchmarks = {}
    
    # Filter to 2024 data (handle both string and int year values)
    if 'year' in county_df.columns:
        # Try both integer and string comparisons
        county_2024 = pd.DataFrame()
        # First try integer comparison
        if county_df['year'].dtype in ['int64', 'int32', 'int']:
            county_2024 = county_df[county_df['year'] == 2024].copy()
            print(f"DEBUG: Filtered to 2024 data (int): {len(county_2024)} rows from {len(county_df)} total rows")
        # If that didn't work, try string comparison
        if county_2024.empty:
            county_df_year_str = county_df['year'].astype(str)
            county_2024 = county_df[county_df_year_str == '2024'].copy()
            print(f"DEBUG: Filtered to 2024 data (str): {len(county_2024)} rows from {len(county_df)} total rows")
        
        print(f"DEBUG: Year column type: {county_df['year'].dtype}, unique values: {county_df['year'].unique()}")
        print(f"DEBUG: Year column sample values: {county_df['year'].head(10).tolist()}")
    else:
        county_2024 = county_df.copy()
        print("DEBUG: No 'year' column in county_df, using all data")
        print(f"DEBUG: county_df columns: {county_df.columns.tolist()}")
    
    if county_2024.empty:
        print("DEBUG: No 2024 data in county_df for comparison table")
        print(f"DEBUG: county_df shape: {county_df.shape}, columns: {county_df.columns.tolist()}")
        if 'year' in county_df.columns:
            print(f"DEBUG: Available years: {county_df['year'].unique()}")
            print(f"DEBUG: Year value types: {[type(v).__name__ for v in county_df['year'].unique()[:5]]}")
        return pd.DataFrame()
    
    # Calculate county 2024 metrics
    num_under_100k = safe_int(county_2024.get('num_under_100k', pd.Series([0])).sum())
    num_100k_250k = safe_int(county_2024.get('num_100k_250k', pd.Series([0])).sum())
    num_250k_1m = safe_int(county_2024.get('num_250k_1m', pd.Series([0])).sum())
    
    amt_under_100k = safe_float(county_2024.get('amt_under_100k', pd.Series([0.0])).sum())
    amt_100k_250k = safe_float(county_2024.get('amt_100k_250k', pd.Series([0.0])).sum())
    amt_250k_1m = safe_float(county_2024.get('amt_250k_1m', pd.Series([0.0])).sum())
    
    numsb_col = 'numsbrev_under_1m' if 'numsbrev_under_1m' in county_2024.columns else 'numsb_under_1m'
    amtsb_col = 'amtsbrev_under_1m' if 'amtsbrev_under_1m' in county_2024.columns else 'amtsb_under_1m'
    numsb_under_1m = safe_int(county_2024.get(numsb_col, pd.Series([0])).sum())
    amtsb_under_1m = safe_float(county_2024.get(amtsb_col, pd.Series([0.0])).sum())
    
    # Calculate totals
    num_total = num_under_100k + num_100k_250k + num_250k_1m
    amt_total = amt_under_100k + amt_100k_250k + amt_250k_1m
    
    # Calculate LMI tract loans
    if 'is_lmi_tract' in county_2024.columns:
        lmi_mask = (county_2024['is_lmi_tract'] == 1) | (county_2024['is_lmi_tract'] == True) | (county_2024['is_lmi_tract'].astype(str) == '1')
        lmi_tract_loans = safe_int(county_2024[lmi_mask].get('loan_count', pd.Series([0])).sum())
    else:
        lmi_tract_loans = 0
    
    # Calculate income category breakdowns for county 2024
    county_low_income_loans = 0
    county_moderate_income_loans = 0
    county_middle_income_loans = 0
    county_upper_income_loans = 0
    county_low_income_amount = 0.0
    county_moderate_income_amount = 0.0
    county_middle_income_amount = 0.0
    county_upper_income_amount = 0.0
    
    if 'income_level' in county_2024.columns:
        low_mask = county_2024['income_level'].fillna(0) == 1
        moderate_mask = county_2024['income_level'].fillna(0) == 2
        middle_mask = county_2024['income_level'].fillna(0) == 3
        upper_mask = county_2024['income_level'].fillna(0) == 4
        
        county_low_income_loans = int(county_2024[low_mask].get('loan_count', pd.Series([0])).sum())
        county_moderate_income_loans = int(county_2024[moderate_mask].get('loan_count', pd.Series([0])).sum())
        county_middle_income_loans = int(county_2024[middle_mask].get('loan_count', pd.Series([0])).sum())
        county_upper_income_loans = int(county_2024[upper_mask].get('loan_count', pd.Series([0])).sum())
        
        county_low_income_amount = float(county_2024[low_mask].get('loan_amount', pd.Series([0.0])).sum())
        county_moderate_income_amount = float(county_2024[moderate_mask].get('loan_amount', pd.Series([0.0])).sum())
        county_middle_income_amount = float(county_2024[middle_mask].get('loan_amount', pd.Series([0.0])).sum())
        county_upper_income_amount = float(county_2024[upper_mask].get('loan_amount', pd.Series([0.0])).sum())
    elif 'income_category' in county_2024.columns:
        low_mask = county_2024['income_category'].str.contains('Low Income', na=False)
        moderate_mask = county_2024['income_category'].str.contains('Moderate Income', na=False)
        middle_mask = county_2024['income_category'].str.contains('Middle Income', na=False)
        upper_mask = county_2024['income_category'].str.contains('Upper Income', na=False)
        
        county_low_income_loans = int(county_2024[low_mask].get('loan_count', pd.Series([0])).sum())
        county_moderate_income_loans = int(county_2024[moderate_mask].get('loan_count', pd.Series([0])).sum())
        county_middle_income_loans = int(county_2024[middle_mask].get('loan_count', pd.Series([0])).sum())
        county_upper_income_loans = int(county_2024[upper_mask].get('loan_count', pd.Series([0])).sum())
        
        county_low_income_amount = float(county_2024[low_mask].get('loan_amount', pd.Series([0.0])).sum())
        county_moderate_income_amount = float(county_2024[moderate_mask].get('loan_amount', pd.Series([0.0])).sum())
        county_middle_income_amount = float(county_2024[middle_mask].get('loan_amount', pd.Series([0.0])).sum())
        county_upper_income_amount = float(county_2024[upper_mask].get('loan_amount', pd.Series([0.0])).sum())
    
    # Calculate percentages
    county_pct_under_100k = (num_under_100k / num_total * 100) if num_total > 0 else 0.0
    county_pct_100k_250k = (num_100k_250k / num_total * 100) if num_total > 0 else 0.0
    county_pct_250k_1m = (num_250k_1m / num_total * 100) if num_total > 0 else 0.0
    county_pct_sb_under_1m = (numsb_under_1m / num_total * 100) if num_total > 0 else 0.0
    county_pct_lmi_tract = (lmi_tract_loans / num_total * 100) if num_total > 0 else 0.0
    
    county_pct_amt_under_100k = (amt_under_100k / amt_total * 100) if amt_total > 0 else 0.0
    county_pct_amt_100k_250k = (amt_100k_250k / amt_total * 100) if amt_total > 0 else 0.0
    county_pct_amt_250k_1m = (amt_250k_1m / amt_total * 100) if amt_total > 0 else 0.0
    county_pct_amt_sb_under_1m = (amtsb_under_1m / amt_total * 100) if amt_total > 0 else 0.0
    
    county_pct_loans_low_income = (county_low_income_loans / num_total * 100) if num_total > 0 else 0.0
    county_pct_loans_moderate_income = (county_moderate_income_loans / num_total * 100) if num_total > 0 else 0.0
    county_pct_loans_middle_income = (county_middle_income_loans / num_total * 100) if num_total > 0 else 0.0
    county_pct_loans_upper_income = (county_upper_income_loans / num_total * 100) if num_total > 0 else 0.0
    
    county_pct_amount_low_income = (county_low_income_amount / amt_total * 100) if amt_total > 0 else 0.0
    county_pct_amount_moderate_income = (county_moderate_income_amount / amt_total * 100) if amt_total > 0 else 0.0
    county_pct_amount_middle_income = (county_middle_income_amount / amt_total * 100) if amt_total > 0 else 0.0
    county_pct_amount_upper_income = (county_upper_income_amount / amt_total * 100) if amt_total > 0 else 0.0
    
    # Get state and national values (with defaults)
    state_total = state_benchmarks.get('total_loans', 0)
    state_amount = state_benchmarks.get('total_amount', 0.0)
    state_pct_under_100k = state_benchmarks.get('pct_loans_under_100k', 0.0)
    state_pct_100k_250k = state_benchmarks.get('pct_loans_100k_250k', 0.0)
    state_pct_250k_1m = state_benchmarks.get('pct_loans_250k_1m', 0.0)
    state_pct_sb_under_1m = state_benchmarks.get('pct_loans_sb_under_1m', 0.0)
    state_pct_lmi_tract = state_benchmarks.get('pct_loans_lmi_tract', 0.0)
    state_pct_amt_under_100k = state_benchmarks.get('pct_amount_under_100k', 0.0)
    state_pct_amt_100k_250k = state_benchmarks.get('pct_amount_100k_250k', 0.0)
    state_pct_amt_250k_1m = state_benchmarks.get('pct_amount_250k_1m', 0.0)
    state_pct_amt_sb_under_1m = state_benchmarks.get('pct_amount_sb_under_1m', 0.0)
    state_pct_loans_low_income = state_benchmarks.get('pct_loans_low_income', 0.0)
    state_pct_loans_moderate_income = state_benchmarks.get('pct_loans_moderate_income', 0.0)
    state_pct_loans_middle_income = state_benchmarks.get('pct_loans_middle_income', 0.0)
    state_pct_loans_upper_income = state_benchmarks.get('pct_loans_upper_income', 0.0)
    state_pct_amount_low_income = state_benchmarks.get('pct_amount_low_income', 0.0)
    state_pct_amount_moderate_income = state_benchmarks.get('pct_amount_moderate_income', 0.0)
    state_pct_amount_middle_income = state_benchmarks.get('pct_amount_middle_income', 0.0)
    state_pct_amount_upper_income = state_benchmarks.get('pct_amount_upper_income', 0.0)
    
    national_total = national_benchmarks.get('total_loans', 0)
    national_amount = national_benchmarks.get('total_amount', 0.0)
    national_pct_under_100k = national_benchmarks.get('pct_loans_under_100k', 0.0)
    national_pct_100k_250k = national_benchmarks.get('pct_loans_100k_250k', 0.0)
    national_pct_250k_1m = national_benchmarks.get('pct_loans_250k_1m', 0.0)
    national_pct_sb_under_1m = national_benchmarks.get('pct_loans_sb_under_1m', 0.0)
    national_pct_lmi_tract = national_benchmarks.get('pct_loans_lmi_tract', 0.0)
    national_pct_amt_under_100k = national_benchmarks.get('pct_amount_under_100k', 0.0)
    national_pct_amt_100k_250k = national_benchmarks.get('pct_amount_100k_250k', 0.0)
    national_pct_amt_250k_1m = national_benchmarks.get('pct_amount_250k_1m', 0.0)
    national_pct_amt_sb_under_1m = national_benchmarks.get('pct_amount_sb_under_1m', 0.0)
    national_pct_loans_low_income = national_benchmarks.get('pct_loans_low_income', 0.0)
    national_pct_loans_moderate_income = national_benchmarks.get('pct_loans_moderate_income', 0.0)
    national_pct_loans_middle_income = national_benchmarks.get('pct_loans_middle_income', 0.0)
    national_pct_loans_upper_income = national_benchmarks.get('pct_loans_upper_income', 0.0)
    national_pct_amount_low_income = national_benchmarks.get('pct_amount_low_income', 0.0)
    national_pct_amount_moderate_income = national_benchmarks.get('pct_amount_moderate_income', 0.0)
    national_pct_amount_middle_income = national_benchmarks.get('pct_amount_middle_income', 0.0)
    national_pct_amount_upper_income = national_benchmarks.get('pct_amount_upper_income', 0.0)
    
    # Calculate % change since 2020 (baseline year)
    def calc_pct_change(current, base):
        if base is None or base == 0:
            return None
        try:
            base_val = float(base)
            current_val = float(current)
            if base_val > 0:
                return ((current_val - base_val) / base_val) * 100
        except (ValueError, TypeError):
            pass
        return None
    
    pct_change_total_loans = calc_pct_change(num_total, county_2020_data.get('total_loans', 0) if county_2020_data else 0)
    pct_change_total_amount = calc_pct_change(amt_total, county_2020_data.get('total_amount', 0.0) if county_2020_data else 0.0)
    pct_change_num_under_100k = calc_pct_change(num_under_100k, county_2020_data.get('num_under_100k', 0) if county_2020_data else 0)
    pct_change_num_100k_250k = calc_pct_change(num_100k_250k, county_2020_data.get('num_100k_250k', 0) if county_2020_data else 0)
    pct_change_num_250k_1m = calc_pct_change(num_250k_1m, county_2020_data.get('num_250k_1m', 0) if county_2020_data else 0)
    pct_change_numsb_under_1m = calc_pct_change(numsb_under_1m, county_2020_data.get('numsb_under_1m', 0) if county_2020_data else 0)
    pct_change_lmi_tract_loans = calc_pct_change(lmi_tract_loans, county_2020_data.get('lmi_tract_loans', 0) if county_2020_data else 0)
    pct_change_amt_under_100k = calc_pct_change(amt_under_100k, county_2020_data.get('amt_under_100k', 0.0) if county_2020_data else 0.0)
    pct_change_amt_100k_250k = calc_pct_change(amt_100k_250k, county_2020_data.get('amt_100k_250k', 0.0) if county_2020_data else 0.0)
    pct_change_amt_250k_1m = calc_pct_change(amt_250k_1m, county_2020_data.get('amt_250k_1m', 0.0) if county_2020_data else 0.0)
    pct_change_amtsb_under_1m = calc_pct_change(amtsb_under_1m, county_2020_data.get('amtsb_under_1m', 0.0) if county_2020_data else 0.0)
    pct_change_low_income_loans = calc_pct_change(county_low_income_loans, county_2020_data.get('low_income_loans', 0) if county_2020_data else 0)
    pct_change_moderate_income_loans = calc_pct_change(county_moderate_income_loans, county_2020_data.get('moderate_income_loans', 0) if county_2020_data else 0)
    pct_change_middle_income_loans = calc_pct_change(county_middle_income_loans, county_2020_data.get('middle_income_loans', 0) if county_2020_data else 0)
    pct_change_upper_income_loans = calc_pct_change(county_upper_income_loans, county_2020_data.get('upper_income_loans', 0) if county_2020_data else 0)
    pct_change_low_income_amount = calc_pct_change(county_low_income_amount, county_2020_data.get('low_income_amount', 0.0) if county_2020_data else 0.0)
    pct_change_moderate_income_amount = calc_pct_change(county_moderate_income_amount, county_2020_data.get('moderate_income_amount', 0.0) if county_2020_data else 0.0)
    pct_change_middle_income_amount = calc_pct_change(county_middle_income_amount, county_2020_data.get('middle_income_amount', 0.0) if county_2020_data else 0.0)
    pct_change_upper_income_amount = calc_pct_change(county_upper_income_amount, county_2020_data.get('upper_income_amount', 0.0) if county_2020_data else 0.0)
    
    # Build comparison data rows
    comparison_data = [
        {
            'Metric': 'Total Loans',
            'County (2024)': num_total,
            'State (2024)': state_total,
            'National (2024)': national_total,
            '% Change Since 2020': pct_change_total_loans
        },
        {
            'Metric': 'Loans Under $100K (% of Total)',
            'County (2024)': county_pct_under_100k,
            'State (2024)': state_pct_under_100k,
            'National (2024)': national_pct_under_100k,
            '% Change Since 2018': pct_change_num_under_100k
        },
        {
            'Metric': 'Loans $100K-$250K (% of Total)',
            'County (2024)': county_pct_100k_250k,
            'State (2024)': state_pct_100k_250k,
            'National (2024)': national_pct_100k_250k,
            '% Change Since 2018': pct_change_num_100k_250k
        },
        {
            'Metric': 'Loans $250K-$1M (% of Total)',
            'County (2024)': county_pct_250k_1m,
            'State (2024)': state_pct_250k_1m,
            'National (2024)': national_pct_250k_1m,
            '% Change Since 2018': pct_change_num_250k_1m
        },
        {
            'Metric': 'Loans to Businesses Under $1M Revenue (% of Total)',
            'County (2024)': county_pct_sb_under_1m,
            'State (2024)': state_pct_sb_under_1m,
            'National (2024)': national_pct_sb_under_1m,
            '% Change Since 2018': pct_change_numsb_under_1m
        },
        {
            'Metric': 'Loans to Low Income Tracts (% of Total)',
            'County (2024)': county_pct_loans_low_income,
            'State (2024)': state_pct_loans_low_income,
            'National (2024)': national_pct_loans_low_income,
            '% Change Since 2018': pct_change_low_income_loans
        },
        {
            'Metric': 'Loans to Moderate Income Tracts (% of Total)',
            'County (2024)': county_pct_loans_moderate_income,
            'State (2024)': state_pct_loans_moderate_income,
            'National (2024)': national_pct_loans_moderate_income,
            '% Change Since 2018': pct_change_moderate_income_loans
        },
        {
            'Metric': 'Loans to Middle Income Tracts (% of Total)',
            'County (2024)': county_pct_loans_middle_income,
            'State (2024)': state_pct_loans_middle_income,
            'National (2024)': national_pct_loans_middle_income,
            '% Change Since 2018': pct_change_middle_income_loans
        },
        {
            'Metric': 'Loans to Upper Income Tracts (% of Total)',
            'County (2024)': county_pct_loans_upper_income,
            'State (2024)': state_pct_loans_upper_income,
            'National (2024)': national_pct_loans_upper_income,
            '% Change Since 2018': pct_change_upper_income_loans
        },
        {
            'Metric': 'Total Loan Amount (in millions)',
            'County (2024)': amt_total,
            'State (2024)': state_amount,
            'National (2024)': national_amount,
            '% Change Since 2018': pct_change_total_amount
        },
        {
            'Metric': 'Amount Under $100K (% of Total)',
            'County (2024)': county_pct_amt_under_100k,
            'State (2024)': state_pct_amt_under_100k,
            'National (2024)': national_pct_amt_under_100k,
            '% Change Since 2018': pct_change_amt_under_100k
        },
        {
            'Metric': 'Amount $100K-$250K (% of Total)',
            'County (2024)': county_pct_amt_100k_250k,
            'State (2024)': state_pct_amt_100k_250k,
            'National (2024)': national_pct_amt_100k_250k,
            '% Change Since 2018': pct_change_amt_100k_250k
        },
        {
            'Metric': 'Amount $250K-$1M (% of Total)',
            'County (2024)': county_pct_amt_250k_1m,
            'State (2024)': state_pct_amt_250k_1m,
            'National (2024)': national_pct_amt_250k_1m,
            '% Change Since 2018': pct_change_amt_250k_1m
        },
        {
            'Metric': 'Amount to Businesses Under $1M Revenue (% of Total)',
            'County (2024)': county_pct_amt_sb_under_1m,
            'State (2024)': state_pct_amt_sb_under_1m,
            'National (2024)': national_pct_amt_sb_under_1m,
            '% Change Since 2018': pct_change_amtsb_under_1m
        },
        {
            'Metric': 'Amount to Low Income Tracts (% of Total)',
            'County (2024)': county_pct_amount_low_income,
            'State (2024)': state_pct_amount_low_income,
            'National (2024)': national_pct_amount_low_income,
            '% Change Since 2018': pct_change_low_income_amount
        },
        {
            'Metric': 'Amount to Moderate Income Tracts (% of Total)',
            'County (2024)': county_pct_amount_moderate_income,
            'State (2024)': state_pct_amount_moderate_income,
            'National (2024)': national_pct_amount_moderate_income,
            '% Change Since 2018': pct_change_moderate_income_amount
        },
        {
            'Metric': 'Amount to Middle Income Tracts (% of Total)',
            'County (2024)': county_pct_amount_middle_income,
            'State (2024)': state_pct_amount_middle_income,
            'National (2024)': national_pct_amount_middle_income,
            '% Change Since 2018': pct_change_middle_income_amount
        },
        {
            'Metric': 'Amount to Upper Income Tracts (% of Total)',
            'County (2024)': county_pct_amount_upper_income,
            'State (2024)': state_pct_amount_upper_income,
            'National (2024)': national_pct_amount_upper_income,
            '% Change Since 2018': pct_change_upper_income_amount
        }
    ]
    
    print(f"DEBUG: create_comparison_table: Built {len(comparison_data)} rows of comparison data")
    if comparison_data:
        print(f"DEBUG: create_comparison_table: First row sample: {comparison_data[0]}")
    
    result_df = pd.DataFrame(comparison_data)
    print(f"DEBUG: create_comparison_table: Returning DataFrame with {len(result_df)} rows, {len(result_df.columns)} columns")
    if not result_df.empty:
        print(f"DEBUG: create_comparison_table: DataFrame columns: {result_df.columns.tolist()}")
    return result_df


def clean_lender_name(name: str) -> str:
    """
    Clean and abbreviate lender names.
    
    Args:
        name: Raw lender name
    
    Returns:
        Cleaned lender name
    """
    if not name or not isinstance(name, str):
        return str(name) if name else ''
    
    # Abbreviate common bank name suffixes
    name = name.strip()
    
    # American Express National Bank -> American Express
    if 'AMERICAN EXPRESS NATIONAL BANK' in name.upper():
        return 'American Express'
    
    # Remove common suffixes (case-insensitive)
    suffixes = [
        ' National Bank',
        ' N.A.',
        ' NA',
        ' National Association',
        ' Bank, National Association',
        ', National Association',
        ' Bank N.A.',
        ' Bank NA'
    ]
    
    for suffix in suffixes:
        if name.upper().endswith(suffix.upper()):
            name = name[:-len(suffix)]
            break
    
    return name.strip()


def create_top_lenders_table(df: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    """
    Create top lenders table for Section 4 (2024 only).
    
    Shows top lenders by number of loans in 2024 with income category breakdowns.
    
    Args:
        df: DataFrame from disclosure table query (must include lender_name and all SB fields)
        year: Year to use for the table (default 2024)
    
    Returns:
        DataFrame with lenders sorted by Num Total descending
    """
    if df.empty:
        return pd.DataFrame()
    
    # Filter to specified year (handle both string and int)
    print(f"DEBUG: create_top_lenders_table: Filtering to year {year}")
    print(f"DEBUG: create_top_lenders_table: Input df has {len(df)} rows")
    print(f"DEBUG: create_top_lenders_table: Available years in df: {df['year'].unique() if 'year' in df.columns else 'no year column'}")
    
    if 'year' in df.columns:
        if df['year'].dtype in ['int64', 'int32', 'int']:
            year_df = df[df['year'] == year].copy()
        else:
            year_df_str = df['year'].astype(str)
            year_df = df[year_df_str == str(year)].copy()
    else:
        print(f"DEBUG: WARNING - No 'year' column in disclosure_df, using all data (this may be wrong!)")
        year_df = df.copy()
    
    print(f"DEBUG: create_top_lenders_table: After filtering to {year}, year_df has {len(year_df)} rows")
    if not year_df.empty:
        print(f"DEBUG: create_top_lenders_table: Years in filtered df: {year_df['year'].unique() if 'year' in year_df.columns else 'no year column'}")
    
    if year_df.empty:
        print(f"DEBUG: WARNING - No data for year {year} in disclosure_df")
        return pd.DataFrame()
    
    # Map field names (handle variations)
    field_map = {
        'num_under_100k': ['num_under_100k', 'Num_Under_100K', 'NUM_UNDER_100K'],
        'num_100k_250k': ['num_100k_250k', 'Num_100K_250K', 'NUM_100K_250K'],
        'num_250k_1m': ['num_250k_1m', 'Num_250K_1M', 'NUM_250K_1M'],
        'amt_under_100k': ['amt_under_100k', 'Amt_Under_100K', 'AMT_UNDER_100K'],
        'amt_100k_250k': ['amt_100k_250k', 'Amt_100K_250K', 'AMT_100K_250K'],
        'amt_250k_1m': ['amt_250k_1m', 'Amt_250K_1M', 'AMT_250K_1M'],
        'numsbrev_under_1m': ['numsbrev_under_1m', 'NumsbRev_Under_1M', 'NUMSBREV_UNDER_1M', 'numsb_under_1m'],
        'amtsbrev_under_1m': ['amtsbrev_under_1m', 'AmtsbRev_Under_1M', 'AMTSBREV_UNDER_1M', 'amtsb_under_1m'],
        'income_group_total': ['income_group_total', 'Income_Group_Total', 'INCOME_GROUP_TOTAL']
    }
    
    # Find actual column names
    available_cols = year_df.columns.tolist()
    actual_fields = {}
    for key, possible_names in field_map.items():
        found = False
        for name in possible_names:
            if name in available_cols:
                actual_fields[key] = name
                found = True
                break
        if not found:
            actual_fields[key] = key
    
    # Aggregate by lender
    lender_data = []
    
    # Verify we only have data for the specified year
    if 'year' in year_df.columns:
        unique_years = year_df['year'].unique()
        if len(unique_years) > 1 or (len(unique_years) == 1 and unique_years[0] != year):
            print(f"DEBUG: WARNING - year_df contains data for years {unique_years}, expected only {year}")
        else:
            print(f"DEBUG: Verified year_df contains only year {year} data")
    
    for lender_name in year_df['lender_name'].unique():
        lender_df = year_df[year_df['lender_name'] == lender_name]
        
        # Debug: Check if this lender has multiple rows (which is expected for different income groups/loan sizes)
        if len(lender_df) > 1:
            print(f"DEBUG: Lender {lender_name} has {len(lender_df)} rows (expected for different income groups/loan sizes)")
        
        # Sum numeric fields
        num_under_100k = safe_int(lender_df[actual_fields['num_under_100k']].sum()) if actual_fields['num_under_100k'] in lender_df.columns else 0
        num_100k_250k = safe_int(lender_df[actual_fields['num_100k_250k']].sum()) if actual_fields['num_100k_250k'] in lender_df.columns else 0
        num_250k_1m = safe_int(lender_df[actual_fields['num_250k_1m']].sum()) if actual_fields['num_250k_1m'] in lender_df.columns else 0
        
        amt_under_100k = safe_float(lender_df[actual_fields['amt_under_100k']].sum()) if actual_fields['amt_under_100k'] in lender_df.columns else 0.0
        amt_100k_250k = safe_float(lender_df[actual_fields['amt_100k_250k']].sum()) if actual_fields['amt_100k_250k'] in lender_df.columns else 0.0
        amt_250k_1m = safe_float(lender_df[actual_fields['amt_250k_1m']].sum()) if actual_fields['amt_250k_1m'] in lender_df.columns else 0.0
        
        numsb_col = actual_fields['numsbrev_under_1m']
        amtsb_col = actual_fields['amtsbrev_under_1m']
        numsbrev_under_1m = safe_int(lender_df[numsb_col].sum()) if numsb_col in lender_df.columns else 0
        amtsbrev_under_1m = safe_float(lender_df[amtsb_col].sum()) if amtsb_col in lender_df.columns else 0.0
        
        # Calculate totals
        num_total = num_under_100k + num_100k_250k + num_250k_1m
        amt_total = amt_under_100k + amt_100k_250k + amt_250k_1m
        
        # Calculate LMI Tract percentage using income_group_total
        # LMI = Low Income + Moderate Income (consistent with MergerMeter and SQL queries)
        # Known values: 101=Low, 102=Moderate, 103=Middle, 104=Upper
        # Single digits 1-8 are all LMI categories
        lmi_tract_pct = 0.0
        lmi_tract_amt_pct = 0.0
        if actual_fields['income_group_total'] in lender_df.columns:
            income_group_str = lender_df[actual_fields['income_group_total']].astype(str)
            # LMI codes: 101, 102, and zero-padded 001-008 (as stored in database)
            lmi_codes = ['101', '102', '001', '002', '003', '004', '005', '006', '007', '008']
            lmi_mask = income_group_str.isin(lmi_codes)

            # Calculate LMI loans and amounts
            lmi_num = 0
            lmi_amt = 0.0
            if actual_fields['num_under_100k'] in lender_df.columns:
                lmi_num += safe_int(lender_df[lmi_mask][actual_fields['num_under_100k']].sum())
            if actual_fields['num_100k_250k'] in lender_df.columns:
                lmi_num += safe_int(lender_df[lmi_mask][actual_fields['num_100k_250k']].sum())
            if actual_fields['num_250k_1m'] in lender_df.columns:
                lmi_num += safe_int(lender_df[lmi_mask][actual_fields['num_250k_1m']].sum())

            if actual_fields['amt_under_100k'] in lender_df.columns:
                lmi_amt += safe_float(lender_df[lmi_mask][actual_fields['amt_under_100k']].sum())
            if actual_fields['amt_100k_250k'] in lender_df.columns:
                lmi_amt += safe_float(lender_df[lmi_mask][actual_fields['amt_100k_250k']].sum())
            if actual_fields['amt_250k_1m'] in lender_df.columns:
                lmi_amt += safe_float(lender_df[lmi_mask][actual_fields['amt_250k_1m']].sum())

            lmi_tract_pct = (lmi_num / num_total * 100) if num_total > 0 else 0.0
            lmi_tract_amt_pct = (lmi_amt / amt_total * 100) if amt_total > 0 else 0.0

        # Calculate income category breakdowns (consistent with SQL queries)
        # Low Income: 101, 1, 2, 3, 4, 5
        # Moderate Income: 102, 6, 7, 8
        # Middle Income: 103
        # Upper Income: 104
        # Unknown: All others
        low_income_num = 0
        moderate_income_num = 0
        middle_income_num = 0
        upper_income_num = 0
        low_income_amt = 0.0
        moderate_income_amt = 0.0
        middle_income_amt = 0.0
        upper_income_amt = 0.0

        if actual_fields['income_group_total'] in lender_df.columns:
            income_group_str = lender_df[actual_fields['income_group_total']].astype(str)

            # Low Income: 101 and zero-padded 001-005 (as stored in database)
            low_mask = income_group_str.isin(['101', '001', '002', '003', '004', '005'])

            # Moderate Income: 102 and zero-padded 006-008 (as stored in database)
            moderate_mask = income_group_str.isin(['102', '006', '007', '008'])

            # Middle Income: 103
            middle_mask = income_group_str.isin(['103'])

            # Upper Income: 104
            upper_mask = income_group_str.isin(['104'])
            
            # Calculate counts and amounts for each category
            for field in ['num_under_100k', 'num_100k_250k', 'num_250k_1m']:
                if actual_fields[field] in lender_df.columns:
                    low_income_num += safe_int(lender_df[low_mask][actual_fields[field]].sum())
                    moderate_income_num += safe_int(lender_df[moderate_mask][actual_fields[field]].sum())
                    middle_income_num += safe_int(lender_df[middle_mask][actual_fields[field]].sum())
                    upper_income_num += safe_int(lender_df[upper_mask][actual_fields[field]].sum())
            
            for field in ['amt_under_100k', 'amt_100k_250k', 'amt_250k_1m']:
                if actual_fields[field] in lender_df.columns:
                    low_income_amt += safe_float(lender_df[low_mask][actual_fields[field]].sum())
                    moderate_income_amt += safe_float(lender_df[moderate_mask][actual_fields[field]].sum())
                    middle_income_amt += safe_float(lender_df[middle_mask][actual_fields[field]].sum())
                    upper_income_amt += safe_float(lender_df[upper_mask][actual_fields[field]].sum())
        
        # Calculate percentages
        num_under_100k_pct = (num_under_100k / num_total * 100) if num_total > 0 else 0.0
        num_100k_250k_pct = (num_100k_250k / num_total * 100) if num_total > 0 else 0.0
        num_250k_1m_pct = (num_250k_1m / num_total * 100) if num_total > 0 else 0.0
        numsb_under_1m_pct = (numsbrev_under_1m / num_total * 100) if num_total > 0 else 0.0
        
        amt_under_100k_pct = (amt_under_100k / amt_total * 100) if amt_total > 0 else 0.0
        amt_100k_250k_pct = (amt_100k_250k / amt_total * 100) if amt_total > 0 else 0.0
        amt_250k_1m_pct = (amt_250k_1m / amt_total * 100) if amt_total > 0 else 0.0
        amtsb_under_1m_pct = (amtsbrev_under_1m / amt_total * 100) if amt_total > 0 else 0.0
        
        low_income_pct = (low_income_num / num_total * 100) if num_total > 0 else 0.0
        moderate_income_pct = (moderate_income_num / num_total * 100) if num_total > 0 else 0.0
        middle_income_pct = (middle_income_num / num_total * 100) if num_total > 0 else 0.0
        upper_income_pct = (upper_income_num / num_total * 100) if num_total > 0 else 0.0
        
        low_income_amt_pct = (low_income_amt / amt_total * 100) if amt_total > 0 else 0.0
        moderate_income_amt_pct = (moderate_income_amt / amt_total * 100) if amt_total > 0 else 0.0
        middle_income_amt_pct = (middle_income_amt / amt_total * 100) if amt_total > 0 else 0.0
        upper_income_amt_pct = (upper_income_amt / amt_total * 100) if amt_total > 0 else 0.0
        
        # Clean lender name (abbreviate common suffixes)
        cleaned_lender_name = clean_lender_name(lender_name)
        
        lender_row = {
            'Lender Name': cleaned_lender_name.upper() if isinstance(cleaned_lender_name, str) else str(cleaned_lender_name),
            'Num Total': num_total,
            'Num Under 100K': num_under_100k,
            'Num Under 100K %': num_under_100k_pct,
            'Num 100K 250K': num_100k_250k,
            'Num 100K 250K %': num_100k_250k_pct,
            'Num 250K 1M': num_250k_1m,
            'Num 250K 1M %': num_250k_1m_pct,
            'Numsb Under 1M': numsbrev_under_1m,
            'Numsb Under 1M %': numsb_under_1m_pct,
            'Lmi Tract': lmi_tract_pct,
            'Low Income %': low_income_pct,
            'Moderate Income %': moderate_income_pct,
            'Middle Income %': middle_income_pct,
            'Upper Income %': upper_income_pct,
            'Amt Total': amt_total,
            'Amt Total (in $000s)': amt_total,  # Same value, will be formatted in frontend
            'Amt Under 100K': amt_under_100k,
            'Amt Under 100K %': amt_under_100k_pct,
            'Amt 100K 250K': amt_100k_250k,
            'Amt 100K 250K %': amt_100k_250k_pct,
            'Amt 250K 1M': amt_250k_1m,
            'Amt 250K 1M %': amt_250k_1m_pct,
            'Amtsb Under 1M': amtsbrev_under_1m,
            'Amtsb Under 1M %': amtsb_under_1m_pct,
            'Amount to LMI Tracts': lmi_tract_amt_pct,
            'Low Income Amt %': low_income_amt_pct,
            'Moderate Income Amt %': moderate_income_amt_pct,
            'Middle Income Amt %': middle_income_amt_pct,
            'Upper Income Amt %': upper_income_amt_pct
        }
        
        lender_data.append(lender_row)
    
    # Sort by Num Total descending
    lender_data.sort(key=lambda x: x['Num Total'], reverse=True)
    
    if not lender_data:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(lender_data)
    
    # Debug: Verify totals and year filtering
    if not result_df.empty:
        total_loans_all_lenders = result_df['Num Total'].sum()
        total_amount_all_lenders = result_df['Amt Total'].sum()
        print(f"DEBUG: create_top_lenders_table: Total loans across all lenders: {total_loans_all_lenders:,}")
        print(f"DEBUG: create_top_lenders_table: Total amount across all lenders: ${total_amount_all_lenders:,.0f} (in thousands)")
        print(f"DEBUG: create_top_lenders_table: Number of unique lenders: {len(result_df)}")
        if len(result_df) > 0:
            top_lender = result_df.iloc[0]
            print(f"DEBUG: create_top_lenders_table: Top lender: {top_lender['Lender Name']}, Loans: {top_lender['Num Total']:,}, Amount: ${top_lender['Amt Total']:,.0f}")
    
    return result_df


def calculate_hhi_for_lenders(disclosure_df: pd.DataFrame, year: int = 2024) -> Optional[float]:
    """
    Calculate HHI for a specific year from disclosure data.
    
    Args:
        disclosure_df: DataFrame with disclosure data
        year: Year to calculate HHI for
    
    Returns:
        HHI value (0-10,000 scale) or None if calculation fails
    """
    if disclosure_df.empty or 'year' not in disclosure_df.columns:
        return None
    
    # Filter to year data
    if disclosure_df['year'].dtype in ['int64', 'int32', 'int']:
        year_df = disclosure_df[disclosure_df['year'] == year].copy()
    else:
        year_df_str = disclosure_df['year'].astype(str)
        year_df = disclosure_df[year_df_str == str(year)].copy()
    
    if year_df.empty or 'lender_name' not in year_df.columns:
        return None
    
    # Sum all amount fields for each lender
    amt_fields = ['amt_under_100k', 'amt_100k_250k', 'amt_250k_1m']
    lender_amounts = {}
    for lender_name in year_df['lender_name'].unique():
        lender_df = year_df[year_df['lender_name'] == lender_name]
        total_amt = 0.0
        for field in amt_fields:
            if field in lender_df.columns:
                amt_sum = lender_df[field].sum()
                total_amt += float(amt_sum) if pd.notna(amt_sum) else 0.0
        if total_amt > 0:
            lender_amounts[lender_name] = total_amt
    
    if not lender_amounts:
        return None
    
    total_amount = sum(lender_amounts.values())
    if total_amount <= 0:
        return None
    
    # Calculate market shares as percentages
    market_shares = {}
    for lender_name, lender_amt in lender_amounts.items():
        market_shares[lender_name] = (lender_amt / total_amount) * 100
    
    # Calculate HHI: sum of squared market shares (0-10,000 scale)
    hhi = sum(share ** 2 for share in market_shares.values())
    return round(hhi, 2)


def calculate_hhi_by_year(disclosure_df: pd.DataFrame, years: List[int]) -> List[Dict]:
    """
    Calculate HHI for each year from 2018 to 2024.
    
    Args:
        disclosure_df: DataFrame with disclosure data for all years
        years: List of years to calculate HHI for
        
    Returns:
        List of dictionaries with year, hhi_value, and concentration_level
    """
    hhi_by_year = []
    
    if disclosure_df.empty or 'year' not in disclosure_df.columns:
        return hhi_by_year
    
    for year in years:
        hhi_value = calculate_hhi_for_lenders(disclosure_df, year)
        
        if hhi_value is not None:
            # Determine concentration level
            if hhi_value < 1500:
                concentration = 'Low concentration (competitive market)'
            elif hhi_value < 2500:
                concentration = 'Moderate concentration'
            else:
                concentration = 'High concentration'
            
            hhi_by_year.append({
                'year': year,
                'hhi_value': hhi_value,
                'concentration_level': concentration
            })
        else:
            hhi_by_year.append({
                'year': year,
                'hhi_value': None,
                'concentration_level': 'Data not available'
            })
    
    return hhi_by_year
