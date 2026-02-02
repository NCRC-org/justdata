#!/usr/bin/env python3
"""
LendSight-specific data utilities for BigQuery and county reference.
Similar to BranchSight but for HMDA mortgage data.
"""

import os
from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
from typing import List, Optional, Dict, Any
from justdata.apps.lendsight.config import PROJECT_ID

# App name for per-app credential support
APP_NAME = 'LENDSIGHT'


def find_exact_county_match(county_input: str) -> list:
    """
    Find exact county match from the database using geoid5 for precise matching.
    
    Args:
        county_input: County input in format "County, State" (exact format from dropdown)
    
    Returns:
        List with single exact county match (or empty if none found)
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        
        # Use exact match on county_state (since it comes from the dropdown, it should be exact)
        # Also match by geoid5 to ensure we get the exact county
        # Escape apostrophes in county name for SQL safety
        escaped_county = escape_sql_string(county_input)
        county_query = f"""
            SELECT DISTINCT county_state, geoid5
            FROM geo.cbsa_to_county 
            WHERE county_state = '{escaped_county}'
            ORDER BY geoid5
            LIMIT 1
            """
        
        # Set job configuration with timeout
        from google.cloud.bigquery import QueryJobConfig
        
        job_config = QueryJobConfig()
        job_config.use_query_cache = True
        
        county_job = client.query(county_query, job_config=job_config)
        
        # Wait for results with timeout handling
        try:
            county_results = list(county_job.result(timeout=30))  # 30 second timeout
            if county_results:
                # Return exact match
                exact_match = county_results[0].county_state
                print(f"Found exact match for {county_input}: {exact_match} (geoid5: {county_results[0].geoid5})")
                return [exact_match]
            else:
                # If no exact match, try case-insensitive match
                print(f"No exact match found for {county_input}, trying case-insensitive match...")
                county_query_ci = f"""
                    SELECT DISTINCT county_state, geoid5
                    FROM geo.cbsa_to_county
                    WHERE LOWER(county_state) = LOWER('{escaped_county}')
                    ORDER BY geoid5
                    LIMIT 1
                    """
                county_job_ci = client.query(county_query_ci, job_config=job_config)
                county_results_ci = list(county_job_ci.result(timeout=30))
                if county_results_ci:
                    exact_match = county_results_ci[0].county_state
                    print(f"Found case-insensitive match for {county_input}: {exact_match} (geoid5: {county_results_ci[0].geoid5})")
                    return [exact_match]
                else:
                    # If no matches found, return the input as-is (fallback)
                    print(f"No BigQuery matches found for {county_input}, using input as-is")
                    return [county_input]
        except Exception as query_error:
            print(f"BigQuery query timeout or error for {county_input}: {query_error}")
            # Fallback: return the input county name
            return [county_input]
            
    except Exception as e:
        print(f"Error finding county match for {county_input}: {e}")
        # Fallback: if BigQuery is not available, use the input county name directly
        print(f"Using county input as-is: {county_input}")
        return [county_input]


def get_available_counties() -> List[Dict[str, str]]:
    """Get list of available counties from the database with FIPS codes.
    
    Returns:
        List of dictionaries with 'name', 'geoid5', 'state_fips', 'county_fips'
    """
    try:
        print("Attempting to connect to BigQuery...")
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        query = """
        SELECT DISTINCT 
            county_state,
            geoid5,
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as county_fips
        FROM geo.cbsa_to_county 
        WHERE geoid5 IS NOT NULL
            AND county_state IS NOT NULL
            AND TRIM(county_state) != ''
        ORDER BY county_state
        """
        print("Executing county query...")
        query_job = client.query(query)
        results = query_job.result()
        counties = []
        seen_geoids = set()  # Track unique GEOIDs to avoid duplicates
        for row in results:
            geoid5 = str(row.geoid5).zfill(5) if row.geoid5 else None
            if geoid5 and geoid5 in seen_geoids:
                continue
            if geoid5:
                seen_geoids.add(geoid5)
            counties.append({
                'name': row.county_state,
                'geoid5': geoid5,
                'state_fips': row.state_fips,
                'county_fips': row.county_fips
            })
        print(f"Fetched {len(counties)} counties from BigQuery")
        return counties
    except Exception as e:
        print(f"BigQuery not available: {e}")
        print("Using fallback county list...")
        # Return fallback list (convert to standard format)
        fallback_strings = get_fallback_counties()
        # Convert fallback strings to dict format (without geoid5 since we don't have it)
        return [{'name': county, 'geoid5': None, 'state_fips': None, 'county_fips': None} 
                for county in fallback_strings]


def get_fallback_counties() -> List[str]:
    """Get a fallback list of counties for local development when BigQuery is not available."""
    return [
        "Montgomery County, Maryland",
        "Prince George's County, Maryland",
        "Baltimore County, Maryland",
        "Anne Arundel County, Maryland",
        "Los Angeles County, California",
        "San Diego County, California",
        "Orange County, California",
        "Cook County, Illinois",
        "DuPage County, Illinois",
        "Lake County, Illinois",
        "Harris County, Texas",
        "Dallas County, Texas",
        "Tarrant County, Texas",
        "Miami-Dade County, Florida",
        "Broward County, Florida",
        "Palm Beach County, Florida",
        "King County, Washington",
        "Pierce County, Washington",
        "Maricopa County, Arizona",
        "Pima County, Arizona",
        "New York County, New York",
        "Kings County, New York",
        "Queens County, New York",
        "Bronx County, New York",
        "Nassau County, New York",
        "Suffolk County, New York",
        "Philadelphia County, Pennsylvania",
        "Allegheny County, Pennsylvania",
        "Montgomery County, Pennsylvania",
        "Fulton County, Georgia",
        "Gwinnett County, Georgia",
        "Cobb County, Georgia",
        "Wayne County, Michigan",
        "Oakland County, Michigan",
        "Cuyahoga County, Ohio",
        "Franklin County, Ohio",
        "Hamilton County, Ohio"
    ]


def get_available_states() -> List[Dict[str, str]]:
    """Get list of all available US states.
    
    Returns all 50 states + DC + territories with their FIPS codes.
    This ensures all states are visible in the dropdown regardless of database content.
    
    Returns:
        List of dictionaries with 'code' and 'name'
    """
    # Complete list of all US states, DC, and territories with FIPS codes
    all_states = [
        {'code': '01', 'name': 'Alabama'}, {'code': '02', 'name': 'Alaska'},
        {'code': '04', 'name': 'Arizona'}, {'code': '05', 'name': 'Arkansas'},
        {'code': '06', 'name': 'California'}, {'code': '08', 'name': 'Colorado'},
        {'code': '09', 'name': 'Connecticut'}, {'code': '10', 'name': 'Delaware'},
        {'code': '11', 'name': 'District of Columbia'}, {'code': '12', 'name': 'Florida'},
        {'code': '13', 'name': 'Georgia'}, {'code': '15', 'name': 'Hawaii'},
        {'code': '16', 'name': 'Idaho'}, {'code': '17', 'name': 'Illinois'},
        {'code': '18', 'name': 'Indiana'}, {'code': '19', 'name': 'Iowa'},
        {'code': '20', 'name': 'Kansas'}, {'code': '21', 'name': 'Kentucky'},
        {'code': '22', 'name': 'Louisiana'}, {'code': '23', 'name': 'Maine'},
        {'code': '24', 'name': 'Maryland'}, {'code': '25', 'name': 'Massachusetts'},
        {'code': '26', 'name': 'Michigan'}, {'code': '27', 'name': 'Minnesota'},
        {'code': '28', 'name': 'Mississippi'}, {'code': '29', 'name': 'Missouri'},
        {'code': '30', 'name': 'Montana'}, {'code': '31', 'name': 'Nebraska'},
        {'code': '32', 'name': 'Nevada'}, {'code': '33', 'name': 'New Hampshire'},
        {'code': '34', 'name': 'New Jersey'}, {'code': '35', 'name': 'New Mexico'},
        {'code': '36', 'name': 'New York'}, {'code': '37', 'name': 'North Carolina'},
        {'code': '38', 'name': 'North Dakota'}, {'code': '39', 'name': 'Ohio'},
        {'code': '40', 'name': 'Oklahoma'}, {'code': '41', 'name': 'Oregon'},
        {'code': '42', 'name': 'Pennsylvania'}, {'code': '44', 'name': 'Rhode Island'},
        {'code': '45', 'name': 'South Carolina'}, {'code': '46', 'name': 'South Dakota'},
        {'code': '47', 'name': 'Tennessee'}, {'code': '48', 'name': 'Texas'},
        {'code': '49', 'name': 'Utah'}, {'code': '50', 'name': 'Vermont'},
        {'code': '51', 'name': 'Virginia'}, {'code': '53', 'name': 'Washington'},
        {'code': '54', 'name': 'West Virginia'}, {'code': '55', 'name': 'Wisconsin'},
        {'code': '56', 'name': 'Wyoming'},
        # Territories
        {'code': '60', 'name': 'American Samoa'}, {'code': '66', 'name': 'Guam'},
        {'code': '69', 'name': 'Northern Mariana Islands'}, {'code': '72', 'name': 'Puerto Rico'},
        {'code': '78', 'name': 'U.S. Virgin Islands'}
    ]
    
    print(f"Returning all {len(all_states)} US states and territories")
    return all_states


def get_available_metro_areas() -> List[Dict[str, Any]]:
    """Get list of available metro areas (CBSAs) from the database.
    
    Returns:
        List of dictionaries with 'cbsa_code', 'cbsa_name', and 'counties' (list of county names)
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        
        test_query = """
        SELECT 
            CAST(cbsa_code AS STRING) as cbsa_code,
            cbsa_name,
            ARRAY_AGG(DISTINCT county_state ORDER BY county_state) as counties
        FROM geo.cbsa_to_county
        WHERE cbsa_code IS NOT NULL 
            AND cbsa_name IS NOT NULL
            AND TRIM(cbsa_name) != ''
        GROUP BY cbsa_code, cbsa_name
        ORDER BY cbsa_name
        LIMIT 100
        """
        
        print("Executing metro areas query...")
        query_job = client.query(test_query)
        results = query_job.result()
        
        metros = []
        row_count = 0
        for row in results:
            row_count += 1
            # Handle potential NULL values
            cbsa_code = str(row.cbsa_code) if row.cbsa_code is not None else ''
            cbsa_name = str(row.cbsa_name).strip() if row.cbsa_name is not None else ''
            
            # Only add if we have both code and name
            if cbsa_code and cbsa_name:
                counties_list = list(row.counties) if row.counties is not None else []
                metros.append({
                    'code': cbsa_code,
                    'name': cbsa_name,
                    'counties': counties_list
                })
        
        print(f"Fetched {row_count} rows, {len(metros)} valid metro areas from BigQuery")
        return metros
    except Exception as e:
        print(f"Error fetching metro areas: {e}")
        import traceback
        traceback.print_exc()
        return []


