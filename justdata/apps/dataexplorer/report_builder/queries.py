"""Census ACS housing data queries for the area report builder."""
import logging
import os
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from requests.exceptions import HTTPError, RequestException, Timeout

logger = logging.getLogger(__name__)


def _census_api_request_with_retry(
    url: str,
    params: dict,
    max_retries: int = 3,
    base_delay: float = 1.0,
    timeout: int = 15,
    description: str = "Census API"
) -> Optional[dict]:
    """
    Make a Census API request with retry logic and exponential backoff.

    Args:
        url: The API endpoint URL
        params: Query parameters for the request
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        timeout: Request timeout in seconds
        description: Description for logging

    Returns:
        Parsed JSON response or None if all retries failed
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt) + (time.time() % 1)
                logger.info(f"[{description}] Retry {attempt + 1}/{max_retries} after {delay:.1f}s delay...")
                time.sleep(delay)

            response = requests.get(url, params=params, timeout=timeout)

            # Handle rate limiting (429) and service unavailable (503)
            if response.status_code == 429:
                logger.warning(f"[{description}] Rate limited (429), will retry...")
                last_error = "Rate limited (429)"
                continue

            if response.status_code == 503:
                logger.warning(f"[{description}] Service unavailable (503), will retry...")
                last_error = "Service unavailable (503)"
                continue

            if response.status_code != 200:
                logger.warning(f"[{description}] HTTP {response.status_code}: {response.text[:200]}")
                last_error = f"HTTP {response.status_code}"
                continue

            # Parse JSON response
            try:
                data = response.json()
                if data and len(data) > 1:
                    return data
                else:
                    logger.warning(f"[{description}] Empty or invalid response")
                    last_error = "Empty response"
                    continue
            except Exception as json_err:
                logger.warning(f"[{description}] JSON parse error: {json_err}. Response preview: {response.text[:300]}")
                last_error = f"JSON parse error: {json_err}"
                continue

        except Timeout:
            logger.warning(f"[{description}] Request timed out (timeout={timeout}s)")
            last_error = "Timeout"
            continue
        except RequestException as e:
            logger.warning(f"[{description}] Request failed: {e}")
            last_error = str(e)
            continue
        except Exception as e:
            logger.warning(f"[{description}] Unexpected error: {e}")
            last_error = str(e)
            continue

    logger.error(f"[{description}] All {max_retries} retries failed. Last error: {last_error}")
    return None


# Delay between Census API calls to avoid rate limiting
_CENSUS_API_DELAY = 0.3  # 300ms between requests


def fetch_acs_housing_data(geoids: List[str], api_key: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Fetch ACS housing data for multiple counties.
    
    Fetches:
    - Median home value (B25077_001E)
    - Median selected monthly owner costs (B25088_001E)
    - Median gross rent (B25064_001E)
    - Owner cost burden (B25091_001E - median selected monthly owner costs as % of income)
    - Rental burden (B25070_001E - gross rent as % of income)
    - Owner occupied units (B25003_002E)
    - Total occupied units (B25003_001E)
    - Total housing units (B25001_001E)
    - 1-unit detached (B25024_002E)
    - 1-unit attached (B25024_003E)
    - 2 units (B25024_004E)
    - 3-4 units (B25024_005E)
    - Mobile home (B25024_010E)
    - Owner occupied by race/ethnicity (B25003B_002E, B25003C_002E, B25003D_002E, B25003E_002E, B25003F_002E, B25003G_002E, B25003H_002E, B25003I_002E)
    
    Args:
        geoids: List of 5-digit GEOID5 codes (counties)
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Dictionary mapping geoid5 to housing data with structure:
        {
            'geoid5': {
                'time_periods': {
                    'acs_2006_2010': {...},
                    'acs_2016_2020': {...},
                    'acs_recent': {...}
                }
            }
        }
    """
    if api_key is None:
        # Use unified_env to ensure .env file is loaded (same as census population functions)
        try:
            from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
            ensure_unified_env_loaded(verbose=False)
            config = get_unified_config(load_env=True, verbose=False)
            api_key = config.get('CENSUS_API_KEY')
            if api_key:
                logger.info(f"[DEBUG] Got CENSUS_API_KEY from unified_env (length: {len(api_key)})")
        except ImportError:
            logger.warning("Could not import unified_env, falling back to direct env check")

        # Fallback to direct env check
        if not api_key:
            api_key = os.getenv('CENSUS_API_KEY') or os.getenv('census_api_key')

    if not api_key:
        logger.error("[CRITICAL] CENSUS_API_KEY not set - cannot fetch housing data")
        return {}
    
    if not geoids:
        return {}
    
    # Group geoids by state for efficient processing
    counties_by_state = {}
    for geoid in geoids:
        if len(geoid) != 5:
            continue
        state_fips = geoid[:2]
        county_fips = geoid[2:]
        if state_fips not in counties_by_state:
            counties_by_state[state_fips] = []
        counties_by_state[state_fips].append({
            'geoid5': geoid,
            'county_fips': county_fips
        })
    
    result = {}
    
    # Housing variables to fetch (split into two groups to avoid API issues)
    # Basic housing variables
    housing_vars = [
        'NAME',
        'B25077_001E',  # Median value (dollars) - Owner-occupied housing units
        'B25088_001E',  # Median selected monthly owner costs (dollars) - Owner-occupied housing units
        'B25064_001E',  # Median gross rent (dollars)
        'B19013_001E',  # Median household income (dollars)
        'B25003_001E',  # Total occupied housing units
        'B25003_002E',  # Owner-occupied housing units
        'B25001_001E',  # Total housing units
        'B25024_002E',  # 1-unit, detached
        'B25024_003E',  # 1-unit, attached
        'B25024_004E',  # 2 units
        'B25024_005E',  # 3-4 units
        'B25024_010E',  # Mobile home
        # Owner occupied by race/ethnicity
        'B25003B_002E',  # Black or African American alone - Owner-occupied
        'B25003C_002E',  # American Indian and Alaska Native alone - Owner-occupied
        'B25003D_002E',  # Asian alone - Owner-occupied
        'B25003E_002E',  # Native Hawaiian and Other Pacific Islander alone - Owner-occupied
        'B25003F_002E',  # Some other race alone - Owner-occupied
        'B25003G_002E',  # Two or more races - Owner-occupied
        'B25003H_002E',  # White alone, not Hispanic or Latino - Owner-occupied
        'B25003I_002E',  # Hispanic or Latino - Owner-occupied
        # Total occupied by race/ethnicity (for calculating percentages)
        'B25003B_001E',  # Black or African American alone - Total occupied
        'B25003C_001E',  # American Indian and Alaska Native alone - Total occupied
        'B25003D_001E',  # Asian alone - Total occupied
        'B25003E_001E',  # Native Hawaiian and Other Pacific Islander alone - Total occupied
        'B25003F_001E',  # Some other race alone - Total occupied
        'B25003G_001E',  # Two or more races - Total occupied
        'B25003H_001E',  # White alone, not Hispanic or Latino - Total occupied
        'B25003I_001E',  # Hispanic or Latino - Total occupied
        # NOTE: B25032 variables temporarily removed - may not exist for all ACS years
        # Will add back after testing if they cause API failures
        # NOTE: B25070 and B25091 burden variables removed - will fetch separately
    ]
    
    # Rent burden variables (B25070): Gross rent as percentage of income
    # We need categories to calculate % of renters who are burdened (30%+)
    rent_burden_vars = [
        'B25070_001E',  # Total renters
        'B25070_007E',  # 30.0 to 34.9 percent
        'B25070_008E',  # 35.0 to 39.9 percent
        'B25070_009E',  # 40.0 to 49.9 percent
        'B25070_010E',  # 50.0 percent or more
    ]
    
    # Owner cost burden variables (B25091): Selected monthly owner costs as percentage of income
    # We need categories to calculate % of owners who are burdened (30%+)
    owner_burden_vars = [
        'B25091_001E',  # Total owners
        'B25091_007E',  # 30.0 to 34.9 percent
        'B25091_008E',  # 35.0 to 39.9 percent
        'B25091_009E',  # 40.0 to 49.9 percent
        'B25091_010E',  # 50.0 percent or more
    ]
    
    
    # Time periods to fetch: 2006-2010, 2016-2020, most recent
    acs_years = [
        (2010, 'acs5', 'acs_2006_2010'),
        (2020, 'acs5', 'acs_2016_2020'),
        (2023, 'acs5', 'acs_recent')  # Will try 2023, 2022, etc. if needed
    ]
    
    # Process each state
    for state_fips, counties in counties_by_state.items():
        for county_info in counties:
            geoid5 = county_info['geoid5']
            county_fips = county_info['county_fips']
            
            county_data = {
                'geoid5': geoid5,
                'time_periods': {}
            }
            
            # Fetch data for each time period
            for year, acs_type, period_key in acs_years:
                if period_key == 'acs_recent':
                    # Try most recent years first
                    attempts = [(2023, 'acs5'), (2022, 'acs5'), (2021, 'acs5')]
                else:
                    attempts = [(year, acs_type)]
                
                data_fetched = False
                for attempt_year, attempt_type in attempts:
                    try:
                        url = f"https://api.census.gov/data/{attempt_year}/acs/{attempt_type}"
                        params = {
                            'get': ','.join(housing_vars),
                            'for': f'county:{county_fips}',
                            'in': f'state:{state_fips}',
                            'key': api_key
                        }

                        logger.info(f"[DEBUG] Fetching ACS {attempt_year} housing data for {geoid5} (state={state_fips}, county={county_fips})")

                        # Use retry helper for robust API calls
                        data = _census_api_request_with_retry(
                            url=url,
                            params=params,
                            max_retries=3,
                            base_delay=1.0,
                            timeout=15,
                            description=f"ACS {attempt_year} housing for {geoid5}"
                        )

                        # Add delay between requests to avoid rate limiting
                        time.sleep(_CENSUS_API_DELAY)

                        if data and len(data) > 1:
                            headers = data[0]
                            row = data[1]
                            record = dict(zip(headers, row))
                            
                            # Extract values
                            def safe_int(v):
                                try:
                                    return int(float(v)) if v and v != 'null' else 0
                                except (ValueError, TypeError):
                                    return 0
                            
                            def safe_float(v):
                                try:
                                    return float(v) if v and v != 'null' else 0.0
                                except (ValueError, TypeError):
                                    return 0.0
                            
                            period_data = {
                                'year': f"{attempt_year} ACS",
                                'median_home_value': safe_int(record.get('B25077_001E', 0)),
                                'median_owner_costs': safe_int(record.get('B25088_001E', 0)),
                                'median_rent': safe_int(record.get('B25064_001E', 0)),
                                # Burden percentages will be calculated from burden category variables
                                'owner_cost_burden_pct': 0.0,  # Will be calculated from B25091 categories
                                'rental_burden_pct': 0.0,  # Will be calculated from B25070 categories
                                'median_household_income': safe_int(record.get('B19013_001E', 0)),
                                'total_occupied_units': safe_int(record.get('B25003_001E', 0)),
                                'owner_occupied_units': safe_int(record.get('B25003_002E', 0)),
                                'total_housing_units': safe_int(record.get('B25001_001E', 0)),
                                'units_1_detached': safe_int(record.get('B25024_002E', 0)),
                                'units_1_attached': safe_int(record.get('B25024_003E', 0)),
                                'units_2': safe_int(record.get('B25024_004E', 0)),
                                'units_3_4': safe_int(record.get('B25024_005E', 0)),
                                'units_mobile': safe_int(record.get('B25024_010E', 0)),
                                # Owner-occupied by structure type (from B25032) - will be 0 if not fetched
                                'owner_occupied_1_detached': 0,  # Will fetch separately if needed
                                'owner_occupied_1_attached': 0,
                                'owner_occupied_2': 0,
                                'owner_occupied_3_4': 0,
                                # Total occupied by structure type (for denominator) - will be 0 if not fetched
                                'occupied_1_detached': 0,
                                'occupied_1_attached': 0,
                                'occupied_2': 0,
                                'occupied_3_4': 0,
                                # Owner occupied by race
                                'owner_occupied_black': safe_int(record.get('B25003B_002E', 0)),
                                'owner_occupied_native': safe_int(record.get('B25003C_002E', 0)),
                                'owner_occupied_asian': safe_int(record.get('B25003D_002E', 0)),
                                'owner_occupied_pacific': safe_int(record.get('B25003E_002E', 0)),
                                'owner_occupied_other': safe_int(record.get('B25003F_002E', 0)),
                                'owner_occupied_multi': safe_int(record.get('B25003G_002E', 0)),
                                'owner_occupied_white': safe_int(record.get('B25003H_002E', 0)),
                                'owner_occupied_hispanic': safe_int(record.get('B25003I_002E', 0)),
                                # Total occupied by race (for percentages)
                                'total_occupied_black': safe_int(record.get('B25003B_001E', 0)),
                                'total_occupied_native': safe_int(record.get('B25003C_001E', 0)),
                                'total_occupied_asian': safe_int(record.get('B25003D_001E', 0)),
                                'total_occupied_pacific': safe_int(record.get('B25003E_001E', 0)),
                                'total_occupied_other': safe_int(record.get('B25003F_001E', 0)),
                                'total_occupied_multi': safe_int(record.get('B25003G_001E', 0)),
                                'total_occupied_white': safe_int(record.get('B25003H_001E', 0)),
                                'total_occupied_hispanic': safe_int(record.get('B25003I_001E', 0)),
                            }
                            
                            # Fetch B25032 variables separately (occupied units by structure type)
                            # These are needed for calculating % of 1-4 units that are owner-occupied
                            b25032_vars = [
                                'B25032_001E',  # Total occupied: 1-unit, detached
                                'B25032_002E',  # Owner-occupied: 1-unit, detached
                                'B25032_004E',  # Total occupied: 1-unit, attached
                                'B25032_005E',  # Owner-occupied: 1-unit, attached
                                'B25032_007E',  # Total occupied: 2 units
                                'B25032_008E',  # Owner-occupied: 2 units
                                'B25032_010E',  # Total occupied: 3-4 units
                                'B25032_011E',  # Owner-occupied: 3-4 units
                            ]

                            try:
                                b25032_url = f"https://api.census.gov/data/{attempt_year}/acs/{attempt_type}"
                                b25032_params = {
                                    'get': ','.join(b25032_vars),
                                    'for': f'county:{county_fips}',
                                    'in': f'state:{state_fips}',
                                    'key': api_key
                                }

                                # Use retry helper for B25032 data
                                b25032_data = _census_api_request_with_retry(
                                    url=b25032_url,
                                    params=b25032_params,
                                    max_retries=2,
                                    base_delay=0.5,
                                    timeout=15,
                                    description=f"B25032 for {geoid5} ({attempt_year})"
                                )
                                time.sleep(_CENSUS_API_DELAY)

                                if b25032_data and len(b25032_data) > 1:
                                    b25032_headers = b25032_data[0]
                                    b25032_row = b25032_data[1]
                                    b25032_record = dict(zip(b25032_headers, b25032_row))

                                    period_data.update({
                                        'owner_occupied_1_detached': safe_int(b25032_record.get('B25032_002E', 0)),
                                        'owner_occupied_1_attached': safe_int(b25032_record.get('B25032_005E', 0)),
                                        'owner_occupied_2': safe_int(b25032_record.get('B25032_008E', 0)),
                                        'owner_occupied_3_4': safe_int(b25032_record.get('B25032_011E', 0)),
                                        'occupied_1_detached': safe_int(b25032_record.get('B25032_001E', 0)),
                                        'occupied_1_attached': safe_int(b25032_record.get('B25032_004E', 0)),
                                        'occupied_2': safe_int(b25032_record.get('B25032_007E', 0)),
                                        'occupied_3_4': safe_int(b25032_record.get('B25032_010E', 0)),
                                    })
                                    logger.info(f"Successfully fetched B25032 data for {geoid5} ({attempt_year})")
                            except Exception as e:
                                logger.warning(f"Could not fetch B25032 data for {geoid5} ({attempt_year}): {e}")
                            
                            # Fetch rent burden categories (B25070) to calculate % of renters who are burdened
                            try:
                                rent_burden_url = f"https://api.census.gov/data/{attempt_year}/acs/{attempt_type}"
                                rent_burden_params = {
                                    'get': ','.join(rent_burden_vars),
                                    'for': f'county:{county_fips}',
                                    'in': f'state:{state_fips}',
                                    'key': api_key
                                }

                                # Use retry helper for rent burden data
                                rent_burden_data = _census_api_request_with_retry(
                                    url=rent_burden_url,
                                    params=rent_burden_params,
                                    max_retries=2,
                                    base_delay=0.5,
                                    timeout=15,
                                    description=f"B25070 rent burden for {geoid5} ({attempt_year})"
                                )
                                time.sleep(_CENSUS_API_DELAY)

                                if rent_burden_data and len(rent_burden_data) > 1:
                                    rent_burden_headers = rent_burden_data[0]
                                    rent_burden_row = rent_burden_data[1]
                                    rent_burden_record = dict(zip(rent_burden_headers, rent_burden_row))

                                    total_renters = safe_int(rent_burden_record.get('B25070_001E', 0))
                                    burdened_renters = (
                                        safe_int(rent_burden_record.get('B25070_007E', 0)) +  # 30.0-34.9%
                                        safe_int(rent_burden_record.get('B25070_008E', 0)) +  # 35.0-39.9%
                                        safe_int(rent_burden_record.get('B25070_009E', 0)) +  # 40.0-49.9%
                                        safe_int(rent_burden_record.get('B25070_010E', 0))    # 50.0%+
                                    )

                                    if total_renters > 0:
                                        period_data['rental_burden_pct'] = (burdened_renters / total_renters) * 100
                                    logger.info(f"Calculated rental burden for {geoid5} ({attempt_year}): {period_data['rental_burden_pct']:.1f}%")
                            except Exception as e:
                                logger.warning(f"Could not fetch B25070 rent burden data for {geoid5} ({attempt_year}): {e}")
                            
                            # Fetch owner cost burden categories (B25091) to calculate % of owners who are burdened
                            try:
                                owner_burden_url = f"https://api.census.gov/data/{attempt_year}/acs/{attempt_type}"
                                owner_burden_params = {
                                    'get': ','.join(owner_burden_vars),
                                    'for': f'county:{county_fips}',
                                    'in': f'state:{state_fips}',
                                    'key': api_key
                                }

                                # Use retry helper for owner burden data
                                owner_burden_data = _census_api_request_with_retry(
                                    url=owner_burden_url,
                                    params=owner_burden_params,
                                    max_retries=2,
                                    base_delay=0.5,
                                    timeout=15,
                                    description=f"B25091 owner burden for {geoid5} ({attempt_year})"
                                )
                                time.sleep(_CENSUS_API_DELAY)

                                if owner_burden_data and len(owner_burden_data) > 1:
                                    owner_burden_headers = owner_burden_data[0]
                                    owner_burden_row = owner_burden_data[1]
                                    owner_burden_record = dict(zip(owner_burden_headers, owner_burden_row))

                                    total_owners = safe_int(owner_burden_record.get('B25091_001E', 0))
                                    burdened_owners = (
                                        safe_int(owner_burden_record.get('B25091_007E', 0)) +  # 30.0-34.9%
                                        safe_int(owner_burden_record.get('B25091_008E', 0)) +  # 35.0-39.9%
                                        safe_int(owner_burden_record.get('B25091_009E', 0)) +  # 40.0-49.9%
                                        safe_int(owner_burden_record.get('B25091_010E', 0))    # 50.0%+
                                    )

                                    if total_owners > 0:
                                        period_data['owner_cost_burden_pct'] = (burdened_owners / total_owners) * 100
                                    logger.info(f"Calculated owner cost burden for {geoid5} ({attempt_year}): {period_data['owner_cost_burden_pct']:.1f}%")
                            except Exception as e:
                                logger.warning(f"Could not fetch B25091 owner burden data for {geoid5} ({attempt_year}): {e}")
                            
                            county_data['time_periods'][period_key] = period_data
                            data_fetched = True
                            logger.info(f"Successfully fetched ACS {attempt_year} housing data for {geoid5}")
                            break
                            
                    except Exception as e:
                        logger.warning(f"Failed to fetch ACS {attempt_year} housing data for {geoid5}: {e}")
                        continue
                
                if not data_fetched and period_key != 'acs_recent':
                    logger.warning(f"Could not fetch {period_key} housing data for {geoid5}")
            
            if county_data['time_periods']:
                result[geoid5] = county_data
    
    return result


