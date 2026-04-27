"""Demographic overview section table."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

def create_demographic_overview_table(df: pd.DataFrame, years: List[int], census_data: Dict = None) -> pd.DataFrame:
    """
    Create demographic overview table showing lending activity by race/ethnicity.
    
    Shows number of loans and percent for each race/ethnic group over time.
    Only includes groups that are >= 1% of all loans.
    Denominator = loans with demographic data (total loans minus loans without race/ethnicity data).
    
    Table structure:
    - Far left: Metric column (race/ethnicity group)
    - Middle: Column for each year showing "Number (Percent%)"
    - Far right: Change column showing increase/decrease over entire span
    """
    print(f"  [DEBUG] create_demographic_overview_table called with census_data: {census_data is not None}")
    if census_data:
        print(f"  [DEBUG] census_data has {len(census_data)} counties: {list(census_data.keys())}")
    
    # Check if we have the race/ethnicity columns
    race_columns = ['hispanic_originations', 'black_originations', 'white_originations', 
                   'asian_originations', 'native_american_originations', 'hopi_originations',
                   'multi_racial_originations']
    
    if not all(col in df.columns for col in race_columns):
        # Return empty DataFrame if we don't have the required columns
        return pd.DataFrame()
    
    # Aggregate by year
    yearly_data = []
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        
        # Calculate total loans with demographic data
        # This is the sum of all race/ethnicity originations (may have overlap)
        # We need to calculate loans WITH demographic data differently
        # For now, use total_originations and subtract those without data
        # But we need to track which loans have demographic data
        
        # Sum originations by race/ethnicity
        hispanic = int(year_df['hispanic_originations'].sum())
        black = int(year_df['black_originations'].sum())
        white = int(year_df['white_originations'].sum())
        asian = int(year_df['asian_originations'].sum())
        native_american = int(year_df['native_american_originations'].sum())
        hopi = int(year_df['hopi_originations'].sum())
        multi_racial = int(year_df['multi_racial_originations'].sum()) if 'multi_racial_originations' in year_df.columns else 0
        
        # Total originations
        total_originations = int(year_df['total_originations'].sum())
        
        # Loans with demographic data (from SQL query if available)
        if 'loans_with_demographic_data' in year_df.columns:
            loans_with_demographics = int(year_df['loans_with_demographic_data'].sum())
        else:
            # Fallback: estimate as sum of all race/ethnicity originations
            # Note: This may overcount if loans are counted in multiple categories
            loans_with_demographics = hispanic + black + white + asian + native_american + hopi
        
        # More accurate: loans with demographics = total - loans without any classification
        # Since we're using COALESCE methodology, if a loan has no valid race/ethnicity,
        # it won't be counted in any of the race columns
        # So loans_with_demographics should be the sum of unique loans across all categories
        # For simplicity, we'll use the maximum of the individual counts as a proxy
        # But actually, we should track this in the SQL query
        
        # For now, use total_originations as denominator and calculate percentages
        # The SQL query should provide a has_demographic_data flag, but if not,
        # we'll use the sum of race originations as proxy
        
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
            'loans_with_demographics': loans_with_demographics
        })
    
    # Build table structure
    # First, determine which groups are >= 1% across all years
    # Use total_originations (all applications) as denominator for threshold calculation
    all_totals = [d['total_originations'] for d in yearly_data]
    max_total = max(all_totals) if all_totals else 0
    
    # Define the standard order: White, Hispanic, Black, Asian, Native American, HoPI, Multi-Racial
    standard_order = ['white', 'hispanic', 'black', 'asian', 'native_american', 'hopi', 'multi_racial']
    
    # Calculate max percentage for each group across all years
    group_max_pct = {}
    group_total_share = {}  # Total share across all years for sorting
    for group in standard_order:
        max_count = max([d[group] for d in yearly_data]) if yearly_data else 0
        # Use the year with max total_originations as denominator for threshold check
        max_pct = (max_count / max_total * 100) if max_total > 0 else 0
        group_max_pct[group] = max_pct
        
        # Calculate total share (average across all years) for sorting
        # Use loans_with_demographics for percentage calculation, but total_originations for threshold
        total_count = sum([d[group] for d in yearly_data]) if yearly_data else 0
        total_loans_all_years = sum([d['loans_with_demographics'] for d in yearly_data]) if yearly_data else 0
        avg_share = (total_count / total_loans_all_years * 100) if total_loans_all_years > 0 else 0
        group_total_share[group] = avg_share
    
    # Filter groups >= 1% and sort by total share (descending), then maintain standard order for ties
    included_groups = [group for group in standard_order if group_max_pct.get(group, 0) >= 1.0]
    # Sort by total share descending, but maintain standard order for groups with same share
    included_groups.sort(key=lambda g: (-group_total_share.get(g, 0), standard_order.index(g)))
    
    if not included_groups:
        return pd.DataFrame()
    
    # Get population shares from Census data (if available)
    # Use most recent census data: ACS if available, otherwise 2020 Census
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
            demographics = None
            
            # Check for new structure (time_periods) - prefer ACS, fallback to 2020 Census
            if 'time_periods' in county_census:
                time_periods = county_census.get('time_periods', {})
                # Prefer ACS (most recent), fallback to 2020 Census
                if 'acs' in time_periods and time_periods['acs'].get('demographics'):
                    demographics = time_periods['acs'].get('demographics', {})
                    print(f"  [DEBUG] Using ACS data for {county}")
                elif 'census2020' in time_periods and time_periods['census2020'].get('demographics'):
                    demographics = time_periods['census2020'].get('demographics', {})
                    print(f"  [DEBUG] Using 2020 Census data for {county}")
            # Fallback to old structure (demographics at top level)
            elif 'demographics' in county_census:
                demographics = county_census.get('demographics', {})
                print(f"  [DEBUG] Using legacy demographics structure for {county}")
            
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
            print(f"  [DEBUG] Calculated population_shares: {population_shares}")
        else:
            print(f"  [WARNING] Total population is 0, cannot calculate population shares")
    else:
        print(f"  [DEBUG] No census_data provided, skipping population shares")
    
    # Build result table
    result_data = {'Metric': []}
    
    # Add year columns
    for year in sorted(years):
        result_data[str(year)] = []
    
    # Add Population Share column (if Census data available)
    if population_shares:
        print(f"  [DEBUG] Adding Population Share (%) column to table")
        result_data['Population Share (%)'] = []
    else:
        print(f"  [DEBUG] No population_shares, skipping Population Share column")
    
    # Add change column
    if len(years) >= 2:
        first_year = str(min(years))
        last_year = str(max(years))
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
    
    # Add Total Loans row at the top (showing just the integer, no percentage)
    result_data['Metric'].append('Total Loans')
    for year in sorted(years):
        year_data = next((d for d in yearly_data if d['year'] == year), None)
        if year_data:
            total = year_data['total_originations']
            result_data[str(year)].append(f"{total:,}")
        else:
            result_data[str(year)].append("0")
    # Population Share column (empty for Total Loans row)
    if population_shares:
        result_data['Population Share (%)'].append("")
    # Change column for Total Loans shows percentage change from first to last year
    if len(years) >= 2:
        first_year_data = next((d for d in yearly_data if d['year'] == min(years)), None)
        last_year_data = next((d for d in yearly_data if d['year'] == max(years)), None)
        if first_year_data and last_year_data:
            first_total = first_year_data['total_originations']
            last_total = last_year_data['total_originations']
            if first_total > 0:
                pct_change = ((last_total - first_total) / first_total) * 100
                if pct_change > 0:
                    change_str = f"+{pct_change:.1f}%"
                elif pct_change < 0:
                    change_str = f"{pct_change:.1f}%"
                else:
                    change_str = "0.0%"
            else:
                change_str = "N/A"
            result_data[f'Change Over Time ({time_span})'].append(change_str)
        else:
            result_data[f'Change Over Time ({time_span})'].append("N/A")
    else:
        if len(years) >= 2:
            result_data[f'Change Over Time ({time_span})'].append("N/A")
    
    # Calculate for each included group (show only percentages, no raw numbers)
    for group in included_groups:
        result_data['Metric'].append(group_labels[group])
        
        # Calculate for each year
        group_changes = []
        for year in sorted(years):
            year_data = next((d for d in yearly_data if d['year'] == year), None)
            if year_data:
                count = year_data.get(group, 0)
                # Denominator: loans with demographic data (total loans minus loans without race/ethnicity data)
                total_loans = year_data['total_originations']
                loans_with_demo = year_data['loans_with_demographics']
                denominator = loans_with_demo if loans_with_demo > 0 else total_loans
                pct = (count / denominator * 100) if denominator > 0 else 0.0
                result_data[str(year)].append(f"{pct:.1f}%")
                group_changes.append((count, pct))
            else:
                result_data[str(year)].append("0.0%")
                group_changes.append((0, 0.0))
        
        # Add Population Share column (if Census data available)
        if population_shares:
            pop_share = population_shares.get(group, 0)
            result_data['Population Share (%)'].append(f"{pop_share:.1f}%")
        
        # Calculate change from first to last year (show only percentage point change)
        if len(years) >= 2 and len(group_changes) >= 2:
            first_pct = group_changes[0][1]
            last_pct = group_changes[-1][1]
            pct_change = last_pct - first_pct
            
            # Format change: show only percentage point change
            if pct_change > 0:
                change_str = f"+{pct_change:.1f}pp"
            elif pct_change < 0:
                change_str = f"{pct_change:.1f}pp"
            else:
                change_str = "0.0pp"
            result_data[f'Change Over Time ({time_span})'].append(change_str)
        else:
            if len(years) >= 2:
                result_data[f'Change Over Time ({time_span})'].append("N/A")
    
    result = pd.DataFrame(result_data)
    return result


