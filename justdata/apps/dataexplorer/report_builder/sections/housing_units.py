"""Housing units section table."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def create_housing_units_table(housing_data: Dict[str, Dict[str, Any]], geoids: List[str]) -> List[Dict[str, Any]]:
    """
    Create Table 6: Number of units, % that are 1-4 units, % of those that are manufactured/mobile.
    
    Args:
        housing_data: Dictionary from fetch_acs_housing_data
        geoids: List of GEOID5 codes
    
    Returns:
        List of dictionaries with time period data
    """
    if not housing_data:
        return []
    
    time_periods = ['acs_2006_2010', 'acs_2016_2020', 'acs_recent']
    result = []
    
    for period_key in time_periods:
        period_data = {
            'time_period': period_key,
            'year': None,
            'total_units': 0,
            'pct_1_4_units': 0.0,
            'pct_manufactured_mobile': 0.0,
            'pct_5_plus_units': 0.0,
            'pct_1_4_owner_occupied': 0.0
        }
        
        total_units = 0
        units_1_4 = 0
        units_mobile = 0
        owner_occupied_1_4 = 0
        occupied_1_4 = 0  # Total occupied 1-4 units (for denominator)
        
        for geoid in geoids:
            if geoid not in housing_data:
                continue
            county_periods = housing_data[geoid].get('time_periods', {})
            if period_key not in county_periods:
                continue
            
            county_data = county_periods[period_key]
            if not period_data['year']:
                period_data['year'] = county_data.get('year', period_key)
            
            # Aggregate
            county_total = county_data.get('total_housing_units', 0)
            total_units += county_total
            
            # 1-4 units = 1 detached + 1 attached + 2 units + 3-4 units
            county_1_4 = (
                county_data.get('units_1_detached', 0) +
                county_data.get('units_1_attached', 0) +
                county_data.get('units_2', 0) +
                county_data.get('units_3_4', 0)
            )
            units_1_4 += county_1_4
            
            # Owner-occupied 1-4 units (from B25032 - occupied units only)
            county_owner_occupied_1_4 = (
                county_data.get('owner_occupied_1_detached', 0) +
                county_data.get('owner_occupied_1_attached', 0) +
                county_data.get('owner_occupied_2', 0) +
                county_data.get('owner_occupied_3_4', 0)
            )
            owner_occupied_1_4 += county_owner_occupied_1_4
            
            # Total occupied 1-4 units (for denominator - should use B25032, not B25024)
            # B25024 counts all units (occupied + vacant), B25032 counts only occupied
            county_occupied_1_4 = (
                county_data.get('occupied_1_detached', 0) +
                county_data.get('occupied_1_attached', 0) +
                county_data.get('occupied_2', 0) +
                county_data.get('occupied_3_4', 0)
            )
            # If B25032 data not available, fall back to using B25024 (total units) as approximation
            if county_occupied_1_4 == 0:
                county_occupied_1_4 = county_1_4
            
            occupied_1_4 += county_occupied_1_4
            units_mobile += county_data.get('units_mobile', 0)
        
        period_data['total_units'] = total_units
        
        if total_units > 0:
            period_data['pct_1_4_units'] = (units_1_4 / total_units) * 100
            period_data['pct_manufactured_mobile'] = (units_mobile / total_units) * 100
            # 5+ units = total - 1-4 units - mobile (approximate, as mobile might be included in 1-4)
            # Actually, mobile is separate, so 5+ = total - 1-4 - mobile
            units_5_plus = total_units - units_1_4 - units_mobile
            period_data['pct_5_plus_units'] = (units_5_plus / total_units) * 100
        
        # Calculate % of 1-4 units that are owner-occupied
        # Use occupied_1_4 as denominator (occupied units only), not total units_1_4
        if occupied_1_4 > 0:
            period_data['pct_1_4_owner_occupied'] = (owner_occupied_1_4 / occupied_1_4) * 100
        elif units_1_4 > 0:
            # Fallback: if we don't have occupied data, use total units (less accurate)
            period_data['pct_1_4_owner_occupied'] = (owner_occupied_1_4 / units_1_4) * 100
        
        result.append(period_data)
    
    return result


