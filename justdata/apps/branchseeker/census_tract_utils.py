"""
Census Tract Utilities for BranchMapper
Fetches census tract boundaries and demographic data for map layers.
"""

import os
from typing import Dict, List, Optional, Any
import requests
import json


def get_census_api_key() -> Optional[str]:
    """Get Census API key from environment variable."""
    return os.getenv('CENSUS_API_KEY')


def get_cbsa_for_county(county_state: str) -> Optional[Dict[str, Any]]:
    """
    Get the CBSA (metro area) code and name for a county.
    
    Uses GEOID5 (state FIPS + county FIPS) for reliable lookup instead of county name.
    
    Args:
        county_state: County name in format "County, State" (e.g., "Hillsborough County, Florida")
    
    Returns:
        Dictionary with 'cbsa_code' and 'cbsa_name', or None if not found
    """
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from apps.branchseeker.config import PROJECT_ID
        
        # First, extract FIPS codes to get GEOID5
        fips_data = extract_fips_from_county_state(county_state)
        if not fips_data:
            print(f"Could not extract FIPS codes for {county_state}")
            return None
        
        state_fips = fips_data['state_fips']
        county_fips = fips_data['county_fips']
        geoid5 = fips_data.get('geoid5') or f"{state_fips}{county_fips}"
        
        print(f"Looking up CBSA using GEOID5: {geoid5} (State: {state_fips}, County: {county_fips}) for {county_state}")
        
        client = get_bigquery_client(PROJECT_ID)
        
        # Query using GEOID5 (more reliable than county name)
        # Check for both metropolitan and micropolitan areas
        # Note: geo.cbsa_to_county table has cbsa_code and CBSA (the name)
        query = f"""
        SELECT DISTINCT
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name
        FROM geo.cbsa_to_county
        WHERE CAST(geoid5 AS STRING) = '{geoid5}'
            AND cbsa_code IS NOT NULL
        LIMIT 1
        """
        
        print(f"Executing BigQuery: {query}")
        try:
            query_job = client.query(query)
            results = list(query_job.result())
            print(f"BigQuery returned {len(results)} results for GEOID5 {geoid5}")
        except Exception as query_error:
            print(f"[ERROR] BigQuery query failed: {query_error}")
            results = []
        
        if results and results[0].cbsa_code:
            cbsa_code = str(results[0].cbsa_code)
            cbsa_name = str(results[0].cbsa_name) if results[0].cbsa_name else None
            print(f"[OK] Found CBSA: {cbsa_code} ({cbsa_name}) for GEOID5 {geoid5} ({county_state})")
            return {
                'cbsa_code': cbsa_code,
                'cbsa_name': cbsa_name
            }
        
        # If no results, check if the GEOID5 exists in the table at all
        check_query = f"""
        SELECT DISTINCT geoid5, county_state, cbsa_code
        FROM geo.cbsa_to_county
        WHERE CAST(geoid5 AS STRING) = '{geoid5}'
        LIMIT 5
        """
        try:
            check_job = client.query(check_query)
            check_results = list(check_job.result())
        except Exception as check_error:
            print(f"[ERROR] Check query failed: {check_error}")
            check_results = []
        
        if check_results:
            print(f"Found {len(check_results)} rows for GEOID5 {geoid5}, but cbsa_code is NULL:")
            for row in check_results:
                print(f"  - {row.county_state}: cbsa_code={row.cbsa_code}")
        else:
            print(f"No rows found in geo.cbsa_to_county for GEOID5 {geoid5} ({county_state})")
            # Try querying by county_state as a fallback
            print(f"Trying fallback query by county_state: '{county_state}'")
            fallback_query = f"""
            SELECT DISTINCT
                CAST(cbsa_code AS STRING) as cbsa_code,
                CBSA as cbsa_name,
                geoid5
            FROM geo.cbsa_to_county
            WHERE county_state = '{county_state}'
                AND cbsa_code IS NOT NULL
            LIMIT 1
            """
            try:
                fallback_job = client.query(fallback_query)
                fallback_results = list(fallback_job.result())
                if fallback_results and fallback_results[0].cbsa_code:
                    cbsa_code = str(fallback_results[0].cbsa_code)
                    cbsa_name = str(fallback_results[0].cbsa_name) if fallback_results[0].cbsa_name else None
                    found_geoid5 = str(fallback_results[0].geoid5).zfill(5) if fallback_results[0].geoid5 else None
                    print(f"[OK] Found CBSA via county_state fallback: {cbsa_code} ({cbsa_name}) for {county_state} (GEOID5: {found_geoid5})")
                    return {
                        'cbsa_code': cbsa_code,
                        'cbsa_name': cbsa_name
                    }
            except Exception as fallback_error:
                print(f"[ERROR] Fallback query by county_state also failed: {fallback_error}")
            
            # Try to find similar GEOID5s
            similar_query = f"""
            SELECT DISTINCT geoid5, county_state
            FROM geo.cbsa_to_county
            WHERE CAST(geoid5 AS STRING) LIKE '{geoid5[:4]}%'
            LIMIT 5
            """
            try:
                similar_job = client.query(similar_query)
                similar_results = list(similar_job.result())
                if similar_results:
                    print(f"Similar GEOID5s found: {[(str(r.geoid5), str(r.county_state)) for r in similar_results]}")
            except Exception:
                pass
        
        print(f"[ERROR] No CBSA found for GEOID5 {geoid5} ({county_state}). This county may not be in a metro/micro area.")
        return None
        
    except Exception as e:
        print(f"Error getting CBSA for county {county_state}: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_fips_from_county_state(county_state: str) -> Optional[Dict[str, str]]:
    """
    Extract state and county FIPS codes from "County, State" format.
    
    Uses BigQuery to look up the geoid5 (5-digit FIPS) from the geo.cbsa_to_county table.
    Tries exact match first, then case-insensitive match.
    
    Args:
        county_state: County name in format "County, State" (e.g., "Hillsborough County, Florida")
    
    Returns:
        Dictionary with 'state_fips', 'county_fips', and 'geoid5', or None if not found
    """
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from apps.branchseeker.config import PROJECT_ID
        
        client = get_bigquery_client(PROJECT_ID)
        
        # Try exact match first
        query = f"""
        SELECT DISTINCT geoid5
        FROM geo.cbsa_to_county
        WHERE county_state = '{county_state}'
        LIMIT 1
        """
        
        print(f"Extracting FIPS codes for: '{county_state}'")
        query_job = client.query(query)
        results = list(query_job.result())
        
        if results and results[0].geoid5:
            geoid5 = str(results[0].geoid5).zfill(5)  # Ensure 5 digits
            state_fips = geoid5[:2]  # First 2 digits = state
            county_fips = geoid5[2:]  # Last 3 digits = county
            
            print(f"Found GEOID5: {geoid5} (State: {state_fips}, County: {county_fips}) for {county_state}")
            return {
                'state_fips': state_fips,
                'county_fips': county_fips,
                'geoid5': geoid5
            }
        
        # Try case-insensitive match
        print(f"No exact match, trying case-insensitive match...")
        query_case_insensitive = f"""
        SELECT DISTINCT geoid5, county_state
        FROM geo.cbsa_to_county
        WHERE UPPER(county_state) = UPPER('{county_state}')
        LIMIT 1
        """
        
        query_job = client.query(query_case_insensitive)
        results = list(query_job.result())
        
        if results and results[0].geoid5:
            geoid5 = str(results[0].geoid5).zfill(5)
            state_fips = geoid5[:2]
            county_fips = geoid5[2:]
            matched_name = str(results[0].county_state) if results[0].county_state else county_state
            
            print(f"Found GEOID5 with case-insensitive match: {geoid5} (State: {state_fips}, County: {county_fips}) for '{matched_name}' (searched for '{county_state}')")
            return {
                'state_fips': state_fips,
                'county_fips': county_fips,
                'geoid5': geoid5
            }
        
        print(f"Could not find GEOID5 for {county_state}")
        return None
        
    except Exception as e:
        print(f"Error extracting FIPS codes for {county_state}: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_county_median_family_income(state_fips: str, county_fips: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get median family income for a county from Census API.
    
    Uses ACS 5-Year Estimates, variable B19113_001E (Median Family Income).
    
    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Median family income in dollars, or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()
    
    if not api_key:
        print("Warning: No Census API key found. Set CENSUS_API_KEY environment variable.")
        return None
    
    try:
        acs_year = "2022"
        
        url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
        params = {
            'get': 'NAME,B19113_001E',
            'for': f'county:{county_fips}',
            'in': f'state:{state_fips}',
            'key': api_key
        }
        
        print(f"Fetching county median income from Census API: {url}")
        print(f"Parameters: state={state_fips}, county={county_fips}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"Census API response: {data}")
        
        if len(data) > 1 and len(data[1]) > 1:
            income_str = data[1][1]  # B19113_001E value
            print(f"Raw income value from Census API: '{income_str}'")
            
            if income_str and income_str != '-888888888' and income_str != 'null':
                try:
                    income = float(income_str)
                    print(f"[OK] Found county median family income: ${income:,.0f} for state FIPS {state_fips}, county FIPS {county_fips}")
                    return income
                except ValueError as ve:
                    print(f"[ERROR] Could not convert income value '{income_str}' to float: {ve}")
            else:
                print(f"[ERROR] Income value is null or error code: '{income_str}'")
        else:
            print(f"[ERROR] Unexpected response format. Expected at least 2 rows, got {len(data)} rows")
            print(f"Response: {data}")
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] HTTP error fetching county median family income: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text[:500]}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[ERROR] Error fetching county median family income: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_county_minority_percentage(state_fips: str, county_fips: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get minority population percentage for a county from Census API.
    
    Minority = Total population - Non-Hispanic White alone
    Uses ACS 5-Year Estimates.
    
    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Minority population percentage (0-100), or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()
    
    if not api_key:
        print("Warning: No Census API key found. Set CENSUS_API_KEY environment variable.")
        return None
    
    try:
        acs_year = "2022"
        
        # Census API variables:
        # B01003_001E = Total population
        # B03002_003E = White alone, not Hispanic or Latino
        url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
        params = {
            'get': 'NAME,B01003_001E,B03002_003E',
            'for': f'county:{county_fips}',
            'in': f'state:{state_fips}',
            'key': api_key
        }
        
        print(f"Fetching county minority data from Census API: {url}")
        print(f"Parameters: state={state_fips}, county={county_fips}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"Census API response: {data}")
        
        if len(data) > 1 and len(data[1]) > 2:
            total_pop = data[1][1]  # B01003_001E
            white_non_hisp = data[1][2]  # B03002_003E
            
            print(f"Raw data - Total pop: {total_pop}, White non-Hispanic: {white_non_hisp}")
            
            if total_pop and white_non_hisp and total_pop != '-888888888' and white_non_hisp != '-888888888':
                try:
                    total = float(total_pop)
                    white = float(white_non_hisp)
                    if total > 0:
                        minority = total - white
                        percentage = (minority / total) * 100
                        print(f"[OK] Calculated county minority percentage: {percentage:.1f}% (Total: {total:,.0f}, White: {white:,.0f}, Minority: {minority:,.0f})")
                        return percentage
                    else:
                        print(f"[ERROR] Total population is 0 or negative: {total}")
                except (ValueError, TypeError) as ve:
                    print(f"[ERROR] Could not convert population values to float: {ve}")
            else:
                print(f"[ERROR] Invalid population data - Total: '{total_pop}', White: '{white_non_hisp}'")
        else:
            print(f"[ERROR] Unexpected response format. Expected at least 2 rows with 3 columns, got {len(data)} rows")
            if len(data) > 0:
                print(f"Response structure: {data[0]}")
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] HTTP error fetching county minority percentage: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text[:500]}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[ERROR] Error fetching county minority percentage: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_state_median_family_income(state_fips: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get median family income for a state from Census API (fallback when CBSA not available).
    
    Uses ACS 5-Year Estimates, variable B19113_001E (Median Family Income).
    
    Args:
        state_fips: 2-digit state FIPS code
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Median family income in dollars, or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()
    
    if not api_key:
        print("Warning: No Census API key found. Set CENSUS_API_KEY environment variable.")
        return None
    
    try:
        acs_year = "2022"
        
        url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
        params = {
            'get': 'NAME,B19113_001E',
            'for': f'state:{state_fips}',
            'key': api_key
        }
        
        print(f"Fetching state median income from Census API: {url}")
        print(f"Parameters: state={state_fips}, key={'*' * (len(api_key) - 4) + api_key[-4:] if api_key else 'None'}")
        
        response = requests.get(url, params=params, timeout=10)
        print(f"Census API response status: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        print(f"Census API response data: {data}")
        
        if len(data) > 1 and len(data[1]) > 1:
            income_str = data[1][1]  # B19113_001E value
            print(f"Raw income value from Census API: '{income_str}'")
            
            if income_str and income_str != '-888888888' and income_str != 'null':
                try:
                    income = float(income_str)
                    print(f"[OK] Found state median family income: ${income:,.0f} for state FIPS {state_fips}")
                    return income
                except ValueError as ve:
                    print(f"[ERROR] Could not convert income value '{income_str}' to float: {ve}")
            else:
                print(f"[ERROR] Income value is null or error code: '{income_str}'")
        else:
            print(f"[ERROR] Unexpected response format. Expected at least 2 rows, got {len(data)} rows")
            print(f"Response: {data}")
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] HTTP error fetching state median family income: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text[:500]}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[ERROR] Error fetching state median family income: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_cbsa_median_family_income(cbsa_code: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get median family income for a CBSA (metro area) from Census API.
    
    Uses ACS 5-Year Estimates, variable B19113_001E (Median Family Income).
    
    Args:
        cbsa_code: CBSA code (metro area code)
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Median family income in dollars, or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()
    
    if not api_key:
        print("Warning: No Census API key found. Set CENSUS_API_KEY environment variable.")
        return None
    
    try:
        # Use most recent ACS 5-year estimates (2022 = 2018-2022 data)
        acs_year = "2022"
        
        # Census API endpoint for ACS 5-year estimates
        # B19113_001E = Median Family Income
        # Note: For CBSA, we need to use the correct geography code
        url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
        params = {
            'get': 'NAME,B19113_001E',
            'for': f'metropolitan statistical area/micropolitan statistical area:{cbsa_code}',
            'key': api_key
        }
        
        # Try alternative format if first doesn't work
        # Some CBSAs might need different geography specification
        
        print(f"Fetching CBSA median income from Census API: {url}")
        print(f"Parameters: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"Census API response: {data}")
        
        # First row is headers, second row is data
        if len(data) > 1 and len(data[1]) > 1:
            income_str = data[1][1]  # B19113_001E value
            print(f"Raw income value from Census API: '{income_str}'")
            
            if income_str and income_str != '-888888888':  # Census uses -888888888 for nulls
                try:
                    income = float(income_str)
                    print(f"[OK] Found CBSA median family income: ${income:,.0f} for CBSA code {cbsa_code}")
                    return income
                except ValueError as ve:
                    print(f"[ERROR] Could not convert income value '{income_str}' to float: {ve}")
            else:
                print(f"[ERROR] Income value is null or error code: '{income_str}'")
        else:
            print(f"[ERROR] Unexpected response format. Expected at least 2 rows, got {len(data)} rows")
            if len(data) > 0:
                print(f"Response structure: {data[0]}")
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] HTTP error fetching CBSA median family income: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text[:500]}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[ERROR] Error fetching CBSA median family income: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_tract_income_data(state_fips: str, county_fips: str, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get median family income for all census tracts in a county from Census API.
    
    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        List of dictionaries with tract data including:
        - tract_geoid: 11-digit census tract GEOID
        - tract_name: Tract name
        - median_family_income: Median family income in dollars
    """
    if api_key is None:
        api_key = get_census_api_key()
    
    if not api_key:
        print("Warning: No Census API key found. Set CENSUS_API_KEY environment variable.")
        return []
    
    try:
        # Use most recent ACS 5-year estimates (2022 = 2018-2022 data)
        acs_year = "2022"
        
        # Census API endpoint for ACS 5-year estimates
        # B19113_001E = Median Family Income
        url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
        params = {
            'get': 'NAME,B19113_001E,GEO_ID',
            'for': f'tract:*',
            'in': f'state:{state_fips} county:{county_fips}',
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # First row is headers
        if len(data) < 2:
            return []
        
        headers = data[0]
        name_idx = headers.index('NAME')
        income_idx = headers.index('B19113_001E')
        geo_id_idx = headers.index('GEO_ID')
        tract_idx = headers.index('tract')
        
        tracts = []
        for row in data[1:]:
            tract_name = row[name_idx]
            income_str = row[income_idx]
            geo_id = row[geo_id_idx]
            tract_code = row[tract_idx]
            
            # Create 11-digit GEOID: state (2) + county (3) + tract (6)
            tract_geoid = f"{state_fips}{county_fips}{tract_code.zfill(6)}"
            
            # Parse income (Census uses -888888888 for nulls/errors, also -666666666 for other errors)
            # Filter out invalid values: negative, null, or Census sentinel values
            median_income = None
            if income_str:
                # Check for Census sentinel values indicating missing/invalid data
                invalid_values = ['-888888888', '-666666666', '-999999999', 'null', 'None', '']
                if income_str not in invalid_values:
                    try:
                        income_value = float(income_str)
                        # Only accept positive income values
                        if income_value > 0:
                            median_income = income_value
                        else:
                            print(f"Filtering out tract {tract_geoid} ({tract_name}): Invalid negative income value: {income_value}")
                    except ValueError:
                        print(f"Filtering out tract {tract_geoid} ({tract_name}): Could not parse income value: '{income_str}'")
                else:
                    # Census sentinel value - skip this tract
                    print(f"Filtering out tract {tract_geoid} ({tract_name}): Census sentinel value for income: {income_str}")
            
            # Only add tract if it has valid income data
            if median_income is not None:
                tracts.append({
                    'tract_geoid': tract_geoid,
                    'tract_name': tract_name,
                    'tract_code': tract_code,
                    'median_family_income': median_income
                })
        
        valid_tracts = len(tracts)
        print(f"Fetched income data for {valid_tracts} valid census tracts (invalid/water tracts filtered out)")
        return tracts
        
    except Exception as e:
        print(f"Error fetching tract income data: {e}")
        import traceback
        traceback.print_exc()
        return []


def categorize_income_level(tract_income: Optional[float], cbsa_income: Optional[float]) -> str:
    """
    Categorize a census tract's income level based on CBSA median.
    
    Categories:
    - Low income: ≤50% of CBSA median
    - Moderate income: ≤80% of CBSA median
    - Middle income: ≤120% of CBSA median
    - Upper income: >120% of CBSA median
    
    Args:
        tract_income: Median family income for the tract (in dollars)
        cbsa_income: Median family income for the CBSA (in dollars)
    
    Returns:
        Income category string, or 'Unknown' if data unavailable
    """
    if tract_income is None or cbsa_income is None or cbsa_income <= 0:
        return 'Unknown'
    
    ratio = tract_income / cbsa_income
    
    if ratio <= 0.50:
        return 'Low'
    elif ratio <= 0.80:
        return 'Moderate'
    elif ratio <= 1.20:
        return 'Middle'
    else:
        return 'Upper'


def get_cbsa_minority_percentage(cbsa_code: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get minority population percentage for a CBSA (metro area) from Census API.
    
    Minority = Total population - Non-Hispanic White alone
    Uses ACS 5-Year Estimates.
    
    Args:
        cbsa_code: CBSA code (metro area code)
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Minority population percentage (0-100), or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()
    
    if not api_key:
        print("Warning: No Census API key found. Set CENSUS_API_KEY environment variable.")
        return None
    
    try:
        acs_year = "2022"
        
        # Census API variables:
        # B01003_001E = Total population
        # B03002_003E = White alone, not Hispanic or Latino
        url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
        params = {
            'get': 'NAME,B01003_001E,B03002_003E',
            'for': f'metropolitan statistical area/micropolitan statistical area:{cbsa_code}',
            'key': api_key
        }
        
        print(f"Fetching CBSA minority data from Census API: {url}")
        print(f"Parameters: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"Census API response: {data}")
        
        if len(data) > 1 and len(data[1]) > 2:
            total_pop = data[1][1]  # B01003_001E
            white_non_hisp = data[1][2]  # B03002_003E
            
            print(f"Raw data - Total pop: {total_pop}, White non-Hispanic: {white_non_hisp}")
            
            if total_pop and white_non_hisp and total_pop != '-888888888' and white_non_hisp != '-888888888':
                try:
                    total = float(total_pop)
                    white = float(white_non_hisp)
                    if total > 0:
                        minority = total - white
                        percentage = (minority / total) * 100
                        print(f"[OK] Calculated CBSA minority percentage: {percentage:.1f}% (Total: {total:,.0f}, White: {white:,.0f}, Minority: {minority:,.0f})")
                        return percentage
                    else:
                        print(f"[ERROR] Total population is 0 or negative: {total}")
                except (ValueError, TypeError) as ve:
                    print(f"[ERROR] Could not convert population values to float: {ve}")
            else:
                print(f"[ERROR] Invalid population data - Total: '{total_pop}', White: '{white_non_hisp}'")
        else:
            print(f"[ERROR] Unexpected response format. Expected at least 2 rows with 3 columns, got {len(data)} rows")
            if len(data) > 0:
                print(f"Response structure: {data[0]}")
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] HTTP error fetching CBSA minority percentage: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text[:500]}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[ERROR] Error fetching CBSA minority percentage: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_tract_minority_data(state_fips: str, county_fips: str, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get minority population data for all census tracts in a county from Census API.
    
    Minority = Total population - Non-Hispanic White alone
    
    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        List of dictionaries with tract data including:
        - tract_geoid: 11-digit census tract GEOID
        - tract_name: Tract name
        - total_population: Total population
        - minority_population: Minority population (non-Hispanic white excluded)
        - minority_percentage: Percentage of minority population
    """
    if api_key is None:
        api_key = get_census_api_key()
    
    if not api_key:
        print("Warning: No Census API key found. Set CENSUS_API_KEY environment variable.")
        return []
    
    try:
        acs_year = "2022"
        
        # Census API variables:
        # B01003_001E = Total population
        # B03002_003E = White alone, not Hispanic or Latino
        url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
        params = {
            'get': 'NAME,B01003_001E,B03002_003E,GEO_ID',
            'for': f'tract:*',
            'in': f'state:{state_fips} county:{county_fips}',
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if len(data) < 2:
            return []
        
        headers = data[0]
        name_idx = headers.index('NAME')
        total_pop_idx = headers.index('B01003_001E')
        white_non_hisp_idx = headers.index('B03002_003E')
        geo_id_idx = headers.index('GEO_ID')
        tract_idx = headers.index('tract')
        
        tracts = []
        for row in data[1:]:
            tract_name = row[name_idx]
            total_pop_str = row[total_pop_idx]
            white_non_hisp_str = row[white_non_hisp_idx]
            geo_id = row[geo_id_idx]
            tract_code = row[tract_idx]
            
            # Create 11-digit GEOID: state (2) + county (3) + tract (6)
            tract_geoid = f"{state_fips}{county_fips}{tract_code.zfill(6)}"
            
            # Parse population data
            # Filter out invalid values: Census sentinel values indicating missing/invalid data
            total_pop = None
            white_non_hisp = None
            minority_percentage = None
            
            invalid_values = ['-888888888', '-666666666', '-999999999', 'null', 'None', '']
            
            if total_pop_str and total_pop_str not in invalid_values:
                try:
                    pop_value = float(total_pop_str)
                    # Only accept positive population values
                    if pop_value > 0:
                        total_pop = pop_value
                    else:
                        print(f"Filtering out tract {tract_geoid} ({tract_name}): Invalid total population: {pop_value}")
                except ValueError:
                    print(f"Filtering out tract {tract_geoid} ({tract_name}): Could not parse total population: '{total_pop_str}'")
            elif total_pop_str in invalid_values:
                print(f"Filtering out tract {tract_geoid} ({tract_name}): Census sentinel value for total population: {total_pop_str}")
            
            if white_non_hisp_str and white_non_hisp_str not in invalid_values:
                try:
                    white_value = float(white_non_hisp_str)
                    # Accept non-negative values (could be 0)
                    if white_value >= 0:
                        white_non_hisp = white_value
                    else:
                        print(f"Filtering out tract {tract_geoid} ({tract_name}): Invalid white non-Hispanic population: {white_value}")
                except ValueError:
                    print(f"Filtering out tract {tract_geoid} ({tract_name}): Could not parse white non-Hispanic population: '{white_non_hisp_str}'")
            elif white_non_hisp_str in invalid_values:
                print(f"Filtering out tract {tract_geoid} ({tract_name}): Census sentinel value for white non-Hispanic population: {white_non_hisp_str}")
            
            # Calculate minority percentage only if we have valid data
            if total_pop and total_pop > 0 and white_non_hisp is not None and white_non_hisp >= 0:
                minority_pop = total_pop - white_non_hisp
                if minority_pop >= 0:  # Minority population should be non-negative
                    minority_percentage = (minority_pop / total_pop) * 100
                else:
                    print(f"Filtering out tract {tract_geoid} ({tract_name}): Invalid minority calculation (minority_pop < 0)")
            
            # Only add tract if it has valid minority data
            if total_pop is not None and total_pop > 0 and white_non_hisp is not None and minority_percentage is not None:
                tracts.append({
                    'tract_geoid': tract_geoid,
                    'tract_name': tract_name,
                    'tract_code': tract_code,
                    'total_population': total_pop,
                    'minority_population': minority_pop,
                    'minority_percentage': minority_percentage
                })
            else:
                print(f"Filtering out tract {tract_geoid} ({tract_name}): Missing or invalid minority data")
        
        valid_tracts = len(tracts)
        print(f"Fetched minority data for {valid_tracts} valid census tracts (invalid/water tracts filtered out)")
        return tracts
        
    except Exception as e:
        print(f"Error fetching tract minority data: {e}")
        import traceback
        traceback.print_exc()
        return []


def categorize_minority_level(tract_minority_pct: Optional[float], cbsa_minority_pct: Optional[float]) -> tuple:
    """
    Categorize a census tract's minority level based on CBSA baseline using relative ratio.
    
    Uses ratio method: Tract % / Metro %
    Categories:
    - Very High: Ratio ≥ 2.0 (tract has 2x+ metro average)
    - High: Ratio 1.5-2.0 (tract has 50-100% more than metro)
    - Above Average: Ratio 1.2-1.5 (tract has 20-50% more)
    - Average: Ratio 0.8-1.2 (within 20% of metro)
    - Below Average: Ratio < 0.8 (below metro average)
    
    Args:
        tract_minority_pct: Minority percentage for the tract (0-100)
        cbsa_minority_pct: Minority percentage for the CBSA (0-100)
    
    Returns:
        Tuple of (category, ratio) or ('Unknown', None) if data unavailable
    """
    if tract_minority_pct is None or cbsa_minority_pct is None or cbsa_minority_pct <= 0:
        return ('Unknown', None)
    
    ratio = tract_minority_pct / cbsa_minority_pct
    
    if ratio >= 2.0:
        return ('Very High', ratio)
    elif ratio >= 1.5:
        return ('High', ratio)
    elif ratio >= 1.2:
        return ('Above Average', ratio)
    elif ratio >= 0.8:
        return ('Average', ratio)
    else:
        return ('Below Average', ratio)


def get_tract_boundaries_geojson(state_fips: str, county_fips: str) -> Optional[Dict]:
    """
    Fetch census tract boundaries as GeoJSON from Census TIGER/Line files.
    
    Uses the Census Bureau's TIGERweb service to get tract boundaries.
    
    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code
    
    Returns:
        GeoJSON dictionary with tract boundaries, or None if unavailable
    """
    try:
        # Census TIGERweb REST API endpoint
        # This gets 2020 census tract boundaries
        url = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/8/query"
        
        # Create query for specific county
        params = {
            'where': f"STATE='{state_fips}' AND COUNTY='{county_fips}'",
            'outFields': 'GEOID,NAME,STATE,COUNTY,TRACT',
            'f': 'geojson',
            'outSR': '4326'  # WGS84 coordinate system
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        geojson = response.json()
        
        if 'features' in geojson and len(geojson['features']) > 0:
            print(f"Fetched {len(geojson['features'])} tract boundaries")
            return geojson
        
        return None
        
    except Exception as e:
        print(f"Error fetching tract boundaries: {e}")
        import traceback
        traceback.print_exc()
        return None


def categorize_income_level(tract_income: float, county_income: float) -> str:
    """
    Categorize a census tract's income level relative to county median income.
    
    Categories:
    - Low: ≤50% of county median
    - Moderate: ≤80% of county median
    - Middle: ≤120% of county median
    - Upper: >120% of county median
    
    Args:
        tract_income: Tract median family income
        county_income: County median family income
    
    Returns:
        Income category string, or 'Unknown' if data unavailable
    """
    if tract_income is None or county_income is None or county_income <= 0:
        return 'Unknown'
    
    ratio = tract_income / county_income
    
    if ratio <= 0.50:
        return 'Low'
    elif ratio <= 0.80:
        return 'Moderate'
    elif ratio <= 1.20:
        return 'Middle'
    else:
        return 'Upper'


def categorize_minority_level(tract_minority_pct: float, county_minority_pct: float) -> tuple:
    """
    Categorize a census tract's minority percentage relative to county average.
    
    Categories based on ratio to county:
    - Very High: ≥2.0x county average
    - High: 1.5-2.0x county average
    - Above Average: 1.2-1.5x county average
    - Average: 0.8-1.2x county average
    - Below Average: <0.8x county average
    
    Args:
        tract_minority_pct: Tract minority percentage (0-100)
        county_minority_pct: County minority percentage (0-100)
    
    Returns:
        Tuple of (category string, ratio float), or ('Unknown', None) if data unavailable
    """
    if tract_minority_pct is None or county_minority_pct is None or county_minority_pct <= 0:
        return ('Unknown', None)
    
    ratio = tract_minority_pct / county_minority_pct
    
    if ratio >= 2.0:
        return ('Very High', ratio)
    elif ratio >= 1.5:
        return ('High', ratio)
    elif ratio >= 1.2:
        return ('Above Average', ratio)
    elif ratio >= 0.8:
        return ('Average', ratio)
    else:
        return ('Below Average', ratio)

