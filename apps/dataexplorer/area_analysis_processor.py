#!/usr/bin/env python3
"""
Area Analysis Data Processor
Processes raw HMDA, Small Business, and Branch data into table formats for Area Analysis dashboard.
Similar to LendSight's mortgage_report_builder but returns JSON instead of DataFrames.
"""

from typing import List, Dict, Any
from collections import defaultdict


def process_hmda_area_analysis(raw_data: List[Dict[str, Any]], years: List[int], geoids: List[str], raw_data_all_purposes: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process raw HMDA data into structured tables for Area Analysis.
    
    Args:
        raw_data: List of dictionaries from BigQuery results (filtered by user's loan purpose selection)
        years: List of years in the analysis
        geoids: List of geographic identifiers
        raw_data_all_purposes: Optional list with ALL loan purposes (1,2,3,4) for summary_by_purpose table
    
    Returns:
        Dictionary with all analysis tables
    """
    if not raw_data:
        return {
            'summary': [],
            'summary_by_purpose': [],
            'demographics': [],
            'income_neighborhood': [],
            'top_lenders': [],
            'top_lenders_by_purpose': {},
            'hhi': None,
            'hhi_by_year': [],
            'hhi_by_year_by_purpose': {},
            'trends': [],
            'trends_by_purpose': {}
        }
    
    # Process each table
    summary_table = create_summary_table(raw_data, years)
    # Use all-purposes data for summary_by_purpose to ensure all loan types are shown
    summary_by_purpose_data = raw_data_all_purposes if raw_data_all_purposes else raw_data
    summary_by_purpose_table = create_summary_by_purpose_table(summary_by_purpose_data, years)
    demographics_table = create_demographics_table(raw_data, years)
    demographics_by_purpose = create_demographics_by_purpose_table(summary_by_purpose_data, years) if summary_by_purpose_data else {'all': demographics_table, 'Home Purchase': [], 'Refinance': [], 'Home Equity': []}
    income_neighborhood_table = create_income_neighborhood_table(raw_data, years)
    income_neighborhood_by_purpose = create_income_neighborhood_by_purpose_table(summary_by_purpose_data, years) if summary_by_purpose_data else {'all': income_neighborhood_table, 'Home Purchase': [], 'Refinance': [], 'Home Equity': []}
    top_lenders_table = create_top_lenders_table(raw_data, years)
    # Use all-purposes data for top_lenders_by_purpose to ensure all loan types are shown
    top_lenders_by_purpose = create_top_lenders_by_purpose(summary_by_purpose_data, years) if summary_by_purpose_data else create_top_lenders_by_purpose(raw_data, years)
    hhi_data = calculate_hhi(raw_data, years)
    hhi_by_year_table = calculate_hhi_by_year(raw_data, years)
    # Use all-purposes data for HHI by purpose to ensure Refinance (31,32) and Home Equity (2,4) are included
    hhi_by_year_by_purpose = calculate_hhi_by_year_by_purpose(summary_by_purpose_data, years) if summary_by_purpose_data else calculate_hhi_by_year_by_purpose(raw_data, years)
    trends_table = create_trends_table(raw_data, years)
    trends_by_purpose = create_trends_by_purpose(raw_data, years)
    
    return {
        'summary': summary_table,
        'summary_by_purpose': summary_by_purpose_table,
        'demographics': demographics_table,
        'demographics_by_purpose': demographics_by_purpose,
        'income_neighborhood': income_neighborhood_table,
        'income_neighborhood_by_purpose': income_neighborhood_by_purpose,
        'top_lenders': top_lenders_table,
        'top_lenders_by_purpose': top_lenders_by_purpose,
        'hhi': hhi_data,
        'hhi_by_year': hhi_by_year_table,
        'hhi_by_year_by_purpose': hhi_by_year_by_purpose,
        'trends': trends_table,
        'trends_by_purpose': trends_by_purpose
    }


def process_sb_area_analysis(raw_data: List[Dict[str, Any]], years: List[int], geoids: List[str]) -> Dict[str, Any]:
    """
    Process raw Small Business data into structured tables for Area Analysis.
    """
    if not raw_data:
        return {
            'summary': [],
            'demographics': [],
            'income_neighborhood': [],
            'top_lenders': [],
            'hhi': None,
            'trends': []
        }
    
    # For Small Business, we'll create similar tables but adapted for SB data structure
    summary_table = create_sb_summary_table(raw_data, years)
    demographics_table = create_sb_demographics_table(raw_data, years)
    income_neighborhood_table = create_sb_income_neighborhood_table(raw_data, years)
    top_lenders_table = create_sb_top_lenders_table(raw_data, years)
    hhi_data = calculate_sb_hhi(raw_data, years)
    hhi_by_year_table = calculate_sb_hhi_by_year(raw_data, years)
    hhi_by_year_by_revenue = calculate_sb_hhi_by_year_by_revenue(raw_data, years)
    trends_table = create_sb_trends_table(raw_data, years)
    
    return {
        'summary': summary_table,
        'demographics': demographics_table,
        'income_neighborhood': income_neighborhood_table,
        'top_lenders': top_lenders_table,
        'hhi': hhi_data,
        'hhi_by_year': hhi_by_year_table,
        'hhi_by_year_by_revenue': hhi_by_year_by_revenue,
        'trends': trends_table
    }


def process_branch_area_analysis(raw_data: List[Dict[str, Any]], years: List[int], geoids: List[str]) -> Dict[str, Any]:
    """
    Process raw Branch data into structured tables for Area Analysis.
    """
    if not raw_data:
        return {
            'summary': [],
            'demographics': [],
            'income_neighborhood': [],
            'top_lenders': [],
            'hhi': None,
            'trends': []
        }
    
    # For Branches, we'll create similar tables but adapted for branch data structure
    summary_table = create_branch_summary_table(raw_data, years)
    demographics_table = []  # Branches don't have demographic data
    income_neighborhood_table = create_branch_income_neighborhood_table(raw_data, years)
    top_lenders_table = create_branch_top_lenders_table(raw_data, years)
    hhi_data = calculate_branch_hhi(raw_data, years)
    hhi_by_year_result = calculate_branch_hhi_by_year(raw_data, years)
    # Convert dict structure to list for frontend compatibility
    if isinstance(hhi_by_year_result, dict):
        # Use all_branches as the main list, but keep the full structure
        hhi_by_year_table = hhi_by_year_result.get('all_branches', [])
        # Store full structure separately for Excel export
        hhi_by_year_full = hhi_by_year_result
    else:
        hhi_by_year_table = hhi_by_year_result
        hhi_by_year_full = None
    trends_table = create_branch_trends_table(raw_data, years)
    
    # Calculate total change in branches from 2021 to 2025
    branch_change_2021_2025 = None
    if 2021 in years and 2025 in years:
        branches_2021 = len([row for row in raw_data if str(row.get('year', '')) == '2021'])
        branches_2025 = len([row for row in raw_data if str(row.get('year', '')) == '2025'])
        branch_change_2021_2025 = {
            'year_2021': branches_2021,
            'year_2025': branches_2025,
            'change': branches_2025 - branches_2021,
            'change_percent': ((branches_2025 - branches_2021) / branches_2021 * 100) if branches_2021 > 0 else 0
        }
    
    result = {
        'summary': summary_table,
        'demographics': demographics_table,
        'income_neighborhood': income_neighborhood_table,
        'top_lenders': top_lenders_table,
        'hhi': hhi_data,
        'hhi_by_year': hhi_by_year_table,
        'trends': trends_table,
        'branch_change_2021_2025': branch_change_2021_2025
    }
    # Add full HHI by year structure for Excel export
    if hhi_by_year_full:
        result['hhi_by_year_full'] = hhi_by_year_full
    return result


# HMDA Processing Functions (existing)

def create_summary_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create summary table with yearly totals."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.debug(f"create_summary_table: Processing {len(raw_data)} rows for years {years}")
    if raw_data and len(raw_data) > 0:
        logger.debug(f"create_summary_table: Sample row keys: {list(raw_data[0].keys())}")
        logger.debug(f"create_summary_table: Sample row (first 5 fields): {dict(list(raw_data[0].items())[:5])}")
    
    yearly_totals = defaultdict(lambda: {'loans': 0, 'amount': 0})
    
    # Track which fields we're actually finding
    found_fields = set()
    missing_count = 0
    
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        year_str_list = [str(y) for y in years]
        if year and year in year_str_list:
            # Try multiple possible field names for loan count
            loan_count = (
                row.get('total_metric') or 
                row.get('total_loans') or 
                row.get('loan_count') or 
                0
            )
            loan_amount = row.get('total_loan_amount') or row.get('loan_amount') or 0
            
            # Track which fields we found
            if 'total_metric' in row:
                found_fields.add('total_metric')
            if 'total_loan_amount' in row:
                found_fields.add('total_loan_amount')
            
            # Convert to numeric, handling None and empty strings
            try:
                count_val = int(loan_count) if loan_count is not None and loan_count != '' else 0
                amount_val = float(loan_amount) if loan_amount is not None and loan_amount != '' else 0
            except (ValueError, TypeError) as e:
                logger.warning(f"Error converting loan_count/amount: {e}, row: {dict(list(row.items())[:3])}")
                count_val = 0
                amount_val = 0
            
            if count_val == 0 and loan_count not in (None, '', 0):
                missing_count += 1
            
            yearly_totals[year]['loans'] += count_val
            yearly_totals[year]['amount'] += amount_val
        else:
            # Debug: log rows that don't match
            if raw_data and len(raw_data) <= 20:  # Only log if small dataset
                logger.debug(f"Row year '{year}' not in {year_str_list}")
    
    logger.info(f"create_summary_table: Yearly totals: {dict(yearly_totals)}")
    logger.info(f"create_summary_table: Found fields: {found_fields}, Rows with count=0 but field exists: {missing_count}")
    
    table = []
    for year in sorted(years, reverse=True):
        year_str = str(year)
        totals = yearly_totals[year_str]
        avg = totals['amount'] / totals['loans'] if totals['loans'] > 0 else 0
        
        table.append({
            'year': year_str,
            'total_loans': totals['loans'],
            'total_amount': round(totals['amount'], 2),
            'avg_amount': round(avg, 2)
        })
    
    return table


def create_summary_by_purpose_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """
    Create summary table broken down by loan purpose:
    - Home Purchase (loan_purpose = '1')
    - Refinance (loan_purpose = '31' or '32' - refinance and cash-out refinance)
    - Home Equity (loan_purpose = '2' or '4' - home improvement and other)
    """
    # Map loan purposes to categories
    purpose_categories = {
        '1': 'Home Purchase',
        '2': 'Home Equity',  # Home Improvement
        '4': 'Home Equity',  # Other
        '31': 'Refinance',  # Refinance
        '32': 'Refinance'   # Cash-out refinance
    }
    
    # Aggregate by year and purpose category
    yearly_by_purpose = defaultdict(lambda: defaultdict(lambda: {'loans': 0, 'amount': 0}))
    
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        loan_purpose = str(row.get('loan_purpose', ''))
        
        if year and year in [str(y) for y in years]:
            purpose_category = purpose_categories.get(loan_purpose, 'Other')
            if purpose_category == 'Other':
                continue  # Skip other loan purposes
            
            loan_count = row.get('total_metric', row.get('total_loans', row.get('loan_count', 0)))
            loan_amount = row.get('total_loan_amount', row.get('loan_amount', 0))
            
            try:
                count_val = int(loan_count) if loan_count is not None and loan_count != '' else 0
                amount_val = float(loan_amount) if loan_amount is not None and loan_amount != '' else 0
            except (ValueError, TypeError):
                count_val = 0
                amount_val = 0
            
            yearly_by_purpose[year][purpose_category]['loans'] += count_val
            yearly_by_purpose[year][purpose_category]['amount'] += amount_val
    
    # Build table structure: rows are loan purposes, columns are years
    # Always include all three purposes, even if they have 0 data
    purpose_order = ['Home Purchase', 'Refinance', 'Home Equity']
    table = []
    
    for purpose in purpose_order:
        row_data = {'loan_purpose': purpose}
        
        for year in sorted(years, reverse=True):
            year_str = str(year)
            totals = yearly_by_purpose[year_str].get(purpose, {'loans': 0, 'amount': 0})
            avg = totals['amount'] / totals['loans'] if totals['loans'] > 0 else 0
            
            row_data[year_str] = {
                'total_loans': totals['loans'],
                'total_amount': round(totals['amount'], 2),
                'avg_amount': round(avg, 2)
            }
        
        # Always append the row, even if all values are 0
        table.append(row_data)
    
    return table


def create_demographics_table_by_tract_race(raw_data: List[Dict[str, Any]], years: List[int], tract_race_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create demographic overview table using census tract race data instead of applicant race.
    Aggregates loans by the race composition of the census tract where the loan was made.
    
    Args:
        raw_data: List of loan records with census_tract, geoid5, activity_year, loan_count/loan_amount
        years: List of years to process
        tract_race_data: Dictionary mapping geoid10 to race percentages
    """
    from collections import defaultdict
    
    # Map race groups to their names (for matching with tract_race_data majority_race)
    race_groups = [
        'Hispanic or Latino',
        'Black or African American',
        'White',
        'Asian',
        'Native American or Alaska Native',
        'Native Hawaiian or Other Pacific Islander'
    ]
    
    # Aggregate loans by tract race category
    # We'll classify tracts by their majority race
    demographic_data = defaultdict(lambda: defaultdict(int))
    total_by_year = defaultdict(int)
    
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        if year and year in [str(y) for y in years]:
            # Get census tract and geoid5 to construct geoid10
            census_tract = row.get('census_tract', '')
            geoid5 = row.get('geoid5', '')
            
            # Construct geoid10 (state + county + tract)
            # geoid5 is state (2) + county (3), census_tract is 6 digits
            geoid10 = None
            if geoid5 and census_tract:
                # Normalize census_tract to 6 digits
                tract_str = str(census_tract).strip()
                if '.' in tract_str:
                    parts = tract_str.split('.')
                    tract_str = parts[0] + parts[1][:2].ljust(2, '0')
                tract_str = ''.join(c for c in tract_str if c.isdigit())
                if tract_str:
                    tract_code = tract_str.zfill(6)
                    geoid10 = geoid5 + tract_code
            
            # Get loan count (for loan-level data, each row is 1 loan)
            loan_count = row.get('loan_count', 1)  # Default to 1 if not specified
            if geoid10:
                # Look up race data for this tract
                tract_race = tract_race_data.get(geoid10)
                if tract_race:
                    # Classify tract by majority race
                    majority_race = tract_race.get('majority_race', 'Unknown')
                    if majority_race in race_groups:
                        demographic_data[majority_race][year] += int(loan_count)
                    total_by_year[year] += int(loan_count)
                else:
                    # If no race data, still count in total
                    total_by_year[year] += int(loan_count)
            else:
                # If no geoid10, still count in total
                total_by_year[year] += int(loan_count)
    
    # Create table rows
    table = []
    for group_name in race_groups:
        row_data = {'group': group_name}
        
        for year in sorted(years):
            year_str = str(year)
            count = demographic_data[group_name][year_str]
            total = total_by_year[year_str]
            pct = (count / total * 100) if total > 0 else 0
            
            row_data[year_str] = {
                'count': count,
                'percent': round(pct, 2)
            }
        
        if len(years) >= 2:
            first_count = demographic_data[group_name][str(min(years))]
            last_count = demographic_data[group_name][str(max(years))]
            change = last_count - first_count
            change_pct = ((last_count - first_count) / first_count * 100) if first_count > 0 else 0
            
            row_data['change'] = {
                'absolute': change,
                'percent': round(change_pct, 2)
            }
        
        table.append(row_data)
    
    return table


def create_demographics_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create demographic overview table using applicant race (legacy method)."""
    demographic_groups = {
        'hispanic_metric': 'Hispanic or Latino',
        'black_metric': 'Black or African American',
        'white_metric': 'White',
        'asian_metric': 'Asian',
        'native_american_metric': 'Native American or Alaska Native',
        'hawaiian_pacific_islander_metric': 'Native Hawaiian or Other Pacific Islander'
    }
    
    demographic_data = defaultdict(lambda: defaultdict(int))
    total_by_year = defaultdict(int)
    
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        if year and year in [str(y) for y in years]:
            total = row.get('total_metric', row.get('total_loans', row.get('loan_count', 0)))
            if total:
                total_by_year[year] += int(total)
            
            for group_key, group_name in demographic_groups.items():
                count = row.get(group_key, 0)
                if count:
                    demographic_data[group_key][year] += int(count)
    
    table = []
    for group_key, group_name in demographic_groups.items():
        row_data = {'group': group_name}
        
        for year in sorted(years):
            year_str = str(year)
            count = demographic_data[group_key][year_str]
            total = total_by_year[year_str]
            pct = (count / total * 100) if total > 0 else 0
            
            row_data[year_str] = {
                'count': count,
                'percent': round(pct, 2)
            }
        
        if len(years) >= 2:
            first_count = demographic_data[group_key][str(min(years))]
            last_count = demographic_data[group_key][str(max(years))]
            change = last_count - first_count
            change_pct = ((last_count - first_count) / first_count * 100) if first_count > 0 else 0
            
            row_data['change'] = {
                'absolute': change,
                'percent': round(change_pct, 2)
            }
        
        table.append(row_data)
    
    return table


def create_demographics_by_purpose_table_by_tract_race(raw_data: List[Dict[str, Any]], years: List[int], tract_race_data: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Create demographic overview table by loan purpose using census tract race data.
    """
    result = {}
    
    # Get unique purposes
    purposes = set()
    for row in raw_data:
        purpose = row.get('loan_purpose', '')
        if purpose:
            # Map loan purpose codes to names
            purpose_map = {
                '1': 'Home Purchase',
                '2': 'Home Improvement',
                '31': 'Refinance',
                '32': 'Cash-out Refi',
                '4': 'Other'
            }
            purpose_name = purpose_map.get(str(purpose), 'Other')
            purposes.add(purpose_name)
    
    # Standardize purpose names
    purpose_names = {
        'Home Purchase': 'Home Purchase',
        'Refinance': 'Refinance',  # Includes both 31 and 32
        'Home Equity': 'Home Equity'  # Maps to Home Improvement (2)
    }
    
    # Process all loans first
    all_loans = create_demographics_table_by_tract_race(raw_data, years, tract_race_data)
    result['all'] = all_loans
    
    # Process by purpose
    for purpose_name in ['Home Purchase', 'Refinance', 'Home Equity']:
        # Filter data by purpose
        if purpose_name == 'Home Purchase':
            filtered_data = [r for r in raw_data if str(r.get('loan_purpose', '')) == '1']
        elif purpose_name == 'Refinance':
            filtered_data = [r for r in raw_data if str(r.get('loan_purpose', '')) in ['31', '32']]
        elif purpose_name == 'Home Equity':
            filtered_data = [r for r in raw_data if str(r.get('loan_purpose', '')) == '2']
        else:
            filtered_data = []
        
        if filtered_data:
            result[purpose_name] = create_demographics_table_by_tract_race(filtered_data, years, tract_race_data)
        else:
            result[purpose_name] = []
    
    return result


def create_demographics_by_purpose_table(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Create demographic overview table broken down by loan purpose:
    - All Loans (combined)
    - Home Purchase (loan_purpose = '1')
    - Refinance (loan_purpose = '31' or '32')
    - Home Equity (loan_purpose = '2' or '4')
    """
    demographic_groups = {
        'hispanic_metric': 'Hispanic or Latino',
        'black_metric': 'Black or African American',
        'white_metric': 'White',
        'asian_metric': 'Asian',
        'native_american_metric': 'Native American or Alaska Native',
        'hawaiian_pacific_islander_metric': 'Native Hawaiian or Other Pacific Islander'
    }
    
    purpose_categories = {
        '1': 'Home Purchase',
        '2': 'Home Equity',
        '4': 'Home Equity',
        '31': 'Refinance',
        '32': 'Refinance'
    }
    
    result = {
        'all': create_demographics_table(raw_data, years),
        'Home Purchase': [],
        'Refinance': [],
        'Home Equity': []
    }
    
    # Process each loan purpose category
    for purpose_key, purpose_name in [('1', 'Home Purchase'), ('31', 'Refinance'), ('32', 'Refinance'), ('2', 'Home Equity'), ('4', 'Home Equity')]:
        if purpose_name == 'Refinance' and len(result['Refinance']) > 0:
            continue  # Already processed
        if purpose_name == 'Home Equity' and len(result['Home Equity']) > 0:
            continue  # Already processed
        
        # Filter data by purpose
        if purpose_name == 'Refinance':
            filtered_data = [row for row in raw_data if str(row.get('loan_purpose', '')) in ['31', '32']]
        elif purpose_name == 'Home Equity':
            filtered_data = [row for row in raw_data if str(row.get('loan_purpose', '')) in ['2', '4']]
        else:
            filtered_data = [row for row in raw_data if str(row.get('loan_purpose', '')) == purpose_key]
        
        if filtered_data:
            result[purpose_name] = create_demographics_table(filtered_data, years)
        else:
            # Create empty table structure
            result[purpose_name] = []
            for group_key, group_name in demographic_groups.items():
                row_data = {'group': group_name}
                for year in sorted(years):
                    row_data[str(year)] = {'count': 0, 'percent': 0}
                result[purpose_name].append(row_data)
    
    return result


def create_income_neighborhood_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create income and neighborhood indicators table."""
    indicators = {
        'total': defaultdict(int),
        'low_income_metric': defaultdict(int),
        'moderate_income_metric': defaultdict(int),
        'middle_income_metric': defaultdict(int),
        'upper_income_metric': defaultdict(int),
        'lmict_metric': defaultdict(int),
        'low_income_tract_metric': defaultdict(int),
        'moderate_income_tract_metric': defaultdict(int),
        'middle_income_tract_metric': defaultdict(int),
        'upper_income_tract_metric': defaultdict(int)
    }
    
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        if year and year in [str(y) for y in years]:
            total = row.get('total_metric', row.get('total_loans', row.get('loan_count', 0)))
            indicators['total'][year] += int(total) if total else 0
            
            for key in ['low_income_metric', 'moderate_income_metric', 'middle_income_metric', 'upper_income_metric', 
                       'lmict_metric', 'low_income_tract_metric', 'moderate_income_tract_metric', 
                       'middle_income_tract_metric', 'upper_income_tract_metric']:
                count = row.get(key, 0)
                indicators[key][year] += int(count) if count else 0
    
    # Calculate combined Low & Moderate Income (LMI) for borrowers
    lmi_borrower_metric = defaultdict(int)
    for year in years:
        year_str = str(year)
        lmi_borrower_metric[year_str] = indicators['low_income_metric'][year_str] + indicators['moderate_income_metric'][year_str]
    
    # Calculate combined Low & Moderate Income Tracts (LMI Tracts)
    lmi_tract_metric = defaultdict(int)
    for year in years:
        year_str = str(year)
        lmi_tract_metric[year_str] = indicators['low_income_tract_metric'][year_str] + indicators['moderate_income_tract_metric'][year_str]
    
    # Calculate MMCT (Majority-Minority Census Tract) - tracts with >50% minority
    # We need to get mmct_metric from raw_data
    mmct_metric = defaultdict(int)
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        if year and year in [str(y) for y in years]:
            count = row.get('mmct_metric', 0)
            mmct_metric[year] += int(count) if count else 0
    
    # For MMCT breakdowns, we need to calculate minority tract categories using standard deviation
    # This requires tract-level data which we don't have in the aggregated data
    # For now, we'll create placeholder structure that can be populated from tract-level queries
    # The frontend will need to calculate this from tract data if available
    
    indicator_names = {
        'total': 'Total Loans',
        'low_income_metric': 'Low Income',
        'moderate_income_metric': 'Moderate Income',
        'middle_income_metric': 'Middle Income',
        'upper_income_metric': 'Upper Income',
        'lmi_borrower': 'Low & Moderate Income Borrowers',  # Combined
        'low_income_tract_metric': 'Low Income Tracts',
        'moderate_income_tract_metric': 'Moderate Income Tracts',
        'middle_income_tract_metric': 'Middle Income Tracts',
        'upper_income_tract_metric': 'Upper Income Tracts',
        'lmi_tract': 'Low & Moderate Income Census Tracts',  # Combined
        'mmct': 'Majority-Minority Census Tracts (MMCT)',
        'mmct_low': 'Low Minority Tracts',
        'mmct_moderate': 'Moderate Minority Tracts',
        'mmct_middle': 'Middle Minority Tracts',
        'mmct_upper': 'High Minority Tracts'
    }
    
    table = []
    
    # Total Loans
    total_row = {'indicator': 'Total Loans'}
    for year in sorted(years):
        year_str = str(year)
        count = indicators['total'][year_str]
        total_row[year_str] = {'count': count, 'percent': 100.0}
    table.append(total_row)
    
    # Borrower Income section
    for key in ['low_income_metric', 'moderate_income_metric', 'middle_income_metric', 'upper_income_metric']:
        row_data = {'indicator': indicator_names[key]}
        for year in sorted(years):
            year_str = str(year)
            count = indicators[key][year_str]
            total = indicators['total'][year_str]
            pct = (count / total * 100) if total > 0 else 0
            row_data[year_str] = {'count': count, 'percent': round(pct, 2)}
        table.append(row_data)
    
    # LMI Borrowers (combined) - will be shown as expandable header
    lmi_borrower_row = {'indicator': 'Low & Moderate Income Borrowers'}
    for year in sorted(years):
        year_str = str(year)
        count = lmi_borrower_metric[year_str]
        total = indicators['total'][year_str]
        pct = (count / total * 100) if total > 0 else 0
        lmi_borrower_row[year_str] = {'count': count, 'percent': round(pct, 2)}
    table.append(lmi_borrower_row)
    
    # Neighborhood Income Tracts section
    for key in ['low_income_tract_metric', 'moderate_income_tract_metric', 'middle_income_tract_metric', 'upper_income_tract_metric']:
        row_data = {'indicator': indicator_names[key]}
        for year in sorted(years):
            year_str = str(year)
            count = indicators[key][year_str]
            total = indicators['total'][year_str]
            pct = (count / total * 100) if total > 0 else 0
            row_data[year_str] = {'count': count, 'percent': round(pct, 2)}
        table.append(row_data)
    
    # LMI Tracts (combined) - will be shown as expandable header
    lmi_tract_row = {'indicator': 'Low & Moderate Income Census Tracts'}
    for year in sorted(years):
        year_str = str(year)
        count = lmi_tract_metric[year_str]
        total = indicators['total'][year_str]
        pct = (count / total * 100) if total > 0 else 0
        lmi_tract_row[year_str] = {'count': count, 'percent': round(pct, 2)}
    table.append(lmi_tract_row)
    
    # MMCT section
    mmct_row = {'indicator': 'Majority-Minority Census Tracts (MMCT)'}
    for year in sorted(years):
        year_str = str(year)
        count = mmct_metric[year_str]
        total = indicators['total'][year_str]
        pct = (count / total * 100) if total > 0 else 0
        mmct_row[year_str] = {'count': count, 'percent': round(pct, 2)}
    table.append(mmct_row)
    
    # MMCT breakdowns (low, moderate, middle, upper) - calculate using standard deviation method
    # Note: This requires a separate query to get tract-level data
    # For now, create empty structure - will be populated when MMCT breakdown query is added
    for key in ['mmct_low', 'mmct_moderate', 'mmct_middle', 'mmct_upper']:
        row_data = {'indicator': indicator_names[key]}
        for year in sorted(years):
            row_data[str(year)] = {'count': 0, 'percent': 0}
        table.append(row_data)
    
    return table


def create_income_neighborhood_by_purpose_table(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Create income and neighborhood indicators table broken down by loan purpose.
    """
    result = {
        'all': create_income_neighborhood_table(raw_data, years),
        'Home Purchase': [],
        'Refinance': [],
        'Home Equity': []
    }
    
    # Process each loan purpose category
    for purpose_key, purpose_name in [('1', 'Home Purchase'), ('31', 'Refinance'), ('32', 'Refinance'), ('2', 'Home Equity'), ('4', 'Home Equity')]:
        if purpose_name == 'Refinance' and len(result['Refinance']) > 0:
            continue  # Already processed
        if purpose_name == 'Home Equity' and len(result['Home Equity']) > 0:
            continue  # Already processed
        
        # Filter data by purpose
        if purpose_name == 'Refinance':
            filtered_data = [row for row in raw_data if str(row.get('loan_purpose', '')) in ['31', '32']]
        elif purpose_name == 'Home Equity':
            filtered_data = [row for row in raw_data if str(row.get('loan_purpose', '')) in ['2', '4']]
        else:
            filtered_data = [row for row in raw_data if str(row.get('loan_purpose', '')) == purpose_key]
        
        if filtered_data:
            result[purpose_name] = create_income_neighborhood_table(filtered_data, years)
        else:
            # Create empty table structure
            result[purpose_name] = []
    
    return result


def create_top_lenders_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """
    Create top lenders table.
    
    Aggregates loans by LEI for the latest year, summing across all loan purposes.
    If raw_data contains multiple rows per LEI (different loan purposes), they are summed together.
    """
    latest_year = max(years)
    latest_year_str = str(latest_year)
    
    lender_data = defaultdict(lambda: {
        'name': '',
        'type': '',
        'total_loans': 0,
        'total_amount': 0,
        'demographics': defaultdict(int),
        'lmib_count': 0,  # Low & Moderate Income Borrowers
        'lmict_count': 0,  # Low & Moderate Income Census Tracts
        'mmct_count': 0   # Majority Minority Census Tracts
    })
    
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        if year == latest_year_str:
            lei = row.get('lei', '')
            lender_name = row.get('lender_name', f'Lender {lei[:8] if lei else "Unknown"}')
            lender_type = row.get('lender_type', '')
            
            loan_count = row.get('total_metric', row.get('total_loans', row.get('loan_count', 0)))
            loan_amount = row.get('total_loan_amount', row.get('loan_amount', 0))
            
            lender_data[lei]['name'] = lender_name
            if lender_type:
                lender_data[lei]['type'] = lender_type  # Store the actual type from lenders18 table
            # Sum across all loan purposes for this LEI
            lender_data[lei]['total_loans'] += int(loan_count) if loan_count else 0
            lender_data[lei]['total_amount'] += float(loan_amount) if loan_amount else 0
            
            # Add demographic counts
            for group in ['hispanic_metric', 'black_metric', 'white_metric', 'asian_metric', 'native_american_metric']:
                count = row.get(group, 0)
                lender_data[lei]['demographics'][group.replace('_metric', '')] += int(count) if count else 0
            
            # Add performance indicator counts
            lmib_count = row.get('lmib_metric', 0)
            lmict_count = row.get('lmict_metric', 0)
            mmct_count = row.get('mmct_metric', 0)
            lender_data[lei]['lmib_count'] += int(lmib_count) if lmib_count else 0
            lender_data[lei]['lmict_count'] += int(lmict_count) if lmict_count else 0
            lender_data[lei]['mmct_count'] += int(mmct_count) if mmct_count else 0
    
    sorted_lenders = sorted(
        lender_data.items(),
        key=lambda x: x[1]['total_loans'],
        reverse=True
    )  # Return ALL lenders, not just top 10
    
    # Helper function to format lender type
    def format_lender_type(type_name: str) -> str:
        """Format lender type name for display - shorten long names."""
        if not type_name:
            return 'Mortgage Lender'
        # Map long names to shorter ones
        type_mapping = {
            'Mortgage Bankers': 'Mortgage Lender',
            'Banks': 'Bank',
            'Credit Unions': 'Credit Union',
            'Banks or Affiliates': 'Bank',
            'Bank': 'Bank',
            'Credit Union': 'Credit Union',
            'Mortgage Lender': 'Mortgage Lender'
        }
        # Check exact match first
        if type_name in type_mapping:
            return type_mapping[type_name]
        # Check if it contains "Bank" or "Credit Union"
        if 'Bank' in type_name or 'bank' in type_name:
            return 'Bank'
        if 'Credit Union' in type_name or 'credit union' in type_name:
            return 'Credit Union'
        # Default to first word or Mortgage Lender
        return type_name.split()[0] if type_name else 'Mortgage Lender'
    
    table = []
    for lei, data in sorted_lenders:
        row_data = {
            'lei': lei,
            'name': data['name'],
            'type': format_lender_type(data.get('type', 'Mortgage Lender')),
            'total_loans': data['total_loans'],
            'total_amount': round(data['total_amount'], 2),
            'demographics': {},
            'performance_indicators': {}
        }
        
        for group in ['hispanic', 'black', 'white', 'asian', 'native_american']:
            count = data['demographics'][group]
            pct = (count / data['total_loans'] * 100) if data['total_loans'] > 0 else 0
            row_data['demographics'][group] = {
                'count': count,
                'percent': round(pct, 2)
            }
        
        # Calculate performance indicator percentages
        total_loans = data['total_loans']
        row_data['performance_indicators'] = {
            'lmib': {
                'count': data['lmib_count'],
                'percent': round((data['lmib_count'] / total_loans * 100) if total_loans > 0 else 0, 2)
            },
            'lmict': {
                'count': data['lmict_count'],
                'percent': round((data['lmict_count'] / total_loans * 100) if total_loans > 0 else 0, 2)
            },
            'mmct': {
                'count': data['mmct_count'],
                'percent': round((data['mmct_count'] / total_loans * 100) if total_loans > 0 else 0, 2)
            }
        }
        
        table.append(row_data)
    
    return table


def create_top_lenders_by_purpose(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, List[Dict[str, Any]]]:
    """Create top lenders table broken down by loan purpose."""
    purpose_categories = {
        '1': 'Home Purchase',
        '2': 'Home Equity',  # Home Improvement
        '4': 'Home Equity',  # Other
        '31': 'Refinance',   # Refinance
        '32': 'Refinance'    # Cash-out refinance
    }
    
    result = {
        'all': create_top_lenders_table(raw_data, years),
        'Home Purchase': [],
        'Refinance': [],
        'Home Equity': []
    }
    
    # Filter data by purpose and create tables (use all years, not just latest)
    for purpose_key, purpose_name in [('1', 'Home Purchase'), ('2', 'Home Equity'), ('4', 'Home Equity'), ('31', 'Refinance'), ('32', 'Refinance')]:
        if purpose_name == 'Refinance' and 'Refinance' in result and len(result['Refinance']) > 0:
            continue  # Already processed
        if purpose_name == 'Home Equity' and 'Home Equity' in result and len(result['Home Equity']) > 0:
            continue  # Already processed
        
        # Use only latest year for consistency with create_top_lenders_table
        latest_year = max(years)
        latest_year_str = str(latest_year)
        
        if purpose_name == 'Refinance':
            # Combine 31 and 32 for Refinance (latest year only)
            filtered_data = [row for row in raw_data 
                            if str(row.get('loan_purpose', '')) in ['31', '32']
                            and str(row.get('activity_year', row.get('year', ''))) == latest_year_str]
        elif purpose_name == 'Home Equity':
            # Combine 2 and 4 for Home Equity (latest year only)
            filtered_data = [row for row in raw_data 
                            if str(row.get('loan_purpose', '')) in ['2', '4']
                            and str(row.get('activity_year', row.get('year', ''))) == latest_year_str]
        else:
            filtered_data = [row for row in raw_data 
                            if str(row.get('loan_purpose', '')) == purpose_key 
                            and str(row.get('activity_year', row.get('year', ''))) == latest_year_str]
        
        if filtered_data:
            
            # Create lender aggregation for this purpose
            lender_data = defaultdict(lambda: {
                'name': '',
                'type': '',
                'total_loans': 0,
                'total_amount': 0,
                'demographics': defaultdict(int),
                'lmib_count': 0,  # Low & Moderate Income Borrowers
                'lmict_count': 0,  # Low & Moderate Income Census Tracts
                'mmct_count': 0   # Majority Minority Census Tracts
            })
            
            for row in filtered_data:
                lei = row.get('lei', '')
                lender_name = row.get('lender_name', f'Lender {lei[:8] if lei else "Unknown"}')
                lender_type = row.get('lender_type', '')
                
                loan_count = row.get('total_metric', row.get('total_loans', row.get('loan_count', 0)))
                loan_amount = row.get('total_loan_amount', row.get('loan_amount', 0))
                
                lender_data[lei]['name'] = lender_name
                if lender_type:
                    lender_data[lei]['type'] = lender_type
                lender_data[lei]['total_loans'] += int(loan_count) if loan_count else 0
                lender_data[lei]['total_amount'] += float(loan_amount) if loan_amount else 0
                
                for group in ['hispanic_metric', 'black_metric', 'white_metric', 'asian_metric', 'native_american_metric', 'hawaiian_pacific_islander_metric']:
                    count = row.get(group, 0)
                    lender_data[lei]['demographics'][group.replace('_metric', '')] += int(count) if count else 0
                
                # Add performance indicator counts
                lmib_count = row.get('lmib_metric', 0)
                lmict_count = row.get('lmict_metric', 0)
                mmct_count = row.get('mmct_metric', 0)
                lender_data[lei]['lmib_count'] += int(lmib_count) if lmib_count else 0
                lender_data[lei]['lmict_count'] += int(lmict_count) if lmict_count else 0
                lender_data[lei]['mmct_count'] += int(mmct_count) if mmct_count else 0
            
            sorted_lenders = sorted(
                lender_data.items(),
                key=lambda x: x[1]['total_loans'],
                reverse=True
            )  # Return ALL lenders, not just top 10
            
            # Helper function to format lender type (same as in create_top_lenders_table)
            def format_lender_type(type_name: str) -> str:
                """Format lender type name for display - shorten long names."""
                if not type_name:
                    return 'Mortgage Lender'
                type_mapping = {
                    'Mortgage Bankers': 'Mortgage Lender',
                    'Banks': 'Bank',
                    'Credit Unions': 'Credit Union',
                    'Banks or Affiliates': 'Bank',
                    'Bank': 'Bank',
                    'Credit Union': 'Credit Union',
                    'Mortgage Lender': 'Mortgage Lender'
                }
                if type_name in type_mapping:
                    return type_mapping[type_name]
                if 'Bank' in type_name or 'bank' in type_name:
                    return 'Bank'
                if 'Credit Union' in type_name or 'credit union' in type_name:
                    return 'Credit Union'
                return type_name.split()[0] if type_name else 'Mortgage Lender'
            
            table = []
            for lei, data in sorted_lenders:
                row_data = {
                    'lei': lei,
                    'name': data['name'],
                    'type': format_lender_type(data.get('type', 'Mortgage Lender')),
                    'total_loans': data['total_loans'],
                    'total_amount': round(data['total_amount'], 2),
                    'demographics': {},
                    'performance_indicators': {}
                }
                
                for group in ['hispanic', 'black', 'white', 'asian', 'native_american', 'hawaiian_pacific_islander']:
                    count = data['demographics'][group]
                    pct = (count / data['total_loans'] * 100) if data['total_loans'] > 0 else 0
                    row_data['demographics'][group] = {
                        'count': count,
                        'percent': round(pct, 2)
                    }
                
                # Calculate performance indicator percentages
                total_loans = data['total_loans']
                row_data['performance_indicators'] = {
                    'lmib': {
                        'count': data['lmib_count'],
                        'percent': round((data['lmib_count'] / total_loans * 100) if total_loans > 0 else 0, 2)
                    },
                    'lmict': {
                        'count': data['lmict_count'],
                        'percent': round((data['lmict_count'] / total_loans * 100) if total_loans > 0 else 0, 2)
                    },
                    'mmct': {
                        'count': data['mmct_count'],
                        'percent': round((data['mmct_count'] / total_loans * 100) if total_loans > 0 else 0, 2)
                    }
                }
                
                table.append(row_data)
            
            result[purpose_name] = table
    
    return result


def calculate_hhi(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, Any]:
    """
    Calculate Herfindahl-Hirschman Index (HHI) for market concentration (latest year).
    
    IMPORTANT: This calculation uses ALL lenders in the geography, not just top 10.
    The HHI is calculated by summing the squared market shares of ALL lenders.
    The [:5] limit below is ONLY for the top_lenders display list, not for the HHI calculation.
    """
    latest_year = max(years)
    latest_year_str = str(latest_year)
    
    # Aggregate amounts by LEI for ALL lenders in raw_data
    lender_amounts = defaultdict(float)
    total_amount = 0
    
    # Iterate through ALL rows in raw_data (no limit)
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        if year == latest_year_str:
            lei = row.get('lei', '')
            loan_amount = row.get('total_loan_amount', row.get('loan_amount', 0))
            amount = float(loan_amount) if loan_amount else 0
            
            lender_amounts[lei] += amount
            total_amount += amount
    
    if total_amount == 0:
        return {
            'hhi': None,
            'concentration_level': 'Not Available',
            'year': latest_year,
            'total_amount': 0,
            'top_lenders': []
        }
    
    # Calculate HHI using ALL lenders (not limited to top 10)
    # HHI = sum of (market_share^2) for all lenders * 10000
    hhi = 0
    for lei, amount in lender_amounts.items():  # Iterates through ALL lenders
        market_share = amount / total_amount
        hhi += market_share * market_share
    
    hhi = hhi * 10000
    
    # Determine concentration level per 2023 DOJ/FTC Merger Guidelines
    # Thresholds: <1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), >2,500 (Highly Concentrated)
    # Source: U.S. Department of Justice and Federal Trade Commission, 2023 Merger Guidelines
    if hhi < 1500:
        level = 'Unconcentrated'
    elif hhi < 2500:
        level = 'Moderately Concentrated'
    else:
        level = 'Highly Concentrated'
    
    # Get top 5 lenders for display purposes only (does NOT affect HHI calculation above)
    # HHI was already calculated using ALL lenders above
    sorted_lenders = sorted(
        lender_amounts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    top_lenders = []
    for lei, amount in sorted_lenders:
        market_share = (amount / total_amount * 100) if total_amount > 0 else 0
        top_lenders.append({
            'lei': lei,
            'amount': round(amount, 2),
            'market_share': round(market_share, 2)
        })
    
    return {
        'hhi': round(hhi, 2),
        'concentration_level': level,
        'year': latest_year,
        'total_amount': round(total_amount, 2),
        'top_lenders': top_lenders
    }


def get_top_lenders_by_year(raw_data: List[Dict[str, Any]], years: List[int], top_n: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get top N lenders by year with their loan counts and amounts.
    
    Returns:
        Dictionary mapping year (as string) to list of lender dictionaries with:
        - lender_name: Lender name
        - lei: LEI code
        - lender_type: Lender type
        - total_loans: Total loans for this year
        - total_amount: Total loan amount for this year
    """
    from collections import defaultdict
    
    yearly_lender_data = defaultdict(lambda: defaultdict(lambda: {
        'lender_name': '',
        'lei': '',
        'lender_type': '',
        'total_loans': 0,
        'total_amount': 0
    }))
    
    # Process raw data by year
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        if year and year in [str(y) for y in years]:
            lei = row.get('lei', '')
            lender_name = row.get('lender_name', f'Lender {lei[:8] if lei else "Unknown"}')
            lender_type = row.get('lender_type', '')
            
            loan_count = row.get('total_metric', row.get('total_loans', row.get('loan_count', 0)))
            loan_amount = row.get('total_loan_amount', row.get('loan_amount', 0))
            
            yearly_lender_data[year][lei]['lender_name'] = lender_name
            yearly_lender_data[year][lei]['lei'] = lei
            if lender_type:
                yearly_lender_data[year][lei]['lender_type'] = lender_type
            yearly_lender_data[year][lei]['total_loans'] += int(loan_count) if loan_count else 0
            yearly_lender_data[year][lei]['total_amount'] += float(loan_amount) if loan_amount else 0
    
    # Sort and get top N for each year
    result = {}
    for year in sorted(years):
        year_str = str(year)
        lenders = list(yearly_lender_data[year_str].values())
        lenders.sort(key=lambda x: x['total_loans'], reverse=True)
        result[year_str] = lenders[:top_n]
    
    return result


def calculate_hhi_by_year(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """
    Calculate HHI for each year to show trends over time.
    
    IMPORTANT: This calculation uses ALL lenders in the geography for each year, not just top 10.
    The HHI is calculated by summing the squared market shares of ALL lenders.
    The [:5] limit below is ONLY for the top_lenders display list, not for the HHI calculation.
    
    Returns entries for all years, even if raw_data is empty (HHI will be None).
    """
    # Always return entries for all years, even if no data (so frontend can display the dataset)
    hhi_by_year = []
    sorted_years = sorted(years)
    
    if not raw_data:
        # Return entries for all years with null HHI
        for year in sorted_years:
            hhi_by_year.append({
                'year': str(year),
                'hhi': None,
                'concentration_level': 'Not Available',
                'total_amount': 0,
                'top_lenders': []
            })
        return hhi_by_year
    
    # Group data by year - includes ALL lenders (no limit)
    yearly_data = defaultdict(lambda: defaultdict(float))
    yearly_totals = defaultdict(float)
    
    # Iterate through ALL rows in raw_data (no limit)
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        if year and year in [str(y) for y in years]:
            lei = row.get('lei', '')
            loan_amount = row.get('total_loan_amount', row.get('loan_amount', 0))
            amount = float(loan_amount) if loan_amount else 0
            
            yearly_data[year][lei] += amount
            yearly_totals[year] += amount
    
    # Calculate HHI for each year (hhi_by_year already initialized above)
    for year in sorted_years:
        year_str = str(year)
        lender_amounts = yearly_data[year_str]  # Contains ALL lenders for this year
        total_amount = yearly_totals[year_str]
        
        if total_amount == 0:
            hhi_by_year.append({
                'year': year_str,
                'hhi': None,
                'concentration_level': 'Not Available',
                'total_amount': 0,
                'top_lenders': []
            })
            continue
        
        # Calculate HHI using ALL lenders (not limited to top 10)
        # HHI = sum of (market_share^2) for all lenders * 10000
        hhi = 0
        for lei, amount in lender_amounts.items():  # Iterates through ALL lenders
            market_share = amount / total_amount
            hhi += market_share * market_share
        
        hhi = hhi * 10000
        
        # Determine concentration level per 2023 DOJ/FTC Merger Guidelines
        # Thresholds: <1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), >2,500 (Highly Concentrated)
        if hhi < 1500:
            level = 'Unconcentrated'
        elif hhi < 2500:
            level = 'Moderately Concentrated'
        else:
            level = 'Highly Concentrated'
        
        # Get top 5 lenders for display purposes only (does NOT affect HHI calculation above)
        # HHI was already calculated using ALL lenders above
        sorted_lenders = sorted(
            lender_amounts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        top_lenders = []
        for lei, amount in sorted_lenders:
            market_share = (amount / total_amount * 100) if total_amount > 0 else 0
            top_lenders.append({
                'lei': lei,
                'amount': round(amount, 2),
                'market_share': round(market_share, 2)
            })
        
        hhi_by_year.append({
            'year': year_str,
            'hhi': round(hhi, 2),
            'concentration_level': level,
            'total_amount': round(total_amount, 2),
            'top_lenders': top_lenders
        })
    
    return hhi_by_year


def calculate_hhi_by_year_by_purpose(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, List[Dict[str, Any]]]:
    """Calculate HHI by year broken down by loan purpose."""
    purpose_categories = {
        '1': 'Home Purchase',
        '2': 'Home Equity',  # Home Improvement
        '4': 'Home Equity',  # Other
        '31': 'Refinance',   # Refinance
        '32': 'Refinance'    # Cash-out refinance
    }
    
    result = {
        'all': calculate_hhi_by_year(raw_data, years),
        'Home Purchase': [],
        'Refinance': [],
        'Home Equity': []
    }
    
    # Filter by purpose and calculate HHI
    # Process Refinance first (combines '31' and '32')
    # Always call calculate_hhi_by_year even if no data (it will return entries with null HHI)
    refinance_data = [row for row in raw_data if str(row.get('loan_purpose', '')) in ['31', '32']]
    result['Refinance'] = calculate_hhi_by_year(refinance_data, years)
    
    # Process Home Equity (combines '2' and '4')
    # Always call calculate_hhi_by_year even if no data (it will return entries with null HHI)
    home_equity_data = [row for row in raw_data if str(row.get('loan_purpose', '')) in ['2', '4']]
    result['Home Equity'] = calculate_hhi_by_year(home_equity_data, years)
    
    # Process Home Purchase ('1')
    # Always call calculate_hhi_by_year even if no data (it will return entries with null HHI)
    home_purchase_data = [row for row in raw_data if str(row.get('loan_purpose', '')) == '1']
    result['Home Purchase'] = calculate_hhi_by_year(home_purchase_data, years)
    
    return result


def create_trends_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create year-over-year trends table."""
    if len(years) < 2:
        return []
    
    # Aggregate totals by year
    yearly_totals = defaultdict(lambda: {'loans': 0, 'amount': 0})
    
    for row in raw_data:
        year = str(row.get('activity_year', row.get('year', '')))
        if year and year in [str(y) for y in years]:
            # The query returns 'total_metric' for count
            loan_count = row.get('total_metric', row.get('total_loans', row.get('loan_count', 0)))
            loan_amount = row.get('total_loan_amount', row.get('loan_amount', 0))
            
            yearly_totals[year]['loans'] += int(loan_count) if loan_count else 0
            yearly_totals[year]['amount'] += float(loan_amount) if loan_amount else 0
    
    # Calculate year-over-year changes
    table = []
    sorted_years = sorted(years)
    
    for i in range(1, len(sorted_years)):
        prev_year = str(sorted_years[i-1])
        curr_year = str(sorted_years[i])
        
        prev_loans = yearly_totals[prev_year]['loans']
        curr_loans = yearly_totals[curr_year]['loans']
        prev_amount = yearly_totals[prev_year]['amount']
        curr_amount = yearly_totals[curr_year]['amount']
        
        loan_change = curr_loans - prev_loans
        loan_change_pct = ((curr_loans - prev_loans) / prev_loans * 100) if prev_loans > 0 else 0
        amount_change = curr_amount - prev_amount
        amount_change_pct = ((curr_amount - prev_amount) / prev_amount * 100) if prev_amount > 0 else 0
        
        table.append({
            'period': f'{prev_year}→{curr_year}',
            'loans': {
                'change': loan_change,
                'percent': round(loan_change_pct, 2)
            },
            'amount': {
                'change': round(amount_change, 2),
                'percent': round(amount_change_pct, 2)
            }
        })
    
    return table


def create_trends_by_purpose(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, List[Dict[str, Any]]]:
    """Create trends table broken down by loan purpose."""
    result = {
        'all': create_trends_table(raw_data, years),
        'Home Purchase': [],
        'Refinance': [],
        'Home Equity': []
    }
    
    # Filter by purpose and create trends
    for purpose_key, purpose_name in [('1', 'Home Purchase'), ('2', 'Home Equity'), ('4', 'Home Equity'), ('31', 'Refinance'), ('32', 'Refinance')]:
        if purpose_name == 'Refinance' and len(result['Refinance']) > 0:
            continue  # Already processed
        if purpose_name == 'Home Equity' and len(result['Home Equity']) > 0:
            continue  # Already processed
        
        if purpose_name == 'Refinance':
            filtered_data = [row for row in raw_data if str(row.get('loan_purpose', '')) in ['31', '32']]
        elif purpose_name == 'Home Equity':
            filtered_data = [row for row in raw_data if str(row.get('loan_purpose', '')) in ['2', '4']]
        else:
            filtered_data = [row for row in raw_data if str(row.get('loan_purpose', '')) == purpose_key]
        
        if filtered_data:
            result[purpose_name] = create_trends_table(filtered_data, years)
    
    return result


# Small Business Processing Functions

def create_sb_summary_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create summary table for Small Business data."""
    yearly_totals = defaultdict(lambda: {'total_loans': 0, 'total_amount': 0, 'avg_amount': 0})
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            loan_count = row.get('total_metric', row.get('sb_loans_count', 0))
            loan_amount = row.get('sb_loans_amount', row.get('total_loan_amount', 0))
            
            yearly_totals[year]['total_loans'] += int(loan_count) if loan_count else 0
            yearly_totals[year]['total_amount'] += float(loan_amount) if loan_amount else 0
    
    table = []
    for year in sorted(years, reverse=True):
        year_str = str(year)
        totals = yearly_totals[year_str]
        avg = totals['total_amount'] / totals['total_loans'] if totals['total_loans'] > 0 else 0
        
        table.append({
            'year': year_str,
            'total_loans': totals['total_loans'],
            'total_amount': round(totals['total_amount'], 2),
            'avg_amount': round(avg, 2)
        })
    
    return table


def create_sb_demographics_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create demographic overview table for Small Business (by income groups)."""
    # Small Business uses income groups instead of race/ethnicity
    income_groups = {
        'low_income': 'Low Income',
        'moderate_income': 'Moderate Income',
        'middle_income': 'Middle Income',
        'upper_income': 'Upper Income'
    }
    
    demographic_data = defaultdict(lambda: defaultdict(int))
    total_by_year = defaultdict(int)
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            total = row.get('total_metric', row.get('sb_loans_count', 0))
            if total:
                total_by_year[year] += int(total)
            
            for group_key, group_name in income_groups.items():
                count = row.get(f'{group_key}_metric', 0)
                if count:
                    demographic_data[group_key][year] += int(count)
    
    table = []
    for group_key, group_name in income_groups.items():
        row_data = {'group': group_name}
        
        for year in sorted(years):
            year_str = str(year)
            count = demographic_data[group_key][year_str]
            total = total_by_year[year_str]
            pct = (count / total * 100) if total > 0 else 0
            
            row_data[year_str] = {
                'count': count,
                'percent': round(pct, 2)
            }
        
        if len(years) >= 2:
            first_count = demographic_data[group_key][str(min(years))]
            last_count = demographic_data[group_key][str(max(years))]
            change = last_count - first_count
            change_pct = ((last_count - first_count) / first_count * 100) if first_count > 0 else 0
            
            row_data['change'] = {
                'absolute': change,
                'percent': round(change_pct, 2)
            }
        
        table.append(row_data)
    
    return table


def create_sb_income_neighborhood_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create income and neighborhood indicators table for Small Business."""
    indicators = {
        'total': defaultdict(int),
        'total_amount': defaultdict(float),
        'lmict': defaultdict(int),
        'lmict_amount': defaultdict(float),
        'low_income_tract': defaultdict(int),
        'low_income_tract_amount': defaultdict(float),
        'moderate_income_tract': defaultdict(int),
        'moderate_income_tract_amount': defaultdict(float),
        'middle_income_tract': defaultdict(int),
        'middle_income_tract_amount': defaultdict(float),
        'upper_income_tract': defaultdict(int),
        'upper_income_tract_amount': defaultdict(float),
        'under_100k': defaultdict(int),
        'under_100k_amount': defaultdict(float),
        '100k_250k': defaultdict(int),
        '100k_250k_amount': defaultdict(float),
        '250k_1m': defaultdict(int),
        '250k_1m_amount': defaultdict(float),
        # Revenue category breakdowns for loan sizes
        'under_100k_rev_under_1m': defaultdict(int),
        'under_100k_rev_under_1m_amount': defaultdict(float),
        '100k_250k_rev_under_1m': defaultdict(int),
        '100k_250k_rev_under_1m_amount': defaultdict(float),
        '250k_1m_rev_under_1m': defaultdict(int),
        '250k_1m_rev_under_1m_amount': defaultdict(float),
        'under_100k_rev_over_1m': defaultdict(int),
        'under_100k_rev_over_1m_amount': defaultdict(float),
        '100k_250k_rev_over_1m': defaultdict(int),
        '100k_250k_rev_over_1m_amount': defaultdict(float),
        '250k_1m_rev_over_1m': defaultdict(int),
        '250k_1m_rev_over_1m_amount': defaultdict(float)
    }
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            total = row.get('total_metric', row.get('sb_loans_count', 0))
            total_amount = row.get('sb_loans_amount', 0)
            lmict = row.get('lmict_metric', row.get('lmict_loans_count', 0))
            lmict_amt = row.get('lmict_metric', 0) if 'amount' in str(row.get('lmict_metric', '')) else 0
            low_income_tract = row.get('low_income_metric', 0)
            low_income_tract_amt = row.get('low_income_metric', 0) if isinstance(row.get('low_income_metric'), (int, float)) and row.get('total_metric', 0) > 1000000 else 0
            moderate_income_tract = row.get('moderate_income_metric', 0)
            moderate_income_tract_amt = row.get('moderate_income_metric', 0) if isinstance(row.get('moderate_income_metric'), (int, float)) and row.get('total_metric', 0) > 1000000 else 0
            middle_income_tract = row.get('middle_income_metric', 0)
            middle_income_tract_amt = row.get('middle_income_metric', 0) if isinstance(row.get('middle_income_metric'), (int, float)) and row.get('total_metric', 0) > 1000000 else 0
            upper_income_tract = row.get('upper_income_metric', 0)
            upper_income_tract_amt = row.get('upper_income_metric', 0) if isinstance(row.get('upper_income_metric'), (int, float)) and row.get('total_metric', 0) > 1000000 else 0
            under_100k = row.get('loans_under_100k_metric', row.get('num_under_100k', 0))
            under_100k_amt = row.get('amt_under_100k', 0)
            loans_100k_250k = row.get('loans_100k_250k_metric', row.get('num_100k_250k', 0))
            loans_100k_250k_amt = row.get('amt_100k_250k', 0)
            loans_250k_1m = row.get('loans_250k_1m_metric', row.get('num_250k_1m', 0))
            loans_250k_1m_amt = row.get('amt_250k_1m', 0)
            
            indicators['total'][year] += int(total) if total else 0
            indicators['total_amount'][year] += float(total_amount) if total_amount else 0
            indicators['lmict'][year] += int(lmict) if lmict else 0
            indicators['lmict_amount'][year] += float(row.get('lmict_amount', 0)) if row.get('lmict_amount') else 0
            indicators['low_income_tract'][year] += int(low_income_tract) if low_income_tract else 0
            indicators['low_income_tract_amount'][year] += float(row.get('low_income_tract_amount', 0)) if row.get('low_income_tract_amount') else 0
            indicators['moderate_income_tract'][year] += int(moderate_income_tract) if moderate_income_tract else 0
            indicators['moderate_income_tract_amount'][year] += float(row.get('moderate_income_tract_amount', 0)) if row.get('moderate_income_tract_amount') else 0
            indicators['middle_income_tract'][year] += int(middle_income_tract) if middle_income_tract else 0
            indicators['middle_income_tract_amount'][year] += float(row.get('middle_income_tract_amount', 0)) if row.get('middle_income_tract_amount') else 0
            indicators['upper_income_tract'][year] += int(upper_income_tract) if upper_income_tract else 0
            indicators['upper_income_tract_amount'][year] += float(row.get('upper_income_tract_amount', 0)) if row.get('upper_income_tract_amount') else 0
            indicators['under_100k'][year] += int(under_100k) if under_100k else 0
            indicators['under_100k_amount'][year] += float(under_100k_amt) if under_100k_amt else 0
            indicators['100k_250k'][year] += int(loans_100k_250k) if loans_100k_250k else 0
            indicators['100k_250k_amount'][year] += float(loans_100k_250k_amt) if loans_100k_250k_amt else 0
            indicators['250k_1m'][year] += int(loans_250k_1m) if loans_250k_1m else 0
            indicators['250k_1m_amount'][year] += float(loans_250k_1m_amt) if loans_250k_1m_amt else 0
            
            # Add business revenue category data
            amount_rev_under_1m = row.get('amtsbrev_under_1m', 0)
            if amount_rev_under_1m is None:
                amount_rev_under_1m = 0
            # Calculate revenue over $1M as total amount - under $1M
            total_amt = row.get('sb_loans_amount', 0)
            amount_rev_over_1m = float(total_amt) - float(amount_rev_under_1m) if total_amt else 0
            
            # Store revenue amounts (we'll add these as new indicators)
            if 'rev_under_1m_amount' not in indicators:
                indicators['rev_under_1m_amount'] = defaultdict(float)
            if 'rev_over_1m_amount' not in indicators:
                indicators['rev_over_1m_amount'] = defaultdict(float)
            indicators['rev_under_1m_amount'][year] += float(amount_rev_under_1m) if amount_rev_under_1m else 0
            indicators['rev_over_1m_amount'][year] += float(amount_rev_over_1m) if amount_rev_over_1m > 0 else 0
    
    indicator_names = {
        'total': 'Total Loans',
        'lmict': 'Low-to-Moderate Income Census Tract (LMICT)',
        'low_income_tract': 'Low Income Tracts',
        'moderate_income_tract': 'Moderate Income Tracts',
        'middle_income_tract': 'Middle Income Tracts',
        'upper_income_tract': 'Upper Income Tracts',
        'under_100k': 'Loans Under $100K',
        '100k_250k': 'Loans $100K-$250K',
        '250k_1m': 'Loans $250K-$1M',
        'mmct': 'Majority-Minority Census Tracts (MMCT)',
        'mmct_low': 'Low Minority Tracts',
        'mmct_moderate': 'Moderate Minority Tracts',
        'mmct_middle': 'Middle Minority Tracts',
        'mmct_upper': 'High Minority Tracts',
        'rev_under_1m_amount': 'Loans to Businesses Under $1M Revenue',
        'rev_over_1m_amount': 'Loans to Businesses Over $1M Revenue'
    }
    
    # Calculate combined Low & Moderate Income Tracts (LMI Tracts)
    lmi_tract_metric = defaultdict(int)
    lmi_tract_metric_amount = defaultdict(float)
    for year in years:
        year_str = str(year)
        lmi_tract_metric[year_str] = indicators['low_income_tract'][year_str] + indicators['moderate_income_tract'][year_str]
        lmi_tract_metric_amount[year_str] = indicators['low_income_tract_amount'][year_str] + indicators['moderate_income_tract_amount'][year_str]
    
    table = []
    for key, name in indicator_names.items():
        # Skip MMCT breakdown rows - they will be populated by app.py from mmct_breakdowns
        if key in ['mmct_low', 'mmct_moderate', 'mmct_middle', 'mmct_upper']:
            row_data = {'indicator': name}
            for year in sorted(years):
                row_data[str(year)] = {'count': 0, 'percent': 0}
            table.append(row_data)
            continue
        
        # Skip LMICT row - it will be replaced by the combined "Low & Moderate Income Census Tracts" row
        if key == 'lmict':
            continue
        
        # Skip individual income tract rows - they'll be shown as expandable rows under LMI Tracts
        if key in ['low_income_tract', 'moderate_income_tract', 'middle_income_tract', 'upper_income_tract']:
            row_data = {'indicator': name}
            for year in sorted(years):
                year_str = str(year)
                count = indicators[key][year_str]
                total = indicators['total'][year_str]
                pct = (count / total * 100) if total > 0 else 0
                amount = indicators.get(f'{key}_amount', {}).get(year_str, 0)
                total_amount = indicators.get('total_amount', {}).get(year_str, 0)
                amount_pct = (amount / total_amount * 100) if total_amount > 0 else 0
                row_data[year_str] = {
                    'count': count,
                    'percent': round(pct, 2),
                    'amount': round(amount, 2),
                    'amount_percent': round(amount_pct, 2)
                }
            table.append(row_data)
            continue
        
        row_data = {'indicator': name}
        
        for year in sorted(years):
            year_str = str(year)
            if key == 'mmct':
                # MMCT row - will be calculated from mmct breakdowns in app.py
                # Initialize with zero values, will be populated in app.py
                row_data[year_str] = {'count': 0, 'percent': 0, 'amount': 0, 'amount_percent': 0}
            else:
                count = indicators[key][year_str]
                # For loan size categories, use sum of all three categories as denominator
                # to ensure percentages add up to 100%
                if key in ['under_100k', '100k_250k', '250k_1m']:
                    total = (indicators['under_100k'][year_str] + 
                             indicators['100k_250k'][year_str] + 
                             indicators['250k_1m'][year_str])
                    total_amount = (indicators.get('under_100k_amount', {}).get(year_str, 0) +
                                   indicators.get('100k_250k_amount', {}).get(year_str, 0) +
                                   indicators.get('250k_1m_amount', {}).get(year_str, 0))
                else:
                    total = indicators['total'][year_str]
                    total_amount = indicators.get('total_amount', {}).get(year_str, 0)
                
                pct = (count / total * 100) if total > 0 else 0
                
                # Also include amount if available
                amount_key = f'{key}_amount'
                amount = indicators.get(amount_key, {}).get(year_str, 0) if amount_key in indicators else 0
                # For income tracts, use total_amount as denominator
                if key in ['low_income_tract', 'moderate_income_tract', 'middle_income_tract', 'upper_income_tract', 'lmict']:
                    amount_pct = (amount / total_amount * 100) if total_amount > 0 else 0
                else:
                    amount_pct = (amount / total_amount * 100) if total_amount > 0 else 0
                
                row_data[year_str] = {
                    'count': count,
                    'percent': round(pct, 2),
                    'amount': round(amount, 2),
                    'amount_percent': round(amount_pct, 2)
                }
        
        if len(years) >= 2 and key != 'mmct':
            first_count = indicators[key][str(min(years))]
            last_count = indicators[key][str(max(years))]
            change = last_count - first_count
            change_pct = ((last_count - first_count) / first_count * 100) if first_count > 0 else 0
            
            row_data['change'] = {
                'absolute': change,
                'percent': round(change_pct, 2)
            }
        elif key == 'mmct':
            row_data['change'] = {'absolute': 0, 'percent': 0}
        
        table.append(row_data)
    
    # Add combined Low & Moderate Income Census Tracts row (for expandable header)
    lmi_tract_row = {'indicator': 'Low & Moderate Income Census Tracts'}
    for year in sorted(years):
        year_str = str(year)
        count = lmi_tract_metric[year_str]
        total = indicators['total'][year_str]
        pct = (count / total * 100) if total > 0 else 0
        amount = lmi_tract_metric_amount[year_str]
        total_amount = indicators.get('total_amount', {}).get(year_str, 0)
        amount_pct = (amount / total_amount * 100) if total_amount > 0 else 0
        lmi_tract_row[year_str] = {
            'count': count,
            'percent': round(pct, 2),
            'amount': round(amount, 2),
            'amount_percent': round(amount_pct, 2)
        }
    if len(years) >= 2:
        first_count = lmi_tract_metric[str(min(years))]
        last_count = lmi_tract_metric[str(max(years))]
        change = last_count - first_count
        change_pct = ((last_count - first_count) / first_count * 100) if first_count > 0 else 0
        lmi_tract_row['change'] = {
            'absolute': change,
            'percent': round(change_pct, 2)
        }
    table.append(lmi_tract_row)
    
    # Add business revenue category rows (for chart display)
    for rev_key in ['rev_under_1m_amount', 'rev_over_1m_amount']:
        if rev_key in indicators:
            row_data = {'indicator': indicator_names[rev_key]}
            for year in sorted(years):
                year_str = str(year)
                amount = indicators[rev_key].get(year_str, 0)
                total_amount = indicators.get('total_amount', {}).get(year_str, 0)
                amount_pct = (amount / total_amount * 100) if total_amount > 0 else 0
                row_data[year_str] = {
                    'count': 0,  # Not using counts for this chart
                    'percent': 0,
                    'amount': round(amount, 2),
                    'amount_percent': round(amount_pct, 2)
                }
            table.append(row_data)
    
    return table


def create_sb_top_lenders_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create top lenders table for Small Business."""
    latest_year = max(years)
    latest_year_str = str(latest_year)
    
    lender_data = defaultdict(lambda: {
        'name': '',
        'total_loans': 0,
        'total_amount': 0,
        'lmict_loans': 0,
        'lmict_amount': 0,
        'loans_under_100k': 0,
        'amount_under_100k': 0,
        'loans_100k_250k': 0,
        'amount_100k_250k': 0,
        'loans_250k_1m': 0,
        'amount_250k_1m': 0,
        'loans_rev_under_1m': 0,
        'amount_rev_under_1m': 0,
        'demographics': defaultdict(int)
    })
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year == latest_year_str:
            respondent_id = row.get('sb_resid', row.get('respondent_id', ''))
            lender_name = row.get('lender_name', f'Lender {respondent_id[:8] if respondent_id else "Unknown"}')
            # Clean up lender names - remove ", National Bank" suffix from American Express
            if lender_name and ', National Bank' in lender_name:
                lender_name = lender_name.replace(', National Bank', '').strip()
            
            loan_count = row.get('total_metric', row.get('sb_loans_count', 0))
            loan_amount = row.get('sb_loans_amount', row.get('total_loan_amount', 0))
            
            lender_data[respondent_id]['name'] = lender_name
            lender_data[respondent_id]['total_loans'] += int(loan_count) if loan_count else 0
            lender_data[respondent_id]['total_amount'] += float(loan_amount) if loan_amount else 0
            
            # Add LMICT loans (counts and amounts)
            lmict_count = row.get('lmict_metric', row.get('lmict_loans_count', 0))
            lender_data[respondent_id]['lmict_loans'] += int(lmict_count) if lmict_count else 0
            # For amounts, use lmict_amount from merged amount data (set in app.py)
            lmict_amt = row.get('lmict_amount', 0)
            lender_data[respondent_id]['lmict_amount'] += float(lmict_amt) if lmict_amt else 0
            
            # Add loan size categories (counts and amounts)
            under_100k = row.get('loans_under_100k_metric', row.get('num_under_100k', 0))
            lender_data[respondent_id]['loans_under_100k'] += int(under_100k) if under_100k else 0
            under_100k_amt = row.get('amt_under_100k', 0)
            lender_data[respondent_id]['amount_under_100k'] += float(under_100k_amt) if under_100k_amt else 0
            
            loans_100k_250k = row.get('loans_100k_250k_metric', row.get('num_100k_250k', 0))
            lender_data[respondent_id]['loans_100k_250k'] += int(loans_100k_250k) if loans_100k_250k else 0
            loans_100k_250k_amt = row.get('amt_100k_250k', 0)
            lender_data[respondent_id]['amount_100k_250k'] += float(loans_100k_250k_amt) if loans_100k_250k_amt else 0
            
            loans_250k_1m = row.get('loans_250k_1m_metric', row.get('num_250k_1m', 0))
            lender_data[respondent_id]['loans_250k_1m'] += int(loans_250k_1m) if loans_250k_1m else 0
            loans_250k_1m_amt = row.get('amt_250k_1m', 0)
            lender_data[respondent_id]['amount_250k_1m'] += float(loans_250k_1m_amt) if loans_250k_1m_amt else 0
            
            # Add business revenue category (counts and amounts)
            # numsbrev_under_1m represents loans to businesses with revenue under $1M
            # IMPORTANT: Do NOT fall back to total loans if numsbrev_under_1m is missing - use 0 instead
            loans_rev_under_1m = row.get('numsbrev_under_1m', 0)
            if loans_rev_under_1m is None:
                loans_rev_under_1m = 0
            lender_data[respondent_id]['loans_rev_under_1m'] += int(loans_rev_under_1m) if loans_rev_under_1m else 0
            
            amount_rev_under_1m = row.get('amtsbrev_under_1m', 0)
            if amount_rev_under_1m is None:
                amount_rev_under_1m = 0
            lender_data[respondent_id]['amount_rev_under_1m'] += float(amount_rev_under_1m) if amount_rev_under_1m else 0
            
            # Add income group counts
            for group in ['low_income', 'moderate_income', 'middle_income', 'upper_income']:
                count = row.get(f'{group}_metric', 0)
                lender_data[respondent_id]['demographics'][group] += int(count) if count else 0
    
    sorted_lenders = sorted(
        lender_data.items(),
        key=lambda x: x[1]['total_loans'],
        reverse=True
    )  # Remove [:10] limit to get all lenders for Excel export
    
    table = []
    for respondent_id, data in sorted_lenders:
        # Calculate percentages for counts (using total_loans as denominator)
        # For loan size categories, use sum of the three categories as denominator to ensure they add up to 100%
        total_loan_size_categories = data['loans_under_100k'] + data['loans_100k_250k'] + data['loans_250k_1m']
        total_loan_size_amounts = data['amount_under_100k'] + data['amount_100k_250k'] + data['amount_250k_1m']
        
        # Calculate revenue under $1M percentage
        # Note: total_loans might actually be from numsbrev_under_1m in some cases, so we need to be careful
        # Calculate percentage only if we have valid data
        rev_under_1m_pct = 0
        if data['total_loans'] > 0 and data['loans_rev_under_1m'] >= 0:
            # Calculate the percentage
            calculated_pct = (data['loans_rev_under_1m'] / data['total_loans'] * 100) if data['total_loans'] > 0 else 0
            
            # Only show 0% if loans_rev_under_1m is actually 0 (not if it's missing data)
            # If it's > 0, show the calculated percentage (even if it's 100%, that might be correct)
            # The issue was that we were hiding valid 100% values thinking they were fallback data
            if data['loans_rev_under_1m'] > 0:
                rev_under_1m_pct = round(calculated_pct, 2)
            # If loans_rev_under_1m is 0, show 0% (which is correct)
        
        row_data = {
            'lei': respondent_id,  # Using respondent_id as identifier
            'name': data['name'],
            'type': 'Small Business Lender',
            'total_loans': data['total_loans'],
            'total_amount': round(data['total_amount'], 2),
            'demographics': {},
            'performance_indicators': {
                # Count-based percentages
                'lmict_percent': round((data['lmict_loans'] / data['total_loans'] * 100) if data['total_loans'] > 0 else 0, 2),
                'under_100k_percent': round((data['loans_under_100k'] / total_loan_size_categories * 100) if total_loan_size_categories > 0 else 0, 2),
                '100k_250k_percent': round((data['loans_100k_250k'] / total_loan_size_categories * 100) if total_loan_size_categories > 0 else 0, 2),
                '250k_1m_percent': round((data['loans_250k_1m'] / total_loan_size_categories * 100) if total_loan_size_categories > 0 else 0, 2),
                'rev_under_1m_percent': rev_under_1m_pct,
                # Amount-based percentages
                'lmict_amount_percent': round((data['lmict_amount'] / data['total_amount'] * 100) if data['total_amount'] > 0 else 0, 2),
                'under_100k_amount_percent': round((data['amount_under_100k'] / total_loan_size_amounts * 100) if total_loan_size_amounts > 0 else 0, 2),
                '100k_250k_amount_percent': round((data['amount_100k_250k'] / total_loan_size_amounts * 100) if total_loan_size_amounts > 0 else 0, 2),
                '250k_1m_amount_percent': round((data['amount_250k_1m'] / total_loan_size_amounts * 100) if total_loan_size_amounts > 0 else 0, 2),
                'rev_under_1m_amount_percent': round((data['amount_rev_under_1m'] / data['total_amount'] * 100) if data['total_amount'] > 0 else 0, 2)
            }
        }
        
        for group in ['low_income', 'moderate_income', 'middle_income', 'upper_income']:
            count = data['demographics'][group]
            pct = (count / data['total_loans'] * 100) if data['total_loans'] > 0 else 0
            row_data['demographics'][group] = {
                'count': count,
                'percent': round(pct, 2)
            }
        
        table.append(row_data)
    
    return table


def calculate_sb_hhi(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, Any]:
    """Calculate HHI for Small Business market concentration (latest year)."""
    latest_year = max(years)
    latest_year_str = str(latest_year)
    
    lender_amounts = defaultdict(float)
    total_amount = 0
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year == latest_year_str:
            respondent_id = row.get('sb_resid', row.get('respondent_id', ''))
            loan_amount = row.get('sb_loans_amount', row.get('total_loan_amount', 0))
            amount = float(loan_amount) if loan_amount else 0
            
            lender_amounts[respondent_id] += amount
            total_amount += amount
    
    if total_amount == 0:
        return {
            'hhi': None,
            'concentration_level': 'Not Available',
            'year': latest_year,
            'total_amount': 0,
            'top_lenders': []
        }
    
    hhi = 0
    for respondent_id, amount in lender_amounts.items():
        market_share = amount / total_amount
        hhi += market_share * market_share
    
    hhi = hhi * 10000
    
    if hhi < 1500:
        level = 'Unconcentrated'
    elif hhi < 2500:
        level = 'Moderately Concentrated'
    else:
        level = 'Highly Concentrated'
    
    sorted_lenders = sorted(
        lender_amounts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    top_lenders = []
    for respondent_id, amount in sorted_lenders:
        market_share = (amount / total_amount * 100) if total_amount > 0 else 0
        top_lenders.append({
            'lei': respondent_id,
            'amount': round(amount, 2),
            'market_share': round(market_share, 2)
        })
    
    return {
        'hhi': round(hhi, 2),
        'concentration_level': level,
        'year': latest_year,
        'total_amount': round(total_amount, 2),
        'top_lenders': top_lenders
    }


def calculate_sb_hhi_by_year(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Calculate HHI for Small Business for each year to show trends over time."""
    if not raw_data:
        return []
    
    # Group data by year
    yearly_data = defaultdict(lambda: defaultdict(float))
    yearly_totals = defaultdict(float)
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            respondent_id = row.get('sb_resid', row.get('respondent_id', ''))
            loan_amount = row.get('sb_loans_amount', row.get('total_loan_amount', 0))
            amount = float(loan_amount) if loan_amount else 0
            
            yearly_data[year][respondent_id] += amount
            yearly_totals[year] += amount
    
    # Calculate HHI for each year
    hhi_by_year = []
    sorted_years = sorted(years)
    
    for year in sorted_years:
        year_str = str(year)
        lender_amounts = yearly_data[year_str]
        total_amount = yearly_totals[year_str]
        
        if total_amount == 0:
            hhi_by_year.append({
                'year': year_str,
                'hhi': None,
                'concentration_level': 'Not Available',
                'total_amount': 0,
                'top_lenders': []
            })
            continue
        
        # Calculate HHI
        hhi = 0
        for respondent_id, amount in lender_amounts.items():
            market_share = amount / total_amount
            hhi += market_share * market_share
        
        hhi = hhi * 10000
        
        # Determine concentration level per 2023 DOJ/FTC Merger Guidelines
        # Thresholds: <1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), >2,500 (Highly Concentrated)
        if hhi < 1500:
            level = 'Unconcentrated'
        elif hhi < 2500:
            level = 'Moderately Concentrated'
        else:
            level = 'Highly Concentrated'
        
        # Get top 5 lenders for this year
        sorted_lenders = sorted(
            lender_amounts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        top_lenders = []
        for respondent_id, amount in sorted_lenders:
            market_share = (amount / total_amount * 100) if total_amount > 0 else 0
            top_lenders.append({
                'lei': respondent_id,
                'amount': round(amount, 2),
                'market_share': round(market_share, 2)
            })
        
        hhi_by_year.append({
            'year': year_str,
            'hhi': round(hhi, 2),
            'concentration_level': level,
            'total_amount': round(total_amount, 2),
            'top_lenders': top_lenders
        })
    
    return hhi_by_year


def calculate_sb_hhi_by_year_by_revenue(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, List[Dict[str, Any]]]:
    """Calculate HHI by year broken down by business revenue category (<$1M vs ≥$1M)."""
    # Calculate HHI for all loans
    all_hhi = calculate_sb_hhi_by_year(raw_data, years)
    
    # Calculate HHI for "Under $1M Revenue" using amtsbrev_under_1m
    under_1m_hhi = []
    for year in years:
        year_str = str(year)
        lender_amounts = defaultdict(float)
        total_amount = 0
        
        for row in raw_data:
            if str(row.get('year', '')) == year_str:
                respondent_id = row.get('sb_resid', row.get('respondent_id', ''))
                # Use amtsbrev_under_1m for under $1M revenue
                amount = float(row.get('amtsbrev_under_1m', row.get('amount_rev_under_1m', 0)) or 0)
                if amount > 0:
                    lender_amounts[respondent_id] += amount
                    total_amount += amount
        
        if total_amount > 0:
            hhi = sum((amt / total_amount * 100) ** 2 for amt in lender_amounts.values())
            if hhi < 1500:
                level = 'Unconcentrated'
            elif hhi < 2500:
                level = 'Moderately Concentrated'
            else:
                level = 'Highly Concentrated'
            
            # Get top 5 lenders
            sorted_lenders = sorted(lender_amounts.items(), key=lambda x: x[1], reverse=True)
            top_lenders = [{'lei': lei, 'amount': round(amt, 2), 'share': round((amt / total_amount * 100), 2)} 
                          for lei, amt in sorted_lenders[:5]]
            
            under_1m_hhi.append({
                'year': year_str,
                'hhi': round(hhi, 2),
                'concentration_level': level,
                'total_amount': round(total_amount, 2),
                'top_lenders': top_lenders
            })
        else:
            under_1m_hhi.append({
                'year': year_str,
                'hhi': None,
                'concentration_level': 'Not Available',
                'total_amount': 0,
                'top_lenders': []
            })
    
    # Calculate HHI for "Over $1M Revenue" using total - under $1M
    over_1m_hhi = []
    for year in years:
        year_str = str(year)
        lender_amounts = defaultdict(float)
        total_amount = 0
        
        for row in raw_data:
            if str(row.get('year', '')) == year_str:
                respondent_id = row.get('sb_resid', row.get('respondent_id', ''))
                # Calculate over $1M as total - under $1M
                total_amt = float(row.get('sb_loans_amount', 0) or 0)
                under_1m_amt = float(row.get('amtsbrev_under_1m', row.get('amount_rev_under_1m', 0)) or 0)
                amount = total_amt - under_1m_amt
                if amount > 0:
                    lender_amounts[respondent_id] += amount
                    total_amount += amount
        
        if total_amount > 0:
            hhi = sum((amt / total_amount * 100) ** 2 for amt in lender_amounts.values())
            if hhi < 1500:
                level = 'Unconcentrated'
            elif hhi < 2500:
                level = 'Moderately Concentrated'
            else:
                level = 'Highly Concentrated'
            
            # Get top 5 lenders
            sorted_lenders = sorted(lender_amounts.items(), key=lambda x: x[1], reverse=True)
            top_lenders = [{'lei': lei, 'amount': round(amt, 2), 'share': round((amt / total_amount * 100), 2)} 
                          for lei, amt in sorted_lenders[:5]]
            
            over_1m_hhi.append({
                'year': year_str,
                'hhi': round(hhi, 2),
                'concentration_level': level,
                'total_amount': round(total_amount, 2),
                'top_lenders': top_lenders
            })
        else:
            over_1m_hhi.append({
                'year': year_str,
                'hhi': None,
                'concentration_level': 'Not Available',
                'total_amount': 0,
                'top_lenders': []
            })
    
    result = {
        'all': all_hhi,
        'Under $1M Revenue': under_1m_hhi,
        'Over $1M Revenue': over_1m_hhi
    }
    
    return result


def create_sb_trends_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create year-over-year trends table for Small Business."""
    if len(years) < 2:
        return []
    
    yearly_totals = defaultdict(lambda: {'loans': 0, 'amount': 0})
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            loan_count = row.get('total_metric', row.get('sb_loans_count', 0))
            loan_amount = row.get('sb_loans_amount', row.get('total_loan_amount', 0))
            
            yearly_totals[year]['loans'] += int(loan_count) if loan_count else 0
            yearly_totals[year]['amount'] += float(loan_amount) if loan_amount else 0
    
    table = []
    sorted_years = sorted(years)
    
    for i in range(1, len(sorted_years)):
        prev_year = str(sorted_years[i-1])
        curr_year = str(sorted_years[i])
        
        prev_loans = yearly_totals[prev_year]['loans']
        curr_loans = yearly_totals[curr_year]['loans']
        prev_amount = yearly_totals[prev_year]['amount']
        curr_amount = yearly_totals[curr_year]['amount']
        
        loan_change = curr_loans - prev_loans
        loan_change_pct = ((curr_loans - prev_loans) / prev_loans * 100) if prev_loans > 0 else 0
        amount_change = curr_amount - prev_amount
        amount_change_pct = ((curr_amount - prev_amount) / prev_amount * 100) if prev_amount > 0 else 0
        
        table.append({
            'period': f'{prev_year}→{curr_year}',
            'loans': {
                'change': loan_change,
                'percent': round(loan_change_pct, 2)
            },
            'amount': {
                'change': round(amount_change, 2),
                'percent': round(amount_change_pct, 2)
            }
        })
    
    return table


# Branch Processing Functions

def create_branch_summary_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create summary table for Branch data."""
    yearly_totals = defaultdict(lambda: {'total_branches': 0, 'total_deposits': 0, 'avg_deposits': 0})
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            deposits = row.get('deposits', row.get('total_deposits', 0))
            
            yearly_totals[year]['total_branches'] += 1
            yearly_totals[year]['total_deposits'] += float(deposits) if deposits else 0
    
    table = []
    for year in sorted(years, reverse=True):
        year_str = str(year)
        totals = yearly_totals[year_str]
        avg = totals['total_deposits'] / totals['total_branches'] if totals['total_branches'] > 0 else 0
        
        table.append({
            'year': year_str,
            'total_loans': totals['total_branches'],  # Using 'total_loans' key for consistency
            'total_amount': round(totals['total_deposits'], 2),
            'avg_amount': round(avg, 2)
        })
    
    return table


def create_branch_income_neighborhood_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create income and neighborhood indicators table for Branch data - matching HMDA format."""
    indicators = {
        'total': defaultdict(int),
        'low_income_tract': defaultdict(int),
        'moderate_income_tract': defaultdict(int),
        'middle_income_tract': defaultdict(int),
        'upper_income_tract': defaultdict(int),
        'lmi_tract': defaultdict(int),  # Combined low + moderate
        'mmct_tract': defaultdict(int),
        'lmi_only': defaultdict(int),  # LMI but NOT MMCT
        'mmct_only': defaultdict(int),  # MMCT but NOT LMI
        'both_lmi_mmct': defaultdict(int),  # Both LMI and MMCT (deduplicated)
        # For minority breakdowns, we need tract_minority_population_percent from the data
        'low_minority_tract': defaultdict(int),   # < mean - stddev
        'moderate_minority_tract': defaultdict(int),  # mean - stddev to mean
        'middle_minority_tract': defaultdict(int),    # mean to mean + stddev
        'high_minority_tract': defaultdict(int)       # > mean + stddev
    }
    
    # First pass: collect all minority percentages to calculate mean and stddev
    minority_percentages_by_year = defaultdict(list)
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            # Get minority percentage from tract_minority_population_percent if available
            minority_pct = row.get('tract_minority_population_percent')
            if minority_pct is not None:
                try:
                    minority_percentages_by_year[year].append(float(minority_pct))
                except (ValueError, TypeError):
                    pass
    
    # Calculate mean and stddev for each year
    minority_stats_by_year = {}
    for year in years:
        year_str = str(year)
        percentages = minority_percentages_by_year.get(year_str, [])
        if percentages:
            import statistics
            mean = statistics.mean(percentages)
            stddev = statistics.stdev(percentages) if len(percentages) > 1 else 0
            minority_stats_by_year[year_str] = {'mean': mean, 'stddev': stddev}
        else:
            minority_stats_by_year[year_str] = {'mean': 0, 'stddev': 0}
    
    # Second pass: categorize branches
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            indicators['total'][year] += 1
            
            # Income tract categorization
            if row.get('is_low_income_tract', 0):
                indicators['low_income_tract'][year] += 1
            if row.get('is_moderate_income_tract', 0):
                indicators['moderate_income_tract'][year] += 1
            if row.get('is_middle_income_tract', 0):
                indicators['middle_income_tract'][year] += 1
            if row.get('is_upper_income_tract', 0):
                indicators['upper_income_tract'][year] += 1
            is_lmi = row.get('is_lmi_tract', 0)
            is_mmct = row.get('is_mmct_tract', 0)
            
            if is_lmi:
                indicators['lmi_tract'][year] += 1
            
            if is_mmct:
                indicators['mmct_tract'][year] += 1
            
            # Calculate LMI Only, MMCT Only, and Both
            if is_lmi and not is_mmct:
                indicators['lmi_only'][year] += 1
            elif is_mmct and not is_lmi:
                indicators['mmct_only'][year] += 1
            elif is_lmi and is_mmct:
                indicators['both_lmi_mmct'][year] += 1
            
            # Minority tract categorization (using mean/stddev approach like HMDA)
            minority_pct = row.get('tract_minority_population_percent')
            if minority_pct is not None:
                try:
                    pct = float(minority_pct)
                    stats = minority_stats_by_year.get(year, {'mean': 0, 'stddev': 0})
                    mean = stats['mean']
                    stddev = stats['stddev']
                    
                    if stddev > 0:
                        if pct < (mean - stddev):
                            indicators['low_minority_tract'][year] += 1
                        elif pct < mean:
                            indicators['moderate_minority_tract'][year] += 1
                        elif pct < (mean + stddev):
                            indicators['middle_minority_tract'][year] += 1
                        else:
                            indicators['high_minority_tract'][year] += 1
                except (ValueError, TypeError):
                    pass
    
    # Build table matching HMDA format
    table = []
    
    # Total Branches
    total_row = {'indicator': 'Total Branches'}
    for year in sorted(years):
        year_str = str(year)
        count = indicators['total'][year_str]
        total_row[year_str] = {'count': count, 'percent': 100.0}
    table.append(total_row)
    
    # LMI Tracts (combined) - expandable header
    lmi_tract_row = {'indicator': 'Low & Moderate Income Census Tracts'}
    for year in sorted(years):
        year_str = str(year)
        count = indicators['lmi_tract'][year_str]
        total = indicators['total'][year_str]
        pct = (count / total * 100) if total > 0 else 0
        lmi_tract_row[year_str] = {'count': count, 'percent': round(pct, 2)}
    table.append(lmi_tract_row)
    
    # Individual income tract rows (expandable under LMI)
    income_tract_rows = [
        ('low_income_tract', 'Low Income Tracts'),
        ('moderate_income_tract', 'Moderate Income Tracts'),
        ('middle_income_tract', 'Middle Income Tracts'),
        ('upper_income_tract', 'Upper Income Tracts')
    ]
    
    for key, name in income_tract_rows:
        row_data = {'indicator': name}
        for year in sorted(years):
            year_str = str(year)
            count = indicators[key][year_str]
            total = indicators['total'][year_str]
            pct = (count / total * 100) if total > 0 else 0
            row_data[year_str] = {'count': count, 'percent': round(pct, 2)}
        table.append(row_data)
    
    # MMCT (combined) - expandable header
    mmct_row = {'indicator': 'Majority-Minority Census Tracts (MMCT)'}
    for year in sorted(years):
        year_str = str(year)
        count = indicators['mmct_tract'][year_str]
        total = indicators['total'][year_str]
        pct = (count / total * 100) if total > 0 else 0
        mmct_row[year_str] = {'count': count, 'percent': round(pct, 2)}
    table.append(mmct_row)
    
    # Add LMI Only, MMCT Only, and Both rows for lender comparison cards
    lmi_only_row = {'indicator': 'LMI Only Branches'}
    for year in sorted(years):
        year_str = str(year)
        count = indicators['lmi_only'][year_str]
        total = indicators['total'][year_str]
        pct = (count / total * 100) if total > 0 else 0
        lmi_only_row[year_str] = {'count': count, 'percent': round(pct, 2)}
    table.append(lmi_only_row)
    
    mmct_only_row = {'indicator': 'MMCT Only Branches'}
    for year in sorted(years):
        year_str = str(year)
        count = indicators['mmct_only'][year_str]
        total = indicators['total'][year_str]
        pct = (count / total * 100) if total > 0 else 0
        mmct_only_row[year_str] = {'count': count, 'percent': round(pct, 2)}
    table.append(mmct_only_row)
    
    both_lmi_mmct_row = {'indicator': 'Both LMI and MMCT Branches'}
    for year in sorted(years):
        year_str = str(year)
        count = indicators['both_lmi_mmct'][year_str]
        total = indicators['total'][year_str]
        pct = (count / total * 100) if total > 0 else 0
        both_lmi_mmct_row[year_str] = {'count': count, 'percent': round(pct, 2)}
    table.append(both_lmi_mmct_row)
    
    # Individual minority tract rows (expandable under MMCT)
    minority_tract_rows = [
        ('low_minority_tract', 'Low Minority Tracts'),
        ('moderate_minority_tract', 'Moderate Minority Tracts'),
        ('middle_minority_tract', 'Middle Minority Tracts'),
        ('high_minority_tract', 'High Minority Tracts')
    ]
    
    for key, name in minority_tract_rows:
        row_data = {'indicator': name}
        for year in sorted(years):
            year_str = str(year)
            count = indicators[key][year_str]
            total = indicators['total'][year_str]
            pct = (count / total * 100) if total > 0 else 0
            row_data[year_str] = {'count': count, 'percent': round(pct, 2)}
        table.append(row_data)
    
    return table


def clean_bank_name(bank_name: str) -> str:
    """Clean bank name by removing suffixes like 'National Association' and postscripts."""
    if not bank_name:
        return ""
    
    import re
    
    # Remove leading "THE" or "The"
    bank_name = re.sub(r'^THE\s+', '', bank_name, flags=re.IGNORECASE).strip()
    bank_name = re.sub(r'^The\s+', '', bank_name, flags=re.IGNORECASE).strip()
    
    # Remove everything after the first comma (including the comma)
    bank_name = bank_name.split(',')[0].strip()
    
    # List of suffixes to remove (case-insensitive)
    suffixes = [
        r'\s+National\s+Association\s*$',
        r'\s+National\s+Assoc\.?\s*$',
        r'\s+N\.?A\.?\s*$',
        r'\s+NA\s*$',
        r'\s+Federal\s+Savings\s+Bank\s*$',
        r'\s+FSB\s*$',
        r'\s+Federal\s+Credit\s+Union\s*$',
        r'\s+FCU\s*$',
        r'\s+State\s+Bank\s*$',
        r'\s+Savings\s+Bank\s*$',
        r'\s+Savings\s+and\s+Loan\s*$',
        r'\s+S&L\s*$',
        r'\s+INC\.?\s*$',
        r'\s+LLC\.?\s*$',
        r'\s+Corporation\s*$',
        r'\s+CORP\.?\s*$',
        r'\s+Corp\.?\s*$',
        r'\s+Company\s*$',
        r'\s+CO\.?\s*$',
        r'\s+Co\.?\s*$',
    ]
    
    # Apply patterns repeatedly until no more matches
    changed = True
    while changed:
        changed = False
        for pattern in suffixes:
            new_name = re.sub(pattern, '', bank_name, flags=re.IGNORECASE).strip()
            if new_name != bank_name:
                bank_name = new_name
                changed = True
    
    return bank_name.strip()


def create_branch_top_lenders_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create top lenders table for Branch data."""
    latest_year = max(years)
    latest_year_str = str(latest_year)
    
    # Get 2021 data for comparison (not 2020)
    year_2021_str = '2021'
    has_2021 = 2021 in years
    
    lender_data = defaultdict(lambda: {
        'name': '',
        'total_branches_latest': 0,
        'total_branches_2021': 0,
        'total_deposits_latest': 0,
        'total_deposits_2021': 0,
        'lmi_branches': 0,
        'mmct_branches': 0
    })
    
    for row in raw_data:
        year = str(row.get('year', ''))
        rssd = row.get('rssd', '')
        lender_name = row.get('bank_name', f'Bank {rssd[:8] if rssd else "Unknown"}')
        
        # Clean bank name
        lender_name = clean_bank_name(lender_name)
        
        if year == latest_year_str:
            deposits = row.get('deposits', 0)
            
            lender_data[rssd]['name'] = lender_name
            lender_data[rssd]['total_branches_latest'] += 1
            lender_data[rssd]['total_deposits_latest'] += float(deposits) if deposits else 0
            if row.get('is_lmi_tract', 0):
                lender_data[rssd]['lmi_branches'] += 1
            if row.get('is_mmct_tract', 0):
                lender_data[rssd]['mmct_branches'] += 1
        elif year == year_2021_str and has_2021:
            deposits = row.get('deposits', 0)
            lender_data[rssd]['total_branches_2021'] += 1
            lender_data[rssd]['total_deposits_2021'] += float(deposits) if deposits else 0
    
    sorted_lenders = sorted(
        lender_data.items(),
        key=lambda x: x[1]['total_branches_latest'],
        reverse=True
    )[:10]
    
    table = []
    for rssd, data in sorted_lenders:
        total_branches_latest = data['total_branches_latest']
        total_branches_2021 = data['total_branches_2021']
        total_deposits_latest = data['total_deposits_latest']
        total_deposits_2021 = data['total_deposits_2021']
        
        branches_change_2021 = total_branches_latest - total_branches_2021
        deposits_change_2021 = total_deposits_latest - total_deposits_2021
        
        lmi_pct = (data['lmi_branches'] / total_branches_latest * 100) if total_branches_latest > 0 else 0
        mmct_pct = (data['mmct_branches'] / total_branches_latest * 100) if total_branches_latest > 0 else 0
        
        row_data = {
            'lei': rssd,  # Using RSSD as identifier
            'name': data['name'],
            'total_loans': total_branches_latest,  # Using branches as "loans" for consistency
            'total_amount': round(total_deposits_latest, 2),
            'branches_change_2021': branches_change_2021,
            'deposits_change_2021': round(deposits_change_2021, 2),
            'demographics': {
                'lmi': {
                    'count': data['lmi_branches'],
                    'percent': round(lmi_pct, 2)
                },
                'mmct': {
                    'count': data['mmct_branches'],
                    'percent': round(mmct_pct, 2)
                }
            },
            'performance_indicators': {
                'lmict': {
                    'count': data['lmi_branches'],
                    'percent': round(lmi_pct, 2)
                },
                'mmct': {
                    'count': data['mmct_branches'],
                    'percent': round(mmct_pct, 2)
                }
            }
        }
        
        table.append(row_data)
    
    return table


def calculate_branch_hhi(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, Any]:
    """Calculate HHI for Branch market concentration (by deposits) - latest year.
    Returns HHI for: all branches, LMI branches, MMCT branches, and both LMI+MMCT (deduplicated).
    """
    latest_year = max(years)
    latest_year_str = str(latest_year)
    
    # Calculate HHI for different branch categories
    def calculate_hhi_for_branches(branch_rows):
        """Calculate HHI for a set of branch rows (by deposits, not branch count)."""
        lender_deposits = defaultdict(float)
        total_deposits = 0
        
        if len(branch_rows) == 0:
            return {
                'hhi': None,
                'concentration_level': 'Not Available',
                'total_deposits': 0,
                'total_branches': 0,
                'top_lenders': []
            }
        
        # Sum deposits by lender (RSSD)
        for row in branch_rows:
            rssd = row.get('rssd', '')
            deposits = row.get('deposits', 0)
            amount = float(deposits) if deposits else 0
            if rssd:
                lender_deposits[rssd] += amount
                total_deposits += amount
        
        if total_deposits == 0:
            return {
                'hhi': None,
                'concentration_level': 'Not Available',
                'total_deposits': 0,
                'total_branches': len(branch_rows),
                'top_lenders': []
            }
        
        # Calculate HHI
        hhi = 0
        for rssd, amount in lender_deposits.items():
            market_share = amount / total_deposits
            hhi += market_share * market_share
        
        hhi = hhi * 10000
        
        if hhi < 1500:
            level = 'Unconcentrated'
        elif hhi < 2500:
            level = 'Moderately Concentrated'
        else:
            level = 'Highly Concentrated'
        
        sorted_lenders = sorted(
            lender_deposits.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        top_lenders = []
        for rssd, amount in sorted_lenders:
            market_share = (amount / total_deposits * 100) if total_deposits > 0 else 0
            top_lenders.append({
                'lei': rssd,
                'amount': round(amount, 2),  # Deposits
                'market_share': round(market_share, 2)
            })
        
        return {
            'hhi': round(hhi, 2),
            'concentration_level': level,
            'total_deposits': round(total_deposits, 2),
            'total_branches': len(branch_rows),
            'top_lenders': top_lenders
        }
    
    # Filter branches for latest year
    latest_year_branches = [row for row in raw_data if str(row.get('year', '')) == latest_year_str]
    
    # All branches
    all_hhi = calculate_hhi_for_branches(latest_year_branches)
    
    # LMI branches
    lmi_branches = [row for row in latest_year_branches if row.get('is_lmi_tract', 0)]
    lmi_hhi = calculate_hhi_for_branches(lmi_branches)
    
    # MMCT branches
    mmct_branches = [row for row in latest_year_branches if row.get('is_mmct_tract', 0)]
    mmct_hhi = calculate_hhi_for_branches(mmct_branches)
    
    # Both LMI and MMCT (deduplicated - branches that are in both)
    both_branches = [row for row in latest_year_branches 
                     if row.get('is_lmi_tract', 0) and row.get('is_mmct_tract', 0)]
    both_hhi = calculate_hhi_for_branches(both_branches)
    
    return {
        'hhi': all_hhi.get('hhi'),
        'concentration_level': all_hhi.get('concentration_level'),
        'year': latest_year,
        'total_amount': all_hhi.get('total_deposits', 0),
        'total_branches': all_hhi.get('total_branches', 0),
        'top_lenders': all_hhi.get('top_lenders', []),
        'all_branches': all_hhi,
        'lmi_branches': lmi_hhi,
        'mmct_branches': mmct_hhi,
        'both_lmi_mmct_branches': both_hhi
    }


def calculate_branch_hhi_by_year(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Calculate HHI for Branch market concentration for each year (2021-2025) by branch count.
    Returns HHI for: all branches, LMI branches, MMCT branches, and both LMI+MMCT (deduplicated).
    """
    if not raw_data:
        return []
    
    # Filter to 2021-2025 only
    filtered_years = [y for y in years if 2021 <= y <= 2025]
    if not filtered_years:
        return []
    
    def calculate_hhi_for_branches_by_year(branch_rows_by_year):
        """Calculate HHI for branches by year (by deposits, not branch count)."""
        hhi_by_year = []
        sorted_years = sorted(filtered_years)
        
        for year in sorted_years:
            year_str = str(year)
            year_branches = branch_rows_by_year.get(year_str, [])
            
            lender_deposits = defaultdict(float)
            total_deposits = 0
            
            if len(year_branches) == 0:
                hhi_by_year.append({
                    'year': year_str,
                    'hhi': None,
                    'concentration_level': 'Not Available',
                    'total_amount': 0,
                    'total_branches': 0,
                    'top_lenders': []
                })
                continue
            
            # Sum deposits by lender (RSSD)
            for row in year_branches:
                rssd = row.get('rssd', '')
                deposits = row.get('deposits', 0)
                amount = float(deposits) if deposits else 0
                if rssd:
                    lender_deposits[rssd] += amount
                    total_deposits += amount
            
            if total_deposits == 0:
                hhi_by_year.append({
                    'year': year_str,
                    'hhi': None,
                    'concentration_level': 'Not Available',
                    'total_amount': 0,
                    'total_branches': len(year_branches),
                    'top_lenders': []
                })
                continue
            
            # Calculate HHI
            hhi = 0
            for rssd, amount in lender_deposits.items():
                market_share = amount / total_deposits
                hhi += market_share * market_share
            
            hhi = hhi * 10000
            
            if hhi < 1500:
                level = 'Unconcentrated'
            elif hhi < 2500:
                level = 'Moderately Concentrated'
            else:
                level = 'Highly Concentrated'
            
            sorted_lenders = sorted(
                lender_deposits.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            top_lenders = []
            for rssd, amount in sorted_lenders:
                market_share = (amount / total_deposits * 100) if total_deposits > 0 else 0
                top_lenders.append({
                    'lei': rssd,
                    'amount': round(amount, 2),  # Deposits
                    'market_share': round(market_share, 2)
                })
            
            hhi_by_year.append({
                'year': year_str,
                'hhi': round(hhi, 2),
                'concentration_level': level,
                'total_amount': round(total_deposits, 2),
                'total_branches': len(year_branches),
                'top_lenders': top_lenders
            })
        
        return hhi_by_year
    
    # Group branches by year
    all_branches_by_year = defaultdict(list)
    lmi_branches_by_year = defaultdict(list)
    mmct_branches_by_year = defaultdict(list)
    both_branches_by_year = defaultdict(list)
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and int(year) in filtered_years:
            all_branches_by_year[year].append(row)
            if row.get('is_lmi_tract', 0):
                lmi_branches_by_year[year].append(row)
            if row.get('is_mmct_tract', 0):
                mmct_branches_by_year[year].append(row)
            if row.get('is_lmi_tract', 0) and row.get('is_mmct_tract', 0):
                both_branches_by_year[year].append(row)
    
    # Calculate HHI for each category
    all_hhi_by_year = calculate_hhi_for_branches_by_year(all_branches_by_year)
    lmi_hhi_by_year = calculate_hhi_for_branches_by_year(lmi_branches_by_year)
    mmct_hhi_by_year = calculate_hhi_for_branches_by_year(mmct_branches_by_year)
    both_hhi_by_year = calculate_hhi_for_branches_by_year(both_branches_by_year)
    
    # Return structure with all categories
    return {
        'all_branches': all_hhi_by_year,
        'lmi_branches': lmi_hhi_by_year,
        'mmct_branches': mmct_hhi_by_year,
        'both_lmi_mmct_branches': both_hhi_by_year
    }


def create_branch_trends_table(raw_data: List[Dict[str, Any]], years: List[int]) -> List[Dict[str, Any]]:
    """Create year-over-year trends table for Branch data."""
    if len(years) < 2:
        return []
    
    yearly_totals = defaultdict(lambda: {'branches': 0, 'deposits': 0})
    
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            deposits = row.get('deposits', 0)
            
            yearly_totals[year]['branches'] += 1
            yearly_totals[year]['deposits'] += float(deposits) if deposits else 0
    
    table = []
    sorted_years = sorted(years)
    
    for i in range(1, len(sorted_years)):
        prev_year = str(sorted_years[i-1])
        curr_year = str(sorted_years[i])
        
        prev_branches = yearly_totals[prev_year]['branches']
        curr_branches = yearly_totals[curr_year]['branches']
        prev_deposits = yearly_totals[prev_year]['deposits']
        curr_deposits = yearly_totals[curr_year]['deposits']
        
        branch_change = curr_branches - prev_branches
        branch_change_pct = ((curr_branches - prev_branches) / prev_branches * 100) if prev_branches > 0 else 0
        deposit_change = curr_deposits - prev_deposits
        deposit_change_pct = ((curr_deposits - prev_deposits) / prev_deposits * 100) if prev_deposits > 0 else 0
        
        table.append({
            'period': f'{prev_year}→{curr_year}',
            'loans': {  # Using 'loans' key for consistency with frontend
                'change': branch_change,
                'percent': round(branch_change_pct, 2)
            },
            'amount': {
                'change': round(deposit_change, 2),
                'percent': round(deposit_change_pct, 2)
            }
        })
    
    return table
