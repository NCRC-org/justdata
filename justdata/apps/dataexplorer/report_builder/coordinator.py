"""Coordinator that assembles area analysis reports.

The build_area_report orchestrator contains inline shared state (e.g.,
fixed_quartile_shares used across multiple sections) and runs the table
builders from sections/. It is intentionally kept monolithic rather
than further refactored — this PR only splits the file, not the function.
"""
import gc
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from justdata.apps.dataexplorer.report_builder.queries import fetch_acs_housing_data
from justdata.apps.dataexplorer.report_builder.sections.housing_costs import (
    create_housing_costs_table,
)
from justdata.apps.dataexplorer.report_builder.sections.housing_units import (
    create_housing_units_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_borrower_income import (
    create_lender_borrower_income_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_neighborhood_demographics import (
    create_lender_neighborhood_demographics_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_neighborhood_income import (
    create_lender_neighborhood_income_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_race_ethnicity import (
    create_lender_race_ethnicity_table,
)
from justdata.apps.dataexplorer.report_builder.sections.loan_costs import (
    create_lender_loan_costs_table,
    create_loan_costs_table,
)
from justdata.apps.dataexplorer.report_builder.sections.owner_occupancy import (
    create_owner_occupancy_table,
)
from justdata.apps.dataexplorer.shared.filters import filter_df_by_loan_purpose

# Import LendSight's proven table building functions
from justdata.apps.lendsight.report_builder import (
    create_demographic_overview_table,
    create_income_borrowers_table,
    create_income_tracts_table,
    create_minority_tracts_table,
    calculate_mortgage_hhi_for_year,
)
from justdata.apps.lendsight.hud_processor import get_hud_data_for_counties

logger = logging.getLogger(__name__)


def build_area_report(
    hmda_data: List[Dict[str, Any]],  # Changed: Now expects list of dicts, just like LendSight
    geoids: List[str],
    years: List[int],
    census_data: Dict = None,
    historical_census_data: Dict = None,
    progress_tracker=None,
    action_taken: List[str] = None  # Track whether this is originations or applications
) -> Dict[str, Any]:
    """
    Build area analysis report data structure.
    
    Uses the same structure as LendSight's build_mortgage_report:
    - Takes raw_data (list of dicts from BigQuery) as input
    - Converts to DataFrame internally
    - Uses exact same column names and structure as LendSight
    
    Note: Column names use "_originations" suffix for compatibility with LendSight functions,
    but when action_taken includes applications (not just '1'), these columns actually
    represent applications, not just originations. The data is correct regardless of the label.
    
    Report Structure:
    - Section 1: Population Demographics (shared utility)
    - Section 2 (most recent 5 years): 
      - Table 1: Loans by Race and Ethnicity
      - Table 2: Loans by Borrower Income
      - Table 3: Loans by Neighborhood Income
      - Table 4: Loans by Neighborhood Demographics
    - Section 3 (top lenders - show top 10, expandable):
      - Table 1: Loans by Race and Ethnicity
      - Table 2: Loans by Borrower Income
      - Table 3: Loans by Neighborhood Income
      - Table 4: Loans by Neighborhood Demographics
    - Section 4:
      - Table 1: HHI Market Concentration
    
    Args:
        hmda_data: List of dictionaries from BigQuery results (same as LendSight raw_data)
        geoids: List of county GEOIDs
        years: List of years
        census_data: Optional census demographics data
        historical_census_data: Optional historical census data for chart
        progress_tracker: Optional progress tracker
        action_taken: Optional list of action_taken codes to track data type
        
    Returns:
        Dictionary with report data organized by sections
    """
    if not hmda_data:
        raise ValueError("No data provided for report building")
    
    # Initialize report_data dictionary
    report_data = {}
    
    # Track whether this is applications or originations for metadata
    is_applications = action_taken and set(action_taken) != {'1'}
    report_data['data_type'] = 'applications' if is_applications else 'originations'
    
    # Convert to DataFrame - exactly like LendSight does
    # Memory optimization: Use more efficient dtypes where possible
    df = pd.DataFrame(hmda_data)
    
    # Clean and prepare data - use LendSight's cleaning function
    from justdata.apps.lendsight.report_builder import clean_mortgage_data
    df = clean_mortgage_data(df)
    
    # Split geoid5 into state_fips and county_fips for tract population data functions
    # geoid5 is a 5-digit code: first 2 digits = state FIPS, last 3 digits = county FIPS
    if 'geoid5' in df.columns and ('state_fips' not in df.columns or 'county_fips' not in df.columns):
        df['state_fips'] = df['geoid5'].astype(str).str[:2].astype(int)
        df['county_fips'] = df['geoid5'].astype(str).str[2:].astype(int)
        logger.info(f"[DEBUG] Split geoid5 into state_fips and county_fips")
    
    # Memory optimization: Delete original data after DataFrame creation
    del hmda_data
    import gc
    gc.collect()
    
    # Ensure required columns exist (same as LendSight)
    required_columns = ['lei', 'year', 'county_code', 'county_state', 'total_originations', 'lmict_originations', 'mmct_originations']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.warning(f"Missing required columns: {missing_columns}")
        # Don't raise error, just log warning - some columns might be optional
    
    logger.info(f"[DEBUG] DataFrame created. Shape: {df.shape}, Columns: {list(df.columns)}")
    if not df.empty:
        logger.info(f"[DEBUG] DataFrame sample: {df.head(1).to_dict('records')}")
        logger.info(f"[DEBUG] Years in DataFrame: {sorted(df['year'].unique()) if 'year' in df.columns else 'NO YEAR COLUMN'}")
        
        # Check for required race/ethnicity columns (same names as LendSight)
        race_columns = ['hispanic_originations', 'black_originations', 'white_originations', 
                       'asian_originations', 'native_american_originations', 'hopi_originations',
                       'multi_racial_originations']
        missing_race_cols = [col for col in race_columns if col not in df.columns]
        if missing_race_cols:
            logger.warning(f"[DEBUG] Missing race/ethnicity columns: {missing_race_cols}")
        else:
            logger.info(f"[DEBUG] All race/ethnicity columns present")
        
        # Check for lender column (same name as LendSight)
        lender_cols = [col for col in df.columns if 'lender' in col.lower() or 'respondent' in col.lower() or 'name' in col.lower()]
        logger.info(f"[DEBUG] Potential lender columns: {lender_cols}")
        if 'lender_name' not in df.columns:
            logger.warning(f"[DEBUG] 'lender_name' column NOT found. Available columns with 'name': {[col for col in df.columns if 'name' in col.lower()]}")
        
        # Check for required income columns
        income_cols = ['lmib_originations', 'low_income_borrower_originations', 'moderate_income_borrower_originations',
                      'middle_income_borrower_originations', 'upper_income_borrower_originations']
        missing_income_cols = [col for col in income_cols if col not in df.columns]
        if missing_income_cols:
            logger.warning(f"[DEBUG] Missing income columns: {missing_income_cols}")
        
        # Check for tract columns
        tract_cols = [col for col in df.columns if 'tract' in col.lower() or 'lmict' in col.lower() or 'mmct' in col.lower()]
        logger.info(f"[DEBUG] Tract-related columns: {tract_cols}")
    else:
        logger.warning(f"[DEBUG] DataFrame is EMPTY!")
    
    # Section 1: Population Demographics
    # This will be handled by the shared population demographics utility
    report_data['population_demographics'] = {
        'census_data': census_data,
        'historical_census_data': historical_census_data,
        'geoids': geoids
    }
    
    # Section 1: Table 2 - Loans by Loan Purpose Over Time
    # Aggregate loans by year and loan purpose
    if 'loan_purpose' in df.columns and not df.empty:
        loan_purpose_data = []
        for year in sorted(years):
            year_df = df[df['year'] == year]
            if not year_df.empty:
                # Map loan purpose codes to readable names
                # HMDA codes: 1=purchase, 31/32=refinance, 2/4=home equity
                purpose_map = {
                    '1': 'Home Purchase',
                    '31': 'Refinance',  # HMDA code 31 is refinance
                    '32': 'Refinance',  # HMDA code 32 is cash-out refinance
                    'purchase': 'Home Purchase',
                    'refinance': 'Refinance',
                    '2': 'Home Equity',  # HMDA code 2 is home equity
                    '4': 'Home Equity',  # HMDA code 4 is also home equity
                    'equity': 'Home Equity',
                    '3': 'Home Improvement',  # HMDA code 3 is home improvement
                    '33': 'Home Improvement',
                    '34': 'Home Improvement',
                    '5': 'Other',
                    '35': 'Other'
                }
                
                # Group by loan purpose
                purpose_totals = {}
                for purpose_code in year_df['loan_purpose'].unique():
                    purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
                    total = int(purpose_df['total_originations'].sum())
                    purpose_name = purpose_map.get(str(purpose_code), 'Other')
                    if purpose_name in purpose_totals:
                        purpose_totals[purpose_name] += total
                    else:
                        purpose_totals[purpose_name] = total
                
                # Only include the three main purposes
                loan_purpose_data.append({
                    'year': year,
                    'Home Purchase': purpose_totals.get('Home Purchase', 0),
                    'Refinance': purpose_totals.get('Refinance', 0),
                    'Home Equity': purpose_totals.get('Home Equity', 0)
                })
        
        report_data['loan_purpose_over_time'] = loan_purpose_data
    else:
        report_data['loan_purpose_over_time'] = []
    
    # Section 1: Table 3 - Loan Amounts by Loan Purpose Over Time
    # Aggregate loan amounts by year and loan purpose
    if 'loan_purpose' in df.columns and 'total_loan_amount' in df.columns and not df.empty:
        loan_amount_purpose_data = []
        for year in sorted(years):
            year_df = df[df['year'] == year]
            if not year_df.empty:
                # Map loan purpose codes to readable names (same as above)
                purpose_map = {
                    '1': 'Home Purchase',
                    '31': 'Refinance',
                    '32': 'Refinance',
                    'purchase': 'Home Purchase',
                    'refinance': 'Refinance',
                    '2': 'Home Equity',
                    '4': 'Home Equity',
                    'equity': 'Home Equity',
                    '3': 'Home Improvement',
                    '33': 'Home Improvement',
                    '34': 'Home Improvement',
                    '5': 'Other',
                    '35': 'Other'
                }
                
                # Group by loan purpose and sum loan amounts
                purpose_amounts = {}
                for purpose_code in year_df['loan_purpose'].unique():
                    purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
                    # Sum total_loan_amount (convert to int if needed)
                    total_amount = purpose_df['total_loan_amount'].sum()
                    if pd.notna(total_amount):
                        total_amount = int(total_amount)
                    else:
                        total_amount = 0
                    purpose_name = purpose_map.get(str(purpose_code), 'Other')
                    if purpose_name in purpose_amounts:
                        purpose_amounts[purpose_name] += total_amount
                    else:
                        purpose_amounts[purpose_name] = total_amount
                
                # Only include the three main purposes
                loan_amount_purpose_data.append({
                    'year': year,
                    'Home Purchase': purpose_amounts.get('Home Purchase', 0),
                    'Refinance': purpose_amounts.get('Refinance', 0),
                    'Home Equity': purpose_amounts.get('Home Equity', 0)
                })
        
        report_data['loan_amount_purpose_over_time'] = loan_amount_purpose_data
    else:
        report_data['loan_amount_purpose_over_time'] = []
    
    # Section 1: Tables 4-6 - Housing Data
    if progress_tracker:
        progress_tracker.update_progress('building_report', 65, 'Fetching housing data...')
    
    try:
        logger.info(f"[DEBUG] Starting housing data fetch for {len(geoids)} geoids: {geoids[:3]}...")
        housing_data = fetch_acs_housing_data(geoids)
        logger.info(f"[DEBUG] Fetched housing data for {len(housing_data)} counties")
        logger.info(f"[DEBUG] Housing data keys: {list(housing_data.keys())}")
        if housing_data:
            sample_geoid = list(housing_data.keys())[0]
            sample_data = housing_data[sample_geoid]
            logger.info(f"[DEBUG] Sample housing data for {sample_geoid}: time_periods keys = {list(sample_data.get('time_periods', {}).keys())}")
            for period_key, period_data in sample_data.get('time_periods', {}).items():
                logger.info(f"[DEBUG]   {period_key}: has {len(period_data)} fields")
        else:
            logger.warning(f"[DEBUG] No housing data returned from fetch_acs_housing_data!")
        
        # Table 4: Housing Costs
        logger.info(f"[DEBUG] Creating housing costs table with {len(housing_data)} counties...")
        report_data['housing_costs'] = create_housing_costs_table(housing_data, geoids)
        logger.info(f"[DEBUG] Housing costs table: {len(report_data['housing_costs'])} periods")
        if report_data['housing_costs']:
            logger.info(f"[DEBUG] Housing costs sample: {report_data['housing_costs'][0]}")
        
        # Table 5: Owner Occupancy
        logger.info(f"[DEBUG] Creating owner occupancy table...")
        report_data['owner_occupancy'] = create_owner_occupancy_table(
            housing_data, geoids, historical_census_data
        )
        logger.info(f"[DEBUG] Owner occupancy table: {len(report_data['owner_occupancy'])} periods")
        
        # Table 6: Housing Units
        logger.info(f"[DEBUG] Creating housing units table...")
        report_data['housing_units'] = create_housing_units_table(housing_data, geoids)
        logger.info(f"[DEBUG] Housing units table: {len(report_data['housing_units'])} periods")
        
        logger.info(f"Built housing tables: costs={len(report_data['housing_costs'])}, "
                   f"occupancy={len(report_data['owner_occupancy'])}, "
                   f"units={len(report_data['housing_units'])}")
    except Exception as e:
        logger.error(f"Error fetching/building housing tables: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        report_data['housing_costs'] = []
        report_data['owner_occupancy'] = []
        report_data['housing_units'] = []
    
    if progress_tracker:
        progress_tracker.update_progress('building_report', 70, 'Building Section 2 tables...')
    
    # Get HUD data for benchmark figures (check cache first)
    from justdata.apps.dataexplorer.cache_utils import load_hud_data, save_hud_data

    logger.info(f"[HUD Debug] Loading HUD data for geoids: {geoids}")
    hud_data = load_hud_data(geoids)

    # Helper to check if HUD data is valid (has non-zero total_persons)
    def is_valid_hud_data(data):
        if not data:
            return False
        total_persons = sum(d.get('total_persons', 0) for d in data.values())
        return total_persons > 0

    if hud_data is None or not is_valid_hud_data(hud_data):
        # Cache miss or invalid cached data - fetch from HUD processor
        cache_status = "cache miss" if hud_data is None else "invalid cache (all zeros)"
        try:
            # get_hud_data_for_counties expects a list of GEOID5 strings
            logger.info(f"[HUD Debug] {cache_status}, fetching from HUD processor")
            hud_data = get_hud_data_for_counties(geoids)
            if hud_data:
                logger.info(f"[HUD Debug] HUD data loaded for {len(hud_data)} counties")
                # Log sample data for first county
                if hud_data:
                    sample_geoid = list(hud_data.keys())[0]
                    sample_data = hud_data[sample_geoid]
                    logger.info(f"[HUD Debug] Sample HUD data for {sample_geoid}: low_mod_pct={sample_data.get('low_mod_income_pct', 'N/A')}, total_persons={sample_data.get('total_persons', 'N/A')}")

                # Calculate total persons to verify data is valid
                total_persons_check = sum(d.get('total_persons', 0) for d in hud_data.values())
                logger.info(f"[HUD Debug] Total persons across all counties: {total_persons_check:,}")

                # Only cache if data is valid
                if total_persons_check > 0:
                    save_hud_data(geoids, hud_data)
                    logger.info("[HUD Debug] Cached valid HUD data")
                else:
                    logger.warning("[HUD Debug] HUD data has zero total_persons - NOT caching (HUD file may be missing)")
        except Exception as e:
            logger.error(f"[HUD Debug] Error fetching HUD data: {e}", exc_info=True)
            hud_data = {}
    else:
        total_persons_cached = sum(d.get('total_persons', 0) for d in hud_data.values())
        logger.info(f"[HUD Debug] Loaded HUD data from cache for {len(hud_data)} counties (total_persons: {total_persons_cached:,})")
    
    # Section 2: Most recent 5 years - aggregate tables
    # Get most recent 5 years (already filtered in years list)
    recent_years = sorted(years)[-5:] if len(years) > 5 else years
    
    # Debug: Check DataFrame structure
    logger.info(f"[DEBUG] Building Section 2 tables")
    logger.info(f"[DEBUG] DataFrame shape: {df.shape}")
    logger.info(f"[DEBUG] DataFrame columns: {list(df.columns)}")
    logger.info(f"[DEBUG] Recent years: {recent_years}")
    recent_years_df = df[df['year'].isin(recent_years)]
    logger.info(f"[DEBUG] Recent years DataFrame shape: {recent_years_df.shape}")
    
    # Calculate quartile_shares once using full dataset (all loans) for Table 4
    # This ensures Population Share doesn't change when switching loan purpose tabs
    from justdata.apps.lendsight.report_builder import (
        calculate_minority_quartiles, 
        classify_tract_minority_quartile,
        get_tract_population_data_for_counties
    )
    
    fixed_quartile_shares = {}
    fixed_tract_income_shares = {}  # For Table 3
    if not recent_years_df.empty and 'tract_minority_population_percent' in recent_years_df.columns:
        # Calculate quartiles from full dataset
        quartiles = calculate_minority_quartiles(recent_years_df)
        recent_years_df_copy = recent_years_df.copy()
        recent_years_df_copy['minority_quartile'] = recent_years_df_copy['tract_minority_population_percent'].apply(
            lambda x: classify_tract_minority_quartile(x, quartiles)
        )
        
        # Get tract population data
        tract_pop_data = get_tract_population_data_for_counties(recent_years_df_copy)
        
        # Calculate population shares from full dataset
        unique_tracts = recent_years_df_copy[['tract_code', 'minority_quartile', 'tract_minority_population_percent']].drop_duplicates()
        total_tracts = len(unique_tracts)
        
        if tract_pop_data and len(tract_pop_data) > 0:
            total_population = 0
            mmct_population = 0
            quartile_populations = {'low': 0, 'moderate': 0, 'middle': 0, 'high': 0}
            
            if 'state_fips' in recent_years_df_copy.columns and 'county_fips' in recent_years_df_copy.columns:
                tract_to_fips = recent_years_df_copy[['tract_code', 'state_fips', 'county_fips']].drop_duplicates()
                tract_fips_map = {}
                for _, row in tract_to_fips.iterrows():
                    tract_code_short = str(row['tract_code']).zfill(6)
                    state_fips = str(int(row['state_fips'])).zfill(2)
                    county_fips = str(int(row['county_fips'])).zfill(3)
                    full_tract_code = f"{state_fips}{county_fips}{tract_code_short}"
                    tract_fips_map[tract_code_short] = full_tract_code
                
                for _, tract_row in unique_tracts.iterrows():
                    tract_code_short = str(tract_row['tract_code']).zfill(6)
                    tract_minority_pct = tract_row['tract_minority_population_percent']
                    quartile = tract_row['minority_quartile']
                    
                    full_tract_code = tract_fips_map.get(tract_code_short)
                    if full_tract_code and full_tract_code in tract_pop_data:
                        pop = tract_pop_data[full_tract_code]['total_population']
                        total_population += pop
                        
                        if tract_minority_pct >= 50:
                            mmct_population += pop
                        
                        if quartile in quartile_populations:
                            quartile_populations[quartile] += pop
            
            if total_population > 0:
                fixed_quartile_shares['mmct'] = (mmct_population / total_population) * 100
                fixed_quartile_shares['low'] = (quartile_populations['low'] / total_population) * 100
                fixed_quartile_shares['moderate'] = (quartile_populations['moderate'] / total_population) * 100
                fixed_quartile_shares['middle'] = (quartile_populations['middle'] / total_population) * 100
                fixed_quartile_shares['high'] = (quartile_populations['high'] / total_population) * 100
            elif total_tracts > 0:
                # Fallback to tract distribution
                mmct_tracts = unique_tracts[unique_tracts['tract_minority_population_percent'] >= 50]
                fixed_quartile_shares['mmct'] = (len(mmct_tracts) / total_tracts * 100) if total_tracts > 0 else 0
                fixed_quartile_shares['low'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'low']) / total_tracts * 100
                fixed_quartile_shares['moderate'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'moderate']) / total_tracts * 100
                fixed_quartile_shares['middle'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'middle']) / total_tracts * 100
                fixed_quartile_shares['high'] = len(unique_tracts[unique_tracts['minority_quartile'] == 'high']) / total_tracts * 100
        
        logger.info(f"[DEBUG] Calculated fixed quartile shares from full dataset: {fixed_quartile_shares}")
    
    # Calculate tract income shares once using full dataset (all loans) for Table 3
    # This ensures Population Share doesn't change when switching loan purpose tabs
    if not recent_years_df.empty and 'tract_to_msa_income_percentage' in recent_years_df.columns:
        # Get unique tracts with their income percentages
        unique_tracts_income = recent_years_df[['tract_code', 'tract_to_msa_income_percentage']].drop_duplicates()
        unique_tracts_income_clean = unique_tracts_income.dropna(subset=['tract_to_msa_income_percentage'])
        total_valid_tracts = len(unique_tracts_income_clean)
        
        if total_valid_tracts > 0:
            # Classify tracts by income level
            low_tracts = len(unique_tracts_income_clean[unique_tracts_income_clean['tract_to_msa_income_percentage'] <= 50])
            moderate_tracts = len(unique_tracts_income_clean[
                (unique_tracts_income_clean['tract_to_msa_income_percentage'] > 50) &
                (unique_tracts_income_clean['tract_to_msa_income_percentage'] <= 80)
            ])
            middle_tracts = len(unique_tracts_income_clean[
                (unique_tracts_income_clean['tract_to_msa_income_percentage'] > 80) &
                (unique_tracts_income_clean['tract_to_msa_income_percentage'] <= 120)
            ])
            upper_tracts = len(unique_tracts_income_clean[unique_tracts_income_clean['tract_to_msa_income_percentage'] > 120])
            
            # Calculate shares as percentage of total tracts
            fixed_tract_income_shares['low'] = (low_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
            fixed_tract_income_shares['moderate'] = (moderate_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
            fixed_tract_income_shares['lmict'] = fixed_tract_income_shares['low'] + fixed_tract_income_shares['moderate']
            fixed_tract_income_shares['middle'] = (middle_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
            fixed_tract_income_shares['upper'] = (upper_tracts / total_valid_tracts * 100) if total_valid_tracts > 0 else 0
            
            logger.info(f"[DEBUG] Calculated fixed tract income shares from full dataset: {fixed_tract_income_shares}")
    
    # Generate tables for each loan purpose: all, purchase, refinance, equity
    loan_purposes = ['all', 'purchase', 'refinance', 'equity']
    section2_tables = {}
    
    for purpose in loan_purposes:
        logger.info(f"[DEBUG] Building Section 2 tables for loan purpose: {purpose}")
        purpose_df = filter_df_by_loan_purpose(recent_years_df, purpose)
        
        if purpose_df.empty:
            logger.warning(f"[DEBUG] No data for loan purpose: {purpose}")
            section2_tables[purpose] = {
                'loans_by_race_ethnicity': pd.DataFrame(),
                'loans_by_borrower_income': pd.DataFrame(),
                'loans_by_neighborhood_income': pd.DataFrame(),
                'loans_by_neighborhood_demographics': pd.DataFrame()
            }
            continue
        
        # Table 1: Loans by Race and Ethnicity
        race_columns = ['hispanic_originations', 'black_originations', 'white_originations', 
                       'asian_originations', 'native_american_originations', 'hopi_originations',
                       'multi_racial_originations']
        missing_race = [col for col in race_columns if col not in purpose_df.columns]
        if missing_race:
            logger.error(f"[DEBUG] CANNOT create demographic table for {purpose} - missing columns: {missing_race}")
            loans_by_race_ethnicity = pd.DataFrame()
        else:
            # Use historical_census_data if available, otherwise fall back to census_data
            # Both formats are supported by create_demographic_overview_table
            census_data_for_table = historical_census_data if historical_census_data else census_data
            if not census_data_for_table:
                logger.warning(f"[DEBUG] No census data available for demographic table (historical_census_data: {bool(historical_census_data)}, census_data: {bool(census_data)})")
            
            loans_by_race_ethnicity = create_demographic_overview_table(
                purpose_df, 
                recent_years, 
                census_data=census_data_for_table
            )
        
        # Table 2: Loans by Borrower Income
        loans_by_borrower_income = create_income_borrowers_table(
            purpose_df,
            recent_years,
            hud_data=hud_data
        )

        # Add income ranges to borrower income table labels
        if isinstance(loans_by_borrower_income, pd.DataFrame) and not loans_by_borrower_income.empty and 'Metric' in loans_by_borrower_income.columns:
            income_range_map = {
                'Low Income Borrowers': 'Low Income Borrowers (≤50% of AMFI)',
                'Moderate Income Borrowers': 'Moderate Income Borrowers (>50% and ≤80% of AMFI)',
                'Middle Income Borrowers': 'Middle Income Borrowers (>80% and ≤120% of AMFI)',
                'Upper Income Borrowers': 'Upper Income Borrowers (>120% of AMFI)',
                'Low to Moderate Income Borrowers': 'Low to Moderate Income Borrowers (≤80% of AMFI)'
            }
            loans_by_borrower_income['Metric'] = loans_by_borrower_income['Metric'].replace(income_range_map)
        
        # Table 3: Loans by Neighborhood Income
        loans_by_neighborhood_income = create_income_tracts_table(
            purpose_df, 
            recent_years, 
            hud_data=hud_data,
            census_data=census_data
        )
        
        # Add income ranges to neighborhood income table labels
        if isinstance(loans_by_neighborhood_income, pd.DataFrame) and not loans_by_neighborhood_income.empty and 'Metric' in loans_by_neighborhood_income.columns:
            tract_income_range_map = {
                'Low Income Census Tracts': 'Low Income Census Tracts (≤50% of AMFI)',
                'Moderate Income Census Tracts': 'Moderate Income Census Tracts (>50% and ≤80% of AMFI)',
                'Middle Income Census Tracts': 'Middle Income Census Tracts (>80% and ≤120% of AMFI)',
                'Upper Income Census Tracts': 'Upper Income Census Tracts (>120% of AMFI)',
                'Low to Moderate Income Census Tracts': 'Low to Moderate Income Census Tracts (≤80% of AMFI)'
            }
            loans_by_neighborhood_income['Metric'] = loans_by_neighborhood_income['Metric'].replace(tract_income_range_map)
        
        # Override Population Share column with fixed values from full dataset
        # This ensures Population Share doesn't change when switching loan purpose tabs
        if isinstance(loans_by_neighborhood_income, pd.DataFrame) and not loans_by_neighborhood_income.empty:
            if 'Population Share (%)' in loans_by_neighborhood_income.columns and fixed_tract_income_shares:
                # Map metric names to income share keys
                for idx, row in loans_by_neighborhood_income.iterrows():
                    metric = row['Metric']
                    # Extract income category from metric label
                    if 'Low to Moderate Income' in metric or 'LMI' in metric:
                        share_key = 'lmict'
                    elif 'Low Income' in metric and 'Moderate' not in metric:
                        share_key = 'low'
                    elif 'Moderate Income' in metric:
                        share_key = 'moderate'
                    elif 'Middle Income' in metric:
                        share_key = 'middle'
                    elif 'Upper Income' in metric:
                        share_key = 'upper'
                    else:
                        share_key = None
                    
                    if share_key and share_key in fixed_tract_income_shares:
                        loans_by_neighborhood_income.at[idx, 'Population Share (%)'] = f"{fixed_tract_income_shares[share_key]:.1f}%"
        
        # Table 4: Loans by Neighborhood Demographics
        # Use historical_census_data if available, otherwise fall back to census_data
        census_data_for_minority = historical_census_data if historical_census_data else census_data
        loans_by_neighborhood_demographics = create_minority_tracts_table(
            purpose_df, 
            recent_years, 
            census_data=census_data_for_minority
        )
        
        # Override Population Share column with fixed values from full dataset
        # This ensures Population Share doesn't change when switching loan purpose tabs
        if isinstance(loans_by_neighborhood_demographics, pd.DataFrame) and not loans_by_neighborhood_demographics.empty:
            if 'Population Share (%)' in loans_by_neighborhood_demographics.columns and fixed_quartile_shares:
                logger.info(f"[DEBUG] Overriding Population Share for Table 4 with fixed values: {fixed_quartile_shares}")
                # Map metric names to quartile share keys
                # Get quartile ranges for labels (from the table itself)
                for idx, row in loans_by_neighborhood_demographics.iterrows():
                    metric = row['Metric']
                    # Extract quartile from metric label (handle various formats)
                    share_key = None
                    if 'Low Minority' in metric:
                        share_key = 'low'
                    elif 'Moderate Minority' in metric:
                        share_key = 'moderate'
                    elif 'Middle Minority' in metric:
                        share_key = 'middle'
                    elif 'High Minority' in metric:
                        share_key = 'high'
                    elif 'Majority Minority' in metric:
                        share_key = 'mmct'
                    
                    if share_key and share_key in fixed_quartile_shares:
                        old_value = loans_by_neighborhood_demographics.at[idx, 'Population Share (%)']
                        new_value = f"{fixed_quartile_shares[share_key]:.1f}%"
                        loans_by_neighborhood_demographics.at[idx, 'Population Share (%)'] = new_value
                        logger.info(f"[DEBUG] Overrode Population Share for '{metric}': {old_value} -> {new_value}")
                    else:
                        logger.warning(f"[DEBUG] Could not find share_key for metric '{metric}' or share_key '{share_key}' not in fixed_quartile_shares")
        
        # Table 5: Loan Costs (new)
        loans_by_loan_costs = create_loan_costs_table(purpose_df, recent_years)
        
        section2_tables[purpose] = {
            'loans_by_race_ethnicity': loans_by_race_ethnicity,
            'loans_by_borrower_income': loans_by_borrower_income,
            'loans_by_neighborhood_income': loans_by_neighborhood_income,
            'loans_by_neighborhood_demographics': loans_by_neighborhood_demographics,
            'loans_by_loan_costs': loans_by_loan_costs
        }
    
    report_data['section2'] = {
        'years': recent_years,
        'by_purpose': section2_tables
    }
    
    if progress_tracker:
        progress_tracker.update_progress('building_report', 80, 'Building Section 3 (top lenders)...')
    
    # Section 3: Top lenders (top 10, expandable) - by loan purpose
    # Structure: Rows = Lenders, Columns = Metrics
    # Same 4 tables as Section 2, but transposed:
    # - Table 1: Loans by Race and Ethnicity (lenders as rows, race/ethnicity % as columns)
    # - Table 2: Loans by Borrower Income (lenders as rows, Low/Mod/Middle/Upper % as columns)
    # - Table 3: Loans by Neighborhood Income (lenders as rows, Low/Mod/Middle/Upper tract % as columns)
    # - Table 4: Loans by Neighborhood Demographics (lenders as rows, Low/Mod/Middle/High minority % as columns)
    
    # Generate tables for each loan purpose (top lenders may differ per purpose)
    logger.info(f"[DEBUG] Building Section 3 tables")
    latest_year = max(years)
    latest_year_df = df[df['year'] == latest_year].copy()
    
    # Check if lender_name column exists
    lender_col = None
    if 'lender_name' in latest_year_df.columns:
        lender_col = 'lender_name'
    else:
        for col in ['lender', 'name', 'respondent_name', 'respondent_name_clean']:
            if col in latest_year_df.columns:
                lender_col = col
                break
    
    if not lender_col:
        logger.error(f"[DEBUG] No lender column found. Cannot build Section 3 tables.")
        section3_tables = {}
        for purpose in loan_purposes:
            section3_tables[purpose] = {
                'top_lender_names': [],
                'loans_by_race_ethnicity': pd.DataFrame(),
                'loans_by_borrower_income': pd.DataFrame(),
                'loans_by_neighborhood_income': pd.DataFrame(),
                'loans_by_neighborhood_demographics': pd.DataFrame()
            }
    else:
        section3_tables = {}
        
        for purpose in loan_purposes:
            logger.info(f"[DEBUG] Building Section 3 tables for loan purpose: {purpose}")
            
            # Filter latest year data by loan purpose to get top lenders for this purpose
            purpose_latest_df = filter_df_by_loan_purpose(latest_year_df, purpose)
            
            if purpose_latest_df.empty or purpose_latest_df[lender_col].notna().sum() == 0:
                logger.warning(f"[DEBUG] No lender data for loan purpose: {purpose}")
                section3_tables[purpose] = {
                    'top_lender_names': [],
                    'loans_by_race_ethnicity': pd.DataFrame(),
                    'loans_by_borrower_income': pd.DataFrame(),
                    'loans_by_neighborhood_income': pd.DataFrame(),
                    'loans_by_neighborhood_demographics': pd.DataFrame(),
                    'loans_by_loan_costs': {}
                }
                continue
            
            # Get top 10 lenders for this loan purpose
            purpose_latest_df_clean = purpose_latest_df[purpose_latest_df[lender_col].notna()].copy()
            lender_totals = purpose_latest_df_clean.groupby(lender_col)['total_originations'].sum().reset_index()
            lender_totals = lender_totals.sort_values('total_originations', ascending=False)
            top_lender_names = lender_totals.head(10)[lender_col].tolist()
            logger.info(f"[DEBUG] Top {len(top_lender_names)} lenders for {purpose}: {top_lender_names[:3]}...")
            
            # Filter full DataFrame (all years) for these top lenders and this loan purpose
            purpose_df = filter_df_by_loan_purpose(df, purpose)
            if lender_col == 'lender_name':
                top_lenders_df = purpose_df[purpose_df['lender_name'].isin(top_lender_names)] if top_lender_names else pd.DataFrame()
            else:
                top_lenders_df = purpose_df[purpose_df[lender_col].isin(top_lender_names)] if top_lender_names else pd.DataFrame()
                if not top_lenders_df.empty and lender_col != 'lender_name':
                    top_lenders_df = top_lenders_df.rename(columns={lender_col: 'lender_name'})
            
            # Create lender-focused tables
            if top_lenders_df.empty:
                loans_by_race_ethnicity_lenders = pd.DataFrame()
                loans_by_borrower_income_lenders = pd.DataFrame()
                loans_by_neighborhood_income_lenders = pd.DataFrame()
                loans_by_neighborhood_demographics_lenders = pd.DataFrame()
                loans_by_loan_costs_lenders = {}
            else:
                # Use historical_census_data if available, otherwise fall back to census_data
                census_data_for_lenders = historical_census_data if historical_census_data else census_data
                loans_by_race_ethnicity_lenders = create_lender_race_ethnicity_table(
                    top_lenders_df, years, census_data=census_data_for_lenders
                )
                loans_by_borrower_income_lenders = create_lender_borrower_income_table(
                    top_lenders_df, years, hud_data=hud_data
                )
                loans_by_neighborhood_income_lenders = create_lender_neighborhood_income_table(
                    top_lenders_df, years, hud_data=hud_data, census_data=census_data_for_lenders
                )
                loans_by_neighborhood_demographics_lenders = create_lender_neighborhood_demographics_table(
                    top_lenders_df, years, census_data=census_data_for_lenders
                )
                
                # Table 5: Loan Costs by lender type (new)
                # Get top 10 lenders WITHIN each lender type for this loan purpose
                loans_by_loan_costs_lenders = {}
                if 'lender_type' in purpose_df.columns:
                    # Normalize lender_type values to match expected categories
                    # Map values like "Bank or Affiliate" -> "Bank", "Mortgage Company" -> "Mortgage Company", etc.
                    from justdata.apps.lendsight.report_builder import map_lender_type
                    purpose_df_normalized = purpose_df.copy()
                    purpose_df_normalized['lender_type_normalized'] = purpose_df_normalized['lender_type'].apply(
                        lambda x: map_lender_type(x) if pd.notna(x) else ''
                    )
                    
                    # Map normalized values to display names
                    def normalize_to_display(normalized_type):
                        if normalized_type == 'Bank':
                            return 'Bank'
                        elif normalized_type == 'Mortgage':
                            return 'Mortgage Company'
                        elif normalized_type == 'Credit Union':
                            return 'Credit Union'
                        else:
                            return normalized_type
                    
                    purpose_df_normalized['lender_type_display'] = purpose_df_normalized['lender_type_normalized'].apply(normalize_to_display)
                    
                    # First, create "All Lenders" table with top 10 overall
                    purpose_latest_df = purpose_df_normalized[purpose_df_normalized['year'] == latest_year].copy()
                    if not purpose_latest_df.empty:
                        all_lender_totals = purpose_latest_df.groupby('lender_name')['total_originations'].sum().reset_index()
                        all_lender_totals = all_lender_totals.sort_values('total_originations', ascending=False)
                        top_all_lender_names = all_lender_totals.head(10)['lender_name'].tolist()
                        top_all_df = purpose_df_normalized[purpose_df_normalized['lender_name'].isin(top_all_lender_names)].copy()
                        # Drop normalized columns before passing to create_lender_loan_costs_table
                        top_all_df_clean = top_all_df.drop(columns=['lender_type_normalized', 'lender_type_display'], errors='ignore')
                        loans_by_loan_costs_lenders['All'] = create_lender_loan_costs_table(
                            top_all_df_clean, latest_year, lender_type=None
                        )
                    else:
                        loans_by_loan_costs_lenders['All'] = pd.DataFrame()
                    
                    # Then, get top 10 within each lender type
                    for lender_type_display in ['Bank', 'Mortgage Company', 'Credit Union']:
                        # Filter to this lender type for this loan purpose using normalized display name
                        type_df = purpose_df_normalized[purpose_df_normalized['lender_type_display'] == lender_type_display].copy()
                        
                        if not type_df.empty:
                            # Get top 10 lenders within this type for this loan purpose
                            type_latest_df = type_df[type_df['year'] == latest_year].copy()
                            if not type_latest_df.empty:
                                type_lender_totals = type_latest_df.groupby('lender_name')['total_originations'].sum().reset_index()
                                type_lender_totals = type_lender_totals.sort_values('total_originations', ascending=False)
                                top_type_lender_names = type_lender_totals.head(10)['lender_name'].tolist()
                                
                                # Filter to top 10 lenders within this type
                                top_type_df = type_df[type_df['lender_name'].isin(top_type_lender_names)].copy()
                                # Drop normalized columns before passing to create_lender_loan_costs_table
                                top_type_df_clean = top_type_df.drop(columns=['lender_type_normalized', 'lender_type_display'], errors='ignore')
                                
                                # Create table with top 10 lenders within this type
                                loans_by_loan_costs_lenders[lender_type_display] = create_lender_loan_costs_table(
                                    top_type_df_clean, latest_year, lender_type=None  # Already filtered by type
                                )
                            else:
                                loans_by_loan_costs_lenders[lender_type_display] = pd.DataFrame()
                        else:
                            loans_by_loan_costs_lenders[lender_type_display] = pd.DataFrame()
                else:
                    # If lender_type not available, get top 10 overall
                    if not purpose_df.empty:
                        purpose_latest_df = purpose_df[purpose_df['year'] == latest_year].copy()
                        if not purpose_latest_df.empty:
                            lender_totals = purpose_latest_df.groupby('lender_name')['total_originations'].sum().reset_index()
                            lender_totals = lender_totals.sort_values('total_originations', ascending=False)
                            top_lender_names = lender_totals.head(10)['lender_name'].tolist()
                            top_lenders_df = purpose_df[purpose_df['lender_name'].isin(top_lender_names)].copy()
                            loans_by_loan_costs_lenders['All'] = create_lender_loan_costs_table(
                                top_lenders_df, latest_year
                            )
                        else:
                            loans_by_loan_costs_lenders['All'] = pd.DataFrame()
                    else:
                        loans_by_loan_costs_lenders['All'] = pd.DataFrame()
            
            section3_tables[purpose] = {
                'top_lender_names': top_lender_names,
                'loans_by_race_ethnicity': loans_by_race_ethnicity_lenders,
                'loans_by_borrower_income': loans_by_borrower_income_lenders,
                'loans_by_neighborhood_income': loans_by_neighborhood_income_lenders,
                'loans_by_neighborhood_demographics': loans_by_neighborhood_demographics_lenders,
                'loans_by_loan_costs': loans_by_loan_costs_lenders
            }
    
    report_data['section3'] = {
        'years': years,
        'by_purpose': section3_tables
    }
    
    # Section 4: HHI Market Concentration by Loan Purpose
    # Calculate HHI separately for each loan purpose
    if progress_tracker:
        progress_tracker.update_progress('building_report', 90, 'Building Section 4 (HHI)...')
    
    hhi_by_year_purpose = []
    loan_purpose_map = {
        '1': 'Home Purchase',
        '31': 'Refinance',
        '32': 'Refinance',
        '2': 'Home Equity',
        '4': 'Home Equity'
    }
    
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        year_data = {'year': year}
        
        # Calculate HHI for each loan purpose
        for purpose_code, purpose_name in loan_purpose_map.items():
            purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
            if not purpose_df.empty:
                hhi_result = calculate_mortgage_hhi_for_year(purpose_df, year)
                year_data[purpose_name] = hhi_result['hhi'] if hhi_result['hhi'] is not None else None
            else:
                year_data[purpose_name] = None
        
        hhi_by_year_purpose.append(year_data)
    
    report_data['section4'] = {
        'hhi_by_year_purpose': hhi_by_year_purpose
    }
    
    logger.info(f"[DEBUG] Created section4 with {len(hhi_by_year_purpose)} years of HHI data")
    logger.info(f"[DEBUG] Section4 keys: {list(report_data['section4'].keys())}")
    logger.info(f"[DEBUG] Sample HHI data: {hhi_by_year_purpose[0] if hhi_by_year_purpose else 'None'}")
    
    return report_data


