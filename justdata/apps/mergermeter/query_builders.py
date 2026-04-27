"""
Query builders for MergerMeter analysis.
Generates BigQuery SQL for HMDA and Small Business data (subject and peer).
Uses 50%-200% volume rule for peer selection.

HYBRID ROUTING:
When USE_SUMMARY_TABLES is enabled:
- Default filters (originations, owner-occupied, site-built, no reverse) → Use summary tables
- Non-default filters (applications, manufactured, etc.) → Use raw tables
"""

import os
from justdata.apps.mergermeter.sql_loader import load_sql

# Configuration for hybrid routing
SUMMARY_PROJECT_ID = os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
USE_SUMMARY_TABLES = os.getenv('USE_SUMMARY_TABLES', 'false').lower() == 'true'

# Default filter values
DEFAULT_ACTION_TAKEN = '1'
DEFAULT_OCCUPANCY_TYPE = '1'
DEFAULT_CONSTRUCTION_METHOD = '1'
DEFAULT_NOT_REVERSE = '1'


def is_using_default_filters(
    action_taken: str = '1',
    occupancy_type: str = '1',
    construction_method: str = '1',
    not_reverse: str = '1'
) -> bool:
    """
    Check if the query is using default filters.
    
    Returns True if all filters match default values (originations, owner-occupied,
    site-built, no reverse mortgages). In this case, we can use summary tables.
    """
    return (
        action_taken == DEFAULT_ACTION_TAKEN and
        occupancy_type == DEFAULT_OCCUPANCY_TYPE and
        construction_method == DEFAULT_CONSTRUCTION_METHOD and
        not_reverse == DEFAULT_NOT_REVERSE
    )


def get_hmda_data_source(
    action_taken: str = '1',
    occupancy_type: str = '1',
    construction_method: str = '1',
    not_reverse: str = '1',
    project_id: str = 'justdata-ncrc'
) -> tuple:
    """
    Determine the appropriate data source based on filters.
    
    Returns:
        Tuple of (project_id, table_path, is_summary)
    """
    if USE_SUMMARY_TABLES and is_using_default_filters(action_taken, occupancy_type, construction_method, not_reverse):
        # Use summary tables for default filters (~99% cost reduction)
        return (SUMMARY_PROJECT_ID, f'{SUMMARY_PROJECT_ID}.lendsight.de_hmda_county_summary', True)
    else:
        # Use raw tables for non-default filters (full flexibility)
        return (project_id, f'{project_id}.shared.de_hmda', False)


