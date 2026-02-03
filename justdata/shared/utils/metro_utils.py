"""
Shared utilities for mapping counties to metro/CBSA areas.
Used by MemberView, BranchSight, LendSight, and other apps needing geographic data.
"""
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def get_bigquery_client(project_id: str = "justdata-ncrc"):
    """Get BigQuery client."""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client as _get_client
        return _get_client(project_id)
    except ImportError:
        logger.error("Could not import BigQuery client")
        return None


def get_cbsa_for_county(county_name: str, state_name: str, project_id: str = "justdata-ncrc") -> Optional[Dict[str, str]]:
    """
    Get CBSA code and name for a county.

    Args:
        county_name: County name (e.g., "Hillsborough")
        state_name: State name (e.g., "Florida")
        project_id: BigQuery project ID

    Returns:
        Dictionary with 'cbsa_code' and 'cbsa_name', or None if not found
    """
    try:
        client = get_bigquery_client(project_id)
        if not client:
            return None

        # Query using county and state name
        query = f"""
        SELECT DISTINCT
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name
        FROM `{project_id}.shared.cbsa_to_county`
        WHERE LOWER(TRIM(County)) = LOWER(TRIM('{county_name.replace("'", "''")}'))
            AND LOWER(TRIM(State)) = LOWER(TRIM('{state_name.replace("'", "''")}'))
            AND cbsa_code IS NOT NULL
        LIMIT 1
        """

        query_job = client.query(query)
        results = list(query_job.result())

        if results:
            row = results[0]
            cbsa_code = str(row.cbsa_code).strip()
            cbsa_name = str(row.cbsa_name).strip() if row.cbsa_name else None

            # Handle non-metro (CBSA 99999)
            if cbsa_code == '99999':
                cbsa_name = f"{state_name} non-metro"

            return {
                'cbsa_code': cbsa_code,
                'cbsa_name': cbsa_name
            }

        return None
    except Exception as e:
        logger.warning(f"Error getting CBSA for {county_name}, {state_name}: {e}")
        return None


def get_cbsa_for_geoid5(geoid5: str, project_id: str = "justdata-ncrc") -> Optional[Dict[str, str]]:
    """
    Get CBSA code and name for a county using GEOID5 (state+county FIPS).

    Args:
        geoid5: 5-digit GEOID (2-digit state FIPS + 3-digit county FIPS)
        project_id: BigQuery project ID

    Returns:
        Dictionary with 'cbsa_code' and 'cbsa_name', or None if not found
    """
    try:
        client = get_bigquery_client(project_id)
        if not client:
            return None

        query = f"""
        SELECT DISTINCT
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name,
            State as state_name
        FROM `{project_id}.shared.cbsa_to_county`
        WHERE CAST(geoid5 AS STRING) = '{geoid5}'
            AND cbsa_code IS NOT NULL
        LIMIT 1
        """

        query_job = client.query(query)
        results = list(query_job.result())

        if results:
            row = results[0]
            cbsa_code = str(row.cbsa_code).strip()
            cbsa_name = str(row.cbsa_name).strip() if row.cbsa_name else None
            state_name = str(row.state_name).strip() if row.state_name else None

            # Handle non-metro (CBSA 99999)
            if cbsa_code == '99999' and state_name:
                cbsa_name = f"{state_name} non-metro"

            return {
                'cbsa_code': cbsa_code,
                'cbsa_name': cbsa_name
            }

        return None
    except Exception as e:
        logger.warning(f"Error getting CBSA for GEOID5 {geoid5}: {e}")
        return None


