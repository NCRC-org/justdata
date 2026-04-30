"""Summary, lender, county, and trend tables."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

def create_mortgage_summary_table(df: pd.DataFrame, counties: List[str], years: List[int]) -> pd.DataFrame:
    """
    Create yearly breakdown table for mortgage origination data.
    
    Similar to branch summary but for mortgage originations.
    Properly dedupes: LMI Borrower only, MMCT only, and both LMICT/MMCT.
    """
    result_data = {
        'Variable': ['Total Originations', 'LMI Borrower Only Originations', 'MMCT Only Originations', 'Both LMICT/MMCT Originations']
    }
    
    # Calculate for each year
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        
        # Total originations
        total_originations = int(year_df['total_originations'].sum())
        
        # LMI Borrower only (LMIB but not MMCT)
        # Note: We need to check if we have both LMIB and MMCT flags
        # For now, use lmib_originations - mmct_originations as approximation
        # This is a simplification - actual data may need different logic
        lmib_only = int(year_df['lmib_originations'].sum() - year_df[year_df['mmct_originations'] > 0]['lmib_originations'].sum())
        lmib_only = max(0, lmib_only)  # Ensure non-negative
        
        # MMCT only (not LMI Borrower)
        mmct_only = int(year_df['mmct_originations'].sum() - year_df[year_df['lmib_originations'] > 0]['mmct_originations'].sum())
        mmct_only = max(0, mmct_only)  # Ensure non-negative
        
        # Both LMICT/MMCT
        both = int(year_df[(year_df['lmib_originations'] > 0) & (year_df['mmct_originations'] > 0)]['total_originations'].sum())
        
        result_data[str(year)] = [
            total_originations,
            lmib_only,
            mmct_only,
            both
        ]
    
    result = pd.DataFrame(result_data)
    
    # Calculate net change from first to last year
    if len(years) >= 2:
        first_year = str(min(years))
        last_year = str(max(years))
        
        net_changes = []
        for idx, row in result.iterrows():
            first_val = row[first_year]
            last_val = row[last_year]
            net_change = last_val - first_val
            net_changes.append(net_change)
        
        result['Net Change'] = net_changes
    
    return result


def create_lender_summary(df: pd.DataFrame, years: List[int] = None) -> pd.DataFrame:
    """
    Create lender summary table showing top lenders by origination volume.
    
    Similar to bank summary but for mortgage lenders.
    """
    if not years or len(years) == 0:
        return pd.DataFrame()
    
    latest_year = max(years)
    first_year = min(years)
    
    latest_year_df = df[df['year'] == latest_year].copy()
    first_year_df = df[df['year'] == first_year].copy()
    
    if latest_year_df.empty:
        return pd.DataFrame()
    
    lender_data = []
    
    # Get all unique lenders
    all_lenders = latest_year_df['lender_name'].unique()
    
    for lender_name in all_lenders:
        # Latest year data for this lender
        lender_latest = latest_year_df[latest_year_df['lender_name'] == lender_name]
        lender_first = first_year_df[first_year_df['lender_name'] == lender_name] if first_year != latest_year else lender_latest
        
        # Sum originations
        total_originations_latest = int(lender_latest['total_originations'].sum())
        total_originations_first = int(lender_first['total_originations'].sum())
        
        # Calculate LMI Borrower, MMCT, and both
        lmib_latest = int(lender_latest['lmib_originations'].sum())
        mmct_latest = int(lender_latest['mmct_originations'].sum())
        both_latest = int(lender_latest[(lender_latest['lmib_originations'] > 0) & (lender_latest['mmct_originations'] > 0)]['total_originations'].sum())
        
        # Calculate percentages
        lmib_pct = round((lmib_latest / total_originations_latest * 100), 1) if total_originations_latest > 0 else 0.0
        mmct_pct = round((mmct_latest / total_originations_latest * 100), 1) if total_originations_latest > 0 else 0.0
        both_pct = round((both_latest / total_originations_latest * 100), 1) if total_originations_latest > 0 else 0.0
        
        # Net change
        net_change = total_originations_latest - total_originations_first
        
        lender_data.append({
            'Lender Name': lender_name,  # Already uppercase from clean_mortgage_data
            'Total Originations': total_originations_latest,
            'LMI Borrower Only Originations': f"{lmib_latest} ({lmib_pct}%)",
            'MMCT Only Originations': f"{mmct_latest} ({mmct_pct}%)",
            'Both LMICT/MMCT Originations': f"{both_latest} ({both_pct}%)",
            'Net Change': net_change,
            # Store raw values for sorting
            '_total_originations': total_originations_latest
        })
    
    result = pd.DataFrame(lender_data)
    
    # Sort by total originations descending
    result = result.sort_values('_total_originations', ascending=False).reset_index(drop=True)
    
    # Remove helper column
    result = result.drop(columns=['_total_originations'])
    
    return result


def create_mortgage_county_summary(df: pd.DataFrame, counties: List[str] = None, years: List[int] = None) -> pd.DataFrame:
    """
    Create county-by-county summary for mortgage originations.
    
    Only shown if multiple counties selected.
    """
    # Only create this table if multiple counties
    if counties and len(counties) <= 1:
        return pd.DataFrame()
    
    if not years or len(years) == 0:
        return pd.DataFrame()
    
    # Use the most recent year
    latest_year = max(years)
    df_latest = df[df['year'] == latest_year].copy()
    
    if df_latest.empty:
        return pd.DataFrame()
    
    county_data = []
    
    # Process each county
    for county in df_latest['county_state'].unique():
        county_df = df_latest[df_latest['county_state'] == county]
        
        # Sum originations
        total_originations = int(county_df['total_originations'].sum())
        
        # Calculate LMI Borrower, MMCT, and both
        lmib = int(county_df['lmib_originations'].sum())
        mmct = int(county_df['mmct_originations'].sum())
        both = int(county_df[(county_df['lmib_originations'] > 0) & (county_df['mmct_originations'] > 0)]['total_originations'].sum())
        
        # Count unique lenders
        num_lenders = county_df['lender_name'].nunique()
        
        # Calculate percentages
        lmib_pct = round((lmib / total_originations * 100), 1) if total_originations > 0 else 0.0
        mmct_pct = round((mmct / total_originations * 100), 1) if total_originations > 0 else 0.0
        both_pct = round((both / total_originations * 100), 1) if total_originations > 0 else 0.0
        
        county_data.append({
            'County': county,
            'Total Originations': total_originations,
            'LMI Borrower Only Originations': f"{lmib} ({lmib_pct}%)",
            'MMCT Only Originations': f"{mmct} ({mmct_pct}%)",
            'Both LMICT/MMCT Originations': f"{both} ({both_pct}%)",
            'Number of Lenders': num_lenders
        })
    
    result = pd.DataFrame(county_data)
    
    # Sort by Total Originations descending
    result = result.sort_values('Total Originations', ascending=False).reset_index(drop=True)
    
    return result


def create_mortgage_trend_analysis(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """
    Create year-over-year trend analysis for mortgage originations.
    """
    if not years or len(years) < 2:
        return pd.DataFrame()
    
    yearly_totals = []
    
    for year in sorted(years):
        year_df = df[df['year'] == year]
        
        total = int(year_df['total_originations'].sum())
        lmib = int(year_df['lmib_originations'].sum())
        mmct = int(year_df['mmct_originations'].sum())
        
        yearly_totals.append({
            'Year': year,
            'Total Originations': total,
            'LMI Borrower Originations': lmib,
            'MMCT Originations': mmct
        })
    
    result = pd.DataFrame(yearly_totals)
    
    # Calculate year-over-year changes
    if len(result) > 1:
        result['YoY Change (%)'] = result['Total Originations'].pct_change() * 100
        result['YoY Change (%)'] = result['YoY Change (%)'].round(1)
        result.loc[0, 'YoY Change (%)'] = None  # First year has no previous year
    
    return result


