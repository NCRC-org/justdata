"""SQL filter / parameter parsing for lender analysis."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from justdata.shared.utils.bigquery_client import escape_sql_string

logger = logging.getLogger(__name__)


def apply_filters_to_sql_template(sql_template: str, query_filters: Dict[str, Any]) -> str:
    """
    Apply query filters to SQL template by replacing hardcoded filter values.
    
    Args:
        sql_template: SQL query template with hardcoded filters
        query_filters: Dictionary of filters from wizard (action_taken, occupancy, total_units, etc.)
        
    Returns:
        Modified SQL template with filters applied
    """
    sql = sql_template
    
    # Apply action_taken filter
    action_taken = query_filters.get('action_taken', ['1'])
    if len(action_taken) == 1:
        action_taken_clause = f"h.action_taken = '{action_taken[0]}'"
    else:
        action_taken_values = "', '".join(action_taken)
        action_taken_clause = f"h.action_taken IN ('{action_taken_values}')"
    sql = sql.replace("h.action_taken = '1'  -- Originated loans only", f"{action_taken_clause}  -- Action taken filter")
    
    # Apply occupancy filter
    occupancy = query_filters.get('occupancy', ['1'])
    if len(occupancy) == 1:
        occupancy_clause = f"h.occupancy_type = '{occupancy[0]}'"
    else:
        occupancy_values = "', '".join(occupancy)
        occupancy_clause = f"h.occupancy_type IN ('{occupancy_values}')"
    sql = sql.replace("h.occupancy_type = '1'  -- Owner-occupied", f"{occupancy_clause}  -- Occupancy filter")
    
    # Apply total_units filter
    total_units = query_filters.get('total_units', ['1', '2', '3', '4'])
    if total_units == ['5+']:
        total_units_clause = "(h.total_units IS NOT NULL AND h.total_units NOT IN ('1','2','3','4'))  -- 5+ units"
    elif len(total_units) == 1:
        total_units_clause = f"h.total_units = '{total_units[0]}'"
    else:
        total_units_values = "', '".join(total_units)
        total_units_clause = f"h.total_units IN ('{total_units_values}')"
    sql = sql.replace("h.total_units IN ('1','2','3','4')  -- 1-4 units", f"{total_units_clause}  -- Total units filter")
    
    # Apply construction filter
    construction = query_filters.get('construction', ['1'])
    if len(construction) == 1:
        construction_clause = f"h.construction_method = '{construction[0]}'"
    else:
        construction_values = "', '".join(construction)
        construction_clause = f"h.construction_method IN ('{construction_values}')"
    sql = sql.replace("h.construction_method = '1'  -- Site-built", f"{construction_clause}  -- Construction filter")
    
    # Apply loan_type filter (if specified)
    loan_type = query_filters.get('loan_type')
    if loan_type:
        if len(loan_type) == 1:
            loan_type_clause = f"h.loan_type = '{loan_type[0]}'"
        else:
            loan_type_values = "', '".join(loan_type)
            loan_type_clause = f"h.loan_type IN ('{loan_type_values}')"
        # Add loan_type filter after construction_method filter
        # Find the line after construction_method and add loan_type filter
        # For now, we'll add it as a new condition
        if "h.loan_type IN ('1','2','3','4')" not in sql:
            # Insert loan_type filter after construction_method line
            sql = sql.replace(
                f"{construction_clause}  -- Construction filter",
                f"{construction_clause}  -- Construction filter\n    AND {loan_type_clause}  -- Loan type filter"
            )
        else:
            sql = sql.replace("h.loan_type IN ('1','2','3','4')", loan_type_clause)
    
    # Apply reverse mortgage filter (exclude by default unless explicitly included)
    exclude_reverse = query_filters.get('exclude_reverse_mortgages', True)
    if exclude_reverse:
        reverse_clause = "(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages"
    else:
        reverse_clause = "1=1  -- Include reverse mortgages"
    sql = sql.replace("(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages", reverse_clause)
    
    return sql


def parse_lender_wizard_parameters(wizard_data: Dict[str, Any]) -> tuple:
    """
    Parse parameters from lender wizard data structure.
    
    Args:
        wizard_data: Dictionary from wizard with lender, geography, and filters
        
    Returns:
        Tuple of (lender_info, geography_scope, comparison_group, years_list, filters_dict, counties_list)
    """
    lender = wizard_data.get('lender', {})
    
    # Get years - default to last 3 years for lender analysis
    if 'years' in wizard_data and wizard_data['years']:
        years = wizard_data['years']
        if isinstance(years, str):
            years = [int(y.strip()) for y in years.split(',') if y.strip()]
        elif not isinstance(years, list):
            years = [int(years)]
    else:
        # Default to most recent 3 years (dynamic based on current year, capped at 2024 for HMDA)
        current_year = datetime.now().year
        max_year = min(current_year, 2024)  # HMDA data only available through 2024
        years = list(range(max_year - 2, max_year + 1))  # Most recent 3 years
    
    # Geography scope
    geography_scope = wizard_data.get('geography_scope', 'loan_cbsas')  # 'loan_cbsas', 'branch_cbsas', 'custom', 'all_cbsas'
    
    # For custom scope, get counties from lenderAnalysis or direct fields
    if geography_scope == 'custom':
        lender_analysis = wizard_data.get('lenderAnalysis', {})
        counties = lender_analysis.get('customCounties', []) or wizard_data.get('custom_counties', [])
    else:
        counties = []
    
    # Comparison group
    comparison_group = wizard_data.get('comparison_group', 'peers')  # 'peers', 'all', 'banks', 'mortgage', 'credit_unions'
    
    # Parse filters from wizard data (same format as area analysis)
    filters = wizard_data.get('filters', {})
    
    # Convert wizard filter format to query format
    query_filters = {}
    
    # Action taken: 'origination' -> ['1']
    if filters.get('actionTaken') == 'origination':
        query_filters['action_taken'] = ['1']
    elif filters.get('actionTaken') == 'application':
        query_filters['action_taken'] = ['1', '2', '3', '4', '5']
    
    # Occupancy
    occupancy_map = {
        'owner-occupied': '1',
        'second-home': '2',
        'investor': '3'
    }
    if filters.get('occupancy'):
        query_filters['occupancy'] = [occupancy_map.get(o, o) for o in filters.get('occupancy', [])]
    
    # Loan purpose - Convert wizard format to LendSight format
    if filters.get('loanPurpose'):
        purpose_list = []
        for p in filters.get('loanPurpose', []):
            if p == 'home-purchase':
                purpose_list.append('purchase')
            elif p == 'refinance':
                purpose_list.append('refinance')
            elif p == 'home-equity':
                purpose_list.append('equity')
        if purpose_list:
            query_filters['loan_purpose'] = purpose_list
    
    # Total units
    if filters.get('totalUnits') == '1-4':
        query_filters['total_units'] = ['1', '2', '3', '4']
    elif filters.get('totalUnits') == '5+':
        query_filters['total_units'] = ['5+']
    
    # Construction type
    construction_map = {
        'site-built': '1',
        'manufactured': '2'
    }
    if filters.get('construction'):
        query_filters['construction'] = [construction_map.get(c, c) for c in filters.get('construction', [])]
    
    # Loan type
    loan_type_map = {
        'conventional': '1',
        'fha': '2',
        'va': '3',
        'rhs': '4'
    }
    if filters.get('loanType'):
        query_filters['loan_type'] = [loan_type_map.get(lt, lt) for lt in filters.get('loanType', [])]
    
    # Reverse mortgage
    query_filters['exclude_reverse_mortgages'] = filters.get('reverseMortgage', True)
    
    # Counties are already extracted above for custom scope
    # For other scopes, counties will be determined in run_lender_analysis
    
    return lender, geography_scope, comparison_group, years, query_filters, counties


