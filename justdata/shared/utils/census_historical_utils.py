#!/usr/bin/env python3
"""
Historical Census data utilities.
Fetches 2010, 2020, and most recent ACS census data for counties.
Originally from DataExplorer v1, moved to shared/utils/ on December 19, 2025.
Used by BizSight and BranchSight for historical census data in reports.
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


def get_most_recent_acs_year() -> str:
    """
    Get the most recent ACS 5-year estimate year available.
    
    Returns:
        Year string (e.g., '2023' for 2019-2023 estimates)
    """
    # ACS 5-year estimates are typically released in December
    # As of December 2024, most current is 2023 ACS 5-year (2019-2023 data, released Dec 2024)
    # 2024 ACS 5-year (2020-2024 data) will be released Jan 2026
    # Try to use shared utility's function if available, otherwise default to 2023
    try:
        from shared.utils.census_adult_demographics import get_most_recent_acs_year as get_shared_acs_year
        return str(get_shared_acs_year())
    except ImportError:
        return "2023"


def get_census_data_for_geoids(geoids: List[str], api_key: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Get census data (2010, 2020, most recent ACS) for multiple counties by GEOID5.
    
    Args:
        geoids: List of 5-digit GEOID5 codes (counties)
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Dictionary mapping geoid5 to census data with structure:
        {
            'geoid5': {
                'county_name': str,
                'state_fips': str,
                'county_fips': str,
                'time_periods': {
                    'census2010': { 'year': '2010 Census', 'demographics': {...} },
                    'census2020': { 'year': '2020 Census', 'demographics': {...} },
                    'acs': { 'year': '2024 ACS', 'demographics': {...} }
                }
            }
        }
    """
    if api_key is None:
        # Try uppercase first (standard), then lowercase (some systems use lowercase)
        api_key = os.getenv('CENSUS_API_KEY') or os.getenv('census_api_key')
    
    if not api_key:
        logger.error("[CRITICAL] CENSUS_API_KEY not set - cannot fetch Census data. This will cause empty historical_census_data!")
        logger.error("[CRITICAL] Checked both CENSUS_API_KEY and census_api_key environment variables")
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
    
    # Process each state
    for state_fips, counties in counties_by_state.items():
        for county_info in counties:
            geoid5 = county_info['geoid5']
            county_fips = county_info['county_fips']
            
            # Get county name from geo table (we'll fetch it if needed)
            logger.info(f"[DEBUG] get_census_data_for_geoids: Calling get_census_data_for_county for {geoid5} (state_fips={state_fips}, county_fips={county_fips})")
            county_data = get_census_data_for_county(
                state_fips=state_fips,
                county_fips=county_fips,
                county_name=f"County {county_fips}, State {state_fips}",
                api_key=api_key
            )
            
            logger.info(f"[DEBUG] get_census_data_for_geoids: get_census_data_for_county returned type={type(county_data)}, empty={not county_data}")
            if county_data:
                time_periods = county_data.get('time_periods', {})
                logger.info(f"[DEBUG] get_census_data_for_geoids: county_data has time_periods type={type(time_periods)}, keys={list(time_periods.keys()) if time_periods else 'EMPTY'}")
                result[geoid5] = county_data
                logger.info(f"[DEBUG] get_census_data_for_geoids: Added data for {geoid5}, time_periods keys: {list(time_periods.keys()) if time_periods else 'EMPTY'}")
            else:
                logger.error(f"[CRITICAL] get_census_data_for_geoids: No data returned for {geoid5} (state_fips={state_fips}, county_fips={county_fips})")
                logger.error(f"[CRITICAL] This means get_census_data_for_county returned empty dict - check API calls above")
    
    return result


