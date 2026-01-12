#!/usr/bin/env python3
"""
Connecticut Census Data Normalization

Normalizes Connecticut planning region codes (09110-09190) to legacy county codes (09001-09015)
for fetching 2010 and 2020 census data, then aggregates the results back to planning region level.
"""

import logging
from typing import Dict, List, Any, Optional
from justdata.shared.utils.connecticut_county_mapper import PLANNING_REGION_TO_COUNTIES

logger = logging.getLogger(__name__)

# Mapping from planning region codes to county codes
PLANNING_REGION_CODE_TO_COUNTIES = {
    '09110': ['09003'],  # Capitol → Hartford County
    '09120': ['09001'],  # Greater Bridgeport → Fairfield County
    '09130': ['09007', '09011'],  # Lower Connecticut River Valley → Middlesex, New London
    '09140': ['09009', '09005'],  # Naugatuck Valley → New Haven, Litchfield
    '09150': ['09013', '09015'],  # Northeastern Connecticut → Tolland, Windham
    '09160': ['09005'],  # Northwest Hills → Litchfield County
    '09170': ['09009', '09007'],  # South Central → New Haven, Middlesex
    '09180': ['09011'],  # Southeastern Connecticut → New London County (assumed)
    '09190': ['09001', '09005'],  # Western Connecticut → Fairfield, Litchfield
}


def normalize_connecticut_geoids_for_census(geoids: List[str]) -> Dict[str, List[str]]:
    """
    Normalize Connecticut planning region codes to legacy county codes for census API calls.
    
    Args:
        geoids: List of 5-digit GEOID codes (may include planning regions 09110-09190)
    
    Returns:
        Dictionary mapping original geoid to list of county geoids to fetch:
        {
            '09120': ['09001'],  # Planning region → counties
            '09001': ['09001'],  # Already a county → unchanged
            '24031': ['24031']   # Non-CT → unchanged
        }
    """
    result = {}
    
    for geoid in geoids:
        geoid_str = str(geoid).zfill(5)
        
        # Check if it's a Connecticut planning region
        if geoid_str in PLANNING_REGION_CODE_TO_COUNTIES:
            # Map planning region to constituent counties
            result[geoid] = PLANNING_REGION_CODE_TO_COUNTIES[geoid_str]
        else:
            # Not a planning region, use as-is
            result[geoid] = [geoid_str]
    
    return result


