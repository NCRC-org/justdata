#!/usr/bin/env python3
"""
Shared utility for fetching adult population (18+) demographics from Census API.
Uses the most current ACS vintage available.

This utility provides standardized adult population demographics that are more
appropriate for lending analysis than total population, since lending decisions
are made for adults (18+), not children.

Returns data in a format compatible with report generation across all apps.
"""

import os
import requests
from requests.exceptions import HTTPError, Timeout, RequestException
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


def _safe_int(value) -> int:
    """Safely convert value to int, handling None and empty strings."""
    if value is None or value == '':
        return 0
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return 0


def get_most_recent_acs_year() -> int:
    """
    Get the most recent ACS 5-year estimate year available.
    
    As of December 2024, the most current ACS 5-year estimates are:
    - 2023 ACS 5-year (2019-2023 data, released Dec 2024)
    - 2024 ACS 5-year (2020-2024 data) will be released Jan 2026
    
    Returns:
        Year integer (e.g., 2023 for 2019-2023 estimates)
    """
    # Try 2023 first (most recent available as of Dec 2024)
    # Will update to 2024 when released in Jan 2026
    return 2023


def get_adult_population_demographics_for_county(
    state_fips: str,
    county_fips: str,
    county_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get adult population (18+) demographics for a single county using ACS data.
    
    Uses B01001 (Sex by Age) to calculate total adult population, then uses
    race/ethnicity tables to calculate percentages based on total population.
    
    For ACS: Uses B01001 for adult population and B03002 for race/ethnicity.
    Note: B03002 provides race/ethnicity for all ages, so we calculate percentages
    based on total population denominator (not adult population) to avoid inflating percentages.
    We display adult population in the chart, but percentages are mathematically correct.
    
    Args:
        state_fips: Two-digit state FIPS code (e.g., "24" for Maryland)
        county_fips: Three-digit county FIPS code (e.g., "031" for Montgomery County)
        county_name: Optional county name for logging
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Dictionary with adult population demographics:
        {
            'adult_population': int,  # Total population 18+
            'demographics': {
                'white_percentage': float,
                'black_percentage': float,
                'asian_percentage': float,
                'native_american_percentage': float,
                'hopi_percentage': float,
                'multi_racial_percentage': float,
                'hispanic_percentage': float
            }
        }
        Returns empty dict if unavailable.
    """
    if api_key is None:
        # Try uppercase first (standard), then lowercase (some systems use lowercase)
        api_key = os.getenv('CENSUS_API_KEY') or os.getenv('census_api_key')
    
    if not api_key:
        logger.warning("CENSUS_API_KEY not set - Cannot fetch Census data")
        return {}
    
    # Validate FIPS codes
    if not state_fips or not county_fips:
        logger.error(f"Invalid FIPS codes - state_fips: {state_fips}, county_fips: {county_fips}")
        return {}
    
    # Ensure FIPS codes are properly formatted
    state_fips = str(state_fips).zfill(2)
    county_fips = str(county_fips).zfill(3)
    
    display_name = county_name or f"State {state_fips}, County {county_fips}"
    
    # Get most recent ACS year
    acs_year = get_most_recent_acs_year()
    
    # Try ACS 5-year first, then 1-year, with fallback years
    acs_attempts = [
        (acs_year, 'acs5', '5-year'),
        (acs_year, 'acs1', '1-year'),
        (acs_year - 1, 'acs5', '5-year'),
        (acs_year - 1, 'acs1', '1-year'),
    ]
    
    for attempt_year, acs_type, acs_label in acs_attempts:
        try:
            # Step 1: Get adult population (18+) using B01001 (Sex by Age)
            # Sum all age groups 18 and over
            adult_pop_variables = [
                'B01001_001E',  # Total population (for validation)
                # Male age groups 18+
                'B01001_003E',  # Male 18-19
                'B01001_004E',  # Male 20-24
                'B01001_005E',  # Male 25-29
                'B01001_006E',  # Male 30-34
                'B01001_007E',  # Male 35-39
                'B01001_008E',  # Male 40-44
                'B01001_009E',  # Male 45-49
                'B01001_010E',  # Male 50-54
                'B01001_011E',  # Male 55-59
                'B01001_012E',  # Male 60-64
                'B01001_013E',  # Male 65-69
                'B01001_014E',  # Male 70-74
                'B01001_015E',  # Male 75-79
                'B01001_016E',  # Male 80-84
                'B01001_017E',  # Male 85+
                # Female age groups 18+
                'B01001_027E',  # Female 18-19
                'B01001_028E',  # Female 20-24
                'B01001_029E',  # Female 25-29
                'B01001_030E',  # Female 30-34
                'B01001_031E',  # Female 35-39
                'B01001_032E',  # Female 40-44
                'B01001_033E',  # Female 45-49
                'B01001_034E',  # Female 50-54
                'B01001_035E',  # Female 55-59
                'B01001_036E',  # Female 60-64
                'B01001_037E',  # Female 65-69
                'B01001_038E',  # Female 70-74
                'B01001_039E',  # Female 75-79
                'B01001_040E',  # Female 80-84
                'B01001_041E',  # Female 85+
            ]
            
            logger.info(f"Fetching adult population (B01001) from ACS {attempt_year} {acs_label} for {display_name}...")
            url = f"https://api.census.gov/data/{attempt_year}/acs/{acs_type}"
            params = {
                'get': ','.join(adult_pop_variables),
                'for': f'county:{county_fips}',
                'in': f'state:{state_fips}',
                'key': api_key
            }
            # Reduced timeout and better error handling for 503/timeout
            response = requests.get(url, params=params, timeout=10)
            # Check for 503 immediately without waiting
            if response.status_code == 503:
                logger.warning(f"ACS {attempt_year} {acs_label} returned 503 (Service Unavailable) for {display_name} - skipping remaining attempts")
                # If we get 503, the API is down - skip remaining attempts
                break
            response.raise_for_status()
            data = response.json()
            
            if not data or len(data) < 2:
                logger.warning(f"ACS {attempt_year} {acs_label} returned no data for {display_name}")
                continue
            
            headers = data[0]
            row = data[1]
            record = dict(zip(headers, row))
            
            # Calculate adult population (18+) by summing all age groups 18+
            adult_pop = 0
            adult_age_vars = [
                'B01001_003E', 'B01001_004E', 'B01001_005E', 'B01001_006E', 'B01001_007E',
                'B01001_008E', 'B01001_009E', 'B01001_010E', 'B01001_011E', 'B01001_012E',
                'B01001_013E', 'B01001_014E', 'B01001_015E', 'B01001_016E', 'B01001_017E',
                'B01001_027E', 'B01001_028E', 'B01001_029E', 'B01001_030E', 'B01001_031E',
                'B01001_032E', 'B01001_033E', 'B01001_034E', 'B01001_035E', 'B01001_036E',
                'B01001_037E', 'B01001_038E', 'B01001_039E', 'B01001_040E', 'B01001_041E',
            ]
            
            for var in adult_age_vars:
                adult_pop += _safe_int(record.get(var, 0))
            
            if adult_pop == 0:
                logger.warning(f"ACS {attempt_year} {acs_label} returned zero adult population for {display_name}")
                continue
            
            # Step 2: Get race/ethnicity data using B03002
            # Note: B03002 is for all ages, so we use total population as denominator
            race_variables = [
                'B03002_001E',  # Total population (for race breakdown - this is the correct denominator)
                'B03002_003E',  # White alone (not Hispanic)
                'B03002_004E',  # Black or African American alone (not Hispanic)
                'B03002_005E',  # American Indian/Alaska Native alone (not Hispanic)
                'B03002_006E',  # Asian alone (not Hispanic)
                'B03002_007E',  # Native Hawaiian/Pacific Islander alone (not Hispanic)
                'B03002_009E',  # Two or more races (not Hispanic)
                'B03002_012E',  # Hispanic or Latino (of any race)
            ]
            
            logger.info(f"Fetching race/ethnicity (B03002) from ACS {attempt_year} {acs_label} for {display_name}...")
            params_race = {
                'get': ','.join(race_variables),
                'for': f'county:{county_fips}',
                'in': f'state:{state_fips}',
                'key': api_key
            }
            response_race = requests.get(url, params=params_race, timeout=10)
            # Check for 503 immediately
            if response_race.status_code == 503:
                logger.warning(f"ACS {attempt_year} {acs_label} race API returned 503 (Service Unavailable) for {display_name}")
                break
            response_race.raise_for_status()
            data_race = response_race.json()
            
            if not data_race or len(data_race) < 2:
                logger.warning(f"ACS {attempt_year} {acs_label} race data returned no data for {display_name}")
                continue
            
            headers_race = data_race[0]
            row_race = data_race[1]
            record_race = dict(zip(headers_race, row_race))
            
            # Get race/ethnicity counts (all ages - we use total population as denominator)
            white = _safe_int(record_race.get('B03002_003E', 0))
            black = _safe_int(record_race.get('B03002_004E', 0))
            asian = _safe_int(record_race.get('B03002_006E', 0))
            native_am = _safe_int(record_race.get('B03002_005E', 0))
            hopi = _safe_int(record_race.get('B03002_007E', 0))
            multi_racial = _safe_int(record_race.get('B03002_009E', 0))
            hispanic = _safe_int(record_race.get('B03002_012E', 0))
            
            # Calculate percentages based on TOTAL population (not adult population)
            # IMPORTANT: Race/ethnicity data (B03002) is for ALL ages, so we must use total_pop as denominator
            # Using adult_pop as denominator would inflate percentages since race counts include children
            # We display adult_pop in the chart, but percentages are calculated from total population
            
            # Get total population from B03002_001E (Total population for race/ethnicity breakdown)
            # This is the correct denominator since race counts are from B03002 which includes all ages
            total_pop = _safe_int(record_race.get('B03002_001E', 0))  # Total population from B03002
            if total_pop == 0:
                # Fallback: estimate total pop from adult pop (typically ~75-80% of total)
                total_pop = int(adult_pop / 0.77) if adult_pop > 0 else 0
                logger.warning(f"[ACS] B03002_001E was 0, estimated total_pop from adult_pop: {total_pop}")
            
            pop_denominator = total_pop if total_pop > 0 else adult_pop  # Use total pop, fallback to adult if unavailable
            
            result = {
                'adult_population': adult_pop,
                'data_year': f"{attempt_year} (ACS {acs_label} estimates)",
                'data_source': f"ACS {attempt_year} {acs_label}",
                'demographics': {
                    'white_percentage': round((white / pop_denominator * 100) if pop_denominator > 0 else 0, 1),
                    'black_percentage': round((black / pop_denominator * 100) if pop_denominator > 0 else 0, 1),
                    'asian_percentage': round((asian / pop_denominator * 100) if pop_denominator > 0 else 0, 1),
                    'native_american_percentage': round((native_am / pop_denominator * 100) if pop_denominator > 0 else 0, 1),
                    'hopi_percentage': round((hopi / pop_denominator * 100) if pop_denominator > 0 else 0, 1),
                    'multi_racial_percentage': round((multi_racial / pop_denominator * 100) if pop_denominator > 0 else 0, 1),
                    'hispanic_percentage': round((hispanic / pop_denominator * 100) if pop_denominator > 0 else 0, 1)
                }
            }
            
            logger.info(f"Successfully fetched adult population demographics for {display_name}: adult_pop={adult_pop}, year={attempt_year} {acs_label}")
            return result
            
        except HTTPError as e:
            # Handle HTTP errors (like 503) - fail fast
            if e.response and e.response.status_code == 503:
                logger.warning(f"ACS API returned 503 (Service Unavailable) for {display_name} - Census API is down, skipping remaining attempts")
                break  # Don't try other years if API is down
            logger.warning(f"Failed to fetch ACS {attempt_year} {acs_label} data for {display_name}: {e}")
            continue
        except Timeout as e:
            logger.warning(f"ACS {attempt_year} {acs_label} request timed out for {display_name} (timeout: 10s)")
            continue
        except RequestException as e:
            logger.warning(f"ACS {attempt_year} {acs_label} request failed for {display_name}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Failed to fetch ACS {attempt_year} {acs_label} data for {display_name}: {e}")
            if (attempt_year, acs_type) == acs_attempts[-1][:2]:  # Last attempt
                logger.error(f"All ACS attempts failed for {display_name}")
            continue
    
    logger.warning(f"Could not fetch adult population demographics for {display_name}")
    return {}


def get_adult_population_demographics_for_geoids(
    geoids: List[str],
    api_key: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Get adult population (18+) demographics for multiple counties by GEOID5.
    
    Args:
        geoids: List of 5-digit GEOID5 codes (counties)
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Dictionary mapping geoid5 to adult population demographics:
        {
            'geoid5': {
                'county_name': str,
                'state_fips': str,
                'county_fips': str,
                'adult_population': int,
                'data_year': str,
                'data_source': str,
                'demographics': {
                    'white_percentage': float,
                    'black_percentage': float,
                    ...
                }
            }
        }
    """
    if api_key is None:
        # Try uppercase first (standard), then lowercase (some systems use lowercase)
        api_key = os.getenv('CENSUS_API_KEY') or os.getenv('census_api_key')
    
    if not api_key:
        logger.warning("CENSUS_API_KEY not set - cannot fetch Census data")
        return {}
    
    if not geoids:
        return {}
    
    result = {}
    
    # Process each geoid
    for geoid in geoids:
        if len(geoid) != 5:
            logger.warning(f"Invalid geoid length: {geoid} (expected 5 digits)")
            continue
        
        state_fips = geoid[:2]
        county_fips = geoid[2:]
        
        county_data = get_adult_population_demographics_for_county(
            state_fips=state_fips,
            county_fips=county_fips,
            county_name=f"County {county_fips}, State {state_fips}",
            api_key=api_key
        )
        
        if county_data:
            county_data['geoid5'] = geoid
            county_data['state_fips'] = state_fips
            county_data['county_fips'] = county_fips
            result[geoid] = county_data
    
    return result
