"""Owner-occupancy section table."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def create_owner_occupancy_table(housing_data: Dict[str, Dict[str, Any]], geoids: List[str], 
                                  population_data: Dict[str, Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Create Table 5: Owner occupied % overall, then by race (limit to races with 1%+ of population).
    
    Args:
        housing_data: Dictionary from fetch_acs_housing_data
        geoids: List of GEOID5 codes
        population_data: Optional historical census data to determine which races have 1%+ population
    
    Returns:
        List of dictionaries with time period data
    """
    if not housing_data:
        return []
    
    # Determine which races have 1%+ of population (use most recent ACS data)
    race_threshold = 0.01  # 1%
    races_to_include = set()
    
    if population_data:
        # Check most recent ACS data for each county
        for geoid in geoids:
            if geoid not in population_data:
                continue
            county_data = population_data[geoid]
            time_periods = county_data.get('time_periods', {})
            acs_data = time_periods.get('acs', {})
            demographics = acs_data.get('demographics', {})
            
            total_pop = demographics.get('total_population', 0)
            if total_pop > 0:
                if demographics.get('white_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('white')
                if demographics.get('black_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('black')
                if demographics.get('asian_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('asian')
                if demographics.get('native_american_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('native')
                if demographics.get('hopi_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('pacific')
                if demographics.get('multi_racial_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('multi')
                if demographics.get('hispanic_percentage', 0) >= race_threshold * 100:
                    races_to_include.add('hispanic')
    else:
        # If no population data, include all races
        races_to_include = {'white', 'black', 'asian', 'native', 'pacific', 'multi', 'hispanic'}
    
    time_periods = ['acs_2006_2010', 'acs_2016_2020', 'acs_recent']
    result = []
    
    for period_key in time_periods:
        period_data = {
            'time_period': period_key,
            'year': None,
            'owner_occupied_pct_overall': 0.0,
            'owner_occupied_by_race': {}
        }
        
        total_occupied = 0
        total_owner_occupied = 0
        race_totals = {}
        race_owner_occupied = {}
        
        for geoid in geoids:
            if geoid not in housing_data:
                continue
            county_periods = housing_data[geoid].get('time_periods', {})
            if period_key not in county_periods:
                continue
            
            county_data = county_periods[period_key]
            if not period_data['year']:
                period_data['year'] = county_data.get('year', period_key)
            
            # Aggregate overall
            total_occupied += county_data.get('total_occupied_units', 0)
            total_owner_occupied += county_data.get('owner_occupied_units', 0)
            
            # Aggregate by race
            race_mapping = {
                'white': ('total_occupied_white', 'owner_occupied_white'),
                'black': ('total_occupied_black', 'owner_occupied_black'),
                'asian': ('total_occupied_asian', 'owner_occupied_asian'),
                'native': ('total_occupied_native', 'owner_occupied_native'),
                'pacific': ('total_occupied_pacific', 'owner_occupied_pacific'),
                'multi': ('total_occupied_multi', 'owner_occupied_multi'),
                'hispanic': ('total_occupied_hispanic', 'owner_occupied_hispanic'),
            }
            
            for race, (total_key, owner_key) in race_mapping.items():
                if race not in races_to_include:
                    continue
                
                if race not in race_totals:
                    race_totals[race] = 0
                    race_owner_occupied[race] = 0
                
                race_totals[race] += county_data.get(total_key, 0)
                race_owner_occupied[race] += county_data.get(owner_key, 0)
        
        # Calculate percentages
        if total_occupied > 0:
            period_data['owner_occupied_pct_overall'] = (total_owner_occupied / total_occupied) * 100
        
        # Store population shares for sorting (calculate for all periods, but use most recent for sorting)
        period_data['population_shares'] = {}
        for race in races_to_include:
            if race in race_totals and race_totals[race] > 0:
                period_data['owner_occupied_by_race'][race] = (race_owner_occupied[race] / race_totals[race]) * 100
                # Calculate population share (% of total occupied units)
                if total_occupied > 0:
                    period_data['population_shares'][race] = (race_totals[race] / total_occupied) * 100
        
        result.append(period_data)
    
    return result


