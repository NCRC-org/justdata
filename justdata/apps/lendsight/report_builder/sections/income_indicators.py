"""Income/neighborhood indicators (legacy table + minority quartile helpers)."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from justdata.shared.utils.no_data import NO_DATA, fmt_pct_change, fmt_pp_change, fmt_share

def create_income_neighborhood_indicators_table(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """
    Create income and neighborhood indicators table.
    
    Shows:
    - Number of loans overall (total originations)
    - Low to Moderate Income Census Tract (LMICT) originations
    - Low to Moderate Income Borrower (LMIB) originations
    - Majority Minority Census Tract (MMCT) originations
    
    Table structure:
    - Far left: Metric column
    - Middle: Column for each year showing "Number (Percent%)"
    - Far right: Change column showing increase/decrease over entire span
    """
    # Check if we have the required columns
    required_columns = ['total_originations', 'lmict_originations', 'lmib_originations', 'mmct_originations']
    if not all(col in df.columns for col in required_columns):
        return pd.DataFrame()
    
    # Aggregate by year
    yearly_data = []
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        if year_df.empty:
            # No rows at all: the whole year is no data, an em dash, never 0
            # (no-data decision, 2026-11-17).
            continue
        
        # Sum originations
        total = int(year_df['total_originations'].sum())
        lmict = int(year_df['lmict_originations'].sum())
        lmib = int(year_df['lmib_originations'].sum())
        mmct = int(year_df['mmct_originations'].sum())
        
        yearly_data.append({
            'year': year,
            'total': total,
            'lmict': lmict,
            'lmib': lmib,
            'mmct': mmct
        })
    
    # Build result table
    result_data = {'Metric': []}
    
    # Add year columns
    for year in sorted(years):
        result_data[str(year)] = []
    
    # Add change column
    if len(years) >= 2:
        first_year = str(min(years))
        last_year = str(max(years))
        time_span = f"{min(years)}-{max(years)}"
        result_data[f'Change Over Time ({time_span})'] = []
    
    # Define metrics in order
    metrics = [
        ('total', 'Loans'),
        ('lmict', 'Low to Moderate Income Census Tract'),
        ('lmib', 'Low to Moderate Income Borrower'),
        ('mmct', 'Majority Minority Census Tract')
    ]
    
    # Calculate for each metric
    for metric_key, metric_label in metrics:
        result_data['Metric'].append(metric_label)
        
        # Calculate for each year
        metric_changes = []
        for year in sorted(years):
            year_data = next((d for d in yearly_data if d['year'] == year), None)
            if year_data:
                count = year_data[metric_key]
                total = year_data['total']
                # For "Loans" row, show just the integer (no percentage)
                if metric_key == 'total':
                    result_data[str(year)].append(f"{count:,}")
                    metric_changes.append((count, 100.0))
                else:
                    # For other rows, show only percentage
                    pct = (count / total * 100) if total > 0 else None
                    result_data[str(year)].append(fmt_share(pct))
                    metric_changes.append((count, pct))
            else:
                if metric_key == 'total':
                    result_data[str(year)].append(NO_DATA)
                    metric_changes.append((None, None))
                else:
                    result_data[str(year)].append(NO_DATA)
                    metric_changes.append((None, None))
        
        # Calculate change from first to last year
        if len(years) >= 2 and len(metric_changes) >= 2:
            first_count, first_pct = metric_changes[0]
            last_count, last_pct = metric_changes[-1]
            
            # For "Loans" row, show percentage change from first to last year
            if metric_key == 'total':
                # No percent change on a zero or missing base
                change_str = fmt_pct_change(first_count, last_count)
            else:
                # For other rows, show only percentage point change
                change_str = fmt_pp_change(first_pct, last_pct)
            
            result_data[f'Change Over Time ({time_span})'].append(change_str)
        else:
            if len(years) >= 2:
                result_data[f'Change Over Time ({time_span})'].append(NO_DATA)
    
    result = pd.DataFrame(result_data)
    return result


def calculate_minority_quartiles(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate minority population quartile thresholds from tract-level data.
    
    Args:
        df: DataFrame with tract-level data including 'tract_minority_population_percent'
    
    Returns:
        Dictionary with quartile thresholds: {'q25': float, 'q50': float, 'q75': float}
    """
    if 'tract_minority_population_percent' not in df.columns:
        return {'q25': 0.0, 'q50': 0.0, 'q75': 0.0}
    
    # Get unique tracts with their minority percentages
    tract_minority = df[df['tract_minority_population_percent'].notna()].copy()
    if tract_minority.empty:
        return {'q25': 0.0, 'q50': 0.0, 'q75': 0.0}
    
    # Get unique tract minority percentages (one per tract)
    unique_tracts = tract_minority.groupby('tract_code')['tract_minority_population_percent'].first()
    minority_pcts = unique_tracts.tolist()
    
    if not minority_pcts:
        return {'q25': 0.0, 'q50': 0.0, 'q75': 0.0}
    
    # Calculate quartiles
    q25 = float(np.percentile(minority_pcts, 25))
    q50 = float(np.percentile(minority_pcts, 50))
    q75 = float(np.percentile(minority_pcts, 75))
    
    return {'q25': q25, 'q50': q50, 'q75': q75}


def classify_tract_minority_quartile(minority_pct: float, quartiles: Dict[str, float]) -> str:
    """
    Classify a tract's minority percentage into a quartile.
    
    Args:
        minority_pct: Minority population percentage for the tract
        quartiles: Dictionary with quartile thresholds
    
    Returns:
        Quartile label: 'low', 'moderate', 'middle', or 'high'
    """
    if pd.isna(minority_pct):
        return 'unknown'
    
    if minority_pct <= quartiles['q25']:
        return 'low'
    elif minority_pct <= quartiles['q50']:
        return 'moderate'
    elif minority_pct <= quartiles['q75']:
        return 'middle'
    else:
        return 'high'


