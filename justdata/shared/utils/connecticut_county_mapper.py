#!/usr/bin/env python3
"""
Connecticut County/Planning Region Mapping Utility

Connecticut eliminated county governments in 1960, but the Census Bureau and federal
data systems still use county FIPS codes. The state now uses planning regions for
administrative purposes.

CRITICAL UNDERSTANDING - Tract Boundaries Are Stable:
- Census tract boundaries do NOT change by year
- A tract in Fairfield County in 2020 is still in Fairfield County in 2024
- Planning regions are just aggregations of counties - they don't change tract boundaries
- If a tract is in a planning region in 2024, it was also in that planning region in 2020-2023
- The mapping logic: Selection → County FIPS codes → Tracts (same tracts for all years)

This module provides mapping functions that:
1. Allow selection of either planning region OR county
2. Map selections to county FIPS codes (planning regions → multiple counties)
3. Get census tracts for those counties (same tracts for all years)

Example:
- User selects "Fairfield County" → Maps to 09001 → Gets all tracts in 09001 → Same tracts for 2020-2024
- User selects "Greater Bridgeport" (planning region) → Maps to 09001 → Gets all tracts in 09001 → Same tracts for 2020-2024

Connecticut State FIPS: 09
Connecticut has 8 counties with FIPS codes:
- Fairfield County: 09001
- Hartford County: 09003
- Litchfield County: 09005
- Middlesex County: 09007
- New Haven County: 09009
- New London County: 09011
- Tolland County: 09013
- Windham County: 09015

Planning Regions (as of 2024):
1. Capitol (includes Hartford County)
2. Central Naugatuck Valley (includes parts of New Haven, Litchfield)
3. Greater Bridgeport (includes parts of Fairfield)
4. Lower Connecticut River Valley (includes parts of Middlesex, New London)
5. Northeastern Connecticut (includes parts of Tolland, Windham)
6. Northwest Hills (includes parts of Litchfield)
7. South Central (includes parts of New Haven, Middlesex)
8. Western Connecticut (includes parts of Fairfield, Litchfield)
"""

from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime

# Connecticut County FIPS to County Name mapping
CONNECTICUT_COUNTIES = {
    '09001': 'Fairfield County',
    '09003': 'Hartford County',
    '09005': 'Litchfield County',
    '09007': 'Middlesex County',
    '09009': 'New Haven County',
    '09011': 'New London County',
    '09013': 'Tolland County',
    '09015': 'Windham County'
}

# Connecticut County Name to FIPS mapping (case-insensitive)
CONNECTICUT_COUNTY_NAME_TO_FIPS = {
    'fairfield county': '09001',
    'fairfield': '09001',
    'hartford county': '09003',
    'hartford': '09003',
    'litchfield county': '09005',
    'litchfield': '09005',
    'middlesex county': '09007',
    'middlesex': '09007',
    'new haven county': '09009',
    'new haven': '09009',
    'new london county': '09011',
    'new london': '09011',
    'tolland county': '09013',
    'tolland': '09013',
    'windham county': '09015',
    'windham': '09015'
}

# Planning Region to County FIPS mapping
# Note: Planning regions can span multiple counties, so we map to all relevant county FIPS
PLANNING_REGION_TO_COUNTIES = {
    'Capitol': ['09003'],  # Hartford County
    'Central Naugatuck Valley': ['09009', '09005'],  # New Haven, Litchfield
    'Greater Bridgeport': ['09001'],  # Fairfield County
    'Lower Connecticut River Valley': ['09007', '09011'],  # Middlesex, New London
    'Northeastern Connecticut': ['09013', '09015'],  # Tolland, Windham
    'Northwest Hills': ['09005'],  # Litchfield County
    'South Central': ['09009', '09007'],  # New Haven, Middlesex
    'Western Connecticut': ['09001', '09005']  # Fairfield, Litchfield
}

