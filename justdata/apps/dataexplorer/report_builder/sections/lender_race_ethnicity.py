"""Lender race/ethnicity section table."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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
                from justdata.apps.lendsight.report_builder import map_lender_type
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