def expand_state_to_counties(state_code: str) -> List[str]:
    """Expand a state code to a list of counties in that state.
    
    geoid5 structure: First 2 digits = state FIPS code, next 3 digits = county FIPS code
    
    Args:
        state_code: Two-digit state FIPS code (e.g., '24' for Maryland)
    
    Returns:
        List of county names in "County, State" format
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        # Ensure state_code is zero-padded to 2 digits
        state_code_padded = state_code.zfill(2)
        query = f"""
        SELECT DISTINCT county_state
        FROM geo.cbsa_to_county
        WHERE SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) = '{state_code_padded}'
        ORDER BY county_state
        """
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        print(f"Expanded state {state_code_padded} to {len(counties)} counties")
        return counties
    except Exception as e:
        print(f"Error expanding state to counties: {e}")
        import traceback
        traceback.print_exc()
        return []


def expand_metro_to_counties(cbsa_code: str) -> List[str]:
    """Expand a CBSA metro area code to a list of counties in that metro area.
    
    Args:
        cbsa_code: CBSA code (e.g., '47900' for Washington-Arlington-Alexandria)
    
    Returns:
        List of county names in "County, State" format
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        # Cast cbsa_code to string for comparison (it might be stored as integer)
        query = f"""
        SELECT DISTINCT county_state
        FROM geo.cbsa_to_county
        WHERE CAST(cbsa_code AS STRING) = '{cbsa_code}'
        ORDER BY county_state
        """
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        print(f"Expanded metro {cbsa_code} to {len(counties)} counties")
        return counties
    except Exception as e:
        print(f"Error expanding metro to counties: {e}")
        import traceback
        traceback.print_exc()
        return []


