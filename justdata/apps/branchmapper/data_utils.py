#!/usr/bin/env python3
"""
BranchMapper-specific data utilities for BigQuery and county reference.
"""

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from typing import List, Optional, Dict
from justdata.apps.branchmapper.config import PROJECT_ID

# App name for per-app credential support
APP_NAME = 'BRANCHMAPPER'

# Cache for FIPS lookups
_fips_cache = {}


def get_county_fips(county_state: str) -> Optional[Dict[str, str]]:
    """Look up state FIPS and county FIPS from a county_state string.

    Args:
        county_state: e.g. "Montgomery County, Maryland"

    Returns:
        {'state_fips': '24', 'county_fips': '031'} or None
    """
    if county_state in _fips_cache:
        return _fips_cache[county_state]

    # Try BigQuery first
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        query = """
        SELECT DISTINCT
            SUBSTR(geoid5, 1, 2) as state_fips,
            SUBSTR(geoid5, 3, 3) as county_fips
        FROM shared.cbsa_to_county
        WHERE county_state = @county_state
        LIMIT 1
        """
        from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("county_state", "STRING", county_state)
            ]
        )
        result = list(client.query(query, job_config=job_config).result())
        if result:
            fips = {
                'state_fips': result[0].state_fips,
                'county_fips': result[0].county_fips
            }
            _fips_cache[county_state] = fips
            return fips
    except Exception as e:
        print(f"BigQuery FIPS lookup failed for {county_state}: {e}")

    # Fallback: use Census FIPS lookup via us library or hardcoded map
    fips = _get_fallback_fips(county_state)
    if fips:
        _fips_cache[county_state] = fips
    return fips


# Fallback FIPS codes for counties in the fallback county list
_FALLBACK_FIPS = {
    "Montgomery County, Maryland": ("24", "031"),
    "Prince George's County, Maryland": ("24", "033"),
    "Baltimore County, Maryland": ("24", "005"),
    "Anne Arundel County, Maryland": ("24", "003"),
    "Los Angeles County, California": ("06", "037"),
    "San Diego County, California": ("06", "073"),
    "Orange County, California": ("06", "059"),
    "Cook County, Illinois": ("17", "031"),
    "DuPage County, Illinois": ("17", "043"),
    "Lake County, Illinois": ("17", "097"),
    "Harris County, Texas": ("48", "201"),
    "Dallas County, Texas": ("48", "113"),
    "Tarrant County, Texas": ("48", "439"),
    "Miami-Dade County, Florida": ("12", "086"),
    "Broward County, Florida": ("12", "011"),
    "Palm Beach County, Florida": ("12", "099"),
    "King County, Washington": ("53", "033"),
    "Pierce County, Washington": ("53", "053"),
    "Maricopa County, Arizona": ("04", "013"),
    "Pima County, Arizona": ("04", "019"),
    "New York County, New York": ("36", "061"),
    "Kings County, New York": ("36", "047"),
    "Queens County, New York": ("36", "081"),
    "Bronx County, New York": ("36", "005"),
    "Nassau County, New York": ("36", "059"),
    "Suffolk County, New York": ("36", "103"),
    "Philadelphia County, Pennsylvania": ("42", "101"),
    "Allegheny County, Pennsylvania": ("42", "003"),
    "Montgomery County, Pennsylvania": ("42", "091"),
    "Fulton County, Georgia": ("13", "121"),
    "Gwinnett County, Georgia": ("13", "135"),
    "Cobb County, Georgia": ("13", "067"),
    "Wayne County, Michigan": ("26", "163"),
    "Oakland County, Michigan": ("26", "125"),
    "Cuyahoga County, Ohio": ("39", "035"),
    "Franklin County, Ohio": ("39", "049"),
    "Hamilton County, Ohio": ("39", "061"),
    "Hillsborough County, Florida": ("12", "057"),
    "Duval County, Florida": ("12", "031"),
    "Orange County, Florida": ("12", "095"),
    "Pinellas County, Florida": ("12", "103"),
}


