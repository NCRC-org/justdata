#!/usr/bin/env python3
"""
Query builders for DataExplorer 2.0
Fixed query logic with proper SQL injection protection and correct filters.
"""

from typing import List, Optional, Dict, Any
from justdata.shared.utils.bigquery_client import escape_sql_string
from justdata.apps.dataexplorer.config import (
    PROJECT_ID, HMDA_DATASET, HMDA_TABLE,
    SB_DATASET, SB_DISCLOSURE_TABLE, SB_AGGREGATE_TABLE,
    BRANCHES_DATASET, BRANCHES_TABLE,
    DEFAULT_ACTION_TAKEN, DEFAULT_EXCLUDE_REVERSE_MORTGAGE_CODES,
    MAX_YEARS, MAX_GEOIDS
)


def validate_inputs(years: List[int] = None, geoids: List[str] = None):
    """
    Validate input parameters to prevent resource exhaustion.
    
    Args:
        years: List of years
        geoids: List of GEOIDs (counties/tracts)
        
    Raises:
        ValueError: If inputs exceed limits
    """
    if years and len(years) > MAX_YEARS:
        raise ValueError(f"Maximum {MAX_YEARS} years allowed per query. Received {len(years)} years.")
    
    if geoids and len(geoids) > MAX_GEOIDS:
        raise ValueError(f"Maximum {MAX_GEOIDS} GEOIDs allowed per query. Received {len(geoids)} GEOIDs.")


