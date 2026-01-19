#!/usr/bin/env python3
"""
BizSight Core Analysis Logic
Single-county small business lending analysis with map visualization.
"""

import os
import sys
import json
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from justdata.apps.bizsight.config import BizSightConfig
from justdata.apps.bizsight.utils.bigquery_client import BigQueryClient
from justdata.apps.bizsight.utils.progress_tracker import ProgressTracker
from justdata.apps.bizsight.report_builder import create_top_lenders_table, create_county_summary_table, create_comparison_table, calculate_hhi_by_year, calculate_hhi_for_lenders, safe_int, safe_float
from justdata.apps.bizsight.ai_analysis import BizSightAnalyzer


def parse_web_parameters(county_data: dict, years_str: str) -> tuple:
    """
    Parse parameters from web interface.
    
    Args:
        county_data: Dictionary with county info (name, geoid5, etc.)
        years_str: Comma-separated years (e.g., "2018,2019,2020")
    
    Returns:
        Tuple of (geoid5, years_list)
    """
    # Extract GEOID5 from county data
    geoid5 = county_data.get('geoid5') or county_data.get('GEOID5')
    if not geoid5:
        raise ValueError("County GEOID5 not provided")
    
    # Parse years
    years = [int(y.strip()) for y in years_str.split(",") if y.strip().isdigit()]
    
    # Validate year range
    # Allow 1 year for planning regions (2024 only), otherwise require MIN_YEARS
    is_planning_region = county_data.get('is_planning_region', False)
    min_required_years = 1 if is_planning_region else BizSightConfig.MIN_YEARS
    if len(years) < min_required_years:
        if is_planning_region:
            raise ValueError("Planning region analysis requires 2024 data")
        else:
            raise ValueError(f"Must select at least {BizSightConfig.MIN_YEARS} years")
    
    # Validate years are in range
    min_year = min(years)
    max_year = max(years)
    # Limit to most recent 5 years (2020-2024)
    if min_year < 2020 or max_year > 2024:
        raise ValueError("Years must be between 2020 and 2024 (most recent 5 years)")
    
    return str(geoid5).zfill(5), sorted(years)


