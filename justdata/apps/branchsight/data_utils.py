#!/usr/bin/env python3
"""
BranchSight-specific data utilities for BigQuery and county reference.
Adapted from ncrc-test-apps branchsight.
"""

from justdata.shared.utils.bigquery_client import get_bigquery_client, escape_sql_string
from functools import lru_cache
from typing import List, Dict
from .config import PROJECT_ID

# App name for per-app credential support
APP_NAME = 'BRANCHSIGHT'


def exact_county_matches(client, county_input: str) -> List[str]:
    """county_state values equal to county_input, ignoring case."""
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    job_config = QueryJobConfig(query_parameters=[
        ScalarQueryParameter('county', 'STRING', county_input.strip())])
    rows = client.query(
        "SELECT DISTINCT county_state FROM shared.cbsa_to_county "
        "WHERE LOWER(county_state) = LOWER(@county) ORDER BY county_state",
        job_config=job_config).result()
    return [row.county_state for row in rows]


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

        # The picker sends the exact county_state, so match it exactly first.
        # A substring match is wrong for 35 counties: "Kansas" is inside
        # "Arkansas" and "Smith County" inside "Deaf Smith County", and the
        # first sorted match was used (Johnson County, Kansas ran as Johnson
        # County, Arkansas).
        exact = exact_county_matches(client, county_input)
        if exact:
            return exact[:1]

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
        # Free-text input only: an ambiguous substring match is not a match.
        return matches if len(matches) == 1 else []
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
        # This can be implemented by querying the shared.cbsa_to_county table
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


def execute_branch_query(sql_template: str, county: str, years: List[int]) -> List[dict]:
    """
    Run the branch query for one county and all its years in one BigQuery job.

    Args:
        sql_template: SQL with @county (STRING) and @years (ARRAY<STRING>)
                      query parameters
        county: Exact county_state, as resolved by find_exact_county_match
        years: Years to include

    Returns:
        List of dictionaries containing query results
    """
    from google.cloud.bigquery import ArrayQueryParameter, QueryJobConfig, ScalarQueryParameter
    client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
    job_config = QueryJobConfig(query_parameters=[
        ScalarQueryParameter('county', 'STRING', county),
        ArrayQueryParameter('years', 'STRING', [str(y) for y in years]),
    ])
    rows = client.query(sql_template, job_config=job_config).result(timeout=120)
    return [dict(row.items()) for row in rows]


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


# ACS 5-year vintage for the Geography Context table (the page states it).
TRACT_CONTEXT_ACS_YEAR = 2022


@lru_cache(maxsize=512)
def tract_context(geoid5: str) -> Dict:
    """Census tract counts and population for one county, by LMI and
    majority-minority status (ACS 5-year, TRACT_CONTEXT_ACS_YEAR).

    LMI: tract median family income at or below 80% of the county median.
    Majority-minority: people other than non-Hispanic white residents are
    more than 50% of the tract population. Tracts with no population are
    left out. The Census API requires a key, so this runs on the server.
    """
    import requests
    from justdata.shared.utils.census_historical_utils import _get_census_api_key as get_census_api_key

    key = get_census_api_key()
    if not key:
        raise RuntimeError('CENSUS_API_KEY is not set')
    st, co = geoid5[:2], geoid5[2:]
    base = f'https://api.census.gov/data/{TRACT_CONTEXT_ACS_YEAR}/acs/acs5'
    tracts = requests.get(base, timeout=20, params={
        'get': 'B01003_001E,B19113_001E,B03002_001E,B03002_003E',
        'for': 'tract:*', 'in': f'state:{st} county:{co}', 'key': key}).json()
    county = requests.get(base, timeout=20, params={
        'get': 'B19113_001E', 'for': f'county:{co}', 'in': f'state:{st}', 'key': key}).json()
    median = float(county[1][0] or 0)
    threshold = median * 0.8
    groups = {k: {'tracts': 0, 'population': 0} for k in ('all', 'lmi_only', 'mmct_only', 'both')}
    for row in tracts[1:]:
        pop = float(row[0] or 0)
        if pop <= 0:
            continue
        income = float(row[1] or 0)
        race_total, white = float(row[2] or 0), float(row[3] or 0)
        is_lmi = 0 < income <= threshold
        is_mmct = race_total > 0 and (race_total - white) / race_total * 100 > 50
        key_ = 'both' if is_lmi and is_mmct else 'lmi_only' if is_lmi else 'mmct_only' if is_mmct else None
        for k in ('all', key_):
            if k:
                groups[k]['tracts'] += 1
                groups[k]['population'] += int(pop)
    return {'acs_year': TRACT_CONTEXT_ACS_YEAR, 'county_median_family_income': median,
            'lmi_threshold': threshold, 'groups': groups}
