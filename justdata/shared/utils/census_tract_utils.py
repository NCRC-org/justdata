"""
Shared Census Tract Utilities
Provides census tract data, income levels, minority demographics, and geographic boundaries.
Used by BranchSight, BranchMapper, LendSight, BizSight and other apps.
"""

import os
import logging
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_ID = "justdata-ncrc"
DEFAULT_ACS_YEAR = "2022"


def get_census_api_key() -> Optional[str]:
    """Get Census API key from environment variable."""
    return os.getenv('CENSUS_API_KEY')


def get_bigquery_client(project_id: str = DEFAULT_PROJECT_ID):
    """Get BigQuery client."""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client as _get_client
        return _get_client(project_id)
    except ImportError:
        logger.error("Could not import BigQuery client")
        return None


# =============================================================================
# FIPS Code Utilities
# =============================================================================

def extract_fips_from_county_state(county_state: str, project_id: str = DEFAULT_PROJECT_ID) -> Optional[Dict[str, str]]:
    """
    Extract state and county FIPS codes from "County, State" format.

    Uses BigQuery to look up the geoid5 (5-digit FIPS) from the shared.cbsa_to_county table.

    Args:
        county_state: County name in format "County, State" (e.g., "Hillsborough County, Florida")
        project_id: BigQuery project ID

    Returns:
        Dictionary with 'state_fips', 'county_fips', and 'geoid5', or None if not found
    """
    try:
        client = get_bigquery_client(project_id)
        if not client:
            return None

        # Try exact match first
        query = f"""
        SELECT DISTINCT geoid5
        FROM `{project_id}.shared.cbsa_to_county`
        WHERE county_state = '{county_state}'
        LIMIT 1
        """

        query_job = client.query(query)
        results = list(query_job.result())

        if results and results[0].geoid5:
            geoid5 = str(results[0].geoid5).zfill(5)
            return {
                'state_fips': geoid5[:2],
                'county_fips': geoid5[2:],
                'geoid5': geoid5
            }

        # Try case-insensitive match
        query_case_insensitive = f"""
        SELECT DISTINCT geoid5, county_state
        FROM `{project_id}.shared.cbsa_to_county`
        WHERE UPPER(county_state) = UPPER('{county_state}')
        LIMIT 1
        """

        query_job = client.query(query_case_insensitive)
        results = list(query_job.result())

        if results and results[0].geoid5:
            geoid5 = str(results[0].geoid5).zfill(5)
            return {
                'state_fips': geoid5[:2],
                'county_fips': geoid5[2:],
                'geoid5': geoid5
            }

        logger.warning(f"Could not find GEOID5 for {county_state}")
        return None

    except Exception as e:
        logger.error(f"Error extracting FIPS codes for {county_state}: {e}")
        return None


# =============================================================================
# CBSA / Metro Area Utilities
# =============================================================================

def get_cbsa_for_county(county_state: str, project_id: str = DEFAULT_PROJECT_ID) -> Optional[Dict[str, Any]]:
    """
    Get the CBSA (metro area) code and name for a county.

    Args:
        county_state: County name in format "County, State" (e.g., "Hillsborough County, Florida")
        project_id: BigQuery project ID

    Returns:
        Dictionary with 'cbsa_code' and 'cbsa_name', or None if not found
    """
    try:
        fips_data = extract_fips_from_county_state(county_state, project_id)
        if not fips_data:
            return None

        geoid5 = fips_data['geoid5']
        client = get_bigquery_client(project_id)
        if not client:
            return None

        query = f"""
        SELECT DISTINCT
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name
        FROM `{project_id}.shared.cbsa_to_county`
        WHERE CAST(geoid5 AS STRING) = '{geoid5}'
            AND cbsa_code IS NOT NULL
        LIMIT 1
        """

        query_job = client.query(query)
        results = list(query_job.result())

        if results and results[0].cbsa_code:
            return {
                'cbsa_code': str(results[0].cbsa_code),
                'cbsa_name': str(results[0].cbsa_name) if results[0].cbsa_name else None
            }

        return None

    except Exception as e:
        logger.error(f"Error getting CBSA for county {county_state}: {e}")
        return None


# =============================================================================
# Census API - Median Income
# =============================================================================