def run_analysis(county_data: dict, years_str: str, job_id: str = None, 
                 progress_tracker: Optional[ProgressTracker] = None) -> Dict:
    """
    Run small business lending analysis for a single county.
    
    Args:
        county_data: Dictionary with county info (name, geoid5, etc.)
        years_str: Comma-separated years
        job_id: Optional job ID for tracking
        progress_tracker: Optional progress tracker
    
    Returns:
        Dictionary with success status and results
    """
    try:
        # Initialize progress
        if progress_tracker:
            progress_tracker.update_progress('initializing', 0, 'Initializing analysis... Let\'s do this! 🚀')
        
        # Parse parameters
        geoid5, years = parse_web_parameters(county_data, years_str)
        county_name = county_data.get('name', 'Unknown County')
        is_planning_region = county_data.get('is_planning_region', False)
        
        if progress_tracker:
            progress_tracker.update_progress('preparing_data', 5, 
                f'Preparing data for {county_name}... Unpacking the data puzzle! 🧩')
        
        # Initialize BigQuery client
        if progress_tracker:
            progress_tracker.update_progress('connecting_db', 20, 'Connecting to BigQuery... Time to tap into that data goldmine! 💎')
        
        bq_client = BigQueryClient()
        
        # Fetch aggregate data with census demographics
        if progress_tracker:
            progress_tracker.update_progress('fetching_data', 30, 
                'Fetching tract-level lending data with census demographics... Digging deep for insights! ⛏️')
        
        print(f"DEBUG: Starting BigQuery aggregate query for GEOID5: {geoid5}, years: {years}")
        aggregate_query = bq_client.get_aggregate_data_with_census(geoid5, years)
        print(f"DEBUG: Aggregate query completed, converting to DataFrame...")
        aggregate_df = aggregate_query.to_dataframe()
        print(f"DEBUG: Aggregate DataFrame created: {len(aggregate_df)} rows")
        
        if aggregate_df.empty:
            return {
                'success': False,
                'error': f'No small business lending data found for {county_name}'
            }
        
        # Fetch disclosure data for top lenders table (2024) and HHI by year (all years)
        if progress_tracker:
            progress_tracker.update_progress('fetching_data', 40, 
                'Fetching lender-level disclosure data... Who\'s lending where? Let\'s find out! 🏦')
        
        print(f"DEBUG: Starting BigQuery disclosure query for GEOID5: {geoid5}, year: 2024, is_planning_region: {is_planning_region}")
        disclosure_query_2024 = bq_client.get_disclosure_data(geoid5, [2024], is_planning_region=is_planning_region)
        print(f"DEBUG: Disclosure query completed, converting to DataFrame...")
        disclosure_df = disclosure_query_2024.to_dataframe()
        print(f"DEBUG: Disclosure DataFrame created: {len(disclosure_df)} rows")
        
        # Verify that disclosure_df only contains 2024 data
        if 'year' in disclosure_df.columns:
            unique_years = disclosure_df['year'].unique()
            if len(unique_years) > 1 or (len(unique_years) == 1 and unique_years[0] != 2024):
                print(f"DEBUG: WARNING - disclosure_df contains years {unique_years}, expected only 2024")
            else:
                print(f"DEBUG: Verified disclosure_df contains only 2024 data")
        else:
            print(f"DEBUG: WARNING - disclosure_df has no 'year' column, cannot verify year filtering")
        
        # Also fetch disclosure data for all years for HHI by year calculation
        print(f"DEBUG: Starting BigQuery disclosure query for all years: {years}, is_planning_region: {is_planning_region}")
        disclosure_query_all = bq_client.get_disclosure_data(geoid5, years, is_planning_region=is_planning_region)
        print(f"DEBUG: Disclosure query for all years completed, converting to DataFrame...")
        disclosure_df_all_years = disclosure_query_all.to_dataframe()
        print(f"DEBUG: Disclosure DataFrame for all years created: {len(disclosure_df_all_years)} rows")
        
        # Build county summary table (Section 2) - most recent 5 years
        if progress_tracker:
            progress_tracker.update_progress('building_report', 50, 
                'Section 2: Creating county summary table... Organizing the data! 📋')
        county_summary_df = pd.DataFrame()
        if not aggregate_df.empty:
            print(f"DEBUG: Creating county summary table from {len(aggregate_df)} aggregate rows")
            print(f"DEBUG: Aggregate DF columns: {aggregate_df.columns.tolist()}")
            print(f"DEBUG: Aggregate DF years: {aggregate_df['year'].unique() if 'year' in aggregate_df.columns else 'no year column'}")
            county_summary_df = create_county_summary_table(aggregate_df, years)
            print(f"DEBUG: County summary table created: {len(county_summary_df)} rows")
            if not county_summary_df.empty:
                print(f"DEBUG: County summary table columns: {county_summary_df.columns.tolist()}")
                print(f"DEBUG: County summary table first row: {county_summary_df.iloc[0].to_dict()}")
        else:
            print("DEBUG: aggregate_df is empty, cannot create county summary table")
        
        # Fetch state and national benchmarks for comparison table (Section 3)
        if progress_tracker:
            progress_tracker.update_progress('fetching_data', 45, 
                'Loading state and national benchmarks... Setting the bar for comparison! 📈')
        
        # Handle District of Columbia special case (GEOID5 starts with 11, but DC is both county and state)
        # For DC, state_fips should be "11" (DC's state FIPS code)
        state_fips = str(geoid5)[:2]  # First 2 digits of GEOID5
        # DC's GEOID5 is 11001, so state_fips will correctly be "11"
        state_benchmarks = {}
        national_benchmarks = {}
        
        # Try to load benchmarks from individual JSON files first (if pre-generated)
        # Look for state file: state_fips.json (e.g., "01.json", "12.json") or consolidated benchmarks.json
        # Check multiple possible locations - prioritize apps/data where files were generated
        print(f"DEBUG: Looking for benchmark files. State FIPS: {state_fips}")
        print(f"DEBUG: DATA_DIR from config: {BizSightConfig.DATA_DIR}")
        print(f"DEBUG: DATA_DIR as Path: {Path(BizSightConfig.DATA_DIR)}")
        print(f"DEBUG: DATA_DIR exists: {Path(BizSightConfig.DATA_DIR).exists()}")
        
        possible_dirs = [
            Path(BizSightConfig.DATA_DIR),  # apps/data (where files were generated)
            Path(__file__).parent / 'data',  # apps/bizsight/data
            Path(__file__).parent.parent.parent / 'data',  # #JustData_Repo/data
            Path(__file__).parent.parent.parent / 'data' / 'benchmarks',  # #JustData_Repo/data/benchmarks
            Path(BizSightConfig.DATA_DIR) / 'benchmarks',  # apps/data/benchmarks
            Path(BizSightConfig.DATA_DIR) / 'processed',  # apps/data/processed
            Path(BizSightConfig.DATA_DIR) / 'raw',  # apps/data/raw
        ]
        
        print(f"DEBUG: Checking {len(possible_dirs)} possible directories for benchmark files...")
        for i, dir_path in enumerate(possible_dirs):
            print(f"DEBUG:   [{i+1}] {dir_path} (exists: {dir_path.exists()})")
        
        state_file = None
        national_file = None
        consolidated_file = None
        
        # Find files in any of the possible directories
        for benchmarks_dir in possible_dirs:
            if benchmarks_dir.exists():
                test_state_file = benchmarks_dir / f"{state_fips.zfill(2)}.json"
                test_national_file = benchmarks_dir / "national.json"
                test_consolidated_file = benchmarks_dir / "benchmarks.json"
                
                if test_state_file.exists() and not state_file:
                    state_file = test_state_file
                    print(f"DEBUG: Found state benchmark file at {state_file}")
                if test_national_file.exists() and not national_file:
                    national_file = test_national_file
                    print(f"DEBUG: Found national benchmark file at {national_file}")
                if test_consolidated_file.exists() and not consolidated_file:
                    consolidated_file = test_consolidated_file
                    print(f"DEBUG: Found consolidated benchmark file at {consolidated_file}")
        
        # If not found, try default location
        if not state_file:
            benchmarks_dir = Path(BizSightConfig.DATA_DIR)
            state_file = benchmarks_dir / f"{state_fips.zfill(2)}.json"
        if not national_file:
            benchmarks_dir = Path(BizSightConfig.DATA_DIR)
            national_file = benchmarks_dir / "national.json"
        if not consolidated_file:
            benchmarks_dir = Path(BizSightConfig.DATA_DIR)
            consolidated_file = benchmarks_dir / "benchmarks.json"
        
        # Try individual state file first
        if state_file.exists():
            try:
                print(f"DEBUG: Loading state benchmarks from {state_file}")
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    # Handle different file structures
                    if isinstance(state_data, dict):
                        state_benchmarks = state_data.get('2024', state_data)  # Try 2024 key, or use whole dict
                    else:
                        state_benchmarks = state_data
                    print(f"DEBUG: Loaded state benchmarks from file: {state_benchmarks}")
            except Exception as e:
                print(f"Warning: Failed to load state benchmarks from {state_file}: {e}")
                import traceback
                traceback.print_exc()
        
        # Try national file
        if national_file.exists():
            try:
                print(f"DEBUG: Loading national benchmarks from {national_file}")
                with open(national_file, 'r') as f:
                    national_data = json.load(f)
                    # Handle different file structures
                    if isinstance(national_data, dict):
                        national_benchmarks = national_data.get('2024', national_data)  # Try 2024 key, or use whole dict
                    else:
                        national_benchmarks = national_data
                    print(f"DEBUG: Loaded national benchmarks from file: {national_benchmarks}")
            except Exception as e:
                print(f"Warning: Failed to load national benchmarks from {national_file}: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback: Try consolidated benchmarks.json file
        if (not state_benchmarks or not national_benchmarks) and consolidated_file.exists():
            try:
                print(f"DEBUG: Loading benchmarks from consolidated file {consolidated_file}")
                with open(consolidated_file, 'r') as f:
                    benchmarks_data = json.load(f)
                    # Get state benchmarks
                    if not state_benchmarks and 'states' in benchmarks_data and state_fips in benchmarks_data['states']:
                        state_benchmarks = benchmarks_data['states'][state_fips].get('2024', {})
                        print(f"DEBUG: Loaded state benchmarks from consolidated file: {state_benchmarks}")
                    # Get national benchmarks
                    if not national_benchmarks and 'national' in benchmarks_data and '2024' in benchmarks_data['national']:
                        national_benchmarks = benchmarks_data['national']['2024']
                        print(f"DEBUG: Loaded national benchmarks from consolidated file: {national_benchmarks}")
            except Exception as e:
                print(f"Warning: Failed to load benchmarks from consolidated file: {e}")
                import traceback
                traceback.print_exc()
        
        # If benchmarks not loaded from file, query BigQuery
        if not state_benchmarks or not national_benchmarks:
            if not state_benchmarks:
                try:
                    print(f"DEBUG: Fetching state benchmarks from BigQuery for state FIPS: {state_fips}")
                    state_query = bq_client.get_state_benchmarks(state_fips, year=2024)
                    state_df = state_query.to_dataframe()
                    if not state_df.empty:
                        row = state_df.iloc[0]
                        state_total = safe_int(row.get('total_loans', 0))
                        state_amount = float(row.get('total_amount', 0.0))
                        state_num_under_100k = safe_int(row.get('num_under_100k', 0))
                        state_num_100k_250k = safe_int(row.get('num_100k_250k', 0))
                        state_num_250k_1m = safe_int(row.get('num_250k_1m', 0))
                        state_amt_under_100k = safe_float(row.get('amt_under_100k', 0.0))
                        state_amt_250k_1m = safe_float(row.get('amt_250k_1m', 0.0))
                        state_numsb_under_1m = safe_int(row.get('numsb_under_1m', 0))
                        state_amtsb_under_1m = safe_float(row.get('amtsb_under_1m', 0.0))
                        state_lmi_loans = safe_int(row.get('lmi_tract_loans', 0))
                        
                        # Income category breakdowns from BigQuery
                        state_low_income_loans = safe_int(row.get('low_income_loans', 0))
                        state_moderate_income_loans = safe_int(row.get('moderate_income_loans', 0))
                        state_middle_income_loans = safe_int(row.get('middle_income_loans', 0))
                        state_upper_income_loans = safe_int(row.get('upper_income_loans', 0))
                        state_low_income_amount = float(row.get('low_income_amount', 0.0))
                        state_moderate_income_amount = float(row.get('moderate_income_amount', 0.0))
                        state_middle_income_amount = float(row.get('middle_income_amount', 0.0))
                        state_upper_income_amount = float(row.get('upper_income_amount', 0.0))
                        
                        state_benchmarks = {
                            'total_loans': state_total,
                            'total_amount': state_amount,
                            'pct_loans_under_100k': (state_num_under_100k / state_total * 100) if state_total > 0 else 0.0,
                            'pct_loans_100k_250k': (state_num_100k_250k / state_total * 100) if state_total > 0 else 0.0,
                            'pct_loans_250k_1m': (state_num_250k_1m / state_total * 100) if state_total > 0 else 0.0,
                            'pct_loans_sb_under_1m': (state_numsb_under_1m / state_total * 100) if state_total > 0 else 0.0,
                            'pct_loans_lmi_tract': (state_lmi_loans / state_total * 100) if state_total > 0 else 0.0,
                            'pct_amount_under_100k': (state_amt_under_100k / state_amount * 100) if state_amount > 0 else 0.0,
                            'pct_amount_250k_1m': (state_amt_250k_1m / state_amount * 100) if state_amount > 0 else 0.0,
                            'pct_amount_sb_under_1m': (state_amtsb_under_1m / state_amount * 100) if state_amount > 0 else 0.0,
                            # Income category percentages
                            'pct_loans_low_income': (state_low_income_loans / state_total * 100) if state_total > 0 else 0.0,
                            'pct_loans_moderate_income': (state_moderate_income_loans / state_total * 100) if state_total > 0 else 0.0,
                            'pct_loans_middle_income': (state_middle_income_loans / state_total * 100) if state_total > 0 else 0.0,
                            'pct_loans_upper_income': (state_upper_income_loans / state_total * 100) if state_total > 0 else 0.0,
                            'pct_amount_low_income': (state_low_income_amount / state_amount * 100) if state_amount > 0 else 0.0,
                            'pct_amount_moderate_income': (state_moderate_income_amount / state_amount * 100) if state_amount > 0 else 0.0,
                            'pct_amount_middle_income': (state_middle_income_amount / state_amount * 100) if state_amount > 0 else 0.0,
                            'pct_amount_upper_income': (state_upper_income_amount / state_amount * 100) if state_amount > 0 else 0.0
                        }
                        print(f"DEBUG: State benchmarks loaded from BigQuery: {state_benchmarks}")
                except Exception as e:
                    print(f"Warning: Failed to fetch state benchmarks: {e}")
                    import traceback
                    traceback.print_exc()
            
            if not national_benchmarks:
                try:
                    print(f"DEBUG: Fetching national benchmarks from BigQuery")
                    national_query = bq_client.get_national_benchmarks(year=2024)
                    national_df = national_query.to_dataframe()
                    if not national_df.empty:
                        row = national_df.iloc[0]
                        national_total = safe_int(row.get('total_loans', 0))
                        national_amount = float(row.get('total_amount', 0.0))
                        national_num_under_100k = safe_int(row.get('num_under_100k', 0))
                        national_num_100k_250k = safe_int(row.get('num_100k_250k', 0))
                        national_num_250k_1m = safe_int(row.get('num_250k_1m', 0))
                        national_amt_under_100k = safe_float(row.get('amt_under_100k', 0.0))
                        national_amt_250k_1m = safe_float(row.get('amt_250k_1m', 0.0))
                        national_numsb_under_1m = safe_int(row.get('numsb_under_1m', 0))
                        national_amtsb_under_1m = safe_float(row.get('amtsb_under_1m', 0.0))
                        national_lmi_loans = safe_int(row.get('lmi_tract_loans', 0))
                        
                        # Income category breakdowns from BigQuery
                        national_low_income_loans = safe_int(row.get('low_income_loans', 0))
                        national_moderate_income_loans = safe_int(row.get('moderate_income_loans', 0))
                        national_middle_income_loans = safe_int(row.get('middle_income_loans', 0))
                        national_upper_income_loans = safe_int(row.get('upper_income_loans', 0))
                        national_low_income_amount = float(row.get('low_income_amount', 0.0))
                        national_moderate_income_amount = float(row.get('moderate_income_amount', 0.0))
                        national_middle_income_amount = float(row.get('middle_income_amount', 0.0))
                        national_upper_income_amount = float(row.get('upper_income_amount', 0.0))
                        
                        national_benchmarks = {
                            'total_loans': national_total,
                            'total_amount': national_amount,
                            'pct_loans_under_100k': (national_num_under_100k / national_total * 100) if national_total > 0 else 0.0,
                            'pct_loans_100k_250k': (national_num_100k_250k / national_total * 100) if national_total > 0 else 0.0,
                            'pct_loans_250k_1m': (national_num_250k_1m / national_total * 100) if national_total > 0 else 0.0,
                            'pct_loans_sb_under_1m': (national_numsb_under_1m / national_total * 100) if national_total > 0 else 0.0,
                            'pct_loans_lmi_tract': (national_lmi_loans / national_total * 100) if national_total > 0 else 0.0,
                            'pct_amount_under_100k': (national_amt_under_100k / national_amount * 100) if national_amount > 0 else 0.0,
                            'pct_amount_250k_1m': (national_amt_250k_1m / national_amount * 100) if national_amount > 0 else 0.0,
                            'pct_amount_sb_under_1m': (national_amtsb_under_1m / national_amount * 100) if national_amount > 0 else 0.0,
                            # Income category percentages
                            'pct_loans_low_income': (national_low_income_loans / national_total * 100) if national_total > 0 else 0.0,
                            'pct_loans_moderate_income': (national_moderate_income_loans / national_total * 100) if national_total > 0 else 0.0,
                            'pct_loans_middle_income': (national_middle_income_loans / national_total * 100) if national_total > 0 else 0.0,
                            'pct_loans_upper_income': (national_upper_income_loans / national_total * 100) if national_total > 0 else 0.0,
                            'pct_amount_low_income': (national_low_income_amount / national_amount * 100) if national_amount > 0 else 0.0,
                            'pct_amount_moderate_income': (national_moderate_income_amount / national_amount * 100) if national_amount > 0 else 0.0,
                            'pct_amount_middle_income': (national_middle_income_amount / national_amount * 100) if national_amount > 0 else 0.0,
                            'pct_amount_upper_income': (national_upper_income_amount / national_amount * 100) if national_amount > 0 else 0.0
                        }
                        print(f"DEBUG: National benchmarks loaded from BigQuery: {national_benchmarks}")
                except Exception as e:
                    print(f"Warning: Failed to fetch national benchmarks: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Ensure we have at least empty dicts if benchmarks failed to load
        if not state_benchmarks:
            state_benchmarks = {}
        if not national_benchmarks:
            national_benchmarks = {}
        
        # Get county 2020 data for % change calculations (baseline year - most recent 5 years)
        county_2020_data = None
        try:
            county_2020_df = pd.DataFrame()
            if 'year' in aggregate_df.columns:
                # Handle both string and int year values
                if aggregate_df['year'].dtype in ['int64', 'int32', 'int']:
                    county_2020_df = aggregate_df[aggregate_df['year'] == 2020].copy()
                else:
                    county_2020_df = aggregate_df[aggregate_df['year'].astype(str) == '2020'].copy()
            print(f"DEBUG: County 2020 data: {len(county_2020_df)} rows")
            if not county_2020_df.empty:
                county_2020_num_under_100k = safe_int(county_2020_df.get('num_under_100k', pd.Series([0])).sum())
                county_2020_num_100k_250k = safe_int(county_2020_df.get('num_100k_250k', pd.Series([0])).sum())
                county_2020_num_250k_1m = safe_int(county_2020_df.get('num_250k_1m', pd.Series([0])).sum())
                county_2020_amt_under_100k = float(county_2020_df.get('amt_under_100k', pd.Series([0.0])).sum())
                county_2020_amt_250k_1m = float(county_2020_df.get('amt_250k_1m', pd.Series([0.0])).sum())
                numsb_col = 'numsbrev_under_1m' if 'numsbrev_under_1m' in county_2020_df.columns else 'numsb_under_1m'
                amtsb_col = 'amtsbrev_under_1m' if 'amtsbrev_under_1m' in county_2020_df.columns else 'amtsb_under_1m'
                county_2020_numsb_under_1m = safe_int(county_2020_df.get(numsb_col, pd.Series([0])).sum())
                county_2020_amtsb_under_1m = float(county_2020_df.get(amtsb_col, pd.Series([0.0])).sum())
                
                if 'is_lmi_tract' in county_2020_df.columns:
                    lmi_mask = (county_2020_df['is_lmi_tract'] == 1) | (county_2020_df['is_lmi_tract'] == True) | (county_2020_df['is_lmi_tract'].astype(str) == '1')
                    county_2020_lmi_tract_loans = int(county_2020_df[lmi_mask].get('loan_count', pd.Series([0])).sum())
                else:
                    county_2020_lmi_tract_loans = 0
                
                # Calculate 2020 income category breakdowns
                county_2020_low_income_loans = 0
                county_2020_moderate_income_loans = 0
                county_2020_middle_income_loans = 0
                county_2020_upper_income_loans = 0
                county_2020_low_income_amount = 0.0
                county_2020_moderate_income_amount = 0.0
                county_2020_middle_income_amount = 0.0
                county_2020_upper_income_amount = 0.0
                
                if 'income_level' in county_2020_df.columns:
                    low_mask_2020 = county_2020_df['income_level'] == 1
                    moderate_mask_2020 = county_2020_df['income_level'] == 2
                    middle_mask_2020 = county_2020_df['income_level'] == 3
                    upper_mask_2020 = county_2020_df['income_level'] == 4
                    
                    county_2020_low_income_loans = int(county_2020_df[low_mask_2020].get('loan_count', pd.Series([0])).sum())
                    county_2020_moderate_income_loans = int(county_2020_df[moderate_mask_2020].get('loan_count', pd.Series([0])).sum())
                    county_2020_middle_income_loans = int(county_2020_df[middle_mask_2020].get('loan_count', pd.Series([0])).sum())
                    county_2020_upper_income_loans = int(county_2020_df[upper_mask_2020].get('loan_count', pd.Series([0])).sum())
                    
                    county_2020_low_income_amount = float(county_2020_df[low_mask_2020].get('loan_amount', pd.Series([0.0])).sum())
                    county_2020_moderate_income_amount = float(county_2020_df[moderate_mask_2020].get('loan_amount', pd.Series([0.0])).sum())
                    county_2020_middle_income_amount = float(county_2020_df[middle_mask_2020].get('loan_amount', pd.Series([0.0])).sum())
                    county_2020_upper_income_amount = float(county_2020_df[upper_mask_2020].get('loan_amount', pd.Series([0.0])).sum())
                elif 'income_category' in county_2020_df.columns:
                    low_mask_2020 = county_2020_df['income_category'].str.contains('Low Income', na=False)
                    moderate_mask_2020 = county_2020_df['income_category'].str.contains('Moderate Income', na=False)
                    middle_mask_2020 = county_2020_df['income_category'].str.contains('Middle Income', na=False)
                    upper_mask_2020 = county_2020_df['income_category'].str.contains('Upper Income', na=False)
                    
                    county_2020_low_income_loans = int(county_2020_df[low_mask_2020].get('loan_count', pd.Series([0])).sum())
                    county_2020_moderate_income_loans = int(county_2020_df[moderate_mask_2020].get('loan_count', pd.Series([0])).sum())
                    county_2020_middle_income_loans = int(county_2020_df[middle_mask_2020].get('loan_count', pd.Series([0])).sum())
                    county_2020_upper_income_loans = int(county_2020_df[upper_mask_2020].get('loan_count', pd.Series([0])).sum())
                    
                    county_2020_low_income_amount = float(county_2020_df[low_mask_2020].get('loan_amount', pd.Series([0.0])).sum())
                    county_2020_moderate_income_amount = float(county_2020_df[moderate_mask_2020].get('loan_amount', pd.Series([0.0])).sum())
                    county_2020_middle_income_amount = float(county_2020_df[middle_mask_2020].get('loan_amount', pd.Series([0.0])).sum())
                    county_2020_upper_income_amount = float(county_2020_df[upper_mask_2020].get('loan_amount', pd.Series([0.0])).sum())
                
                county_2020_total_loans = county_2020_num_under_100k + county_2020_num_100k_250k + county_2020_num_250k_1m
                county_2020_amt_100k_250k = float(county_2020_df.get('amt_100k_250k', pd.Series([0.0])).sum())
                county_2020_total_amount = county_2020_amt_under_100k + county_2020_amt_100k_250k + county_2020_amt_250k_1m
                
                county_2020_data = {
                    'total_loans': county_2020_total_loans,
                    'total_amount': county_2020_total_amount,
                    'num_under_100k': county_2020_num_under_100k,
                    'num_100k_250k': county_2020_num_100k_250k,
                    'num_250k_1m': county_2020_num_250k_1m,
                    'numsb_under_1m': county_2020_numsb_under_1m,
                    'low_income_loans': county_2020_low_income_loans,
                    'moderate_income_loans': county_2020_moderate_income_loans,
                    'middle_income_loans': county_2020_middle_income_loans,
                    'upper_income_loans': county_2020_upper_income_loans,
                    'low_income_amount': county_2020_low_income_amount,
                    'moderate_income_amount': county_2020_moderate_income_amount,
                    'middle_income_amount': county_2020_middle_income_amount,
                    'upper_income_amount': county_2020_upper_income_amount,
                    'lmi_tract_loans': county_2020_lmi_tract_loans,
                    'amt_under_100k': county_2020_amt_under_100k,
                    'amt_100k_250k': county_2020_amt_100k_250k,
                    'amt_250k_1m': county_2020_amt_250k_1m,
                    'amtsb_under_1m': county_2020_amtsb_under_1m
                }
                print(f"DEBUG: County 2020 data calculated: total_loans={county_2020_total_loans}, total_amount={county_2020_total_amount}")
            else:
                print(f"DEBUG: County 2020 data: county_2020_df is empty")
        except Exception as e:
            print(f"Warning: Failed to calculate county 2020 data: {e}")
            import traceback
            traceback.print_exc()
        
        # Build comparison table (Section 3) - County, State, National Comparison
        if progress_tracker:
            progress_tracker.update_progress('section_3', 70, 
                'Section 3: Creating comparison table... See how we stack up! 📊')
        comparison_df = pd.DataFrame()
        if not aggregate_df.empty:
            print(f"DEBUG: Creating comparison table")
            print(f"DEBUG: State benchmarks available: {bool(state_benchmarks)}, keys: {list(state_benchmarks.keys()) if state_benchmarks else 'None'}")
            print(f"DEBUG: National benchmarks available: {bool(national_benchmarks)}, keys: {list(national_benchmarks.keys()) if national_benchmarks else 'None'}")
            print(f"DEBUG: County 2020 data available: {bool(county_2020_data)}")
            try:
                comparison_df = create_comparison_table(aggregate_df, state_benchmarks, national_benchmarks, county_2020_data)
                print(f"DEBUG: Comparison table created: {len(comparison_df)} rows")
                if not comparison_df.empty:
                    print(f"DEBUG: Comparison table columns: {comparison_df.columns.tolist()}")
                    print(f"DEBUG: Comparison table first row: {comparison_df.iloc[0].to_dict()}")
                    print(f"DEBUG: Comparison table sample: {comparison_df.head(3).to_dict('records')}")
                else:
                    print(f"DEBUG: WARNING - Comparison table is EMPTY!")
            except Exception as e:
                print(f"DEBUG: ERROR creating comparison table: {e}")
                import traceback
                traceback.print_exc()
        
        # Build top lenders table (Section 4) - 2024 only
        if progress_tracker:
            progress_tracker.update_progress('section_4', 75, 
                'Section 4: Creating top lenders table... Who are the big players? 🏆')
        top_lenders_df = pd.DataFrame()
        hhi_value = None
        hhi_concentration = None
        if not disclosure_df.empty:
            print(f"DEBUG: Creating top lenders table from {len(disclosure_df)} disclosure rows")
            print(f"DEBUG: Disclosure DF columns: {disclosure_df.columns.tolist()}")
            print(f"DEBUG: Disclosure DF years: {disclosure_df['year'].unique() if 'year' in disclosure_df.columns else 'no year column'}")
            print(f"DEBUG: Disclosure DF lenders: {disclosure_df['lender_name'].nunique() if 'lender_name' in disclosure_df.columns else 'no lender_name column'} unique lenders")
            top_lenders_df = create_top_lenders_table(disclosure_df, year=2024)
            print(f"DEBUG: Top lenders table created: {len(top_lenders_df)} rows")
            if not top_lenders_df.empty:
                print(f"DEBUG: Top lenders table columns: {top_lenders_df.columns.tolist()}")
                print(f"DEBUG: Top lenders table first row: {top_lenders_df.iloc[0].to_dict()}")
        
        # Calculate HHI using dollar amounts of small business loans in 2024
        # We can calculate from either disclosure_df or top_lenders_df
        if not disclosure_df.empty:
            # Filter to 2024 data (handle both string and int year values)
            if 'year' in disclosure_df.columns:
                disclosure_year_str = disclosure_df['year'].astype(str)
                disclosure_2024 = disclosure_df[disclosure_year_str == '2024'].copy()
                print(f"DEBUG: Filtered disclosure to 2024: {len(disclosure_2024)} rows from {len(disclosure_df)} total")
            else:
                disclosure_2024 = disclosure_df.copy()
            
            # Get total loan amounts by lender
            if 'lender_name' in disclosure_2024.columns:
                # Sum all amount fields for each lender
                amt_fields = ['amt_under_100k', 'amt_100k_250k', 'amt_250k_1m']
                lender_amounts = {}
                for lender_name in disclosure_2024['lender_name'].unique():
                    lender_df = disclosure_2024[disclosure_2024['lender_name'] == lender_name]
                    total_amt = 0.0
                    for field in amt_fields:
                        if field in lender_df.columns:
                            amt_sum = lender_df[field].sum()
                            total_amt += float(amt_sum) if pd.notna(amt_sum) else 0.0
                    if total_amt > 0:
                        lender_amounts[lender_name] = total_amt
                
                print(f"DEBUG: Found {len(lender_amounts)} lenders with amounts > 0")
                if lender_amounts:
                    print(f"DEBUG: Sample lender amounts: {dict(list(lender_amounts.items())[:3])}")
                
                # Calculate HHI (following Branch Seeker pattern)
                if lender_amounts:
                    total_amount = sum(lender_amounts.values())
                    if total_amount > 0:
                        # Calculate market shares as percentages (like Branch Seeker)
                        market_shares = {}
                        for lender_name, lender_amt in lender_amounts.items():
                            market_shares[lender_name] = (lender_amt / total_amount) * 100
                        
                        # Calculate HHI: sum of squared market shares (0-10,000 scale)
                        hhi = sum(share ** 2 for share in market_shares.values())
                        hhi_value = round(hhi, 2)
                        
                        # Determine concentration level
                        if hhi_value < 1500:
                            hhi_concentration = 'Low concentration (competitive market)'
                        elif hhi_value < 2500:
                            hhi_concentration = 'Moderate concentration'
                        else:
                            hhi_concentration = 'High concentration'
                        
                        print(f"DEBUG: HHI calculated: {hhi_value:.2f} ({hhi_concentration})")
                        print(f"DEBUG: Total loan amount: ${total_amount:,.0f}, Number of lenders: {len(lender_amounts)}")
                else:
                    print("DEBUG: WARNING - No lender amounts found for HHI calculation")
            else:
                print("DEBUG: WARNING - No 'lender_name' column in disclosure data for HHI calculation")
        elif not top_lenders_df.empty:
            # Fallback: Calculate HHI from top_lenders_df if disclosure_df is empty
            print("DEBUG: Calculating HHI from top_lenders_df (disclosure_df was empty)")
            print(f"DEBUG: top_lenders_df columns: {top_lenders_df.columns.tolist()}")
            lender_amounts = {}
            # Try different column names for amount
            amt_col = None
            for col in ['Amt Total', 'Amt Total (in $000s)', 'amt_total']:
                if col in top_lenders_df.columns:
                    amt_col = col
                    break
            
            if amt_col:
                print(f"DEBUG: Using column '{amt_col}' for HHI calculation")
                for _, row in top_lenders_df.iterrows():
                    lender_name = row.get('Lender Name', '')
                    amt_total = row.get(amt_col, 0.0)
                    # Handle if amt_total is in thousands - convert to actual amount
                    if amt_total and amt_total > 0:
                        # If the column name suggests thousands, multiply by 1000
                        if '000s' in amt_col or 'thousands' in amt_col.lower():
                            lender_amounts[lender_name] = float(amt_total) * 1000
                        else:
                            lender_amounts[lender_name] = float(amt_total)
                print(f"DEBUG: Found {len(lender_amounts)} lenders with amounts from top_lenders_df")
            else:
                print(f"DEBUG: WARNING - No amount column found in top_lenders_df for HHI calculation")
            
            if lender_amounts:
                total_amount = sum(lender_amounts.values())
                if total_amount > 0:
                    # Calculate market shares as percentages
                    market_shares = {}
                    for lender_name, lender_amt in lender_amounts.items():
                        market_shares[lender_name] = (lender_amt / total_amount) * 100
                    
                    # Calculate HHI: sum of squared market shares (0-10,000 scale)
                    hhi = sum(share ** 2 for share in market_shares.values())
                    hhi_value = round(hhi, 2)
                    
                    # Determine concentration level
                    if hhi_value < 1500:
                        hhi_concentration = 'Low concentration (competitive market)'
                    elif hhi_value < 2500:
                        hhi_concentration = 'Moderate concentration'
                    else:
                        hhi_concentration = 'High concentration'
                    
                    print(f"DEBUG: HHI calculated from top_lenders_df: {hhi_value:.2f} ({hhi_concentration})")
                    print(f"DEBUG: Total loan amount: ${total_amount:,.0f}, Number of lenders: {len(lender_amounts)}")
        else:
            print("DEBUG: WARNING - Cannot calculate HHI: both disclosure_df and top_lenders_df are empty or missing required columns")
        
        # Calculate HHI by year (2018-2024) for Section 5
        hhi_by_year = []
        # Use disclosure_df_all_years if available, otherwise try disclosure_df, then fallback
        if not disclosure_df_all_years.empty:
            print(f"DEBUG: Calculating HHI by year from disclosure_df_all_years for years: {years}")
            hhi_by_year = calculate_hhi_by_year(disclosure_df_all_years, years)
        elif not disclosure_df.empty:
            print(f"DEBUG: Calculating HHI by year from disclosure_df (2024 only) for years: {years}")
            # Only 2024 data available, calculate for 2024 only
            hhi_value_2024 = calculate_hhi_for_lenders(disclosure_df, 2024)
            if hhi_value_2024 is not None:
                if hhi_value_2024 < 1500:
                    concentration = 'Low concentration (competitive market)'
                elif hhi_value_2024 < 2500:
                    concentration = 'Moderate concentration'
                else:
                    concentration = 'High concentration'
                hhi_by_year.append({
                    'year': 2024,
                    'hhi_value': hhi_value_2024,
                    'concentration_level': concentration
                })
        elif not top_lenders_df.empty:
            # Fallback: Calculate HHI by year from top_lenders_df if available
            # Note: top_lenders_df only has 2024 data, so we can only calculate for 2024
            print(f"DEBUG: Calculating HHI by year from top_lenders_df (2024 only)")
            # Use the HHI already calculated above if available
            if hhi_value is not None:
                hhi_by_year.append({
                    'year': 2024,
                    'hhi_value': hhi_value,
                    'concentration_level': hhi_concentration
                })
        
        print(f"DEBUG: HHI by year calculated: {len(hhi_by_year)} years")
        for hhi_year_data in hhi_by_year:
            print(f"DEBUG: Year {hhi_year_data['year']}: HHI={hhi_year_data.get('hhi_value')}, Level={hhi_year_data.get('concentration_level')}")
        
        # Fetch county summary statistics for 2024 only (for the summary table next to map)
        if progress_tracker:
            progress_tracker.update_progress('section_1', 55, 
                'Section 1: Preparing geographic overview... Mapping it out! 🗺️')
        
        summary_query = bq_client.get_county_summary_stats(geoid5, [2024])  # 2024 only for summary table
        summary_df = summary_query.to_dataframe()
        
        # Get county minority threshold for race layers - calculate from aggregate data
        # Use median minority percentage from tracts in the county
        if 'tract_minority_population_percent' in aggregate_df.columns:
            county_minority_pct = aggregate_df['tract_minority_population_percent'].median()
            if pd.isna(county_minority_pct):
                county_minority_pct = 50.0  # Default if no data
        else:
            county_minority_pct = 50.0  # Default if field doesn't exist
        
        # Prepare tract data for map
        if progress_tracker:
            progress_tracker.update_progress('section_1', 60, 
                'Section 1: Preparing map data and visualizations... Making it look pretty! 🎨')
        
        # Aggregate tract data across years
        # Use census_tract_geoid (from SQL alias) or fallback to tract_geoid if it exists
        tract_id_col = 'census_tract_geoid' if 'census_tract_geoid' in aggregate_df.columns else 'tract_geoid'
        if tract_id_col not in aggregate_df.columns:
            # Try other possible column names
            for col in ['census_tract', 'tract', 'tract_code']:
                if col in aggregate_df.columns:
                    tract_id_col = col
                    break
        
        # First, create year-by-year amounts for each tract (for popup charts)
        tract_year_data = {}
        if 'year' in aggregate_df.columns and tract_id_col in aggregate_df.columns:
            for _, row in aggregate_df.iterrows():
                tract_id = str(row[tract_id_col])
                year = str(row['year'])
                loan_amount = float(row.get('loan_amount', 0.0))
                
                if tract_id not in tract_year_data:
                    tract_year_data[tract_id] = {}
                tract_year_data[tract_id][year] = loan_amount
        
        tract_summary = aggregate_df.groupby(tract_id_col).agg({
            'loan_count': 'sum',
            'loan_amount': 'sum',
            'tract_minority_population_percent': 'first',
            'tract_to_msa_income_percentage': 'first',
            'tract_median_income': 'first',
            'tract_population': 'first',
            'tract_white_percent': 'first',
            'tract_black_percent': 'first',
            'tract_hispanic_percent': 'first',
            'tract_asian_percent': 'first',
            'tract_other_race_percent': 'first',
            'income_category': 'first',
            'is_lmi_tract': 'first'
        }).reset_index()
        
        # Add year-by-year amounts to tract_summary
        if tract_year_data:
            def get_year_amounts(tract_id):
                tract_id_str = str(tract_id)
                year_amounts = tract_year_data.get(tract_id_str, {})
                # Ensure all years 2020-2024 are present (with 0 if missing)
                result = {}
                for year in ['2020', '2021', '2022', '2023', '2024']:
                    result[year] = float(year_amounts.get(year, 0.0))
                return result
            
            tract_summary['year_amounts'] = tract_summary[tract_id_col].apply(get_year_amounts)
            
            # Convert year_amounts dictionaries to JSON strings for proper serialization
            def convert_to_json(x):
                """Convert dict to JSON string, return other types as-is."""
                if isinstance(x, dict):
                    return json.dumps(x)
                return x
            tract_summary['year_amounts'] = tract_summary['year_amounts'].apply(convert_to_json)
        
        # Rename tract ID column to consistent name for downstream use
        if tract_id_col in tract_summary.columns:
            tract_summary = tract_summary.rename(columns={tract_id_col: 'tract_geoid'})
        elif 'tract_geoid' not in tract_summary.columns:
            # Create a tract_geoid from available data if it doesn't exist
            if 'geoid5' in tract_summary.columns and 'year' in tract_summary.columns:
                tract_summary['tract_geoid'] = tract_summary['geoid5'].astype(str) + '-' + tract_summary['year'].astype(str)
            else:
                tract_summary['tract_geoid'] = tract_summary.index.astype(str)
        
        # Add race classification based on county threshold
        tract_summary['is_majority_minority'] = (
            tract_summary['tract_minority_population_percent'] > county_minority_pct
        )
        
        print(f"DEBUG: Tract summary created: {len(tract_summary)} tracts")
        
        # Calculate quartiles for number of loans and amount of loans
        # These will be used for map layers
        if len(tract_summary) > 0:
            print(f"DEBUG: Calculating quartiles for {len(tract_summary)} tracts...")
            # Number of loans quartiles
            # Use qcut which handles duplicates better
            try:
                tract_summary['loan_count_quartile'] = pd.qcut(
                    tract_summary['loan_count'],
                    q=4,
                    labels=['Q1', 'Q2', 'Q3', 'Q4'],
                    duplicates='drop'
                )
            except (ValueError, TypeError):
                # If qcut fails (too many duplicates or all same value), assign based on rank
                unique_values = tract_summary['loan_count'].nunique()
                if unique_values > 1:
                    # Use rank to create quartiles
                    ranks = tract_summary['loan_count'].rank(method='min', pct=True)
                    tract_summary['loan_count_quartile'] = pd.cut(
                        ranks,
                        bins=[0, 0.25, 0.5, 0.75, 1.0],
                        labels=['Q1', 'Q2', 'Q3', 'Q4'],
                        include_lowest=True
                    )
                else:
                    # All values are the same, assign all to Q1
                    tract_summary['loan_count_quartile'] = 'Q1'
            
            # Amount of loans quartiles
            try:
                tract_summary['loan_amount_quartile'] = pd.qcut(
                    tract_summary['loan_amount'],
                    q=4,
                    labels=['Q1', 'Q2', 'Q3', 'Q4'],
                    duplicates='drop'
                )
            except (ValueError, TypeError):
                # If qcut fails (too many duplicates or all same value), assign based on rank
                unique_values = tract_summary['loan_amount'].nunique()
                if unique_values > 1:
                    # Use rank to create quartiles
                    ranks = tract_summary['loan_amount'].rank(method='min', pct=True)
                    tract_summary['loan_amount_quartile'] = pd.cut(
                        ranks,
                        bins=[0, 0.25, 0.5, 0.75, 1.0],
                        labels=['Q1', 'Q2', 'Q3', 'Q4'],
                        include_lowest=True
                    )
                else:
                    # All values are the same, assign all to Q1
                    tract_summary['loan_amount_quartile'] = 'Q1'
        else:
            tract_summary['loan_count_quartile'] = 'Q1'
            tract_summary['loan_amount_quartile'] = 'Q1'
        
        # Prepare summary table data
        summary_row = summary_df.iloc[0] if not summary_df.empty else {}
        # Calculate income category percentages for summary statistics (2024 only)
        # Filter to 2024 data (handle both string and int year values)
        if 'year' in aggregate_df.columns:
            aggregate_year_str = aggregate_df['year'].astype(str)
            summary_2024_df = aggregate_df[aggregate_year_str == '2024'].copy()
            print(f"DEBUG: Filtered aggregate to 2024: {len(summary_2024_df)} rows from {len(aggregate_df)} total")
            print(f"DEBUG: Year column type: {aggregate_df['year'].dtype}, unique values: {aggregate_df['year'].unique()}")
        else:
            summary_2024_df = aggregate_df.copy()
            print("DEBUG: No 'year' column in aggregate_df, using all data")
        
        print(f"DEBUG: Summary 2024 DF has {len(summary_2024_df)} rows")
        print(f"DEBUG: Summary 2024 DF columns: {summary_2024_df.columns.tolist() if not summary_2024_df.empty else 'empty'}")
        
        if not summary_2024_df.empty and 'income_level' in summary_2024_df.columns:
            print(f"DEBUG: income_level values: {summary_2024_df['income_level'].value_counts().to_dict()}")
            print(f"DEBUG: income_level nulls: {summary_2024_df['income_level'].isna().sum()}")
        
        summary_total_loans = safe_int(summary_2024_df.get('loan_count', pd.Series([0])).sum()) if not summary_2024_df.empty else 0
        summary_total_amount = float(summary_2024_df.get('loan_amount', pd.Series([0.0])).sum()) if not summary_2024_df.empty else 0.0
        
        # Extract amtsb_under_1m from aggregate data (2024 only)
        # Try both column name variations (amounts are in thousands)
        amtsb_under_1m = 0.0
        if not summary_2024_df.empty:
            # Check for both possible column names
            if 'amtsbrev_under_1m' in summary_2024_df.columns:
                amtsb_under_1m = float(summary_2024_df['amtsbrev_under_1m'].sum())
                print(f"DEBUG: Found amtsbrev_under_1m column, sum: {amtsb_under_1m}")
            elif 'amtsb_under_1m' in summary_2024_df.columns:
                amtsb_under_1m = float(summary_2024_df['amtsb_under_1m'].sum())
                print(f"DEBUG: Found amtsb_under_1m column, sum: {amtsb_under_1m}")
            else:
                print(f"DEBUG: WARNING - Neither amtsbrev_under_1m nor amtsb_under_1m found in columns: {summary_2024_df.columns.tolist()}")
                # Try to find any column with 'under' and '1m' in the name
                for col in summary_2024_df.columns:
                    if 'under' in col.lower() and '1m' in col.lower() and 'amt' in col.lower():
                        amtsb_under_1m = float(summary_2024_df[col].sum())
                        print(f"DEBUG: Found alternative column '{col}', sum: {amtsb_under_1m}")
                        break
        
        print(f"DEBUG: Summary total loans: {summary_total_loans}, total amount: {summary_total_amount}")
        
        summary_low_income_loans = 0
        summary_moderate_income_loans = 0
        summary_middle_income_loans = 0
        summary_upper_income_loans = 0
        summary_low_income_amount = 0.0
        summary_moderate_income_amount = 0.0
        summary_middle_income_amount = 0.0
        summary_upper_income_amount = 0.0
        
        if not summary_2024_df.empty:
            if 'income_level' in summary_2024_df.columns:
                # Handle NaN values in income_level
                low_mask = summary_2024_df['income_level'].fillna(0) == 1
                moderate_mask = summary_2024_df['income_level'].fillna(0) == 2
                middle_mask = summary_2024_df['income_level'].fillna(0) == 3
                upper_mask = summary_2024_df['income_level'].fillna(0) == 4
                
                summary_low_income_loans = int(summary_2024_df[low_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
                summary_moderate_income_loans = int(summary_2024_df[moderate_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
                summary_middle_income_loans = int(summary_2024_df[middle_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
                summary_upper_income_loans = int(summary_2024_df[upper_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
                
                summary_low_income_amount = float(summary_2024_df[low_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
                summary_moderate_income_amount = float(summary_2024_df[moderate_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
                summary_middle_income_amount = float(summary_2024_df[middle_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
                summary_upper_income_amount = float(summary_2024_df[upper_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
                
                print(f"DEBUG: Income breakdown - Low: {summary_low_income_loans}, Moderate: {summary_moderate_income_loans}, Middle: {summary_middle_income_loans}, Upper: {summary_upper_income_loans}")
            elif 'income_category' in summary_2024_df.columns:
                low_mask = summary_2024_df['income_category'].str.contains('Low Income', na=False)
                moderate_mask = summary_2024_df['income_category'].str.contains('Moderate Income', na=False)
                middle_mask = summary_2024_df['income_category'].str.contains('Middle Income', na=False)
                upper_mask = summary_2024_df['income_category'].str.contains('Upper Income', na=False)
                
                summary_low_income_loans = int(summary_2024_df[low_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
                summary_moderate_income_loans = int(summary_2024_df[moderate_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
                summary_middle_income_loans = int(summary_2024_df[middle_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
                summary_upper_income_loans = int(summary_2024_df[upper_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
                
                summary_low_income_amount = float(summary_2024_df[low_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
                summary_moderate_income_amount = float(summary_2024_df[moderate_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
                summary_middle_income_amount = float(summary_2024_df[middle_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
                summary_upper_income_amount = float(summary_2024_df[upper_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
        
        # Calculate percentage for amtsb_under_1m (for JavaScript fallback)
        pct_amount_sb_under_1m = 0.0
        if summary_total_amount > 0 and amtsb_under_1m > 0:
            pct_amount_sb_under_1m = (amtsb_under_1m / summary_total_amount * 100)

        # Calculate LMI tract data from aggregate data (since county summary returns 0)
        lmi_tract_loans_calculated = 0
        lmi_tract_amount_calculated = 0.0
        if not summary_2024_df.empty and 'is_lmi_tract' in summary_2024_df.columns:
            lmi_mask = (summary_2024_df['is_lmi_tract'] == 1) | (summary_2024_df['is_lmi_tract'] == True) | (summary_2024_df['is_lmi_tract'].astype(str) == '1')
            lmi_tract_loans_calculated = int(summary_2024_df[lmi_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
            lmi_tract_amount_calculated = float(summary_2024_df[lmi_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
            print(f"DEBUG: LMI tract data calculated from aggregate: loans={lmi_tract_loans_calculated}, amount={lmi_tract_amount_calculated}")
        elif not summary_2024_df.empty and 'income_level' in summary_2024_df.columns:
            # LMI = Low (1) + Moderate (2) income levels
            lmi_mask = summary_2024_df['income_level'].fillna(0).isin([1, 2])
            lmi_tract_loans_calculated = int(summary_2024_df[lmi_mask]['loan_count'].sum() if 'loan_count' in summary_2024_df.columns else 0)
            lmi_tract_amount_calculated = float(summary_2024_df[lmi_mask]['loan_amount'].sum() if 'loan_amount' in summary_2024_df.columns else 0.0)
            print(f"DEBUG: LMI tract data calculated from income_level: loans={lmi_tract_loans_calculated}, amount={lmi_tract_amount_calculated}")

        # Calculate LMI percentages
        pct_loans_to_lmi = (lmi_tract_loans_calculated / summary_total_loans * 100) if summary_total_loans > 0 else 0.0
        pct_dollars_to_lmi = (lmi_tract_amount_calculated / summary_total_amount * 100) if summary_total_amount > 0 else 0.0

        summary_table = {
            'total_loans': safe_int(summary_row.get('total_loans', 0)),
            'total_loan_amount': float(summary_row.get('total_loan_amount', 0) or summary_row.get('total_amount', 0)),
            'pct_loans_to_lmi_tracts': pct_loans_to_lmi,
            'pct_dollars_to_lmi_tracts': pct_dollars_to_lmi,
            'lmi_tract_loans': lmi_tract_loans_calculated,
            'lmi_tract_amount': lmi_tract_amount_calculated,
            'amtsb_under_1m': amtsb_under_1m,  # Use value extracted from aggregate data (in thousands)
            'pct_amount_sb_under_1m': pct_amount_sb_under_1m,  # Percentage for JavaScript fallback
            # Income category percentages
            'pct_loans_low_income': (summary_low_income_loans / summary_total_loans * 100) if summary_total_loans > 0 else 0.0,
            'pct_loans_moderate_income': (summary_moderate_income_loans / summary_total_loans * 100) if summary_total_loans > 0 else 0.0,
            'pct_loans_middle_income': (summary_middle_income_loans / summary_total_loans * 100) if summary_total_loans > 0 else 0.0,
            'pct_loans_upper_income': (summary_upper_income_loans / summary_total_loans * 100) if summary_total_loans > 0 else 0.0,
            'pct_amount_low_income': (summary_low_income_amount / summary_total_amount * 100) if summary_total_amount > 0 else 0.0,
            'pct_amount_moderate_income': (summary_moderate_income_amount / summary_total_amount * 100) if summary_total_amount > 0 else 0.0,
            'pct_amount_middle_income': (summary_middle_income_amount / summary_total_amount * 100) if summary_total_amount > 0 else 0.0,
            'pct_amount_upper_income': (summary_upper_income_amount / summary_total_amount * 100) if summary_total_amount > 0 else 0.0
        }
        
        # Check which income categories have census tracts in the county
        income_categories_exist = {
            'low_income': False,
            'moderate_income': False,
            'middle_income': False,
            'upper_income': False
        }
        
        if 'income_category' in tract_summary.columns:
            unique_categories = tract_summary['income_category'].dropna().unique()
            income_categories_exist['low_income'] = any('Low Income' in str(cat) for cat in unique_categories)
            income_categories_exist['moderate_income'] = any('Moderate Income' in str(cat) for cat in unique_categories)
            income_categories_exist['middle_income'] = any('Middle Income' in str(cat) for cat in unique_categories)
            income_categories_exist['upper_income'] = any('Upper Income' in str(cat) for cat in unique_categories)
        
        # Fetch historical census data for population demographics section
        historical_census_data = {}
        try:
            from justdata.shared.utils.census_historical_utils import get_census_data_for_geoids
            historical_census_data = get_census_data_for_geoids([geoid5])
            print(f"[BizSight] Fetched historical census data for {geoid5}: {len(historical_census_data)} counties")
        except Exception as e:
            print(f"[BizSight] Error fetching census data: {e}")
            import traceback
            traceback.print_exc()
            historical_census_data = {}
        
        # Prepare metadata (ai_insights_enabled will be set after AI analysis attempt)
        metadata = {
            'historical_census_data': historical_census_data,
            'county_name': county_name,
            'state_name': county_data.get('state_name', ''),
            'geoid5': geoid5,
            'years': years,
            'year_range': f"{min(years)}-{max(years)}",
            'county_minority_threshold': float(county_minority_pct),
            'total_tracts': len(tract_summary),
            'income_categories_exist': income_categories_exist,
            'generated_at': datetime.now().isoformat()
        }
        
        # Prepare report data
        report_data = {
            'tract_data': tract_summary,
            'aggregate_data': aggregate_df,
            'summary_stats': summary_df,
            'county_summary': county_summary_df,
            'comparison': comparison_df,
            'top_lenders': top_lenders_df
        }
        
        # Generate AI narratives
        if progress_tracker:
            progress_tracker.update_progress('generating_ai', 90, 'Generating AI narratives... Let the AI work its magic! ✨')
        
        # Initialize all AI insights keys with empty strings (ensures keys exist even if threads fail)
        ai_insights = {
            'county_summary_number_discussion': "",
            'county_summary_amount_discussion': "",
            'comparison_number_discussion': "",
            'comparison_amount_discussion': "",
            'top_lenders_number_discussion': "",
            'top_lenders_amount_discussion': "",
            'hhi_trends_discussion': ""
        }
        ai_insights_enabled = False  # Track whether AI insights are enabled
        
        # Check for API key before initializing (using unified environment system)
        from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
        from justdata.shared.utils.env_utils import is_local_development
        
        # Ensure unified environment is loaded (primary method)
        ensure_unified_env_loaded(verbose=False)
        config = get_unified_config(load_env=False, verbose=False)
        claude_api_key = config.get('CLAUDE_API_KEY')
        
        if not claude_api_key:
            print(f"[WARNING] CLAUDE_API_KEY not set - AI insights will not be generated")
            if is_local_development():
                print(f"[INFO] To enable AI insights locally, add CLAUDE_API_KEY to your .env file")
            else:
                print(f"[INFO] To enable AI insights, set CLAUDE_API_KEY environment variable in Render dashboard")
            print(f"[INFO] Skipping AI analysis and continuing with report generation...")
            ai_insights_enabled = False
        else:
            # Update environment variable with cleaned key
            import os
            os.environ['CLAUDE_API_KEY'] = claude_api_key
            ai_insights_enabled = True  # API key exists, AI should be enabled
        
        try:
            if not claude_api_key:
                raise Exception("No API key found for provider: claude")
            print("DEBUG: Initializing AI analyzer for key findings generation...", flush=True)
            ai_analyzer = BizSightAnalyzer()
            print("DEBUG: AI analyzer initialized successfully", flush=True)
            ai_insights_enabled = True  # Analyzer initialized successfully
            ai_data = {
                'county_name': county_name,
                'state_name': county_data.get('state_name', ''),
                'years': years,
                'county_summary_table': county_summary_df.to_dict('records') if not county_summary_df.empty else [],
                'comparison_table': comparison_df.to_dict('records') if not comparison_df.empty else [],
                'top_lenders_table': top_lenders_df.to_dict('records') if not top_lenders_df.empty else [],
                'hhi': {
                    'value': hhi_value,
                    'concentration_level': hhi_concentration,
                    'year': 2024
                } if hhi_value is not None else None
            }

            # Debug: Log data being passed to AI
            print(f"DEBUG: AI data being prepared:", flush=True)
            print(f"DEBUG:   county_name: {ai_data['county_name']}", flush=True)
            print(f"DEBUG:   years: {ai_data['years']}", flush=True)
            print(f"DEBUG:   county_summary_table length: {len(ai_data['county_summary_table'])}", flush=True)
            print(f"DEBUG:   comparison_table length: {len(ai_data['comparison_table'])}", flush=True)
            print(f"DEBUG:   top_lenders_table length: {len(ai_data['top_lenders_table'])}", flush=True)
            if ai_data['county_summary_table']:
                print(f"DEBUG:   county_summary_table first item keys: {list(ai_data['county_summary_table'][0].keys())}", flush=True)

            # Generate AI insights with timeout protection (using threading for Windows compatibility)
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def generate_county_number():
                try:
                    result = ai_analyzer.generate_county_summary_number_discussion(ai_data)
                    result_queue.put(('county_number', result))
                except Exception as e:
                    print(f"Warning: Failed to generate county summary number discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('county_number', ""))

            def generate_county_amount():
                try:
                    result = ai_analyzer.generate_county_summary_amount_discussion(ai_data)
                    result_queue.put(('county_amount', result))
                except Exception as e:
                    print(f"Warning: Failed to generate county summary amount discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('county_amount', ""))

            def generate_comparison_number():
                try:
                    result = ai_analyzer.generate_comparison_number_discussion(ai_data)
                    result_queue.put(('comparison_number', result))
                except Exception as e:
                    print(f"Warning: Failed to generate comparison number discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('comparison_number', ""))

            def generate_comparison_amount():
                try:
                    result = ai_analyzer.generate_comparison_amount_discussion(ai_data)
                    result_queue.put(('comparison_amount', result))
                except Exception as e:
                    print(f"Warning: Failed to generate comparison amount discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('comparison_amount', ""))

            def generate_lenders_number():
                try:
                    result = ai_analyzer.generate_top_lenders_number_discussion(ai_data)
                    result_queue.put(('lenders_number', result))
                except Exception as e:
                    print(f"Warning: Failed to generate top lenders number discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('lenders_number', ""))

            def generate_lenders_amount():
                try:
                    result = ai_analyzer.generate_top_lenders_amount_discussion(ai_data)
                    result_queue.put(('lenders_amount', result))
                except Exception as e:
                    print(f"Warning: Failed to generate top lenders amount discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('lenders_amount', ""))
            
            def generate_hhi_trends():
                try:
                    hhi_trends_data = {
                        'county_name': county_name,
                        'state_name': county_data.get('state_name', ''),
                        'hhi_by_year': hhi_by_year
                    }
                    result = ai_analyzer.generate_hhi_trends_discussion(hhi_trends_data)
                    result_queue.put(('hhi_trends', result))
                except Exception as e:
                    print(f"Warning: Failed to generate HHI trends discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('hhi_trends', ""))
            
            # Start all AI calls in separate threads (7 threads total: 6 table narratives + 1 HHI)
            county_number_thread = threading.Thread(target=generate_county_number, daemon=True)
            county_amount_thread = threading.Thread(target=generate_county_amount, daemon=True)
            comparison_number_thread = threading.Thread(target=generate_comparison_number, daemon=True)
            comparison_amount_thread = threading.Thread(target=generate_comparison_amount, daemon=True)
            lenders_number_thread = threading.Thread(target=generate_lenders_number, daemon=True)
            lenders_amount_thread = threading.Thread(target=generate_lenders_amount, daemon=True)
            hhi_trends_thread = threading.Thread(target=generate_hhi_trends, daemon=True)

            county_number_thread.start()
            county_amount_thread.start()
            comparison_number_thread.start()
            comparison_amount_thread.start()
            lenders_number_thread.start()
            lenders_amount_thread.start()
            hhi_trends_thread.start()

            # Wait for all with 30 second timeout each
            county_number_thread.join(timeout=30)
            county_amount_thread.join(timeout=30)
            comparison_number_thread.join(timeout=30)
            comparison_amount_thread.join(timeout=30)
            lenders_number_thread.join(timeout=30)
            lenders_amount_thread.join(timeout=30)
            hhi_trends_thread.join(timeout=30)
            
            # Collect results
            while not result_queue.empty():
                try:
                    key, value = result_queue.get_nowait()
                    if key == 'county_number':
                        ai_insights['county_summary_number_discussion'] = value
                    elif key == 'county_amount':
                        ai_insights['county_summary_amount_discussion'] = value
                    elif key == 'comparison_number':
                        ai_insights['comparison_number_discussion'] = value
                    elif key == 'comparison_amount':
                        ai_insights['comparison_amount_discussion'] = value
                    elif key == 'lenders_number':
                        ai_insights['top_lenders_number_discussion'] = value
                    elif key == 'lenders_amount':
                        ai_insights['top_lenders_amount_discussion'] = value
                    elif key == 'hhi_trends':
                        ai_insights['hhi_trends_discussion'] = value
                except queue.Empty:
                    break

            # If threads are still alive, they timed out
            if county_number_thread.is_alive():
                print("Warning: County summary number AI analysis timed out after 30 seconds")
            if county_amount_thread.is_alive():
                print("Warning: County summary amount AI analysis timed out after 30 seconds")
            if comparison_number_thread.is_alive():
                print("Warning: Comparison number AI analysis timed out after 30 seconds")
            if comparison_amount_thread.is_alive():
                print("Warning: Comparison amount AI analysis timed out after 30 seconds")
            if lenders_number_thread.is_alive():
                print("Warning: Top lenders number AI analysis timed out after 30 seconds")
            if lenders_amount_thread.is_alive():
                print("Warning: Top lenders amount AI analysis timed out after 30 seconds")
        except Exception as e:
            print(f"Warning: AI analysis failed completely: {e}")
            import traceback
            traceback.print_exc()
            ai_insights = {
                'county_summary_number_discussion': "",
                'county_summary_amount_discussion': "",
                'comparison_number_discussion': "",
                'comparison_amount_discussion': "",
                'top_lenders_number_discussion': "",
                'top_lenders_amount_discussion': "",
                'hhi_trends_discussion': ""
            }
            ai_insights_enabled = False  # Ensure flag is set when AI fails
        
        # Debug: Log AI insights status
        print(f"[DEBUG] AI insights status: enabled={ai_insights_enabled}, keys={list(ai_insights.keys())}", flush=True)
        for key, value in ai_insights.items():
            if value:
                print(f"[DEBUG] AI insight '{key}': length={len(str(value))}", flush=True)
            else:
                print(f"[DEBUG] AI insight '{key}': empty", flush=True)
        
        if progress_tracker:
            progress_tracker.update_progress('completed', 95, 'Finalizing report... Dotting the i\'s and crossing the t\'s! [OK]')
        
        # Add AI insights enabled flag to metadata
        metadata['ai_insights_enabled'] = ai_insights_enabled
        print(f"[DEBUG] Metadata ai_insights_enabled set to: {ai_insights_enabled}", flush=True)
        
        # Ensure HHI is always included (even if None)
        hhi_data = None
        if hhi_value is not None:
            hhi_data = {
                'value': hhi_value,
                'concentration_level': hhi_concentration,
                'year': 2024
            }
            print(f"DEBUG: HHI data included in result: {hhi_data}")
        else:
            print(f"DEBUG: WARNING - HHI value is None, not including in result")
            print(f"DEBUG: disclosure_df empty: {disclosure_df.empty}, top_lenders_df empty: {top_lenders_df.empty}")
            if not top_lenders_df.empty:
                print(f"DEBUG: top_lenders_df columns: {top_lenders_df.columns.tolist()}")
        
        result = {
            'success': True,
            'report_data': report_data,
            'metadata': metadata,
            'summary_table': summary_table,
            'tract_data_for_map': tract_summary.to_dict('records'),
            'county_summary_table': county_summary_df.to_dict('records') if not county_summary_df.empty else [],
            'comparison_table': comparison_df.to_dict('records') if not comparison_df.empty else [],
            'top_lenders_table': top_lenders_df.to_dict('records') if not top_lenders_df.empty else [],
            'hhi': hhi_data,
            'hhi_by_year': hhi_by_year,
            'ai_insights': ai_insights
        }
        
        # Debug: Log final AI insights in result
        print(f"[DEBUG] Final result ai_insights keys: {list(result.get('ai_insights', {}).keys())}", flush=True)
        print(f"[DEBUG] Final result metadata ai_insights_enabled: {result.get('metadata', {}).get('ai_insights_enabled')}", flush=True)
        
        print(f"\n{'='*80}")
        print(f"DEBUG: ========== FINAL RESULT SUMMARY ==========")
        print(f"{'='*80}")
        print(f"DEBUG: Final result keys: {list(result.keys())}")
        print(f"DEBUG: county_summary_table length: {len(result['county_summary_table'])}")
        print(f"DEBUG: county_summary_table empty: {county_summary_df.empty}")
        if result['county_summary_table']:
            print(f"DEBUG: county_summary_table first item: {result['county_summary_table'][0]}")
        print(f"DEBUG: comparison_table length: {len(result['comparison_table'])}")
        print(f"DEBUG: comparison_table type: {type(result['comparison_table'])}")
        if result['comparison_table']:
            print(f"DEBUG: comparison_table first item keys: {list(result['comparison_table'][0].keys())}")
            print(f"DEBUG: comparison_table first item: {result['comparison_table'][0]}")
        print(f"DEBUG: hhi value: {result['hhi']}")
        print(f"DEBUG: hhi type: {type(result['hhi'])}")
        if result['hhi']:
            print(f"DEBUG: hhi full data: {result['hhi']}")
        print(f"DEBUG: hhi_by_year length: {len(result['hhi_by_year'])}")
        if result['hhi_by_year']:
            print(f"DEBUG: hhi_by_year: {result['hhi_by_year']}")
        print(f"DEBUG: top_lenders_table length: {len(result['top_lenders_table'])}")
        print(f"{'='*80}\n")
        
        if progress_tracker:
            progress_tracker.complete(success=True)
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        if progress_tracker:
            progress_tracker.complete(success=False, error=error_msg)
        return {
            'success': False,
            'error': error_msg
        }