def _get_fallback_fips(county_state: str) -> Optional[Dict[str, str]]:
    """Fallback FIPS lookup from hardcoded map."""
    entry = _FALLBACK_FIPS.get(county_state)
    if entry:
        return {'state_fips': entry[0], 'county_fips': entry[1]}
    return None


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
            FROM shared.cbsa_to_county 
            WHERE LOWER(county_state) LIKE LOWER('%{county_name_escaped}%')
            AND LOWER(county_state) LIKE LOWER('%{state_escaped}%')
            ORDER BY county_state
            """
        else:
            county_query = f"""
            SELECT DISTINCT county_state 
            FROM shared.cbsa_to_county 
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


def get_all_bank_names() -> List[str]:
    """Get all unique bank names from the current SOD table.

    Returns:
        Sorted list of distinct bank names
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        query = """
        SELECT DISTINCT bank_name
        FROM branchsight.sod
        WHERE bank_name IS NOT NULL
        ORDER BY bank_name
        """
        result = list(client.query(query).result())
        return [row.bank_name for row in result]
    except Exception as e:
        print(f"Error getting bank names: {e}")
        return []


def execute_national_bank_query(bank_name: str, year: int) -> List[dict]:
    """Execute a BigQuery query for all branches of a specific bank nationwide.

    Args:
        bank_name: Exact bank name to match
        year: Year as integer

    Returns:
        List of dictionaries containing query results
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

        sql = """
        SELECT
            s.bank_name,
            s.year,
            s.geoid5,
            c.county_state,
            s.uninumbr,
            1 as total_branches,
            MAX(s.br_lmi) as lmict,
            MAX(s.br_minority) as mmct,
            COALESCE(SUM(COALESCE(s.deposits_000s, 0) * 1000), 0) as total_deposits,
            MAX(s.address) as address,
            MAX(s.city) as city,
            MAX(s.county) as county,
            MAX(s.state) as state,
            MAX(s.state_abbrv) as state_abbrv,
            MAX(s.zip) as zip,
            MAX(s.service_type) as service_type,
            MAX(s.branch_name) as branch_name,
            MAX(s.latitude) as latitude,
            MAX(s.longitude) as longitude,
            MAX(s.rssd) as rssd,
            MAX(s.assets_000s) as assets_000s
        FROM branchsight.sod s
        LEFT JOIN shared.cbsa_to_county c
            USING(geoid5)
        WHERE s.bank_name = @bank_name
            AND s.year = @year
        GROUP BY 1,2,3,4,5
        UNION ALL
        SELECT
            s.bank_name,
            s.year,
            s.geoid5,
            c.county_state,
            s.uninumbr,
            1 as total_branches,
            MAX(s.br_lmi) as lmict,
            MAX(s.br_minority) as mmct,
            COALESCE(SUM(COALESCE(s.deposits_000s, 0) * 1000), 0) as total_deposits,
            MAX(s.address) as address,
            MAX(s.city) as city,
            MAX(s.county) as county,
            MAX(s.state) as state,
            MAX(s.state_abbrv) as state_abbrv,
            MAX(s.zip) as zip,
            MAX(s.service_type) as service_type,
            MAX(s.branch_name) as branch_name,
            MAX(s.latitude) as latitude,
            MAX(s.longitude) as longitude,
            MAX(s.rssd) as rssd,
            MAX(s.assets_000s) as assets_000s
        FROM branchsight.sod_legacy s
        LEFT JOIN shared.cbsa_to_county c
            USING(geoid5)
        WHERE s.bank_name = @bank_name
            AND s.year = @year
        GROUP BY 1,2,3,4,5
        ORDER BY bank_name, county_state, year
        """

        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("bank_name", "STRING", bank_name),
                ScalarQueryParameter("year", "STRING", str(year))
            ]
        )

        results = list(client.query(sql, job_config=job_config).result())
        return [dict(row) for row in results]

    except Exception as e:
        raise Exception(f"Error executing national bank query for {bank_name}: {e}")


