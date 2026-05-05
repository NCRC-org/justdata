"""Lender neighborhood demographics section table."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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
    from justdata.apps.lendsight.report_builder import calculate_minority_quartiles, classify_tract_minority_quartile
    
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
                from justdata.apps.lendsight.report_builder import map_lender_type
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

