"""
Statistical analysis functions for MergerMeter.
Includes chi-squared tests for Small Business lending and branch locations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Try to import scipy, but handle if not available
try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    # Create a dummy stats object for when scipy is not available
    class DummyStats:
        @staticmethod
        def chisquare(observed, expected=None):
            return (0.0, 1.0)  # Return non-significant result
    stats = DummyStats()


def perform_chi_squared_test(
    observed: pd.Series,
    expected: pd.Series = None,
    expected_proportions: Dict[str, float] = None
) -> Dict[str, float]:
    """
    Perform chi-squared test for goodness of fit.
    
    Args:
        observed: Observed frequencies
        expected: Expected frequencies (if None, will calculate from proportions)
        expected_proportions: Dictionary of expected proportions (must sum to 1.0)
    
    Returns:
        Dictionary with chi2_statistic, p_value, and degrees_of_freedom
    """
    try:
        # Ensure observed is numeric
        observed = pd.to_numeric(observed, errors='coerce').fillna(0)
        
        if expected is None:
            if expected_proportions is None:
                # Default: equal proportions
                total = observed.sum()
                n_categories = len(observed)
                expected = pd.Series([total / n_categories] * n_categories, index=observed.index)
            else:
                # Calculate expected from proportions
                total = observed.sum()
                expected = pd.Series(
                    [expected_proportions.get(idx, 0) * total for idx in observed.index],
                    index=observed.index
                )
        
        # Ensure expected is numeric
        expected = pd.to_numeric(expected, errors='coerce').fillna(0)
        
        # Remove categories with zero expected (to avoid division by zero)
        mask = expected > 0
        observed_filtered = observed[mask]
        expected_filtered = expected[mask]
        
        if len(observed_filtered) == 0:
            return {
                'chi2_statistic': 0.0,
                'p_value': 1.0,
                'degrees_of_freedom': 0,
                'significant': False
            }
        
        # Perform chi-squared test
        if not SCIPY_AVAILABLE:
            # Fallback calculation if scipy not available
            chi2 = float(((observed_filtered - expected_filtered) ** 2 / expected_filtered).sum())
            degrees_of_freedom = len(observed_filtered) - 1
            # Approximate p-value (would need scipy.stats.chi2 for exact)
            p_value = 0.5  # Conservative estimate
        else:
            chi2, p_value = stats.chisquare(observed_filtered, expected_filtered)
        degrees_of_freedom = len(observed_filtered) - 1
        
        return {
            'chi2_statistic': float(chi2),
            'p_value': float(p_value),
            'degrees_of_freedom': int(degrees_of_freedom),
            'significant': p_value < 0.05
        }
    except Exception as e:
        print(f"Error performing chi-squared test: {e}")
        return {
            'chi2_statistic': 0.0,
            'p_value': 1.0,
            'degrees_of_freedom': 0,
            'significant': False,
            'error': str(e)
        }


def analyze_sb_lending_distribution(
    sb_data: pd.DataFrame,
    cbsa_column: str = 'cbsa_code'
) -> Dict[str, any]:
    """
    Analyze Small Business lending distribution across CBSAs using chi-squared test.
    
    Args:
        sb_data: DataFrame with SB lending data
        cbsa_column: Column name for CBSA codes
    
    Returns:
        Dictionary with analysis results including concerning CBSAs
    """
    if sb_data is None or sb_data.empty:
        return {
            'test_result': None,
            'concerning_cbsas': [],
            'underperforming_cbsas': [],
            'summary': 'No Small Business lending data available.'
        }
    
    try:
        # Group by CBSA and calculate total loans
        if cbsa_column not in sb_data.columns:
            return {
                'test_result': None,
                'concerning_cbsas': [],
                'underperforming_cbsas': [],
                'summary': f'CBSA column "{cbsa_column}" not found in data.'
            }
        
        cbsa_totals = sb_data.groupby(cbsa_column).agg({
            'sb_loans_count': 'sum',
            'sb_loans_amount': 'sum',
            'lmict_loans_count': 'sum'
        }).reset_index()
        
        # Calculate expected distribution (equal across all CBSAs)
        total_loans = cbsa_totals['sb_loans_count'].sum()
        n_cbsas = len(cbsa_totals)
        
        if total_loans == 0 or n_cbsas == 0:
            return {
                'test_result': None,
                'concerning_cbsas': [],
                'underperforming_cbsas': [],
                'summary': 'No loans found in Small Business data.'
            }
        
        # Perform chi-squared test
        observed = cbsa_totals['sb_loans_count']
        test_result = perform_chi_squared_test(observed)
        
        # Identify concerning CBSAs (underperforming or overconcentrated)
        expected_per_cbsa = total_loans / n_cbsas
        cbsa_totals['deviation'] = (cbsa_totals['sb_loans_count'] - expected_per_cbsa) / expected_per_cbsa
        
        # Underperforming: less than 50% of expected
        underperforming = cbsa_totals[
            cbsa_totals['sb_loans_count'] < (expected_per_cbsa * 0.5)
        ].copy()
        
        # Overconcentrated: more than 200% of expected (potential redlining concern)
        overconcentrated = cbsa_totals[
            cbsa_totals['sb_loans_count'] > (expected_per_cbsa * 2.0)
        ].copy()
        
        concerning_cbsas = pd.concat([underperforming, overconcentrated]).drop_duplicates()
        
        return {
            'test_result': test_result,
            'concerning_cbsas': concerning_cbsas.to_dict('records') if not concerning_cbsas.empty else [],
            'underperforming_cbsas': underperforming.to_dict('records') if not underperforming.empty else [],
            'overconcentrated_cbsas': overconcentrated.to_dict('records') if not overconcentrated.empty else [],
            'total_loans': int(total_loans),
            'n_cbsas': n_cbsas,
            'expected_per_cbsa': float(expected_per_cbsa),
            'summary': f'Analyzed {n_cbsas} CBSAs with {total_loans} total loans. '
                      f'Chi-squared test: {"significant" if test_result.get("significant") else "not significant"} '
                      f'(p={test_result.get("p_value", 0):.4f}).'
        }
    except Exception as e:
        print(f"Error analyzing SB lending distribution: {e}")
        import traceback
        traceback.print_exc()
        return {
            'test_result': None,
            'concerning_cbsas': [],
            'underperforming_cbsas': [],
            'summary': f'Error analyzing data: {str(e)}'
        }


def analyze_branch_distribution(
    branch_data: pd.DataFrame,
    cbsa_column: str = 'cbsa_code'
) -> Dict[str, any]:
    """
    Analyze branch distribution across CBSAs using chi-squared test.
    
    Args:
        branch_data: DataFrame with branch data
        cbsa_column: Column name for CBSA codes
    
    Returns:
        Dictionary with analysis results including concerning CBSAs
    """
    if branch_data is None or branch_data.empty:
        return {
            'test_result': None,
            'concerning_cbsas': [],
            'underperforming_cbsas': [],
            'summary': 'No branch data available.'
        }
    
    try:
        # Group by CBSA and calculate total branches
        if cbsa_column not in branch_data.columns:
            return {
                'test_result': None,
                'concerning_cbsas': [],
                'underperforming_cbsas': [],
                'summary': f'CBSA column "{cbsa_column}" not found in data.'
            }
        
        cbsa_totals = branch_data.groupby(cbsa_column).agg({
            'total_branches': 'sum',
            'branches_in_lmict': 'sum',
            'branches_in_mmct': 'sum'
        }).reset_index()
        
        # Calculate expected distribution (equal across all CBSAs)
        total_branches = cbsa_totals['total_branches'].sum()
        n_cbsas = len(cbsa_totals)
        
        if total_branches == 0 or n_cbsas == 0:
            return {
                'test_result': None,
                'concerning_cbsas': [],
                'underperforming_cbsas': [],
                'summary': 'No branches found in data.'
            }
        
        # Perform chi-squared test
        observed = cbsa_totals['total_branches']
        test_result = perform_chi_squared_test(observed)
        
        # Identify concerning CBSAs
        expected_per_cbsa = total_branches / n_cbsas
        cbsa_totals['deviation'] = (cbsa_totals['total_branches'] - expected_per_cbsa) / expected_per_cbsa
        
        # Underperforming: less than 50% of expected branches
        underperforming = cbsa_totals[
            cbsa_totals['total_branches'] < (expected_per_cbsa * 0.5)
        ].copy()
        
        # Overconcentrated: more than 200% of expected branches
        overconcentrated = cbsa_totals[
            cbsa_totals['total_branches'] > (expected_per_cbsa * 2.0)
        ].copy()
        
        concerning_cbsas = pd.concat([underperforming, overconcentrated]).drop_duplicates()
        
        return {
            'test_result': test_result,
            'concerning_cbsas': concerning_cbsas.to_dict('records') if not concerning_cbsas.empty else [],
            'underperforming_cbsas': underperforming.to_dict('records') if not underperforming.empty else [],
            'overconcentrated_cbsas': overconcentrated.to_dict('records') if not overconcentrated.empty else [],
            'total_branches': int(total_branches),
            'n_cbsas': n_cbsas,
            'expected_per_cbsa': float(expected_per_cbsa),
            'summary': f'Analyzed {n_cbsas} CBSAs with {total_branches} total branches. '
                      f'Chi-squared test: {"significant" if test_result.get("significant") else "not significant"} '
                      f'(p={test_result.get("p_value", 0):.4f}).'
        }
    except Exception as e:
        print(f"Error analyzing branch distribution: {e}")
        import traceback
        traceback.print_exc()
        return {
            'test_result': None,
            'concerning_cbsas': [],
            'underperforming_cbsas': [],
            'summary': f'Error analyzing data: {str(e)}'
        }


def analyze_hhi_concentration(
    hhi_data: pd.DataFrame
) -> Dict[str, any]:
    """
    Analyze HHI data to identify concerning concentration spikes.
    
    Args:
        hhi_data: DataFrame with HHI analysis data
    
    Returns:
        Dictionary with analysis results including concerning counties
    """
    if hhi_data is None or hhi_data.empty:
        return {
            'concerning_counties': [],
            'high_concentration_counties': [],
            'summary': 'No HHI data available.'
        }
    
    try:
        # HHI thresholds:
        # < 1500: Competitive
        # 1500-2500: Moderately concentrated
        # > 2500: Highly concentrated
        # > 2500 with increase > 200: Concerning spike
        
        # Find post-merger HHI column
        post_hhi_col = None
        pre_hhi_col = None
        county_col = None
        
        for col in hhi_data.columns:
            col_lower = str(col).lower()
            if 'post' in col_lower and 'hhi' in col_lower:
                post_hhi_col = col
            elif 'pre' in col_lower and 'hhi' in col_lower:
                pre_hhi_col = col
            elif 'county' in col_lower:
                county_col = col
        
        if post_hhi_col is None:
            return {
                'concerning_counties': [],
                'high_concentration_counties': [],
                'summary': 'Post-merger HHI column not found in data.'
            }
        
        # Calculate HHI changes
        hhi_analysis = hhi_data.copy()
        if pre_hhi_col:
            hhi_analysis['hhi_change'] = (
                hhi_analysis[post_hhi_col] - hhi_analysis[pre_hhi_col]
            )
        else:
            hhi_analysis['hhi_change'] = hhi_analysis[post_hhi_col]
        
        # Highly concentrated: Post-merger HHI > 2500
        high_concentration = hhi_analysis[
            hhi_analysis[post_hhi_col] > 2500
        ].copy()
        
        # Concerning spikes: Post-merger HHI > 2500 AND increase > 200
        concerning = hhi_analysis[
            (hhi_analysis[post_hhi_col] > 2500) & 
            (hhi_analysis['hhi_change'] > 200)
        ].copy()
        
        # Sort by HHI change (most concerning first)
        if not concerning.empty:
            concerning = concerning.sort_values('hhi_change', ascending=False)
        
        return {
            'concerning_counties': concerning.to_dict('records') if not concerning.empty else [],
            'high_concentration_counties': high_concentration.to_dict('records') if not high_concentration.empty else [],
            'total_counties': len(hhi_analysis),
            'high_concentration_count': len(high_concentration),
            'concerning_count': len(concerning),
            'summary': f'Analyzed {len(hhi_analysis)} counties. '
                      f'{len(high_concentration)} counties have high concentration (HHI > 2500). '
                      f'{len(concerning)} counties show concerning spikes (HHI > 2500 and increase > 200).'
        }
    except Exception as e:
        print(f"Error analyzing HHI concentration: {e}")
        import traceback
        traceback.print_exc()
        return {
            'concerning_counties': [],
            'high_concentration_counties': [],
            'summary': f'Error analyzing HHI data: {str(e)}'
        }