def execute_bounds_query(sw_lat, sw_lng, ne_lat, ne_lng, year):
    """Query all branches within a geographic bounding box.

    Args:
        sw_lat, sw_lng: Southwest corner coordinates
        ne_lat, ne_lng: Northeast corner coordinates
        year: Year as integer (will be converted to string for query)

    Returns:
        List of dictionaries containing branch data
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

        sql = """
        SELECT
            s.bank_name,
            s.year,
            s.geoid5,
            c.county_state,
            s.uninumbr,
            1 as total_branches,
            MAX(s.br_lmi) as lmict,
            MAX(s.br_minority) as mmct,
            COALESCE(SUM(COALESCE(s.deposits_000s, 0) * 1000), 0) as total_deposits,
            MAX(s.address) as address,
            MAX(s.city) as city,
            MAX(s.county) as county,
            MAX(s.state) as state,
            MAX(s.state_abbrv) as state_abbrv,
            MAX(s.zip) as zip,
            MAX(s.service_type) as service_type,
            MAX(s.branch_name) as branch_name,
            MAX(s.latitude) as latitude,
            MAX(s.longitude) as longitude,
            MAX(s.rssd) as rssd,
            MAX(s.assets_000s) as assets_000s
        FROM branchsight.sod s
        LEFT JOIN shared.cbsa_to_county c
            USING(geoid5)
        WHERE SAFE_CAST(s.latitude AS FLOAT64) BETWEEN @sw_lat AND @ne_lat
            AND SAFE_CAST(s.longitude AS FLOAT64) BETWEEN @sw_lng AND @ne_lng
            AND s.year = @year
        GROUP BY 1,2,3,4,5
        UNION ALL
        SELECT
            s.bank_name,
            s.year,
            s.geoid5,
            c.county_state,
            s.uninumbr,
            1 as total_branches,
            MAX(s.br_lmi) as lmict,
            MAX(s.br_minority) as mmct,
            COALESCE(SUM(COALESCE(s.deposits_000s, 0) * 1000), 0) as total_deposits,
            MAX(s.address) as address,
            MAX(s.city) as city,
            MAX(s.county) as county,
            MAX(s.state) as state,
            MAX(s.state_abbrv) as state_abbrv,
            MAX(s.zip) as zip,
            MAX(s.service_type) as service_type,
            MAX(s.branch_name) as branch_name,
            MAX(s.latitude) as latitude,
            MAX(s.longitude) as longitude,
            MAX(s.rssd) as rssd,
            MAX(s.assets_000s) as assets_000s
        FROM branchsight.sod_legacy s
        LEFT JOIN shared.cbsa_to_county c
            USING(geoid5)
        WHERE SAFE_CAST(s.latitude AS FLOAT64) BETWEEN @sw_lat AND @ne_lat
            AND SAFE_CAST(s.longitude AS FLOAT64) BETWEEN @sw_lng AND @ne_lng
            AND s.year = @year
        GROUP BY 1,2,3,4,5
        ORDER BY bank_name, county_state, year
        LIMIT 10000
        """

        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("sw_lat", "FLOAT64", float(sw_lat)),
                ScalarQueryParameter("sw_lng", "FLOAT64", float(sw_lng)),
                ScalarQueryParameter("ne_lat", "FLOAT64", float(ne_lat)),
                ScalarQueryParameter("ne_lng", "FLOAT64", float(ne_lng)),
                ScalarQueryParameter("year", "STRING", str(year))
            ]
        )

        results = list(client.query(sql, job_config=job_config).result())
        return [dict(row) for row in results]

    except Exception as e:
        raise Exception(f"Error executing bounds query: {e}")


def get_counties_in_bounds(sw_lat, sw_lng, ne_lat, ne_lng):
    """Get counties with branches in a bounding box (from SOD data).

    Returns:
        List of dicts with geoid5, county_state, state_fips, county_fips
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

        sql = """
        SELECT DISTINCT
            s.geoid5,
            c.county_state,
            SUBSTR(CAST(s.geoid5 AS STRING), 1, 2) as state_fips,
            SUBSTR(CAST(s.geoid5 AS STRING), 3, 3) as county_fips
        FROM branchsight.sod s
        LEFT JOIN shared.cbsa_to_county c USING(geoid5)
        WHERE SAFE_CAST(s.latitude AS FLOAT64) BETWEEN @sw_lat AND @ne_lat
            AND SAFE_CAST(s.longitude AS FLOAT64) BETWEEN @sw_lng AND @ne_lng
            AND c.county_state IS NOT NULL
        ORDER BY c.county_state
        """

        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("sw_lat", "FLOAT64", float(sw_lat)),
                ScalarQueryParameter("sw_lng", "FLOAT64", float(sw_lng)),
                ScalarQueryParameter("ne_lat", "FLOAT64", float(ne_lat)),
                ScalarQueryParameter("ne_lng", "FLOAT64", float(ne_lng)),
            ]
        )

        results = list(client.query(sql, job_config=job_config).result())
        return [
            {
                'geoid5': row.geoid5,
                'county_state': row.county_state,
                'state_fips': row.state_fips,
                'county_fips': row.county_fips
            }
            for row in results
        ]

    except Exception as e:
        print(f"Error getting counties in bounds: {e}")
        return []