# Note: Census tract boundaries are stable and do NOT change by year.
# A tract in a county in 2020 is still in that same county in 2024.
# Planning regions are just aggregations of counties - they don't change tract boundaries.
# The year parameter is used for data queries, but tract-to-county mapping is the same for all years.


def is_connecticut_geoid(geoid5: str) -> bool:
    """Check if a GEOID5 is a Connecticut county (state FIPS 09)."""
    geoid5_str = str(geoid5).zfill(5)
    return geoid5_str.startswith('09')


def get_connecticut_county_fips(county_name: str) -> Optional[str]:
    """
    Get Connecticut county FIPS code from county name.
    
    Args:
        county_name: County name (e.g., "Fairfield County", "Fairfield", "Fairfield County, Connecticut")
    
    Returns:
        5-digit FIPS code (e.g., "09001") or None if not found
    """
    # Clean county name
    county_clean = str(county_name).strip()
    
    # Remove "County" suffix if present
    if county_clean.lower().endswith(' county'):
        county_clean = county_clean[:-7].strip()
    
    # Remove state name if present (e.g., "Fairfield County, Connecticut")
    if ',' in county_clean:
        county_clean = county_clean.split(',')[0].strip()
    
    # Look up in mapping
    county_lower = county_clean.lower()
    return CONNECTICUT_COUNTY_NAME_TO_FIPS.get(county_lower)


def get_connecticut_county_name(geoid5: str) -> Optional[str]:
    """
    Get Connecticut county name from GEOID5.
    
    Args:
        geoid5: 5-digit FIPS code (e.g., "09001" or "9001")
    
    Returns:
        County name (e.g., "Fairfield County") or None if not found
    """
    geoid5_str = str(geoid5).zfill(5)
    if not is_connecticut_geoid(geoid5_str):
        return None
    return CONNECTICUT_COUNTIES.get(geoid5_str)


def is_planning_region(identifier: str) -> bool:
    """
    Check if an identifier is a Connecticut planning region.
    
    Args:
        identifier: Planning region name or county name
    
    Returns:
        True if it's a planning region, False otherwise
    """
    identifier_clean = str(identifier).strip()
    return identifier_clean in PLANNING_REGION_TO_COUNTIES


def get_county_fips_for_selection(selection: str, selection_type: str = 'auto') -> List[str]:
    """
    Get county FIPS codes for a user selection (county or planning region).
    
    Args:
        selection: County name or planning region name
        selection_type: 'county', 'planning_region', or 'auto' (detect automatically)
    
    Returns:
        List of 5-digit FIPS codes for counties in the selection
    """
    if selection_type == 'auto':
        # Auto-detect: check if it's a planning region first
        if is_planning_region(selection):
            selection_type = 'planning_region'
        else:
            selection_type = 'county'
    
    if selection_type == 'planning_region':
        # Map planning region to counties
        return PLANNING_REGION_TO_COUNTIES.get(selection, [])
    else:
        # Map county name to FIPS
        geoid5 = get_connecticut_county_fips(selection)
        return [geoid5] if geoid5 else []


