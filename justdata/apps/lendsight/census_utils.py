"""
Census Bureau API Client for LendSight - retrieving demographic data for context.

Uses the U.S. Census Bureau API to fetch:
- American Community Survey (ACS) data (most current)
- Demographic data (race, ethnicity) for comparing lending patterns to population

References:
    Census Data API User Guide: https://www.census.gov/data/developers/guidance/api-user-guide.html
    Request API Key: https://api.census.gov/data/key_signup.html

Requires:
    pip install census us requests

API Key:
    Get a free API key from: https://api.census.gov/data/key_signup.html
    Set environment variable: CENSUS_API_KEY=your-key-here
"""

import os
from typing import Dict, Optional, List
import requests


def get_most_recent_acs_year() -> str:
    """
    Determine the most recent available ACS 5-year estimate year
    
    Returns:
        Year string (e.g., '2024' for 2020-2024 estimates)
    """
    # ACS 5-year estimates are typically released in December
    # 2024 ACS 5-year = 2020-2024 data (released Dec 2024/Jan 2025)
    # Most recent comprehensive data as of early 2025
    return "2024"


def extract_fips_from_county_state(county_state: str) -> Optional[Dict[str, str]]:
    """
    Extract state and county FIPS codes from "County, State" format.
    
    Uses BigQuery to look up the geoid5 (5-digit FIPS) from the geo.cbsa_to_county table.
    
    Args:
        county_state: County name in format "County, State" (e.g., "Montgomery County, Maryland")
    
    Returns:
        Dictionary with 'state_fips' and 'county_fips', or None if not found
    """
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from justdata.apps.lendsight.config import PROJECT_ID
        
        client = get_bigquery_client(PROJECT_ID)
        
        from justdata.shared.utils.bigquery_client import escape_sql_string
        # Query to get geoid5 from county_state
        escaped_county_state = escape_sql_string(county_state)
        query = f"""
        SELECT DISTINCT geoid5
        FROM geo.cbsa_to_county
        WHERE county_state = '{escaped_county_state}'
        LIMIT 1
        """
        
        query_job = client.query(query)
        results = list(query_job.result())
        
        if results and results[0].geoid5:
            geoid5 = str(results[0].geoid5).zfill(5)  # Ensure 5 digits
            state_fips = geoid5[:2]  # First 2 digits = state
            county_fips = geoid5[2:]  # Last 3 digits = county
            
            return {
                'state_fips': state_fips,
                'county_fips': county_fips,
                'geoid5': geoid5
            }
        
        return None
        
    except Exception as e:
        print(f"Error extracting FIPS codes for {county_state}: {e}")
        return None