def aggregate_county_census_data_to_planning_region(
    planning_region_geoid: str,
    county_census_data: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate census data from multiple counties into a single planning region.
    
    Args:
        planning_region_geoid: Planning region GEOID (e.g., '09120')
        county_census_data: Dictionary mapping county geoid to census data
    
    Returns:
        Aggregated census data for the planning region
    """
    if planning_region_geoid not in PLANNING_REGION_CODE_TO_COUNTIES:
        # Not a planning region, return first county's data
        if county_census_data:
            return list(county_census_data.values())[0]
        return {}
    
    county_geoids = PLANNING_REGION_CODE_TO_COUNTIES[planning_region_geoid]
    
    # Collect all time periods from all counties
    all_time_periods = {}
    county_names = []
    total_pop_by_period = {}
    
    for county_geoid in county_geoids:
        county_data = county_census_data.get(county_geoid, {})
        if not county_data:
            logger.warning(f"No census data found for county {county_geoid}")
            continue
        
        county_names.append(county_data.get('county_name', f'County {county_geoid}'))
        
        time_periods = county_data.get('time_periods', {})
        logger.info(f"County {county_geoid} has time_periods: {list(time_periods.keys())}")
        for period_key, period_data in time_periods.items():
            if period_key not in all_time_periods:
                all_time_periods[period_key] = {
                    'demographics': {
                        'total_population': 0,
                        'white': 0,
                        'black': 0,
                        'asian': 0,
                        'native_american': 0,
                        'hopi': 0,
                        'multi_racial': 0,
                        'hispanic': 0
                    }
                }
                total_pop_by_period[period_key] = 0
            
            demo = period_data.get('demographics', {})
            total_pop = demo.get('total_population', 0)
            total_pop_by_period[period_key] += total_pop
            
            # Sum populations
            all_time_periods[period_key]['demographics']['total_population'] += total_pop
            all_time_periods[period_key]['demographics']['white'] += int(total_pop * demo.get('white_percentage', 0) / 100)
            all_time_periods[period_key]['demographics']['black'] += int(total_pop * demo.get('black_percentage', 0) / 100)
            all_time_periods[period_key]['demographics']['asian'] += int(total_pop * demo.get('asian_percentage', 0) / 100)
            all_time_periods[period_key]['demographics']['native_american'] += int(total_pop * demo.get('native_american_percentage', 0) / 100)
            all_time_periods[period_key]['demographics']['hopi'] += int(total_pop * demo.get('hopi_percentage', 0) / 100)
            all_time_periods[period_key]['demographics']['multi_racial'] += int(total_pop * demo.get('multi_racial_percentage', 0) / 100)
            all_time_periods[period_key]['demographics']['hispanic'] += int(total_pop * demo.get('hispanic_percentage', 0) / 100)
    
    # Calculate percentages from aggregated totals
    # First, collect year/data_year from any county that has this period
    period_metadata = {}
    for county_geoid in county_geoids:
        county_data = county_census_data.get(county_geoid, {})
        if not county_data:
            continue
        time_periods = county_data.get('time_periods', {})
        for period_key, period_data in time_periods.items():
            if period_key not in period_metadata and period_data:
                period_metadata[period_key] = {
                    'year': period_data.get('year', period_key),
                    'data_year': period_data.get('data_year', period_key)
                }
    
    aggregated_periods = {}
    for period_key, period_data in all_time_periods.items():
        total_pop = period_data['demographics']['total_population']
        if total_pop > 0:
            # Get year/data_year from collected metadata, or use defaults
            metadata = period_metadata.get(period_key, {})
            aggregated_periods[period_key] = {
                'year': metadata.get('year', period_key),
                'data_year': metadata.get('data_year', period_key),
                'demographics': {
                    'total_population': total_pop,
                    'white_percentage': round((period_data['demographics']['white'] / total_pop) * 100, 1),
                    'black_percentage': round((period_data['demographics']['black'] / total_pop) * 100, 1),
                    'asian_percentage': round((period_data['demographics']['asian'] / total_pop) * 100, 1),
                    'native_american_percentage': round((period_data['demographics']['native_american'] / total_pop) * 100, 1),
                    'hopi_percentage': round((period_data['demographics']['hopi'] / total_pop) * 100, 1),
                    'multi_racial_percentage': round((period_data['demographics']['multi_racial'] / total_pop) * 100, 1),
                    'hispanic_percentage': round((period_data['demographics']['hispanic'] / total_pop) * 100, 1)
                }
            }
        else:
            # Even if no population, preserve the period structure
            metadata = period_metadata.get(period_key, {})
            aggregated_periods[period_key] = {
                'year': metadata.get('year', period_key),
                'data_year': metadata.get('data_year', period_key),
                'demographics': {
                    'total_population': 0,
                    'white_percentage': 0,
                    'black_percentage': 0,
                    'asian_percentage': 0,
                    'native_american_percentage': 0,
                    'hopi_percentage': 0,
                    'multi_racial_percentage': 0,
                    'hispanic_percentage': 0
                }
            }
    
    # Get planning region name
    planning_region_names = {
        '09110': 'Capitol Planning Region',
        '09120': 'Greater Bridgeport Planning Region',
        '09130': 'Lower Connecticut River Valley Planning Region',
        '09140': 'Naugatuck Valley Planning Region',
        '09150': 'Northeastern Connecticut Planning Region',
        '09160': 'Northwest Hills Planning Region',
        '09170': 'South Central Connecticut Planning Region',
        '09180': 'Southeastern Connecticut Planning Region',
        '09190': 'Western Connecticut Planning Region'
    }
    
    return {
        'county_name': planning_region_names.get(planning_region_geoid, f'Planning Region {planning_region_geoid}'),
        'state_fips': '09',
        'county_fips': planning_region_geoid[2:],  # Last 3 digits
        'time_periods': aggregated_periods
    }


def normalize_connecticut_census_data(
    geoids: List[str],
    census_data_func
) -> Dict[str, Dict[str, Any]]:
    """
    Normalize Connecticut planning regions for census data fetching and aggregate results.
    
    Args:
        geoids: List of GEOIDs (may include planning regions)
        census_data_func: Function to call with county geoids (e.g., get_census_data_for_geoids)
    
    Returns:
        Dictionary mapping original geoid to census data (aggregated for planning regions)
    """
    # Normalize geoids: map planning regions to counties
    geoid_mapping = normalize_connecticut_geoids_for_census(geoids)
    
    # Collect all unique county geoids to fetch
    all_county_geoids = set()
    for county_list in geoid_mapping.values():
        all_county_geoids.update(county_list)
    
    # Fetch census data for all counties
    logger.info(f"Fetching census data for counties: {list(all_county_geoids)}")
    county_census_data = census_data_func(list(all_county_geoids))
    
    # Log what we got back
    logger.info(f"[DEBUG] normalize_connecticut_census_data: Received {len(county_census_data)} counties from census_data_func")
    for county_geoid, data in county_census_data.items():
        if not data:
            logger.warning(f"County {county_geoid} returned empty census data")
        else:
            logger.info(f"[DEBUG] County {county_geoid} data type: {type(data)}, keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            time_periods = data.get('time_periods', {})
            logger.info(f"[DEBUG] County {county_geoid} time_periods: {list(time_periods.keys()) if time_periods else 'EMPTY'}")
            if 'acs' not in time_periods:
                logger.warning(f"County {county_geoid} missing ACS data")
    
    # Aggregate and map back to original geoids
    result = {}
    for original_geoid, county_geoids in geoid_mapping.items():
        if len(county_geoids) == 1:
            # Single county - use data directly (but make a copy to avoid modifying original)
            county_geoid = county_geoids[0]
            county_data = county_census_data.get(county_geoid, {})
            logger.info(f"[DEBUG] Mapping {original_geoid} → {county_geoid}: county_data type={type(county_data)}, empty={not county_data}")
            if county_data:
                # Make a deep copy to avoid modifying the original
                import copy
                county_data_copy = copy.deepcopy(county_data)
                time_periods = county_data_copy.get('time_periods', {})
                logger.info(f"[DEBUG] After deepcopy: time_periods keys={list(time_periods.keys()) if time_periods else 'EMPTY'}")
                logger.info(f"Single county mapping {original_geoid} → {county_geoid}: time_periods={list(time_periods.keys())}")
                # Update county_name to planning region name if it's a planning region
                if original_geoid in PLANNING_REGION_CODE_TO_COUNTIES:
                    planning_region_names = {
                        '09110': 'Capitol Planning Region',
                        '09120': 'Greater Bridgeport Planning Region',
                        '09130': 'Lower Connecticut River Valley Planning Region',
                        '09140': 'Naugatuck Valley Planning Region',
                        '09150': 'Northeastern Connecticut Planning Region',
                        '09160': 'Northwest Hills Planning Region',
                        '09170': 'South Central Connecticut Planning Region',
                        '09180': 'Southeastern Connecticut Planning Region',
                        '09190': 'Western Connecticut Planning Region'
                    }
                    county_data_copy['county_name'] = planning_region_names.get(original_geoid, county_data_copy.get('county_name', ''))
                logger.info(f"[DEBUG] Setting result[{original_geoid}] with time_periods keys: {list(county_data_copy.get('time_periods', {}).keys())}")
                result[original_geoid] = county_data_copy
            else:
                logger.warning(f"No census data found for county {county_geoid} (mapped from {original_geoid})")
                result[original_geoid] = {}
        else:
            # Multiple counties - aggregate
            county_data_subset = {
                geoid: county_census_data.get(geoid, {})
                for geoid in county_geoids
            }
            aggregated = aggregate_county_census_data_to_planning_region(
                original_geoid,
                county_data_subset
            )
            if aggregated:
                time_periods = aggregated.get('time_periods', {})
                if 'acs' not in time_periods:
                    logger.warning(f"Aggregated data for {original_geoid} missing ACS")
            result[original_geoid] = aggregated
    
    # Log final result
    for geoid, data in result.items():
        if data:
            time_periods = data.get('time_periods', {})
            logger.info(f"Final result for {geoid}: time_periods={list(time_periods.keys())}")
    
    return result

