"""Minority tracts section table."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from justdata.apps.lendsight.report_builder.sections.income_indicators import (
    calculate_minority_quartiles,
    classify_tract_minority_quartile,
)

def create_minority_tracts_table(df: pd.DataFrame, years: List[int], 
                                  census_data: Dict = None) -> pd.DataFrame:
    """
    Create Table 3: Lending to Census Tracts by Minority Population.
    
    Shows:
    - Majority Minority Census Tracts (aggregate)
    - Low Minority Census Tracts (bottom quartile)
    - Moderate Minority Census Tracts (2nd quartile)
    - Middle Minority Census Tracts (3rd quartile)
    - High Minority Census Tracts (top quartile)
    
    Args:
        df: DataFrame with loan data
        years: List of years
        census_data: Dictionary with census demographic data for population shares
    """
    # Check required columns
    required_cols = ['total_originations', 'mmct_originations', 
                     'tract_minority_population_percent', 'tract_code']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Warning: Missing columns for minority tracts table: {missing_cols}")
        return pd.DataFrame()
    
    # Calculate minority quartiles
    quartiles = calculate_minority_quartiles(df)
    
    # Classify each row's tract into a quartile
    df['minority_quartile'] = df['tract_minority_population_percent'].apply(
        lambda x: classify_tract_minority_quartile(x, quartiles)
    )
    
    # Get tract-level population data from Census API
    tract_pop_data = get_tract_population_data_for_counties(df)
    
    # Calculate population shares based on actual population in tracts
    unique_tracts = df[['tract_code', 'minority_quartile', 'tract_minority_population_percent']].drop_duplicates()
    total_tracts = len(unique_tracts)
    quartile_shares = {}
    
    # Calculate MMCT population share using actual population data
    if tract_pop_data and len(tract_pop_data) > 0:
        total_population = 0
        mmct_population = 0
        quartile_populations = {'low': 0, 'moderate': 0, 'middle': 0, 'high': 0}
        
        # Get state and county FIPS from dataframe to construct full tract codes
        if 'state_fips' in df.columns and 'county_fips' in df.columns:
            # Create a mapping of tract_code to state/county for constructing full GEOID
            tract_to_fips = df[['tract_code', 'state_fips', 'county_fips']].drop_duplicates()
            tract_fips_map = {}
            for _, row in tract_to_fips.iterrows():
                tract_code_short = str(row['tract_code']).zfill(6)  # 6-digit tract code
                state_fips = str(int(row['state_fips'])).zfill(2)
                county_fips = str(int(row['county_fips'])).zfill(3)
                full_tract_code = f"{state_fips}{county_fips}{tract_code_short}"  # 11-digit GEOID
                tract_fips_map[tract_code_short] = full_tract_code
        
        for _, tract_row in unique_tracts.iterrows():
            tract_code_short = str(tract_row['tract_code']).zfill(6)  # 6-digit tract code
            tract_minority_pct = tract_row['tract_minority_population_percent']
            quartile = tract_row['minority_quartile']
            
            # Construct full 11-digit tract code for lookup
            full_tract_code = tract_fips_map.get(tract_code_short) if 'tract_fips_map' in locals() else None
            
            if full_tract_code and full_tract_code in tract_pop_data:
                pop = tract_pop_data[full_tract_code]['total_population']
                total_population += pop
                
                # Check if MMCT (>= 50% minority)
                if tract_minority_pct >= 50:
                    mmct_population += pop
                
                # Add to quartile population
                if quartile in quartile_populations:
                    quartile_populations[quartile] += pop
        
        # Calculate population shares
        if total_population > 0:
            quartile_shares['mmct'] = (mmct_population / total_population) * 100
            quartile_shares['low'] = (quartile_populations['low'] / total_population) * 100
            quartile_shares['moderate'] = (quartile_populations['moderate'] / total_population) * 100
            quartile_shares['middle'] = (quartile_populations['middle'] / total_population) * 100
            quartile_shares['high'] = (quartile_populations['high'] / total_population) * 100
        else:
            # Fallback to tract distribution if no population data
            if total_tracts > 0:
                mmct_tracts = unique_tracts[unique_tracts['tract_minority_population_percent'] >= 50]
                quartile_shares['mmct'] = (len(mmct_tracts) / total_tracts * 100) if total_tracts > 0 else 0
                quartile_shares['low'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'low']) / total_tracts * 100
                quartile_shares['moderate'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'moderate']) / total_tracts * 100
                quartile_shares['middle'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'middle']) / total_tracts * 100
                quartile_shares['high'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'high']) / total_tracts * 100
    else:
        # Fallback to tract distribution if Census API data not available
        if total_tracts > 0:
            mmct_tracts = unique_tracts[unique_tracts['tract_minority_population_percent'] >= 50]
            quartile_shares['mmct'] = (len(mmct_tracts) / total_tracts * 100) if total_tracts > 0 else 0
            quartile_shares['low'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'low']) / total_tracts * 100
            quartile_shares['moderate'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'moderate']) / total_tracts * 100
            quartile_shares['middle'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'middle']) / total_tracts * 100
            quartile_shares['high'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'high']) / total_tracts * 100
    
    # Aggregate by year
    yearly_data = []
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        
        total = int(year_df['total_originations'].sum())
        mmct = int(year_df['mmct_originations'].sum())
        
        # Minority quartile categories
        low_minority = int(year_df[year_df['minority_quartile'] == 'low']['total_originations'].sum())
        moderate_minority = int(year_df[year_df['minority_quartile'] == 'moderate']['total_originations'].sum())
        middle_minority = int(year_df[year_df['minority_quartile'] == 'middle']['total_originations'].sum())
        high_minority = int(year_df[year_df['minority_quartile'] == 'high']['total_originations'].sum())
        
        yearly_data.append({
            'year': year,
            'total': total,
            'mmct': mmct,
            'low_minority': low_minority,
            'moderate_minority': moderate_minority,
            'middle_minority': middle_minority,
            'high_minority': high_minority
        })
    
    # Build result table
    result_data = {'Metric': []}
    
    # Add year columns
    for year in sorted(years):
        result_data[str(year)] = []
    
    # Add Population Share column (if quartile shares calculated)
    if quartile_shares:
        result_data['Population Share (%)'] = []
    
    # Add change column
    if len(years) >= 2:
        time_span = f"{min(years)}-{max(years)}"
        result_data['Change'] = []
    
    # Format quartile ranges for labels
    q25_str = f"{quartiles['q25']:.1f}%"
    q50_str = f"{quartiles['q50']:.1f}%"
    q75_str = f"{quartiles['q75']:.1f}%"
    
    # Check if majority minority tracts exist (if mmct count is 0 and no tracts have >= 50% minority)
    has_mmct_tracts = False
    if 'tract_code' in df.columns and 'tract_minority_population_percent' in df.columns:
        unique_tracts = df[['tract_code', 'tract_minority_population_percent']].drop_duplicates()
        has_mmct_tracts = len(unique_tracts[unique_tracts['tract_minority_population_percent'] >= 50]) > 0
    
    # Define metrics in order
    metrics = [
        ('mmct', 'Majority Minority Census Tracts', quartile_shares.get('mmct'), not has_mmct_tracts),
        ('low_minority', f'Low Minority Census Tracts (0-{q25_str})', quartile_shares.get('low'), False),
        ('moderate_minority', f'Moderate Minority Census Tracts ({q25_str}-{q50_str})', quartile_shares.get('moderate'), False),
        ('middle_minority', f'Middle Minority Census Tracts ({q50_str}-{q75_str})', quartile_shares.get('middle'), False),
        ('high_minority', f'High Minority Census Tracts ({q75_str}-100%)', quartile_shares.get('high'), False),
    ]
    
    # Calculate for each metric
    for metric_key, metric_label, pop_share, needs_asterisk in metrics:
        # Add asterisk if this category doesn't exist
        display_label = metric_label + ('*' if needs_asterisk else '')
        result_data['Metric'].append(display_label)
        
        # Calculate for each year
        metric_changes = []
        for year in sorted(years):
            year_data = next((d for d in yearly_data if d['year'] == year), None)
            if year_data:
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
        if quartile_shares:
            if pop_share is not None:
                result_data['Population Share (%)'].append(f"{pop_share:.1f}%")
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
    if quartile_shares:
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


