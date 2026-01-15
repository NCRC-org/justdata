#!/usr/bin/env python3
"""
BizSight Data Utilities
Helper functions for data loading and validation.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from justdata.apps.bizsight.utils.bigquery_client import BigQueryClient


def get_available_counties(state_code: str = None) -> List[Dict]:
    """Get list of available counties, optionally filtered by state."""
    try:
        print(f"DEBUG: get_available_counties called with state_code: {state_code}")
        bq_client = BigQueryClient()
        query_job = bq_client.get_available_counties(state_code)
        print(f"DEBUG: Query job created, job_id: {query_job.job_id}, fetching results...")
        
        # Wait for the query to complete and get results - convert to list like LendSight does
        try:
            results = list(query_job.result())  # Convert to list like LendSight
            print(f"DEBUG: Got {len(results)} rows from query")
        except Exception as query_error:
            print(f"ERROR: Query execution failed: {query_error}")
            import traceback
            traceback.print_exc()
            return []
        
        # Process results like LendSight does
        counties = []
        seen_geoids = set()  # Track unique GEOIDs to avoid duplicates
        
        for row in results:
            try:
                # Ensure geoid5 is properly formatted as 5-digit string
                geoid5 = str(row.geoid5).zfill(5) if row.geoid5 else None
                
                # Skip if we've already seen this GEOID
                if geoid5 and geoid5 in seen_geoids:
                    continue
                    
                if geoid5:
                    seen_geoids.add(geoid5)
                
                # Extract state and county FIPS from GEOID5 (like LendSight)
                state_fips = geoid5[:2] if geoid5 and len(geoid5) >= 2 else None
                county_fips = geoid5[2:] if geoid5 and len(geoid5) >= 5 else None
                
                # Get county_state directly from row
                county_state = row.county_state if hasattr(row, 'county_state') else None
                
                # Parse county_name and state_name from county_state
                county_name = ''
                state_name = ''
                if county_state and ',' in county_state:
                    parts = county_state.split(',', 1)
                    county_name = parts[0].strip()
                    state_name = parts[1].strip() if len(parts) > 1 else ''
                else:
                    # Fallback to query columns if available
                    county_name = getattr(row, 'county_name', '')
                    state_name = getattr(row, 'state_name', '')
                
                counties.append({
                    'geoid5': geoid5,
                    'name': county_state or f"{county_name}, {state_name}",
                    'county_name': county_name,
                    'state_name': state_name,
                    'state_fips': state_fips,
                    'county_fips': county_fips
                })
            except Exception as row_error:
                print(f"DEBUG: Error processing row: {row_error}")
                print(f"DEBUG: Row data: {dict(row) if hasattr(row, '__dict__') else 'N/A'}")
                continue
        
        print(f"DEBUG: Processed {len(results)} rows, returning {len(counties)} counties")
        if len(counties) > 0:
            print(f"DEBUG: First county: {counties[0]}")
        else:
            print(f"DEBUG: WARNING - No counties found for state_code: {state_code}")
        return counties
    except Exception as e:
        print(f"ERROR loading counties: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_available_states() -> List[Dict]:
    """Get list of all available US states.
    
    Returns all 50 states + DC + territories with their FIPS codes.
    This ensures all states are visible in the dropdown regardless of database content.
    
    Returns:
        List of dictionaries with 'code', 'name', and 'fips'
    """
    # Complete list of all US states, DC, and territories with FIPS codes
    all_states = [
        {'code': '01', 'name': 'Alabama', 'fips': '01'}, {'code': '02', 'name': 'Alaska', 'fips': '02'},
        {'code': '04', 'name': 'Arizona', 'fips': '04'}, {'code': '05', 'name': 'Arkansas', 'fips': '05'},
        {'code': '06', 'name': 'California', 'fips': '06'}, {'code': '08', 'name': 'Colorado', 'fips': '08'},
        {'code': '09', 'name': 'Connecticut', 'fips': '09'}, {'code': '10', 'name': 'Delaware', 'fips': '10'},
        {'code': '11', 'name': 'District of Columbia', 'fips': '11'}, {'code': '12', 'name': 'Florida', 'fips': '12'},
        {'code': '13', 'name': 'Georgia', 'fips': '13'}, {'code': '15', 'name': 'Hawaii', 'fips': '15'},
        {'code': '16', 'name': 'Idaho', 'fips': '16'}, {'code': '17', 'name': 'Illinois', 'fips': '17'},
        {'code': '18', 'name': 'Indiana', 'fips': '18'}, {'code': '19', 'name': 'Iowa', 'fips': '19'},
        {'code': '20', 'name': 'Kansas', 'fips': '20'}, {'code': '21', 'name': 'Kentucky', 'fips': '21'},
        {'code': '22', 'name': 'Louisiana', 'fips': '22'}, {'code': '23', 'name': 'Maine', 'fips': '23'},
        {'code': '24', 'name': 'Maryland', 'fips': '24'}, {'code': '25', 'name': 'Massachusetts', 'fips': '25'},
        {'code': '26', 'name': 'Michigan', 'fips': '26'}, {'code': '27', 'name': 'Minnesota', 'fips': '27'},
        {'code': '28', 'name': 'Mississippi', 'fips': '28'}, {'code': '29', 'name': 'Missouri', 'fips': '29'},
        {'code': '30', 'name': 'Montana', 'fips': '30'}, {'code': '31', 'name': 'Nebraska', 'fips': '31'},
        {'code': '32', 'name': 'Nevada', 'fips': '32'}, {'code': '33', 'name': 'New Hampshire', 'fips': '33'},
        {'code': '34', 'name': 'New Jersey', 'fips': '34'}, {'code': '35', 'name': 'New Mexico', 'fips': '35'},
        {'code': '36', 'name': 'New York', 'fips': '36'}, {'code': '37', 'name': 'North Carolina', 'fips': '37'},
        {'code': '38', 'name': 'North Dakota', 'fips': '38'}, {'code': '39', 'name': 'Ohio', 'fips': '39'},
        {'code': '40', 'name': 'Oklahoma', 'fips': '40'}, {'code': '41', 'name': 'Oregon', 'fips': '41'},
        {'code': '42', 'name': 'Pennsylvania', 'fips': '42'}, {'code': '44', 'name': 'Rhode Island', 'fips': '44'},
        {'code': '45', 'name': 'South Carolina', 'fips': '45'}, {'code': '46', 'name': 'South Dakota', 'fips': '46'},
        {'code': '47', 'name': 'Tennessee', 'fips': '47'}, {'code': '48', 'name': 'Texas', 'fips': '48'},
        {'code': '49', 'name': 'Utah', 'fips': '49'}, {'code': '50', 'name': 'Vermont', 'fips': '50'},
        {'code': '51', 'name': 'Virginia', 'fips': '51'}, {'code': '53', 'name': 'Washington', 'fips': '53'},
        {'code': '54', 'name': 'West Virginia', 'fips': '54'}, {'code': '55', 'name': 'Wisconsin', 'fips': '55'},
        {'code': '56', 'name': 'Wyoming', 'fips': '56'},
        # Territories
        {'code': '60', 'name': 'American Samoa', 'fips': '60'}, {'code': '66', 'name': 'Guam', 'fips': '66'},
        {'code': '69', 'name': 'Northern Mariana Islands', 'fips': '69'}, {'code': '72', 'name': 'Puerto Rico', 'fips': '72'},
        {'code': '78', 'name': 'U.S. Virgin Islands', 'fips': '78'}
    ]
    
    print(f"Returning all {len(all_states)} US states and territories")
    return all_states


def get_available_years() -> List[int]:
    """Get list of available years."""
    try:
        bq_client = BigQueryClient()
        return bq_client.get_available_years()
    except Exception as e:
        print(f"Error loading years: {e}")
        return list(range(2018, 2025))


def get_county_by_geoid5(geoid5: str) -> Optional[Dict]:
    """Get county information by GEOID5."""
    counties = get_available_counties()
    geoid5_padded = str(geoid5).zfill(5)
    
    for county in counties:
        if str(county.get('geoid5', '')).zfill(5) == geoid5_padded:
            return county
    
    return None



def get_last_5_years_sb() -> List[int]:
    """
    Get the last 5 years dynamically from SB disclosure data.

    Returns:
        List of the 5 most recent years available
    """
    try:
        bq_client = BigQueryClient()
        return bq_client.get_last_5_years_sb()
    except Exception as e:
        print(f"Error loading SB years: {e}")
        return list(range(2020, 2025))  # Fallback


def validate_year_range(start_year: int, end_year: int) -> tuple[bool, Optional[str]]:
    """
    Validate year range.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if start_year < 2018 or end_year > 2024:
        return False, "Years must be between 2018 and 2024"
    
    if start_year > end_year:
        return False, "Start year must be before or equal to end year"
    
    year_count = end_year - start_year + 1
    if year_count < 3:
        # Allow 1 year for planning regions (2024 only)
        # Check if this is a planning region request (would need to be passed in, but for now just allow 1 year)
        if year_count == 1:
            return True, ""  # Allow single year (for planning regions)
        return False, "Must select at least 3 years"
    
    return True, None