def build_hmda_subject_query(
    subject_lei: str,
    assessment_area_geoids: list,
    years: list,
    loan_purpose: str = None,
    action_taken: str = '1',
    occupancy_type: str = '1',
    total_units: str = '1-4',
    construction_method: str = '1',
    not_reverse: str = '1'
) -> str:
    """
    Build HMDA query for subject bank.
    
    Args:
        subject_lei: Bank's LEI (string)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings)
        years: List of years as strings
        loan_purpose: Optional loan purpose filter (e.g., '1' for home purchase)
    
    Returns:
        SQL query string
    """
    if not assessment_area_geoids:
        return f"""
SELECT 
    CAST(NULL AS STRING) as activity_year,
    CAST(NULL AS STRING) as cbsa_code,
    CAST(NULL AS INT64) as total_loans,
    CAST(NULL AS FLOAT64) as total_amount,
    CAST(NULL AS INT64) as lmict_loans,
    CAST(NULL AS FLOAT64) as lmict_percentage,
    CAST(NULL AS INT64) as lmib_loans,
    CAST(NULL AS FLOAT64) as lmib_percentage,
    CAST(NULL AS FLOAT64) as lmib_amount,
    CAST(NULL AS INT64) as mmct_loans,
    CAST(NULL AS FLOAT64) as mmct_percentage,
    CAST(NULL AS INT64) as minb_loans,
    CAST(NULL AS FLOAT64) as minb_percentage
WHERE FALSE
"""
    
    geoid5_list = "', '".join([str(g).zfill(5) for g in assessment_area_geoids])
    years_list = "', '".join([str(y) for y in years])
    
    # Build filter conditions dynamically
    loan_purpose_filter = ""
    if loan_purpose:
        if ',' in loan_purpose:
            # Multiple loan purposes
            purposes = [p.strip() for p in loan_purpose.split(',')]
            purpose_list = "', '".join(purposes)
            loan_purpose_filter = f"AND h.loan_purpose IN ('{purpose_list}')"
        else:
            loan_purpose_filter = f"AND h.loan_purpose = '{loan_purpose.strip()}'"
    
    # Build action_taken filter
    action_taken_filter = ""
    if action_taken:
        if ',' in action_taken:
            # Multiple action types (Applications: 1,2,3,4,5)
            actions = [a.strip() for a in action_taken.split(',')]
            action_list = "', '".join(actions)
            action_taken_filter = f"AND h.action_taken IN ('{action_list}')"
        else:
            # Single action type (Originations: 1)
            action_taken_filter = f"AND h.action_taken = '{action_taken.strip()}'"
    
    # Build occupancy_type filter
    occupancy_filter = ""
    if occupancy_type:
        if ',' in occupancy_type:
            # Multiple occupancy types
            occupancies = [o.strip() for o in occupancy_type.split(',')]
            occupancy_list = "', '".join(occupancies)
            occupancy_filter = f"AND h.occupancy_type IN ('{occupancy_list}')"
        else:
            # Single occupancy type
            occupancy_filter = f"AND h.occupancy_type = '{occupancy_type.strip()}'"
    
    # Build total_units filter
    units_filter = ""
    if total_units:
        # Handle range notation like '1-4' → expand to '1','2','3','4'
        if '-' in total_units and ',' not in total_units:
            try:
                parts = total_units.split('-')
                start, end = int(parts[0].strip()), int(parts[1].strip())
                units = [str(i) for i in range(start, end + 1)]
            except (ValueError, IndexError):
                units = [total_units.strip()]
        elif ',' in total_units:
            units = [u.strip() for u in total_units.split(',')]
        else:
            units = [total_units.strip()]

        if len(units) == 1:
            units_filter = f"AND h.total_units = '{units[0]}'"
        else:
            units_list = "', '".join(units)
            units_filter = f"AND h.total_units IN ('{units_list}')"

    # Build construction_method filter
    construction_filter = ""
    if construction_method:
        if ',' in construction_method:
            # Multiple construction methods
            constructions = [c.strip() for c in construction_method.split(',')]
            construction_list = "', '".join(constructions)
            construction_filter = f"AND h.construction_method IN ('{construction_list}')"
        else:
            # Single construction method
            construction_filter = f"AND h.construction_method = '{construction_method.strip()}'"
    
    # Build reverse_mortgage filter
    reverse_filter = ""
    if not_reverse:
        if ',' in not_reverse:
            # Multiple values - if includes '1' (Not Reverse), exclude reverse mortgages
            reverse_values = [r.strip() for r in not_reverse.split(',')]
            if '1' in reverse_values and '2' not in reverse_values:
                # Only "Not Reverse" selected
                reverse_filter = "AND h.reverse_mortgage != '1'"
            elif '2' in reverse_values and '1' not in reverse_values:
                # Only "Reverse Mortgage" selected
                reverse_filter = "AND h.reverse_mortgage = '1'"
            # If both selected, no filter (include all)
        else:
            # Single value
            if not_reverse == '1':
                reverse_filter = "AND h.reverse_mortgage != '1'"
            elif not_reverse == '2':
                reverse_filter = "AND h.reverse_mortgage = '1'"
    
    query = load_sql("mergermeter_hmda_subject.sql").format(action_taken_filter=action_taken_filter, construction_filter=construction_filter, geoid5_list=geoid5_list, loan_purpose_filter=loan_purpose_filter, occupancy_filter=occupancy_filter, reverse_filter=reverse_filter, subject_lei=subject_lei, units_filter=units_filter, years_list=years_list)
    return query