def get_states_overlapping_bounds(sw_lat, sw_lng, ne_lat, ne_lng):
    """Get distinct state FIPS codes for branches in a bounding box.

    Returns:
        List of state FIPS code strings (e.g. ['24', '51', '11'])
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

        sql = """
        SELECT DISTINCT
            SUBSTR(CAST(s.geoid5 AS STRING), 1, 2) as state_fips
        FROM branchsight.sod s
        WHERE SAFE_CAST(s.latitude AS FLOAT64) BETWEEN @sw_lat AND @ne_lat
            AND SAFE_CAST(s.longitude AS FLOAT64) BETWEEN @sw_lng AND @ne_lng
            AND s.geoid5 IS NOT NULL
        ORDER BY state_fips
        """

        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("sw_lat", "FLOAT64", float(sw_lat)),
                ScalarQueryParameter("sw_lng", "FLOAT64", float(sw_lng)),
                ScalarQueryParameter("ne_lat", "FLOAT64", float(ne_lat)),
                ScalarQueryParameter("ne_lng", "FLOAT64", float(ne_lng)),
            ]
        )

        results = list(client.query(sql, job_config=job_config).result())
        return [row.state_fips for row in results]

    except Exception as e:
        print(f"Error getting states overlapping bounds: {e}")
        return []


def parse_fdic_events(fdic_json):
    """Parse FDIC OSCR history API response into structured events.

    Handles changecode mapping, coordinate parsing, display_type/is_relocation
    assignment, and relocation inference (same CERT, <=90 days, <=2 miles, different address).

    Args:
        fdic_json: Raw JSON response from FDIC /banks/history API

    Returns:
        Dict with keys: events, count, openings, closings, relocation_pairs
    """
    import re
    import math
    from datetime import datetime

    def parse_date(date_str):
        if not date_str:
            return datetime.min
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S'):
            try:
                return datetime.strptime(date_str.split('T')[0] if 'T' in date_str else date_str, fmt)
            except ValueError:
                continue
        return datetime.min

    def clean_bank_name(name):
        if not name:
            return name
        suffixes = [
            r',?\s*National Association$',
            r',?\s*N\.?A\.?$',
            r',?\s*Inc\.?$',
            r',?\s*Corporation$',
            r',?\s*Corp\.?$',
        ]
        for pattern in suffixes:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
        return name.rstrip(',').strip()

    def haversine_miles(lat1, lon1, lat2, lon2):
        R = 3959
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    events = []
    for record in fdic_json.get('data', []):
        d = record.get('data', {})
        changecode = str(d.get('CHANGECODE', ''))

        if changecode == '712':
            continue

        if changecode == '711':
            event_type = 'opening'
        elif changecode == '713':
            event_type = 'opening_relocation'
        elif changecode == '721':
            event_type = 'closing'
        elif changecode == '722':
            event_type = 'closing_relocation'
        else:
            event_type = 'unknown'

        lat = d.get('OFF_LATITUDE')
        lng = d.get('OFF_LONGITUDE')
        if lat == 0 or lng == 0:
            lat = None
            lng = None

        events.append({
            'institution': clean_bank_name(d.get('INSTNAME')),
            'cert': d.get('CERT'),
            'branch_name': d.get('OFF_NAME'),
            'address': d.get('OFF_PADDR'),
            'city': d.get('OFF_PCITY'),
            'state': d.get('OFF_PSTALP'),
            'zip': d.get('OFF_PZIP5'),
            'county': d.get('OFF_CNTYNAME'),
            'latitude': lat,
            'longitude': lng,
            'changecode': changecode,
            'event_type': event_type,
            'effective_date': d.get('EFFDATE'),
            'processed_date': d.get('PROCDATE'),
            'bank_class': d.get('BKCLASS'),
            'service_type': d.get('OFF_SERVTYPE_DESC'),
            'frm_latitude': d.get('FRM_OFF_LATITUDE') if d.get('FRM_OFF_LATITUDE') != 0 else None,
            'frm_longitude': d.get('FRM_OFF_LONGITUDE') if d.get('FRM_OFF_LONGITUDE') != 0 else None,
            'frm_address': d.get('FRM_OFF_PADDR'),
            'frm_city': d.get('FRM_OFF_PCITY'),
            'frm_state': d.get('FRM_OFF_PSTALP'),
            'frm_zip': d.get('FRM_OFF_PZIP5'),
            'frm_branch_name': d.get('FRM_OFF_NAME')
        })

    # Set display_type and is_relocation
    for e in events:
        if e['event_type'] == 'opening_relocation':
            e['display_type'] = 'opening'
            e['is_relocation'] = True
        elif e['event_type'] == 'closing_relocation':
            e['display_type'] = 'closing'
            e['is_relocation'] = True
        elif e['event_type'] == 'opening':
            e['display_type'] = 'opening'
            e['is_relocation'] = False
        elif e['event_type'] == 'closing':
            e['display_type'] = 'closing'
            e['is_relocation'] = False
        else:
            e['display_type'] = 'unknown'
            e['is_relocation'] = False

    # Infer relocations
    closings = [e for e in events if e['display_type'] == 'closing' and e.get('latitude') and e.get('longitude')]
    openings = [e for e in events if e['display_type'] == 'opening' and e.get('latitude') and e.get('longitude')]

    relocation_pairs = []
    matched_closing_ids = set()
    matched_opening_ids = set()

    for ci, closing in enumerate(closings):
        if ci in matched_closing_ids:
            continue
        close_date = parse_date(closing.get('effective_date'))
        if not close_date:
            continue
        for oi, opening in enumerate(openings):
            if oi in matched_opening_ids:
                continue
            if closing.get('cert') != opening.get('cert'):
                continue
            open_date = parse_date(opening.get('effective_date'))
            if not open_date:
                continue
            day_diff = abs((close_date - open_date).days)
            if day_diff > 90:
                continue
            dist = haversine_miles(closing['latitude'], closing['longitude'], opening['latitude'], opening['longitude'])
            if dist > 2.0:
                continue
            if (closing.get('address') or '').strip().upper() == (opening.get('address') or '').strip().upper():
                continue

            closing['is_relocation'] = True
            closing['relocation_pair_address'] = f"{opening['address']}, {opening['city']}, {opening['state']} {opening['zip']}"
            closing['relocation_pair_lat'] = opening['latitude']
            closing['relocation_pair_lng'] = opening['longitude']
            closing['relocation_distance_miles'] = round(dist, 2)

            opening['is_relocation'] = True
            opening['relocation_pair_address'] = f"{closing['address']}, {closing['city']}, {closing['state']} {closing['zip']}"
            opening['relocation_pair_lat'] = closing['latitude']
            opening['relocation_pair_lng'] = closing['longitude']
            opening['relocation_distance_miles'] = round(dist, 2)

            relocation_pairs.append({
                'closing': closing['branch_name'],
                'opening': opening['branch_name'],
                'institution': closing.get('institution'),
                'distance_miles': round(dist, 2),
                'days_apart': day_diff
            })
            matched_closing_ids.add(ci)
            matched_opening_ids.add(oi)
            break

    return {
        'events': events,
        'count': len(events),
        'openings': len([e for e in events if e['display_type'] == 'opening']),
        'closings': len([e for e in events if e['display_type'] == 'closing']),
        'relocation_pairs': relocation_pairs
    }
