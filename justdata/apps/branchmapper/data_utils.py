#!/usr/bin/env python3
"""
BranchMapper-specific data utilities for BigQuery and county reference.
"""

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from typing import List, Optional, Dict
from justdata.apps.branchmapper.config import PROJECT_ID

# App name for per-app credential support
APP_NAME = 'BRANCHMAPPER'


def find_exact_county_match(county_input: str) -> list:
    """
    Find all possible county matches from the database.
    
    Args:
        county_input: County input in format "County, State" or "County State"
    
    Returns:
        List of possible county names from database (empty if none found)
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        
        # Parse county and state
        if ',' in county_input:
            county_name, state = county_input.split(',', 1)
            county_name = county_name.strip()
            state = state.strip()
        else:
            parts = county_input.strip().split()
            if len(parts) >= 2:
                state = parts[-1]
                county_name = ' '.join(parts[:-1])
            else:
                county_name = county_input.strip()
                state = None
        
        # Escape apostrophes in SQL (replace ' with '')
        county_name_escaped = county_name.replace("'", "''")
        state_escaped = state.replace("'", "''") if state else None
        
        # Build query to find matches - use parameterized approach or escape properly
        if state:
            county_query = f"""
            SELECT DISTINCT county_state 
            FROM geo.cbsa_to_county 
            WHERE LOWER(county_state) LIKE LOWER('%{county_name_escaped}%')
            AND LOWER(county_state) LIKE LOWER('%{state_escaped}%')
            ORDER BY county_state
            """
        else:
            county_query = f"""
            SELECT DISTINCT county_state 
            FROM geo.cbsa_to_county 
            WHERE LOWER(county_state) LIKE LOWER('%{county_name_escaped}%')
            ORDER BY county_state
            """
        
        county_job = client.query(county_query)
        county_results = list(county_job.result())
        matches = [row.county_state for row in county_results]
        return matches
    except Exception as e:
        print(f"Error finding county match for {county_input}: {e}")
        return []


def get_available_counties() -> List[str]:
    """Get list of available counties from the database."""
    try:
        print("Attempting to connect to BigQuery...")
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
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
        return get_fallback_counties()


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
    """
    Get list of all available states from the database.
    
    Returns:
        List of dictionaries with 'name' and 'code' keys
    """
    try:
        print("Attempting to get states from BigQuery...")
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        query = """
        SELECT DISTINCT 
            TRIM(SPLIT(county_state, ',')[SAFE_OFFSET(1)]) as state_name
        FROM geo.cbsa_to_county 
        WHERE county_state LIKE '%,%'
        ORDER BY state_name
        """
        print("Executing state query...")
        query_job = client.query(query)
        results = query_job.result()
        states = []
        for row in results:
            if row.state_name:
                states.append({'name': row.state_name, 'code': row.state_name})
        print(f"Fetched {len(states)} states from BigQuery")
        return states
    except Exception as e:
        print(f"BigQuery not available for states: {e}")
        print("Using fallback state list...")
        return get_fallback_states()


def get_fallback_states() -> List[Dict[str, str]]:
    """Get a comprehensive fallback list of all US states."""
    states = [
        {'name': 'Alabama', 'code': 'Alabama'},
        {'name': 'Alaska', 'code': 'Alaska'},
        {'name': 'Arizona', 'code': 'Arizona'},
        {'name': 'Arkansas', 'code': 'Arkansas'},
        {'name': 'California', 'code': 'California'},
        {'name': 'Colorado', 'code': 'Colorado'},
        {'name': 'Connecticut', 'code': 'Connecticut'},
        {'name': 'Delaware', 'code': 'Delaware'},
        {'name': 'District of Columbia', 'code': 'District of Columbia'},
        {'name': 'Florida', 'code': 'Florida'},
        {'name': 'Georgia', 'code': 'Georgia'},
        {'name': 'Hawaii', 'code': 'Hawaii'},
        {'name': 'Idaho', 'code': 'Idaho'},
        {'name': 'Illinois', 'code': 'Illinois'},
        {'name': 'Indiana', 'code': 'Indiana'},
        {'name': 'Iowa', 'code': 'Iowa'},
        {'name': 'Kansas', 'code': 'Kansas'},
        {'name': 'Kentucky', 'code': 'Kentucky'},
        {'name': 'Louisiana', 'code': 'Louisiana'},
        {'name': 'Maine', 'code': 'Maine'},
        {'name': 'Maryland', 'code': 'Maryland'},
        {'name': 'Massachusetts', 'code': 'Massachusetts'},
        {'name': 'Michigan', 'code': 'Michigan'},
        {'name': 'Minnesota', 'code': 'Minnesota'},
        {'name': 'Mississippi', 'code': 'Mississippi'},
        {'name': 'Missouri', 'code': 'Missouri'},
        {'name': 'Montana', 'code': 'Montana'},
        {'name': 'Nebraska', 'code': 'Nebraska'},
        {'name': 'Nevada', 'code': 'Nevada'},
        {'name': 'New Hampshire', 'code': 'New Hampshire'},
        {'name': 'New Jersey', 'code': 'New Jersey'},
        {'name': 'New Mexico', 'code': 'New Mexico'},
        {'name': 'New York', 'code': 'New York'},
        {'name': 'North Carolina', 'code': 'North Carolina'},
        {'name': 'North Dakota', 'code': 'North Dakota'},
        {'name': 'Ohio', 'code': 'Ohio'},
        {'name': 'Oklahoma', 'code': 'Oklahoma'},
        {'name': 'Oregon', 'code': 'Oregon'},
        {'name': 'Pennsylvania', 'code': 'Pennsylvania'},
        {'name': 'Puerto Rico', 'code': 'Puerto Rico'},
        {'name': 'Rhode Island', 'code': 'Rhode Island'},
        {'name': 'South Carolina', 'code': 'South Carolina'},
        {'name': 'South Dakota', 'code': 'South Dakota'},
        {'name': 'Tennessee', 'code': 'Tennessee'},
        {'name': 'Texas', 'code': 'Texas'},
        {'name': 'Utah', 'code': 'Utah'},
        {'name': 'Vermont', 'code': 'Vermont'},
        {'name': 'Virginia', 'code': 'Virginia'},
        {'name': 'Washington', 'code': 'Washington'},
        {'name': 'West Virginia', 'code': 'West Virginia'},
        {'name': 'Wisconsin', 'code': 'Wisconsin'},
        {'name': 'Wyoming', 'code': 'Wyoming'}
    ]
    return states


def get_available_metro_areas() -> List[Dict[str, str]]:
    """
    Get list of all available metro areas (CBSAs) from the database.
    
    Returns:
        List of dictionaries with 'name' and 'code' keys
    """
    try:
        print("Attempting to get metro areas from BigQuery...")
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        query = """
        SELECT DISTINCT 
            cbsa_code,
            cbsa_name
        FROM geo.cbsa_to_county 
        WHERE cbsa_code IS NOT NULL
        AND cbsa_name IS NOT NULL
        ORDER BY cbsa_name
        """
        print("Executing metro areas query...")
        query_job = client.query(query)
        results = query_job.result()
        metros = []
        for row in results:
            if row.cbsa_code and row.cbsa_name:
                metros.append({'name': row.cbsa_name, 'code': row.cbsa_code})
        print(f"Fetched {len(metros)} metro areas from BigQuery")
        return metros
    except Exception as e:
        print(f"BigQuery not available for metro areas: {e}")
        print("Using empty metro areas list...")
        return []


def execute_branch_query(sql_template: str, county: str, year: int) -> List[dict]:
    """
    Execute a BigQuery SQL query for branch data with parameter substitution.
    
    Args:
        sql_template: SQL query template with @county and @year parameters
        county: County name in "County, State" format
        year: Year as integer
        
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
        
        # Escape apostrophes in county name for SQL safety
        from justdata.shared.utils.bigquery_client import escape_sql_string
        exact_county_escaped = escape_sql_string(exact_county)
        
        # Substitute parameters in SQL template
        sql = sql_template.replace('@county', f"'{exact_county_escaped}'").replace('@year', f"'{year}'")
        
        # Execute query
        return execute_query(client, sql)
        
    except Exception as e:
        raise Exception(f"Error executing BigQuery query for {county} {year}: {e}")