def execute_mortgage_query(sql_template: str, county: str, year: int, loan_purpose: list = None) -> List[dict]:
    """
    Execute a BigQuery SQL query for mortgage data with parameter substitution.
    
    Args:
        sql_template: SQL query template with @county, @year, and @loan_purpose parameters
        county: County name in "County, State" format
        year: Year as integer
        loan_purpose: List of loan purpose filters (['purchase', 'refinance', 'equity']) or None for all
        
    Returns:
        List of dictionaries containing query results
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        
        # Find the exact county match from the database
        county_matches = find_exact_county_match(county)
        
        if not county_matches:
            raise Exception(f"No matching counties found for: {county}")
        
        # Use the first match
        exact_county = county_matches[0]
        
        # Escape apostrophes in county name for SQL (double them)
        escaped_county = escape_sql_string(exact_county)
        
        # Convert loan_purpose list to comma-separated string for SQL
        if loan_purpose is None or len(loan_purpose) == 0 or set(loan_purpose) == {'purchase', 'refinance', 'equity'}:
            loan_purpose_str = 'all'
        else:
            loan_purpose_str = ','.join(sorted(loan_purpose))
        
        # Substitute parameters in SQL template (escape apostrophes in county name)
        # Note: year is an integer, so don't wrap it in quotes
        sql = sql_template.replace('@county', f"'{escaped_county}'").replace('@year', f"{year}").replace('@loan_purpose', f"'{loan_purpose_str}'")
        
        # Execute query
        return execute_query(client, sql)
        
    except Exception as e:
        raise Exception(f"Error executing BigQuery query for {county} {year}: {e}")


# =============================================================================
# TIERED SUMMARY TABLE QUERIES (for ~99% cost reduction)
# =============================================================================

# Configuration for summary tables - can switch between old and new project
SUMMARY_PROJECT_ID = os.environ.get('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
USE_SUMMARY_TABLES = os.environ.get('USE_SUMMARY_TABLES', 'true').lower() == 'true'


def execute_county_summary_query(county: str, year: int, loan_purpose: list = None) -> List[dict]:
    """
    Query the pre-aggregated county summary table for ~99% cost reduction.
    
    Used for: Demographic Overview, Income Borrowers, Top Lenders, Market Concentration,
              Summary, Trends sections.
    
    Args:
        county: County name in "County, State" format
        year: Year as integer
        loan_purpose: List of loan purpose filters or None for all
        
    Returns:
        List of dictionaries containing county-level aggregated results
    """
    try:
        client = get_bigquery_client(SUMMARY_PROJECT_ID)
        
        # Find the exact county match
        county_matches = find_exact_county_match(county)
        if not county_matches:
            raise Exception(f"No matching counties found for: {county}")
        
        exact_county = county_matches[0]
        escaped_county = escape_sql_string(exact_county)
        
        # Convert loan_purpose to filter string
        if loan_purpose is None or len(loan_purpose) == 0 or set(loan_purpose) == {'purchase', 'refinance', 'equity'}:
            loan_purpose_str = 'all'
        else:
            loan_purpose_str = ','.join(sorted(loan_purpose))
        
        # Build loan purpose filter
        if loan_purpose_str == 'all':
            purpose_filter = "1=1"  # No filter
        else:
            purpose_conditions = []
            if 'purchase' in loan_purpose_str:
                purpose_conditions.append("loan_purpose = '1'")
            if 'refinance' in loan_purpose_str:
                purpose_conditions.append("loan_purpose IN ('31','32')")
            if 'equity' in loan_purpose_str:
                purpose_conditions.append("loan_purpose IN ('2','4')")
            purpose_filter = f"({' OR '.join(purpose_conditions)})" if purpose_conditions else "1=1"
        
        sql = f"""
        SELECT
            lei,
            year,
            geoid5,
            county_state,
            loan_purpose,
            lender_name,
            total_originations,
            hispanic_originations,
            black_originations,
            asian_originations,
            white_originations,
            native_american_originations,
            hopi_originations,
            multi_racial_originations,
            lmib_originations,
            low_income_borrower_originations,
            moderate_income_borrower_originations,
            middle_income_borrower_originations,
            upper_income_borrower_originations,
            lmict_originations,
            mmct_originations,
            total_loan_amount,
            avg_loan_amount,
            avg_property_value,
            avg_interest_rate,
            avg_total_loan_costs,
            avg_origination_charges,
            loans_with_demographic_data
        FROM `{SUMMARY_PROJECT_ID}.lendsight.de_hmda_county_summary`
        WHERE county_state = '{escaped_county}'
            AND year = {year}
            AND {purpose_filter}
        ORDER BY lender_name, year
        """
        
        return execute_query(client, sql)
        
    except Exception as e:
        raise Exception(f"Error executing county summary query for {county} {year}: {e}")


def execute_tract_summary_query(county: str, year: int, loan_purpose: list = None) -> List[dict]:
    """
    Query the pre-aggregated tract summary table for minority/income tract sections.
    
    Used for: Minority Tracts table (dynamic quartile calculation),
              Income Tracts table (tract-level income breakdown)
    
    Note: This query adds placeholder columns (0 values) for columns that exist in
    the county summary but not in the tract summary. This ensures the report builder
    can process the data without errors.
    
    Args:
        county: County name in "County, State" format
        year: Year as integer
        loan_purpose: List of loan purpose filters or None for all
        
    Returns:
        List of dictionaries containing tract-level aggregated results
    """
    try:
        client = get_bigquery_client(SUMMARY_PROJECT_ID)
        
        # Find the exact county match
        county_matches = find_exact_county_match(county)
        if not county_matches:
            raise Exception(f"No matching counties found for: {county}")
        
        exact_county = county_matches[0]
        escaped_county = escape_sql_string(exact_county)
        
        # Convert loan_purpose to filter string
        if loan_purpose is None or len(loan_purpose) == 0 or set(loan_purpose) == {'purchase', 'refinance', 'equity'}:
            loan_purpose_str = 'all'
        else:
            loan_purpose_str = ','.join(sorted(loan_purpose))
        
        # Build loan purpose filter
        if loan_purpose_str == 'all':
            purpose_filter = "1=1"
        else:
            purpose_conditions = []
            if 'purchase' in loan_purpose_str:
                purpose_conditions.append("loan_purpose = '1'")
            if 'refinance' in loan_purpose_str:
                purpose_conditions.append("loan_purpose IN ('31','32')")
            if 'equity' in loan_purpose_str:
                purpose_conditions.append("loan_purpose IN ('2','4')")
            purpose_filter = f"({' OR '.join(purpose_conditions)})" if purpose_conditions else "1=1"
        
        # Query includes placeholder columns (0) for columns in county summary but not tract summary
        # This ensures report builder compatibility
        sql = f"""
        SELECT
            lei,
            year,
            geoid5,
            county_state,
            tract_code,
            tract_minority_population_percent,
            tract_to_msa_income_percentage,
            loan_purpose,
            lender_name,
            total_originations,
            -- Race/ethnicity columns (some are placeholders)
            hispanic_originations,
            black_originations,
            asian_originations,
            white_originations,
            0 as native_american_originations,  -- Placeholder: not in tract summary
            0 as hopi_originations,              -- Placeholder: not in tract summary
            0 as multi_racial_originations,      -- Placeholder: not in tract summary
            -- Borrower income columns (placeholders - not in tract summary)
            0 as lmib_originations,
            0 as low_income_borrower_originations,
            0 as moderate_income_borrower_originations,
            0 as middle_income_borrower_originations,
            0 as upper_income_borrower_originations,
            -- Tract income columns
            lmict_originations,
            low_income_tract_originations,
            moderate_income_tract_originations,
            middle_income_tract_originations,
            upper_income_tract_originations,
            mmct_originations,
            -- Loan metrics
            total_loan_amount,
            0.0 as avg_loan_amount,              -- Placeholder: not in tract summary
            0.0 as avg_property_value,           -- Placeholder: not in tract summary
            0.0 as avg_interest_rate,            -- Placeholder: not in tract summary
            0.0 as avg_total_loan_costs,         -- Placeholder: not in tract summary
            0.0 as avg_origination_charges,      -- Placeholder: not in tract summary
            0 as loans_with_demographic_data     -- Placeholder: not in tract summary
        FROM `{SUMMARY_PROJECT_ID}.lendsight.de_hmda_tract_summary`
        WHERE county_state = '{escaped_county}'
            AND year = {year}
            AND {purpose_filter}
        ORDER BY lender_name, tract_code, year
        """
        
        return execute_query(client, sql)
        
    except Exception as e:
        raise Exception(f"Error executing tract summary query for {county} {year}: {e}")


def execute_tiered_queries(county: str, years: List[int], loan_purpose: list = None) -> Dict[str, List[dict]]:
    """
    Execute tiered queries for a county across multiple years.
    Returns both county-level and tract-level data for the report builder.
    
    This is the main entry point for tiered summary table queries.
    Falls back to the original mortgage_report.sql if summary tables are not available.
    
    Args:
        county: County name in "County, State" format
        years: List of years
        loan_purpose: List of loan purpose filters or None for all
        
    Returns:
        Dictionary with 'county_data' and 'tract_data' keys
    """
    county_results = []
    tract_results = []
    
    for year in years:
        try:
            # Query county summary
            county_data = execute_county_summary_query(county, year, loan_purpose)
            county_results.extend(county_data)
            print(f"  [TIERED] County summary: {len(county_data)} rows for {county} {year}")
        except Exception as e:
            print(f"  [TIERED] County summary error for {county} {year}: {e}")
        
        try:
            # Query tract summary
            tract_data = execute_tract_summary_query(county, year, loan_purpose)
            tract_results.extend(tract_data)
            print(f"  [TIERED] Tract summary: {len(tract_data)} rows for {county} {year}")
        except Exception as e:
            print(f"  [TIERED] Tract summary error for {county} {year}: {e}")
    
    return {
        'county_data': county_results,
        'tract_data': tract_results
    }

