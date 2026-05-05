"""Income tracts section tables (and tract population helper)."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import requests

from justdata.apps.lendsight.report_builder.sections.income_indicators import (
    calculate_minority_quartiles,
    classify_tract_minority_quartile,
)

def create_income_neighborhood_tracts_table(df: pd.DataFrame, years: List[int], 
                                            hud_data: Dict[str, Dict[str, float]] = None,
                                            census_data: Dict = None) -> pd.DataFrame:
    """
    Create Table 2: Lending to Census Tracts.
    
    Shows:
    - Low to Moderate Income Census Tracts (aggregate)
    - Low Income Census Tracts
    - Moderate Income Census Tracts
    - Middle Income Census Tracts
    - Upper Income Census Tracts
    - Majority Minority Census Tracts (aggregate)
    - Low Minority Census Tracts (bottom quartile)
    - Moderate Minority Census Tracts (2nd quartile)
    - Middle Minority Census Tracts (3rd quartile)
    - High Minority Census Tracts (top quartile)
    
    Args:
        df: DataFrame with loan data
        years: List of years
        hud_data: Dictionary mapping GEOID5 to HUD income distribution data
        census_data: Dictionary with census demographic data for population shares
    """
    # Check required columns
    required_cols = ['total_originations', 'lmict_originations', 'low_income_tract_originations',
                     'moderate_income_tract_originations', 'middle_income_tract_originations',
                     'upper_income_tract_originations', 'mmct_originations', 
                     'tract_minority_population_percent', 'tract_code']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Warning: Missing columns for income/neighborhood tracts table: {missing_cols}")
        return pd.DataFrame()
    
    # Calculate minority quartiles
    quartiles = calculate_minority_quartiles(df)
    
    # Classify each row's tract into a quartile
    df['minority_quartile'] = df['tract_minority_population_percent'].apply(
        lambda x: classify_tract_minority_quartile(x, quartiles)
    )
    
    # Aggregate by year
    yearly_data = []
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        
        # Income tract categories
        total = int(year_df['total_originations'].sum())
        lmict = int(year_df['lmict_originations'].sum())
        low_tract = int(year_df['low_income_tract_originations'].sum())
        moderate_tract = int(year_df['moderate_income_tract_originations'].sum())
        middle_tract = int(year_df['middle_income_tract_originations'].sum())
        upper_tract = int(year_df['upper_income_tract_originations'].sum())
        mmct = int(year_df['mmct_originations'].sum())
        
        # Minority quartile categories
        low_minority = int(year_df[year_df['minority_quartile'] == 'low']['total_originations'].sum())
        moderate_minority = int(year_df[year_df['minority_quartile'] == 'moderate']['total_originations'].sum())
        middle_minority = int(year_df[year_df['minority_quartile'] == 'middle']['total_originations'].sum())
        high_minority = int(year_df[year_df['minority_quartile'] == 'high']['total_originations'].sum())
        
        yearly_data.append({
            'year': year,
            'total': total,
            'lmict': lmict,
            'low_tract': low_tract,
            'moderate_tract': moderate_tract,
            'middle_tract': middle_tract,
            'upper_tract': upper_tract,
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
    
    # Add change column
    if len(years) >= 2:
        time_span = f"{min(years)}-{max(years)}"
        result_data['Change'] = []
    
    # Format quartile ranges for labels
    q25_str = f"{quartiles['q25']:.1f}%"
    q50_str = f"{quartiles['q50']:.1f}%"
    q75_str = f"{quartiles['q75']:.1f}%"
    
    # Define metrics in order
    metrics = [
        ('lmict', 'Low to Moderate Income Census Tracts', None),
        ('low_tract', 'Low Income Census Tracts', None),
        ('moderate_tract', 'Moderate Income Census Tracts', None),
        ('middle_tract', 'Middle Income Census Tracts', None),
        ('upper_tract', 'Upper Income Census Tracts', None),
        ('mmct', 'Majority Minority Census Tracts', None),
        ('low_minority', f'Low Minority Census Tracts (0-{q25_str})', None),
        ('moderate_minority', f'Moderate Minority Census Tracts ({q25_str}-{q50_str})', None),
        ('middle_minority', f'Middle Minority Census Tracts ({q50_str}-{q75_str})', None),
        ('high_minority', f'High Minority Census Tracts ({q75_str}-100%)', None),
    ]
    
    # Calculate for each metric
    for metric_key, metric_label, _ in metrics:
        result_data['Metric'].append(metric_label)
        
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


def create_income_tracts_table(df: pd.DataFrame, years: List[int],
                                hud_data: Dict[str, Dict[str, float]] = None,
                                census_data: Dict = None) -> pd.DataFrame:
    """
    Create Table 2: Lending to Census Tracts by Income Level.

    Shows:
    - Low to Moderate Income Census Tracts (aggregate)
    - Low Income Census Tracts
    - Moderate Income Census Tracts
    - Middle Income Census Tracts
    - Upper Income Census Tracts

    Population Share column uses ACS tract-level data (percentage of census tracts in each income category).

    Args:
        df: DataFrame with loan data (must include tract_code and tract_to_msa_income_percentage columns)
        years: List of years
        hud_data: Dictionary mapping GEOID5 to HUD income distribution data (not used for Population Share)
        census_data: Dictionary with census demographic data (not used for Population Share)
    """
    # Check required columns
    required_cols = ['total_originations', 'lmict_originations', 'low_income_tract_originations',
                     'moderate_income_tract_originations', 'middle_income_tract_originations',
                     'upper_income_tract_originations', 'geoid5']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Warning: Missing columns for income tracts table: {missing_cols}")
        return pd.DataFrame()
    
    # Aggregate by year
    yearly_data = []
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        
        # Income tract categories
        total = int(year_df['total_originations'].sum())
        lmict = int(year_df['lmict_originations'].sum())
        low_tract = int(year_df['low_income_tract_originations'].sum())
        moderate_tract = int(year_df['moderate_income_tract_originations'].sum())
        middle_tract = int(year_df['middle_income_tract_originations'].sum())
        upper_tract = int(year_df['upper_income_tract_originations'].sum())
        
        yearly_data.append({
            'year': year,
            'total': total,
            'lmict': lmict,
            'low_tract': low_tract,
            'moderate_tract': moderate_tract,
            'middle_tract': middle_tract,
            'upper_tract': upper_tract
        })
    
    # Build result table
    result_data = {'Metric': []}
    
    # Add year columns
    for year in sorted(years):
        result_data[str(year)] = []
    
    # Calculate tract income shares from ACS tract-level data
    # For Table 2 (Neighborhood Income), Population Share represents the percentage of census tracts
    # (not population) in each income category, calculated from the tract data in the DataFrame
    tract_income_shares = {}
    if 'tract_code' in df.columns:
        if 'tract_to_msa_income_percentage' in df.columns:
            # Get unique tracts and their income classifications
            unique_tracts = df[['tract_code', 'tract_to_msa_income_percentage']].drop_duplicates()
            total_tracts = len(unique_tracts)

            if total_tracts > 0:
                # Classify tracts by income category based on tract_to_msa_income_percentage
                # Low: <= 50%, Moderate: >50% and <=80%, Middle: >80% and <=120%, Upper: >120%
                # Handle NaN/null values
                unique_tracts_clean = unique_tracts.dropna(subset=['tract_to_msa_income_percentage'])
                if len(unique_tracts_clean) > 0:
                    low_tracts = len(unique_tracts_clean[unique_tracts_clean['tract_to_msa_income_percentage'] <= 50])
                    moderate_tracts = len(unique_tracts_clean[(unique_tracts_clean['tract_to_msa_income_percentage'] > 50) &
                                                           (unique_tracts_clean['tract_to_msa_income_percentage'] <= 80)])
                    middle_tracts = len(unique_tracts_clean[(unique_tracts_clean['tract_to_msa_income_percentage'] > 80) &
                                                          (unique_tracts_clean['tract_to_msa_income_percentage'] <= 120)])
                    upper_tracts = len(unique_tracts_clean[unique_tracts_clean['tract_to_msa_income_percentage'] > 120])

                    total_valid_tracts = len(unique_tracts_clean)

                    # Calculate percentages of tracts in each category
                    tract_income_shares['low'] = (low_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
                    tract_income_shares['moderate'] = (moderate_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
                    tract_income_shares['lmict'] = tract_income_shares['low'] + tract_income_shares['moderate']
                    tract_income_shares['middle'] = (middle_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
                    tract_income_shares['upper'] = (upper_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
                    print(f"  [DEBUG] Calculated tract income shares from ACS data: {tract_income_shares}")
        else:
            print(f"  [WARNING] tract_to_msa_income_percentage column not found in DataFrame. Available columns: {list(df.columns)}")
            print(f"  [WARNING] Population Share column will not be added to Table 2")

    # Always add Population Share column if we have tract_income_shares data
    if tract_income_shares:
        result_data['Population Share (%)'] = []
        print(f"  [DEBUG] Added Population Share (%) column to Table 2")
    else:
        print(f"  [WARNING] No tract_income_shares calculated - Population Share column will not be added")
    
    # Add change column
    if len(years) >= 2:
        time_span = f"{min(years)}-{max(years)}"
        result_data['Change'] = []
    
    # Check if low income tracts exist
    # Use multiple checks: tract income share, loan data, or tract classification
    has_low_income_tracts = False

    # First check: If tract income shares show > 0, tracts definitely exist
    if tract_income_shares and tract_income_shares.get('low', 0) > 0:
        has_low_income_tracts = True
        print(f"  [DEBUG] Low income tracts detected via tract income share: {tract_income_shares.get('low', 0):.1f}%")
    # Second check: If there are any loans to low-income tracts in any year
    elif any(d['low_tract'] > 0 for d in yearly_data):
        has_low_income_tracts = True
        print(f"  [DEBUG] Low income tracts detected via loan data")
    # Third check: If tract classification data shows tracts with <= 50% MSA income
    elif 'tract_code' in df.columns and 'tract_to_msa_income_percentage' in df.columns:
        unique_tracts = df[['tract_code', 'tract_to_msa_income_percentage']].drop_duplicates()
        has_low_income_tracts = len(unique_tracts[unique_tracts['tract_to_msa_income_percentage'] <= 50]) > 0
        if has_low_income_tracts:
            print(f"  [DEBUG] Low income tracts detected via tract classification")

    if not has_low_income_tracts:
        print(f"  [DEBUG] No low income tracts detected - will add asterisk")

    # Define metrics in order
    # Note: For 'lmict', we'll calculate it as low_tract + moderate_tract to ensure mathematical consistency
    metrics = [
        ('lmict', 'Low to Moderate Income Census Tracts', tract_income_shares.get('lmict'), False, True),  # True = calculate as low + moderate
        ('low_tract', 'Low Income Census Tracts', tract_income_shares.get('low'), not has_low_income_tracts, False),
        ('moderate_tract', 'Moderate Income Census Tracts', tract_income_shares.get('moderate'), False, False),
        ('middle_tract', 'Middle Income Census Tracts', tract_income_shares.get('middle'), False, False),
        ('upper_tract', 'Upper Income Census Tracts', tract_income_shares.get('upper'), False, False),
    ]
    
    # Calculate for each metric
    for metric_key, metric_label, pop_share, needs_asterisk, is_calculated in metrics:
        # Add asterisk if this category doesn't exist
        display_label = metric_label + ('*' if needs_asterisk else '')
        result_data['Metric'].append(display_label)
        
        # Calculate for each year
        metric_changes = []
        for year in sorted(years):
            year_data = next((d for d in yearly_data if d['year'] == year), None)
            if year_data:
                # For LMICT, calculate as Low + Moderate to ensure math is correct
                if is_calculated and metric_key == 'lmict':
                    count = year_data['low_tract'] + year_data['moderate_tract']
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
        if tract_income_shares:
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
    if tract_income_shares:
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


def get_tract_population_data_for_counties(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Fetch tract-level population data from Census API for all counties in the dataframe.
    
    Returns:
        Dictionary mapping tract_code to {total_population, minority_percentage}
    """
    import os
    
    api_key = os.getenv('CENSUS_API_KEY')
    if not api_key:
        print("Warning: CENSUS_API_KEY not set. Cannot fetch tract-level population data.")
        return {}
    
    # Get unique state/county combinations from dataframe
    if 'state_fips' not in df.columns or 'county_fips' not in df.columns:
        print("Warning: state_fips or county_fips not in dataframe. Cannot fetch tract data.")
        return {}
    
    # Get unique state/county pairs
    state_county_pairs = df[['state_fips', 'county_fips']].drop_duplicates()
    
    tract_data = {}
    
    for _, row in state_county_pairs.iterrows():
        state_fips = str(int(row['state_fips'])).zfill(2)
        county_fips = str(int(row['county_fips'])).zfill(3)
        
        try:
            # Use 2022 ACS 5-year estimates (most recent available)
            acs_year = "2022"
            url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
            params = {
                'get': 'NAME,B01003_001E,B03002_003E,tract',
                'for': f'tract:*',
                'in': f'state:{state_fips} county:{county_fips}',
                'key': api_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if len(data) < 2:
                continue
            
            headers = data[0]
            name_idx = headers.index('NAME')
            total_pop_idx = headers.index('B01003_001E')
            white_non_hisp_idx = headers.index('B03002_003E')
            tract_idx = headers.index('tract')
            
            for row_data in data[1:]:
                tract_code_str = row_data[tract_idx].zfill(6)
                # Create full tract code: state (2) + county (3) + tract (6) = 11 digits
                full_tract_code = f"{state_fips}{county_fips}{tract_code_str}"
                
                try:
                    total_pop = float(row_data[total_pop_idx]) if row_data[total_pop_idx] not in ['-888888888', '-666666666', '-999999999', 'null', 'None', ''] else 0
                    white_non_hisp = float(row_data[white_non_hisp_idx]) if row_data[white_non_hisp_idx] not in ['-888888888', '-666666666', '-999999999', 'null', 'None', ''] else 0
                    
                    if total_pop > 0:
                        minority_pop = total_pop - white_non_hisp
                        minority_pct = (minority_pop / total_pop) * 100 if total_pop > 0 else 0
                        
                        tract_data[full_tract_code] = {
                            'total_population': total_pop,
                            'minority_percentage': minority_pct
                        }
                except (ValueError, IndexError):
                    continue
                    
        except Exception as e:
            print(f"Warning: Error fetching tract data for {state_fips}/{county_fips}: {e}")
            continue
    
    return tract_data


