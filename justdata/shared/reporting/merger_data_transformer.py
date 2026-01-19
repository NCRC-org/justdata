"""
Data transformation functions for MergerMeter analysis.

This module provides functions to transform raw query results from BigQuery
into standardized DataFrames suitable for the merger Excel generator.
"""

import pandas as pd
import numpy as np
from typing import Dict, Set, Optional
import logging

logger = logging.getLogger(__name__)


def transform_mortgage_data(
    subject_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    cbsa_name_map: Dict[str, str],
    required_cbsas: Set[str]
) -> pd.DataFrame:
    """
    Transform mortgage (HMDA) data for Excel output.

    Aggregates subject and peer data by CBSA, calculating key metrics:
    - Total loans, LMICT%, LMIB%, LMIB$, MMCT%
    - Demographic percentages: MINB%, Asian%, Black%, Native American%, HoPI%, Hispanic%

    Args:
        subject_df: Subject bank HMDA data with columns like total_loans, lmict_loans, etc.
        peer_df: Peer/market HMDA data with same structure
        cbsa_name_map: Mapping from CBSA code to CBSA name
        required_cbsas: Set of CBSA codes that must be included (from assessment areas)

    Returns:
        Transformed DataFrame with columns:
        - cbsa_code, cbsa_name
        - total_loans, lmict_loans, lmib_loans, lmib_amount, mmct_loans
        - minb_loans, asian_loans, black_loans, native_american_loans, hopi_loans, hispanic_loans
    """
    if subject_df is None or subject_df.empty:
        logger.warning("transform_mortgage_data: Empty subject DataFrame provided")
        return pd.DataFrame()

    # Make a copy to avoid modifying original
    result_df = subject_df.copy()

    # Ensure cbsa_code is string
    if 'cbsa_code' in result_df.columns:
        result_df['cbsa_code'] = result_df['cbsa_code'].astype(str).str.strip()

    # Add cbsa_name from map if not present
    if 'cbsa_name' not in result_df.columns or result_df['cbsa_name'].isna().all():
        result_df['cbsa_name'] = result_df['cbsa_code'].map(
            lambda x: cbsa_name_map.get(str(x), f"CBSA {x}")
        )

    # Ensure all required columns exist with default values
    required_columns = [
        'total_loans', 'lmict_loans', 'lmib_loans', 'lmib_amount', 'mmct_loans',
        'minb_loans', 'asian_loans', 'black_loans', 'native_american_loans',
        'hopi_loans', 'hispanic_loans'
    ]

    for col in required_columns:
        if col not in result_df.columns:
            result_df[col] = 0

    # Convert numeric columns to proper types
    for col in required_columns:
        result_df[col] = pd.to_numeric(result_df[col], errors='coerce').fillna(0)

    logger.info(f"transform_mortgage_data: Transformed {len(result_df)} rows")
    return result_df


def transform_sb_data(
    subject_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    cbsa_name_map: Dict[str, str],
    required_cbsas: Set[str]
) -> pd.DataFrame:
    """
    Transform small business (1071) lending data for Excel output.

    Aggregates subject and peer data by CBSA, calculating key metrics:
    - Total SB loans, LMICT count, Loans to businesses with revenue under $1M
    - Average loan amounts

    Args:
        subject_df: Subject bank SB data with columns like sb_loans_total, lmict_count, etc.
        peer_df: Peer/market SB data with same structure
        cbsa_name_map: Mapping from CBSA code to CBSA name
        required_cbsas: Set of CBSA codes that must be included

    Returns:
        Transformed DataFrame with columns:
        - cbsa_code, cbsa_name
        - sb_loans_total, lmict_count, loans_rev_under_1m_count
        - avg_sb_lmict_loan_amount, avg_loan_amt_rum_sb
    """
    if subject_df is None or subject_df.empty:
        logger.warning("transform_sb_data: Empty subject DataFrame provided")
        return pd.DataFrame()

    # Make a copy to avoid modifying original
    result_df = subject_df.copy()

    # Ensure cbsa_code is string
    if 'cbsa_code' in result_df.columns:
        result_df['cbsa_code'] = result_df['cbsa_code'].astype(str).str.strip()

    # Add cbsa_name from map if not present
    if 'cbsa_name' not in result_df.columns or result_df['cbsa_name'].isna().all():
        result_df['cbsa_name'] = result_df['cbsa_code'].map(
            lambda x: cbsa_name_map.get(str(x), f"CBSA {x}")
        )

    # Ensure all required columns exist with default values
    # Handle both naming conventions
    required_columns = [
        'sb_loans_total', 'lmict_count', 'loans_rev_under_1m_count',
        'avg_sb_lmict_loan_amount', 'avg_loan_amt_rum_sb'
    ]

    for col in required_columns:
        if col not in result_df.columns:
            result_df[col] = 0

    # Convert numeric columns to proper types
    for col in required_columns:
        result_df[col] = pd.to_numeric(result_df[col], errors='coerce').fillna(0)

    logger.info(f"transform_sb_data: Transformed {len(result_df)} rows")
    return result_df


def transform_branch_data(
    branch_df: pd.DataFrame,
    cbsa_name_map: Dict[str, str],
    required_cbsas: Set[str]
) -> pd.DataFrame:
    """
    Transform branch (FDIC) data for Excel output.

    Aggregates branch data by CBSA, calculating key metrics:
    - Total branches, branches in LMICT, branches in MMCT
    - Market/peer total branches for comparison

    Args:
        branch_df: Branch data with columns like total_branches, branches_in_lmict, etc.
        cbsa_name_map: Mapping from CBSA code to CBSA name
        required_cbsas: Set of CBSA codes that must be included

    Returns:
        Transformed DataFrame with columns:
        - cbsa_code, cbsa_name
        - total_branches, branches_in_lmict, branches_in_mmct
        - other_total_branches, other_branches_in_lmict, other_branches_in_mmct
    """
    if branch_df is None or branch_df.empty:
        logger.warning("transform_branch_data: Empty branch DataFrame provided")
        return pd.DataFrame()

    # Make a copy to avoid modifying original
    result_df = branch_df.copy()

    # Ensure cbsa_code is string
    if 'cbsa_code' in result_df.columns:
        result_df['cbsa_code'] = result_df['cbsa_code'].astype(str).str.strip()

    # Add cbsa_name from map if not present
    if 'cbsa_name' not in result_df.columns or result_df['cbsa_name'].isna().all():
        result_df['cbsa_name'] = result_df['cbsa_code'].map(
            lambda x: cbsa_name_map.get(str(x), f"CBSA {x}")
        )

    # Ensure all required columns exist with default values
    required_columns = [
        'total_branches', 'branches_in_lmict', 'branches_in_mmct',
        'other_total_branches', 'other_branches_in_lmict', 'other_branches_in_mmct'
    ]

    for col in required_columns:
        if col not in result_df.columns:
            result_df[col] = 0

    # Convert numeric columns to proper types
    for col in required_columns:
        result_df[col] = pd.to_numeric(result_df[col], errors='coerce').fillna(0)

    logger.info(f"transform_branch_data: Transformed {len(result_df)} rows")
    return result_df