def build_hmda_query(
    geoids: List[str],
    years: List[int],
    action_taken: List[str] = None,
    loan_purpose: List[str] = None,
    occupancy: List[str] = None,
    total_units: List[str] = None,
    construction: List[str] = None,
    property_type: List[str] = None,
    exclude_reverse_mortgages: bool = True,
    lender_id: str = None,
    min_loan_amount: float = None,
    max_loan_amount: float = None
) -> str:
    """
    Build HMDA query with proper filters and SQL injection protection.

    Default filters match the mortgage_report.sql template:
    - action_taken = '1' (originations only)
    - occupancy_type = '1' (owner-occupied)
    - total_units IN ('1','2','3','4') (1-4 family)
    - construction_method = '1' (site-built)
    - reverse_mortgage != '1' (exclude reverse mortgages)

    Args:
        geoids: List of GEOIDs (county FIPS codes)
        years: List of years
        action_taken: List of action taken codes (default: ['1'] for originations only)
        loan_purpose: List of loan purpose codes
        occupancy: List of occupancy codes (default: ['1'] for owner-occupied)
        total_units: List of total unit codes (default: ['1','2','3','4'] for 1-4 family)
        construction: List of construction method codes (default: ['1'] for site-built)
        property_type: List of property type codes
        exclude_reverse_mortgages: Whether to exclude reverse mortgages
        lender_id: Optional lender LEI to filter by
        min_loan_amount: Minimum loan amount filter
        max_loan_amount: Maximum loan amount filter

    Returns:
        SQL query string
    """
    # Validate inputs
    validate_inputs(years=years, geoids=geoids)

    # Default to originations only
    if action_taken is None:
        action_taken = DEFAULT_ACTION_TAKEN

    # Default to owner-occupied
    if occupancy is None:
        occupancy = ['1']

    # Default to 1-4 family
    if total_units is None:
        total_units = ['1', '2', '3', '4']

    # Default to site-built
    if construction is None:
        construction = ['1']

    # Build WHERE clauses
    where_clauses = []

    # GEOID filter (properly escaped)
    if geoids:
        escaped_geoids = [f"'{escape_sql_string(str(geoid))}'" for geoid in geoids]
        where_clauses.append(f"county_code IN ({','.join(escaped_geoids)})")

    # Year filter
    if years:
        year_list = ','.join([str(int(year)) for year in years])
        where_clauses.append(f"activity_year IN ({year_list})")

    # Action taken filter
    if action_taken:
        if len(action_taken) == 1 and action_taken[0] == '1':
            where_clauses.append("action_taken = '1'")
        else:
            escaped_codes = [f"'{escape_sql_string(str(code))}'" for code in action_taken]
            where_clauses.append(f"action_taken IN ({','.join(escaped_codes)})")

    # Reverse mortgage filter: Exclude only '1' (reverse mortgages); '1111' (exempt) is included
    if exclude_reverse_mortgages:
        excluded_codes = [f"'{escape_sql_string(str(code))}'" for code in DEFAULT_EXCLUDE_REVERSE_MORTGAGE_CODES]
        where_clauses.append(f"reverse_mortgage NOT IN ({','.join(excluded_codes)})")

    # Loan purpose filter
    if loan_purpose:
        escaped_purposes = [f"'{escape_sql_string(str(purpose))}'" for purpose in loan_purpose]
        where_clauses.append(f"loan_purpose IN ({','.join(escaped_purposes)})")

    # Occupancy filter
    if occupancy:
        escaped_occupancy = [f"'{escape_sql_string(str(occ))}'" for occ in occupancy]
        where_clauses.append(f"occupancy_type IN ({','.join(escaped_occupancy)})")

    # Total units filter
    if total_units:
        escaped_units = [f"'{escape_sql_string(str(u))}'" for u in total_units]
        where_clauses.append(f"total_units IN ({','.join(escaped_units)})")

    # Construction method filter
    if construction:
        escaped_construction = [f"'{escape_sql_string(str(c))}'" for c in construction]
        where_clauses.append(f"construction_method IN ({','.join(escaped_construction)})")

    # Property type filter
    if property_type:
        escaped_property_types = [f"'{escape_sql_string(str(pt))}'" for pt in property_type]
        where_clauses.append(f"property_type IN ({','.join(escaped_property_types)})")

    # Lender filter
    if lender_id:
        escaped_lender_id = escape_sql_string(str(lender_id))
        where_clauses.append(f"lei = '{escaped_lender_id}'")

    # Loan amount filters
    if min_loan_amount is not None:
        where_clauses.append(f"loan_amount >= {float(min_loan_amount)}")
    if max_loan_amount is not None:
        where_clauses.append(f"loan_amount <= {float(max_loan_amount)}")
    
    # Build query
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    query = f"""
    SELECT 
        activity_year as year,
        county_code as geoid,
        lei as lender_id,
        loan_amount,
        loan_purpose,
        action_taken,
        occupancy_type,
        property_type,
        reverse_mortgage,
        applicant_ethnicity_1,
        applicant_race_1,
        applicant_sex,
        income,
        tract_code,
        state_code,
        county_name,
        lender_name
    FROM `{PROJECT_ID}.{HMDA_DATASET}.{HMDA_TABLE}`
    WHERE {where_clause}
    ORDER BY activity_year DESC, county_code, lei
    """
    
    return query


def build_sb_query(
    geoids: List[str],
    years: List[int],
    lender_id: str = None,
    min_loan_amount: float = None,
    max_loan_amount: float = None
) -> str:
    """
    Build Small Business (Section 1071) query with proper SQL injection protection.
    
    Args:
        geoids: List of GEOIDs (county FIPS codes)
        years: List of years
        lender_id: Optional lender LEI to filter by
        min_loan_amount: Minimum loan amount filter
        max_loan_amount: Maximum loan amount filter
        
    Returns:
        SQL query string
    """
    # Validate inputs
    validate_inputs(years=years, geoids=geoids)
    
    # Build WHERE clauses
    where_clauses = []
    
    # GEOID filter
    if geoids:
        escaped_geoids = [f"'{escape_sql_string(str(geoid))}'" for geoid in geoids]
        where_clauses.append(f"county_code IN ({','.join(escaped_geoids)})")
    
    # Year filter
    if years:
        year_list = ','.join([str(int(year)) for year in years])
        where_clauses.append(f"activity_year IN ({year_list})")
    
    # Lender filter
    if lender_id:
        escaped_lender_id = escape_sql_string(str(lender_id))
        where_clauses.append(f"lei = '{escaped_lender_id}'")
    
    # Loan amount filters
    if min_loan_amount is not None:
        where_clauses.append(f"loan_amount >= {float(min_loan_amount)}")
    if max_loan_amount is not None:
        where_clauses.append(f"loan_amount <= {float(max_loan_amount)}")
    
    # Build query
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    query = f"""
    SELECT 
        activity_year as year,
        county_code as geoid,
        lei as lender_id,
        loan_amount,
        tract_code,
        state_code,
        county_name,
        lender_name,
        number_of_loans,
        number_of_borrowers
    FROM `{PROJECT_ID}.{SB_DATASET}.{SB_DISCLOSURE_TABLE}`
    WHERE {where_clause}
    ORDER BY activity_year DESC, county_code, lei
    """
    
    return query


