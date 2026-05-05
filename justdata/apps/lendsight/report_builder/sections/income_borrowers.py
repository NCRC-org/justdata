"""Income borrowers section table."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from justdata.apps.lendsight.report_builder.formatting import map_lender_type

def create_income_borrowers_table(df: pd.DataFrame, years: List[int], hud_data: Dict[str, Dict[str, float]] = None) -> pd.DataFrame:
    """
    Create Table 1: Lending to Income Borrowers.
    
    Shows:
    - Low to Moderate Income Borrowers (aggregate)
    - Low Income Borrowers
    - Moderate Income Borrowers
    - Middle Income Borrowers
    - Upper Income Borrowers
    
    For borrower income rows, shows percentage of borrowers in that income category.
    Population Share column uses HUD low/mod income distribution data.
    
    Args:
        df: DataFrame with loan data
        years: List of years
        hud_data: Dictionary mapping GEOID5 to HUD income distribution data (for Population Share)
    """
    # Check required columns
    required_cols = ['total_originations', 'lmib_originations', 'low_income_borrower_originations',
                     'moderate_income_borrower_originations', 'middle_income_borrower_originations',
                     'upper_income_borrower_originations', 'geoid5']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Warning: Missing columns for income borrowers table: {missing_cols}")
        return pd.DataFrame()
    
    # Aggregate by year and county
    yearly_data = []
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        
        # Aggregate by county
        county_totals = {}
        for geoid5 in year_df['geoid5'].unique():
            county_df = year_df[year_df['geoid5'] == geoid5]
            county_totals[geoid5] = {
                'total': int(county_df['total_originations'].sum()),
                'lmib': int(county_df['lmib_originations'].sum()),
                'low': int(county_df['low_income_borrower_originations'].sum()),
                'moderate': int(county_df['moderate_income_borrower_originations'].sum()),
                'middle': int(county_df['middle_income_borrower_originations'].sum()),
                'upper': int(county_df['upper_income_borrower_originations'].sum()),
            }
        
        # Sum across all counties
        total = sum(ct['total'] for ct in county_totals.values())
        lmib = sum(ct['lmib'] for ct in county_totals.values())
        low = sum(ct['low'] for ct in county_totals.values())
        moderate = sum(ct['moderate'] for ct in county_totals.values())
        middle = sum(ct['middle'] for ct in county_totals.values())
        upper = sum(ct['upper'] for ct in county_totals.values())
        
        yearly_data.append({
            'year': year,
            'total': total,
            'lmib': lmib,
            'low': low,
            'moderate': moderate,
            'middle': middle,
            'upper': upper
        })
    
    # Build result table
    result_data = {'Metric': []}
    
    # Add year columns
    for year in sorted(years):
        result_data[str(year)] = []
    
    # Get HUD population percentages (aggregate across counties)
    hud_low_mod_pct = 0.0
    hud_low_pct = 0.0
    hud_moderate_pct = 0.0
    hud_middle_pct = 0.0
    hud_upper_pct = 0.0
    total_persons = 0

    if hud_data:
        # Aggregate HUD data across all counties in the report
        geoids = df['geoid5'].unique()
        print(f"  [DEBUG] Table 1 - HUD data available with {len(hud_data)} counties")
        print(f"  [DEBUG] Table 1 - HUD data keys (sample): {list(hud_data.keys())[:5]}")
        print(f"  [DEBUG] Table 1 - DataFrame geoids (sample): {[str(g).zfill(5) for g in list(geoids)[:5]]}")

        # Check for matches between DataFrame geoids and HUD data
        matched_geoids = [str(geoid).zfill(5) for geoid in geoids if str(geoid).zfill(5) in hud_data]
        print(f"  [DEBUG] Table 1 - Matched geoids: {len(matched_geoids)} out of {len(geoids)}: {matched_geoids}")

        total_persons = sum(hud_data.get(str(geoid).zfill(5), {}).get('total_persons', 0) for geoid in geoids)
        print(f"  [DEBUG] Table 1 - Total persons from HUD data: {total_persons:,}")
        if total_persons > 0:
            hud_low_mod_pct = sum(hud_data.get(str(geoid).zfill(5), {}).get('low_mod_income_pct', 0) * 
                                  hud_data.get(str(geoid).zfill(5), {}).get('total_persons', 0) 
                                  for geoid in geoids) / total_persons
            hud_low_pct = sum(hud_data.get(str(geoid).zfill(5), {}).get('low_income_pct', 0) * 
                             hud_data.get(str(geoid).zfill(5), {}).get('total_persons', 0) 
                             for geoid in geoids) / total_persons
            hud_moderate_pct = sum(hud_data.get(str(geoid).zfill(5), {}).get('moderate_income_pct', 0) * 
                                  hud_data.get(str(geoid).zfill(5), {}).get('total_persons', 0) 
                                  for geoid in geoids) / total_persons
            hud_middle_pct = sum(hud_data.get(str(geoid).zfill(5), {}).get('middle_income_pct', 0) * 
                               hud_data.get(str(geoid).zfill(5), {}).get('total_persons', 0) 
                               for geoid in geoids) / total_persons
            hud_upper_pct = sum(hud_data.get(str(geoid).zfill(5), {}).get('upper_income_pct', 0) *
                               hud_data.get(str(geoid).zfill(5), {}).get('total_persons', 0)
                               for geoid in geoids) / total_persons
            print(f"  [DEBUG] Table 1 - HUD percentages: low={hud_low_pct:.1f}%, mod={hud_moderate_pct:.1f}%, mid={hud_middle_pct:.1f}%, upper={hud_upper_pct:.1f}%")
    else:
        print(f"  [WARNING] Table 1 - No HUD data provided, Population Share column will not be added")

    # Add Population Share column (if HUD data available)
    if hud_data and total_persons > 0:
        result_data['Population Share (%)'] = []

    # Add change column
    if len(years) >= 2:
        time_span = f"{min(years)}-{max(years)}"
        result_data['Change'] = []
    
    # Define metrics in order
    # Note: For 'lmib', we'll calculate it as low + moderate to ensure mathematical consistency
    metrics = [
        ('lmib', 'Low to Moderate Income Borrowers', hud_low_mod_pct, True),  # True = calculate as low + moderate
        ('low', 'Low Income Borrowers', hud_low_pct, False),
        ('moderate', 'Moderate Income Borrowers', hud_moderate_pct, False),
        ('middle', 'Middle Income Borrowers', hud_middle_pct, False),
        ('upper', 'Upper Income Borrowers', hud_upper_pct, False),
    ]
    
    # Calculate for each metric
    for metric_key, metric_label, hud_pct, is_calculated in metrics:
        result_data['Metric'].append(metric_label)
        
        # Calculate for each year
        metric_changes = []
        for year in sorted(years):
            year_data = next((d for d in yearly_data if d['year'] == year), None)
            if year_data:
                # For LMI, calculate as Low + Moderate to ensure math is correct
                if is_calculated and metric_key == 'lmib':
                    count = year_data['low'] + year_data['moderate']
                else:
                    count = year_data[metric_key]
                total = year_data['total']
                # Show percentage of loans
                pct = (count / total * 100) if total > 0 else 0.0
                result_data[str(year)].append(f"{pct:.1f}%")
                metric_changes.append((count, pct))
            else:
                result_data[str(year)].append("0.0%")
                metric_changes.append((0, 0.0))
        
        # Add Population Share column
        if hud_data and total_persons > 0:
            if hud_pct is not None and hud_pct > 0:
                result_data['Population Share (%)'].append(f"{hud_pct:.1f}%")
            else:
                result_data['Population Share (%)'].append("")
        
        # Calculate percentage change
        if len(years) >= 2 and len(metric_changes) >= 2:
            first_count, first_pct = metric_changes[0]
            last_count, last_pct = metric_changes[-1]
            pct_change = last_pct - first_pct
            if pct_change > 0:
                change_str = f"+{pct_change:.1f}pp"
            elif pct_change < 0:
                change_str = f"{pct_change:.1f}pp"
            else:
                change_str = "0.0pp"
            result_data['Change'].append(change_str)
        else:
            if len(years) >= 2:
                result_data['Change'].append("N/A")
    
    # Add "Total Loans" row as the first row (before all other metrics)
    total_loans_row = {'Metric': 'Total Loans'}
    for year in sorted(years):
        year_data = next((d for d in yearly_data if d['year'] == year), None)
        if year_data:
            total_loans_row[str(year)] = f"{year_data['total']:,}"
        else:
            total_loans_row[str(year)] = "0"
    
    # Add Population Share column for Total Loans (empty)
    if hud_data and total_persons > 0:
        total_loans_row['Population Share (%)'] = ""
    
    # Add Change column for Total Loans (percentage change from first to last year)
    if len(years) >= 2:
        first_year_data = next((d for d in yearly_data if d['year'] == min(years)), None)
        last_year_data = next((d for d in yearly_data if d['year'] == max(years)), None)
        if first_year_data and last_year_data:
            first_total = first_year_data['total']
            last_total = last_year_data['total']
            if first_total > 0:
                pct_change = ((last_total - first_total) / first_total) * 100
                if pct_change > 0:
                    total_loans_row['Change'] = f"+{pct_change:.1f}%"
                elif pct_change < 0:
                    total_loans_row['Change'] = f"{pct_change:.1f}%"
                else:
                    total_loans_row['Change'] = "0.0%"
            else:
                total_loans_row['Change'] = "N/A"
        else:
            total_loans_row['Change'] = "N/A"

    # Insert Total Loans row at the beginning
    result = pd.DataFrame(result_data)
    total_loans_df = pd.DataFrame([total_loans_row])
    result = pd.concat([total_loans_df, result], ignore_index=True)

    return result