def build_hmda_peer_query(
    subject_lei: str,
    assessment_area_geoids: list,
    years: list,
    loan_purpose: str = None,
    action_taken: str = '1',
    occupancy_type: str = '1',
    total_units: str = '1-4',
    construction_method: str = '1',
    not_reverse: str = '1',
    peer_group: str = 'volume_50_200'
) -> str:
    """
    Build peer HMDA query.
    NOTE: Qualified counties are determined SOLELY by subject lender's applications.
    Peers have no role in determining which CBSAs/counties are included.
    """
    """
    Build HMDA query for peer banks (50%-200% volume rule).
    
    Args:
        subject_lei: Subject bank's LEI (string)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings)
        years: List of years as strings
        loan_purpose: Optional loan purpose filter
    
    Returns:
        SQL query string
    """
    if not assessment_area_geoids:
        return f"""
SELECT 
    CAST(NULL AS STRING) as activity_year,
    CAST(NULL AS STRING) as cbsa_code,
    CAST(NULL AS INT64) as total_loans,
    CAST(NULL AS FLOAT64) as total_amount,
    CAST(NULL AS INT64) as lmict_loans,
    CAST(NULL AS FLOAT64) as lmict_percentage,
    CAST(NULL AS INT64) as lmib_loans,
    CAST(NULL AS FLOAT64) as lmib_percentage,
    CAST(NULL AS FLOAT64) as lmib_amount,
    CAST(NULL AS INT64) as mmct_loans,
    CAST(NULL AS FLOAT64) as mmct_percentage,
    CAST(NULL AS INT64) as minb_loans,
    CAST(NULL AS FLOAT64) as minb_percentage
WHERE FALSE
"""
    
    geoid5_list = "', '".join([str(g).zfill(5) for g in assessment_area_geoids])
    years_list = "', '".join([str(y) for y in years])
    
    # Build filter conditions dynamically (same as subject query)
    loan_purpose_filter = ""
    if loan_purpose:
        if ',' in loan_purpose:
            purposes = [p.strip() for p in loan_purpose.split(',')]
            purpose_list = "', '".join(purposes)
            loan_purpose_filter = f"AND h.loan_purpose IN ('{purpose_list}')"
        else:
            loan_purpose_filter = f"AND h.loan_purpose = '{loan_purpose.strip()}'"
    
    # Build action_taken filter
    action_taken_filter = ""
    if action_taken:
        if ',' in action_taken:
            actions = [a.strip() for a in action_taken.split(',')]
            action_list = "', '".join(actions)
            action_taken_filter = f"AND h.action_taken IN ('{action_list}')"
        else:
            action_taken_filter = f"AND h.action_taken = '{action_taken.strip()}'"
    
    # Build occupancy_type filter
    occupancy_filter = ""
    if occupancy_type:
        if ',' in occupancy_type:
            # Multiple occupancy types
            occupancies = [o.strip() for o in occupancy_type.split(',')]
            occupancy_list = "', '".join(occupancies)
            occupancy_filter = f"AND h.occupancy_type IN ('{occupancy_list}')"
        else:
            # Single occupancy type
            occupancy_filter = f"AND h.occupancy_type = '{occupancy_type.strip()}'"
    
    # Build total_units filter
    units_filter = ""
    if total_units:
        # Handle range notation like '1-4' → expand to '1','2','3','4'
        if '-' in total_units and ',' not in total_units:
            try:
                parts = total_units.split('-')
                start, end = int(parts[0].strip()), int(parts[1].strip())
                units = [str(i) for i in range(start, end + 1)]
            except (ValueError, IndexError):
                units = [total_units.strip()]
        elif ',' in total_units:
            units = [u.strip() for u in total_units.split(',')]
        else:
            units = [total_units.strip()]

        if len(units) == 1:
            units_filter = f"AND h.total_units = '{units[0]}'"
        else:
            units_list = "', '".join(units)
            units_filter = f"AND h.total_units IN ('{units_list}')"

    # Build construction_method filter
    construction_filter = ""
    if construction_method:
        if ',' in construction_method:
            # Multiple construction methods
            constructions = [c.strip() for c in construction_method.split(',')]
            construction_list = "', '".join(constructions)
            construction_filter = f"AND h.construction_method IN ('{construction_list}')"
        else:
            # Single construction method
            construction_filter = f"AND h.construction_method = '{construction_method.strip()}'"
    
    # Build reverse_mortgage filter
    reverse_filter = ""
    if not_reverse:
        if ',' in not_reverse:
            # Multiple values - if includes '1' (Not Reverse), exclude reverse mortgages
            reverse_values = [r.strip() for r in not_reverse.split(',')]
            if '1' in reverse_values and '2' not in reverse_values:
                # Only "Not Reverse" selected
                reverse_filter = "AND h.reverse_mortgage != '1'"
            elif '2' in reverse_values and '1' not in reverse_values:
                # Only "Reverse Mortgage" selected
                reverse_filter = "AND h.reverse_mortgage = '1'"
            # If both selected, no filter (include all)
        else:
            # Single value
            if not_reverse == '1':
                reverse_filter = "AND h.reverse_mortgage != '1'"
            elif not_reverse == '2':
                reverse_filter = "AND h.reverse_mortgage = '1'"

    # Build peer group filter based on selection
    # Note: HMDA LAR data doesn't include agency_code directly.
    # Peer filtering by institution type would require joining with institution metadata.
    # For now, we only support volume-based filtering and "all lenders".
    if peer_group == 'all_banks':
        # All lenders (cannot filter by agency type without institution metadata join)
        peer_type_filter = ""
        volume_filter = ""  # No volume filter
    elif peer_group == 'all_credit_unions':
        # All lenders (cannot filter by agency type without institution metadata join)
        peer_type_filter = ""
        volume_filter = ""  # No volume filter
    elif peer_group == 'all_mortgage_companies':
        # All lenders (cannot filter by agency type without institution metadata join)
        peer_type_filter = ""
        volume_filter = ""  # No volume filter
    elif peer_group == 'all_lenders':
        # All lenders - no agency or volume filter
        peer_type_filter = ""
        volume_filter = ""
    else:
        # Default: volume_50_200 - 50%-200% of subject volume
        peer_type_filter = ""
        volume_filter = "AND al.lender_vol >= sv.subject_vol * 0.5 AND al.lender_vol <= sv.subject_vol * 2.0"

    query = load_sql("mergermeter_hmda_peer.sql").format(action_taken_filter=action_taken_filter, construction_filter=construction_filter, geoid5_list=geoid5_list, loan_purpose_filter=loan_purpose_filter, occupancy_filter=occupancy_filter, peer_type_filter=peer_type_filter, reverse_filter=reverse_filter, subject_lei=subject_lei, units_filter=units_filter, volume_filter=volume_filter, years_list=years_list)
    return query


