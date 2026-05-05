"""Lender neighborhood income section table."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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
                from justdata.apps.lendsight.report_builder import map_lender_type
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