def get_tracts_for_connecticut_selection(
    selection: str,
    selection_type: str = 'auto',
    years: List[int] = None,
    bq_client=None
) -> Dict[int, List[str]]:
    """
    Get census tract GEOID11 codes for a Connecticut selection, organized by year.
    
    This function handles the year-based mapping:
    - For years < 2024: Maps to county FIPS codes (traditional mapping)
    - For years >= 2024: Maps to planning regions if selected, otherwise counties
    
    Args:
        selection: County name or planning region name
        selection_type: 'county', 'planning_region', or 'auto' (detect automatically)
        years: List of years to query (if None, queries all available years)
        bq_client: Optional BigQuery client (if None, will create one)
    
    Returns:
        Dictionary mapping year to list of 11-digit tract GEOIDs
        Example: {2021: ["09001000100", ...], 2024: ["09001000100", ...]}
    """
    if not years:
        # Default to recent years if not specified
        current_year = datetime.now().year
        years = list(range(2020, current_year + 1))
    
    # Get county FIPS codes for this selection
    county_fips_list = get_county_fips_for_selection(selection, selection_type)
    
    if not county_fips_list:
        return {}
    
    try:
        if bq_client is None:
            from justdata.shared.utils.bigquery_client import get_bigquery_client
            from apps.branchseeker.config import PROJECT_ID
            bq_client = get_bigquery_client(PROJECT_ID)
        
        # Build query to get all tracts for these counties
        # For each year, we'll use the county FIPS codes
        # GEOID11 format: SSCCCTTTTTT (2 state + 3 county + 6 tract)
        county_fips_str = "', '".join([str(fips).zfill(5) for fips in county_fips_list])
        
        query = f"""
        SELECT DISTINCT
            LPAD(CAST(geoid AS STRING), 11, '0') as geoid11,
            SUBSTR(LPAD(CAST(geoid AS STRING), 11, '0'), 1, 5) as geoid5
        FROM `hdma1-242116.geo.census`
        WHERE SUBSTR(LPAD(CAST(geoid AS STRING), 11, '0'), 1, 5) IN ('{county_fips_str}')
        ORDER BY geoid11
        """
        
        results = bq_client.query(query).result()
        
        # Get all tracts for these counties
        # Tract boundaries are STABLE - they don't change by year
        # A tract in Fairfield County in 2020 is still in Fairfield County in 2024
        # Planning regions are just aggregations of counties - they don't change tract boundaries
        all_tracts = [str(row.geoid11).zfill(11) for row in results]
        
        # Return the SAME tracts for ALL years
        # Example: If user selects "Fairfield County" or "Greater Bridgeport" (planning region),
        # we get all tracts in Fairfield County (09001) and use them for all years (2020-2024)
        return {year: all_tracts for year in years}
        
    except Exception as e:
        print(f"Error getting Connecticut tracts for {selection}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def normalize_connecticut_selection(selection: str) -> Tuple[str, str, List[str]]:
    """
    Normalize a Connecticut selection (county or planning region) to standard format.
    
    Args:
        selection: County name or planning region name
    
    Returns:
        Tuple of (normalized_name, selection_type, county_fips_list)
        Example: ("Fairfield County", "county", ["09001"])
        Example: ("Greater Bridgeport", "planning_region", ["09001"])
    """
    # Check if it's a planning region
    if is_planning_region(selection):
        county_fips_list = PLANNING_REGION_TO_COUNTIES.get(selection, [])
        return (selection, 'planning_region', county_fips_list)
    
    # Otherwise, treat as county
    geoid5 = get_connecticut_county_fips(selection)
    if geoid5:
        county_name = get_connecticut_county_name(geoid5)
        return (county_name, 'county', [geoid5])
    
    # Not found
    return (selection, 'unknown', [])


def get_connecticut_counties_for_planning_region(planning_region: str) -> List[str]:
    """
    Get list of county names for a planning region.
    
    Args:
        planning_region: Planning region name
    
    Returns:
        List of county names (e.g., ["Fairfield County"])
    """
    county_fips_list = PLANNING_REGION_TO_COUNTIES.get(planning_region, [])
    return [get_connecticut_county_name(fips) for fips in county_fips_list if get_connecticut_county_name(fips)]


def get_all_connecticut_planning_regions() -> List[str]:
    """Get list of all Connecticut planning region names."""
    return list(PLANNING_REGION_TO_COUNTIES.keys())


def get_all_connecticut_counties() -> List[str]:
    """Get list of all Connecticut county names."""
    return list(CONNECTICUT_COUNTIES.values())


def validate_connecticut_mapping(selection: str, geoid5: str) -> bool:
    """
    Validate that a selection (county or planning region) includes a specific GEOID5.
    
    Args:
        selection: County name or planning region name
        geoid5: 5-digit FIPS code to validate
    
    Returns:
        True if the selection includes this GEOID5, False otherwise
    """
    county_fips_list = get_county_fips_for_selection(selection)
    geoid5_str = str(geoid5).zfill(5)
    return geoid5_str in county_fips_list