def get_metros_by_state(state_name: str, project_id: str = "justdata-ncrc") -> List[Dict[str, str]]:
    """
    Get all metro areas (CBSAs) for a state.

    Args:
        state_name: State name (e.g., "Florida")
        project_id: BigQuery project ID

    Returns:
        List of dictionaries with 'cbsa_code' and 'cbsa_name'
    """
    try:
        client = get_bigquery_client(project_id)
        if not client:
            return []

        query = f"""
        SELECT DISTINCT
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name
        FROM `{project_id}.shared.cbsa_to_county`
        WHERE LOWER(TRIM(State)) = LOWER(TRIM('{state_name.replace("'", "''")}'))
            AND cbsa_code IS NOT NULL
        ORDER BY
            CASE WHEN CAST(cbsa_code AS STRING) = '99999' THEN 1 ELSE 0 END,
            CBSA
        """

        query_job = client.query(query)
        results = list(query_job.result())

        metros = []
        for row in results:
            cbsa_code = str(row.cbsa_code).strip()
            cbsa_name = str(row.cbsa_name).strip() if row.cbsa_name else None

            # Handle non-metro (CBSA 99999)
            if cbsa_code == '99999':
                cbsa_name = f"{state_name} non-metro"

            metros.append({
                'cbsa_code': cbsa_code,
                'cbsa_name': cbsa_name
            })

        return metros
    except Exception as e:
        logger.warning(f"Error getting metros for {state_name}: {e}")
        return []


def get_counties_by_metro(cbsa_code: str, project_id: str = "justdata-ncrc") -> List[str]:
    """
    Get all counties in a metro area.

    Args:
        cbsa_code: CBSA code (e.g., '47900' or '99999')
        project_id: BigQuery project ID

    Returns:
        List of county names in "County, State" format
    """
    try:
        client = get_bigquery_client(project_id)
        if not client:
            return []

        query = f"""
        SELECT DISTINCT county_state
        FROM `{project_id}.shared.cbsa_to_county`
        WHERE CAST(cbsa_code AS STRING) = '{cbsa_code}'
        ORDER BY county_state
        """

        query_job = client.query(query)
        results = list(query_job.result())

        counties = [row.county_state for row in results if row.county_state]
        return counties
    except Exception as e:
        logger.warning(f"Error getting counties for metro {cbsa_code}: {e}")
        return []


def get_all_states(project_id: str = "justdata-ncrc") -> List[str]:
    """
    Get list of all US states from the geo data.

    Args:
        project_id: BigQuery project ID

    Returns:
        List of state names, sorted alphabetically
    """
    try:
        client = get_bigquery_client(project_id)
        if not client:
            return []

        query = f"""
        SELECT DISTINCT State as state_name
        FROM `{project_id}.shared.cbsa_to_county`
        WHERE State IS NOT NULL
        ORDER BY State
        """

        query_job = client.query(query)
        results = list(query_job.result())

        states = [row.state_name for row in results if row.state_name]
        return states
    except Exception as e:
        logger.warning(f"Error getting states: {e}")
        return []


def get_counties_by_state(state_name: str, project_id: str = "justdata-ncrc") -> List[Dict[str, str]]:
    """
    Get all counties for a state with their FIPS codes.

    Args:
        state_name: State name (e.g., "Florida")
        project_id: BigQuery project ID

    Returns:
        List of dictionaries with 'county_name', 'county_state', 'geoid5', 'state_fips', 'county_fips'
    """
    try:
        client = get_bigquery_client(project_id)
        if not client:
            return []

        query = f"""
        SELECT DISTINCT
            County as county_name,
            county_state,
            CAST(geoid5 AS STRING) as geoid5
        FROM `{project_id}.shared.cbsa_to_county`
        WHERE LOWER(TRIM(State)) = LOWER(TRIM('{state_name.replace("'", "''")}'))
        ORDER BY County
        """

        query_job = client.query(query)
        results = list(query_job.result())

        counties = []
        for row in results:
            geoid5 = str(row.geoid5).zfill(5) if row.geoid5 else None
            counties.append({
                'county_name': row.county_name,
                'county_state': row.county_state,
                'geoid5': geoid5,
                'state_fips': geoid5[:2] if geoid5 else None,
                'county_fips': geoid5[2:] if geoid5 else None
            })

        return counties
    except Exception as e:
        logger.warning(f"Error getting counties for {state_name}: {e}")
        return []
