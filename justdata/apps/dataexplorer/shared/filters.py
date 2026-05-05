"""Shared dataexplorer utilities used by both area_report_builder and lender_analysis_core."""
import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


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


