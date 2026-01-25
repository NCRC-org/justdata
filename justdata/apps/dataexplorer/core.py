#!/usr/bin/env python3
"""
DataExplorer Area Analysis Core Logic
Handles area-based analysis for HMDA mortgage lending data.
"""

import os
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from justdata.apps.dataexplorer.config import OUTPUT_DIR, PROJECT_ID, HMDA_YEARS
from justdata.apps.dataexplorer.data_utils import execute_hmda_query, validate_geoids, validate_years
from justdata.apps.dataexplorer.area_analysis_processor import process_hmda_area_analysis
from justdata.shared.utils.progress_tracker import ProgressTracker
from justdata.shared.utils.census_adult_demographics import get_adult_population_demographics_for_geoids
from justdata.shared.utils.census_historical_utils import get_census_data_for_geoids
import logging

logger = logging.getLogger(__name__)


def parse_wizard_parameters(wizard_data: Dict[str, Any]) -> tuple:
    """
    Parse parameters from wizard data structure.
    
    Args:
        wizard_data: Dictionary from wizard with geography and filters
        
    Returns:
        Tuple of (geoids_list, years_list, filters_dict)
    """
    geography = wizard_data.get('geography', {})
    counties = geography.get('counties', [])
    
    # Convert county FIPS codes to list if needed
    if isinstance(counties, str):
        counties = [c.strip() for c in counties.split(',') if c.strip()]
    
    # Get years - use wizard data if available, otherwise default to most recent 5 years
    if 'years' in wizard_data and wizard_data['years']:
        years = wizard_data['years']
        if isinstance(years, str):
            # Parse comma-separated string
            years = [int(y.strip()) for y in years.split(',') if y.strip()]
        elif not isinstance(years, list):
            years = [int(years)]
    else:
        # Default to most recent 5 years (dynamic based on current year, capped at 2024 for HMDA)
        from datetime import datetime
        current_year = datetime.now().year
        max_year = min(current_year, 2024)  # HMDA data only available through 2024
        years = list(range(max_year - 4, max_year + 1))  # Most recent 5 years, capped at 2024
    
    # Parse filters from wizard data
    filters = wizard_data.get('filters', {})
    
    # Convert wizard filter format to query format
    query_filters = {}
    
    # Action taken: 'origination' -> ['1']
    if filters.get('actionTaken') == 'origination':
        query_filters['action_taken'] = ['1']
    elif filters.get('actionTaken') == 'application':
        query_filters['action_taken'] = ['1', '2', '3', '4', '5']
    
    # Occupancy
    occupancy_map = {
        'owner-occupied': '1',
        'second-home': '2',
        'investor': '3'
    }
    if filters.get('occupancy'):
        query_filters['occupancy'] = [occupancy_map.get(o, o) for o in filters.get('occupancy', [])]
    
    # Loan purpose - Convert wizard format to LendSight format for query function
    # Wizard format: ['home-purchase', 'refinance', 'home-equity']
    # LendSight format: ['purchase', 'refinance', 'equity']
    if filters.get('loanPurpose'):
        purpose_list = []
        for p in filters.get('loanPurpose', []):
            if p == 'home-purchase':
                purpose_list.append('purchase')
            elif p == 'refinance':
                purpose_list.append('refinance')
            elif p == 'home-equity':
                purpose_list.append('equity')
        if purpose_list:
            query_filters['loan_purpose'] = purpose_list
    
    # Property type / total units
    # Note: The SQL template uses total_units, not property_type
    if filters.get('totalUnits') == '1-4':
        query_filters['total_units'] = ['1', '2', '3', '4']  # 1-4 units
    elif filters.get('totalUnits') == '5+':
        # For 5+ units, use special marker to indicate >= 5 handling needed
        query_filters['total_units'] = ['5+']  # Special marker for query builder to handle >= 5
    
    # Construction type - FIXED: Now applied to query_filters
    construction_map = {
        'site-built': '1',
        'manufactured': '2'
    }
    if filters.get('construction'):
        query_filters['construction'] = [construction_map.get(c, c) for c in filters.get('construction', [])]
    
    # Loan type - FIXED: Now applied to query_filters
    loan_type_map = {
        'conventional': '1',
        'fha': '2',
        'va': '3',
        'rhs': '4'
    }
    if filters.get('loanType'):
        query_filters['loan_type'] = [loan_type_map.get(lt, lt) for lt in filters.get('loanType', [])]
    
    # Reverse mortgage
    query_filters['exclude_reverse_mortgages'] = filters.get('reverseMortgage', True)
    
    return counties, years, query_filters


