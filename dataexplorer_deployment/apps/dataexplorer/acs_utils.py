#!/usr/bin/env python3
"""
ACS (American Community Survey) data utilities for DataExplorer.
Fetches 2024 ACS demographic data for selected geographies.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
import pandas as pd
from .config import DataExplorerConfig

# Try to load .env from parent DREAM Analysis directory if available
try:
    from dotenv import load_dotenv
    # Try loading from parent DREAM Analysis directory (absolute path)
    dream_analysis_env = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\.env")
    if dream_analysis_env.exists():
        load_dotenv(dream_analysis_env, override=False)  # Don't override if already set
except ImportError:
    pass


def get_acs_data_for_geoids(geoids: List[str]) -> Dict[str, Any]:
    """
    Get 2024 ACS demographic data for a list of GEOID5 codes (counties).
    
    Args:
        geoids: List of 5-digit GEOID5 codes (e.g., ['48059', '48253'])
    
    Returns:
        Dictionary with:
        - total_population: Total population across all geoids
        - demographics: Dict mapping demographic group names to percentages
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Try using Census API if available
        api_key = os.getenv('CENSUS_API_KEY')
        logger.info(f"[ACS] Checking for CENSUS_API_KEY - Key present: {api_key is not None}, Key length: {len(api_key) if api_key else 0}")
        
        if not api_key:
            # Log warning but return empty structure - will show N/A in frontend
            logger.warning("CENSUS_API_KEY not set - ACS data will not be available. Set CENSUS_API_KEY environment variable to enable ACS data.")
            logger.warning(f"[ACS] Environment variables checked. CENSUS_API_KEY in os.environ: {'CENSUS_API_KEY' in os.environ}")
            return {
                'total_population': 0,
                'demographics': {}
            }
        
        # Use direct HTTP requests instead of census library to avoid metadata API calls
        # ACS variables for 2024 (use 2022 as latest available 5-year)
        acs_year = 2022  # Latest 5-year ACS available
        acs_variables = [
            'B01003_001E',  # Total population
            'B03002_001E',  # Total (for race breakdown)
            'B03002_003E',  # White alone (not Hispanic)
            'B03002_004E',  # Black or African American alone (not Hispanic)
            'B03002_005E',  # American Indian/Alaska Native alone (not Hispanic)
            'B03002_006E',  # Asian alone (not Hispanic)
            'B03002_007E',  # Native Hawaiian/Pacific Islander alone (not Hispanic)
            'B03002_012E',  # Hispanic or Latino (of any race)
        ]
        
        total_pop = 0
        white = 0
        black = 0
        asian = 0
        native_am = 0
        hawaiian_pi = 0
        hispanic = 0
        
        # Fetch data for each geoid (county) using direct API call
        logger.info(f"[ACS] Fetching demographic data for {len(geoids)} geoids: {geoids}")
        
        for geoid in geoids:
            if len(geoid) != 5:
                logger.warning(f"[ACS] Invalid geoid length: {geoid} (expected 5 digits)")
                continue
            
            state_fips = geoid[:2]
            county_fips = geoid[2:]
            
            try:
                # Direct API call - much faster, no metadata requests
                url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
                params = {
                    'get': ','.join(acs_variables),
                    'for': f'county:{county_fips}',
                    'in': f'state:{state_fips}',
                    'key': api_key
                }
                logger.info(f"[ACS] Making API call for geoid {geoid} (State: {state_fips}, County: {county_fips})")
                response = requests.get(url, params=params, timeout=30)
                logger.info(f"[ACS] API response status: {response.status_code}")
                response.raise_for_status()
                acs_data = response.json()
                logger.info(f"[ACS] API returned {len(acs_data)} rows for geoid {geoid}")
                
                if acs_data and len(acs_data) > 1:
                    # First row is headers, second row is data
                    headers = acs_data[0]
                    data_row = acs_data[1]
                    
                    # Create dict from headers and data
                    record = dict(zip(headers, data_row))
                    
                    county_pop = int(record.get('B01003_001E', 0) or 0)
                    total_pop += county_pop
                    
                    white += int(record.get('B03002_003E', 0) or 0)
                    black += int(record.get('B03002_004E', 0) or 0)
                    asian += int(record.get('B03002_006E', 0) or 0)
                    native_am += int(record.get('B03002_005E', 0) or 0)
                    hawaiian_pi += int(record.get('B03002_007E', 0) or 0)
                    hispanic += int(record.get('B03002_012E', 0) or 0)
            except Exception as e:
                # Log error but continue with other geoids
                logger.error(f"[ACS] Error fetching ACS data for geoid {geoid}: {e}")
                import traceback
                logger.error(f"[ACS] Traceback: {traceback.format_exc()}")
                continue
        
        # Calculate percentages
        demographics = {}
        if total_pop > 0:
            demographics = {
                'Hispanic or Latino': round((hispanic / total_pop) * 100, 1),
                'Black or African American': round((black / total_pop) * 100, 1),
                'White': round((white / total_pop) * 100, 1),
                'Asian': round((asian / total_pop) * 100, 1),
                'Native American or Alaska Native': round((native_am / total_pop) * 100, 1),
                'Native Hawaiian or Other Pacific Islander': round((hawaiian_pi / total_pop) * 100, 1)
            }
            logger.info(f"[ACS] Calculated demographics - Total pop: {total_pop}, Demographics: {demographics}")
        else:
            logger.warning(f"[ACS] Total population is 0 - cannot calculate percentages")
        
        return {
            'total_population': total_pop,
            'demographics': demographics
        }
    
    except ImportError:
        # Census library not installed
        return {
            'total_population': 0,
            'demographics': {}
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[ACS] Exception in get_acs_data_for_geoids: {e}")
        import traceback
        logger.error(f"[ACS] Traceback: {traceback.format_exc()}")
        return {
            'total_population': 0,
            'demographics': {}
        }


def get_hud_low_mod_data_for_geoids(geoids: List[str]) -> Dict[str, Any]:
    """
    Get HUD Low-Mod Summary Data for a list of GEOID5 codes (counties).
    
    This function fetches HUD's Low and Moderate Income Summary Data which provides
    accurate percentages of households at or below 80% of AMI, calculated using
    HUD's official methodology.
    
    Data source: HUD Exchange ACS Low-Mod Summary Data
    URL: https://www.hudexchange.info/programs/acs-low-mod-summary-data/acs-low-mod-summary-data-local-government/
    
    Args:
        geoids: List of 5-digit GEOID5 codes (e.g., ['48059', '48253'])
    
    Returns:
        Dictionary with:
        - household_income_distribution: Dict mapping income categories to percentages
        - data_source: "HUD Low-Mod Summary Data"
        - metro_ami: Metro area AMI from HUD (if available)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Import HUD data processor
        from .hud_data_processor import get_hud_data_for_geoids, load_hud_file_if_needed, process_hud_excel_file
        
        # Ensure HUD file is available
        hud_file = load_hud_file_if_needed()
        if hud_file and not (Path(__file__).parent.parent.parent / 'data' / 'hud' / 'hud_county_data.json').exists():
            # Process the file if cache doesn't exist
            logger.info("[HUD Low-Mod] Processing HUD Excel file...")
            process_hud_excel_file(hud_file)
        
        # Get data for requested geoids
        hud_data = get_hud_data_for_geoids(geoids)
        
        if hud_data.get('household_income_distribution'):
            logger.info(f"[HUD Low-Mod] Successfully retrieved HUD data for {len(geoids)} counties")
            return hud_data
        else:
            logger.warning("[HUD Low-Mod] No HUD data available, will fall back to Census B19001")
            return {
                'household_income_distribution': {},
                'data_source': None,
                'metro_ami': None
            }
    
    except ImportError:
        logger.warning("[HUD Low-Mod] HUD data processor not available. Using Census B19001 as fallback.")
        return {
            'household_income_distribution': {},
            'data_source': None,
            'metro_ami': None
        }
    except Exception as e:
        logger.error(f"[HUD Low-Mod] Error fetching HUD data: {e}")
        import traceback
        logger.error(f"[HUD Low-Mod] Traceback: {traceback.format_exc()}")
        return {
            'household_income_distribution': {},
            'data_source': None,
            'metro_ami': None
        }


def get_household_income_distribution_for_geoids(geoids: List[str], use_hud_data: bool = True) -> Dict[str, Any]:
    """
    Get 2024 ACS household income distribution data for a list of GEOID5 codes (counties).
    Calculates the percentage of households in each income bracket relative to metro area median income (AMI).
    
    This function calculates: Share of households that are themselves low, moderate, middle, or upper income
    (based on household income relative to metro AMI).
    
    Uses weighted averages across counties based on total households in each county.
    
    Args:
        geoids: List of 5-digit GEOID5 codes (e.g., ['48059', '48253'])
    
    Returns:
        Dictionary with:
        - total_households: Total households across all geoids (weighted sum)
        - household_income_distribution: Dict mapping income bracket names to percentages
        - metro_ami: Metro area median family income (if available)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Try HUD data first if requested
    if use_hud_data:
        hud_data = get_hud_low_mod_data_for_geoids(geoids)
        if hud_data.get('household_income_distribution'):
            logger.info("[ACS Household Income] Using HUD Low-Mod Summary Data")
            return {
                'total_households': 0,  # HUD data may not include total households
                'household_income_distribution': hud_data.get('household_income_distribution', {}),
                'metro_ami': hud_data.get('metro_ami'),
                'data_source': 'HUD Low-Mod Summary Data'
            }
        else:
            logger.info("[ACS Household Income] HUD data not available, falling back to Census B19001")
    
    # Fall back to Census B19001 method
    try:
        # Try using Census API if available
        api_key = os.getenv('CENSUS_API_KEY')
        logger.info(f"[ACS Household Income] Using Census B19001 - Key present: {api_key is not None}")
        
        if not api_key:
            logger.warning("CENSUS_API_KEY not set - Household income data will not be available.")
            return {
                'total_households': 0,
                'household_income_distribution': {},
                'metro_ami': None,
                'data_source': None
            }
        
        # First, try to get CBSA code(s) for the counties to fetch accurate metro AMI
        metro_ami = None
        cbsa_codes = set()
        
        try:
            from .data_utils import get_bigquery_client
            from .config import DataExplorerConfig
            
            client = get_bigquery_client()
            project_id = DataExplorerConfig.GCP_PROJECT_ID
            geoid_list = "', '".join([str(g).zfill(5) for g in geoids])
            
            # Query to get CBSA codes for these counties
            cbsa_query = f"""
            SELECT DISTINCT CAST(cbsa_code AS STRING) as cbsa_code
            FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
            WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') IN ('{geoid_list}')
              AND cbsa_code IS NOT NULL
            """
            query_job = client.query(cbsa_query)
            results = query_job.result()
            cbsa_codes = {str(row.cbsa_code) for row in results if row.cbsa_code}
            
            logger.info(f"[ACS Household Income] Found {len(cbsa_codes)} CBSA code(s) for counties: {list(cbsa_codes)}")
            
            # Try to get metro AMI from CBSA code(s) - use first CBSA if multiple
            if cbsa_codes:
                cbsa_code = list(cbsa_codes)[0]  # Use first CBSA if multiple
                acs_year = 2022
                url_cbsa = f"https://api.census.gov/data/{acs_year}/acs/acs5"
                params_cbsa = {
                    'get': 'B19113_001E',  # Median Family Income
                    'for': f'metropolitan statistical area/micropolitan statistical area:{cbsa_code}',
                    'key': api_key
                }
                try:
                    response_cbsa = requests.get(url_cbsa, params=params_cbsa, timeout=30)
                    response_cbsa.raise_for_status()
                    cbsa_data = response_cbsa.json()
                    if cbsa_data and len(cbsa_data) > 1:
                        headers_cbsa = cbsa_data[0]
                        data_row_cbsa = cbsa_data[1]
                        record_cbsa = dict(zip(headers_cbsa, data_row_cbsa))
                        cbsa_median = record_cbsa.get('B19113_001E')
                        if cbsa_median and cbsa_median != 'None' and cbsa_median != '-666666666':
                            metro_ami = float(cbsa_median)
                            logger.info(f"[ACS Household Income] Got metro AMI from CBSA {cbsa_code}: ${metro_ami:,.0f}")
                except Exception as e:
                    logger.warning(f"[ACS Household Income] Could not fetch AMI from CBSA {cbsa_code}: {e}")
        
        except Exception as e:
            logger.warning(f"[ACS Household Income] Could not query BigQuery for CBSA codes: {e}")
        
        # If we don't have metro AMI from CBSA, fall back to averaging county medians
        if metro_ami is None:
            logger.info("[ACS Household Income] Falling back to averaging county median incomes")
            total_median_income = 0
            metro_count = 0
            median_income_variable = 'B19113_001E'
            acs_year = 2022
            
            for geoid in geoids:
                if len(geoid) != 5:
                    continue
                
                state_fips = geoid[:2]
                county_fips = geoid[2:]
                
                try:
                    url_median = f"https://api.census.gov/data/{acs_year}/acs/acs5"
                    params_median = {
                        'get': median_income_variable,
                        'for': f'county:{county_fips}',
                        'in': f'state:{state_fips}',
                        'key': api_key
                    }
                    response_median = requests.get(url_median, params=params_median, timeout=30)
                    response_median.raise_for_status()
                    median_data = response_median.json()
                    
                    if median_data and len(median_data) > 1:
                        headers_median = median_data[0]
                        data_row_median = median_data[1]
                        record_median = dict(zip(headers_median, data_row_median))
                        county_median = record_median.get(median_income_variable)
                        if county_median and county_median != 'None' and county_median != '-666666666':
                            total_median_income += float(county_median)
                            metro_count += 1
                except Exception as e:
                    logger.warning(f"[ACS Household Income] Error fetching county median for {geoid}: {e}")
                    continue
            
            if metro_count > 0:
                metro_ami = total_median_income / metro_count
                logger.info(f"[ACS Household Income] Calculated average metro AMI from {metro_count} counties: ${metro_ami:,.0f}")
        
        # Now fetch household income distribution for all counties (weighted by household count)
        acs_year = 2022
        acs_variables = [
            'B19001_001E',  # Total households
            'B19001_002E',  # < $10,000
            'B19001_003E',  # $10,000 to $14,999
            'B19001_004E',  # $15,000 to $19,999
            'B19001_005E',  # $20,000 to $24,999
            'B19001_006E',  # $25,000 to $29,999
            'B19001_007E',  # $30,000 to $34,999
            'B19001_008E',  # $35,000 to $39,999
            'B19001_009E',  # $40,000 to $44,999
            'B19001_010E',  # $45,000 to $49,999
            'B19001_011E',  # $50,000 to $59,999
            'B19001_012E',  # $60,000 to $74,999
            'B19001_013E',  # $75,000 to $99,999
            'B19001_014E',  # $100,000 to $124,999
            'B19001_015E',  # $125,000 to $149,999
            'B19001_016E',  # $150,000 to $199,999
            'B19001_017E',  # $200,000+
        ]
        
        total_households = 0
        household_counts_by_bracket = {
            '<10k': 0,
            '10k-15k': 0,
            '15k-20k': 0,
            '20k-25k': 0,
            '25k-30k': 0,
            '30k-35k': 0,
            '35k-40k': 0,
            '40k-45k': 0,
            '45k-50k': 0,
            '50k-60k': 0,
            '60k-75k': 0,
            '75k-100k': 0,
            '100k-125k': 0,
            '125k-150k': 0,
            '150k-200k': 0,
            '200k+': 0
        }
        
        # Fetch data for each geoid (county) - weighted by household count
        for geoid in geoids:
            if len(geoid) != 5:
                continue
            
            state_fips = geoid[:2]
            county_fips = geoid[2:]
            
            try:
                url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
                params = {
                    'get': ','.join(acs_variables),
                    'for': f'county:{county_fips}',
                    'in': f'state:{state_fips}',
                    'key': api_key
                }
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                acs_data = response.json()
                
                if acs_data and len(acs_data) > 1:
                    headers = acs_data[0]
                    data_row = acs_data[1]
                    record = dict(zip(headers, data_row))
                    
                    county_households = int(record.get('B19001_001E', 0) or 0)
                    total_households += county_households
                    
                    # Aggregate by bracket (weighted sum across counties)
                    household_counts_by_bracket['<10k'] += int(record.get('B19001_002E', 0) or 0)
                    household_counts_by_bracket['10k-15k'] += int(record.get('B19001_003E', 0) or 0)
                    household_counts_by_bracket['15k-20k'] += int(record.get('B19001_004E', 0) or 0)
                    household_counts_by_bracket['20k-25k'] += int(record.get('B19001_005E', 0) or 0)
                    household_counts_by_bracket['25k-30k'] += int(record.get('B19001_006E', 0) or 0)
                    household_counts_by_bracket['30k-35k'] += int(record.get('B19001_007E', 0) or 0)
                    household_counts_by_bracket['35k-40k'] += int(record.get('B19001_008E', 0) or 0)
                    household_counts_by_bracket['40k-45k'] += int(record.get('B19001_009E', 0) or 0)
                    household_counts_by_bracket['45k-50k'] += int(record.get('B19001_010E', 0) or 0)
                    household_counts_by_bracket['50k-60k'] += int(record.get('B19001_011E', 0) or 0)
                    household_counts_by_bracket['60k-75k'] += int(record.get('B19001_012E', 0) or 0)
                    household_counts_by_bracket['75k-100k'] += int(record.get('B19001_013E', 0) or 0)
                    household_counts_by_bracket['100k-125k'] += int(record.get('B19001_014E', 0) or 0)
                    household_counts_by_bracket['125k-150k'] += int(record.get('B19001_015E', 0) or 0)
                    household_counts_by_bracket['150k-200k'] += int(record.get('B19001_016E', 0) or 0)
                    household_counts_by_bracket['200k+'] += int(record.get('B19001_017E', 0) or 0)
                        
            except Exception as e:
                logger.error(f"[ACS Household Income] Error fetching data for geoid {geoid}: {e}")
                import traceback
                logger.error(f"[ACS Household Income] Traceback: {traceback.format_exc()}")
                continue
        
        logger.info(f"[ACS Household Income] Total households across all counties: {total_households:,}")
        
        # Calculate income distribution percentages using bracket upper bounds for more accurate classification
        # Low: ≤50% AMI, Moderate: 50-80% AMI, Middle: 80-120% AMI, Upper: >120% AMI
        distribution = {}
        if total_households > 0 and metro_ami:
            low_threshold = metro_ami * 0.50
            moderate_threshold = metro_ami * 0.80
            middle_threshold = metro_ami * 1.20
            
            # Use bracket upper bounds for classification (more conservative/accurate)
            bracket_upper_bounds = {
                '<10k': 10000,
                '10k-15k': 15000,
                '15k-20k': 20000,
                '20k-25k': 25000,
                '25k-30k': 30000,
                '30k-35k': 35000,
                '35k-40k': 40000,
                '40k-45k': 45000,
                '45k-50k': 50000,
                '50k-60k': 60000,
                '60k-75k': 75000,
                '75k-100k': 100000,
                '100k-125k': 125000,
                '125k-150k': 150000,
                '150k-200k': 200000,
                '200k+': float('inf')  # All 200k+ are upper income
            }
            
            low_income = 0
            moderate_income = 0
            middle_income = 0
            upper_income = 0
            
            for bracket, count in household_counts_by_bracket.items():
                upper_bound = bracket_upper_bounds.get(bracket, 0)
                if upper_bound <= low_threshold:
                    low_income += count
                elif upper_bound <= moderate_threshold:
                    moderate_income += count
                elif upper_bound <= middle_threshold:
                    middle_income += count
                else:
                    upper_income += count
            
            distribution = {
                'Low Income': round((low_income / total_households) * 100, 1),
                'Moderate Income': round((moderate_income / total_households) * 100, 1),
                'Middle Income': round((middle_income / total_households) * 100, 1),
                'Upper Income': round((upper_income / total_households) * 100, 1)
            }
            
            logger.info(f"[ACS Household Income] Distribution calculated - Low: {distribution['Low Income']}%, "
                       f"Moderate: {distribution['Moderate Income']}%, Middle: {distribution['Middle Income']}%, "
                       f"Upper: {distribution['Upper Income']}%")
        elif total_households > 0:
            logger.warning("[ACS Household Income] No AMI available - cannot calculate distribution")
            distribution = {}
        
        return {
            'total_households': total_households,
            'household_income_distribution': distribution,
            'metro_ami': metro_ami,
            'data_source': 'Census B19001 (approximated using bracket upper bounds)'
        }
    
    except Exception as e:
        logger.error(f"[ACS Household Income] Exception in get_household_income_distribution_for_geoids: {e}")
        import traceback
        logger.error(f"[ACS Household Income] Traceback: {traceback.format_exc()}")
        return {
            'total_households': 0,
            'household_income_distribution': {},
            'metro_ami': None,
            'data_source': None
        }


def get_tract_household_distributions_for_geoids(geoids: List[str], avg_minority_percentage: Optional[float] = None) -> Dict[str, Any]:
    """
    Get tract-level household distributions for income and minority categories.
    Calculates the percentage of households living in different tract types.
    
    This function calculates TWO distinct datasets:
    1. tract_income_distribution: Share of households that live in low/moderate/middle/upper income census tracts
    2. tract_minority_distribution: Share of households that live in low/moderate/middle/high minority census tracts
    
    Uses weighted averages across counties based on total households in each tract.
    
    Uses BigQuery to get tract classifications and Census API to get household counts.
    
    Args:
        geoids: List of 5-digit GEOID5 codes (e.g., ['48059', '48253'])
        avg_minority_percentage: Average minority percentage for the geography (for MMCT categorization)
    
    Returns:
        Dictionary with:
        - tract_income_distribution: Dict mapping income tract categories to percentages of households
        - tract_minority_distribution: Dict mapping minority tract categories to percentages of households
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        from .data_utils import execute_query
        from .config import DataExplorerConfig
        
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        dataset = DataExplorerConfig.HMDA_DATASET
        table = DataExplorerConfig.HMDA_TABLE
        
        # Build WHERE clause for geoids
        geoid_list = "', '".join([str(g).zfill(5) for g in geoids])
        
        # Query to get unique tracts with their income and minority classifications from HMDA
        query = f"""
        WITH unique_tracts AS (
            SELECT DISTINCT
                h.census_tract,
                LPAD(CAST(h.county_code AS STRING), 5, '0') as geoid5,
                CAST(h.tract_to_msa_income_percentage AS FLOAT64) as tract_income_pct,
                CAST(h.tract_minority_population_percent AS FLOAT64) as tract_minority_pct
            FROM `{project_id}.{dataset}.{table}` h
            WHERE LPAD(CAST(h.county_code AS STRING), 5, '0') IN ('{geoid_list}')
              AND CAST(h.activity_year AS STRING) = '2024'
              AND h.census_tract IS NOT NULL
        ),
        tract_minority_stats AS (
            SELECT
                AVG(tract_minority_pct) as mean_minority,
                STDDEV(tract_minority_pct) as stddev_minority
            FROM unique_tracts
            WHERE tract_minority_pct IS NOT NULL
        )
        SELECT
            t.census_tract,
            t.geoid5,
            t.tract_income_pct,
            t.tract_minority_pct,
            CASE
                WHEN t.tract_income_pct IS NOT NULL AND t.tract_income_pct <= 50 THEN 'Low Income'
                WHEN t.tract_income_pct IS NOT NULL AND t.tract_income_pct > 50 AND t.tract_income_pct <= 80 THEN 'Moderate Income'
                WHEN t.tract_income_pct IS NOT NULL AND t.tract_income_pct > 80 AND t.tract_income_pct <= 120 THEN 'Middle Income'
                WHEN t.tract_income_pct IS NOT NULL AND t.tract_income_pct > 120 THEN 'Upper Income'
                ELSE NULL
            END as income_category,
            CASE
                WHEN t.tract_minority_pct IS NOT NULL AND s.mean_minority IS NOT NULL AND s.stddev_minority IS NOT NULL THEN
                    CASE
                        WHEN t.tract_minority_pct < (s.mean_minority - s.stddev_minority) THEN 'Low Minority'
                        WHEN t.tract_minority_pct < s.mean_minority THEN 'Moderate Minority'
                        WHEN t.tract_minority_pct < (s.mean_minority + s.stddev_minority) THEN 'Middle Minority'
                        ELSE 'High Minority'
                    END
                ELSE NULL
            END as minority_category
        FROM unique_tracts t
        CROSS JOIN tract_minority_stats s
        """
        
        results = execute_query(query)
        
        logger.info(f"[ACS Tract Distributions] Processing {len(geoids)} counties: {geoids}")
        logger.info(f"[ACS Tract Distributions] Found {len(results)} unique tracts across {len(geoids)} counties")
        
        if not results:
            logger.warning(f"[ACS Tract Distributions] No tract data found in HMDA table for geoids: {geoids}")
            return {
                'tract_income_distribution': {},
                'tract_minority_distribution': {}
            }
        
        # Get household counts from Census API for each tract
        api_key = os.getenv('CENSUS_API_KEY')
        if not api_key:
            logger.warning("CENSUS_API_KEY not set - Cannot fetch tract household data")
            return {
                'tract_income_distribution': {},
                'tract_minority_distribution': {}
            }
        
        acs_year = 2022  # Latest 5-year ACS available (2022 = 2018-2022 data)
        # Note: ACS 2024 5-year estimates not yet available, using 2022
        household_variable = 'B11001_001E'  # Total households
        
        # Group tracts by county for processing
        tracts_by_county = {}
        for row in results:
            geoid5 = row.get('geoid5')
            tract = row.get('census_tract')
            if geoid5 and tract:
                if geoid5 not in tracts_by_county:
                    tracts_by_county[geoid5] = []
                tracts_by_county[geoid5].append({
                    'tract': tract,
                    'income_category': row.get('income_category'),
                    'minority_category': row.get('minority_category'),
                    'tract_minority_pct': row.get('tract_minority_pct')  # Include minority percentage for MMCT calculation
                })
        
        # Group counties by state for batched API calls
        counties_by_state = {}
        for geoid5 in tracts_by_county.keys():
            if len(geoid5) != 5:
                continue
            state_fips = geoid5[:2]
            county_fips = geoid5[2:]
            if state_fips not in counties_by_state:
                counties_by_state[state_fips] = []
            counties_by_state[state_fips].append({
                'geoid5': geoid5,
                'county_fips': county_fips
            })
        
        # Fetch household counts from Census API (batched by state)
        income_households = {'Low Income': 0, 'Moderate Income': 0, 'Middle Income': 0, 'Upper Income': 0}
        minority_households = {'Low Minority': 0, 'Moderate Minority': 0, 'Middle Minority': 0, 'High Minority': 0}
        total_all_households = 0  # Track total households for MMCT calculation
        
        logger.info(f"[ACS Tract Distributions] Processing {len(tracts_by_county)} counties across {len(counties_by_state)} states - batching API calls by state")
        
        # Process each state, batching counties together
        for state_fips, counties in counties_by_state.items():
            county_fips_list = [c['county_fips'] for c in counties]
            county_fips_str = ','.join(county_fips_list)
            
            logger.info(f"[ACS Tract Distributions] Fetching Census data for state {state_fips}, counties: {county_fips_str} ({len(counties)} counties)")
            
            # Fetch household data for all tracts in all counties of this state in a single API call
            try:
                url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
                params = {
                    'get': f'NAME,{household_variable}',
                    'for': 'tract:*',
                    'in': f'state:{state_fips} county:{county_fips_str}',
                    'key': api_key
                }
                logger.debug(f"[ACS Tract Distributions] Census API URL: {url}")
                logger.debug(f"[ACS Tract Distributions] Census API params: {params}")
                response = requests.get(url, params=params, timeout=60)  # Increased timeout for larger requests
                response.raise_for_status()
                tract_data = response.json()
                
                logger.info(f"[ACS Tract Distributions] Census API returned {len(tract_data) - 1 if tract_data else 0} tracts for state {state_fips} ({len(counties)} counties)")
                
                if tract_data and len(tract_data) > 1:
                    headers = tract_data[0]
                    data_rows = tract_data[1:]
                    
                    # Create a map of (state+county+tract) to household count for all counties in this state
                    # Census API returns state, county, and tract codes
                    tract_household_map_by_geoid5 = {}  # Map geoid5 -> {tract_code -> households}
                    
                    # Check if 'state' and 'county' columns exist in the response
                    has_state_col = 'state' in headers
                    has_county_col = 'county' in headers
                    
                    for data_row in data_rows:
                        record = dict(zip(headers, data_row))
                        tract_code_raw = record.get('tract', '')
                        
                        if tract_code_raw and str(tract_code_raw).upper() not in ['NA', 'N/A', 'NULL', 'NONE', '']:
                            try:
                                # Get state and county codes from response
                                if has_state_col and has_county_col:
                                    state_code = str(record.get('state', '')).zfill(2)
                                    county_code = str(record.get('county', '')).zfill(3)
                                    geoid5_from_response = state_code + county_code
                                else:
                                    # Fallback: use the state we're querying
                                    geoid5_from_response = state_fips + str(record.get('county', '')).zfill(3)
                                
                                # Normalize tract code to 6 digits with leading zeros
                                if isinstance(tract_code_raw, (int, float)):
                                    tract_code = str(int(tract_code_raw)).zfill(6)
                                else:
                                    tract_str = str(tract_code_raw).strip()
                                    if '.' in tract_str:
                                        parts = tract_str.split('.')
                                        tract_str = parts[0] + parts[1][:2].ljust(2, '0')
                                    tract_str = ''.join(c for c in tract_str if c.isdigit())
                                    if tract_str:
                                        tract_code = tract_str.zfill(6)
                                    else:
                                        continue
                                
                                households = int(record.get(household_variable, 0) or 0)
                                if households > 0:
                                    if geoid5_from_response not in tract_household_map_by_geoid5:
                                        tract_household_map_by_geoid5[geoid5_from_response] = {}
                                    tract_household_map_by_geoid5[geoid5_from_response][tract_code] = households
                            except (ValueError, TypeError) as e:
                                logger.debug(f"[ACS Tract Distributions] Skipping invalid tract code '{tract_code_raw}': {e}")
                                continue
                    
                    # Process each county from this state
                    for county_info in counties:
                        geoid5 = county_info['geoid5']
                        tracts = tracts_by_county.get(geoid5, [])
                        
                        if not tracts:
                            continue
                        
                        # Get the tract household map for this specific county
                        tract_household_map = tract_household_map_by_geoid5.get(geoid5, {})
                        
                        logger.info(f"[ACS Tract Distributions] Processing county {geoid5}: {len(tract_household_map)} tracts from API, {len(tracts)} tracts from HMDA")
                        
                        # Log sample tract codes from Census API for debugging (first county only)
                        if geoid5 == counties[0]['geoid5'] and tract_household_map:
                            sample_census_tracts = list(tract_household_map.keys())[:5]
                            logger.info(f"[ACS Tract Distributions] Sample Census API tract codes (normalized): {sample_census_tracts}")
                        
                        # Track matching statistics
                        matched_tracts = 0
                        unmatched_tracts = 0
                        total_households_matched = 0
                        
                        # Match tracts to their categories and sum households
                        # HMDA tract codes might be stored as strings or numbers, normalize to 6-digit string
                        sample_hmda_tracts = []
                        sample_hmda_normalized = []
                        
                        # Pre-normalize all Census tract codes for faster lookup
                        census_tract_normalized = {}
                        census_tract_as_int = {}
                        for census_tract_code, census_households in tract_household_map.items():
                            census_tract_normalized[census_tract_code] = census_households
                            try:
                                census_tract_as_int[int(census_tract_code)] = census_households
                            except (ValueError, TypeError):
                                pass
                        
                        for tract_info in tracts:
                            tract_raw = tract_info['tract']
                            households = 0
                            
                            # Skip invalid tract codes
                            if tract_raw is None or str(tract_raw).upper() in ['NA', 'N/A', 'NULL', 'NONE', '']:
                                continue
                            
                            # Log first few HMDA tract codes for debugging
                            if len(sample_hmda_tracts) < 5:
                                sample_hmda_tracts.append(str(tract_raw))
                            
                            try:
                                # Handle both string and numeric tract codes
                                # CRITICAL: HMDA tract codes may be full 11-digit GEOIDs (state+county+tract)
                                # or just 6-digit tract codes. Census API returns only 6-digit tract codes.
                                # Extract the last 6 digits to get the tract portion.
                                if isinstance(tract_raw, (int, float)):
                                    # Convert to string and take last 6 digits
                                    tract_str = str(int(tract_raw))
                                    # If it's longer than 6 digits, it's a full GEOID - take last 6
                                    if len(tract_str) > 6:
                                        tract_code = tract_str[-6:].zfill(6)
                                    else:
                                        tract_code = tract_str.zfill(6)
                                else:
                                    # Remove any decimal point and normalize
                                    tract_str = str(tract_raw).strip()
                                    # Handle decimal tracts (e.g., "1234.56" -> "123456")
                                    if '.' in tract_str:
                                        parts = tract_str.split('.')
                                        tract_str = parts[0] + parts[1][:2].ljust(2, '0')  # Take integer part + 2 decimal digits
                                    # Remove any non-numeric characters
                                    tract_str = ''.join(c for c in tract_str if c.isdigit())
                                    if not tract_str:
                                        continue  # Skip if no valid digits
                                    # If it's longer than 6 digits, it's a full GEOID - take last 6
                                    if len(tract_str) > 6:
                                        tract_code = tract_str[-6:].zfill(6)
                                    else:
                                        tract_code = tract_str.zfill(6)
                                
                                # Log normalized tract code for first few
                                if len(sample_hmda_normalized) < 5:
                                    sample_hmda_normalized.append(tract_code)
                                
                                # Try exact match first (fastest)
                                households = census_tract_normalized.get(tract_code, 0)
                                
                                # If no match, try matching as integers (removes leading zeros)
                                if households == 0:
                                    try:
                                        hmda_tract_int = int(tract_code)
                                        households = census_tract_as_int.get(hmda_tract_int, 0)
                                    except (ValueError, TypeError):
                                        pass
                            
                            except (ValueError, TypeError) as e:
                                logger.debug(f"[ACS Tract Distributions] Error processing tract '{tract_raw}': {e}")
                                continue
                            
                            # Only add households if we found a match (households > 0)
                            if households > 0:
                                matched_tracts += 1
                                total_households_matched += households
                                total_all_households += households  # Track total for MMCT calculation
                                
                                income_cat = tract_info.get('income_category')
                                if income_cat and income_cat in income_households:
                                    income_households[income_cat] += households
                                
                                minority_cat = tract_info.get('minority_category')
                                if minority_cat and minority_cat in minority_households:
                                    minority_households[minority_cat] += households
                                
                                # Calculate MMCT: tracts where minority % > 50%
                                # Note: tract_minority_pct comes from HMDA BigQuery table, not Census API
                                tract_minority_pct = tract_info.get('tract_minority_pct')
                                if tract_minority_pct is not None:
                                    try:
                                        tract_minority_pct_float = float(tract_minority_pct)
                                        if tract_minority_pct_float > 50:
                                            if 'MMCT' not in minority_households:
                                                minority_households['MMCT'] = 0
                                            minority_households['MMCT'] += households
                                            # Removed per-tract debug logging to reduce log noise
                                    except (ValueError, TypeError):
                                        pass
                            else:
                                unmatched_tracts += 1
                        
                        # Log sample HMDA tract codes for debugging
                        if sample_hmda_tracts:
                            logger.debug(f"[ACS Tract Distributions] Sample HMDA tract codes (raw): {sample_hmda_tracts}")
                        
                        # Log sample normalized HMDA tract codes
                        if sample_hmda_normalized:
                            logger.info(f"[ACS Tract Distributions] Sample HMDA tract codes (normalized): {sample_hmda_normalized}")
                        
                        logger.info(f"[ACS Tract Distributions] County {geoid5}: Matched {matched_tracts}/{len(tracts)} tracts, {total_households_matched:,} households")
                            
            except Exception as e:
                logger.warning(f"[ACS Tract Distributions] Error fetching tract household data for state {state_fips}: {e}")
                import traceback
                logger.debug(f"[ACS Tract Distributions] Traceback: {traceback.format_exc()}")
                continue
        
        # Calculate percentages (weighted by household count across all counties)
        total_income_households = sum(income_households.values())
        total_minority_households = sum(minority_households.values())
        # total_all_households is already calculated above (sum of all matched households)
        
        logger.info(f"[ACS Tract Distributions] Income tract households (weighted sum): {income_households}, Total: {total_income_households:,}")
        logger.info(f"[ACS Tract Distributions] Minority tract households (weighted sum): {minority_households}, Total: {total_minority_households:,}")
        logger.info(f"[ACS Tract Distributions] Total all households (for MMCT): {total_all_households:,}")
        
        income_percentages = {}
        if total_income_households > 0:
            for category, households in income_households.items():
                income_percentages[category] = round((households / total_income_households) * 100, 1)
        
        minority_percentages = {}
        if total_minority_households > 0:
            for category, households in minority_households.items():
                minority_percentages[category] = round((households / total_minority_households) * 100, 1)
        
        # Calculate MMCT percentage: % of all households in tracts with minority % > 50%
        # This is the percentage of households living in census tracts where more than 50% of the population is minority
        mmct_percentage = None
        mmct_households = minority_households.get('MMCT', 0)
        if total_all_households > 0:
            if mmct_households > 0:
                mmct_percentage = round((mmct_households / total_all_households) * 100, 1)
                logger.info(f"[ACS Tract Distributions] MMCT calculation: {mmct_households:,} households in MMCT tracts (minority % > 50%) out of {total_all_households:,} total households = {mmct_percentage}%")
            else:
                mmct_percentage = 0.0  # No MMCT tracts found
                logger.info(f"[ACS Tract Distributions] MMCT calculation: 0 households in MMCT tracts out of {total_all_households:,} total households = 0.0%")
        else:
            logger.warning(f"[ACS Tract Distributions] MMCT calculation failed: total_all_households={total_all_households} (no matched households)")
        
        # Remove MMCT from minority_percentages if it exists (it's a separate metric)
        if 'MMCT' in minority_percentages:
            del minority_percentages['MMCT']
        
        logger.info(f"[ACS Tract Distributions] Final percentages - Income tracts: {income_percentages}, Minority tracts: {minority_percentages}, MMCT: {mmct_percentage}%")
        
        return {
            'tract_income_distribution': income_percentages,
            'tract_minority_distribution': minority_percentages,
            'mmct_percentage': mmct_percentage  # Percentage of households in tracts with minority % > 50%
        }
    
    except Exception as e:
        logger.error(f"[ACS Tract Distributions] Error fetching tract household distributions: {e}")
        import traceback
        logger.error(f"[ACS Tract Distributions] Traceback: {traceback.format_exc()}")
        return {
            'tract_income_distribution': {},
            'tract_minority_distribution': {},
            'mmct_percentage': None
        }


def get_tract_race_data_for_geoids(geoids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Get race data by census tract from Census API for matching with lending data.
    
    Args:
        geoids: List of 5-digit GEOID5 codes (counties)
    
    Returns:
        Dictionary mapping census tract geoid10 to race percentages:
        {
            'geoid10': {
                'white_percent': float,
                'black_percent': float,
                'hispanic_percent': float,
                'asian_percent': float,
                'native_american_percent': float,
                'hawaiian_pi_percent': float,
                'majority_race': str  # The race group with highest percentage
            }
        }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        api_key = os.getenv('CENSUS_API_KEY')
        if not api_key:
            logger.warning("CENSUS_API_KEY not set - Cannot fetch tract race data")
            return {}
        
        acs_year = 2022  # Latest 5-year ACS available
        acs_variables = [
            'B01003_001E',  # Total population
            'B03002_003E',  # White alone (not Hispanic)
            'B03002_004E',  # Black or African American alone (not Hispanic)
            'B03002_005E',  # American Indian/Alaska Native alone (not Hispanic)
            'B03002_006E',  # Asian alone (not Hispanic)
            'B03002_007E',  # Native Hawaiian/Pacific Islander alone (not Hispanic)
            'B03002_012E',  # Hispanic or Latino (of any race)
        ]
        
        tract_race_data = {}
        
        # Group geoids by state for batching
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
        
        logger.info(f"[Tract Race Data] Processing {len(geoids)} counties across {len(counties_by_state)} states")
        
        # Process each state, batching counties together
        for state_fips, counties in counties_by_state.items():
            county_fips_list = [c['county_fips'] for c in counties]
            county_fips_str = ','.join(county_fips_list)
            
            logger.info(f"[Tract Race Data] Fetching race data for state {state_fips}, counties: {county_fips_str}")
            
            try:
                url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
                params = {
                    'get': ','.join(acs_variables),
                    'for': 'tract:*',
                    'in': f'state:{state_fips} county:{county_fips_str}',
                    'key': api_key
                }
                response = requests.get(url, params=params, timeout=60)
                response.raise_for_status()
                tract_data = response.json()
                
                logger.info(f"[Tract Race Data] Census API returned {len(tract_data) - 1 if tract_data else 0} tracts for state {state_fips}")
                
                if tract_data and len(tract_data) > 1:
                    headers = tract_data[0]
                    data_rows = tract_data[1:]
                    
                    for data_row in data_rows:
                        record = dict(zip(headers, data_row))
                        tract_code_raw = record.get('tract', '')
                        state_code = str(record.get('state', '')).zfill(2)
                        county_code = str(record.get('county', '')).zfill(3)
                        
                        if tract_code_raw and str(tract_code_raw).upper() not in ['NA', 'N/A', 'NULL', 'NONE', '']:
                            try:
                                # Normalize tract code to 6 digits
                                if isinstance(tract_code_raw, (int, float)):
                                    tract_code = str(int(tract_code_raw)).zfill(6)
                                else:
                                    tract_str = str(tract_code_raw).strip()
                                    if '.' in tract_str:
                                        parts = tract_str.split('.')
                                        tract_str = parts[0] + parts[1][:2].ljust(2, '0')
                                    tract_str = ''.join(c for c in tract_str if c.isdigit())
                                    if tract_str:
                                        tract_code = tract_str.zfill(6)
                                    else:
                                        continue
                                
                                # Create geoid10 (state + county + tract)
                                geoid10 = state_code + county_code + tract_code
                                
                                # Get population counts
                                total_pop = int(record.get('B01003_001E', 0) or 0)
                                white = int(record.get('B03002_003E', 0) or 0)
                                black = int(record.get('B03002_004E', 0) or 0)
                                asian = int(record.get('B03002_006E', 0) or 0)
                                native_am = int(record.get('B03002_005E', 0) or 0)
                                hawaiian_pi = int(record.get('B03002_007E', 0) or 0)
                                hispanic = int(record.get('B03002_012E', 0) or 0)
                                
                                if total_pop > 0:
                                    # Calculate percentages
                                    white_pct = (white / total_pop) * 100
                                    black_pct = (black / total_pop) * 100
                                    hispanic_pct = (hispanic / total_pop) * 100
                                    asian_pct = (asian / total_pop) * 100
                                    native_am_pct = (native_am / total_pop) * 100
                                    hawaiian_pi_pct = (hawaiian_pi / total_pop) * 100
                                    
                                    # Determine majority race
                                    race_percentages = {
                                        'White': white_pct,
                                        'Black or African American': black_pct,
                                        'Hispanic or Latino': hispanic_pct,
                                        'Asian': asian_pct,
                                        'Native American or Alaska Native': native_am_pct,
                                        'Native Hawaiian or Other Pacific Islander': hawaiian_pi_pct
                                    }
                                    majority_race = max(race_percentages, key=race_percentages.get) if race_percentages else 'Unknown'
                                    
                                    tract_race_data[geoid10] = {
                                        'white_percent': round(white_pct, 2),
                                        'black_percent': round(black_pct, 2),
                                        'hispanic_percent': round(hispanic_pct, 2),
                                        'asian_percent': round(asian_pct, 2),
                                        'native_american_percent': round(native_am_pct, 2),
                                        'hawaiian_pi_percent': round(hawaiian_pi_pct, 2),
                                        'majority_race': majority_race,
                                        'total_population': total_pop
                                    }
                            except (ValueError, TypeError) as e:
                                logger.debug(f"[Tract Race Data] Skipping invalid tract: {e}")
                                continue
                
            except Exception as e:
                logger.error(f"[Tract Race Data] Error fetching data for state {state_fips}: {e}")
                import traceback
                logger.error(f"[Tract Race Data] Traceback: {traceback.format_exc()}")
                continue
        
        logger.info(f"[Tract Race Data] Fetched race data for {len(tract_race_data)} census tracts")
        return tract_race_data
    
    except Exception as e:
        logger.error(f"[Tract Race Data] Exception: {e}")
        import traceback
        logger.error(f"[Tract Race Data] Traceback: {traceback.format_exc()}")
        return {}

