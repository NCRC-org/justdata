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
REPO_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from justdata.apps.bizsight.config import BizSightConfig
from justdata.apps.bizsight.utils.bigquery_client import BigQueryClient
from justdata.apps.bizsight.utils.progress_tracker import ProgressTracker
from justdata.apps.bizsight.report_builder import create_top_lenders_table, create_county_summary_table, create_comparison_table, calculate_hhi_by_year, calculate_hhi_for_lenders
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
    
    # Parse years - if empty or None, automatically get last 5 years
    from .data_utils import get_last_5_years_sb
    
    if not years_str or not years_str.strip():
        # Automatically get last 5 years from SB disclosure data
        years = get_last_5_years_sb()
        print(f"✅ Automatically using last 5 SB disclosure years: {years}")
    else:
        years = [int(y.strip()) for y in years_str.split(",") if y.strip().isdigit()]
    
    # Validate year range
    if len(years) < BizSightConfig.MIN_YEARS:
        raise ValueError(f"Must select at least {BizSightConfig.MIN_YEARS} years")
    
    # Validate years are in range (relaxed for dynamic years)
    min_year = min(years)
    max_year = max(years)
    if min_year < 2018 or max_year > 2025:
        raise ValueError("Years must be between 2018 and 2025")
    
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
            progress_tracker.update_progress('initializing')
        
        # Parse parameters
        geoid5, years = parse_web_parameters(county_data, years_str)
        county_name = county_data.get('name', 'Unknown County')
        
        if progress_tracker:
            progress_tracker.update_progress('parsing_params', 5, 
                f'Analyzing {county_name} for years {min(years)}-{max(years)}')
        
        # Initialize BigQuery client
        if progress_tracker:
            progress_tracker.update_progress('connecting_db', 20, 'Connecting to BigQuery...')
        
        bq_client = BigQueryClient()
        
        # Fetch aggregate data with census demographics
        if progress_tracker:
            progress_tracker.update_progress('fetching_aggregate', 30, 
                'Fetching tract-level lending data with census demographics...')
        
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
            progress_tracker.update_progress('fetching_disclosure', 40, 
                'Fetching lender-level disclosure data...')
        
        print(f"DEBUG: Starting BigQuery disclosure query for GEOID5: {geoid5}, year: 2024")
        disclosure_query_2024 = bq_client.get_disclosure_data(geoid5, [2024])
        print(f"DEBUG: Disclosure query completed, converting to DataFrame...")
        disclosure_df = disclosure_query_2024.to_dataframe()
        print(f"DEBUG: Disclosure DataFrame created: {len(disclosure_df)} rows")
        
        # Also fetch disclosure data for all years for HHI by year calculation
        print(f"DEBUG: Starting BigQuery disclosure query for all years: {years}")
        disclosure_query_all = bq_client.get_disclosure_data(geoid5, years)
        print(f"DEBUG: Disclosure query for all years completed, converting to DataFrame...")
        disclosure_df_all_years = disclosure_query_all.to_dataframe()
        print(f"DEBUG: Disclosure DataFrame for all years created: {len(disclosure_df_all_years)} rows")
        
        # Build county summary table (Section 2) - 2018-2024
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
            progress_tracker.update_progress('fetching_benchmarks', 45, 
                'Loading state and national benchmarks...')
        
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
                import json
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
                import json
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
                import json
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
                        state_total = int(row.get('total_loans', 0))
                        state_amount = float(row.get('total_amount', 0.0))
                        state_num_under_100k = int(row.get('num_under_100k', 0))
                        state_num_100k_250k = int(row.get('num_100k_250k', 0))
                        state_num_250k_1m = int(row.get('num_250k_1m', 0))
                        state_amt_under_100k = float(row.get('amt_under_100k', 0.0))
                        state_amt_250k_1m = float(row.get('amt_250k_1m', 0.0))
                        state_numsb_under_1m = int(row.get('numsb_under_1m', 0))
                        state_amtsb_under_1m = float(row.get('amtsb_under_1m', 0.0))
                        state_lmi_loans = int(row.get('lmi_tract_loans', 0))
                        
                        # Income category breakdowns from BigQuery
                        state_low_income_loans = int(row.get('low_income_loans', 0))
                        state_moderate_income_loans = int(row.get('moderate_income_loans', 0))
                        state_middle_income_loans = int(row.get('middle_income_loans', 0))
                        state_upper_income_loans = int(row.get('upper_income_loans', 0))
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
                        national_total = int(row.get('total_loans', 0))
                        national_amount = float(row.get('total_amount', 0.0))
                        national_num_under_100k = int(row.get('num_under_100k', 0))
                        national_num_100k_250k = int(row.get('num_100k_250k', 0))
                        national_num_250k_1m = int(row.get('num_250k_1m', 0))
                        national_amt_under_100k = float(row.get('amt_under_100k', 0.0))
                        national_amt_250k_1m = float(row.get('amt_250k_1m', 0.0))
                        national_numsb_under_1m = int(row.get('numsb_under_1m', 0))
                        national_amtsb_under_1m = float(row.get('amtsb_under_1m', 0.0))
                        national_lmi_loans = int(row.get('lmi_tract_loans', 0))
                        
                        # Income category breakdowns from BigQuery
                        national_low_income_loans = int(row.get('low_income_loans', 0))
                        national_moderate_income_loans = int(row.get('moderate_income_loans', 0))
                        national_middle_income_loans = int(row.get('middle_income_loans', 0))
                        national_upper_income_loans = int(row.get('upper_income_loans', 0))
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
        
        # Get county 2018 data for % change calculations
        county_2018_data = None
        try:
            county_2018_df = pd.DataFrame()
            if 'year' in aggregate_df.columns:
                # Handle both string and int year values
                if aggregate_df['year'].dtype in ['int64', 'int32', 'int']:
                    county_2018_df = aggregate_df[aggregate_df['year'] == 2018].copy()
                else:
                    county_2018_df = aggregate_df[aggregate_df['year'].astype(str) == '2018'].copy()
            print(f"DEBUG: County 2018 data: {len(county_2018_df)} rows")
            if not county_2018_df.empty:
                county_2018_num_under_100k = int(county_2018_df.get('num_under_100k', pd.Series([0])).sum())
                county_2018_num_100k_250k = int(county_2018_df.get('num_100k_250k', pd.Series([0])).sum())
                county_2018_num_250k_1m = int(county_2018_df.get('num_250k_1m', pd.Series([0])).sum())
                county_2018_amt_under_100k = float(county_2018_df.get('amt_under_100k', pd.Series([0.0])).sum())
                county_2018_amt_250k_1m = float(county_2018_df.get('amt_250k_1m', pd.Series([0.0])).sum())
                numsb_col = 'numsbrev_under_1m' if 'numsbrev_under_1m' in county_2018_df.columns else 'numsb_under_1m'
                amtsb_col = 'amtsbrev_under_1m' if 'amtsbrev_under_1m' in county_2018_df.columns else 'amtsb_under_1m'
                county_2018_numsb_under_1m = int(county_2018_df.get(numsb_col, pd.Series([0])).sum())
                county_2018_amtsb_under_1m = float(county_2018_df.get(amtsb_col, pd.Series([0.0])).sum())
                
                if 'is_lmi_tract' in county_2018_df.columns:
                    lmi_mask = (county_2018_df['is_lmi_tract'] == 1) | (county_2018_df['is_lmi_tract'] == True) | (county_2018_df['is_lmi_tract'].astype(str) == '1')
                    county_2018_lmi_tract_loans = int(county_2018_df[lmi_mask].get('loan_count', pd.Series([0])).sum())
                else:
                    county_2018_lmi_tract_loans = 0
                
                # Calculate 2018 income category breakdowns
                county_2018_low_income_loans = 0
                county_2018_moderate_income_loans = 0
                county_2018_middle_income_loans = 0
                county_2018_upper_income_loans = 0
                county_2018_low_income_amount = 0.0
                county_2018_moderate_income_amount = 0.0
                county_2018_middle_income_amount = 0.0
                county_2018_upper_income_amount = 0.0
                
                if 'income_level' in county_2018_df.columns:
                    low_mask_2018 = county_2018_df['income_level'] == 1
                    moderate_mask_2018 = county_2018_df['income_level'] == 2
                    middle_mask_2018 = county_2018_df['income_level'] == 3
                    upper_mask_2018 = county_2018_df['income_level'] == 4
                    
                    county_2018_low_income_loans = int(county_2018_df[low_mask_2018].get('loan_count', pd.Series([0])).sum())
                    county_2018_moderate_income_loans = int(county_2018_df[moderate_mask_2018].get('loan_count', pd.Series([0])).sum())
                    county_2018_middle_income_loans = int(county_2018_df[middle_mask_2018].get('loan_count', pd.Series([0])).sum())
                    county_2018_upper_income_loans = int(county_2018_df[upper_mask_2018].get('loan_count', pd.Series([0])).sum())
                    
                    county_2018_low_income_amount = float(county_2018_df[low_mask_2018].get('loan_amount', pd.Series([0.0])).sum())
                    county_2018_moderate_income_amount = float(county_2018_df[moderate_mask_2018].get('loan_amount', pd.Series([0.0])).sum())
                    county_2018_middle_income_amount = float(county_2018_df[middle_mask_2018].get('loan_amount', pd.Series([0.0])).sum())
                    county_2018_upper_income_amount = float(county_2018_df[upper_mask_2018].get('loan_amount', pd.Series([0.0])).sum())
                elif 'income_category' in county_2018_df.columns:
                    low_mask_2018 = county_2018_df['income_category'].str.contains('Low Income', na=False)
                    moderate_mask_2018 = county_2018_df['income_category'].str.contains('Moderate Income', na=False)
                    middle_mask_2018 = county_2018_df['income_category'].str.contains('Middle Income', na=False)
                    upper_mask_2018 = county_2018_df['income_category'].str.contains('Upper Income', na=False)
                    
                    county_2018_low_income_loans = int(county_2018_df[low_mask_2018].get('loan_count', pd.Series([0])).sum())
                    county_2018_moderate_income_loans = int(county_2018_df[moderate_mask_2018].get('loan_count', pd.Series([0])).sum())
                    county_2018_middle_income_loans = int(county_2018_df[middle_mask_2018].get('loan_count', pd.Series([0])).sum())
                    county_2018_upper_income_loans = int(county_2018_df[upper_mask_2018].get('loan_count', pd.Series([0])).sum())
                    
                    county_2018_low_income_amount = float(county_2018_df[low_mask_2018].get('loan_amount', pd.Series([0.0])).sum())
                    county_2018_moderate_income_amount = float(county_2018_df[moderate_mask_2018].get('loan_amount', pd.Series([0.0])).sum())
                    county_2018_middle_income_amount = float(county_2018_df[middle_mask_2018].get('loan_amount', pd.Series([0.0])).sum())
                    county_2018_upper_income_amount = float(county_2018_df[upper_mask_2018].get('loan_amount', pd.Series([0.0])).sum())
                
                county_2018_total_loans = county_2018_num_under_100k + county_2018_num_100k_250k + county_2018_num_250k_1m
                county_2018_amt_100k_250k = float(county_2018_df.get('amt_100k_250k', pd.Series([0.0])).sum())
                county_2018_total_amount = county_2018_amt_under_100k + county_2018_amt_100k_250k + county_2018_amt_250k_1m
                
                county_2018_data = {
                    'total_loans': county_2018_total_loans,
                    'total_amount': county_2018_total_amount,
                    'num_under_100k': county_2018_num_under_100k,
                    'num_100k_250k': county_2018_num_100k_250k,
                    'num_250k_1m': county_2018_num_250k_1m,
                    'numsb_under_1m': county_2018_numsb_under_1m,
                    'low_income_loans': county_2018_low_income_loans,
                    'moderate_income_loans': county_2018_moderate_income_loans,
                    'middle_income_loans': county_2018_middle_income_loans,
                    'upper_income_loans': county_2018_upper_income_loans,
                    'low_income_amount': county_2018_low_income_amount,
                    'moderate_income_amount': county_2018_moderate_income_amount,
                    'middle_income_amount': county_2018_middle_income_amount,
                    'upper_income_amount': county_2018_upper_income_amount,
                    'lmi_tract_loans': county_2018_lmi_tract_loans,
                    'amt_under_100k': county_2018_amt_under_100k,
                    'amt_100k_250k': county_2018_amt_100k_250k,
                    'amt_250k_1m': county_2018_amt_250k_1m,
                    'amtsb_under_1m': county_2018_amtsb_under_1m
                }
                print(f"DEBUG: County 2018 data calculated: total_loans={county_2018_total_loans}, total_amount={county_2018_total_amount}")
            else:
                print(f"DEBUG: County 2018 data: county_2018_df is empty")
        except Exception as e:
            print(f"Warning: Failed to calculate county 2018 data: {e}")
            import traceback
            traceback.print_exc()
        
        # Build comparison table (Section 3) - County, State, National Comparison
        comparison_df = pd.DataFrame()
        if not aggregate_df.empty:
            print(f"DEBUG: Creating comparison table")
            print(f"DEBUG: State benchmarks available: {bool(state_benchmarks)}, keys: {list(state_benchmarks.keys()) if state_benchmarks else 'None'}")
            print(f"DEBUG: National benchmarks available: {bool(national_benchmarks)}, keys: {list(national_benchmarks.keys()) if national_benchmarks else 'None'}")
            print(f"DEBUG: County 2018 data available: {bool(county_2018_data)}")
            try:
                comparison_df = create_comparison_table(aggregate_df, state_benchmarks, national_benchmarks, county_2018_data)
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
            progress_tracker.update_progress('processing_data', 50, 
                'Calculating summary statistics...')
        
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
            progress_tracker.update_progress('building_report', 65, 
                'Preparing map data and visualizations...')
        
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
                # Ensure all years 2018-2024 are present (with 0 if missing)
                result = {}
                for year in ['2018', '2019', '2020', '2021', '2022', '2023', '2024']:
                    result[year] = float(year_amounts.get(year, 0.0))
                return result
            
            tract_summary['year_amounts'] = tract_summary[tract_id_col].apply(get_year_amounts)
            
            # Convert year_amounts dictionaries to JSON strings for proper serialization
            tract_summary['year_amounts'] = tract_summary['year_amounts'].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
        
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
        
        summary_total_loans = int(summary_2024_df.get('loan_count', pd.Series([0])).sum()) if not summary_2024_df.empty else 0
        summary_total_amount = float(summary_2024_df.get('loan_amount', pd.Series([0.0])).sum()) if not summary_2024_df.empty else 0.0
        
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
        
        summary_table = {
            'total_loans': int(summary_row.get('total_loans', 0)),
            'total_loan_amount': float(summary_row.get('total_loan_amount', 0)),
            'pct_loans_to_lmi_tracts': float(summary_row.get('pct_loans_to_lmi_tracts', 0)),
            'pct_dollars_to_lmi_tracts': float(summary_row.get('pct_dollars_to_lmi_tracts', 0)),
            'lmi_tract_loans': int(summary_row.get('lmi_tract_loans', 0)),
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
        
        # Prepare metadata
        metadata = {
            'county_name': county_name,
            'state_name': county_data.get('state_name', ''),
            'geoid5': geoid5,
            'years': years,
            'year_range': f"{min(years)}-{max(years)}",
            'county_minority_threshold': float(county_minority_pct),
            'total_tracts': len(tract_summary),
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
            progress_tracker.update_progress('generating_ai', 90, 'Generating AI narratives...')
        
        ai_insights = {}
        try:
            ai_analyzer = BizSightAnalyzer()
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
            
            # Generate AI insights with timeout protection (using threading for Windows compatibility)
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def generate_county():
                try:
                    result = ai_analyzer.generate_county_summary_discussion(ai_data)
                    result_queue.put(('county', result))
                except Exception as e:
                    print(f"Warning: Failed to generate county summary discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('county', ""))
            
            def generate_comparison():
                try:
                    result = ai_analyzer.generate_comparison_discussion(ai_data)
                    result_queue.put(('comparison', result))
                except Exception as e:
                    print(f"Warning: Failed to generate comparison discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('comparison', ""))
            
            def generate_lenders():
                try:
                    result = ai_analyzer.generate_top_lenders_discussion(ai_data)
                    result_queue.put(('lenders', result))
                except Exception as e:
                    print(f"Warning: Failed to generate top lenders discussion: {e}")
                    import traceback
                    traceback.print_exc()
                    result_queue.put(('lenders', ""))
            
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
            
            # Start all four AI calls in separate threads
            county_thread = threading.Thread(target=generate_county, daemon=True)
            comparison_thread = threading.Thread(target=generate_comparison, daemon=True)
            lenders_thread = threading.Thread(target=generate_lenders, daemon=True)
            hhi_trends_thread = threading.Thread(target=generate_hhi_trends, daemon=True)
            
            county_thread.start()
            comparison_thread.start()
            lenders_thread.start()
            hhi_trends_thread.start()
            
            # Wait for all with 30 second timeout each
            county_thread.join(timeout=30)
            comparison_thread.join(timeout=30)
            lenders_thread.join(timeout=30)
            hhi_trends_thread.join(timeout=30)
            
            # Collect results
            while not result_queue.empty():
                try:
                    key, value = result_queue.get_nowait()
                    if key == 'county':
                        ai_insights['county_summary_discussion'] = value
                    elif key == 'comparison':
                        ai_insights['comparison_discussion'] = value
                    elif key == 'lenders':
                        ai_insights['top_lenders_discussion'] = value
                    elif key == 'hhi_trends':
                        ai_insights['hhi_trends_discussion'] = value
                except queue.Empty:
                    break
            
            # If threads are still alive, they timed out
            if county_thread.is_alive():
                print("Warning: County summary AI analysis timed out after 30 seconds")
            if comparison_thread.is_alive():
                print("Warning: Comparison AI analysis timed out after 30 seconds")
            if lenders_thread.is_alive():
                print("Warning: Top lenders AI analysis timed out after 30 seconds")
        except Exception as e:
            print(f"Warning: AI analysis failed completely: {e}")
            import traceback
            traceback.print_exc()
            ai_insights = {
                'county_summary_discussion': "",
                'comparison_discussion': "",
                'top_lenders_discussion': ""
            }
        
        # Save Excel report (like LendSight does)
        if progress_tracker:
            progress_tracker.update_progress('saving_excel', 90, 'Saving Excel report...')
        
        try:
            from apps.bizsight.excel_export import save_bizsight_excel_report
            
            excel_path = os.path.join(BizSightConfig.OUTPUT_DIR, f'bizsight_analysis_{job_id}.xlsx')
            os.makedirs(os.path.dirname(excel_path), exist_ok=True)
            # Pass the full result dict (which will become analysis_result) instead of just report_data
            excel_result = {
                'county_summary_table': county_summary_df.to_dict('records') if not county_summary_df.empty else [],
                'comparison_table': comparison_df.to_dict('records') if not comparison_df.empty else [],
                'top_lenders_table': top_lenders_df.to_dict('records') if not top_lenders_df.empty else [],
                'hhi_by_year': hhi_by_year,
                'report_data': report_data
            }
            save_bizsight_excel_report(excel_result, excel_path, metadata=metadata)
            print(f"Excel report saved: {excel_path}")
        except Exception as e:
            print(f"Warning: Failed to save Excel report: {e}")
            import traceback
            traceback.print_exc()
        
        if progress_tracker:
            progress_tracker.update_progress('finalizing', 95, 'Finalizing report...')
        
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

