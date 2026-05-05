"""Lender borrower income section table."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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
            'Low to Moderate Income Borrowers (%) (≤80% of AMFI)': f"{(lmib_calculated / denominator * 100) if denominator > 0 else 0:.1f}",
            'Low Income Borrowers (%) (≤50% of AMFI)': f"{(low / denominator * 100) if denominator > 0 else 0:.1f}",
            'Moderate Income Borrowers (%) (>50% and ≤80% of AMFI)': f"{(moderate / denominator * 100) if denominator > 0 else 0:.1f}",
            'Middle Income Borrowers (%) (>80% and ≤120% of AMFI)': f"{(middle / denominator * 100) if denominator > 0 else 0:.1f}",
            'Upper Income Borrowers (%) (>120% of AMFI)': f"{(upper / denominator * 100) if denominator > 0 else 0:.1f}"
        })
    
    lender_data.sort(key=lambda x: int(x['Total Loans'].replace(',', '')), reverse=True)
    
    return pd.DataFrame(lender_data)