def build_sb_subject_query(
    sb_respondent_ids,
    assessment_area_geoids: list,
    years: list
) -> str:
    """
    Build Small Business query for subject bank.

    Args:
        sb_respondent_ids: Bank's SB Respondent ID(s) - string or list of strings
        assessment_area_geoids: List of GEOID5 codes (5-digit strings)
        years: List of years as strings

    Returns:
        SQL query string
    """
    if not assessment_area_geoids:
        return f"""
SELECT
    CAST(NULL AS STRING) as year,
    CAST(NULL AS STRING) as cbsa_code,
    CAST(NULL AS STRING) as cbsa_name,
    CAST(NULL AS INT64) as sb_loans_total,
    CAST(NULL AS FLOAT64) as sb_loans_amount,
    CAST(NULL AS INT64) as lmict_count,
    CAST(NULL AS FLOAT64) as lmict_loans_amount,
    CAST(NULL AS INT64) as loans_rev_under_1m_count,
    CAST(NULL AS FLOAT64) as amount_rev_under_1m,
    CAST(NULL AS FLOAT64) as avg_sb_lmict_loan_amount,
    CAST(NULL AS FLOAT64) as avg_loan_amt_rum_sb
WHERE FALSE
"""

    geoid5_list = "', '".join([str(g).zfill(5) for g in assessment_area_geoids])
    years_list = "', '".join([str(y) for y in years])

    # Build respondent_id IN clause from all IDs
    if isinstance(sb_respondent_ids, str):
        sb_respondent_ids = [sb_respondent_ids]
    all_ids = set()
    for sid in sb_respondent_ids:
        all_ids.add(sid)
        if '-' in sid:
            all_ids.add(sid.split('-', 1)[-1])
    id_list = "', '".join(all_ids)
    
    query = load_sql("mergermeter_sb_subject.sql").format(geoid5_list=geoid5_list, id_list=id_list, years_list=years_list)
    return query


