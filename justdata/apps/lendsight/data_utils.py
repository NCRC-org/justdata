#!/usr/bin/env python3
"""
LendSight-specific data utilities for BigQuery and county reference.
Similar to BranchSeeker but for HMDA mortgage data.
"""

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from typing import List, Optional, Dict, Any
from .config import PROJECT_ID


def find_exact_county_match(county_input: str) -> list:
    """
    Find exact county match from the database using geoid5 for precise matching.
    
    Args:
        county_input: County input in format "County, State" (exact format from dropdown)
    
    Returns:
        List with single exact county match (or empty if none found)
    """
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        # Use exact match on county_state (since it comes from the dropdown, it should be exact)
        # Also match by geoid5 to ensure we get the exact county
        county_query = f"""
            SELECT DISTINCT county_state, geoid5
            FROM geo.cbsa_to_county 
            WHERE county_state = '{county_input}'
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
                    WHERE LOWER(county_state) = LOWER('{county_input}')
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


def get_available_counties() -> List[str]:
    """Get list of available counties from the database."""
    try:
        print("Attempting to connect to BigQuery...")
        client = get_bigquery_client(PROJECT_ID)
        query = """
        SELECT DISTINCT county_state 
        FROM geo.cbsa_to_county 
        ORDER BY county_state
        """
        print("Executing county query...")
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        print(f"Fetched {len(counties)} counties from BigQuery")
        return counties
    except Exception as e:
        print(f"BigQuery not available: {e}")
        print("Using fallback county list...")
        # Return fallback list
        return get_fallback_counties()


def get_last_5_years_hmda() -> List[int]:
    """
    Get the last 5 years dynamically from HMDA data (hmda.hmda).
    
    Returns:
        List of the 5 most recent years available, sorted descending (e.g., [2024, 2023, 2022, 2021, 2020])
    """
    try:
        client = get_bigquery_client(PROJECT_ID)
        query = f"""
        SELECT DISTINCT CAST(activity_year AS INT64) as year
        FROM `{PROJECT_ID}.hmda.hmda`
        WHERE activity_year IS NOT NULL
        ORDER BY year DESC
        LIMIT 5
        """
        query_job = client.query(query)
        results = query_job.result()
        years = [int(row.year) for row in results]
        if years:
            print(f"✅ Fetched last 5 HMDA years: {years}")
            return years
        else:
            # Fallback to recent years
            print("⚠️  No HMDA years found, using fallback")
            return list(range(2020, 2025))  # 2020-2024
    except Exception as e:
        print(f"Error fetching HMDA years: {e}")
        # Fallback to recent years
        return list(range(2020, 2025))  # 2020-2024


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
        client = get_bigquery_client(PROJECT_ID)
        
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
        client = get_bigquery_client(PROJECT_ID)
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
        client = get_bigquery_client(PROJECT_ID)
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
        client = get_bigquery_client(PROJECT_ID)
        
        # Find the exact county match from the database
        county_matches = find_exact_county_match(county)
        
        if not county_matches:
            raise Exception(f"No matching counties found for: {county}")
        
        # Use the first match
        exact_county = county_matches[0]
        
        # Convert loan_purpose list to comma-separated string for SQL
        if loan_purpose is None or len(loan_purpose) == 0 or set(loan_purpose) == {'purchase', 'refinance', 'equity'}:
            loan_purpose_str = 'all'
        else:
            loan_purpose_str = ','.join(sorted(loan_purpose))
        
        # Substitute parameters in SQL template
        sql = sql_template.replace('@county', f"'{exact_county}'").replace('@year', f"'{year}'").replace('@loan_purpose', f"'{loan_purpose_str}'")
        
        # Execute query
        return execute_query(client, sql)
        
    except Exception as e:
        raise Exception(f"Error executing BigQuery query for {county} {year}: {e}")

