#!/usr/bin/env python3
"""
Lender Analysis Report Builder
Builds report data structures for lender analysis reports.
Shows last 3 years with Subject/Peer/Difference columns for each year.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Optional import for chi-squared testing
try:
    from scipy.stats import chi2_contingency
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available. Chi-squared testing will be disabled.")

# Import LendSight's proven table building functions
from justdata.apps.lendsight.mortgage_report_builder import (
    create_demographic_overview_table,
    create_income_borrowers_table,
    create_income_tracts_table,
    create_minority_tracts_table,
    calculate_mortgage_hhi_for_year
)
from justdata.apps.lendsight.hud_processor import get_hud_data_for_counties


def chi_squared_test_significant(
    subject_with: int,
    subject_total: int,
    peer_with: int,
    peer_total: int,
    alpha: float = 0.05
) -> bool:
    """
    Perform chi-squared test to determine if the difference between subject and peer is statistically significant.
    
    Args:
        subject_with: Count of subject loans with the characteristic
        subject_total: Total count of subject loans
        peer_with: Count of peer loans with the characteristic
        peer_total: Total count of peer loans
        alpha: Significance level (default 0.05)
        
    Returns:
        True if difference is statistically significant, False otherwise
    """
    if subject_total == 0 or peer_total == 0:
        return False
    
    # Create 2x2 contingency table
    # Row 1: Subject (with, without)
    # Row 2: Peer (with, without)
    subject_without = subject_total - subject_with
    peer_without = peer_total - peer_with
    
    contingency_table = np.array([
        [subject_with, subject_without],
        [peer_with, peer_without]
    ])
    
    # Check if any cell has expected frequency < 5 (chi-squared assumption)
    # If so, we might want to use Fisher's exact test, but for now we'll proceed
    # with a warning if expected frequencies are too low
    
    if not SCIPY_AVAILABLE:
        # If scipy is not available, return False (not significant)
        logger.debug(f"Chi-squared test skipped: scipy not available. Would test: subject={subject_with}/{subject_total}, peer={peer_with}/{peer_total}")
        return False
    
    try:
        chi2, p_value, dof, expected = chi2_contingency(contingency_table)
        
        # Check expected frequencies
        if np.any(expected < 5):
            # If expected frequencies are too low, chi-squared may not be appropriate
            # But we'll still use it with a note that results may be less reliable
            pass
        
        return p_value < alpha
    except Exception as e:
        logger.warning(f"Error in chi-squared test: {e}")
        return False


def calculate_peer_average(df: pd.DataFrame, metric_col: str, total_col: str = 'total_originations') -> float:
    """
    Calculate weighted average for a metric across all peer lenders.
    
    Args:
        df: DataFrame with peer lender data
        metric_col: Column name for the metric (e.g., 'hispanic_originations')
        total_col: Column name for total loans (for weighting)
        
    Returns:
        Weighted average percentage
    """
    if df.empty or metric_col not in df.columns:
        return 0.0
    
    total_metric = df[metric_col].sum()
    total_loans = df[total_col].sum() if total_col in df.columns else len(df)
    
    if total_loans > 0:
        return (total_metric / total_loans) * 100
    return 0.0


def create_lender_comparison_table(
    subject_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    years: List[int],
    metric_configs: List[tuple],
    format_type: str = 'percentage'
) -> pd.DataFrame:
    """
    Create a comparison table with Subject/Peer/Diff columns for each year.
    Years are shown in a note row above the header.
    
    Args:
        subject_df: DataFrame with subject lender data
        peer_df: DataFrame with peer lender data (aggregated)
        years: List of years (should be last 3 years)
        metric_configs: List of (metric_name, metric_key, format_type) tuples
        format_type: 'percentage', 'currency', or 'count'
        
    Returns:
        DataFrame with Metric column and Subject/Peer/Diff columns for each year.
        Also includes a 'year_labels' key in the metadata for the year header row.
    """
    if subject_df.empty:
        return pd.DataFrame()
    
    # Ensure we only use last 3 years
    recent_years = sorted(years)[-3:] if len(years) > 3 else sorted(years)
    
    rows = []
    for metric_name, metric_key, metric_format in metric_configs:
        row = {'Metric': metric_name}
        
        for year in recent_years:
            # Filter to this year
            subject_year_df = subject_df[subject_df['year'] == year] if 'year' in subject_df.columns else pd.DataFrame()
            peer_year_df = peer_df[peer_df['year'] == year] if 'year' in peer_df.columns else pd.DataFrame()
            
            if subject_year_df.empty:
                row[f'{year}_Subject'] = 'N/A'
                row[f'{year}_Peer'] = 'N/A'
                row[f'{year}_Diff'] = 'N/A'
                continue
            
            # Calculate subject value
            if metric_key in subject_year_df.columns:
                if metric_format == 'percentage':
                    # Calculate percentage
                    # For race/ethnicity metrics, use loans_with_demographic_data as denominator
                    # For other metrics, use total_originations
                    is_race_metric = metric_key in ['hispanic_originations', 'black_originations', 'white_originations',
                                                     'asian_originations', 'native_american_originations', 'hopi_originations',
                                                     'multi_racial_originations']
                    
                    if is_race_metric and 'loans_with_demographic_data' in subject_year_df.columns:
                        subject_total = subject_year_df['loans_with_demographic_data'].sum()
                        if subject_total == 0:
                            # Fallback to total_originations if loans_with_demographic_data is 0
                            subject_total = subject_year_df['total_originations'].sum() if 'total_originations' in subject_year_df.columns else 0
                    else:
                        subject_total = subject_year_df['total_originations'].sum() if 'total_originations' in subject_year_df.columns else 0
                    
                    if subject_total > 0:
                        subject_metric = subject_year_df[metric_key].sum()
                        subject_value = (subject_metric / subject_total * 100)
                    else:
                        subject_value = 0.0
                elif metric_format == 'currency':
                    # Average currency value
                    subject_value = subject_year_df[metric_key].mean() if metric_key in subject_year_df.columns else 0.0
                else:  # count
                    subject_value = float(subject_year_df[metric_key].sum())
            else:
                subject_value = 0.0
            
            # Calculate peer average
            if not peer_year_df.empty and metric_key in peer_year_df.columns:
                if metric_format == 'percentage':
                    # For race/ethnicity metrics, use loans_with_demographic_data as denominator
                    is_race_metric = metric_key in ['hispanic_originations', 'black_originations', 'white_originations',
                                                     'asian_originations', 'native_american_originations', 'hopi_originations',
                                                     'multi_racial_originations']
                    if is_race_metric and 'loans_with_demographic_data' in peer_year_df.columns:
                        # Calculate weighted average using loans_with_demographic_data as denominator
                        total_metric = peer_year_df[metric_key].sum()
                        total_with_demo = peer_year_df['loans_with_demographic_data'].sum()
                        if total_with_demo > 0:
                            peer_value = (total_metric / total_with_demo) * 100
                        else:
                            # Fallback to calculate_peer_average if loans_with_demographic_data is 0
                            peer_value = calculate_peer_average(peer_year_df, metric_key)
                    else:
                        peer_value = calculate_peer_average(peer_year_df, metric_key)
                elif metric_format == 'currency':
                    peer_value = float(peer_year_df[metric_key].mean()) if len(peer_year_df) > 0 else 0.0
                else:  # count
                    peer_value = float(peer_year_df[metric_key].sum())
            else:
                # If no peer data, set to 0.0 but still calculate diff
                peer_value = 0.0
                logger.debug(f"No peer data for {metric_key} in year {year}")
            
            # Calculate raw counts for chi-squared test (for percentage metrics)
            subject_with_count = 0
            subject_total_count = 0
            peer_with_count = 0
            peer_total_count = 0
            is_significant = False
            
            if metric_format == 'percentage':
                # Get raw counts for chi-squared test
                # For race metrics, use loans_with_demographic_data as total
                is_race_metric = metric_key in ['hispanic_originations', 'black_originations', 'white_originations',
                                                 'asian_originations', 'native_american_originations', 'hopi_originations',
                                                 'multi_racial_originations']
                
                if metric_key in subject_year_df.columns:
                    subject_with_count = int(subject_year_df[metric_key].sum())
                    if is_race_metric and 'loans_with_demographic_data' in subject_year_df.columns:
                        subject_total_count = int(subject_year_df['loans_with_demographic_data'].sum())
                        if subject_total_count == 0:
                            subject_total_count = int(subject_year_df['total_originations'].sum()) if 'total_originations' in subject_year_df.columns else 0
                    else:
                        subject_total_count = int(subject_year_df['total_originations'].sum()) if 'total_originations' in subject_year_df.columns else 0
                else:
                    subject_with_count = 0
                    subject_total_count = 0
                
                if not peer_year_df.empty and metric_key in peer_year_df.columns:
                    peer_with_count = int(peer_year_df[metric_key].sum())
                    if is_race_metric and 'loans_with_demographic_data' in peer_year_df.columns:
                        peer_total_count = int(peer_year_df['loans_with_demographic_data'].sum())
                        if peer_total_count == 0:
                            peer_total_count = int(peer_year_df['total_originations'].sum()) if 'total_originations' in peer_year_df.columns else 0
                    else:
                        peer_total_count = int(peer_year_df['total_originations'].sum()) if 'total_originations' in peer_year_df.columns else 0
                else:
                    peer_with_count = 0
                    peer_total_count = 0
                
                # Perform chi-squared test
                if subject_total_count > 0 and peer_total_count > 0:
                    is_significant = chi_squared_test_significant(
                        subject_with_count,
                        subject_total_count,
                        peer_with_count,
                        peer_total_count
                    )
            
            # Format values
            if metric_format == 'percentage':
                subject_str = f"{subject_value:.1f}%"
                peer_str = f"{peer_value:.1f}%"
                # Calculate difference in percentage points
                difference = float(subject_value) - float(peer_value)
                if pd.isna(difference) or not isinstance(difference, (int, float)):
                    diff_str = 'N/A'
                    is_significant = False
                else:
                    diff_str = f"{difference:+.1f}pp"
                    # Add asterisk if significant and negative
                    if is_significant and difference < 0:
                        diff_str += '*'
            elif metric_format == 'currency':
                subject_str = f"${subject_value:,.0f}"
                peer_str = f"${peer_value:,.0f}"
                difference = float(subject_value) - float(peer_value)
                if pd.isna(difference) or not isinstance(difference, (int, float)):
                    diff_str = 'N/A'
                else:
                    diff_str = f"${difference:+,.0f}"
            else:  # count
                subject_str = f"{int(subject_value):,}"
                peer_str = f"{int(peer_value):,}"
                difference = float(subject_value) - float(peer_value)
                if pd.isna(difference) or not isinstance(difference, (int, float)):
                    diff_str = 'N/A'
                else:
                    diff_str = f"{int(difference):+,}"
            
            row[f'{year}_Subject'] = subject_str
            row[f'{year}_Peer'] = peer_str
            # Don't calculate diff for Total Loans
            if metric_name == 'Total Loans':
                row[f'{year}_Diff'] = '—'  # Use em dash to indicate no diff
                row[f'{year}_Diff_Significant'] = False
                row[f'{year}_Diff_IsNegative'] = False
            else:
                row[f'{year}_Diff'] = diff_str
                row[f'{year}_Diff_Significant'] = is_significant
                row[f'{year}_Diff_IsNegative'] = difference < 0 if isinstance(difference, (int, float)) and not pd.isna(difference) else False
                # Debug logging
                if diff_str == 'N/A' or diff_str == '':
                    logger.warning(f"Diff calculation issue for {metric_name} in year {year}: subject={subject_value}, peer={peer_value}, diff_str={diff_str}")
        
        rows.append(row)
    
    result_df = pd.DataFrame(rows)
    return result_df


def create_lender_race_ethnicity_comparison_table(
    subject_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    years: List[int],
    census_data: Dict = None
) -> pd.DataFrame:
    """
    Create loans by race and ethnicity comparison table.
    
    Structure: Metric | 2022 Subject | 2022 Peer | 2022 Difference | 2023 Subject | ...
    """
    if subject_df.empty:
        return pd.DataFrame()
    
    # Get race columns
    race_columns = ['hispanic_originations', 'black_originations', 'white_originations', 
                   'asian_originations', 'native_american_originations', 'hopi_originations',
                   'multi_racial_originations']
    
    # Check which race columns exist
    available_races = [col for col in race_columns if col in subject_df.columns]
    if not available_races:
        logger.warning("No race/ethnicity columns found in subject data")
        return pd.DataFrame()
    
    # Build metric configs - include races that are >= 1% of total loans, but always include Native American, HoPI, and Multi-Racial
    recent_years = sorted(years)[-3:] if len(years) > 3 else sorted(years)
    
    # Calculate total loans across all years to determine which races are >= 1%
    total_all_loans = int(subject_df['total_originations'].sum()) if 'total_originations' in subject_df.columns else 0
    total_all_loans_with_demo = int(subject_df['loans_with_demographic_data'].sum()) if 'loans_with_demographic_data' in subject_df.columns else total_all_loans
    denominator_all = total_all_loans_with_demo if total_all_loans_with_demo > 0 else total_all_loans
    
    # Determine which races to include (>= 1% of total, but always include Native American, HoPI, and Multi-Racial)
    included_races = []
    race_names = {
        'hispanic_originations': 'Hispanic (%)',
        'black_originations': 'Black (%)',
        'white_originations': 'White (%)',
        'asian_originations': 'Asian (%)',
        'native_american_originations': 'Native American (%)',
        'hopi_originations': 'Hawaiian/Pacific Islander (%)',
        'multi_racial_originations': 'Multi-Racial (non-Hispanic and two or more races) (%)'
    }
    
    # Always include Native American, HoPI, and Multi-Racial regardless of percentage
    always_include = ['native_american_originations', 'hopi_originations', 'multi_racial_originations']
    
    for race_col in available_races:
        total_race = int(subject_df[race_col].sum())
        race_pct = (total_race / denominator_all * 100) if denominator_all > 0 else 0
        # Include if >= 1% OR if it's Native American, HoPI, or Multi-Racial
        if race_pct >= 1.0 or race_col in always_include:
            included_races.append((race_names[race_col], race_col, 'percentage'))
    
    # Add Total Loans row
    metric_configs = [('Total Loans', 'total_originations', 'count')] + included_races
    
    return create_lender_comparison_table(subject_df, peer_df, years, metric_configs, format_type='percentage')


def create_lender_borrower_income_comparison_table(
    subject_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    years: List[int],
    hud_data: Dict = None
) -> pd.DataFrame:
    """
    Create loans by borrower income comparison table.
    """
    if subject_df.empty:
        return pd.DataFrame()
    
    required_cols = ['total_originations', 'lmib_originations', 
                     'low_income_borrower_originations', 'moderate_income_borrower_originations',
                     'middle_income_borrower_originations', 'upper_income_borrower_originations']
    
    if not all(col in subject_df.columns for col in required_cols):
        logger.warning("Missing required income columns")
        return pd.DataFrame()
    
    metric_configs = [
        ('Total Loans', 'total_originations', 'count'),
        ('Low to Moderate Income Borrowers (%) (≤80% of AMFI)', 'lmib_originations', 'percentage'),
        ('Low Income Borrowers (%) (≤50% of AMFI)', 'low_income_borrower_originations', 'percentage'),
        ('Moderate Income Borrowers (%) (>50% and ≤80% of AMFI)', 'moderate_income_borrower_originations', 'percentage'),
        ('Middle Income Borrowers (%) (>80% and ≤120% of AMFI)', 'middle_income_borrower_originations', 'percentage'),
        ('Upper Income Borrowers (%) (>120% of AMFI)', 'upper_income_borrower_originations', 'percentage')
    ]
    
    return create_lender_comparison_table(subject_df, peer_df, years, metric_configs, format_type='percentage')


def create_lender_neighborhood_income_comparison_table(
    subject_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    years: List[int],
    hud_data: Dict = None,
    census_data: Dict = None
) -> pd.DataFrame:
    """
    Create loans by neighborhood income comparison table.
    """
    if subject_df.empty:
        return pd.DataFrame()
    
    required_cols = ['total_originations', 'lmict_originations',
                     'low_income_tract_originations', 'moderate_income_tract_originations',
                     'middle_income_tract_originations', 'upper_income_tract_originations']
    
    if not all(col in subject_df.columns for col in required_cols):
        logger.warning("Missing required tract income columns")
        return pd.DataFrame()
    
    metric_configs = [
        ('Total Loans', 'total_originations', 'count'),
        ('Low to Moderate Income Census Tracts (%) (≤80% of AMFI)', 'lmict_originations', 'percentage'),
        ('Low Income Census Tracts (%) (≤50% of AMFI)', 'low_income_tract_originations', 'percentage'),
        ('Moderate Income Census Tracts (%) (>50% and ≤80% of AMFI)', 'moderate_income_tract_originations', 'percentage'),
        ('Middle Income Census Tracts (%) (>80% and ≤120% of AMFI)', 'middle_income_tract_originations', 'percentage'),
        ('Upper Income Census Tracts (%) (>120% of AMFI)', 'upper_income_tract_originations', 'percentage')
    ]
    
    return create_lender_comparison_table(subject_df, peer_df, years, metric_configs, format_type='percentage')


def create_lender_neighborhood_demographics_comparison_table(
    subject_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    years: List[int],
    census_data: Dict = None
) -> pd.DataFrame:
    """
    Create loans by neighborhood demographics comparison table.
    """
    if subject_df.empty:
        return pd.DataFrame()
    
    required_cols = ['total_originations', 'mmct_originations',
                     'tract_minority_population_percent', 'tract_code']
    
    if not all(col in subject_df.columns for col in required_cols):
        logger.warning("Missing required demographics columns")
        return pd.DataFrame()
    
    # Use fixed percentage ranges (not quartiles) because lender analysis may span multiple CBSAs
    # Fixed thresholds ensure consistent categorization across different geographies
    # Fixed thresholds ensure consistent categorization across different geographies
    # High Minority: ≥80%
    # Middle Minority: 50%-<80%
    # Moderate Minority: 20%-<50%
    # Low Minority: <20%
    
    # Build comparison table manually with fixed ranges
    recent_years = sorted(years)[-3:] if len(years) > 3 else sorted(years)
    
    # Create copies for filtering
    subject_df_copy = subject_df.copy()
    peer_df_copy = peer_df.copy()
    
    rows = []
    
    # Total Loans
    total_row = {'Metric': 'Total Loans'}
    for year in recent_years:
        subject_year = subject_df_copy[subject_df_copy['year'] == year] if 'year' in subject_df_copy.columns else pd.DataFrame()
        peer_year = peer_df_copy[peer_df_copy['year'] == year] if 'year' in peer_df_copy.columns else pd.DataFrame()
        
        subject_total = int(subject_year['total_originations'].sum()) if not subject_year.empty else 0
        peer_total = int(peer_year['total_originations'].sum()) if not peer_year.empty else 0
        difference = subject_total - peer_total
        
        total_row[f'{year}_Subject'] = f"{subject_total:,}"
        total_row[f'{year}_Peer'] = f"{peer_total:,}"
        total_row[f'{year}_Diff'] = '—'  # No diff for Total Loans
        total_row[f'{year}_Diff_Significant'] = False
        total_row[f'{year}_Diff_IsNegative'] = False
    rows.append(total_row)
    
    # Majority Minority (light grey background)
    mmct_row = {'Metric': 'Majority Minority (%)'}
    for year in recent_years:
        subject_year = subject_df_copy[subject_df_copy['year'] == year] if 'year' in subject_df_copy.columns else pd.DataFrame()
        peer_year = peer_df_copy[peer_df_copy['year'] == year] if 'year' in peer_df_copy.columns else pd.DataFrame()
        
        if not subject_year.empty:
            subject_mmct = int(subject_year['mmct_originations'].sum())
            subject_total = int(subject_year['total_originations'].sum())
            subject_pct = (subject_mmct / subject_total * 100) if subject_total > 0 else 0.0
        else:
            subject_pct = 0.0
        
        if not peer_year.empty:
            peer_mmct = int(peer_year['mmct_originations'].sum())
            peer_total = int(peer_year['total_originations'].sum())
            peer_pct = (peer_mmct / peer_total * 100) if peer_total > 0 else 0.0
        else:
            peer_pct = 0.0
        
        difference = subject_pct - peer_pct
        
        # Chi-squared test for significance
        subject_mmct_count = int(subject_year['mmct_originations'].sum()) if not subject_year.empty else 0
        subject_total_count = int(subject_year['total_originations'].sum()) if not subject_year.empty else 0
        peer_mmct_count = int(peer_year['mmct_originations'].sum()) if not peer_year.empty else 0
        peer_total_count = int(peer_year['total_originations'].sum()) if not peer_year.empty else 0
        is_significant = False
        if subject_total_count > 0 and peer_total_count > 0:
            is_significant = chi_squared_test_significant(
                subject_mmct_count, subject_total_count,
                peer_mmct_count, peer_total_count
            )
        
        diff_str = f"{difference:+.1f}pp"
        if is_significant and difference < 0:
            diff_str += '*'
        
        mmct_row[f'{year}_Subject'] = f"{subject_pct:.1f}%"
        mmct_row[f'{year}_Peer'] = f"{peer_pct:.1f}%"
        mmct_row[f'{year}_Diff'] = diff_str
        mmct_row[f'{year}_Diff_Significant'] = is_significant
        mmct_row[f'{year}_Diff_IsNegative'] = difference < 0
    rows.append(mmct_row)
    
    # Fixed percentage ranges (ordered: High, Middle, Moderate, Low)
    # High Minority: ≥80%
    high_row = {'Metric': 'High Minority (≥80%) (%)'}
    for year in recent_years:
        subject_year = subject_df_copy[subject_df_copy['year'] == year] if 'year' in subject_df_copy.columns else pd.DataFrame()
        peer_year = peer_df_copy[peer_df_copy['year'] == year] if 'year' in peer_df_copy.columns else pd.DataFrame()
        
        # Initialize variables
        subject_high = 0
        subject_total = 0
        peer_high = 0
        peer_total = 0
        
        if not subject_year.empty:
            subject_high = int(subject_year[
                (subject_year['tract_minority_population_percent'].notna()) &
                (subject_year['tract_minority_population_percent'] >= 80.0) & 
                (subject_year['tract_minority_population_percent'] <= 100.0)
            ]['total_originations'].sum())
            subject_total = int(subject_year['total_originations'].sum())
            subject_pct = (subject_high / subject_total * 100) if subject_total > 0 else 0.0
        else:
            subject_pct = 0.0
        
        if not peer_year.empty:
            peer_high = int(peer_year[
                (peer_year['tract_minority_population_percent'].notna()) &
                (peer_year['tract_minority_population_percent'] >= 80.0) & 
                (peer_year['tract_minority_population_percent'] <= 100.0)
            ]['total_originations'].sum())
            peer_total = int(peer_year['total_originations'].sum())
            peer_pct = (peer_high / peer_total * 100) if peer_total > 0 else 0.0
        else:
            peer_pct = 0.0
        
        difference = subject_pct - peer_pct
        
        # Chi-squared test for significance
        is_significant = False
        if subject_total > 0 and peer_total > 0:
            is_significant = chi_squared_test_significant(
                subject_high, subject_total,
                peer_high, peer_total
            )
        
        diff_str = f"{difference:+.1f}pp"
        if is_significant and difference < 0:
            diff_str += '*'
        
        high_row[f'{year}_Subject'] = f"{subject_pct:.1f}%"
        high_row[f'{year}_Peer'] = f"{peer_pct:.1f}%"
        high_row[f'{year}_Diff'] = diff_str
        high_row[f'{year}_Diff_Significant'] = is_significant
        high_row[f'{year}_Diff_IsNegative'] = difference < 0
    rows.append(high_row)
    
    # Middle Minority: 50%-<80%
    middle_row = {'Metric': 'Middle Minority (50%-<80%) (%)'}
    for year in recent_years:
        subject_year = subject_df_copy[subject_df_copy['year'] == year] if 'year' in subject_df_copy.columns else pd.DataFrame()
        peer_year = peer_df_copy[peer_df_copy['year'] == year] if 'year' in peer_df_copy.columns else pd.DataFrame()
        
        # Initialize variables
        subject_middle = 0
        subject_total = 0
        peer_middle = 0
        peer_total = 0
        
        if not subject_year.empty:
            subject_middle = int(subject_year[
                (subject_year['tract_minority_population_percent'].notna()) &
                (subject_year['tract_minority_population_percent'] >= 50.0) & 
                (subject_year['tract_minority_population_percent'] < 80.0)
            ]['total_originations'].sum())
            subject_total = int(subject_year['total_originations'].sum())
            subject_pct = (subject_middle / subject_total * 100) if subject_total > 0 else 0.0
        else:
            subject_pct = 0.0
        
        if not peer_year.empty:
            peer_middle = int(peer_year[
                (peer_year['tract_minority_population_percent'].notna()) &
                (peer_year['tract_minority_population_percent'] >= 50.0) & 
                (peer_year['tract_minority_population_percent'] < 80.0)
            ]['total_originations'].sum())
            peer_total = int(peer_year['total_originations'].sum())
            peer_pct = (peer_middle / peer_total * 100) if peer_total > 0 else 0.0
        else:
            peer_pct = 0.0
        
        difference = subject_pct - peer_pct
        
        # Chi-squared test for significance
        is_significant = False
        if subject_total > 0 and peer_total > 0:
            is_significant = chi_squared_test_significant(
                subject_middle, subject_total,
                peer_middle, peer_total
            )
        
        diff_str = f"{difference:+.1f}pp"
        if is_significant and difference < 0:
            diff_str += '*'
        
        middle_row[f'{year}_Subject'] = f"{subject_pct:.1f}%"
        middle_row[f'{year}_Peer'] = f"{peer_pct:.1f}%"
        middle_row[f'{year}_Diff'] = diff_str
        middle_row[f'{year}_Diff_Significant'] = is_significant
        middle_row[f'{year}_Diff_IsNegative'] = difference < 0
    rows.append(middle_row)
    
    # Moderate Minority: 20%-<50%
    moderate_row = {'Metric': 'Moderate Minority (20%-<50%) (%)'}
    for year in recent_years:
        subject_year = subject_df_copy[subject_df_copy['year'] == year] if 'year' in subject_df_copy.columns else pd.DataFrame()
        peer_year = peer_df_copy[peer_df_copy['year'] == year] if 'year' in peer_df_copy.columns else pd.DataFrame()
        
        # Initialize variables
        subject_moderate = 0
        subject_total = 0
        peer_moderate = 0
        peer_total = 0
        
        if not subject_year.empty:
            subject_moderate = int(subject_year[
                (subject_year['tract_minority_population_percent'].notna()) &
                (subject_year['tract_minority_population_percent'] >= 20.0) & 
                (subject_year['tract_minority_population_percent'] < 50.0)
            ]['total_originations'].sum())
            subject_total = int(subject_year['total_originations'].sum())
            subject_pct = (subject_moderate / subject_total * 100) if subject_total > 0 else 0.0
        else:
            subject_pct = 0.0
        
        if not peer_year.empty:
            peer_moderate = int(peer_year[
                (peer_year['tract_minority_population_percent'].notna()) &
                (peer_year['tract_minority_population_percent'] >= 20.0) & 
                (peer_year['tract_minority_population_percent'] < 50.0)
            ]['total_originations'].sum())
            peer_total = int(peer_year['total_originations'].sum())
            peer_pct = (peer_moderate / peer_total * 100) if peer_total > 0 else 0.0
        else:
            peer_pct = 0.0
        
        difference = subject_pct - peer_pct
        
        # Chi-squared test for significance
        is_significant = False
        if subject_total > 0 and peer_total > 0:
            is_significant = chi_squared_test_significant(
                subject_moderate, subject_total,
                peer_moderate, peer_total
            )
        
        diff_str = f"{difference:+.1f}pp"
        if is_significant and difference < 0:
            diff_str += '*'
        
        moderate_row[f'{year}_Subject'] = f"{subject_pct:.1f}%"
        moderate_row[f'{year}_Peer'] = f"{peer_pct:.1f}%"
        moderate_row[f'{year}_Diff'] = diff_str
        moderate_row[f'{year}_Diff_Significant'] = is_significant
        moderate_row[f'{year}_Diff_IsNegative'] = difference < 0
    rows.append(moderate_row)
    
    # Low Minority: <20%
    low_row = {'Metric': 'Low Minority (<20%) (%)'}
    for year in recent_years:
        subject_year = subject_df_copy[subject_df_copy['year'] == year] if 'year' in subject_df_copy.columns else pd.DataFrame()
        peer_year = peer_df_copy[peer_df_copy['year'] == year] if 'year' in peer_df_copy.columns else pd.DataFrame()
        
        # Initialize variables
        subject_low = 0
        subject_total = 0
        peer_low = 0
        peer_total = 0
        
        if not subject_year.empty:
            subject_low = int(subject_year[
                (subject_year['tract_minority_population_percent'].notna()) &
                (subject_year['tract_minority_population_percent'] >= 0.0) & 
                (subject_year['tract_minority_population_percent'] < 20.0)
            ]['total_originations'].sum())
            subject_total = int(subject_year['total_originations'].sum())
            subject_pct = (subject_low / subject_total * 100) if subject_total > 0 else 0.0
        else:
            subject_pct = 0.0
        
        if not peer_year.empty:
            peer_low = int(peer_year[
                (peer_year['tract_minority_population_percent'].notna()) &
                (peer_year['tract_minority_population_percent'] >= 0.0) & 
                (peer_year['tract_minority_population_percent'] < 20.0)
            ]['total_originations'].sum())
            peer_total = int(peer_year['total_originations'].sum())
            peer_pct = (peer_low / peer_total * 100) if peer_total > 0 else 0.0
        else:
            peer_pct = 0.0
        
        difference = subject_pct - peer_pct
        
        # Chi-squared test for significance
        is_significant = False
        if subject_total > 0 and peer_total > 0:
            is_significant = chi_squared_test_significant(
                subject_low, subject_total,
                peer_low, peer_total
            )
        
        diff_str = f"{difference:+.1f}pp"
        if is_significant and difference < 0:
            diff_str += '*'
        
        low_row[f'{year}_Subject'] = f"{subject_pct:.1f}%"
        low_row[f'{year}_Peer'] = f"{peer_pct:.1f}%"
        low_row[f'{year}_Diff'] = diff_str
        low_row[f'{year}_Diff_Significant'] = is_significant
        low_row[f'{year}_Diff_IsNegative'] = difference < 0
    rows.append(low_row)
    
    result_df = pd.DataFrame(rows)
    return result_df


def create_lender_loan_costs_comparison_table(
    subject_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    years: List[int]
) -> pd.DataFrame:
    """
    Create a loan costs comparison table with Subject/Peer/Diff columns for each year.
    
    Metrics (in order):
    - Property Value (average, currency)
    - Loan Amount (average, currency)
    - Downpayment/Equity (average: property_value - loan_amount, currency)
    - Interest Rate (average, percentage)
    - Closing Costs (average: total_loan_costs, currency)
    - Origination Fees (average: origination_charges, currency)
    
    Args:
        subject_df: DataFrame with subject lender data
        peer_df: DataFrame with peer lender data (aggregated)
        years: List of years (should be last 3 years)
        
    Returns:
        DataFrame with Metric column and Subject/Peer/Diff columns for each year.
    """
    if subject_df.empty:
        return pd.DataFrame()
    
    # Ensure we only use last 3 years
    recent_years = sorted(years)[-3:] if len(years) > 3 else sorted(years)
    
    # Required columns
    required_cols = ['year', 'avg_property_value', 'avg_loan_amount', 'avg_interest_rate', 
                     'avg_total_loan_costs', 'avg_origination_charges', 'total_originations']
    missing_subject = [col for col in required_cols if col not in subject_df.columns]
    if missing_subject:
        logger.warning(f"[DEBUG] Missing columns for loan costs table (subject): {missing_subject}")
        return pd.DataFrame()
    
    rows = []
    
    # Define metrics in order: (metric_name, subject_calc_func, peer_calc_func, format_type)
    # For weighted averages, we need to calculate them per year
    for year in recent_years:
        subject_year_df = subject_df[subject_df['year'] == year].copy()
        peer_year_df = peer_df[peer_df['year'] == year].copy() if not peer_df.empty else pd.DataFrame()
        
        if subject_year_df.empty:
            continue
        
        # Calculate subject weighted averages
        subject_total_loans = subject_year_df['total_originations'].sum()
        if subject_total_loans == 0:
            continue
        
        subject_property_value = (subject_year_df['avg_property_value'] * subject_year_df['total_originations']).sum() / subject_total_loans
        subject_loan_amount = (subject_year_df['avg_loan_amount'] * subject_year_df['total_originations']).sum() / subject_total_loans
        subject_downpayment_equity = subject_property_value - subject_loan_amount
        subject_interest_rate = (subject_year_df['avg_interest_rate'] * subject_year_df['total_originations']).sum() / subject_total_loans
        subject_closing_costs = (subject_year_df['avg_total_loan_costs'] * subject_year_df['total_originations']).sum() / subject_total_loans
        subject_origination_fees = (subject_year_df['avg_origination_charges'] * subject_year_df['total_originations']).sum() / subject_total_loans
        
        # Calculate peer weighted averages
        if not peer_year_df.empty and 'total_originations' in peer_year_df.columns:
            peer_total_loans = peer_year_df['total_originations'].sum()
            if peer_total_loans > 0:
                peer_property_value = (peer_year_df['avg_property_value'] * peer_year_df['total_originations']).sum() / peer_total_loans
                peer_loan_amount = (peer_year_df['avg_loan_amount'] * peer_year_df['total_originations']).sum() / peer_total_loans
                peer_downpayment_equity = peer_property_value - peer_loan_amount
                peer_interest_rate = (peer_year_df['avg_interest_rate'] * peer_year_df['total_originations']).sum() / peer_total_loans
                peer_closing_costs = (peer_year_df['avg_total_loan_costs'] * peer_year_df['total_originations']).sum() / peer_total_loans
                peer_origination_fees = (peer_year_df['avg_origination_charges'] * peer_year_df['total_originations']).sum() / peer_total_loans
            else:
                peer_property_value = peer_loan_amount = peer_downpayment_equity = 0.0
                peer_interest_rate = peer_closing_costs = peer_origination_fees = 0.0
        else:
            peer_property_value = peer_loan_amount = peer_downpayment_equity = 0.0
            peer_interest_rate = peer_closing_costs = peer_origination_fees = 0.0
        
        # Define metrics in order
        metrics = [
            ('Property Value', subject_property_value, peer_property_value, 'currency'),
            ('Loan Amount', subject_loan_amount, peer_loan_amount, 'currency'),
            ('Downpayment/Equity', subject_downpayment_equity, peer_downpayment_equity, 'currency'),
            ('Interest Rate', subject_interest_rate, peer_interest_rate, 'percentage'),
            ('Closing Costs', subject_closing_costs, peer_closing_costs, 'currency'),
            ('Origination Fees', subject_origination_fees, peer_origination_fees, 'currency')
        ]
        
        # Create rows for each metric
        for metric_name, subject_val, peer_val, format_type in metrics:
            # Find or create row for this metric
            row = next((r for r in rows if r['Metric'] == metric_name), None)
            if row is None:
                row = {'Metric': metric_name}
                rows.append(row)
            
            # Format and store values
            if format_type == 'currency':
                subject_str = f"${subject_val:,.0f}" if not pd.isna(subject_val) else 'N/A'
                peer_str = f"${peer_val:,.0f}" if not pd.isna(peer_val) else 'N/A'
                difference = float(subject_val) - float(peer_val) if not pd.isna(subject_val) and not pd.isna(peer_val) else None
                if difference is not None:
                    diff_str = f"${difference:+,.0f}"
                else:
                    diff_str = 'N/A'
            else:  # percentage
                subject_str = f"{subject_val:.2f}%" if not pd.isna(subject_val) else 'N/A'
                peer_str = f"{peer_val:.2f}%" if not pd.isna(peer_val) else 'N/A'
                difference = float(subject_val) - float(peer_val) if not pd.isna(subject_val) and not pd.isna(peer_val) else None
                if difference is not None:
                    diff_str = f"{difference:+.2f}pp"
                else:
                    diff_str = 'N/A'
            
            row[f'{year}_Subject'] = subject_str
            row[f'{year}_Peer'] = peer_str
            row[f'{year}_Diff'] = diff_str
            row[f'{year}_Diff_Significant'] = False  # Loan costs don't use chi-squared
            row[f'{year}_Diff_IsNegative'] = difference < 0 if difference is not None else False
    
    if not rows:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(rows)
    # Ensure metrics are in the correct order
    metric_order = ['Property Value', 'Loan Amount', 'Downpayment/Equity', 'Interest Rate', 'Closing Costs', 'Origination Fees']
    result_df['Metric_Order'] = result_df['Metric'].map({m: i for i, m in enumerate(metric_order)})
    result_df = result_df.sort_values('Metric_Order').drop('Metric_Order', axis=1)
    
    return result_df


def build_lender_report(
    subject_hmda_data: List[Dict[str, Any]],
    peer_hmda_data: List[Dict[str, Any]],
    lender_info: Dict[str, Any],
    years: List[int],
    census_data: Dict = None,
    historical_census_data: Dict = None,
    hud_data: Dict = None,
    progress_tracker=None,
    action_taken: List[str] = None,
    all_metros_data: List[Dict[str, Any]] = None,  # Optional: All metros data for top metros table (not limited to selected geography)
    geography_scope: str = None  # Optional: Geography scope ('custom', 'loan_cbsas', 'branch_cbsas', 'all_cbsas')
) -> Dict[str, Any]:
    """
    Build lender analysis report data structure.
    
    Args:
        subject_hmda_data: List of dictionaries from BigQuery for subject lender
        peer_hmda_data: List of dictionaries from BigQuery for peer lenders (aggregated)
        lender_info: Dictionary with lender information (name, lei, rssd, etc.)
        years: List of years
        census_data: Optional census demographics data
        historical_census_data: Optional historical census data
        hud_data: Optional HUD data
        progress_tracker: Optional progress tracker
        action_taken: Optional list of action_taken codes
        
    Returns:
        Dictionary with report data organized by sections
    """
    if not subject_hmda_data:
        raise ValueError("No subject lender data provided")
    
    # Initialize report_data dictionary
    report_data = {}
    
    # Track whether this is applications or originations
    is_applications = action_taken and set(action_taken) != {'1'}
    report_data['data_type'] = 'applications' if is_applications else 'originations'
    report_data['lender_info'] = lender_info
    
    # Convert to DataFrames
    subject_df = pd.DataFrame(subject_hmda_data)
    peer_df = pd.DataFrame(peer_hmda_data) if peer_hmda_data else pd.DataFrame()
    
    # Log what data we received
    logger.info(f"[build_lender_report] Received subject_hmda_data: {len(subject_hmda_data)} rows")
    logger.info(f"[build_lender_report] Received all_metros_data: {len(all_metros_data) if all_metros_data else 0} rows")
    if all_metros_data and len(all_metros_data) > 0:
        # Quick check of total loans in all_metros_data
        metros_df_check = pd.DataFrame(all_metros_data)
        if 'total_originations' in metros_df_check.columns:
            metros_total = int(pd.to_numeric(metros_df_check['total_originations'], errors='coerce').fillna(0).sum())
            logger.info(f"[build_lender_report] all_metros_data contains {metros_total:,} total loans (should be ~61,756 for national)")
    
    # Clean and prepare data - use LendSight's cleaning function
    from justdata.apps.lendsight.mortgage_report_builder import clean_mortgage_data
    subject_df = clean_mortgage_data(subject_df)
    if not peer_df.empty:
        peer_df = clean_mortgage_data(peer_df)
    
    # Ensure numeric columns are properly typed (in case they come as strings from BigQuery)
    if 'total_originations' in subject_df.columns:
        subject_df['total_originations'] = pd.to_numeric(subject_df['total_originations'], errors='coerce').fillna(0)
    if 'total_originations' in peer_df.columns:
        peer_df['total_originations'] = pd.to_numeric(peer_df['total_originations'], errors='coerce').fillna(0)
    
    # Ensure year is numeric for proper filtering
    if 'year' in subject_df.columns:
        subject_df['year'] = pd.to_numeric(subject_df['year'], errors='coerce')
    if 'year' in peer_df.columns:
        peer_df['year'] = pd.to_numeric(peer_df['year'], errors='coerce')
    
    # Get last 3 years
    recent_years = sorted(years)[-3:] if len(years) > 3 else sorted(years)
    report_data['years'] = recent_years
    
    if progress_tracker:
        progress_tracker.update_progress('building_report', 50, 'Building Section 1 charts...')
    
    # Section 1: Table 1 - Loans by Loan Purpose Over Time (subject lender only)
    # Use all_metros_data if available (national totals), otherwise use subject_df (selected geography)
    # Aggregate loan counts by year and loan purpose
    table1_df = subject_df  # Default to subject_df
    logger.info(f"[Section 1 Table 1] all_metros_data provided: {all_metros_data is not None}, length: {len(all_metros_data) if all_metros_data else 0}")
    if all_metros_data and len(all_metros_data) > 0:
        # Use all metros data for national totals
        table1_df = pd.DataFrame(all_metros_data)
        # Clean the data
        from justdata.apps.lendsight.mortgage_report_builder import clean_mortgage_data
        table1_df = clean_mortgage_data(table1_df)
        # Ensure numeric columns
        if 'total_originations' in table1_df.columns:
            table1_df['total_originations'] = pd.to_numeric(table1_df['total_originations'], errors='coerce').fillna(0)
        if 'year' in table1_df.columns:
            table1_df['year'] = pd.to_numeric(table1_df['year'], errors='coerce')
        
        # Log total loans across all years to verify we have national totals
        total_all_years = int(table1_df['total_originations'].sum()) if not table1_df.empty else 0
        logger.info(f"[Section 1 Table 1] Using all_metros_data for national totals ({len(table1_df)} rows, {total_all_years:,} total loans across all years)")
    else:
        # Log what we're using instead
        total_subject = int(subject_df['total_originations'].sum()) if not subject_df.empty and 'total_originations' in subject_df.columns else 0
        logger.warning(f"[Section 1 Table 1] WARNING: Using subject_df (limited to selected geography, {len(table1_df)} rows, {total_subject:,} total loans) - national totals NOT available!")
    
    if 'loan_purpose' in table1_df.columns and 'total_originations' in table1_df.columns and not table1_df.empty:
        # Log total loans by year for debugging
        total_all_years_check = int(table1_df['total_originations'].sum()) if not table1_df.empty else 0
        logger.info(f"[Section 1 Table 1] Total loans across ALL years: {total_all_years_check:,} (should be ~61,756 for national totals)")
        
        for year in sorted(years):
            year_df = table1_df[table1_df['year'] == year]
            if not year_df.empty and 'total_originations' in year_df.columns:
                total_year_loans = int(year_df['total_originations'].sum())
                logger.info(f"[Section 1 Table 1] Year {year}: Total loans = {total_year_loans:,} (from {len(year_df)} aggregated rows)")
        
        loan_purpose_data = []
        for year in sorted(years):
            year_df = table1_df[table1_df['year'] == year]
            
            if not year_df.empty:
                # Map loan purpose codes to readable names
                purpose_map = {
                    '1': 'Home Purchase',
                    '31': 'Refinance',
                    '32': 'Refinance',
                    'purchase': 'Home Purchase',
                    'refinance': 'Refinance',
                    '2': 'Home Equity',
                    '4': 'Home Equity',
                    'equity': 'Home Equity',
                    '3': 'Home Improvement',
                    '33': 'Home Improvement',
                    '34': 'Home Improvement',
                    '5': 'Other',
                    '35': 'Other'
                }
                
                # Group by loan purpose and sum loan counts for subject
                # Note: total_originations is already aggregated at the tract/loan_purpose level from SQL
                # So we sum these aggregations to get the total for each loan purpose
                subject_purpose_counts = {}
                for purpose_code in year_df['loan_purpose'].unique():
                    purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
                    purpose_name = purpose_map.get(str(purpose_code), 'Other')
                    # Sum the total_originations (which are already counts per tract/loan_purpose combination)
                    total_count = int(purpose_df['total_originations'].sum())
                    if purpose_name in subject_purpose_counts:
                        subject_purpose_counts[purpose_name] += total_count
                    else:
                        subject_purpose_counts[purpose_name] = total_count
                
                # Debug logging to help diagnose issues
                logger.debug(f"[Section 1 Table 1] Year {year}: Total rows={len(year_df)}, "
                           f"Purchase={subject_purpose_counts.get('Home Purchase', 0)}, "
                           f"Refinance={subject_purpose_counts.get('Refinance', 0)}, "
                           f"Equity={subject_purpose_counts.get('Home Equity', 0)}")
                
                # Create row for this year (ensure native Python types for JSON serialization)
                year_row = {'year': int(year)}
                year_row['Home Purchase'] = int(subject_purpose_counts.get('Home Purchase', 0))
                year_row['Refinance'] = int(subject_purpose_counts.get('Refinance', 0))
                year_row['Home Equity'] = int(subject_purpose_counts.get('Home Equity', 0))
                loan_purpose_data.append(year_row)
        
        report_data['loan_purpose_over_time'] = loan_purpose_data
    else:
        report_data['loan_purpose_over_time'] = []
    
    # Section 1: Table 2 - Loan Amounts by Loan Purpose Over Time (subject lender only)
    # Aggregate loan amounts by year and loan purpose
    if 'loan_purpose' in subject_df.columns and 'total_loan_amount' in subject_df.columns and not subject_df.empty:
        loan_amount_purpose_data = []
        for year in sorted(years):
            year_df = subject_df[subject_df['year'] == year]
            
            if not year_df.empty:
                # Map loan purpose codes to readable names (same as above)
                purpose_map = {
                    '1': 'Home Purchase',
                    '31': 'Refinance',
                    '32': 'Refinance',
                    'purchase': 'Home Purchase',
                    'refinance': 'Refinance',
                    '2': 'Home Equity',
                    '4': 'Home Equity',
                    'equity': 'Home Equity',
                    '3': 'Home Improvement',
                    '33': 'Home Improvement',
                    '34': 'Home Improvement',
                    '5': 'Other',
                    '35': 'Other'
                }
                
                # Group by loan purpose and sum loan amounts for subject
                subject_purpose_amounts = {}
                for purpose_code in year_df['loan_purpose'].unique():
                    purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
                    purpose_name = purpose_map.get(str(purpose_code), 'Other')
                    total_amount = float(purpose_df['total_loan_amount'].sum())
                    if purpose_name in subject_purpose_amounts:
                        subject_purpose_amounts[purpose_name] += total_amount
                    else:
                        subject_purpose_amounts[purpose_name] = total_amount
                
                # Create row for this year (ensure native Python types for JSON serialization)
                year_row = {'year': int(year)}
                year_row['Home Purchase'] = float(subject_purpose_amounts.get('Home Purchase', 0))
                year_row['Refinance'] = float(subject_purpose_amounts.get('Refinance', 0))
                year_row['Home Equity'] = float(subject_purpose_amounts.get('Home Equity', 0))
                loan_amount_purpose_data.append(year_row)
        
        report_data['loan_amount_purpose_over_time'] = loan_amount_purpose_data
    else:
        report_data['loan_amount_purpose_over_time'] = []
    
    # Section 1: Table 3 - Top Metros (CBSAs) by Loan Purpose
    # Skip this table if custom geography is selected (user selected specific counties, not metros)
    if geography_scope == 'custom':
        logger.info("Skipping Section 1 Table 3 (Top Metros) - custom geography selected")
        report_data['top_metros'] = []
    else:
        # Aggregate loans by CBSA and loan purpose
        if progress_tracker:
            progress_tracker.update_progress('building_report', 60, 'Building Section 1 Table 3 (Top Metros)...')
        
        # Look up CBSA information from county codes using BigQuery
        # We need to query geo.cbsa_to_county to get CBSA codes and names
        try:
            from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
            from justdata.shared.utils.unified_env import get_unified_config
            
            config = get_unified_config(load_env=False, verbose=False)
            PROJECT_ID = config.get('GCP_PROJECT_ID')
            client = get_bigquery_client(PROJECT_ID)
            
            # Convert all_metros_data to DataFrame if provided (shows ALL metros, not just selected geography)
            # Otherwise fall back to subject_df (limited to selected geography)
            if all_metros_data and len(all_metros_data) > 0:
                metros_df = pd.DataFrame(all_metros_data)
                # Clean the data using LendSight's cleaning function
                from justdata.apps.lendsight.mortgage_report_builder import clean_mortgage_data
                metros_df = clean_mortgage_data(metros_df)
            else:
                # Fall back to subject_df if all_metros_data not provided
                logger.warning("all_metros_data not provided, using subject_df for top metros (may be limited to selected geography)")
                metros_df = subject_df.copy()
            
            # Get unique county codes from metros data
            if not metros_df.empty and ('geoid5' in metros_df.columns or 'county_code' in metros_df.columns):
                county_col = 'geoid5' if 'geoid5' in metros_df.columns else 'county_code'
                unique_counties = metros_df[county_col].unique().tolist()
                
                if unique_counties:
                    # Query CBSA information for these counties
                    counties_str = "', '".join([str(c) for c in unique_counties if pd.notna(c)])
                    cbsa_query = f"""
                    SELECT DISTINCT
                        CAST(c.cbsa_code AS STRING) as cbsa_code,
                        c.CBSA as cbsa_name,
                        CAST(c.geoid5 AS STRING) as geoid5
                    FROM `{PROJECT_ID}.geo.cbsa_to_county` c
                    WHERE CAST(c.geoid5 AS STRING) IN ('{counties_str}')
                      AND c.cbsa_code IS NOT NULL
                      AND c.CBSA IS NOT NULL
                    """
                    
                    cbsa_results = execute_query(client, cbsa_query)
                    cbsa_lookup = {}
                    if cbsa_results:
                        for row in cbsa_results:
                            geoid5 = str(row.get('geoid5', ''))
                            cbsa_code = str(row.get('cbsa_code', ''))
                            cbsa_name = str(row.get('cbsa_name', ''))
                            if geoid5 and cbsa_code:
                                if geoid5 not in cbsa_lookup:
                                    cbsa_lookup[geoid5] = []
                                cbsa_lookup[geoid5].append({'code': cbsa_code, 'name': cbsa_name})
                    
                    # Add CBSA information to metros_df
                    def get_cbsa_info(county_code):
                        county_str = str(county_code) if pd.notna(county_code) else ''
                        if county_str in cbsa_lookup and cbsa_lookup[county_str]:
                            # Use first CBSA if multiple (shouldn't happen, but handle it)
                            return cbsa_lookup[county_str][0]
                        return {'code': None, 'name': None}
                    
                    metros_df['cbsa_code'] = metros_df[county_col].apply(lambda x: get_cbsa_info(x)['code'])
                    metros_df['cbsa_name'] = metros_df[county_col].apply(lambda x: get_cbsa_info(x)['name'])
                    
                    # Now aggregate by CBSA
                    if 'cbsa_code' in metros_df.columns and metros_df['cbsa_code'].notna().any():
                        # Calculate total loans across all years for ranking (excluding null CBSAs)
                        cbsa_df = metros_df[metros_df['cbsa_code'].notna()].copy()
                        if not cbsa_df.empty:
                            total_loans_by_cbsa = cbsa_df.groupby('cbsa_code')['total_originations'].sum().sort_values(ascending=False)
                            
                            # Get top 10 CBSAs (or all if less than 10)
                            top_cbsa_codes = total_loans_by_cbsa.head(10).index.tolist()
                            
                            if len(top_cbsa_codes) < 10:
                                # Show all CBSAs if less than 10
                                top_cbsa_codes = total_loans_by_cbsa.index.tolist()
                            
                            # Aggregate all loans by CBSA
                            from justdata.apps.dataexplorer.area_report_builder import filter_df_by_loan_purpose
                            all_df = filter_df_by_loan_purpose(cbsa_df, 'all')
                            purchase_df = filter_df_by_loan_purpose(cbsa_df, 'purchase')
                            refinance_df = filter_df_by_loan_purpose(cbsa_df, 'refinance')
                            equity_df = filter_df_by_loan_purpose(cbsa_df, 'equity')
                            
                            # Aggregate by CBSA for all loans
                            cbsa_agg = all_df[all_df['cbsa_code'].isin(top_cbsa_codes)].groupby('cbsa_code').agg({
                                'total_originations': 'sum',
                                'cbsa_name': 'first'  # Get name from first occurrence
                            }).reset_index()
                            
                            # Sort by total loans descending
                            cbsa_agg = cbsa_agg.sort_values('total_originations', ascending=False)
                            
                            # Format for display and fill in loan purpose columns
                            metros_list = []
                            for _, row in cbsa_agg.iterrows():
                                cbsa_code = str(row['cbsa_code'])
                                # Get purchase loans for this CBSA
                                purchase_count = int(purchase_df[purchase_df['cbsa_code'] == cbsa_code]['total_originations'].sum()) if not purchase_df.empty else 0
                                # Get refinance loans for this CBSA
                                refinance_count = int(refinance_df[refinance_df['cbsa_code'] == cbsa_code]['total_originations'].sum()) if not refinance_df.empty else 0
                                # Get equity loans for this CBSA
                                equity_count = int(equity_df[equity_df['cbsa_code'] == cbsa_code]['total_originations'].sum()) if not equity_df.empty else 0
                                
                                metros_list.append({
                                    'cbsa_code': cbsa_code,
                                    'cbsa_name': str(row.get('cbsa_name', cbsa_code)),
                                    'all_loans': int(row['total_originations']),
                                    'home_purchase': purchase_count,
                                    'refinance': refinance_count,
                                    'home_equity': equity_count
                                })
                            
                            report_data['top_metros'] = metros_list
                        else:
                            report_data['top_metros'] = []
                    else:
                        report_data['top_metros'] = []
                else:
                    report_data['top_metros'] = []
            else:
                logger.warning("No county code column found in data. Top metros table will be empty.")
                report_data['top_metros'] = []
        except Exception as e:
            logger.error(f"Error building top metros table: {e}", exc_info=True)
            report_data['top_metros'] = []
    
    if progress_tracker:
        progress_tracker.update_progress('building_report', 70, 'Building comparison tables...')
    
    # Section 1: Lender Overview (basic info)
    report_data['lender_overview'] = {
        'lender_name': lender_info.get('name', 'Unknown'),
        'lender_type': lender_info.get('type', 'Unknown'),
        'city': lender_info.get('city', ''),
        'state': lender_info.get('state', ''),
        'total_years': len(recent_years),
        'years': recent_years
    }
    
    # Section 2: Comparison Tables (by loan purpose)
    # Generate tables for each loan purpose: all, purchase, refinance, equity
    loan_purposes = ['all', 'purchase', 'refinance', 'equity']
    section2_tables = {}
    
    # Import filter function from area_report_builder
    from justdata.apps.dataexplorer.area_report_builder import filter_df_by_loan_purpose
    
    for purpose in loan_purposes:
        logger.info(f"[DEBUG] Building Section 2 tables for loan purpose: {purpose}")
        subject_purpose_df = filter_df_by_loan_purpose(subject_df, purpose)
        peer_purpose_df = filter_df_by_loan_purpose(peer_df, purpose) if not peer_df.empty else pd.DataFrame()
        
        if subject_purpose_df.empty:
            logger.warning(f"[DEBUG] No subject lender data for loan purpose: {purpose}")
            section2_tables[purpose] = {
                'loans_by_race_ethnicity': pd.DataFrame(),
                'loans_by_borrower_income': pd.DataFrame(),
                'loans_by_neighborhood_income': pd.DataFrame(),
                'loans_by_neighborhood_demographics': pd.DataFrame()
            }
            continue
        
        # Table 1: Loans by Race and Ethnicity
        loans_by_race_ethnicity = create_lender_race_ethnicity_comparison_table(
            subject_purpose_df,
            peer_purpose_df,
            recent_years,
            census_data=historical_census_data
        )
        
        # Table 2: Loans by Borrower Income
        loans_by_borrower_income = create_lender_borrower_income_comparison_table(
            subject_purpose_df,
            peer_purpose_df,
            recent_years,
            hud_data=hud_data
        )
        
        # Table 3: Loans by Neighborhood Income
        loans_by_neighborhood_income = create_lender_neighborhood_income_comparison_table(
            subject_purpose_df,
            peer_purpose_df,
            recent_years,
            hud_data=hud_data,
            census_data=census_data
        )
        
        # Table 4: Loans by Neighborhood Demographics
        loans_by_neighborhood_demographics = create_lender_neighborhood_demographics_comparison_table(
            subject_purpose_df,
            peer_purpose_df,
            recent_years,
            census_data=census_data
        )
        
        # Table 5: Loan Costs
        loans_by_loan_costs = create_lender_loan_costs_comparison_table(
            subject_purpose_df,
            peer_purpose_df,
            recent_years
        )
        
        section2_tables[purpose] = {
            'loans_by_race_ethnicity': loans_by_race_ethnicity,
            'loans_by_borrower_income': loans_by_borrower_income,
            'loans_by_neighborhood_income': loans_by_neighborhood_income,
            'loans_by_neighborhood_demographics': loans_by_neighborhood_demographics,
            'loans_by_loan_costs': loans_by_loan_costs
        }
    
    report_data['section2'] = {
        'years': recent_years,
        'by_purpose': section2_tables
    }
    
    if progress_tracker:
        progress_tracker.update_progress('building_report', 90, 'Building Section 3 (HHI)...')
    
    # Section 3: HHI Market Concentration by Loan Purpose
    hhi_by_year_purpose = []
    loan_purpose_map = {
        '1': 'Home Purchase',
        '31': 'Refinance',
        '32': 'Refinance',
        '2': 'Home Equity',
        '4': 'Home Equity'
    }
    
    for year in sorted(years):
        year_df = subject_df[subject_df['year'] == year].copy()
        year_data = {'year': year}
        
        # Calculate HHI for each loan purpose
        for purpose_code, purpose_name in loan_purpose_map.items():
            purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
            if not purpose_df.empty:
                hhi_result = calculate_mortgage_hhi_for_year(purpose_df, year)
                year_data[purpose_name] = hhi_result['hhi'] if hhi_result['hhi'] is not None else None
            else:
                year_data[purpose_name] = None
        
        hhi_by_year_purpose.append(year_data)
    
    report_data['section3'] = {
        'hhi_by_year_purpose': hhi_by_year_purpose
    }
    
    # Convert all DataFrames to dict format for JSON serialization
    def convert_dataframes_to_dicts(obj):
        """Recursively convert DataFrames to dicts."""
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict('records') if not obj.empty else []
        elif isinstance(obj, dict):
            return {k: convert_dataframes_to_dicts(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_dataframes_to_dicts(item) for item in obj]
        else:
            return obj
    
    report_data = convert_dataframes_to_dicts(report_data)
    
    logger.info(f"[DEBUG] Created lender report with {len(recent_years)} years of comparison data")
    
    return report_data