def run_area_analysis(
    wizard_data: Dict[str, Any],
    job_id: str = None,
    progress_tracker: Optional[ProgressTracker] = None
) -> Dict[str, Any]:
    """
    Run area analysis for web interface.
    
    Args:
        wizard_data: Dictionary from wizard with geography and filters
        job_id: Optional job ID for tracking
        progress_tracker: Optional progress tracker for real-time updates
        
    Returns:
        Dictionary with success status and results
    """
    try:
        # Initialize progress
        if progress_tracker:
            progress_tracker.update_progress('initializing', 0, 'Initializing area analysis...')
        
        # Parse parameters
        geoids, years, filters = parse_wizard_parameters(wizard_data)
        
        if not geoids:
            return {
                'success': False,
                'error': 'No counties selected. Please select at least one county.'
            }
        
        if progress_tracker:
            progress_tracker.update_progress('preparing_data', 5, f'Preparing data for {len(geoids)} counties...')
        
        # Validate inputs
        try:
            validated_geoids = validate_geoids(geoids)
            validated_years = validate_years(years)
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }
        
        if progress_tracker:
            progress_tracker.update_progress('connecting_db', 10, 'Connecting to database...')
        
        # Import cache utilities
        from justdata.apps.dataexplorer.cache_utils import (
            load_hmda_data, save_hmda_data,
            load_census_data, save_census_data,
            load_historical_census_data, save_historical_census_data,
            load_hud_data, save_hud_data
        )
        
        # Get census demographics data (check cache first)
        if progress_tracker:
            progress_tracker.update_progress('querying_data', 20, 'Fetching population demographics...')
        
        # Try to load from cache
        census_data = load_census_data(validated_geoids)
        historical_census_data = load_historical_census_data(validated_geoids)
        
        # For Connecticut planning regions, we need to ensure ACS data is included
        # Check if we have census_data (which has ACS) but historical_census_data is missing ACS
        if census_data and historical_census_data:
            # Check if historical_census_data is missing ACS but census_data has it
            for geoid in validated_geoids:
                if geoid in historical_census_data and geoid in census_data:
                    hist_time_periods = historical_census_data[geoid].get('time_periods', {})
                    if 'acs' not in hist_time_periods and census_data[geoid]:
                        # Add ACS data from census_data to historical_census_data
                        acs_data = census_data[geoid]
                        if 'adult_population' in acs_data and 'demographics' in acs_data:
                            # Convert census_data format to historical_census_data format
                            data_year = acs_data.get('data_year', '')
                            data_source = acs_data.get('data_source', '')
                            # Extract year from data_source
                            import re
                            year_match = re.search(r'(\d{4})', data_source or data_year or '2023')
                            acs_year_str = year_match.group(1) if year_match else '2023'
                            
                            historical_census_data[geoid]['time_periods']['acs'] = {
                                'year': f"{acs_year_str} ACS",
                                'data_year': data_year or f"{acs_year_str} (ACS 5-year estimates)",
                                'demographics': {
                                    'total_population': acs_data.get('adult_population', 0),
                                    'white_percentage': acs_data['demographics'].get('white_percentage', 0),
                                    'black_percentage': acs_data['demographics'].get('black_percentage', 0),
                                    'asian_percentage': acs_data['demographics'].get('asian_percentage', 0),
                                    'native_american_percentage': acs_data['demographics'].get('native_american_percentage', 0),
                                    'hopi_percentage': acs_data['demographics'].get('hopi_percentage', 0),
                                    'multi_racial_percentage': acs_data['demographics'].get('multi_racial_percentage', 0),
                                    'hispanic_percentage': acs_data['demographics'].get('hispanic_percentage', 0)
                                }
                            }
                            logger.info(f"Added ACS data to historical_census_data for {geoid} from census_data")
        
        # Check if cached historical data has any time periods per geoid
        # FIXED: Accept data with at least one time period instead of requiring all three
        # This prevents census data from being completely missing when only some periods are available
        if historical_census_data:
            has_valid_data = True
            for geoid, county_data in historical_census_data.items():
                if not county_data:
                    has_valid_data = False
                    logger.info(f"Cached historical census data is empty for {geoid}, will refetch")
                    break
                time_periods = county_data.get('time_periods', {})
                # Accept data with at least one time period (instead of requiring all three)
                if not time_periods or len(time_periods) == 0:
                    has_valid_data = False
                    logger.info(f"Cached historical census data has empty time_periods for {geoid}, will refetch")
                    break
                # Log which periods are available (but don't reject data that's missing some)
                available = list(time_periods.keys())
                required_periods = ['census2010', 'census2020', 'acs']
                missing_periods = [p for p in required_periods if p not in time_periods]
                if missing_periods:
                    logger.info(f"Cached historical census data for {geoid} missing periods: {missing_periods} (has: {available}), but will use available data")

            if not has_valid_data:
                historical_census_data = None  # Force refetch
        
        if census_data is None:
            # Cache miss - fetch from API
            try:
                census_data = get_adult_population_demographics_for_geoids(validated_geoids)
                save_census_data(validated_geoids, census_data)
                logger.info("Cached census demographics data")
            except Exception as e:
                logger.warning(f"Error fetching census data: {e}")
                census_data = {}
        
        if historical_census_data is None:
            # Cache miss or incomplete - fetch from API
            try:
                # Check API key before attempting fetch
                import os
                # Try uppercase first (standard), then lowercase (some systems use lowercase)
                api_key = os.getenv('CENSUS_API_KEY') or os.getenv('census_api_key')
                if not api_key:
                    logger.error("[CRITICAL] CENSUS_API_KEY environment variable is not set! Cannot fetch Census data.")
                    logger.error("[CRITICAL] Checked both CENSUS_API_KEY and census_api_key environment variables")
                    logger.error("[CRITICAL] Please set CENSUS_API_KEY (or census_api_key) in your environment variables.")
                    historical_census_data = {}
                else:
                    api_key_preview = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
                    logger.info(f"[DEBUG] CENSUS_API_KEY is set (preview: {api_key_preview}), length: {len(api_key)}")
                    logger.info(f"[DEBUG] About to fetch historical census data for {len(validated_geoids)} geoids: {validated_geoids}")
                    
                    # Normalize Connecticut planning regions to counties for census API
                    from justdata.apps.dataexplorer.connecticut_census_normalizer import normalize_connecticut_census_data
                    logger.info(f"[DEBUG] Calling normalize_connecticut_census_data with geoids: {validated_geoids}")
                    historical_census_data = normalize_connecticut_census_data(
                        validated_geoids,
                        get_census_data_for_geoids
                    )
                    logger.info(f"[DEBUG] normalize_connecticut_census_data returned: type={type(historical_census_data)}, empty={not historical_census_data}, keys={list(historical_census_data.keys()) if historical_census_data else []}")
                
                # Debug: Log structure of historical_census_data after fetching
                if historical_census_data:
                    logger.info(f"[DEBUG] Fetched historical_census_data with {len(historical_census_data)} counties")
                    if len(historical_census_data) > 0:
                        first_geoid = list(historical_census_data.keys())[0]
                        first_county = historical_census_data[first_geoid]
                        logger.info(f"[DEBUG] Sample county ({first_geoid}) type: {type(first_county)}")
                        logger.info(f"[DEBUG] Sample county ({first_geoid}) keys: {list(first_county.keys()) if isinstance(first_county, dict) else 'Not a dict'}")
                        if isinstance(first_county, dict) and 'time_periods' in first_county:
                            time_periods_keys = list(first_county['time_periods'].keys())
                            logger.info(f"[DEBUG] time_periods keys: {time_periods_keys}")
                            if not time_periods_keys:
                                logger.error(f"[CRITICAL] Fetched historical_census_data has empty time_periods for {first_geoid}!")
                        else:
                            logger.warning(f"[DEBUG] time_periods missing in fetched data!")
                
                # Verify geoids have at least one time period (relaxed validation)
                # FIXED: Accept data with at least one time period instead of requiring all three
                valid_data = {}
                required_periods = ['census2010', 'census2020', 'acs']
                for geoid, county_data in historical_census_data.items():
                    if not county_data:
                        logger.warning(f"Historical census data for {geoid} is empty, skipping")
                        continue
                    time_periods = county_data.get('time_periods', {})
                    if not time_periods or len(time_periods) == 0:
                        logger.warning(f"Historical census data for {geoid} has empty time_periods, skipping")
                        continue
                    # Check which periods are available
                    available_periods = list(time_periods.keys())
                    missing_periods = [p for p in required_periods if p not in time_periods]
                    if missing_periods:
                        logger.info(f"Historical census data for {geoid} missing periods: {missing_periods} (has: {available_periods}), using available data")
                    # Accept data with at least one time period
                    valid_data[geoid] = county_data

                # Use valid data (with at least one time period)
                if valid_data:
                    historical_census_data = valid_data
                    # Save to cache if we have any valid data
                    save_historical_census_data(validated_geoids, historical_census_data)
                    logger.info(f"Cached historical census demographics data for {len(valid_data)} counties")
                else:
                    logger.warning("No valid historical census data found after fetching")
                    historical_census_data = {}
                    # Don't save empty/invalid data to cache
                
                # If historical_census_data is empty or missing ACS, try to build it from census_data
                if census_data:
                    for geoid in validated_geoids:
                        if geoid in census_data and census_data[geoid]:
                            # If historical_census_data is empty, create structure for this geoid
                            if geoid not in historical_census_data:
                                historical_census_data[geoid] = {'time_periods': {}}
                            
                            # Check if ACS is missing from historical_census_data
                            hist_time_periods = historical_census_data[geoid].get('time_periods', {})
                            if 'acs' not in hist_time_periods:
                                # Add ACS data from census_data to historical_census_data
                                acs_data = census_data[geoid]
                                if 'adult_population' in acs_data and 'demographics' in acs_data:
                                    # Convert census_data format to historical_census_data format
                                    data_year = acs_data.get('data_year', '')
                                    data_source = acs_data.get('data_source', '')
                                    # Extract year from data_source
                                    import re
                                    year_match = re.search(r'(\d{4})', data_source or data_year or '2023')
                                    acs_year_str = year_match.group(1) if year_match else '2023'
                                    
                                    if 'time_periods' not in historical_census_data[geoid]:
                                        historical_census_data[geoid]['time_periods'] = {}
                                    
                                    historical_census_data[geoid]['time_periods']['acs'] = {
                                        'year': f"{acs_year_str} ACS",
                                        'data_year': data_year or f"{acs_year_str} (ACS 5-year estimates)",
                                        'demographics': {
                                            'total_population': acs_data.get('adult_population', 0),
                                            'white_percentage': acs_data['demographics'].get('white_percentage', 0),
                                            'black_percentage': acs_data['demographics'].get('black_percentage', 0),
                                            'asian_percentage': acs_data['demographics'].get('asian_percentage', 0),
                                            'native_american_percentage': acs_data['demographics'].get('native_american_percentage', 0),
                                            'hopi_percentage': acs_data['demographics'].get('hopi_percentage', 0),
                                            'multi_racial_percentage': acs_data['demographics'].get('multi_racial_percentage', 0),
                                            'hispanic_percentage': acs_data['demographics'].get('hispanic_percentage', 0)
                                        }
                                    }
                                    logger.info(f"Added ACS data to historical_census_data for {geoid} from census_data")
                
                # Save to cache if we have valid data (with at least one time period)
                # FIXED: Cache data with any available time periods instead of requiring all three
                if historical_census_data:
                    # Verify all geoids have at least one time period before saving
                    has_valid_data = True
                    for geoid, county_data in historical_census_data.items():
                        if not county_data:
                            has_valid_data = False
                            break
                        time_periods = county_data.get('time_periods', {})
                        if not time_periods or len(time_periods) == 0:
                            has_valid_data = False
                            break

                    if has_valid_data:
                        save_historical_census_data(validated_geoids, historical_census_data)
                        logger.info(f"Cached historical census data for {len(historical_census_data)} counties")
                    else:
                        logger.warning("Not saving historical census data to cache - no valid data")
            except Exception as e:
                logger.error(f"Error fetching historical census data: {e}", exc_info=True)
                historical_census_data = {}
        
        # Final fallback: If historical_census_data is still empty but we have census_data, create minimal structure
        if (not historical_census_data or len(historical_census_data) == 0) and census_data:
            logger.info("[DEBUG] Creating historical_census_data from census_data as fallback")
            historical_census_data = {}
            for geoid in validated_geoids:
                if geoid in census_data and census_data[geoid]:
                    acs_data = census_data[geoid]
                    if 'adult_population' in acs_data and 'demographics' in acs_data:
                        data_year = acs_data.get('data_year', '')
                        data_source = acs_data.get('data_source', '')
                        import re
                        year_match = re.search(r'(\d{4})', data_source or data_year or '2023')
                        acs_year_str = year_match.group(1) if year_match else '2023'
                        
                        historical_census_data[geoid] = {
                            'time_periods': {
                                'acs': {
                                    'year': f"{acs_year_str} ACS",
                                    'data_year': data_year or f"{acs_year_str} (ACS 5-year estimates)",
                                    'demographics': {
                                        'total_population': acs_data.get('adult_population', 0),
                                        'white_percentage': acs_data['demographics'].get('white_percentage', 0),
                                        'black_percentage': acs_data['demographics'].get('black_percentage', 0),
                                        'asian_percentage': acs_data['demographics'].get('asian_percentage', 0),
                                        'native_american_percentage': acs_data['demographics'].get('native_american_percentage', 0),
                                        'hopi_percentage': acs_data['demographics'].get('hopi_percentage', 0),
                                        'multi_racial_percentage': acs_data['demographics'].get('multi_racial_percentage', 0),
                                        'hispanic_percentage': acs_data['demographics'].get('hispanic_percentage', 0)
                                    }
                                }
                            }
                        }
            if historical_census_data:
                logger.info(f"[DEBUG] Created historical_census_data from census_data for {len(historical_census_data)} counties")
        
        # Try to load from cache (raw list of dicts, not DataFrame)
        import pickle
        from pathlib import Path
        from justdata.apps.dataexplorer.cache_utils import _get_cache_key, CACHE_DIR
        
        # Import the cache key function
        def _get_cache_key(geoids, years, filters):
            import json
            import hashlib
            params_str = json.dumps({
                'geoids': sorted(geoids),
                'years': sorted(years),
                'filters': filters or {}
            }, sort_keys=True)
            return hashlib.md5(params_str.encode()).hexdigest()
        
        # Check if cache should be bypassed (from wizard_data)
        bypass_cache = wizard_data.get('bypass_cache', False) or wizard_data.get('filters', {}).get('bypass_cache', False)
        
        cache_key = _get_cache_key(validated_geoids, validated_years, filters)
        cache_file = CACHE_DIR / f"{cache_key}_hmda_raw.pkl"
        
        all_results = None
        if not bypass_cache and cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    all_results = pickle.load(f)
                logger.info(f"[DEBUG] Loaded cached HMDA raw data: {len(all_results)} rows")
                if len(all_results) > 0:
                    total_loans = sum(r.get('total_originations', 0) for r in all_results)
                    logger.info(f"[DEBUG] Cached total loans: {total_loans:,}")
                    if total_loans == 0:
                        logger.warning(f"[DEBUG] Cached data has 0 loans! Clearing cache and re-querying...")
                        cache_file.unlink()
                        all_results = None
            except Exception as e:
                logger.warning(f"Error loading cache: {e}")
                all_results = None
        elif bypass_cache:
            logger.info(f"[DEBUG] Cache bypass requested - will query fresh data from BigQuery")
        
        if all_results is None:
            # Cache miss - query BigQuery
            if progress_tracker:
                progress_tracker.update_progress('querying_data', 30, 'Querying HMDA mortgage data from BigQuery...')
            
            # Query HMDA data using LendSight's proven SQL template
            # We'll query each county separately and combine results (like LendSight does)
            from justdata.apps.lendsight.core import load_sql_template
            from justdata.apps.dataexplorer.data_utils import get_county_names_from_geoids, execute_mortgage_query_with_filters
            from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
            from justdata.apps.lendsight.data_utils import find_exact_county_match, escape_sql_string
            from justdata.shared.utils.unified_env import get_unified_config
            
            sql_template = load_sql_template()
            
            # Convert GEOIDs to county names for LendSight's query function
            county_names_list = get_county_names_from_geoids(validated_geoids)
            if not county_names_list:
                return {
                    'success': False,
                    'error': 'Could not find county names for the selected GEOIDs.'
                }
            
            # Save for metadata
            county_names_list_for_metadata = county_names_list.copy()
            
            # Convert loan purpose from wizard format to LendSight format
            # Use loan_purpose from query_filters (already converted from wizard format)
            # If not present, default to all purposes
            loan_purpose = filters.get('loan_purpose', ['purchase', 'refinance', 'equity'])
            
            # Get action_taken filter from wizard
            action_taken_filter = filters.get('action_taken', ['1'])  # Default to originations
            
            # Query each county/year combination
            all_results = []
            total_queries = len(county_names_list) * len(validated_years)
            query_index = 0
            
            config = get_unified_config(load_env=False, verbose=False)
            PROJECT_ID = config.get('GCP_PROJECT_ID')
            client = get_bigquery_client(PROJECT_ID)
            
            for county_name in county_names_list:
                for year in validated_years:
                    try:
                        if progress_tracker:
                            progress_pct = 30 + int((query_index / total_queries) * 20)
                            progress_tracker.update_progress('querying_data', progress_pct, 
                                f'Querying {county_name} ({year})...')
                        
                        logger.info(f"[DEBUG] Querying: county={county_name}, year={year}, loan_purpose={loan_purpose}, action_taken={action_taken_filter}")
                        
                        # Use custom query function that applies all filters
                        results = execute_mortgage_query_with_filters(
                            sql_template, county_name, year, loan_purpose, 
                            action_taken=action_taken_filter,
                            occupancy=filters.get('occupancy'),
                            total_units=filters.get('total_units'),
                            construction=filters.get('construction'),
                            loan_type=filters.get('loan_type'),
                            exclude_reverse_mortgages=filters.get('exclude_reverse_mortgages', True)
                        )
                        
                        logger.info(f"[DEBUG] Query returned {len(results)} rows for {county_name} {year}")
                        if len(results) > 0:
                            logger.info(f"[DEBUG] Sample result columns: {list(results[0].keys()) if results else 'N/A'}")
                            if 'total_originations' in results[0]:
                                total = sum(r.get('total_originations', 0) for r in results)
                                logger.info(f"[DEBUG] Total originations in this batch: {total:,}")
                        all_results.extend(results)
                        # Memory optimization: Clear results after extending to free memory immediately
                        results = None
                        query_index += 1
                        
                        # Periodic memory cleanup for large analyses
                        if query_index % 5 == 0:
                            import gc
                            gc.collect()
                        
                    except Exception as e:
                        logger.error(f"Error querying {county_name} {year}: {e}", exc_info=True)
                        query_index += 1
                        continue
            
            if not all_results:
                return {
                    'success': False,
                    'error': 'No HMDA data found for the selected counties and years.'
                }
            
            # Debug: Check raw query results structure (before DataFrame conversion)
            logger.info(f"[DEBUG] ========== HMDA QUERY RESULTS ==========")
            logger.info(f"[DEBUG] Total query results: {len(all_results)} rows")
            if len(all_results) > 0:
                logger.info(f"[DEBUG] Sample result keys: {list(all_results[0].keys())}")
                logger.info(f"[DEBUG] Sample result: {all_results[0]}")
                # Check for key columns in raw results
                required_cols = ['year', 'total_originations']
                missing_cols = [col for col in required_cols if col not in all_results[0].keys()]
                if missing_cols:
                    logger.warning(f"[DEBUG] Missing required columns in raw results: {missing_cols}")
                # Check for lender column
                lender_cols = [col for col in all_results[0].keys() if 'lender' in col.lower() or 'name' in col.lower()]
                logger.info(f"[DEBUG] Potential lender columns: {lender_cols}")
                
                # Check for race/ethnicity columns
                race_cols = [col for col in all_results[0].keys() if any(term in col.lower() for term in ['hispanic', 'black', 'white', 'asian', 'race'])]
                logger.info(f"[DEBUG] Race/ethnicity columns found: {race_cols}")
                
                # Check actual data values in raw results
                total_loans = sum(r.get('total_originations', 0) for r in all_results)
                logger.info(f"[DEBUG] Total loans in raw results: {total_loans:,}")
                
                # Check race/ethnicity totals
                for col in ['hispanic_originations', 'black_originations', 'white_originations', 'asian_originations']:
                    total = sum(r.get(col, 0) for r in all_results)
                    logger.info(f"[DEBUG] {col} total: {total:,}")
                
                # Check lender_name
                if 'lender_name' in all_results[0].keys():
                    non_null_lenders = sum(1 for r in all_results if r.get('lender_name'))
                    unique_lenders = len(set(r.get('lender_name') for r in all_results if r.get('lender_name')))
                    logger.info(f"[DEBUG] lender_name: {non_null_lenders} non-null values, {unique_lenders} unique lenders")
                    if unique_lenders > 0:
                        sample_lenders = list(set(r.get('lender_name') for r in all_results if r.get('lender_name')))[:5]
                        logger.info(f"[DEBUG] Sample lenders: {sample_lenders}")
                else:
                    logger.warning(f"[DEBUG] lender_name column NOT FOUND in raw results!")
            else:
                logger.error(f"[DEBUG] No query results returned! No data from queries.")
                logger.error(f"[DEBUG] Counties queried: {county_names_list}")
                logger.error(f"[DEBUG] Years queried: {validated_years}")
                logger.error(f"[DEBUG] Loan purposes: {loan_purpose}")
            logger.info(f"[DEBUG] =========================================")
            
            # Save raw results to cache (as list of dicts, not DataFrame)
            # We'll convert to DataFrame in the report builder, just like LendSight does
            import pickle
            from pathlib import Path
            from justdata.apps.dataexplorer.cache_utils import CACHE_DIR
            
            def _get_cache_key(geoids, years, filters):
                import json
                import hashlib
                params_str = json.dumps({
                    'geoids': sorted(geoids),
                    'years': sorted(years),
                    'filters': filters or {}
                }, sort_keys=True)
                return hashlib.md5(params_str.encode()).hexdigest()
            
            cache_key = _get_cache_key(validated_geoids, validated_years, filters)
            cache_file = CACHE_DIR / f"{cache_key}_hmda_raw.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(all_results, f)
            logger.info(f"Cached HMDA raw data: {len(all_results)} rows")
        else:
            if progress_tracker:
                progress_tracker.update_progress('querying_data', 30, 'Loaded HMDA data from cache...')
        
        if progress_tracker:
            progress_tracker.update_progress('processing_data', 50, 'Processing loan data...')
        
        # Build report data
        if progress_tracker:
            progress_tracker.update_progress('building_report', 65, 'Building report tables...')
        
        from justdata.apps.dataexplorer.area_report_builder import build_area_report
        import pandas as pd
        import numpy as np
        
        # Pass raw results (list of dicts) to report builder, just like LendSight does
        # The report builder will convert to DataFrame internally
        # Note: Column names use "_originations" suffix but represent the selected action_taken type
        action_taken_filter = filters.get('action_taken', ['1'])  # Default to originations
        report_data = build_area_report(
            hmda_data=all_results,  # This is a list of dicts, not a DataFrame
            geoids=validated_geoids,
            years=validated_years,
            census_data=census_data,
            historical_census_data=historical_census_data,
            progress_tracker=progress_tracker,
            action_taken=action_taken_filter  # Pass action_taken to track data type
        )
        
        # Convert all DataFrames to JSON-serializable format for template rendering
        def convert_dataframes_to_dicts(obj):
            """Recursively convert DataFrames and pandas types to JSON-serializable format."""
            if isinstance(obj, pd.DataFrame):
                return obj.to_dict('records') if not obj.empty else []
            elif isinstance(obj, pd.Series):
                return obj.to_dict()
            elif isinstance(obj, dict):
                return {k: convert_dataframes_to_dicts(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_dataframes_to_dicts(item) for item in obj]
            elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            else:
                return obj
        
        # Debug: Check if section4 is present BEFORE conversion
        logger.info(f"[DEBUG] report_data keys BEFORE conversion: {list(report_data.keys())}")
        if 'section4' in report_data:
            logger.info(f"[DEBUG] Section4 present BEFORE conversion: {list(report_data['section4'].keys())}")
            if 'hhi_by_year_purpose' in report_data['section4']:
                logger.info(f"[DEBUG] HHI data present BEFORE conversion: {len(report_data['section4']['hhi_by_year_purpose'])} years")
        
        # Convert report_data to ensure all DataFrames are converted
        try:
            report_data = convert_dataframes_to_dicts(report_data)
            logger.info(f"[DEBUG] Converted report_data DataFrames to dicts for JSON serialization")
            # Debug: Check if section4 is present after conversion
            logger.info(f"[DEBUG] report_data keys AFTER conversion: {list(report_data.keys())}")
            if 'section4' in report_data:
                logger.info(f"[DEBUG] Section4 present after conversion: {list(report_data['section4'].keys())}")
                if 'hhi_by_year_purpose' in report_data['section4']:
                    logger.info(f"[DEBUG] HHI data present after conversion: {len(report_data['section4']['hhi_by_year_purpose'])} years")
            else:
                logger.warning(f"[DEBUG] Section4 NOT present in report_data after conversion!")
        except Exception as e:
            logger.error(f"Error converting DataFrames to dicts: {e}", exc_info=True)
            # Re-raise the exception so we know about it
            raise
        
        if progress_tracker:
            progress_tracker.update_progress('finalizing', 95, 'Finalizing report...')
        
        # Prepare metadata
        geography = wizard_data.get('geography', {})
        
        # Calculate minority population percentage from census data
        minority_population_pct = None
        if census_data:
            # Aggregate across all counties
            total_pop = 0
            white_pop = 0
            for geoid in validated_geoids:
                county_data = census_data.get(geoid, {})
                if county_data:
                    # Get most recent time period (ACS)
                    time_periods = county_data.get('time_periods', {})
                    acs_data = time_periods.get('acs', {})
                    if acs_data:
                        pop = acs_data.get('total_population', 0)
                        white_pct = acs_data.get('white_percentage', 0)
                        total_pop += pop
                        white_pop += (pop * white_pct / 100) if white_pct else 0
            
            if total_pop > 0:
                minority_pop = total_pop - white_pop
                minority_population_pct = round((minority_pop / total_pop) * 100, 1)
        
        # Get AMFI from HMDA query results (if available)
        # AMFI is stored in ffiec_msa_md_median_family_income column in HMDA data
        amfi = None
        if all_results:
            # Extract AMFI from the first record that has it
            for result in all_results:
                if 'ffiec_msa_md_median_family_income' in result and result['ffiec_msa_md_median_family_income']:
                    try:
                        amfi_value = result['ffiec_msa_md_median_family_income']
                        # Convert to int if it's a string or float
                        if isinstance(amfi_value, str):
                            amfi = int(float(amfi_value))
                        elif isinstance(amfi_value, (int, float)):
                            amfi = int(amfi_value)
                        if amfi and amfi > 0:
                            break
                    except (ValueError, TypeError):
                        continue
        
        # Store original wizard filters in metadata (not the converted query_filters)
        # This ensures the header can display user-friendly filter descriptions
        original_filters = wizard_data.get('filters', {})
        
        metadata = {
            'counties': validated_geoids,
            'county_names': county_names_list_for_metadata if 'county_names_list_for_metadata' in locals() else [],
            'years': validated_years,
            'cbsa': geography.get('cbsa'),
            'cbsa_name': geography.get('cbsa_name'),
            'filters': original_filters,  # Use original wizard format, not query format
            'generated_at': datetime.now().isoformat(),
            'job_id': job_id,
            'minority_population_pct': minority_population_pct,
            'amfi': amfi
        }
        
        if progress_tracker:
            progress_tracker.complete(success=True)

        return {
            'success': True,
            'report_data': report_data,
            'metadata': metadata,
            'tables': report_data,  # For compatibility with report template
            'census_data': census_data,
            'historical_census_data': historical_census_data
        }
        
    except Exception as e:
        logger.error(f"Error in area analysis: {e}", exc_info=True)
        if progress_tracker:
            progress_tracker.complete(success=False, error=str(e))
        return {
            'success': False,
            'error': f'An error occurred during analysis: {str(e)}'
        }

