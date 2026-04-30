"""Housing costs section table."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def create_housing_costs_table(housing_data: Dict[str, Dict[str, Any]], geoids: List[str]) -> List[Dict[str, Any]]:
    """
    Create Table 4: Home value, owner costs, owner cost burden, rent, rental burden.
    
    Args:
        housing_data: Dictionary from fetch_acs_housing_data
        geoids: List of GEOID5 codes
    
    Returns:
        List of dictionaries with time period data
    """
    if not housing_data:
        return []
    
    # Aggregate data across all counties for each time period
    time_periods = ['acs_2006_2010', 'acs_2016_2020', 'acs_recent']
    result = []
    
    for period_key in time_periods:
        period_data = {
            'time_period': period_key,
            'year': None,
            'median_home_value': 0,
            'median_owner_costs': 0,
            'owner_cost_burden_pct': 0.0,
            'median_rent': 0,
            'rental_burden_pct': 0.0,
            'median_household_income': 0
        }
        
        counties_with_data = 0
        # Use weighted medians - weight by number of households/units
        home_values_weighted = []  # (value, weight) tuples
        owner_costs_weighted = []
        owner_burdens_weighted = []  # For burden percentages, weight by number of owners
        rents_weighted = []
        rental_burdens_weighted = []  # For burden percentages, weight by number of renters
        household_incomes_weighted = []  # Weight by total occupied units (households)
        
        for geoid in geoids:
            if geoid not in housing_data:
                continue
            county_periods = housing_data[geoid].get('time_periods', {})
            if period_key not in county_periods:
                continue
            
            county_data = county_periods[period_key]
            if not period_data['year']:
                period_data['year'] = county_data.get('year', period_key)
            
            # Get weights (number of households/units)
            total_occupied = county_data.get('total_occupied_units', 0)  # Total households
            owner_occupied = county_data.get('owner_occupied_units', 0)
            renter_occupied = total_occupied - owner_occupied if total_occupied > 0 else 0
            
            # Collect values with weights for weighted median calculation
            if county_data.get('median_home_value', 0) > 0 and owner_occupied > 0:
                home_values_weighted.append((county_data['median_home_value'], owner_occupied))
            if county_data.get('median_owner_costs', 0) > 0 and owner_occupied > 0:
                owner_costs_weighted.append((county_data['median_owner_costs'], owner_occupied))
            # For burden, accept any value and weight by number of owners/renters
            owner_burden_val = county_data.get('owner_cost_burden_pct', 0)
            if owner_burden_val != 0 and owner_occupied > 0:
                owner_burdens_weighted.append((owner_burden_val, owner_occupied))
            if county_data.get('median_rent', 0) > 0 and renter_occupied > 0:
                rents_weighted.append((county_data['median_rent'], renter_occupied))
            rental_burden_val = county_data.get('rental_burden_pct', 0)
            if rental_burden_val != 0 and renter_occupied > 0:
                rental_burdens_weighted.append((rental_burden_val, renter_occupied))
            if county_data.get('median_household_income', 0) > 0 and total_occupied > 0:
                household_incomes_weighted.append((county_data['median_household_income'], total_occupied))
            
            counties_with_data += 1
        
        # Calculate weighted medians
        def weighted_median(values_weights):
            """Calculate weighted median from list of (value, weight) tuples."""
            if not values_weights:
                return None
            # Sort by value
            sorted_vw = sorted(values_weights, key=lambda x: x[0])
            total_weight = sum(w for _, w in sorted_vw)
            cumsum = 0
            target = total_weight / 2
            for value, weight in sorted_vw:
                cumsum += weight
                if cumsum >= target:
                    return value
            # Fallback to last value
            return sorted_vw[-1][0]
        
        if home_values_weighted:
            period_data['median_home_value'] = int(weighted_median(home_values_weighted))
        if owner_costs_weighted:
            period_data['median_owner_costs'] = int(weighted_median(owner_costs_weighted))
        if owner_burdens_weighted:
            period_data['owner_cost_burden_pct'] = float(weighted_median(owner_burdens_weighted))
        if rents_weighted:
            period_data['median_rent'] = int(weighted_median(rents_weighted))
        if rental_burdens_weighted:
            period_data['rental_burden_pct'] = float(weighted_median(rental_burdens_weighted))
        if household_incomes_weighted:
            period_data['median_household_income'] = int(weighted_median(household_incomes_weighted))
        
        if counties_with_data > 0:
            result.append(period_data)
    
    return result


