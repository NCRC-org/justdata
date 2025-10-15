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
        print("📋 Using fallback county list...")
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

