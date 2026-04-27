"""Top-lenders detailed section table."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from justdata.apps.lendsight.report_builder.formatting import map_lender_type

def create_top_lenders_detailed_table(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """
    Create detailed table showing top lenders by total loans in most recent year.
    
    For each lender, shows:
    - Lender Type (Bank, Mortgage, or Credit Union)
    - Total loans/applications (most recent year)
    - Share to each race/ethnic group (using same methodology as demographic overview)
    - Share to income and neighborhood indicators (LMIB, LMICT, MMCT)
    
    Lenders are sorted in descending order by total loans in the most recent year.
    All lenders are included; JavaScript handles showing/hiding rows beyond the first 10.
    """
    if not years:
        return pd.DataFrame()
    
    # Check required columns
    required_columns = ['lender_name', 'total_originations', 'hispanic_originations', 
                       'black_originations', 'white_originations', 'asian_originations',
                       'native_american_originations', 'hopi_originations', 'multi_racial_originations',
                       'lmib_originations', 'lmict_originations', 'mmct_originations',
                       'loans_with_demographic_data']
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        return pd.DataFrame()
    
    # FIRST: Calculate overall percentages across ALL YEARS (same logic as Section 1)
    # to determine which columns to include
    yearly_totals = []
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        if not year_df.empty:
            total_originations = int(year_df['total_originations'].sum())
            hispanic = int(year_df['hispanic_originations'].sum())
            black = int(year_df['black_originations'].sum())
            white = int(year_df['white_originations'].sum())
            asian = int(year_df['asian_originations'].sum())
            native_american = int(year_df['native_american_originations'].sum())
            hopi = int(year_df['hopi_originations'].sum())
            multi_racial = int(year_df['multi_racial_originations'].sum()) if 'multi_racial_originations' in year_df.columns else 0
            
            if 'loans_with_demographic_data' in year_df.columns:
                loans_with_demographics = int(year_df['loans_with_demographic_data'].sum())
            else:
                loans_with_demographics = hispanic + black + white + asian + native_american + hopi
            
            yearly_totals.append({
                'year': year,
                'total_originations': total_originations,
                'hispanic': hispanic,
                'black': black,
                'white': white,
                'asian': asian,
                'native_american': native_american,
                'hopi': hopi,
                'multi_racial': multi_racial,
                'loans_with_demographics': loans_with_demographics
            })
    
    # Use same logic as Section 1: max count across all years / max total across all years
    all_totals = [d['total_originations'] for d in yearly_totals]
    max_total = max(all_totals) if all_totals else 0
    
    # Calculate max percentage for each group across all years (matching Section 1 logic)
    # Order: White, Hispanic, Black, Asian, Native American, HoPI, Multi-Racial
    group_max_pct = {}
    group_total_share = {}  # For sorting by total share
    for group in ['white', 'hispanic', 'black', 'asian', 'native_american', 'hopi', 'multi_racial']:
        max_count = max([d[group] for d in yearly_totals]) if yearly_totals else 0
        # Use the year with max total as denominator for threshold check (same as Section 1)
        max_pct = (max_count / max_total * 100) if max_total > 0 else 0
        group_max_pct[group] = max_pct
        
        # Calculate total share for sorting
        total_count = sum([d[group] for d in yearly_totals]) if yearly_totals else 0
        total_loans_all_years = sum([d['loans_with_demographics'] for d in yearly_totals]) if yearly_totals else 0
        avg_share = (total_count / total_loans_all_years * 100) if total_loans_all_years > 0 else 0
        group_total_share[group] = avg_share
    
    # Determine which columns to include (>= 1% overall, matching Section 1)
    # Order: White, Hispanic, Black, Asian, Native American, HoPI, Multi-Racial
    include_white = group_max_pct.get('white', 0) >= 1.0
    include_hispanic = group_max_pct.get('hispanic', 0) >= 1.0
    include_black = group_max_pct.get('black', 0) >= 1.0
    include_asian = group_max_pct.get('asian', 0) >= 1.0
    include_native_american = group_max_pct.get('native_american', 0) >= 1.0
    include_hopi = group_max_pct.get('hopi', 0) >= 1.0
    # Always include multi-racial if it has any data (even if < 1%)
    include_multi_racial = group_max_pct.get('multi_racial', 0) > 0
    
    # NOW: Get most recent year data for the actual table
    latest_year = max(years)
    latest_year_df = df[df['year'] == latest_year].copy()
    
    if latest_year_df.empty:
        return pd.DataFrame()
    
    # Aggregate by lender (using latest year data only for the table)
    lender_data = []
    for lender_name in latest_year_df['lender_name'].unique():
        lender_df = latest_year_df[latest_year_df['lender_name'] == lender_name]
        
        total = int(lender_df['total_originations'].sum())
        loans_with_demo = int(lender_df['loans_with_demographic_data'].sum()) if 'loans_with_demographic_data' in lender_df.columns else total
        
        # Get lender type (if available)
        lender_type = None
        if 'lender_type' in lender_df.columns:
            lender_types = lender_df['lender_type'].dropna().unique()
            if len(lender_types) > 0:
                lender_type = lender_types[0]  # Use the first non-null type
        
        # Race/ethnicity originations
        white = int(lender_df['white_originations'].sum())
        hispanic = int(lender_df['hispanic_originations'].sum())
        black = int(lender_df['black_originations'].sum())
        asian = int(lender_df['asian_originations'].sum())
        native_american = int(lender_df['native_american_originations'].sum())
        hopi = int(lender_df['hopi_originations'].sum())
        multi_racial = int(lender_df['multi_racial_originations'].sum()) if 'multi_racial_originations' in lender_df.columns else 0
        
        # Income and neighborhood indicators
        lmib = int(lender_df['lmib_originations'].sum())
        lmict = int(lender_df['lmict_originations'].sum())
        mmct = int(lender_df['mmct_originations'].sum())
        
        lender_data.append({
            'lender_name': lender_name,
            'lender_type': lender_type,  # Include lender type
            'total_loans': total,
            'loans_with_demographic_data': loans_with_demo,
            'white': white,
            'hispanic': hispanic,
            'black': black,
            'asian': asian,
            'native_american': native_american,
            'hopi': hopi,
            'multi_racial': multi_racial,
            'lmib': lmib,
            'lmict': lmict,
            'mmct': mmct
        })
    
    # Sort by total loans descending
    lender_data.sort(key=lambda x: x['total_loans'], reverse=True)
    
    # Return all lenders - JavaScript will handle showing/hiding rows beyond the first 10
    # This allows the table to work for communities with fewer than 10 lenders
    if not lender_data:
        return pd.DataFrame()
    
    # Build result table
    result_rows = []
    
    for lender in lender_data:
        lender_name = lender['lender_name']  # Already uppercase from clean_mortgage_data
        total = lender['total_loans']
        loans_with_demo = lender['loans_with_demographic_data']
        
        # Calculate percentages for race/ethnicity (denominator = loans with demographic data)
        denominator_demo = loans_with_demo if loans_with_demo > 0 else total
        
        # Map lender type to simplified name
        mapped_lender_type = map_lender_type(lender['lender_type']) if lender['lender_type'] else ''
        
        # Calculate percentages for income/neighborhood (denominator = total loans)
        row_data = {
            'Lender Name': lender_name,  # Already uppercase from clean_mortgage_data
            'Lender Type': mapped_lender_type,
            'Total Loans': f"{total:,}"
        }
        
        # Race/ethnicity percentages - only include columns that are >= 1% overall
        # Order: White, Hispanic, Black, Asian, Native American, HoPI, Multi-Racial
        if include_white:
            white_pct = (lender['white'] / denominator_demo * 100) if denominator_demo > 0 else 0.0
            row_data['White (%)'] = f"{white_pct:.1f}"
        
        if include_hispanic:
            hispanic_pct = (lender['hispanic'] / denominator_demo * 100) if denominator_demo > 0 else 0.0
            row_data['Hispanic (%)'] = f"{hispanic_pct:.1f}"
        
        if include_black:
            black_pct = (lender['black'] / denominator_demo * 100) if denominator_demo > 0 else 0.0
            row_data['Black (%)'] = f"{black_pct:.1f}"
        
        if include_asian:
            asian_pct = (lender['asian'] / denominator_demo * 100) if denominator_demo > 0 else 0.0
            row_data['Asian (%)'] = f"{asian_pct:.1f}"
        
        if include_native_american:
            native_american_pct = (lender['native_american'] / denominator_demo * 100) if denominator_demo > 0 else 0.0
            row_data['Native American (%)'] = f"{native_american_pct:.1f}"
        
        if include_hopi:
            hopi_pct = (lender['hopi'] / denominator_demo * 100) if denominator_demo > 0 else 0.0
            row_data['Hawaiian/Pacific Islander (%)'] = f"{hopi_pct:.1f}"
        
        if include_multi_racial:
            multi_racial_pct = (lender['multi_racial'] / denominator_demo * 100) if denominator_demo > 0 else 0.0
            row_data['Multi-Racial (%)'] = f"{multi_racial_pct:.1f}"
        
        # Income and neighborhood indicator percentages (denominator = total loans)
        lmib_pct = (lender['lmib'] / total * 100) if total > 0 else 0.0
        lmict_pct = (lender['lmict'] / total * 100) if total > 0 else 0.0
        mmct_pct = (lender['mmct'] / total * 100) if total > 0 else 0.0
        
        row_data['LMIB (%)'] = f"{lmib_pct:.1f}"
        row_data['LMICT (%)'] = f"{lmict_pct:.1f}"
        row_data['MMCT (%)'] = f"{mmct_pct:.1f}"
        
        # Note: "No Data (%)" column removed per user request
        
        result_rows.append(row_data)
    
    result = pd.DataFrame(result_rows)
    return result


