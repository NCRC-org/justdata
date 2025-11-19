#!/usr/bin/env python3
"""
BranchSeeker-specific data utilities for BigQuery and county reference.
"""

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from typing import List, Optional
from .config import PROJECT_ID


def find_exact_county_match(county_input: str) -> list:
    """
    Find all possible county matches from the database.
    
    Args:
        county_input: County input in format "County, State" or "County State"
    
    Returns:
        List of possible county names from database (empty if none found)
    """
    try:
        client = get_bigquery_client(PROJECT_ID)
        
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


def get_available_counties() -> List[str]:
    """Get list of available counties from the database."""
    try:
        print("📡 Attempting to connect to BigQuery...")
        client = get_bigquery_client(PROJECT_ID)
        query = """
        SELECT DISTINCT county_state 
        FROM geo.cbsa_to_county 
        ORDER BY county_state
        """
        print("🔍 Executing county query...")
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        print(f"✅ Fetched {len(counties)} counties from BigQuery")
        return counties
    except Exception as e:
        print(f"⚠️  BigQuery not available: {e}")
        print("📋 Returning empty list - BigQuery should be available")
        # Return empty list - BigQuery should always be available in production
        return []


def get_fallback_counties() -> List[str]:
    """Minimal fallback list - only for critical error cases."""
    from justdata.shared.utils.geo_data import get_fallback_counties as get_shared_fallback
    return get_shared_fallback()


def get_available_states() -> List[dict]:
    """
    Get list of available states from BigQuery using geo.states crosswalk table.
    
    Returns:
        List of dictionaries with 'code' (abbreviation) and 'name' (full name) keys
    """
    try:
        client = get_bigquery_client(PROJECT_ID)
        query = """
        SELECT DISTINCT 
            s.state_abbrv as code,
            s.state_name as name
        FROM geo.states s
        INNER JOIN geo.cbsa_to_county c ON s.state_name = c.state
        WHERE s.state_abbrv IS NOT NULL AND s.state_name IS NOT NULL
        ORDER BY s.state_name
        """
        query_job = client.query(query)
        results = query_job.result()
        states = [{"code": row.code, "name": row.name} for row in results if row.code and row.name]
        print(f"✅ Fetched {len(states)} states from BigQuery")
        return states
    except Exception as e:
        print(f"⚠️  BigQuery not available for states: {e}")
        print("📋 Using fallback state list...")
        from justdata.shared.utils.geo_data import get_us_states
        return get_us_states()


def get_available_metro_areas() -> List[dict]:
    """
    Get list of available metro areas (CBSAs).
    
    Returns:
        List of dictionaries with 'code' and 'name' keys
    """
    try:
        client = get_bigquery_client(PROJECT_ID)
        query = """
        SELECT DISTINCT 
            cbsa_code as code,
            cbsa_name as name
        FROM geo.cbsa_to_county 
        WHERE cbsa_code IS NOT NULL AND cbsa_name IS NOT NULL
        ORDER BY cbsa_name
        """
        query_job = client.query(query)
        results = query_job.result()
        metros = [{"code": row.code, "name": row.name} for row in results]
        print(f"✅ Fetched {len(metros)} metro areas from BigQuery")
        return metros
    except Exception as e:
        print(f"⚠️  BigQuery not available for metro areas: {e}")
        return []


def expand_state_to_counties(state_code: str) -> List[str]:
    """
    Get all counties for a given state from BigQuery.
    Uses geo.states crosswalk to resolve state abbreviations to full names.
    
    Args:
        state_code: State abbreviation (e.g., "MI", "CA") or full name (e.g., "Michigan", "California")
        
    Returns:
        List of county names in "County Name, State" format
    """
    try:
        client = get_bigquery_client(PROJECT_ID)
        # First, try to resolve state_code to state name using geo.states
        # If input is 2 characters, treat as abbreviation; otherwise treat as full name
            if len(state_code) == 2:
                # Match by abbreviation only
                state_name_query = f"""
                SELECT state_name
                FROM geo.states
                WHERE LOWER(state_abbrv) = LOWER('{state_code}')
                LIMIT 1
                """
            else:
                # Match by full name
                state_name_query = f"""
                SELECT state_name
                FROM geo.states
                WHERE LOWER(state_name) = LOWER('{state_code}')
                LIMIT 1
                """
            
            state_job = client.query(state_name_query)
            state_result = list(state_job.result())
            
            if state_result:
                state_name = state_result[0].state_name
        else:
            # Fallback: assume it's already a state name
            state_name = state_code
        
        # Query counties by state name
        query = f"""
        SELECT DISTINCT county_state
        FROM geo.cbsa_to_county 
        WHERE LOWER(state) = LOWER('{state_name}')
        ORDER BY county_state
        """
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        print(f"✅ Fetched {len(counties)} counties for state {state_code} ({state_name})")
        return counties
    except Exception as e:
        print(f"⚠️  Error fetching counties for state {state_code}: {e}")
        # Return empty list - BigQuery should always be available
        return []


def get_available_years() -> List[int]:
    """
    Get available years dynamically from branches.sod (latest year) and branches.sod_legacy (historical years).
    Both tables have the same schema.
    
    Returns:
        List of available years, sorted ascending
    """
    try:
        client = get_bigquery_client(PROJECT_ID)
        query = """
        SELECT DISTINCT year
        FROM (
            SELECT year FROM branches.sod WHERE year IS NOT NULL
            UNION DISTINCT
            SELECT year FROM branches.sod_legacy WHERE year IS NOT NULL
        )
        ORDER BY year ASC
        """
        query_job = client.query(query)
        results = query_job.result()
        years = [row.year for row in results]
        if years:
            print(f"✅ Fetched {len(years)} years from BigQuery: {min(years)}-{max(years)}")
        else:
            print("⚠️  No years found in BigQuery, using fallback")
            years = list(range(2017, 2026))
        return years
    except Exception as e:
        print(f"⚠️  BigQuery not available for years: {e}")
        print("📋 Using fallback year range...")
        return list(range(2017, 2026))  # 2017-2025 for branches


def expand_metro_to_counties(metro_code: str) -> List[str]:
    """
    Get all counties for a given metro area (CBSA).
    
    Args:
        metro_code: CBSA code (e.g., "12060" for Atlanta)
        
    Returns:
        List of county names in "County Name, State" format
    """
    try:
        client = get_bigquery_client(PROJECT_ID)
        query = f"""
        SELECT DISTINCT county_state
        FROM geo.cbsa_to_county 
        WHERE cbsa_code = '{metro_code}'
        ORDER BY county_state
        """
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        print(f"✅ Fetched {len(counties)} counties for metro {metro_code}")
        return counties
    except Exception as e:
        print(f"⚠️  Error fetching counties for metro {metro_code}: {e}")
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
        
        # Substitute parameters in SQL template
        sql = sql_template.replace('@county', f"'{exact_county}'").replace('@year', f"'{year}'")
        
        # Execute query
        return execute_query(client, sql)
        
    except Exception as e:
        raise Exception(f"Error executing BigQuery query for {county} {year}: {e}")

