#!/usr/bin/env python3
"""
BranchSight-specific data utilities for BigQuery and county reference.
Adapted from ncrc-test-apps branchsight.
"""

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
from typing import List, Optional, Dict
from .config import PROJECT_ID

# App name for per-app credential support
APP_NAME = 'BRANCHSIGHT'


def find_exact_county_match(county_input: str) -> list:
    """
    Find all possible county matches from the database.
    Handles Connecticut planning regions and counties specially.

    Args:
        county_input: County input in format "County, State" or "County State"
                     OR Connecticut planning region name

    Returns:
        List of possible county names from database (empty if none found)
        For Connecticut planning regions, returns all counties in that region
    """
    try:
        # Check if this is a Connecticut planning region or county
        from justdata.shared.utils.connecticut_county_mapper import (
            is_planning_region,
            normalize_connecticut_selection,
            get_connecticut_county_name
        )

        is_ct_planning_region = is_planning_region(county_input)
        is_ct_county = ', Connecticut' in county_input or county_input.endswith(', CT')

        if is_ct_planning_region:
            # Return all counties in this planning region
            normalized_name, selection_type, county_fips_list = normalize_connecticut_selection(county_input)
            county_names = [get_connecticut_county_name(fips) + ', Connecticut'
                          for fips in county_fips_list if get_connecticut_county_name(fips)]
            if county_names:
                print(f"Connecticut planning region '{county_input}' maps to counties: {county_names}")
                return county_names

        if is_ct_county:
            # For Connecticut counties, verify and return the county name
            normalized_name, selection_type, county_fips_list = normalize_connecticut_selection(county_input)
            if county_fips_list:
                county_name = get_connecticut_county_name(county_fips_list[0])
                if county_name:
                    result = [f"{county_name}, Connecticut"]
                    print(f"Connecticut county '{county_input}' normalized to: {result[0]}")
                    return result

        # For non-Connecticut counties, use BigQuery lookup
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

        # Escape apostrophes in county and state names for SQL
        escaped_county_name = escape_sql_string(county_name)
        escaped_state = escape_sql_string(state) if state else None

        # Build query to find matches
        if state:
            county_query = f"""
            SELECT DISTINCT county_state
        FROM shared.cbsa_to_county
        WHERE LOWER(county_state) LIKE LOWER('%{escaped_county_name}%')
        AND LOWER(county_state) LIKE LOWER('%{escaped_state}%')
        ORDER BY county_state
            """
        else:
            county_query = f"""
            SELECT DISTINCT county_state
        FROM shared.cbsa_to_county
        WHERE LOWER(county_state) LIKE LOWER('%{escaped_county_name}%')
        ORDER BY county_state
            """

        county_job = client.query(county_query)
        county_results = list(county_job.result())
        matches = [row.county_state for row in county_results]
        return matches
    except Exception as e:
        print(f"Error finding county match for {county_input}: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_available_counties() -> List[str]:
    """Get list of available counties from the database."""
    try:
        print("Attempting to connect to BigQuery...")
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        query = """
        SELECT DISTINCT county_state
        FROM shared.cbsa_to_county
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
        FROM shared.cbsa_to_county
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


def expand_state_to_counties(state_code: str) -> List[str]:
    """
    Expand a state code/name to a list of counties in that state.

    Args:
        state_code: State name (e.g., "Delaware", "Maryland")

    Returns:
        List of county names in "County, State" format
    """
    try:
        all_counties = get_available_counties()
        # Filter counties by state name (state_code is the state name from the dropdown)
        # County format is "County Name, State"
        filtered = []
        for county in all_counties:
            if ',' in county:
                county_name, state_name = county.split(',', 1)
                state_name = state_name.strip()
                # Match by state name (case-insensitive)
                if state_name.lower() == state_code.lower():
                    filtered.append(county)
        return filtered
    except Exception as e:
        print(f"Error expanding state to counties: {e}")
        return []


def expand_metro_to_counties(metro_code: str) -> List[str]:
    """
    Expand a metro area code to a list of counties in that metro area.

    Args:
        metro_code: Metro area/CBSA code

    Returns:
        List of county names in "County, State" format
    """
    try:
        # For now, return empty list as metro expansion is not yet implemented
        # This can be implemented by querying the geo.cbsa_to_county table
        print(f"Metro expansion not yet implemented for code: {metro_code}")
        return []
    except Exception as e:
        print(f"Error expanding metro to counties: {e}")
        return []


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
            cbsa_name as metro_name,
            cbsa_code as metro_code
        FROM shared.cbsa_to_county
        WHERE cbsa_name IS NOT NULL AND cbsa_code IS NOT NULL
        ORDER BY cbsa_name
        """
        print("Executing metro areas query...")
        query_job = client.query(query)
        results = query_job.result()
        metros = []
        for row in results:
            if row.metro_name and row.metro_code:
                metros.append({'name': row.metro_name, 'code': str(row.metro_code)})
        print(f"Fetched {len(metros)} metro areas from BigQuery")
        return metros
    except Exception as e:
        print(f"BigQuery not available for metro areas: {e}")
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
        escaped_county = escape_sql_string(exact_county)

        # Substitute parameters in SQL template
        sql = sql_template.replace('@county', f"'{escaped_county}'").replace('@year', f"'{year}'")

        # Execute query
        return execute_query(client, sql)

    except Exception as e:
        raise Exception(f"Error executing BigQuery query for {county} {year}: {e}")


def get_available_years() -> List[int]:
    """
    Get list of available years from the FDIC SOD data.

    Returns:
        List of years as integers
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        query = """
        SELECT DISTINCT year
        FROM branchsight.sod
        WHERE year IS NOT NULL
        ORDER BY year DESC
        """
        query_job = client.query(query)
        results = query_job.result()
        years = [int(row.year) for row in results]
        print(f"Fetched {len(years)} years from BigQuery: {years}")
        return years
    except Exception as e:
        print(f"BigQuery not available for years: {e}")
        # Return fallback years
        return list(range(2025, 2016, -1))  # 2025 down to 2017
