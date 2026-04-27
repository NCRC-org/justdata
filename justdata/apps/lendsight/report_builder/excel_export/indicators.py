"""Excel-shaped income neighborhood indicators table."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

def create_income_neighborhood_indicators_table_for_excel(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """
    Create income and neighborhood indicators table for Excel export.
    
    This matches the report table structure exactly:
    - Loans row: integer only
    - Other rows: percentages only
    - Change Over Time column
    """
    required_columns = ['total_originations', 'lmict_originations', 'lmib_originations', 'mmct_originations']
    if not all(col in df.columns for col in required_columns):
        return pd.DataFrame()
    
    # Aggregate by year
    yearly_data = []
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        
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
        
        metric_changes = []
        for year in sorted(years):
            year_data = next((d for d in yearly_data if d['year'] == year), None)
            if year_data:
                count = year_data[metric_key]
                total = year_data['total']
                # For "Loans" row, show just the integer (no percentage)
                if metric_key == 'total':
                    result_data[str(year)].append(count)
                    metric_changes.append((count, 100.0))
                else:
                    # For other rows, show only percentage
                    pct = (count / total * 100) if total > 0 else 0.0
                    result_data[str(year)].append(pct)
                    metric_changes.append((count, pct))
            else:
                if metric_key == 'total':
                    result_data[str(year)].append(0)
                    metric_changes.append((0, 0.0))
                else:
                    result_data[str(year)].append(0.0)
                    metric_changes.append((0, 0.0))
        
        # Calculate change from first to last year
        if len(years) >= 2 and len(metric_changes) >= 2:
            first_count, first_pct = metric_changes[0]
            last_count, last_pct = metric_changes[-1]
            
            # For "Loans" row, show count change only
            if metric_key == 'total':
                count_change = last_count - first_count
                result_data[f'Change Over Time ({time_span})'].append(count_change)
            else:
                # For other rows, show only percentage point change
                pct_change = last_pct - first_pct
                result_data[f'Change Over Time ({time_span})'].append(pct_change)
        else:
            if len(years) >= 2:
                result_data[f'Change Over Time ({time_span})'].append(0 if metric_key == 'total' else 0.0)
    
    result = pd.DataFrame(result_data)
    return result