def build_branch_query(
    subject_rssd: str,
    assessment_area_geoids: list,
    year: int = 2025
) -> str:
    """
    Build branch query for a subject bank by assessment area.
    
    Args:
        subject_rssd: Bank's RSSD ID (string)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings) for assessment area counties
        year: Year for branch data (default: 2025)
    
    Returns:
        SQL query string ready for BigQuery
    
    Note:
        - Queries branches in assessment area counties
        - Calculates total branches, LMICT branches, and MMCT branches
        - Aggregates by assessment area (all counties combined)
    """
    
    # Format GEOID5 list - convert to strings with proper padding
    geoid5_list = [str(g).zfill(5) for g in assessment_area_geoids]
    geoid5_str = ', '.join([f"'{g}'" for g in geoid5_list])
    
    query = load_sql("mergermeter_branch.sql").format(geoid5_str=geoid5_str, subject_rssd=subject_rssd, year=year)
    
    return query


def build_branch_market_query(
    subject_rssd: str,
    assessment_area_geoids: list,
    year: int = 2025
) -> str:
    """
    Build branch query for all OTHER banks (market) in the same CBSAs as the subject bank.
    
    Args:
        subject_rssd: Subject bank's RSSD ID (string) - will be excluded
        assessment_area_geoids: List of GEOID5 codes (5-digit strings) for assessment area counties
        year: Year for branch data (default: 2025)
    
    Returns:
        SQL query string ready for BigQuery that returns aggregated branch data for all other banks
    """
    
    # Format GEOID5 list - convert to strings with proper padding
    geoid5_list = [str(g).zfill(5) for g in assessment_area_geoids]
    geoid5_str = ', '.join([f"'{g}'" for g in geoid5_list])
    
    query = load_sql("mergermeter_branch_market.sql").format(geoid5_str=geoid5_str, subject_rssd=subject_rssd, year=year)
    
    return query


def build_branch_details_query(
    subject_rssd: str,
    assessment_area_geoids: list,
    year: int = 2025
) -> str:
    """
    Build query for individual branch details (address, city, state, zip, etc.).
    
    Args:
        subject_rssd: Bank's RSSD ID (string)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings) for assessment area counties
        year: Year for branch data (default: 2025)
    
    Returns:
        SQL query string ready for BigQuery that returns individual branch records
    """
    
    # Format GEOID5 list - convert to strings with proper padding
    geoid5_list = [str(g).zfill(5) for g in assessment_area_geoids]
    geoid5_str = ', '.join([f"'{g}'" for g in geoid5_list])
    
    query = load_sql("mergermeter_branch_details.sql").format(geoid5_str=geoid5_str, subject_rssd=subject_rssd, year=year)
    
    return query


def build_sb_peer_query(
    sb_respondent_ids,
    assessment_area_geoids: list,
    years: list
) -> str:
    """
    Build Small Business query for peer banks (50%-200% volume rule).

    Args:
        sb_respondent_ids: Subject bank's SB Respondent ID(s) - string or list of strings
        assessment_area_geoids: List of GEOID5 codes (5-digit strings)
        years: List of years as strings

    Returns:
        SQL query string
    """
    if not assessment_area_geoids:
        return f"""
SELECT
    CAST(NULL AS STRING) as year,
    CAST(NULL AS STRING) as cbsa_code,
    CAST(NULL AS STRING) as cbsa_name,
    CAST(NULL AS INT64) as sb_loans_total,
    CAST(NULL AS FLOAT64) as sb_loans_amount,
    CAST(NULL AS INT64) as lmict_count,
    CAST(NULL AS FLOAT64) as lmict_loans_amount,
    CAST(NULL AS INT64) as loans_rev_under_1m_count,
    CAST(NULL AS FLOAT64) as amount_rev_under_1m,
    CAST(NULL AS FLOAT64) as avg_sb_lmict_loan_amount,
    CAST(NULL AS FLOAT64) as avg_loan_amt_rum_sb
WHERE FALSE
"""

    geoid5_list = "', '".join([str(g).zfill(5) for g in assessment_area_geoids])
    years_list = "', '".join([str(y) for y in years])

    # Build respondent_id IN clause from all IDs
    if isinstance(sb_respondent_ids, str):
        sb_respondent_ids = [sb_respondent_ids]
    all_ids = set()
    for sid in sb_respondent_ids:
        all_ids.add(sid)
        if '-' in sid:
            all_ids.add(sid.split('-', 1)[-1])
    id_list = "', '".join(all_ids)
    
    query = load_sql("mergermeter_sb_peer.sql").format(geoid5_list=geoid5_list, id_list=id_list, years_list=years_list)
    return query