def get_cbsa_median_family_income(cbsa_code: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get median family income for a CBSA (metro area) from Census API.

    Args:
        cbsa_code: CBSA code (metro area code)
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)

    Returns:
        Median family income in dollars, or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()

    if not api_key:
        logger.warning("No Census API key found")
        return None

    try:
        url = f"https://api.census.gov/data/{DEFAULT_ACS_YEAR}/acs/acs5"
        params = {
            'get': 'NAME,B19113_001E',
            'for': f'metropolitan statistical area/micropolitan statistical area:{cbsa_code}',
            'key': api_key
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if len(data) > 1 and len(data[1]) > 1:
            income_str = data[1][1]
            if income_str and income_str != '-888888888':
                return float(income_str)

        return None

    except Exception as e:
        logger.error(f"Error fetching CBSA median family income: {e}")
        return None


def get_county_median_family_income(state_fips: str, county_fips: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get median family income for a county from Census API.

    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code
        api_key: Census API key

    Returns:
        Median family income in dollars, or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()

    if not api_key:
        logger.warning("No Census API key found")
        return None

    try:
        url = f"https://api.census.gov/data/{DEFAULT_ACS_YEAR}/acs/acs5"
        params = {
            'get': 'NAME,B19113_001E',
            'for': f'county:{county_fips}',
            'in': f'state:{state_fips}',
            'key': api_key
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if len(data) > 1 and len(data[1]) > 1:
            income_str = data[1][1]
            if income_str and income_str != '-888888888':
                return float(income_str)

        return None

    except Exception as e:
        logger.error(f"Error fetching county median family income: {e}")
        return None


def get_state_median_family_income(state_fips: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get median family income for a state from Census API (fallback when CBSA not available).

    Args:
        state_fips: 2-digit state FIPS code
        api_key: Census API key

    Returns:
        Median family income in dollars, or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()

    if not api_key:
        logger.warning("No Census API key found")
        return None

    try:
        url = f"https://api.census.gov/data/{DEFAULT_ACS_YEAR}/acs/acs5"
        params = {
            'get': 'NAME,B19113_001E',
            'for': f'state:{state_fips}',
            'key': api_key
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if len(data) > 1 and len(data[1]) > 1:
            income_str = data[1][1]
            if income_str and income_str != '-888888888':
                return float(income_str)

        return None

    except Exception as e:
        logger.error(f"Error fetching state median family income: {e}")
        return None


# =============================================================================
# Census API - Minority Population
# =============================================================================

def get_cbsa_minority_percentage(cbsa_code: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get minority population percentage for a CBSA (metro area) from Census API.

    Minority = Total population - Non-Hispanic White alone

    Args:
        cbsa_code: CBSA code (metro area code)
        api_key: Census API key

    Returns:
        Minority population percentage (0-100), or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()

    if not api_key:
        logger.warning("No Census API key found")
        return None

    try:
        url = f"https://api.census.gov/data/{DEFAULT_ACS_YEAR}/acs/acs5"
        params = {
            'get': 'NAME,B01003_001E,B03002_003E',
            'for': f'metropolitan statistical area/micropolitan statistical area:{cbsa_code}',
            'key': api_key
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if len(data) > 1 and len(data[1]) > 2:
            total_pop = data[1][1]
            white_non_hisp = data[1][2]

            if total_pop and white_non_hisp and total_pop != '-888888888' and white_non_hisp != '-888888888':
                total = float(total_pop)
                white = float(white_non_hisp)
                if total > 0:
                    minority = total - white
                    return (minority / total) * 100

        return None

    except Exception as e:
        logger.error(f"Error fetching CBSA minority percentage: {e}")
        return None


def get_county_minority_percentage(state_fips: str, county_fips: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Get minority population percentage for a county from Census API.

    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code
        api_key: Census API key

    Returns:
        Minority population percentage (0-100), or None if unavailable
    """
    if api_key is None:
        api_key = get_census_api_key()

    if not api_key:
        logger.warning("No Census API key found")
        return None

    try:
        url = f"https://api.census.gov/data/{DEFAULT_ACS_YEAR}/acs/acs5"
        params = {
            'get': 'NAME,B01003_001E,B03002_003E',
            'for': f'county:{county_fips}',
            'in': f'state:{state_fips}',
            'key': api_key
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if len(data) > 1 and len(data[1]) > 2:
            total_pop = data[1][1]
            white_non_hisp = data[1][2]

            if total_pop and white_non_hisp and total_pop != '-888888888' and white_non_hisp != '-888888888':
                total = float(total_pop)
                white = float(white_non_hisp)
                if total > 0:
                    minority = total - white
                    return (minority / total) * 100

        return None

    except Exception as e:
        logger.error(f"Error fetching county minority percentage: {e}")
        return None


# =============================================================================
# Census Tract Data
# =============================================================================

def get_tract_income_data(state_fips: str, county_fips: str, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get median family income for all census tracts in a county from Census API.

    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code
        api_key: Census API key

    Returns:
        List of dictionaries with tract_geoid, tract_name, median_family_income
    """
    if api_key is None:
        api_key = get_census_api_key()

    if not api_key:
        logger.warning("No Census API key found")
        return []

    try:
        url = f"https://api.census.gov/data/{DEFAULT_ACS_YEAR}/acs/acs5"
        params = {
            'get': 'NAME,B19113_001E,GEO_ID',
            'for': 'tract:*',
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
        income_idx = headers.index('B19113_001E')
        tract_idx = headers.index('tract')

        invalid_values = ['-888888888', '-666666666', '-999999999', 'null', 'None', '']
        tracts = []

        for row in data[1:]:
            tract_name = row[name_idx]
            income_str = row[income_idx]
            tract_code = row[tract_idx]
            tract_geoid = f"{state_fips}{county_fips}{tract_code.zfill(6)}"

            median_income = None
            if income_str and income_str not in invalid_values:
                try:
                    income_value = float(income_str)
                    if income_value > 0:
                        median_income = income_value
                except ValueError:
                    pass

            if median_income is not None:
                tracts.append({
                    'tract_geoid': tract_geoid,
                    'tract_name': tract_name,
                    'tract_code': tract_code,
                    'median_family_income': median_income
                })

        return tracts

    except Exception as e:
        logger.error(f"Error fetching tract income data: {e}")
        return []


def get_tract_minority_data(state_fips: str, county_fips: str, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get minority population data for all census tracts in a county from Census API.

    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code
        api_key: Census API key

    Returns:
        List of dictionaries with tract_geoid, tract_name, total_population,
        minority_population, minority_percentage
    """
    if api_key is None:
        api_key = get_census_api_key()

    if not api_key:
        logger.warning("No Census API key found")
        return []

    try:
        url = f"https://api.census.gov/data/{DEFAULT_ACS_YEAR}/acs/acs5"
        params = {
            'get': 'NAME,B01003_001E,B03002_003E,GEO_ID',
            'for': 'tract:*',
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
        tract_idx = headers.index('tract')

        invalid_values = ['-888888888', '-666666666', '-999999999', 'null', 'None', '']
        tracts = []

        for row in data[1:]:
            tract_name = row[name_idx]
            total_pop_str = row[total_pop_idx]
            white_non_hisp_str = row[white_non_hisp_idx]
            tract_code = row[tract_idx]
            tract_geoid = f"{state_fips}{county_fips}{tract_code.zfill(6)}"

            total_pop = None
            white_non_hisp = None

            if total_pop_str and total_pop_str not in invalid_values:
                try:
                    pop_value = float(total_pop_str)
                    if pop_value > 0:
                        total_pop = pop_value
                except ValueError:
                    pass

            if white_non_hisp_str and white_non_hisp_str not in invalid_values:
                try:
                    white_value = float(white_non_hisp_str)
                    if white_value >= 0:
                        white_non_hisp = white_value
                except ValueError:
                    pass

            if total_pop and total_pop > 0 and white_non_hisp is not None:
                minority_pop = total_pop - white_non_hisp
                if minority_pop >= 0:
                    minority_percentage = (minority_pop / total_pop) * 100
                    tracts.append({
                        'tract_geoid': tract_geoid,
                        'tract_name': tract_name,
                        'tract_code': tract_code,
                        'total_population': total_pop,
                        'minority_population': minority_pop,
                        'minority_percentage': minority_percentage
                    })

        return tracts

    except Exception as e:
        logger.error(f"Error fetching tract minority data: {e}")
        return []


# =============================================================================
# Income Level Categorization
# =============================================================================

def categorize_income_level(tract_income: Optional[float], reference_income: Optional[float]) -> str:
    """
    Categorize a census tract's income level based on reference median (CBSA or county).

    Categories (CRA standard):
    - Low: <= 50% of reference median
    - Moderate: <= 80% of reference median
    - Middle: <= 120% of reference median
    - Upper: > 120% of reference median

    Args:
        tract_income: Tract median family income
        reference_income: Reference median family income (CBSA or county)

    Returns:
        Income category string, or 'Unknown' if data unavailable
    """
    if tract_income is None or reference_income is None or reference_income <= 0:
        return 'Unknown'

    ratio = tract_income / reference_income

    if ratio <= 0.50:
        return 'Low'
    elif ratio <= 0.80:
        return 'Moderate'
    elif ratio <= 1.20:
        return 'Middle'
    else:
        return 'Upper'


def get_income_ratio(tract_income: Optional[float], reference_income: Optional[float]) -> Optional[float]:
    """
    Calculate income ratio (tract income / reference income).

    Args:
        tract_income: Tract median family income
        reference_income: Reference median family income

    Returns:
        Ratio as decimal (e.g., 0.75 = 75%), or None if data unavailable
    """
    if tract_income is None or reference_income is None or reference_income <= 0:
        return None
    return tract_income / reference_income


# =============================================================================
# Minority Level Categorization
# =============================================================================

def categorize_minority_level(tract_minority_pct: Optional[float], reference_minority_pct: Optional[float]) -> tuple:
    """
    Categorize a census tract's minority level based on reference baseline.

    Categories based on ratio to reference:
    - Very High: >= 2.0x reference average
    - High: 1.5-2.0x reference average
    - Above Average: 1.2-1.5x reference average
    - Average: 0.8-1.2x reference average
    - Below Average: < 0.8x reference average

    Args:
        tract_minority_pct: Tract minority percentage (0-100)
        reference_minority_pct: Reference minority percentage (0-100)

    Returns:
        Tuple of (category string, ratio float), or ('Unknown', None) if data unavailable
    """
    if tract_minority_pct is None or reference_minority_pct is None or reference_minority_pct <= 0:
        return ('Unknown', None)

    ratio = tract_minority_pct / reference_minority_pct

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


def is_majority_minority_tract(tract_minority_pct: Optional[float]) -> bool:
    """
    Determine if a tract is majority-minority (>50% minority population).

    Args:
        tract_minority_pct: Tract minority percentage (0-100)

    Returns:
        True if majority-minority, False otherwise
    """
    if tract_minority_pct is None:
        return False
    return tract_minority_pct > 50.0


# =============================================================================
# Geographic Boundaries
# =============================================================================

def get_tract_boundaries_geojson(state_fips: str, county_fips: str) -> Optional[Dict]:
    """
    Fetch census tract boundaries as GeoJSON from Census TIGER/Line files.

    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code

    Returns:
        GeoJSON dictionary with tract boundaries, or None if unavailable
    """
    try:
        url = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/8/query"
        params = {
            'where': f"STATE='{state_fips}' AND COUNTY='{county_fips}'",
            'outFields': 'GEOID,NAME,STATE,COUNTY,TRACT',
            'f': 'geojson',
            'outSR': '4326'
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        geojson = response.json()

        if 'features' in geojson and len(geojson['features']) > 0:
            logger.info(f"Fetched {len(geojson['features'])} tract boundaries")
            return geojson

        return None

    except Exception as e:
        logger.error(f"Error fetching tract boundaries: {e}")
        return None


# =============================================================================
# SQL Generation Helpers (for BigQuery)
# =============================================================================

def get_income_tract_flags_sql() -> str:
    """
    Get SQL CASE statements for income tract categorization.

    Returns:
        SQL string for income tract flags
    """
    return """
    CASE
        WHEN tract_to_msa_income_pct <= 50 THEN 'Low'
        WHEN tract_to_msa_income_pct <= 80 THEN 'Moderate'
        WHEN tract_to_msa_income_pct <= 120 THEN 'Middle'
        WHEN tract_to_msa_income_pct > 120 THEN 'Upper'
        ELSE 'Unknown'
    END AS income_level
    """


def get_lmi_flag_sql() -> str:
    """
    Get SQL for LMI (Low-Moderate Income) tract flag.

    Returns:
        SQL string for LMI flag
    """
    return """
    CASE
        WHEN tract_to_msa_income_pct <= 80 THEN 1
        ELSE 0
    END AS lmi_flag
    """


def get_mmct_flag_sql() -> str:
    """
    Get SQL for MMCT (Majority-Minority Census Tract) flag.

    Returns:
        SQL string for MMCT flag
    """
    return """
    CASE
        WHEN tract_minority_pct > 50 THEN 1
        ELSE 0
    END AS mmct_flag
    """
