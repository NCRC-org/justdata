#!/usr/bin/env python3
"""
Census Demographic Analysis Utility
Fetches comprehensive demographic data for AI narrative generation.
Includes age, gender, rent, income, and other demographic indicators.
"""

import os
import requests
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


def _safe_float(value) -> float:
    """Safely convert value to float, handling None and empty strings."""
    if value is None or value == '':
        return 0.0
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return 0.0


def get_comprehensive_demographics_for_county(
    state_fips: str,
    county_fips: str,
    county_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive demographic data for a county including:
    - Race/ethnicity (adult population 18+)
    - Age breakdowns
    - Gender distribution
    - Median rent
    - Median household income
    - Educational attainment
    - Employment status
    
    Args:
        state_fips: Two-digit state FIPS code
        county_fips: Three-digit county FIPS code
        county_name: Optional county name for logging
        api_key: Census API key (if None, tries CENSUS_API_KEY env var)
    
    Returns:
        Dictionary with comprehensive demographic data
    """
    if api_key is None:
        api_key = os.getenv('CENSUS_API_KEY')
    
    if not api_key:
        logger.warning("CENSUS_API_KEY not set - Cannot fetch Census data")
        return {}
    
    # Ensure FIPS codes are properly formatted
    state_fips = str(state_fips).zfill(2)
    county_fips = str(county_fips).zfill(3)
    display_name = county_name or f"State {state_fips}, County {county_fips}"
    
    # Get most recent ACS year (2023)
    acs_year = 2023
    acs_type = 'acs5'
    
    result = {
        'county_name': display_name,
        'state_fips': state_fips,
        'county_fips': county_fips,
        'data_year': f"{acs_year} (ACS 5-year estimates)",
        'demographics': {}
    }
    
    try:
        # 1. Get adult population and race/ethnicity (from existing utility)
        from shared.utils.census_adult_demographics import get_adult_population_demographics_for_county
        
        adult_demo = get_adult_population_demographics_for_county(
            state_fips=state_fips,
            county_fips=county_fips,
            county_name=display_name,
            api_key=api_key
        )
        
        if adult_demo:
            result['adult_population'] = adult_demo.get('adult_population', 0)
            result['demographics'].update(adult_demo.get('demographics', {}))
        
        # 2. Get age breakdowns (18-24, 25-34, 35-44, 45-54, 55-64, 65+)
        age_variables = [
            'B01001_001E',  # Total population (for validation)
            # Male age groups
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
            # Female age groups
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
        
        url = f"https://api.census.gov/data/{acs_year}/acs/{acs_type}"
        params = {
            'get': ','.join(age_variables),
            'for': f'county:{county_fips}',
            'in': f'state:{state_fips}',
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 1:
            headers = data[0]
            row = data[1]
            record = dict(zip(headers, row))
            
            # Calculate age groups (18+)
            age_18_24 = (_safe_int(record.get('B01001_003E', 0)) +  # Male 18-19
                        _safe_int(record.get('B01001_004E', 0)) +  # Male 20-24
                        _safe_int(record.get('B01001_027E', 0)) +  # Female 18-19
                        _safe_int(record.get('B01001_028E', 0)))   # Female 20-24
            
            age_25_34 = (_safe_int(record.get('B01001_005E', 0)) +  # Male 25-29
                        _safe_int(record.get('B01001_006E', 0)) +  # Male 30-34
                        _safe_int(record.get('B01001_029E', 0)) +  # Female 25-29
                        _safe_int(record.get('B01001_030E', 0)))   # Female 30-34
            
            age_35_44 = (_safe_int(record.get('B01001_007E', 0)) +  # Male 35-39
                        _safe_int(record.get('B01001_008E', 0)) +  # Male 40-44
                        _safe_int(record.get('B01001_031E', 0)) +  # Female 35-39
                        _safe_int(record.get('B01001_032E', 0)))   # Female 40-44
            
            age_45_54 = (_safe_int(record.get('B01001_009E', 0)) +  # Male 45-49
                        _safe_int(record.get('B01001_010E', 0)) +  # Male 50-54
                        _safe_int(record.get('B01001_033E', 0)) +  # Female 45-49
                        _safe_int(record.get('B01001_034E', 0)))   # Female 50-54
            
            age_55_64 = (_safe_int(record.get('B01001_011E', 0)) +  # Male 55-59
                        _safe_int(record.get('B01001_012E', 0)) +  # Male 60-64
                        _safe_int(record.get('B01001_035E', 0)) +  # Female 55-59
                        _safe_int(record.get('B01001_036E', 0)))   # Female 60-64
            
            age_65_plus = (_safe_int(record.get('B01001_013E', 0)) +  # Male 65-69
                          _safe_int(record.get('B01001_014E', 0)) +  # Male 70-74
                          _safe_int(record.get('B01001_015E', 0)) +  # Male 75-79
                          _safe_int(record.get('B01001_016E', 0)) +  # Male 80-84
                          _safe_int(record.get('B01001_017E', 0)) +  # Male 85+
                          _safe_int(record.get('B01001_037E', 0)) +  # Female 65-69
                          _safe_int(record.get('B01001_038E', 0)) +  # Female 70-74
                          _safe_int(record.get('B01001_039E', 0)) +  # Female 75-79
                          _safe_int(record.get('B01001_040E', 0)) +  # Female 80-84
                          _safe_int(record.get('B01001_041E', 0)))  # Female 85+
            
            adult_pop = result.get('adult_population', 0)
            if adult_pop > 0:
                result['demographics']['age_breakdown'] = {
                    'age_18_24_percentage': round((age_18_24 / adult_pop * 100), 1),
                    'age_25_34_percentage': round((age_25_34 / adult_pop * 100), 1),
                    'age_35_44_percentage': round((age_35_44 / adult_pop * 100), 1),
                    'age_45_54_percentage': round((age_45_54 / adult_pop * 100), 1),
                    'age_55_64_percentage': round((age_55_64 / adult_pop * 100), 1),
                    'age_65_plus_percentage': round((age_65_plus / adult_pop * 100), 1)
                }
        
        # 3. Get gender distribution (adult population)
        gender_variables = [
            'B01001_002E',  # Total male
            'B01001_026E',  # Total female
        ]
        
        # Calculate from age data we already have
        total_male_adult = sum([
            _safe_int(record.get('B01001_003E', 0)), _safe_int(record.get('B01001_004E', 0)),
            _safe_int(record.get('B01001_005E', 0)), _safe_int(record.get('B01001_006E', 0)),
            _safe_int(record.get('B01001_007E', 0)), _safe_int(record.get('B01001_008E', 0)),
            _safe_int(record.get('B01001_009E', 0)), _safe_int(record.get('B01001_010E', 0)),
            _safe_int(record.get('B01001_011E', 0)), _safe_int(record.get('B01001_012E', 0)),
            _safe_int(record.get('B01001_013E', 0)), _safe_int(record.get('B01001_014E', 0)),
            _safe_int(record.get('B01001_015E', 0)), _safe_int(record.get('B01001_016E', 0)),
            _safe_int(record.get('B01001_017E', 0))
        ])
        
        total_female_adult = sum([
            _safe_int(record.get('B01001_027E', 0)), _safe_int(record.get('B01001_028E', 0)),
            _safe_int(record.get('B01001_029E', 0)), _safe_int(record.get('B01001_030E', 0)),
            _safe_int(record.get('B01001_031E', 0)), _safe_int(record.get('B01001_032E', 0)),
            _safe_int(record.get('B01001_033E', 0)), _safe_int(record.get('B01001_034E', 0)),
            _safe_int(record.get('B01001_035E', 0)), _safe_int(record.get('B01001_036E', 0)),
            _safe_int(record.get('B01001_037E', 0)), _safe_int(record.get('B01001_038E', 0)),
            _safe_int(record.get('B01001_039E', 0)), _safe_int(record.get('B01001_040E', 0)),
            _safe_int(record.get('B01001_041E', 0))
        ])
        
        adult_pop = result.get('adult_population', 0)
        if adult_pop > 0:
            result['demographics']['gender'] = {
                'male_percentage': round((total_male_adult / adult_pop * 100), 1),
                'female_percentage': round((total_female_adult / adult_pop * 100), 1)
            }
        
        # 4. Get median rent (B25064)
        rent_variables = ['B25064_001E']  # Median gross rent
        
        url_rent = f"https://api.census.gov/data/{acs_year}/acs/{acs_type}"
        params_rent = {
            'get': ','.join(rent_variables),
            'for': f'county:{county_fips}',
            'in': f'state:{state_fips}',
            'key': api_key
        }
        
        try:
            response_rent = requests.get(url_rent, params=params_rent, timeout=30)
            response_rent.raise_for_status()
            data_rent = response_rent.json()
            
            if data_rent and len(data_rent) > 1:
                headers_rent = data_rent[0]
                row_rent = data_rent[1]
                record_rent = dict(zip(headers_rent, row_rent))
                median_rent = _safe_int(record_rent.get('B25064_001E', 0))
                if median_rent > 0:
                    result['demographics']['median_rent'] = median_rent
        except Exception as e:
            logger.warning(f"Could not fetch median rent for {display_name}: {e}")
        
        # 5. Get median household income (B19013)
        income_variables = ['B19013_001E']  # Median household income
        
        url_income = f"https://api.census.gov/data/{acs_year}/acs/{acs_type}"
        params_income = {
            'get': ','.join(income_variables),
            'for': f'county:{county_fips}',
            'in': f'state:{state_fips}',
            'key': api_key
        }
        
        try:
            response_income = requests.get(url_income, params=params_income, timeout=30)
            response_income.raise_for_status()
            data_income = response_income.json()
            
            if data_income and len(data_income) > 1:
                headers_income = data_income[0]
                row_income = data_income[1]
                record_income = dict(zip(headers_income, row_income))
                median_income = _safe_int(record_income.get('B19013_001E', 0))
                if median_income > 0:
                    result['demographics']['median_household_income'] = median_income
        except Exception as e:
            logger.warning(f"Could not fetch median income for {display_name}: {e}")
        
        # 6. Get educational attainment (B15003) - for population 25+
        # Note: This is for 25+, not 18+, but still useful context
        education_variables = [
            'B15003_001E',  # Total (25+)
            'B15003_022E',  # Bachelor's degree
            'B15003_023E',  # Master's degree
            'B15003_024E',  # Professional degree
            'B15003_025E',  # Doctorate degree
        ]
        
        url_education = f"https://api.census.gov/data/{acs_year}/acs/{acs_type}"
        params_education = {
            'get': ','.join(education_variables),
            'for': f'county:{county_fips}',
            'in': f'state:{state_fips}',
            'key': api_key
        }
        
        try:
            response_education = requests.get(url_education, params=params_education, timeout=30)
            response_education.raise_for_status()
            data_education = response_education.json()
            
            if data_education and len(data_education) > 1:
                headers_education = data_education[0]
                row_education = data_education[1]
                record_education = dict(zip(headers_education, row_education))
                
                total_25_plus = _safe_int(record_education.get('B15003_001E', 0))
                bachelors_plus = (
                    _safe_int(record_education.get('B15003_022E', 0)) +  # Bachelor's
                    _safe_int(record_education.get('B15003_023E', 0)) +  # Master's
                    _safe_int(record_education.get('B15003_024E', 0)) +  # Professional
                    _safe_int(record_education.get('B15003_025E', 0))    # Doctorate
                )
                
                if total_25_plus > 0:
                    result['demographics']['education'] = {
                        'bachelors_plus_percentage': round((bachelors_plus / total_25_plus * 100), 1)
                    }
        except Exception as e:
            logger.warning(f"Could not fetch education data for {display_name}: {e}")
        
        logger.info(f"Successfully fetched comprehensive demographics for {display_name}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching comprehensive demographics for {display_name}: {e}")
        import traceback
        traceback.print_exc()
        return {}