def get_census_data_for_county(
    state_fips: str,
    county_fips: str,
    county_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get census data for a single county.
    Fetches:
    - Most recent ACS 5-year estimates (2024/2022)
    - 2020 Decennial Census
    - 2010 Decennial Census
    
    Args:
        state_fips: Two-digit state FIPS code (e.g., "24" for Maryland)
        county_fips: Three-digit county FIPS code (e.g., "031" for Montgomery County)
        county_name: Optional county name for logging
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Dictionary with demographic data for all three time periods, or empty dict if unavailable
    """
    try:
        # Get API key
        if api_key is None:
            # Try uppercase first (standard), then lowercase (some systems use lowercase)
            api_key = os.getenv('CENSUS_API_KEY') or os.getenv('census_api_key')
        
        if not api_key:
            logger.error("[CRITICAL] CENSUS_API_KEY not set - Cannot fetch Census data")
            logger.error("[CRITICAL] Checked both CENSUS_API_KEY and census_api_key environment variables")
            return {}
        
        # Log API key status (first 8 and last 4 chars for debugging)
        api_key_preview = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        logger.info(f"[DEBUG] get_census_data_for_county: API key present (preview: {api_key_preview}), state_fips={state_fips}, county_fips={county_fips}")
        
        # Validate FIPS codes
        if not state_fips or not county_fips:
            logger.error(f"Invalid FIPS codes - state_fips: {state_fips}, county_fips: {county_fips}")
            return {}
        
        # Ensure FIPS codes are properly formatted
        state_fips = str(state_fips).zfill(2)
        county_fips = str(county_fips).zfill(3)
        
        display_name = county_name or f"State {state_fips}, County {county_fips}"
        
        result = {
            'county_name': display_name,
            'state_fips': state_fips,
            'county_fips': county_fips,
            'time_periods': {}
        }
        
        # 1. Fetch most recent ACS estimates using shared utility for adult population (18+)
        try:
            from shared.utils.census_adult_demographics import get_adult_population_demographics_for_county
            
            logger.info(f"Fetching adult population (18+) demographics from ACS for {display_name}...")
            acs_adult_data = get_adult_population_demographics_for_county(
                state_fips=state_fips,
                county_fips=county_fips,
                county_name=display_name,
                api_key=api_key
            )
            
            if acs_adult_data and acs_adult_data.get('adult_population', 0) > 0:
                # Extract year from data_source (e.g., "ACS 2023 5-year" -> "2023 ACS")
                data_source = acs_adult_data.get('data_source', '')
                data_year = acs_adult_data.get('data_year', '')
                
                # Extract year number from data_source
                import re
                year_match = re.search(r'(\d{4})', data_source)
                acs_year_str = year_match.group(1) if year_match else '2023'
                
                result['time_periods']['acs'] = {
                    'year': f"{acs_year_str} ACS",
                    'data_year': data_year,
                    'demographics': {
                        'total_population': acs_adult_data['adult_population'],  # Using adult population
                        'white_percentage': acs_adult_data['demographics']['white_percentage'],
                        'black_percentage': acs_adult_data['demographics']['black_percentage'],
                        'asian_percentage': acs_adult_data['demographics']['asian_percentage'],
                        'native_american_percentage': acs_adult_data['demographics']['native_american_percentage'],
                        'hopi_percentage': acs_adult_data['demographics']['hopi_percentage'],
                        'multi_racial_percentage': acs_adult_data['demographics']['multi_racial_percentage'],
                        'hispanic_percentage': acs_adult_data['demographics']['hispanic_percentage']
                    }
                }
                logger.info(f"Successfully fetched adult population ACS data for {display_name}: adult_pop={acs_adult_data['adult_population']}")
            else:
                logger.warning(f"Could not fetch adult population ACS data for {display_name}")
        except ImportError:
            logger.warning("Could not import shared.utils.census_adult_demographics - falling back to total population")
            # Fallback to old method if shared utility not available
            acs_data_fetched = False
            acs_year = get_most_recent_acs_year()
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
            acs_attempts = [
                (2023, 'acs5', '5-year'),
                (2023, 'acs1', '1-year'),
                (2022, 'acs5', '5-year'),
                (2022, 'acs1', '1-year')
            ]
            for attempt_year, acs_type, acs_label in acs_attempts:
                try:
                    logger.info(f"Fetching ACS {attempt_year} {acs_label} estimates for {display_name}...")
                    url = f"https://api.census.gov/data/{attempt_year}/acs/{acs_type}"
                    params = {
                        'get': ','.join(acs_variables),
                        'for': f'county:{county_fips}',
                        'in': f'state:{state_fips}',
                        'key': api_key
                    }
                    # Log the actual API call
                    logger.info(f"[DEBUG] ACS API Call - URL: {url}")
                    logger.info(f"[DEBUG] ACS API Call - Params: for=county:{county_fips}, in=state:{state_fips}, get={','.join(acs_variables[:5])}... (truncated)")
                    logger.info(f"[DEBUG] ACS API Call - Full params: {params}")
                    # Reduced timeout and better error handling
                    response = requests.get(url, params=params, timeout=10)
                    logger.info(f"[DEBUG] ACS API Response - Status: {response.status_code}, URL: {response.url}")
                    if response.status_code != 200:
                        logger.error(f"[DEBUG] ACS API Response - Error: {response.text[:500]}")
                    # Check for 503 immediately
                    if response.status_code == 503:
                        logger.warning(f"ACS {attempt_year} {acs_label} returned 503 (Service Unavailable) for {display_name} - skipping remaining attempts")
                        break
                    response.raise_for_status()
                    data = response.json()
                    
                    if data and len(data) > 1:
                        headers = data[0]
                        row = data[1]
                        record = dict(zip(headers, row))
                        
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
                                'year': f"{attempt_year} ACS",
                                'data_year': f"{attempt_year} (ACS {acs_label} estimates)",
                                'demographics': {
                                    'total_population': total_pop or 0,
                                    'white_percentage': (white / total_pop * 100) if total_pop > 0 else 0,
                                    'black_percentage': (black / total_pop * 100) if total_pop > 0 else 0,
                                    'asian_percentage': (asian / total_pop * 100) if total_pop > 0 else 0,
                                    'native_american_percentage': (native_am / total_pop * 100) if total_pop > 0 else 0,
                                    'hopi_percentage': (hopi / total_pop * 100) if total_pop > 0 else 0,
                                    'multi_racial_percentage': (multi_racial / total_pop * 100) if total_pop > 0 else 0,
                                    'hispanic_percentage': (hispanic / total_pop * 100) if total_pop > 0 else 0
                                }
                            }
                            acs_data_fetched = True
                            logger.info(f"Successfully fetched ACS {attempt_year} {acs_label} data for {display_name}: pop={total_pop}")
                            break
                except HTTPError as e:
                    if e.response and e.response.status_code == 503:
                        logger.warning(f"ACS API returned 503 (Service Unavailable) for {display_name} - skipping remaining attempts")
                        break
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
                    continue
        except Exception as e:
            logger.error(f"Error fetching adult population ACS data for {display_name}: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. Fetch 2020 Decennial Census (PL94-171) - Adult Population (18+)
        try:
            logger.info(f"Fetching 2020 Decennial Census (adult population 18+) for {display_name}...")
            
            # First, get adult population (18+) from P12 table (Sex by Age) in DHC dataset
            # P12 variables for age groups 18+:
            # Male: P12_005N (18-19), P12_006N (20-24), P12_007N (25-29), P12_008N (30-34),
            #       P12_009N (35-39), P12_010N (40-44), P12_011N (45-49), P12_012N (50-54),
            #       P12_013N (55-59), P12_014N (60-64), P12_015N (65-69), P12_016N (70-74),
            #       P12_017N (75-79), P12_018N (80-84), P12_019N (85+)
            # Female: P12_029N (18-19), P12_030N (20-24), P12_031N (25-29), P12_032N (30-34),
            #         P12_033N (35-39), P12_034N (40-44), P12_035N (45-49), P12_036N (50-54),
            #         P12_037N (55-59), P12_038N (60-64), P12_039N (65-69), P12_040N (70-74),
            #         P12_041N (75-79), P12_042N (80-84), P12_043N (85+)
            
            adult_age_vars_2020 = [
                'P12_005N', 'P12_006N', 'P12_007N', 'P12_008N', 'P12_009N', 'P12_010N',
                'P12_011N', 'P12_012N', 'P12_013N', 'P12_014N', 'P12_015N', 'P12_016N',
                'P12_017N', 'P12_018N', 'P12_019N',  # Male 18+
                'P12_029N', 'P12_030N', 'P12_031N', 'P12_032N', 'P12_033N', 'P12_034N',
                'P12_035N', 'P12_036N', 'P12_037N', 'P12_038N', 'P12_039N', 'P12_040N',
                'P12_041N', 'P12_042N', 'P12_043N'  # Female 18+
            ]
            
            url_age = f"https://api.census.gov/data/2020/dec/dhc"
            params_age = {
                'get': ','.join(adult_age_vars_2020),
                'for': f'county:{county_fips}',
                'in': f'state:{state_fips}',
                'key': api_key
            }
            
            response_age = requests.get(url_age, params=params_age, timeout=10)
            if response_age.status_code == 503:
                logger.warning(f"2020 Census age API returned 503 (Service Unavailable) for {display_name}")
                raise HTTPError(f"2020 Census age API returned 503")
            response_age.raise_for_status()
            data_age = response_age.json()
            
            adult_pop = 0
            if data_age and len(data_age) > 1:
                headers_age = data_age[0]
                row_age = data_age[1]
                record_age = dict(zip(headers_age, row_age))
                
                # Sum all adult age groups
                for var in adult_age_vars_2020:
                    adult_pop += _safe_int(record_age.get(var, 0))
            
            if adult_pop == 0:
                logger.warning(f"Could not calculate adult population for 2020 Census for {display_name}, using total population")
                # Fallback to total population
                adult_pop = None
            
            # Get race/ethnicity data
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
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 503:
                logger.warning(f"2020 Census race API returned 503 (Service Unavailable) for {display_name}")
                raise HTTPError(f"2020 Census race API returned 503")
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 1:
                headers = data[0]
                row = data[1]
                
                name_idx = headers.index('NAME')
                total_pop_idx = headers.index('P1_001N')
                hispanic_idx = headers.index('P2_002N')
                white_idx = headers.index('P2_005N')
                black_idx = headers.index('P2_006N')
                native_am_idx = headers.index('P2_007N')
                asian_idx = headers.index('P2_008N')
                hopi_idx = headers.index('P2_009N')
                multi_racial_idx = headers.index('P2_011N')
                
                total_pop = _safe_int(row[total_pop_idx])
                # IMPORTANT: Race/ethnicity data is for ALL ages, so we must use total_pop as denominator
                # Using adult_pop as denominator would inflate percentages since race counts include children
                # We display adult_pop in the chart title, but percentages are calculated from total population
                pop_denominator = total_pop  # Always use total population for percentage calculations
                
                if pop_denominator and pop_denominator > 0:
                    white = _safe_int(row[white_idx])
                    black = _safe_int(row[black_idx])
                    asian = _safe_int(row[asian_idx])
                    native_am = _safe_int(row[native_am_idx])
                    hopi = _safe_int(row[hopi_idx])
                    multi_racial = _safe_int(row[multi_racial_idx])
                    hispanic = _safe_int(row[hispanic_idx])
                    
                    result['time_periods']['census2020'] = {
                        'year': '2020 Census',
                        'data_year': '2020 (Decennial Census - Adult Population 18+)' if adult_pop else '2020 (Decennial Census)',
                        'demographics': {
                            'total_population': adult_pop if adult_pop and adult_pop > 0 else total_pop,  # Display adult pop if available
                            'white_percentage': round((white / pop_denominator * 100) if white else 0, 1),
                            'black_percentage': round((black / pop_denominator * 100) if black else 0, 1),
                            'asian_percentage': round((asian / pop_denominator * 100) if asian else 0, 1),
                            'native_american_percentage': round((native_am / pop_denominator * 100) if native_am else 0, 1),
                            'hopi_percentage': round((hopi / pop_denominator * 100) if hopi else 0, 1),
                            'multi_racial_percentage': round((multi_racial / pop_denominator * 100) if multi_racial else 0, 1),
                            'hispanic_percentage': round((hispanic / pop_denominator * 100) if hispanic else 0, 1)
                        }
                    }
                    logger.info(f"Successfully fetched 2020 Census data for {display_name}: {'adult_pop=' + str(adult_pop) if adult_pop else 'total_pop=' + str(total_pop)}")
        except Exception as e:
            logger.warning(f"Failed to fetch 2020 Census data for {display_name}: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. Fetch 2010 Decennial Census (SF1) - Adult Population (18+)
        try:
            logger.info(f"Fetching 2010 Decennial Census (adult population 18+) for {display_name}...")
            
            # First, get adult population (18+) from P12 table (Sex by Age)
            # Correct 2010 SF1 P12 variables for age groups 18+ (6-digit codes):
            # Male: P012007 (18-19), P012008 (20), P012011 (25-29), P012012 (30-34),
            #       P012013 (35-39), P012014 (40-44), P012015 (45-49), P012016 (50-54),
            #       P012017 (55-59), P012018 (60-61), P012020 (65-66), P012022 (70-74),
            #       P012023 (75-79), P012024 (80-84), P012025 (85+)
            # Female: P012031 (18-19), P012032 (20), P012035 (25-29), P012036 (30-34),
            #         P012037 (35-39), P012038 (40-44), P012039 (45-49), P012040 (50-54),
            #         P012041 (55-59), P012042 (60-61), P012044 (65-66), P012046 (70-74),
            #         P012047 (75-79), P012048 (80-84), P012049 (85+)
            # Note: 2010 SF1 doesn't have separate variables for 21-24, 62-64, 67-69 age groups
            # We'll use the available variables which cover most of the 18+ population
            
            adult_age_vars_2010 = [
                'P012007', 'P012008', 'P012011', 'P012012', 'P012013', 'P012014',
                'P012015', 'P012016', 'P012017', 'P012018', 'P012020', 'P012022',
                'P012023', 'P012024', 'P012025',  # Male 18+
                'P012031', 'P012032', 'P012035', 'P012036', 'P012037', 'P012038',
                'P012039', 'P012040', 'P012041', 'P012042', 'P012044', 'P012046',
                'P012047', 'P012048', 'P012049'  # Female 18+
            ]
            
            url_age = f"https://api.census.gov/data/2010/dec/sf1"
            params_age = {
                'get': ','.join(adult_age_vars_2010),
                'for': f'county:{county_fips}',
                'in': f'state:{state_fips}',
                'key': api_key
            }
            
            logger.info(f"[2010 Census] Fetching age data from: {url_age}")
            logger.info(f"[2010 Census] Params: for=county:{county_fips}, in=state:{state_fips}")
            
            adult_pop = None  # Default to None (will use total population)
            try:
                response_age = requests.get(url_age, params=params_age, timeout=10)
                logger.info(f"[2010 Census] Age API response status: {response_age.status_code}")
                
                if response_age.status_code == 200:
                    data_age = response_age.json()
                    logger.info(f"[2010 Census] Age API response data length: {len(data_age) if data_age else 0}")
                    
                    if data_age and len(data_age) > 1:
                        headers_age = data_age[0]
                        row_age = data_age[1]
                        record_age = dict(zip(headers_age, row_age))
                        
                        # Sum all adult age groups
                        adult_pop = 0
                        for var in adult_age_vars_2010:
                            adult_pop += _safe_int(record_age.get(var, 0))
                        
                        if adult_pop == 0:
                            logger.warning(f"[2010 Census] Could not calculate adult population for {display_name} (sum was 0), using total population")
                            adult_pop = None
                        else:
                            logger.info(f"[2010 Census] Successfully calculated adult population: {adult_pop}")
                    else:
                        logger.warning(f"[2010 Census] Age API returned empty data, will use total population")
                else:
                    logger.warning(f"[2010 Census] Age API returned status {response_age.status_code}, will use total population")
                    # Try to get error details
                    try:
                        error_data = response_age.json()
                        logger.warning(f"[2010 Census] Age API error response: {error_data}")
                    except:
                        logger.warning(f"[2010 Census] Age API error text: {response_age.text[:200]}")
            except Exception as age_error:
                logger.warning(f"[2010 Census] Failed to fetch age data for {display_name}: {age_error}, will use total population")
                adult_pop = None
            
            # Get race/ethnicity data
            url = f"https://api.census.gov/data/2010/dec/sf1"
            params = {
                'get': 'NAME,P001001,P005001,P005003,P005004,P005005,P005006,P005007,P005009,P004003',
                'for': f'county:{county_fips}',
                'in': f'state:{state_fips}',
                'key': api_key
            }
            # P001001 = Total population
            # P005001 = Total (for race/ethnicity breakdown)
            # P005003 = Not Hispanic or Latino!!White alone
            # P005004 = Not Hispanic or Latino!!Black or African American alone
            # P005005 = Not Hispanic or Latino!!American Indian/Alaska Native alone
            # P005006 = Not Hispanic or Latino!!Asian alone
            # P005007 = Not Hispanic or Latino!!Native Hawaiian/Pacific Islander alone
            # P005009 = Not Hispanic or Latino!!Two or more races
            # P004003 = Hispanic or Latino (of any race)
            
            logger.info(f"[2010 Census] Fetching race/ethnicity data from: {url}")
            logger.info(f"[2010 Census] Race API params: for=county:{county_fips}, in=state:{state_fips}")
            response = requests.get(url, params=params, timeout=10)
            logger.info(f"[2010 Census] Race API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"[2010 Census] Race API returned status {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"[2010 Census] Race API error response: {error_data}")
                except:
                    logger.error(f"[2010 Census] Race API error text: {response.text[:200]}")
                raise requests.exceptions.HTTPError(f"2010 Census race API returned status {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            logger.info(f"[2010 Census] Race API response data length: {len(data) if data else 0}")
            
            if data and len(data) > 1:
                headers = data[0]
                row = data[1]
                
                name_idx = headers.index('NAME')
                total_pop_idx = headers.index('P001001')
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
                    pass
                
                total_pop = _safe_int(row[total_pop_idx])
                # IMPORTANT: Race/ethnicity data is for ALL ages, so we must use total_pop as denominator
                # Using adult_pop as denominator would inflate percentages since race counts include children
                # We display adult_pop in the chart title, but percentages are calculated from total population
                pop_denominator = total_pop  # Always use total population for percentage calculations
                
                if pop_denominator and pop_denominator > 0:
                    white = _safe_int(row[white_idx])
                    black = _safe_int(row[black_idx])
                    asian = _safe_int(row[asian_idx])
                    native_am = _safe_int(row[native_am_idx])
                    hopi = _safe_int(row[hopi_idx])
                    multi_racial = _safe_int(row[multi_racial_idx])
                    
                    # Get Hispanic - prefer from main call, fallback to separate call
                    if hispanic_idx is not None:
                        hispanic = _safe_int(row[hispanic_idx])
                    else:
                        # Get Hispanic separately (fallback)
                        try:
                            url_hispanic = f"https://api.census.gov/data/2010/dec/sf1"
                            params_hispanic = {
                                'get': 'P004003',  # Hispanic or Latino (of any race)
                                'for': f'county:{county_fips}',
                                'in': f'state:{state_fips}',
                                'key': api_key
                            }
                            response_hispanic = requests.get(url_hispanic, params=params_hispanic, timeout=10)
                            response_hispanic.raise_for_status()
                            data_hispanic = response_hispanic.json()
                            hispanic = _safe_int(data_hispanic[1][0]) if data_hispanic and len(data_hispanic) > 1 else 0
                        except Exception as e:
                            logger.warning(f"Failed to fetch Hispanic data separately: {e}")
                            hispanic = 0
                    
                    result['time_periods']['census2010'] = {
                        'year': '2010 Census',
                        'data_year': '2010 (Decennial Census - Adult Population 18+)' if adult_pop else '2010 (Decennial Census)',
                        'demographics': {
                            'total_population': adult_pop if adult_pop and adult_pop > 0 else total_pop,  # Display adult pop if available
                            'white_percentage': round((white / pop_denominator * 100) if white else 0, 1),
                            'black_percentage': round((black / pop_denominator * 100) if black else 0, 1),
                            'asian_percentage': round((asian / pop_denominator * 100) if asian else 0, 1),
                            'native_american_percentage': round((native_am / pop_denominator * 100) if native_am else 0, 1),
                            'hopi_percentage': round((hopi / pop_denominator * 100) if hopi else 0, 1),
                            'multi_racial_percentage': round((multi_racial / pop_denominator * 100) if multi_racial else 0, 1),
                            'hispanic_percentage': round((hispanic / pop_denominator * 100) if hispanic else 0, 1)
                        }
                    }
                    logger.info(f"✓ Successfully fetched 2010 Census data for {display_name}: adult_pop={adult_pop if adult_pop else 'N/A'}, total_pop={total_pop}, pop_denominator={pop_denominator}")
                    logger.info(f"[2010 Census] Demographics: white={white}, black={black}, asian={asian}, hispanic={hispanic}, multi_racial={multi_racial}")
        except Exception as e:
            logger.error(f"✗ Failed to fetch 2010 Census data for {display_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        except Exception as e:
            logger.warning(f"Failed to fetch 2010 Census data for {display_name}: {e}")
            import traceback
            traceback.print_exc()
        
        # Return empty dict if no data was retrieved
        time_periods = result.get('time_periods', {})
        if not time_periods or len(time_periods) == 0:
            logger.error(f"[CRITICAL] No time periods retrieved for {display_name} (state_fips={state_fips}, county_fips={county_fips}) - returning empty dict")
            logger.error(f"[CRITICAL] This will cause census chart to not render! Check Census API key and network connectivity.")
            logger.error(f"[CRITICAL] Result dict keys: {list(result.keys())}, time_periods type: {type(time_periods)}, time_periods value: {time_periods}")
            return {}
        
        logger.info(f"[DEBUG] get_census_data_for_county SUCCESS: Retrieved {len(time_periods)} time periods for {display_name}: {list(time_periods.keys())}")
        logger.info(f"[DEBUG] Sample time_period data structure: {list(time_periods.values())[0].keys() if time_periods else 'NO TIME PERIODS'}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching census data for {display_name}: {e}")
        import traceback
        traceback.print_exc()
        return {}
