"""Excel-shaped demographic and population tables."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

def create_demographic_overview_table_for_excel(df: pd.DataFrame, years: List[int], census_data: Dict = None) -> pd.DataFrame:
    """
    Create demographic overview table for Excel export with ALL race/ethnic categories.
    
    This version includes all categories regardless of percentage.
    Note: "No Data" row is not included per user request.
    """
    race_columns = ['hispanic_originations', 'black_originations', 'white_originations', 
                   'asian_originations', 'native_american_originations', 'hopi_originations',
                   'multi_racial_originations']
    
    if not all(col in df.columns for col in race_columns):
        return pd.DataFrame()
    
    # Aggregate by year
    yearly_data = []
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        
        hispanic = int(year_df['hispanic_originations'].sum())
        black = int(year_df['black_originations'].sum())
        white = int(year_df['white_originations'].sum())
        asian = int(year_df['asian_originations'].sum())
        native_american = int(year_df['native_american_originations'].sum())
        hopi = int(year_df['hopi_originations'].sum())
        multi_racial = int(year_df['multi_racial_originations'].sum()) if 'multi_racial_originations' in year_df.columns else 0
        
        total_originations = int(year_df['total_originations'].sum())
        
        if 'loans_with_demographic_data' in year_df.columns:
            loans_with_demographics = int(year_df['loans_with_demographic_data'].sum())
        else:
            loans_with_demographics = hispanic + black + white + asian + native_american + hopi
        
        no_data_loans = total_originations - loans_with_demographics
        
        yearly_data.append({
            'year': year,
            'total_originations': total_originations,
            'hispanic': hispanic,
            'black': black,
            'white': white,
            'asian': asian,
            'native_american': native_american,
            'hopi': hopi,
            'multi_racial': multi_racial,
            'loans_with_demographics': loans_with_demographics,
            'no_data_loans': no_data_loans
        })
    
    # Get population shares from Census data (if available)
    # For multiple counties, aggregate by weighting by total population
    population_shares = {}
    if census_data:
        total_population = 0
        group_totals = {
            'hispanic': 0,
            'black': 0,
            'white': 0,
            'asian': 0,
            'native_american': 0,
            'hopi': 0,
            'multi_racial': 0
        }
        
        # Aggregate across all counties by calculating weighted averages
        for county, county_census in census_data.items():
            demographics = county_census.get('demographics', {})
            if demographics:
                county_pop = demographics.get('total_population', 0)
                if county_pop and county_pop > 0:
                    total_population += county_pop
                    # Calculate actual counts from percentages
                    group_totals['hispanic'] += (demographics.get('hispanic_percentage', 0) / 100) * county_pop
                    group_totals['black'] += (demographics.get('black_percentage', 0) / 100) * county_pop
                    group_totals['white'] += (demographics.get('white_percentage', 0) / 100) * county_pop
                    group_totals['asian'] += (demographics.get('asian_percentage', 0) / 100) * county_pop
                    group_totals['native_american'] += (demographics.get('native_american_percentage', 0) / 100) * county_pop
                    group_totals['hopi'] += (demographics.get('hopi_percentage', 0) / 100) * county_pop
                    group_totals['multi_racial'] += (demographics.get('multi_racial_percentage', 0) / 100) * county_pop
        
        # Calculate weighted average percentages
        if total_population > 0:
            for group in group_totals:
                population_shares[group] = (group_totals[group] / total_population * 100)
    
    # Build result table - include ALL groups
    result_data = {'Metric': []}
    
    # Add year columns
    for year in sorted(years):
        result_data[str(year)] = []
    
    # Add Population Share column (if Census data available)
    if population_shares:
        result_data['Population Share (%)'] = []
    
    # Add change column
    if len(years) >= 2:
        time_span = f"{min(years)}-{max(years)}"
        result_data[f'Change Over Time ({time_span})'] = []
    
    # Group labels
    group_labels = {
        'hispanic': 'Hispanic',
        'black': 'Black',
        'white': 'White',
        'asian': 'Asian',
        'native_american': 'Native American',
        'hopi': 'Hawaiian/Pacific Islander',
        'multi_racial': 'Multi-Racial'
    }
    
    # Add Total Loans row
    result_data['Metric'].append('Total Loans')
    for year in sorted(years):
        year_data = next((d for d in yearly_data if d['year'] == year), None)
        if year_data:
            result_data[str(year)].append(year_data['total_originations'])
        else:
            result_data[str(year)].append(0)
    
    # Population Share column (empty for Total Loans row)
    if population_shares:
        result_data['Population Share (%)'].append("")
    
    if len(years) >= 2:
        first_year_data = next((d for d in yearly_data if d['year'] == min(years)), None)
        last_year_data = next((d for d in yearly_data if d['year'] == max(years)), None)
        if first_year_data and last_year_data:
            count_change = last_year_data['total_originations'] - first_year_data['total_originations']
            result_data[f'Change Over Time ({time_span})'].append(count_change)
        else:
            result_data[f'Change Over Time ({time_span})'].append(0)
    
    # Add ALL race/ethnicity groups (not filtered by 1%)
    # Order: White, Hispanic, Black, Asian, Native American, HoPI, Multi-Racial
    for group in ['white', 'hispanic', 'black', 'asian', 'native_american', 'hopi', 'multi_racial']:
        result_data['Metric'].append(group_labels[group])
        
        group_changes = []
        for year in sorted(years):
            year_data = next((d for d in yearly_data if d['year'] == year), None)
            if year_data:
                count = year_data.get(group, 0)
                loans_with_demo = year_data['loans_with_demographics']
                pct = (count / loans_with_demo * 100) if loans_with_demo > 0 else 0.0
                result_data[str(year)].append(pct)
                group_changes.append((count, pct))
            else:
                result_data[str(year)].append(0.0)
                group_changes.append((0, 0.0))
        
        # Add Population Share column (if Census data available)
        if population_shares:
            pop_share = population_shares.get(group, 0)
            result_data['Population Share (%)'].append(pop_share)
        
        # Change column
        if len(years) >= 2 and len(group_changes) >= 2:
            first_pct = group_changes[0][1]
            last_pct = group_changes[-1][1]
            pct_change = last_pct - first_pct
            result_data[f'Change Over Time ({time_span})'].append(pct_change)
        else:
            if len(years) >= 2:
                result_data[f'Change Over Time ({time_span})'].append(0.0)
    
    # Note: "No Data" row removed per user request
    
    result = pd.DataFrame(result_data)
    return result


def create_population_demographics_table_for_excel(census_data: Dict = None) -> pd.DataFrame:
    """
    Create population demographics table from Census data for Excel export.
    
    This table shows total population and racial/ethnic composition across time periods
    (2010 Census, 2020 Census, and most recent ACS 5-year estimates).
    
    For multiple counties, demographics are aggregated using weighted averages
    based on each county's population.
    
    Args:
        census_data: Dictionary of Census data by county name, with structure:
            {
                'County Name': {
                    'time_periods': {
                        'census2010': {
                            'year': '2010 Census',
                            'demographics': {
                                'total_population': int,
                                'white_percentage': float,
                                'black_percentage': float,
                                ...
                            }
                        },
                        ...
                    }
                }
            }
    
    Returns:
        DataFrame with rows for Total Population and each demographic group,
        and columns for each time period.
    """
    if not census_data or len(census_data) == 0:
        return pd.DataFrame()
    
    def aggregate_time_period(time_period_key: str):
        """Aggregate demographics across counties for a specific time period using weighted averages."""
        total_population = 0
        white_sum = 0
        black_sum = 0
        asian_sum = 0
        native_am_sum = 0
        hopi_sum = 0
        multi_racial_sum = 0
        hispanic_sum = 0
        
        for county_name, county_data in census_data.items():
            time_periods = county_data.get('time_periods', {})
            period_data = time_periods.get(time_period_key)
            
            if period_data and period_data.get('demographics'):
                demographics = period_data['demographics']
                pop = demographics.get('total_population', 0)
                
                if pop > 0:
                    total_population += pop
                    
                    # Calculate weighted counts: (percentage * population) / 100
                    white_sum += (demographics.get('white_percentage', 0) * pop) / 100
                    black_sum += (demographics.get('black_percentage', 0) * pop) / 100
                    asian_sum += (demographics.get('asian_percentage', 0) * pop) / 100
                    native_am_sum += (demographics.get('native_american_percentage', 0) * pop) / 100
                    hopi_sum += (demographics.get('hopi_percentage', 0) * pop) / 100
                    multi_racial_sum += (demographics.get('multi_racial_percentage', 0) * pop) / 100
                    hispanic_sum += (demographics.get('hispanic_percentage', 0) * pop) / 100
        
        if total_population == 0:
            return None
        
        # Calculate weighted average percentages
        return {
            'total_population': total_population,
            'white_percentage': (white_sum / total_population) * 100,
            'black_percentage': (black_sum / total_population) * 100,
            'hispanic_percentage': (hispanic_sum / total_population) * 100,
            'asian_percentage': (asian_sum / total_population) * 100,
            'native_american_percentage': (native_am_sum / total_population) * 100,
            'hopi_percentage': (hopi_sum / total_population) * 100,
            'multi_racial_percentage': (multi_racial_sum / total_population) * 100
        }
    
    # Aggregate data for each time period
    census2010_data = aggregate_time_period('census2010')
    census2020_data = aggregate_time_period('census2020')
    acs_data = aggregate_time_period('acs')
    
    # Determine which time periods we have data for and get labels
    time_periods = []
    
    if census2010_data:
        time_periods.append({
            'key': 'census2010',
            'label': '2010 Census',
            'data': census2010_data
        })
    
    if census2020_data:
        time_periods.append({
            'key': 'census2020',
            'label': '2020 Census',
            'data': census2020_data
        })
    
    if acs_data:
        # Get the ACS year label from the first county
        first_county = list(census_data.values())[0]
        acs_period = first_county.get('time_periods', {}).get('acs', {})
        acs_label = acs_period.get('year', '2024 ACS')
        time_periods.append({
            'key': 'acs',
            'label': acs_label,
            'data': acs_data
        })
    
    if len(time_periods) == 0:
        return pd.DataFrame()
    
    # Determine visible race groups (show if >= 1% in any time period)
    all_percentages = {
        'white': [],
        'black': [],
        'hispanic': [],
        'asian': [],
        'native_american': [],
        'hopi': [],
        'multi_racial': []
    }
    
    for period in time_periods:
        if period['data']:
            all_percentages['white'].append(period['data'].get('white_percentage', 0))
            all_percentages['black'].append(period['data'].get('black_percentage', 0))
            all_percentages['hispanic'].append(period['data'].get('hispanic_percentage', 0))
            all_percentages['asian'].append(period['data'].get('asian_percentage', 0))
            all_percentages['native_american'].append(period['data'].get('native_american_percentage', 0))
            all_percentages['hopi'].append(period['data'].get('hopi_percentage', 0))
            all_percentages['multi_racial'].append(period['data'].get('multi_racial_percentage', 0))
    
    # Define race groups in desired order: White, Hispanic, Black, Asian, Native American, HoPI, Multi-Racial
    race_groups = [
        {'name': 'White (%)', 'key': 'white', 'percentages': all_percentages['white']},
        {'name': 'Hispanic (%)', 'key': 'hispanic', 'percentages': all_percentages['hispanic']},
        {'name': 'Black (%)', 'key': 'black', 'percentages': all_percentages['black']},
        {'name': 'Asian (%)', 'key': 'asian', 'percentages': all_percentages['asian']},
        {'name': 'Native American (%)', 'key': 'native_american', 'percentages': all_percentages['native_american']},
        {'name': 'Hawaiian/PI (%)', 'key': 'hopi', 'percentages': all_percentages['hopi']},
        {'name': 'Multi-Racial (%)', 'key': 'multi_racial', 'percentages': all_percentages['multi_racial']}
    ]
    
    # Filter out groups that are less than 1% in all time periods
    visible_groups = [g for g in race_groups if any(pct >= 1.0 for pct in g['percentages'])]
    
    # Build the table data
    table_data = []
    
    # Total Population row
    total_pop_row = {'Demographic': 'Total Population'}
    for period in time_periods:
        total_pop_row[period['label']] = period['data'].get('total_population', 0)
    table_data.append(total_pop_row)
    
    # Add rows for visible race groups
    for group in visible_groups:
        group_row = {'Demographic': group['name']}
        for period in time_periods:
            pct = period['data'].get(f"{group['key']}_percentage", 0)
            group_row[period['label']] = pct
        table_data.append(group_row)
    
    # Create DataFrame
    if not table_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(table_data)
    return df