def get_census_demographics_for_county(
    state_fips: str,
    county_fips: str,
    county_name: str = None,
    api_key: Optional[str] = None,
    progress_tracker=None,
    county_index: int = 1,
    total_counties: int = 1
) -> Dict:
    """
    Get demographic data for a county across three time periods using the Census API.
    
    Fetches:
    - Most recent ACS 5-year estimates (2024/2022)
    - 2020 Decennial Census
    - 2010 Decennial Census
    
    Args:
        state_fips: Two-digit state FIPS code (e.g., "24" for Maryland)
        county_fips: Three-digit county FIPS code (e.g., "031" for Montgomery County)
        county_name: Optional county name for logging (e.g., "Montgomery County, Maryland")
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Dictionary with demographic data for all three time periods, or empty dict if unavailable
    """
    try:
        from census import Census
        
        # Get API key
        if api_key is None:
            api_key = os.getenv('CENSUS_API_KEY')
        
        if not api_key:
            print("Warning: No Census API key found. Set CENSUS_API_KEY environment variable.")
            return {}
        
        # Validate FIPS codes
        if not state_fips or not county_fips:
            print(f"ERROR: Invalid FIPS codes - state_fips: {state_fips}, county_fips: {county_fips}")
            return {}
        
        # Ensure FIPS codes are properly formatted
        state_fips = str(state_fips).zfill(2)
        county_fips = str(county_fips).zfill(3)
        
        display_name = county_name or f"State {state_fips}, County {county_fips}"
        
        # Initialize Census client
        c = Census(api_key)
        
        result = {
            'county_name': display_name,
            'state_fips': state_fips,
            'county_fips': county_fips,
            'time_periods': {}
        }
        
        # 1. Fetch most recent ACS estimates (try 5-year first, then 1-year)
        acs_data_fetched = False
        acs_year = get_most_recent_acs_year()
        acs_year_int = int(acs_year)
        
        acs_variables = [
            'NAME',
            'B01003_001E',  # Total population
            'B03002_001E',  # Total (for race breakdown)
            'B03002_003E',  # White alone (not Hispanic)
            'B03002_004E',  # Black or African American alone (not Hispanic)
            'B03002_005E',  # American Indian/Alaska Native alone (not Hispanic)
            'B03002_006E',  # Asian alone (not Hispanic)
            'B03002_007E',  # Native Hawaiian/Pacific Islander alone (not Hispanic)
            'B03002_009E',  # Two or more races (not Hispanic)
            'B03002_012E',  # Hispanic or Latino (of any race)
        ]
        
        # Try ACS 5-year estimates first
        try:
            print(f"Fetching ACS {acs_year} 5-year estimates for {display_name} (State: {state_fips}, County: {county_fips})...")
            print(f"  [DEBUG] Census API parameters: for=county:{county_fips}, in=state:{state_fips}, year={acs_year_int}")
            if progress_tracker and total_counties > 0:
                base_pct = 50 + int((county_index - 1) / total_counties * 10)
                progress_tracker.update_progress('fetching_census_data', base_pct + 1, 
                    f'Fetching Census: {display_name} - ACS 5-year ({county_index}/{total_counties})...')
            acs_data = c.acs5.get(
                acs_variables,
                {
                    'for': f'county:{county_fips}',
                    'in': f'state:{state_fips}'
                },
                year=acs_year_int
            )
            print(f"  [DEBUG] ACS API response: {len(acs_data) if acs_data else 0} records returned")
            
            if acs_data and len(acs_data) > 0:
                record = acs_data[0]
                total_pop = _safe_int(record.get('B01003_001E'))
                
                if total_pop and total_pop > 0:
                    white = _safe_int(record.get('B03002_003E', 0))
                    black = _safe_int(record.get('B03002_004E', 0))
                    asian = _safe_int(record.get('B03002_006E', 0))
                    native_am = _safe_int(record.get('B03002_005E', 0))
                    hopi = _safe_int(record.get('B03002_007E', 0))
                    multi_racial = _safe_int(record.get('B03002_009E', 0))
                    hispanic = _safe_int(record.get('B03002_012E', 0))
                    
                    result['time_periods']['acs'] = {
                        'year': f"{acs_year} ACS",
                        'data_year': f"{acs_year} (ACS 5-year estimates)",
                        'demographics': {
                            'total_population': total_pop or 0,
                            'white_percentage': (white / total_pop * 100) if white else 0,
                            'black_percentage': (black / total_pop * 100) if black else 0,
                            'asian_percentage': (asian / total_pop * 100) if asian else 0,
                            'native_american_percentage': (native_am / total_pop * 100) if native_am else 0,
                            'hopi_percentage': (hopi / total_pop * 100) if hopi else 0,
                            'multi_racial_percentage': (multi_racial / total_pop * 100) if multi_racial else 0,
                            'hispanic_percentage': (hispanic / total_pop * 100) if hispanic else 0
                        }
                    }
                    acs_data_fetched = True
                    print(f"  [OK] Successfully fetched ACS 5-year data for {display_name}")
        except Exception as e:
            print(f"  [WARNING] Failed to fetch ACS 5-year data for {display_name}: {e}")
            print(f"  [INFO] Trying ACS 1-year estimates instead...")
        
        # If 5-year failed, try 1-year ACS estimates
        if not acs_data_fetched:
            try:
                print(f"Fetching ACS {acs_year} 1-year estimates for {display_name}...")
                if progress_tracker and total_counties > 0:
                    base_pct = 50 + int((county_index - 1) / total_counties * 10)
                    progress_tracker.update_progress('fetching_census_data', base_pct + 2, 
                        f'Fetching Census: {display_name} - ACS 1-year ({county_index}/{total_counties})...')
                acs_data = c.acs1.get(
                    acs_variables,
                    {
                        'for': f'county:{county_fips}',
                        'in': f'state:{state_fips}'
                    },
                    year=acs_year_int
                )
                
                if acs_data and len(acs_data) > 0:
                    record = acs_data[0]
                    total_pop = _safe_int(record.get('B01003_001E'))
                    
                    if total_pop and total_pop > 0:
                        white = _safe_int(record.get('B03002_003E', 0))
                        black = _safe_int(record.get('B03002_004E', 0))
                        asian = _safe_int(record.get('B03002_006E', 0))
                        native_am = _safe_int(record.get('B03002_005E', 0))
                        hopi = _safe_int(record.get('B03002_007E', 0))
                        multi_racial = _safe_int(record.get('B03002_009E', 0))
                        hispanic = _safe_int(record.get('B03002_012E', 0))
                        
                        result['time_periods']['acs'] = {
                            'year': f"{acs_year} ACS",
                            'data_year': f"{acs_year} (ACS 1-year estimates)",
                            'demographics': {
                                'total_population': total_pop or 0,
                                'white_percentage': (white / total_pop * 100) if white else 0,
                                'black_percentage': (black / total_pop * 100) if black else 0,
                                'asian_percentage': (asian / total_pop * 100) if asian else 0,
                                'native_american_percentage': (native_am / total_pop * 100) if native_am else 0,
                                'hopi_percentage': (hopi / total_pop * 100) if hopi else 0,
                                'multi_racial_percentage': (multi_racial / total_pop * 100) if multi_racial else 0,
                                'hispanic_percentage': (hispanic / total_pop * 100) if hispanic else 0
                            }
                        }
                        acs_data_fetched = True
                        print(f"  [OK] Successfully fetched ACS 1-year data for {display_name}")
            except Exception as e:
                print(f"  [WARNING] Failed to fetch ACS 1-year data for {display_name}: {e}")
                # Try previous year as fallback
                try:
                    fallback_year = acs_year_int - 1
                    print(f"  [INFO] Trying ACS 5-year estimates for {fallback_year} as fallback...")
                    acs_data = c.acs5.get(
                        acs_variables,
                        {
                            'for': f'county:{county_fips}',
                            'in': f'state:{state_fips}'
                        },
                        year=fallback_year
                    )
                    
                    if acs_data and len(acs_data) > 0:
                        record = acs_data[0]
                        total_pop = _safe_int(record.get('B01003_001E'))
                        
                        if total_pop and total_pop > 0:
                            white = _safe_int(record.get('B03002_003E', 0))
                            black = _safe_int(record.get('B03002_004E', 0))
                            asian = _safe_int(record.get('B03002_006E', 0))
                            native_am = _safe_int(record.get('B03002_005E', 0))
                            hopi = _safe_int(record.get('B03002_007E', 0))
                            multi_racial = _safe_int(record.get('B03002_009E', 0))
                            hispanic = _safe_int(record.get('B03002_012E', 0))
                            
                            result['time_periods']['acs'] = {
                                'year': f"{fallback_year} ACS",
                                'data_year': f"{fallback_year} (ACS 5-year estimates)",
                                'demographics': {
                                    'total_population': total_pop or 0,
                                    'white_percentage': (white / total_pop * 100) if white else 0,
                                    'black_percentage': (black / total_pop * 100) if black else 0,
                                    'asian_percentage': (asian / total_pop * 100) if asian else 0,
                                    'native_american_percentage': (native_am / total_pop * 100) if native_am else 0,
                                    'hopi_percentage': (hopi / total_pop * 100) if hopi else 0,
                                    'multi_racial_percentage': (multi_racial / total_pop * 100) if multi_racial else 0,
                                    'hispanic_percentage': (hispanic / total_pop * 100) if hispanic else 0
                                }
                            }
                            acs_data_fetched = True
                            print(f"  [OK] Successfully fetched ACS 5-year data for {fallback_year} as fallback")
                except Exception as e2:
                    print(f"  [WARNING] Failed to fetch fallback ACS data: {e2}")
        
        # 2. Fetch 2020 Decennial Census (PL94-171)
        try:
            print(f"Fetching 2020 Decennial Census for {display_name}...")
            if progress_tracker and total_counties > 0:
                base_pct = 50 + int((county_index - 1) / total_counties * 10)
                progress_tracker.update_progress('fetching_census_data', base_pct + 3, 
                    f'Fetching Census: {display_name} - 2020 Census ({county_index}/{total_counties})...')
            # Use direct API call for 2020 PL94-171 data
            url = f"https://api.census.gov/data/2020/dec/pl"
            params = {
                'get': 'NAME,P1_001N,P2_001N,P2_002N,P2_005N,P2_006N,P2_007N,P2_008N,P2_009N,P2_011N',
                'for': f'county:{county_fips}',
                'in': f'state:{state_fips}',
                'key': api_key
            }
            # P1_001N = Total population
            # P2_001N = Total (for race/ethnicity)
            # P2_002N = Hispanic or Latino (of any race)
            # P2_005N = White alone (not Hispanic)
            # P2_006N = Black or African American alone (not Hispanic)
            # P2_007N = American Indian/Alaska Native alone (not Hispanic)
            # P2_008N = Asian alone (not Hispanic)
            # P2_009N = Native Hawaiian/Pacific Islander alone (not Hispanic)
            # P2_011N = Two or more races (not Hispanic)
            
            print(f"  [DEBUG] 2020 Census API URL: {url}")
            print(f"  [DEBUG] 2020 Census API params: for=county:{county_fips}, in=state:{state_fips}")
            response = requests.get(url, params=params, timeout=30)
            print(f"  [DEBUG] 2020 Census API response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 1:
                headers = data[0]
                row = data[1]
                
                name_idx = headers.index('NAME')
                total_pop_idx = headers.index('P1_001N')
                total_race_idx = headers.index('P2_001N')
                hispanic_idx = headers.index('P2_002N')
                white_idx = headers.index('P2_005N')
                black_idx = headers.index('P2_006N')
                native_am_idx = headers.index('P2_007N')
                asian_idx = headers.index('P2_008N')
                hopi_idx = headers.index('P2_009N')
                multi_racial_idx = headers.index('P2_011N')
                
                total_pop = _safe_int(row[total_pop_idx])
                
                if total_pop and total_pop > 0:
                    white = _safe_int(row[white_idx])
                    black = _safe_int(row[black_idx])
                    asian = _safe_int(row[asian_idx])
                    native_am = _safe_int(row[native_am_idx])
                    hopi = _safe_int(row[hopi_idx])
                    multi_racial = _safe_int(row[multi_racial_idx])
                    hispanic = _safe_int(row[hispanic_idx])
                    
                    result['time_periods']['census2020'] = {
                        'year': '2020 Census',
                        'data_year': '2020 (Decennial Census)',
                        'demographics': {
                            'total_population': total_pop or 0,
                            'white_percentage': (white / total_pop * 100) if white else 0,
                            'black_percentage': (black / total_pop * 100) if black else 0,
                            'asian_percentage': (asian / total_pop * 100) if asian else 0,
                            'native_american_percentage': (native_am / total_pop * 100) if native_am else 0,
                            'hopi_percentage': (hopi / total_pop * 100) if hopi else 0,
                            'multi_racial_percentage': (multi_racial / total_pop * 100) if multi_racial else 0,
                            'hispanic_percentage': (hispanic / total_pop * 100) if hispanic else 0
                        }
                    }
        except Exception as e:
            print(f"Warning: Failed to fetch 2020 Census data for {display_name}: {e}")
        
        # 3. Fetch 2010 Decennial Census (SF1)
        try:
            print(f"Fetching 2010 Decennial Census for {display_name}...")
            if progress_tracker and total_counties > 0:
                base_pct = 50 + int((county_index - 1) / total_counties * 10)
                progress_tracker.update_progress('fetching_census_data', base_pct + 4, 
                    f'Fetching Census: {display_name} - 2010 Census ({county_index}/{total_counties})...')
            # Use direct API call with correct 2010 SF1 variable names
            # Correct variables for 2010 SF1:
            # P001001 = Total population
            # P005001 = Total (for race/ethnicity breakdown)
            # P005003 = Not Hispanic or Latino!!White alone
            # P005004 = Not Hispanic or Latino!!Black or African American alone
            # P005005 = Not Hispanic or Latino!!American Indian/Alaska Native alone
            # P005006 = Not Hispanic or Latino!!Asian alone
            # P005007 = Not Hispanic or Latino!!Native Hawaiian/Pacific Islander alone
            # P005009 = Not Hispanic or Latino!!Two or more races
            # P004003 = Hispanic or Latino (of any race)
            
            url = f"https://api.census.gov/data/2010/dec/sf1"
            params = {
                'get': 'NAME,P001001,P005001,P005003,P005004,P005005,P005006,P005007,P005009,P004003',  # Include P004003 (Hispanic) and P005009 (Two or more races) in main call
                'for': f'county:{county_fips}',
                'in': f'state:{state_fips}',
                'key': api_key
            }
            
            print(f"  [DEBUG] 2010 Census API URL: {url}")
            print(f"  [DEBUG] 2010 Census API params: for=county:{county_fips}, in=state:{state_fips}")
            response = requests.get(url, params=params, timeout=30)
            print(f"  [DEBUG] 2010 Census API response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            print(f"  [DEBUG] 2010 Census API response: {len(data) if data else 0} records returned")
            
            if data and len(data) > 1:
                headers = data[0]
                row = data[1]
                
                name_idx = headers.index('NAME')
                total_pop_idx = headers.index('P001001')
                total_race_idx = headers.index('P005001')
                white_idx = headers.index('P005003')
                black_idx = headers.index('P005004')
                native_am_idx = headers.index('P005005')
                asian_idx = headers.index('P005006')
                hopi_idx = headers.index('P005007')
                multi_racial_idx = headers.index('P005009')
                
                # Try to get Hispanic from main call (P004003), fallback to separate call if not present
                hispanic_idx = None
                try:
                    hispanic_idx = headers.index('P004003')
                except ValueError:
                    # P004003 not in headers, will fetch separately
                    pass
                
                total_pop = _safe_int(row[total_pop_idx])
                
                if total_pop and total_pop > 0:
                    white = _safe_int(row[white_idx])
                    black = _safe_int(row[black_idx])
                    asian = _safe_int(row[asian_idx])
                    native_am = _safe_int(row[native_am_idx])
                    hopi = _safe_int(row[hopi_idx])
                    multi_racial = _safe_int(row[multi_racial_idx])
                    
                    # Get Hispanic - prefer from main call, fallback to separate call
                    if hispanic_idx is not None:
                        hispanic = _safe_int(row[hispanic_idx])
                        print(f"  [DEBUG] Hispanic data from main 2010 Census call: {hispanic}")
                    else:
                        # Get Hispanic separately (fallback)
                        try:
                            print(f"  [DEBUG] Fetching Hispanic data separately for 2010 Census...")
                            url_hispanic = f"https://api.census.gov/data/2010/dec/sf1"
                            params_hispanic = {
                                'get': 'P004003',  # Hispanic or Latino (of any race)
                                'for': f'county:{county_fips}',
                                'in': f'state:{state_fips}',
                                'key': api_key
                            }
                            response_hispanic = requests.get(url_hispanic, params=params_hispanic, timeout=30)
                            response_hispanic.raise_for_status()
                            data_hispanic = response_hispanic.json()
                            hispanic = _safe_int(data_hispanic[1][0]) if data_hispanic and len(data_hispanic) > 1 else 0
                            print(f"  [DEBUG] Hispanic data from separate 2010 Census call: {hispanic}")
                        except Exception as e:
                            print(f"  [WARNING] Failed to fetch Hispanic data separately: {e}")
                            hispanic = 0
                    
                    result['time_periods']['census2010'] = {
                        'year': '2010 Census',
                        'data_year': '2010 (Decennial Census)',
                        'demographics': {
                            'total_population': total_pop or 0,
                            'white_percentage': (white / total_pop * 100) if white else 0,
                            'black_percentage': (black / total_pop * 100) if black else 0,
                            'asian_percentage': (asian / total_pop * 100) if asian else 0,
                            'native_american_percentage': (native_am / total_pop * 100) if native_am else 0,
                            'hopi_percentage': (hopi / total_pop * 100) if hopi else 0,
                            'multi_racial_percentage': (multi_racial / total_pop * 100) if multi_racial else 0,
                            'hispanic_percentage': (hispanic / total_pop * 100) if hispanic else 0
                        }
                    }
        except Exception as e:
            print(f"Warning: Failed to fetch 2010 Census data for {display_name}: {e}")
            import traceback
            traceback.print_exc()
        
        # Return empty dict if no data was retrieved
        time_periods = result.get('time_periods', {})
        if not time_periods or len(time_periods) == 0:
            print(f"  [WARNING] No time periods retrieved for {display_name} - returning empty dict")
            print(f"  [DEBUG] Result structure: {list(result.keys())}")
            return {}
        
        print(f"  [DEBUG] Successfully retrieved {len(time_periods)} time periods for {display_name}: {list(time_periods.keys())}")
        return result
        
    except ImportError:
        print("Warning: 'census' package not installed. Install with: pip install census us requests")
        return {}
    except Exception as e:
        print(f"Error fetching census data for {display_name}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def get_census_data_for_multiple_counties(
    counties_data: List[Dict],
    state_code: str,
    api_key: Optional[str] = None,
    progress_tracker=None
) -> Dict[str, Dict]:
    """
    Get census data for multiple counties using FIPS codes.
    
    Args:
        counties_data: List of county dicts with 'name', 'geoid5', 'state_fips', 'county_fips'
        state_code: Two-digit state FIPS code (e.g., "10" for Delaware)
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Dictionary mapping county name to census data
    """
    import os
    if api_key is None:
        api_key = os.getenv('CENSUS_API_KEY')
    
    if not api_key:
        print("  [WARNING] CENSUS_API_KEY not set - cannot fetch Census data")
        return {}
    
    # Ensure state_code is properly formatted
    state_code = str(state_code).zfill(2)
    
    print(f"  [INFO] Fetching Census data for {len(counties_data)} counties in state {state_code}...")
    print(f"  [INFO] Note: Each county requires 3-4 API calls (ACS, 2020 Census, 2010 Census), so this may take 30-60 seconds...")
    result = {}
    for idx, county_info in enumerate(counties_data, 1):
        # Extract FIPS codes from county data
        if isinstance(county_info, dict):
            county_name = county_info.get('name', 'Unknown')
            # Extract county_fips: prefer explicit county_fips, otherwise extract from geoid5
            # geoid5 format: SSCCC (2-digit state + 3-digit county)
            if county_info.get('county_fips'):
                county_fips = str(county_info.get('county_fips')).zfill(3)  # Ensure 3 digits
            elif county_info.get('geoid5'):
                geoid5_str = str(county_info.get('geoid5')).zfill(5)  # Ensure 5 digits
                county_fips = geoid5_str[2:]  # Last 3 digits (positions 2, 3, 4)
            else:
                county_fips = None
            
            # Extract state_fips: prefer explicit state_fips, otherwise extract from geoid5 or use state_code
            if county_info.get('state_fips'):
                state_fips = str(county_info.get('state_fips')).zfill(2)  # Ensure 2 digits
            elif county_info.get('geoid5'):
                geoid5_str = str(county_info.get('geoid5')).zfill(5)  # Ensure 5 digits
                state_fips = geoid5_str[:2]  # First 2 digits
            elif state_code:
                state_fips = str(state_code).zfill(2)
            else:
                state_fips = None
        else:
            # Fallback: if it's still a string, try to extract FIPS (backward compatibility)
            county_name = str(county_info)
            print(f"  [WARNING] County data is string format, attempting to extract FIPS codes...")
            # extract_fips_from_county_state is in the same module, no import needed
            fips_data = extract_fips_from_county_state(county_name)
            if fips_data:
                state_fips = fips_data['state_fips']
                county_fips = fips_data['county_fips']
            else:
                print(f"  [ERROR] Could not extract FIPS codes for {county_name}, skipping...")
                continue
        
        # Validate FIPS codes before making API call
        if not state_fips or not county_fips:
            print(f"    [ERROR] Invalid FIPS codes for {county_name}: state_fips={state_fips}, county_fips={county_fips}")
            print(f"    [DEBUG] County info: {county_info}")
            continue
        
        # Ensure FIPS codes are properly formatted (2 digits for state, 3 digits for county)
        state_fips = str(state_fips).zfill(2)
        county_fips = str(county_fips).zfill(3)
        
        print(f"    [{idx}/{len(counties_data)}] Processing {county_name} (State: {state_fips}, County: {county_fips})...")
        print(f"    [DEBUG] Census API will use: for=county:{county_fips}, in=state:{state_fips}")
        if progress_tracker:
            # Update progress: 50% base + up to 10% for Census (50-60% range)
            progress_pct = 50 + int((idx - 1) / len(counties_data) * 10)
            progress_tracker.update_progress('fetching_census_data', progress_pct, 
                f'Starting Census data fetch: {county_name} ({idx}/{len(counties_data)})...')
        try:
            data = get_census_demographics_for_county(
                state_fips, county_fips, county_name, api_key, progress_tracker, idx, len(counties_data)
            )
            print(f"    [DEBUG] get_census_demographics_for_county returned: type={type(data)}, len={len(data) if data else 0}, keys={list(data.keys()) if data else []}")
            
            # Check for new structure (time_periods) or old structure (demographics) for compatibility
            has_time_periods = data and data.get('time_periods')
            has_demographics = data and data.get('demographics')
            print(f"    [DEBUG] has_time_periods={bool(has_time_periods)}, has_demographics={bool(has_demographics)}")
            
            if data and (has_time_periods or has_demographics):
                result[county_name] = data
                print(f"    [OK] Retrieved Census data for {county_name}")
                if progress_tracker:
                    # Mark this county as complete
                    base_pct = 50 + int((idx / len(counties_data)) * 10)
                    progress_tracker.update_progress('fetching_census_data', base_pct, 
                        f'Completed Census data: {county_name} ({idx}/{len(counties_data)})...')
                if has_time_periods:
                    time_periods = data.get('time_periods', {})
                    print(f"      - Time periods: {list(time_periods.keys())}")
                    for period_key, period_data in time_periods.items():
                        demo = period_data.get('demographics', {})
                        pop = demo.get('total_population', 'N/A')
                        print(f"        - {period_key}: population={pop}")
                elif has_demographics:
                    print(f"      - Using legacy demographics format")
            else:
                print(f"    [WARNING] No Census data returned for {county_name} - data is empty or missing time_periods/demographics")
                if data:
                    print(f"      - Data keys: {list(data.keys())}")
                else:
                    print(f"      - Data is None or empty")
                if progress_tracker:
                    # Still mark as attempted
                    base_pct = 50 + int((idx / len(counties_data)) * 10)
                    progress_tracker.update_progress('fetching_census_data', base_pct, 
                        f'No Census data: {county_name} ({idx}/{len(counties_data)})...')
        except Exception as e:
            print(f"    [ERROR] Failed to get Census data for {county_name}: {e}")
            import traceback
            traceback.print_exc()
            if progress_tracker:
                # Mark as failed
                base_pct = 50 + int((idx / len(counties_data)) * 10)
                progress_tracker.update_progress('fetching_census_data', base_pct, 
                    f'Failed Census data: {county_name} ({idx}/{len(counties_data)})...')
    
    print(f"  [INFO] Retrieved Census data for {len(result)} out of {len(counties_data)} counties")
    if progress_tracker:
        progress_tracker.update_progress('fetching_census_data', 60, 
            f'Census data fetch complete ({len(result)}/{len(counties_data)} counties)...')
    if len(result) == 0:
        print(f"  [WARNING] No Census data retrieved for any counties!")
        print(f"  [DEBUG] Counties requested: {[c.get('name', 'Unknown') if isinstance(c, dict) else c for c in counties_data]}")
        print(f"  [DEBUG] API key present: {api_key is not None}")
    else:
        print(f"  [DEBUG] Census data counties: {list(result.keys())}")
        # Print sample to verify structure
        sample_county = list(result.keys())[0]
        sample_data = result[sample_county]
        print(f"  [DEBUG] Sample county '{sample_county}' structure: {list(sample_data.keys())}")
        if 'demographics' in sample_data:
            print(f"  [DEBUG] Demographics keys: {list(sample_data['demographics'].keys())}")
    return result


def _safe_int(value) -> Optional[int]:
    """Safely convert value to integer, handling null and error codes"""
    if value is None:
        return None
    try:
        val = int(value)
        # Census API uses -888888888 or similar for nulls/errors
        if val < 0:
            return None
        return val
    except (ValueError, TypeError):
        return None

