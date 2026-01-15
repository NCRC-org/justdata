#!/usr/bin/env python3
"""
BranchSeeker-specific data utilities for BigQuery and county reference.
"""

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from typing import List, Optional, Dict
from justdata.apps.branchsight.config import PROJECT_ID


def find_exact_county_match(county_input: str) -> list:
    """
    Find all possible county matches from the database.

    Args:
        county_input: County input in format "County, State", "County State", or geoid5 FIPS code (e.g., "24031")

    Returns:
        List of possible county names from database (empty if none found)
    """
    try:
        client = get_bigquery_client(PROJECT_ID)

        # Check if input is a geoid5 (5-digit FIPS code)
        county_input_stripped = county_input.strip()
        if county_input_stripped.isdigit() and len(county_input_stripped) <= 5:
            # Treat as geoid5 FIPS code
            geoid5 = county_input_stripped.zfill(5)  # Pad to 5 digits if needed
            county_query = f"""
            SELECT DISTINCT county_state
            FROM geo.cbsa_to_county
            WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') = '{geoid5}'
            ORDER BY county_state
            """
            county_job = client.query(county_query)
            county_results = list(county_job.result())
            matches = [row.county_state for row in county_results]
            if matches:
                print(f"Found county match for geoid5 {geoid5}: {matches}")
                return matches
            else:
                print(f"No match found for geoid5 {geoid5}")

        # Parse county and state from text format
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

        # Build query to find matches
        if state:
            county_query = f"""
            SELECT DISTINCT county_state
            FROM geo.cbsa_to_county
            WHERE LOWER(county_state) LIKE LOWER('%{county_name}%')
            AND LOWER(county_state) LIKE LOWER('%{state}%')
            ORDER BY county_state
            """
        else:
            county_query = f"""
            SELECT DISTINCT county_state
            FROM geo.cbsa_to_county
            WHERE LOWER(county_state) LIKE LOWER('%{county_name}%')
            ORDER BY county_state
            """

        county_job = client.query(county_query)
        county_results = list(county_job.result())
        matches = [row.county_state for row in county_results]
        return matches
    except Exception as e:
        print(f"Error finding county match for {county_input}: {e}")
        return []


def get_available_counties() -> List[Dict[str, str]]:
    """Get list of available counties from the database with FIPS codes.
    
    Returns:
        List of dictionaries with 'name', 'geoid5', 'state_fips', 'county_fips'
    """
    try:
        print("Attempting to connect to BigQuery...")
        client = get_bigquery_client(PROJECT_ID)
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
    """
    Get list of all available US states with FIPS codes.
    
    Returns all 50 states + DC + territories with their FIPS codes.
    This ensures all states are visible in the dropdown regardless of database content.
    
    Returns:
        List of dictionaries with 'code' and 'name' keys (code is FIPS code)
    """
    # Use hardcoded list like LendSight for consistency and reliability
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
        # Filter counties by state (state_code can be FIPS code or state name)
        filtered = []
        for county in all_counties:
            # Handle both dict format (new) and string format (old/fallback)
            if isinstance(county, dict):
                county_name = county.get('name', '')
                state_fips = county.get('state_fips', '')
                # Check if state_code is a FIPS code (2 digits) or state name
                if state_code.isdigit() and len(state_code) <= 2:
                    # Match by state FIPS code
                    state_code_padded = state_code.zfill(2)
                    if state_fips and state_fips == state_code_padded:
                        filtered.append(county.get('name', ''))  # Return just the name for backward compatibility
                else:
                    # Match by state name
                    if ',' in county_name:
                        _, state_name = county_name.split(',', 1)
                        state_name = state_name.strip()
                        if state_name.lower() == state_code.lower():
                            filtered.append(county.get('name', ''))  # Return just the name for backward compatibility
            else:
                # Old format: string
                if ',' in county:
                    county_name, state_name = county.split(',', 1)
                    state_name = state_name.strip()
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
        client = get_bigquery_client(PROJECT_ID)
        
        # Find the exact county match from the database
        county_matches = find_exact_county_match(county)
        
        if not county_matches:
            raise Exception(f"No matching counties found for: {county}")
        
        # Use the first match
        exact_county = county_matches[0]
        
        # Escape apostrophes in county name for SQL safety
        from justdata.shared.utils.bigquery_client import escape_sql_string
        escaped_county = escape_sql_string(exact_county)
        
        # Substitute parameters in SQL template
        sql = sql_template.replace('@county', f"'{escaped_county}'").replace('@year', f"'{year}'")
        
        # Execute query
        return execute_query(client, sql)
        
    except Exception as e:
        raise Exception(f"Error executing BigQuery query for {county} {year}: {e}")