def build_branch_query(
    geoids: List[str] = None,
    years: List[int] = None,
    lender_id: str = None,
    state: str = None,
    county: str = None
) -> str:
    """
    Build Branch (FDIC SOD) query with proper SQL injection protection.
    
    FIXED ISSUES FROM V1:
    - Proper year filtering (not forced to 2025)
    - Proper SQL escaping for county/state names
    - Deterministic ORDER BY clauses
    
    Args:
        geoids: List of GEOIDs (county FIPS codes)
        years: List of years
        lender_id: Optional lender RSSD ID to filter by
        state: Optional state name (properly escaped)
        county: Optional county name (properly escaped)
        
    Returns:
        SQL query string
    """
    # Validate inputs
    validate_inputs(years=years, geoids=geoids)
    
    # Build WHERE clauses
    where_clauses = []
    
    # GEOID filter
    if geoids:
        escaped_geoids = [f"'{escape_sql_string(str(geoid))}'" for geoid in geoids]
        where_clauses.append(f"county_code IN ({','.join(escaped_geoids)})")
    
    # Year filter - FIXED: Proper year filtering (not forced to 2025)
    if years:
        year_list = ','.join([str(int(year)) for year in years])
        where_clauses.append(f"year IN ({year_list})")
    
    # Lender filter
    if lender_id:
        escaped_lender_id = escape_sql_string(str(lender_id))
        where_clauses.append(f"rssd_id = '{escaped_lender_id}'")
    
    # State filter (properly escaped)
    if state:
        escaped_state = escape_sql_string(str(state))
        where_clauses.append(f"state = '{escaped_state}'")
    
    # County filter (properly escaped)
    if county:
        escaped_county = escape_sql_string(str(county))
        where_clauses.append(f"county_name = '{escaped_county}'")
    
    # Build query
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    query = f"""
    SELECT 
        year,
        rssd_id as lender_id,
        state,
        state_code,
        county_name,
        county_code as geoid,
        branch_name,
        branch_address,
        deposits,
        service_type
    FROM `{PROJECT_ID}.{BRANCHES_DATASET}.{BRANCHES_TABLE}`
    WHERE {where_clause}
    ORDER BY year DESC, state_code, county_code, rssd_id, branch_name
    """
    
    return query


def build_lender_lookup_query(lender_name: str, exact_match: bool = False) -> str:
    """
    Build lender lookup query with proper SQL injection protection.
    
    FIXED ISSUES FROM V1:
    - Deterministic ORDER BY clause
    - Proper SQL escaping
    - Query hmda.hmda table and group by LEI to get distinct lenders
    
    Args:
        lender_name: Lender name to search for
        exact_match: Whether to use exact match or LIKE search
        
    Returns:
        SQL query string
    """
    escaped_name = escape_sql_string(str(lender_name))
    
    if exact_match:
        where_clause = f"lender_name = '{escaped_name}'"
    else:
        where_clause = f"LOWER(lender_name) LIKE LOWER('%{escaped_name}%')"
    
    # Query hmda.hmda table and group by LEI to get distinct lenders
    # Use most recent year's data for better accuracy
    query = f"""
    SELECT 
        lei as lender_id,
        MAX(lender_name) as lender_name,
        'HMDA' as source
    FROM `{PROJECT_ID}.{HMDA_DATASET}.{HMDA_TABLE}`
    WHERE {where_clause}
      AND lender_name IS NOT NULL
      AND lei IS NOT NULL
    GROUP BY lei
    ORDER BY lender_name, lei
    LIMIT 100
    """
    
    return query
