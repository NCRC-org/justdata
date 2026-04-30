"""Excel-shaped top-lenders tables."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from justdata.apps.lendsight.report_builder.formatting import (
    abbreviate_long_lender_name,
    correct_lender_name_capitalization,
)

def create_top_lenders_table_for_excel(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """
    Create top lenders table for Excel export with ALL race/ethnic categories and No Data column.
    
    This version includes all categories regardless of percentage, and includes the No Data column.
    """
    if not years:
        return pd.DataFrame()
    
    latest_year = max(years)
    
    latest_year_df = df[df['year'] == latest_year].copy()
    
    if latest_year_df.empty:
        return pd.DataFrame()
    
    required_columns = ['lender_name', 'total_originations', 'hispanic_originations', 
                       'black_originations', 'white_originations', 'asian_originations',
                       'native_american_originations', 'hopi_originations', 'multi_racial_originations',
                       'lmib_originations', 'lmict_originations', 'mmct_originations',
                       'loans_with_demographic_data']
    
    missing_cols = [col for col in required_columns if col not in latest_year_df.columns]
    if missing_cols:
        return pd.DataFrame()
    
    # Aggregate by lender
    lender_data = []
    for lender_name in latest_year_df['lender_name'].unique():
        lender_df = latest_year_df[latest_year_df['lender_name'] == lender_name]
        
        total = int(lender_df['total_originations'].sum())
        loans_with_demo = int(lender_df['loans_with_demographic_data'].sum()) if 'loans_with_demographic_data' in lender_df.columns else total
        
        lender_type = None
        if 'lender_type' in lender_df.columns:
            lender_types = lender_df['lender_type'].dropna().unique()
            if len(lender_types) > 0:
                lender_type = lender_types[0]
        
        hispanic = int(lender_df['hispanic_originations'].sum())
        black = int(lender_df['black_originations'].sum())
        white = int(lender_df['white_originations'].sum())
        asian = int(lender_df['asian_originations'].sum())
        multi_racial = int(lender_df['multi_racial_originations'].sum()) if 'multi_racial_originations' in lender_df.columns else 0
        native_american = int(lender_df['native_american_originations'].sum())
        hopi = int(lender_df['hopi_originations'].sum())
        
        lmib = int(lender_df['lmib_originations'].sum())
        lmict = int(lender_df['lmict_originations'].sum())
        mmct = int(lender_df['mmct_originations'].sum())
        
        loans_no_data = total - loans_with_demo
        
        lender_data.append({
            'Lender Name': lender_name,  # Already uppercase from clean_mortgage_data
            'Lender Type': lender_type if lender_type else '',
            'Total Loans': total,
            'Hispanic (%)': (hispanic / loans_with_demo * 100) if loans_with_demo > 0 else 0.0,
            'Black (%)': (black / loans_with_demo * 100) if loans_with_demo > 0 else 0.0,
            'White (%)': (white / loans_with_demo * 100) if loans_with_demo > 0 else 0.0,
            'Asian (%)': (asian / loans_with_demo * 100) if loans_with_demo > 0 else 0.0,
            'Native American (%)': (native_american / loans_with_demo * 100) if loans_with_demo > 0 else 0.0,
            'Hawaiian/Pacific Islander (%)': (hopi / loans_with_demo * 100) if loans_with_demo > 0 else 0.0,
            'Multi-Racial (%)': (multi_racial / loans_with_demo * 100) if loans_with_demo > 0 else 0.0,
            'LMIB (%)': (lmib / total * 100) if total > 0 else 0.0,
            'LMICT (%)': (lmict / total * 100) if total > 0 else 0.0,
            'MMCT (%)': (mmct / total * 100) if total > 0 else 0.0,
            'No Data (%)': (loans_no_data / total * 100) if total > 0 else 0.0
        })
    
    # Sort by total loans descending
    lender_data.sort(key=lambda x: x['Total Loans'], reverse=True)
    
    result = pd.DataFrame(lender_data)
    return result


def create_top_lenders_by_year_table_for_excel(df: pd.DataFrame, years: List[int], top_n: int = 10) -> pd.DataFrame:
    """
    Create top N lenders by year table for Excel export (2020-2024).
    Shows loan counts and amounts for top lenders across years.
    
    Args:
        df: DataFrame with raw mortgage data
        years: List of years to include (should be 2020-2024)
        top_n: Number of top lenders to include (default 10)
    
    Returns:
        DataFrame with columns: Lender Name, [Year] Loans, [Year] Amount ($000s) for each year
    """
    if df.empty or not years:
        return pd.DataFrame()
    
    # Get top N lenders from latest year
    latest_year = max(years)
    latest_year_df = df[df['year'] == latest_year].copy()
    
    if latest_year_df.empty:
        return pd.DataFrame()
    
    # Aggregate by lender for latest year to get top N
    latest_year_lenders = latest_year_df.groupby('lender_name').agg({
        'total_originations': 'sum'
    }).reset_index()
    latest_year_lenders = latest_year_lenders.sort_values('total_originations', ascending=False)
    top_lender_names = latest_year_lenders.head(top_n)['lender_name'].tolist()
    
    # Build result data
    result_data = []
    
    # Header row
    header = ['Lender Name']
    for year in sorted(years):
        header.append(f'{year} Loans')
    for year in sorted(years):
        header.append(f'{year} Amount ($000s)')
    result_data.append(header)
    
    # Data rows for each top lender
    for lender_name in top_lender_names:
        row = [lender_name]
        
        # Add loan counts for each year
        for year in sorted(years):
            year_df = df[(df['year'] == year) & (df['lender_name'] == lender_name)]
            total_loans = int(year_df['total_originations'].sum()) if not year_df.empty else 0
            row.append(total_loans)
        
        # Add loan amounts for each year (in thousands)
        for year in sorted(years):
            year_df = df[(df['year'] == year) & (df['lender_name'] == lender_name)]
            # Try different column names for loan amount
            if not year_df.empty:
                if 'total_loan_amount' in year_df.columns:
                    total_amount = year_df['total_loan_amount'].sum() / 1000
                elif 'loan_amount' in year_df.columns:
                    total_amount = year_df['loan_amount'].sum() / 1000
                else:
                    total_amount = 0
            else:
                total_amount = 0
            row.append(total_amount)
        
        result_data.append(row)
    
    result = pd.DataFrame(result_data[1:], columns=result_data[0])
    return result


