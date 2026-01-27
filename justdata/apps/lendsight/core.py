#!/usr/bin/env python3
"""
LendSight core analysis logic - Mortgage lending analysis.
Similar structure to BranchSight but for HMDA mortgage data.
"""

import os
import pandas as pd
from typing import Dict, List
from datetime import datetime
from justdata.apps.lendsight.config import OUTPUT_DIR, PROJECT_ID
from justdata.apps.lendsight.data_utils import find_exact_county_match, execute_mortgage_query
from justdata.apps.lendsight.mortgage_report_builder import build_mortgage_report, save_mortgage_excel_report
from justdata.apps.lendsight.hud_processor import get_hud_data_for_counties
from justdata.apps.lendsight.version import __version__


def parse_web_parameters(counties_str: str, years_str: str, selection_type: str = 'county', 
                        state_code: str = None, metro_code: str = None) -> tuple:
    """Parse parameters from web interface.
    
    Args:
        counties_str: Semicolon-separated county names (for county selection)
        years_str: Comma-separated years or "all"
        selection_type: 'county', 'state', or 'metro'
        state_code: Two-digit state FIPS code (for state selection)
        metro_code: CBSA code (for metro selection)
    
    Returns:
        Tuple of (counties_list, years_list)
    """
    from justdata.apps.lendsight.data_utils import expand_state_to_counties, expand_metro_to_counties
    
    # Parse years
    # Handle empty string, "auto", or "auto (last 5)" - default to last 5 years
    if not years_str or years_str.strip() == "" or years_str.lower().startswith("auto"):
        years = list(range(2020, 2025))  # HMDA data 2020-2024 (last 5 years)
    elif years_str.lower() == "all":
        years = list(range(2020, 2025))  # HMDA data 2020-2024
    else:
        years = [int(y.strip()) for y in years_str.split(",") if y.strip().isdigit()]
        # If parsing failed, default to last 5 years
        if not years:
            years = list(range(2020, 2025))
    
    # Parse counties based on selection type
    if selection_type == 'state' and state_code:
        # Expand state to counties
        counties = expand_state_to_counties(state_code)
        if not counties:
            raise ValueError(f"No counties found for state code: {state_code}")
    elif selection_type == 'metro' and metro_code:
        # Expand metro area to counties
        counties = expand_metro_to_counties(metro_code)
        if not counties:
            raise ValueError(f"No counties found for metro code: {metro_code}")
    else:
        # Default: parse counties from string
        counties = [c.strip() for c in counties_str.split(";") if c.strip()]
    
    return counties, years


def load_sql_template() -> str:
    """Load the SQL query template from file."""
    sql_template_path = os.path.join(
        os.path.dirname(__file__), 
        'sql_templates', 
        'mortgage_report.sql'
    )
    try:
        with open(sql_template_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise Exception(f"SQL template not found at {sql_template_path}")


def run_analysis(counties_str: str, years_str: str, run_id: str = None, progress_tracker=None, 
                 selection_type: str = 'county', state_code: str = None, metro_code: str = None,
                 loan_purpose: list = None, counties_with_fips: list = None) -> Dict:
    """
    Run mortgage analysis for web interface.
    
    Args:
        counties_str: Semicolon-separated county names (or empty if using state/metro selection)
        years_str: Comma-separated years or "all"
        run_id: Optional run ID for tracking
        progress_tracker: Optional progress tracker for real-time updates
        selection_type: 'county', 'state', or 'metro'
        state_code: Two-digit state FIPS code (for state selection)
        metro_code: CBSA code (for metro selection)
    
    Returns:
        Dictionary with success status and results
    """
    try:
        # Initialize progress
        if progress_tracker:
            progress_tracker.update_progress('initializing', 0, 'Initializing analysis... Getting ready to crunch some numbers! 🚀')
        
        # Parse parameters with selection context
        counties, years = parse_web_parameters(counties_str, years_str, selection_type, state_code, metro_code)
        
        if progress_tracker:
            progress_tracker.update_progress('preparing_data', 5, f'Preparing data for {len(counties)} counties... Unpacking the data puzzle! 🧩')
        
        if not counties:
            return {'success': False, 'error': 'No counties provided'}
        
        if not years:
            return {'success': False, 'error': 'No years provided'}
        
        # Clarify county selections
        if progress_tracker:
            progress_tracker.update_progress('preparing_data', 10, 'Matching counties... Making sure we have the right places! 📍')
        
        clarified_counties = []
        total_counties = len(counties)
        for idx, county in enumerate(counties, 1):
            try:
                if progress_tracker:
                    progress_tracker.update_progress('preparing_data', 
                        int(10 + (idx / total_counties) * 5),
                        f'Matching county {idx}/{total_counties}: {county}... Almost there! 📍')
                
                print(f"Matching county {idx}/{total_counties}: {county}")
                matches = find_exact_county_match(county)
                if not matches:
                    print(f"Warning: No matches found for {county}, using input as-is")
                    clarified_counties.append(county)
                else:
                    clarified_counties.append(matches[0])
                    print(f"Using county: {matches[0]}")
            except Exception as e:
                print(f"Error matching county {county}: {e}, using input as-is")
                clarified_counties.append(county)
        
        # Load SQL template
        if progress_tracker:
            progress_tracker.update_progress('connecting_db', 15, 'Connecting to BigQuery... Time to tap into that data goldmine! 💎')
        
        sql_template = load_sql_template()
        
        # Execute BigQuery queries
        if progress_tracker:
            progress_tracker.update_progress('fetching_data', 20, 'Fetching mortgage data... Digging deep for insights! ⛏️')
        
        all_results = []
        total_queries = len(clarified_counties) * len(years)
        query_index = 0
        
        print(f"\n[DEBUG] Starting data fetch: {total_queries} queries ({len(clarified_counties)} counties × {len(years)} years)")
        
        for county in clarified_counties:
            for year in years:
                try:
                    print(f"  [DEBUG] Querying {county} for year {year} with loan_purpose={loan_purpose}...")
                    print(f"  [DEBUG] About to call execute_mortgage_query...")
                    if progress_tracker:
                        progress_tracker.update_progress('fetching_data', 
                            20 + int((query_index / total_queries) * 25),
                            f'Fetching data: {county} ({year})... Who\'s lending where? Let\'s find out! 🏦')
                    
                    print(f"  [DEBUG] Calling execute_mortgage_query now...")
                    results = execute_mortgage_query(sql_template, county, year, loan_purpose)
                    print(f"  [DEBUG] execute_mortgage_query returned, got {len(results) if results else 0} results")
                    all_results.extend(results)
                    print(f"    [OK] Found {len(results)} records")
                    
                    # Update progress
                    query_index += 1
                    if progress_tracker:
                        progress_tracker.update_query_progress(query_index, total_queries)
                        
                except Exception as e:
                    print(f"    [ERROR] Error querying {county} {year}: {e}")
                    import traceback
                    traceback.print_exc()
                    query_index += 1
                    # Continue with other queries even if one fails
                    continue
        
        print(f"[DEBUG] Data fetch complete: {len(all_results)} total records", flush=True)
        
        if not all_results:
            print(f"[ERROR] No data found for the specified parameters", flush=True)
            return {'success': False, 'error': 'No data found for the specified parameters'}
        
        print(f"[DEBUG] Moving to Census data fetch...", flush=True)
        print(f"[DEBUG] counties_with_fips provided: {counties_with_fips is not None}, length: {len(counties_with_fips) if counties_with_fips else 0}", flush=True)
        print(f"[DEBUG] state_code: {state_code}", flush=True)
        # Fetch Census data FIRST (before building report) so it can be used in AI analysis
        if progress_tracker:
            print(f"[DEBUG] Updating progress to fetching_data", flush=True)
            progress_tracker.update_progress('fetching_data', 45, 'Fetching Census demographic data... Getting the full picture! 📊')
        
        census_data = {}
        try:
            print(f"[DEBUG] Importing census_utils...", flush=True)
            import sys
            sys.stdout.flush()
            from justdata.apps.lendsight.census_utils import get_census_data_for_multiple_counties
            import os
            # Use unified environment system (primary method)
            from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
            
            # Ensure unified environment is loaded (already loaded in app.py, but ensure it's loaded here too)
            ensure_unified_env_loaded(verbose=False)
            config = get_unified_config(load_env=False, verbose=False)
            api_key = config.get('CENSUS_API_KEY')
            print(f"\n[DEBUG] Fetching Census demographic data for context...", flush=True)
            print(f"  [DEBUG] Checking for CENSUS_API_KEY in environment...", flush=True)
            print(f"  [DEBUG] CENSUS_API_KEY from os.getenv: {api_key is not None}", flush=True)
            if not api_key:
                print(f"  [WARNING] CENSUS_API_KEY not set - Census data will not be available", flush=True)
                print(f"  [INFO] To enable Census data, set CENSUS_API_KEY environment variable in Render dashboard", flush=True)
                print(f"  [INFO] Get a free API key from: https://api.census.gov/data/key_signup.html", flush=True)
                # Debug: Show all environment variables that contain 'CENSUS'
                env_vars_with_census = [k for k in os.environ.keys() if 'CENSUS' in k.upper()]
                if env_vars_with_census:
                    print(f"  [DEBUG] Found these related env vars: {env_vars_with_census}", flush=True)
                else:
                    print(f"  [DEBUG] No environment variables found containing 'CENSUS'", flush=True)
            else:
                print(f"  [INFO] CENSUS_API_KEY is set (length: {len(api_key)})", flush=True)
            print(f"[DEBUG] Calling get_census_data_for_multiple_counties with {len(clarified_counties)} counties...", flush=True)
            print(f"[DEBUG] This may take 30-60 seconds as it makes multiple API calls per county...", flush=True)
            sys.stdout.flush()
            if progress_tracker:
                progress_tracker.update_progress('fetching_data', 50, f'Fetching Census data for {len(clarified_counties)} counties... This may take a minute, but it\'s worth it! ⏳')
            
            # Use FIPS codes if provided, otherwise look them up
            if counties_with_fips and len(counties_with_fips) > 0:
                # FIPS codes already provided from frontend
                print(f"  [INFO] Using FIPS codes provided from frontend for {len(counties_with_fips)} counties", flush=True)
                print(f"  [DEBUG] Sample county data: {counties_with_fips[0] if counties_with_fips else 'None'}", flush=True)
                # Extract state_code from first county if not provided
                if not state_code and counties_with_fips:
                    first_county = counties_with_fips[0]
                    if isinstance(first_county, dict):
                        state_code = first_county.get('state_fips') or (first_county.get('geoid5', '')[:2] if first_county.get('geoid5') else None)
                        print(f"  [DEBUG] Extracted state_code from county data: {state_code}", flush=True)
                if not state_code:
                    print(f"  [ERROR] state_code is required but not provided and cannot be extracted from county data", flush=True)
                    census_data = {}
                else:
                    print(f"  [INFO] Starting Census API calls with state_code={state_code} (this may take 1-2 minutes)...", flush=True)
                import sys
                sys.stdout.flush()
                census_data = get_census_data_for_multiple_counties(counties_with_fips, state_code, api_key, progress_tracker)
                print(f"  [INFO] Census API calls completed", flush=True)
            else:
                # Fallback: Look up FIPS codes from BigQuery
                print(f"  [INFO] Looking up FIPS codes from BigQuery for {len(clarified_counties)} counties...", flush=True)
                from justdata.shared.utils.bigquery_client import get_bigquery_client
                from justdata.apps.lendsight.config import PROJECT_ID
                counties_with_fips_lookup = []
                client = get_bigquery_client(PROJECT_ID)
                
                for county_name in clarified_counties:
                    try:
                        from justdata.shared.utils.bigquery_client import escape_sql_string
                        escaped_county = escape_sql_string(county_name)
                        query = f"""
                        SELECT DISTINCT county_state, geoid5
                        FROM geo.cbsa_to_county
                        WHERE county_state = '{escaped_county}'
                        LIMIT 1
                        """
                        query_job = client.query(query)
                        results = list(query_job.result())
                        if results and results[0].geoid5:
                            geoid5 = str(results[0].geoid5).zfill(5)
                            counties_with_fips_lookup.append({
                                'name': county_name,
                                'geoid5': geoid5,
                                'state_fips': geoid5[:2],
                                'county_fips': geoid5[2:]
                            })
                        else:
                            print(f"  [WARNING] Could not find geoid5 for {county_name}, skipping Census data...")
                    except Exception as e:
                        print(f"  [WARNING] Error looking up FIPS for {county_name}: {e}")
                
                if counties_with_fips_lookup:
                    # Extract state_code from first county if not provided
                    if not state_code and counties_with_fips_lookup:
                        first_county = counties_with_fips_lookup[0]
                        state_code = first_county.get('state_fips')
                        print(f"  [DEBUG] Extracted state_code from lookup: {state_code}", flush=True)
                    if not state_code:
                        print(f"  [ERROR] state_code is required but not provided and cannot be extracted", flush=True)
                        census_data = {}
                    else:
                        census_data = get_census_data_for_multiple_counties(counties_with_fips_lookup, state_code, api_key, progress_tracker)
                else:
                    print(f"  [WARNING] No counties with valid FIPS codes found, skipping Census data...", flush=True)
                    census_data = {}
            print(f"[DEBUG] get_census_data_for_multiple_counties returned successfully", flush=True)
            if census_data and len(census_data) > 0:
                print(f"  [OK] Retrieved Census data for {len(census_data)} counties")
                print(f"  [DEBUG] Census data keys: {list(census_data.keys())}")
                # Debug: print sample data
                for county, data in list(census_data.items())[:1]:  # Print first county only
                    print(f"  [DEBUG] Sample Census data for {county}:")
                    print(f"    - Data keys: {list(data.keys())}")
                    
                    # Check for new structure (time_periods) or old structure (demographics)
                    if 'time_periods' in data:
                        time_periods = data.get('time_periods', {})
                        print(f"    - Time periods: {list(time_periods.keys())}")
                        for period_key, period_data in time_periods.items():
                            demographics = period_data.get('demographics', {})
                            print(f"      - {period_key}: {period_data.get('year', 'N/A')}")
                            print(f"        Total Population: {demographics.get('total_population', 'N/A')}")
                            print(f"        White: {demographics.get('white_percentage', 0):.1f}%")
                            print(f"        Black: {demographics.get('black_percentage', 0):.1f}%")
                            print(f"        Hispanic: {demographics.get('hispanic_percentage', 0):.1f}%")
                    elif 'demographics' in data:
                        demographics = data.get('demographics', {})
                        print(f"    - Using legacy demographics format")
                        print(f"    - Demographics keys: {list(demographics.keys()) if demographics else 'None'}")
                        print(f"    - Total Population: {demographics.get('total_population', 'N/A')}")
                        print(f"    - Hispanic: {demographics.get('hispanic_percentage', 0):.1f}%")
                        print(f"    - Black: {demographics.get('black_percentage', 0):.1f}%")
                        print(f"    - White: {demographics.get('white_percentage', 0):.1f}%")
                        print(f"    - Data year: {data.get('data_year', 'N/A')}")
            else:
                print(f"  [WARNING] No Census data retrieved (returned empty dict or None)")
                print(f"  [DEBUG] Census data type: {type(census_data)}, value: {census_data}")
                print(f"  [DEBUG] API key was provided: {api_key is not None}")
                if api_key:
                    print(f"  [DEBUG] API key length: {len(api_key)}")
                else:
                    print(f"  [ERROR] CENSUS_API_KEY is missing - Census data cannot be fetched")
                census_data = {}  # Ensure it's an empty dict, not None
        except Exception as census_error:
            print(f"  [WARNING] Error fetching Census data: {census_error}")
            import traceback
            traceback.print_exc()
            census_data = {}
        
        print(f"[DEBUG] Census data fetch complete, moving to report building...", flush=True)
        # Build report (pass census_data so it can be included in tables)
        if progress_tracker:
            print(f"[DEBUG] Updating progress to building_report", flush=True)
            progress_tracker.update_progress('building_report', 60, 'Processing data and building report... Making it look pretty! 🎨')
        
        # Load HUD data for income distribution
        if progress_tracker:
            progress_tracker.update_progress('building_report', 62, 'Loading HUD income distribution data... Setting the bar for comparison! 📈')

        # Extract unique GEOIDs from either counties_with_fips or BigQuery results
        geoids = []

        # First, try to get GEOIDs from counties_with_fips (frontend-provided FIPS data)
        if counties_with_fips:
            for county_data in counties_with_fips:
                if isinstance(county_data, dict) and county_data.get('geoid5'):
                    geoids.append(str(county_data['geoid5']).zfill(5))
            print(f"[DEBUG] Extracted {len(geoids)} GEOIDs from counties_with_fips: {geoids}")

        # If no GEOIDs from counties_with_fips, fall back to BigQuery results
        if not geoids and all_results:
            county_df = pd.DataFrame(all_results)
            if 'geoid5' in county_df.columns:
                raw_geoids = county_df['geoid5'].unique().tolist()
                # Convert to strings with zero-padding
                geoids = [str(g).zfill(5) for g in raw_geoids if g is not None]
                print(f"[DEBUG] Extracted {len(geoids)} GEOIDs from BigQuery results: {geoids[:5]}...")

        # Remove duplicates
        geoids = list(set(geoids))
        print(f"[DEBUG] Final unique GEOIDs for HUD lookup: {geoids}")

        # Load HUD data for these GEOIDs
        hud_data = get_hud_data_for_counties(geoids) if geoids else {}
        print(f"[DEBUG] HUD data loaded for {len(hud_data)} counties")
        
        print(f"\n[DEBUG] Building report with {len(all_results)} records...", flush=True)
        if progress_tracker:
            progress_tracker.update_progress('building_report', 65, f'Processing {len(all_results):,} records... This may take a moment for large datasets! ⏳')
        report_data = build_mortgage_report(all_results, clarified_counties, years, census_data=census_data, hud_data=hud_data, progress_tracker=progress_tracker)
        print(f"[DEBUG] Report building complete")
        
        # Add census data to report_data
        report_data['census_data'] = census_data
        
        # Note: Excel report is now generated on-demand when user requests download
        # This improves performance and prevents timeouts during analysis
        
        # Generate AI insights (optional if API key is configured)
        ai_insights = {}
        try:
            from justdata.apps.lendsight.analysis import LendSightAnalyzer
            from justdata.shared.analysis.ai_provider import convert_numpy_types
            
            # Prepare data for AI analysis
            county_df = report_data.get('by_county', pd.DataFrame())
            hhi_data = report_data.get('hhi', {})
            raw_df = report_data.get('raw_data', pd.DataFrame())
            
            # Calculate final year's unique origination count
            final_year_origination_count = 0
            if not raw_df.empty and 'year' in raw_df.columns and 'total_originations' in raw_df.columns:
                final_year = max(years)
                final_year_df = raw_df[raw_df['year'] == final_year]
                final_year_origination_count = int(final_year_df['total_originations'].sum())
            
            # Prepare table data for AI analysis
            # Note: Converting DataFrames to dicts can be slow for large datasets
            # We optimize by only converting what's needed and using efficient methods
            if progress_tracker:
                progress_tracker.update_progress('generating_ai', 88, 'Preparing data for AI analysis... Almost there! 🤖')
            
            by_lender_df = report_data.get('by_lender', pd.DataFrame())
            by_lender_data = convert_numpy_types(by_lender_df.to_dict('records') if not by_lender_df.empty else [])
            
            # Prepare demographic overview data
            demographic_df = report_data.get('demographic_overview', pd.DataFrame())
            demographic_data = convert_numpy_types(demographic_df.to_dict('records') if not demographic_df.empty else [])

            # Prepare top lenders detailed data
            top_lenders_detailed_df = report_data.get('top_lenders_detailed', pd.DataFrame())
            top_lenders_detailed_data = convert_numpy_types(top_lenders_detailed_df.to_dict('records') if not top_lenders_detailed_df.empty else [])
            
            # Prepare market concentration data
            market_concentration_data = report_data.get('market_concentration', [])
            if isinstance(market_concentration_data, pd.DataFrame):
                market_concentration_data = convert_numpy_types(market_concentration_data.to_dict('records') if not market_concentration_data.empty else [])
            elif isinstance(market_concentration_data, list):
                market_concentration_data = convert_numpy_types(market_concentration_data)
            else:
                market_concentration_data = []

            # Prepare individual Section 2 table data for AI analysis
            income_borrowers_df = report_data.get('income_borrowers', pd.DataFrame())
            income_borrowers_data = convert_numpy_types(income_borrowers_df.to_dict('records') if not income_borrowers_df.empty else [])

            income_tracts_df = report_data.get('income_tracts', pd.DataFrame())
            income_tracts_data = convert_numpy_types(income_tracts_df.to_dict('records') if not income_tracts_df.empty else [])

            minority_tracts_df = report_data.get('minority_tracts', pd.DataFrame())
            minority_tracts_data = convert_numpy_types(minority_tracts_df.to_dict('records') if not minority_tracts_df.empty else [])
            
            # Safely get top lenders list
            top_lenders_list = []
            if not by_lender_df.empty and 'Lender Name' in by_lender_df.columns:
                top_lenders_list = by_lender_df.head(5)['Lender Name'].tolist()
            
            # Validate data before passing to AI
            if not clarified_counties:
                raise ValueError("No counties available for AI analysis")
            if not years:
                raise ValueError("No years available for AI analysis")
            
            # Ensure counties is a list of strings
            counties_list = [str(c) for c in clarified_counties] if clarified_counties else []
            
            ai_data = {
                'counties': counties_list,
                'years': years,
                'final_year': max(years) if years else None,
                'final_year_origination_count': final_year_origination_count,
                'top_lenders': top_lenders_list,
                'loan_purpose': loan_purpose if loan_purpose else ['purchase', 'refinance', 'equity'],  # Include loan purpose in AI data
                'summary_data': convert_numpy_types(report_data.get('summary', {}).to_dict('records') if not report_data.get('summary', pd.DataFrame()).empty else []),
                'demographic_overview': demographic_data,
                'income_borrowers': income_borrowers_data,  # Section 2 Table 1: Lending to Income Borrowers
                'income_tracts': income_tracts_data,  # Section 2 Table 2: Lending to Census Tracts by Income
                'minority_tracts': minority_tracts_data,  # Section 2 Table 3: Lending to Census Tracts by Minority Pop
                'top_lenders_detailed': top_lenders_detailed_data,
                'market_concentration': market_concentration_data,
                'trends_data': convert_numpy_types(report_data.get('trends', {}).to_dict('records') if not report_data.get('trends', pd.DataFrame()).empty else []),
                'hhi': convert_numpy_types(hhi_data),
                'county_data': convert_numpy_types(county_df.to_dict('records') if not county_df.empty else []),
                'by_lender': by_lender_data,
                'census_data': convert_numpy_types(census_data)  # Include Census data for context
            }

            # Debug: Log what data is being passed to AI
            print(f"[DEBUG] AI data summary:")
            print(f"  - demographic_overview: {len(demographic_data)} records")
            print(f"  - income_borrowers: {len(income_borrowers_data)} records")
            print(f"  - income_tracts: {len(income_tracts_data)} records")
            print(f"  - minority_tracts: {len(minority_tracts_data)} records")
            print(f"  - top_lenders_detailed: {len(top_lenders_detailed_data)} records")
            print(f"  - census_data: {len(census_data) if census_data else 0} counties")

            # Validate that we have data before calling AI
            if len(demographic_data) == 0:
                print(f"[WARNING] demographic_overview is empty - AI may return empty discussion")
            if len(income_borrowers_data) == 0:
                print(f"[WARNING] income_borrowers is empty - AI may return empty discussion")
            if len(top_lenders_detailed_data) == 0:
                print(f"[WARNING] top_lenders_detailed is empty - AI may return empty discussion")
            
            if progress_tracker:
                progress_tracker.update_progress('generating_ai', 90, 'Generating AI narratives... Let the AI work its magic! ✨')
            
            # Initialize analyzer
            print(f"Initializing AI analyzer...")
            print(f"Counties for AI: {clarified_counties}")
            print(f"Years for AI: {years}")
            print(f"Final year origination count: {final_year_origination_count}")
            
            # Check for API key before initializing (using unified environment system)
            from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
            from justdata.shared.utils.env_utils import is_local_development
            
            # Ensure unified environment is loaded (primary method)
            ensure_unified_env_loaded(verbose=False)
            config = get_unified_config(load_env=False, verbose=False)
            claude_api_key = config.get('CLAUDE_API_KEY')
            analyzer = None
            ai_insights = {}
            ai_insights_enabled = False  # Track whether AI insights are enabled
            
            # Debug: Show what we found
            print(f"[DEBUG] Checking for Claude API key...")
            print(f"  CLAUDE_API_KEY from os.getenv: {os.getenv('CLAUDE_API_KEY') is not None}")
            print(f"  ANTHROPIC_API_KEY from os.getenv: {os.getenv('ANTHROPIC_API_KEY') is not None}")
            print(f"  Final claude_api_key result: {claude_api_key is not None}")
            
            if not claude_api_key:
                print(f"[WARNING] CLAUDE_API_KEY not set - AI insights will not be generated")
                print(f"[INFO] To enable AI insights, set CLAUDE_API_KEY environment variable in Render dashboard")
                print(f"[INFO] Skipping AI analysis and continuing with report generation...")
                ai_insights_enabled = False
            else:
                # Update environment variable with cleaned key
                os.environ['CLAUDE_API_KEY'] = claude_api_key
                ai_insights_enabled = True  # API key exists, AI should be enabled
                print(f"[INFO] CLAUDE_API_KEY is set (length: {len(claude_api_key)})")
            try:
                analyzer = LendSightAnalyzer()
                print("AI analyzer initialized successfully")
                ai_insights_enabled = True  # Analyzer initialized successfully
            except Exception as init_error:
                print(f"Failed to initialize AI analyzer: {init_error}")
                import traceback
                traceback.print_exc()
                print(f"[WARNING] AI analyzer initialization failed, continuing without AI insights")
                analyzer = None
                ai_insights_enabled = False  # Analyzer failed to initialize
            
            # Generate AI insights with progress tracking (only if analyzer was successfully initialized)
            # NOTE: demographic_overview_intro, income_neighborhood_intro, and top_lenders_detailed_intro
            # are hardcoded in JavaScript, so we don't need AI calls for those.
            
            if analyzer:
                # Combined call 1: All table discussions (reduces 3 calls to 1)
                if progress_tracker:
                    progress_tracker.update_ai_progress(1, 3, 'Table Discussions (Combined)')
                print("  Generating all table discussions (combined call)...")
                try:
                    discussions = analyzer.generate_all_table_discussions(ai_data)
                    print(f"  [DEBUG] Discussions returned: {list(discussions.keys())}")
                    
                    # Extract and validate each discussion
                    demo_disc = discussions.get('demographic_overview_discussion', '')
                    income_disc = discussions.get('income_neighborhood_discussion', '')
                    lenders_disc = discussions.get('top_lenders_detailed_discussion', '')
                    market_conc_disc = discussions.get('market_concentration_discussion', '')
                    
                    print(f"  [DEBUG] demographic_overview_discussion length: {len(demo_disc)}")
                    print(f"  [DEBUG] income_neighborhood_discussion length: {len(income_disc)}")
                    print(f"  [DEBUG] top_lenders_detailed_discussion length: {len(lenders_disc)}")
                    print(f"  [DEBUG] market_concentration_discussion length: {len(market_conc_disc)}")
                    
                    # Check if discussions are empty and count how many are empty
                    empty_count = 0
                    if not demo_disc or len(demo_disc.strip()) == 0:
                        print(f"  [WARNING] demographic_overview_discussion is empty or whitespace only")
                        empty_count += 1
                    if not income_disc or len(income_disc.strip()) == 0:
                        print(f"  [WARNING] income_neighborhood_discussion is empty or whitespace only")
                        empty_count += 1
                    if not lenders_disc or len(lenders_disc.strip()) == 0:
                        print(f"  [WARNING] top_lenders_detailed_discussion is empty or whitespace only")
                        empty_count += 1
                    if not market_conc_disc or len(market_conc_disc.strip()) == 0:
                        print(f"  [WARNING] market_concentration_discussion is empty or whitespace only")
                        empty_count += 1

                    # If ALL discussions are empty, trigger fallback to individual calls
                    if empty_count == 4:
                        print(f"  [WARNING] All 4 discussions are empty, triggering fallback to individual calls")
                        raise ValueError("All discussions returned empty from combined call")

                    # Store the discussions (even if some are empty, so frontend knows they were attempted)
                    ai_insights['demographic_overview_discussion'] = demo_disc
                    ai_insights['income_neighborhood_discussion'] = income_disc
                    ai_insights['top_lenders_detailed_discussion'] = lenders_disc
                    ai_insights['market_concentration_discussion'] = market_conc_disc

                    print("  [OK] All table discussions generated successfully")

                    # Generate individual Section 2 narratives (one per table)
                    print("  Generating individual Section 2 table narratives...")
                    try:
                        ai_insights['income_borrowers_discussion'] = analyzer.generate_income_borrowers_discussion(ai_data)
                        print(f"    [OK] income_borrowers_discussion length: {len(ai_insights.get('income_borrowers_discussion', ''))}")
                    except Exception as e:
                        print(f"    [WARNING] Failed to generate income_borrowers_discussion: {e}")
                        ai_insights['income_borrowers_discussion'] = ''

                    try:
                        ai_insights['income_tracts_discussion'] = analyzer.generate_income_tracts_discussion(ai_data)
                        print(f"    [OK] income_tracts_discussion length: {len(ai_insights.get('income_tracts_discussion', ''))}")
                    except Exception as e:
                        print(f"    [WARNING] Failed to generate income_tracts_discussion: {e}")
                        ai_insights['income_tracts_discussion'] = ''

                    try:
                        ai_insights['minority_tracts_discussion'] = analyzer.generate_minority_tracts_discussion(ai_data)
                        print(f"    [OK] minority_tracts_discussion length: {len(ai_insights.get('minority_tracts_discussion', ''))}")
                    except Exception as e:
                        print(f"    [WARNING] Failed to generate minority_tracts_discussion: {e}")
                        ai_insights['minority_tracts_discussion'] = ''
                    print(f"  [DEBUG] ai_insights keys after storing: {list(ai_insights.keys())}")
                    print(f"  [DEBUG] Stored demographic_overview_discussion length: {len(ai_insights.get('demographic_overview_discussion', ''))}")
                    print(f"  [DEBUG] Stored income_neighborhood_discussion length: {len(ai_insights.get('income_neighborhood_discussion', ''))}")
                    print(f"  [DEBUG] Stored top_lenders_detailed_discussion length: {len(ai_insights.get('top_lenders_detailed_discussion', ''))}")
                    print(f"  [DEBUG] Stored market_concentration_discussion length: {len(ai_insights.get('market_concentration_discussion', ''))}")
                except Exception as gen_error:
                    print(f"  [ERROR] Error generating table discussions: {gen_error}")
                    import traceback
                    traceback.print_exc()
                    # Fallback to individual calls if combined call fails
                    print("  Falling back to individual discussion calls...")
                    try:
                        print("    Generating demographic_overview_discussion individually...")
                        ai_insights['demographic_overview_discussion'] = analyzer.generate_demographic_overview_discussion(ai_data)
                        print(f"    [OK] demographic_overview_discussion length: {len(ai_insights.get('demographic_overview_discussion', ''))}")

                        print("    Generating income_neighborhood_discussion individually...")
                        ai_insights['income_neighborhood_discussion'] = analyzer.generate_income_neighborhood_discussion(ai_data)
                        print(f"    [OK] income_neighborhood_discussion length: {len(ai_insights.get('income_neighborhood_discussion', ''))}")

                        print("    Generating top_lenders_detailed_discussion individually...")
                        ai_insights['top_lenders_detailed_discussion'] = analyzer.generate_top_lenders_detailed_discussion(ai_data)
                        print(f"    [OK] top_lenders_detailed_discussion length: {len(ai_insights.get('top_lenders_detailed_discussion', ''))}")

                        # Note: market_concentration_discussion is only available via combined call
                        print("    [INFO] market_concentration_discussion not available in fallback mode")
                        ai_insights['market_concentration_discussion'] = ''

                        # Generate individual Section 2 narratives in fallback mode
                        print("    Generating individual Section 2 table narratives...")
                        try:
                            ai_insights['income_borrowers_discussion'] = analyzer.generate_income_borrowers_discussion(ai_data)
                            print(f"      [OK] income_borrowers_discussion length: {len(ai_insights.get('income_borrowers_discussion', ''))}")
                        except Exception as e:
                            print(f"      [WARNING] Failed to generate income_borrowers_discussion: {e}")
                            ai_insights['income_borrowers_discussion'] = ''

                        try:
                            ai_insights['income_tracts_discussion'] = analyzer.generate_income_tracts_discussion(ai_data)
                            print(f"      [OK] income_tracts_discussion length: {len(ai_insights.get('income_tracts_discussion', ''))}")
                        except Exception as e:
                            print(f"      [WARNING] Failed to generate income_tracts_discussion: {e}")
                            ai_insights['income_tracts_discussion'] = ''

                        try:
                            ai_insights['minority_tracts_discussion'] = analyzer.generate_minority_tracts_discussion(ai_data)
                            print(f"      [OK] minority_tracts_discussion length: {len(ai_insights.get('minority_tracts_discussion', ''))}")
                        except Exception as e:
                            print(f"      [WARNING] Failed to generate minority_tracts_discussion: {e}")
                            ai_insights['minority_tracts_discussion'] = ''
                    except Exception as fallback_error:
                        print(f"  [ERROR] Fallback also failed: {fallback_error}")
                        traceback.print_exc()
                        # Don't raise - continue without these insights
                
                # Call 2: Key findings (intro paragraph is now generated in JavaScript)
                if progress_tracker:
                    progress_tracker.update_ai_progress(2, 3, 'Key Findings')
                print("  Generating key findings...")
                try:
                    ai_insights['key_findings'] = analyzer.generate_key_findings(ai_data)
                    print("  [OK] Key findings generated successfully")
                except Exception as gen_error:
                    print(f"  [ERROR] Error generating key findings: {gen_error}")
                    import traceback
                    traceback.print_exc()
                    # Don't raise - continue without key findings
                
                # Optional calls (only if needed - these may not be displayed in the report)
                # Call 3: Trends analysis (if needed)
                if progress_tracker:
                    progress_tracker.update_ai_progress(3, 3, 'Trends Analysis')
                print("  Generating trends analysis...")
                try:
                    ai_insights['trends_analysis'] = analyzer.generate_trends_analysis(ai_data)
                    print("  [OK] Trends analysis generated successfully")
                except Exception as gen_error:
                    print(f"  [WARNING] Error generating trends analysis (non-critical): {gen_error}")
                    ai_insights['trends_analysis'] = ""
                
                # Note: lender_strategies and community_impact are not currently displayed in the report template
                # so we skip them to reduce API calls
                
                # Generate table-specific introductions and narratives
                print("Generating table introductions and narratives...")
                table_introductions = {}
                table_narratives = {}
                try:
                    if not report_data.get('summary', pd.DataFrame()).empty:
                        table_introductions['table1'] = analyzer.generate_table_introduction('table1', ai_data)
                        table_narratives['table1'] = analyzer.generate_table_narrative('table1', ai_data)
                    if not report_data.get('by_lender', pd.DataFrame()).empty:
                        table_introductions['table2'] = analyzer.generate_table_introduction('table2', ai_data)
                        table_narratives['table2'] = analyzer.generate_table_narrative('table2', ai_data)
                    if not report_data.get('by_county', pd.DataFrame()).empty and len(clarified_counties) > 1:
                        table_introductions['table3'] = analyzer.generate_table_introduction('table3', ai_data)
                        table_narratives['table3'] = analyzer.generate_table_narrative('table3', ai_data)
                except Exception as intro_error:
                    print(f"Error generating table introductions/narratives: {intro_error}")
                    import traceback
                    traceback.print_exc()
                    # Don't raise - continue without table intros/narratives
                
                ai_insights['table_introductions'] = table_introductions
                ai_insights['table_narratives'] = table_narratives
                
                print("AI insights generated successfully")
            else:
                print("[INFO] Skipping AI insights generation (no API key or analyzer not initialized)")
                ai_insights = {}
                ai_insights_enabled = False  # Ensure flag is set when skipping
            
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            try:
                error_message = str(e).encode('ascii', 'replace').decode('ascii')
            except:
                error_message = "An error occurred during AI analysis"
            
            print(f"AI analysis skipped: {error_type}: {error_message}")
            print("Full traceback:")
            traceback.print_exc()
            
            if "API key" in error_message or "No API key" in error_message:
                error_msg = "AI analysis not available - API key not configured or service unavailable."
            elif "No counties" in error_message or "No years" in error_message:
                error_msg = f"AI analysis not available - {error_message}"
            else:
                error_msg = f"AI analysis not available - Error: {error_type}: {error_message}"
            
            ai_insights = {
                'executive_summary': error_msg,
                'key_findings': error_msg,
                'trends_analysis': error_msg,
                'lender_strategies': error_msg,
                'community_impact': error_msg,
                'table_introductions': {},
                'table_narratives': {},
                'methods': 'Methods section not available - AI analysis failed.'
            }
        
        # Finalize - but don't mark as complete yet!
        # The blueprint.py will call progress_tracker.complete() AFTER storing results to BigQuery
        if progress_tracker:
            progress_tracker.update_progress('saving', 95, 'Saving results... Almost done! 💾')

        print("Analysis completed successfully!")
        
        # Ensure census_data is properly formatted for JSON serialization
        census_data_serialized = {}
        if census_data and len(census_data) > 0:
            from justdata.shared.analysis.ai_provider import convert_numpy_types
            try:
                print(f"  [DEBUG] Before serialization: {len(census_data)} counties")
                # Debug: print structure before serialization
                for county, data in list(census_data.items())[:1]:
                    print(f"  [DEBUG] Sample Census data BEFORE serialization for {county}:")
                    print(f"    - Top-level keys: {list(data.keys())}")
                    if 'time_periods' in data:
                        print(f"    - Has time_periods: {list(data.get('time_periods', {}).keys())}")
                    if 'demographics' in data:
                        print(f"    - Has demographics (legacy format)")
                
                census_data_serialized = convert_numpy_types(census_data)
                print(f"  [DEBUG] Census data serialized: {len(census_data_serialized)} counties")
                
                if len(census_data_serialized) > 0:
                    for county, data in list(census_data_serialized.items())[:1]:
                        print(f"  [DEBUG] Sample serialized Census data for {county}:")
                        print(f"    - Top-level keys: {list(data.keys())}")
                        if 'time_periods' in data:
                            time_periods = data.get('time_periods', {})
                            print(f"    - Time periods: {list(time_periods.keys())}")
                            for period_key, period_data in time_periods.items():
                                demo = period_data.get('demographics', {})
                                print(f"      - {period_key}: pop={demo.get('total_population', 'N/A')}")
                        elif 'demographics' in data:
                            demo = data['demographics']
                            print(f"    - Demographics keys: {list(demo.keys())}")
                            print(f"    - Total pop: {demo.get('total_population', 'N/A')}")
                else:
                    print(f"  [WARNING] Census data became empty after serialization!")
                    print(f"  [DEBUG] Original census_data type: {type(census_data)}")
                    print(f"  [DEBUG] Original census_data keys: {list(census_data.keys()) if census_data else 'None'}")
            except Exception as ser_error:
                print(f"  [ERROR] Error serializing census_data: {ser_error}")
                import traceback
                traceback.print_exc()
                census_data_serialized = {}
        else:
            print(f"  [WARNING] No census_data to serialize (type: {type(census_data)}, len: {len(census_data) if census_data else 0})")
        
        # Debug: Check AI insights before returning
        print(f"\n[DEBUG] Final ai_insights keys: {list(ai_insights.keys())}")
        print(f"[DEBUG] demographic_overview_discussion in ai_insights: {'demographic_overview_discussion' in ai_insights}")
        print(f"[DEBUG] demographic_overview_discussion length: {len(ai_insights.get('demographic_overview_discussion', ''))}")
        print(f"[DEBUG] income_neighborhood_discussion in ai_insights: {'income_neighborhood_discussion' in ai_insights}")
        print(f"[DEBUG] income_neighborhood_discussion length: {len(ai_insights.get('income_neighborhood_discussion', ''))}")
        print(f"[DEBUG] top_lenders_detailed_discussion in ai_insights: {'top_lenders_detailed_discussion' in ai_insights}")
        print(f"[DEBUG] top_lenders_detailed_discussion length: {len(ai_insights.get('top_lenders_detailed_discussion', ''))}")
        
        return {
            'success': True,
            'report_data': report_data,
            'ai_insights': ai_insights,
            'metadata': {
                'counties': clarified_counties,
                'years': years,
                'total_records': len(all_results),
                'generated_at': datetime.now().isoformat(),
                'loan_purpose': loan_purpose if loan_purpose else ['purchase', 'refinance', 'equity'],  # Include loan purpose in metadata
                'census_data': census_data_serialized,  # Include Census data for frontend display (serialized)
                'hhi': convert_numpy_types(hhi_data),  # Include HHI data for frontend display
                'version': __version__,  # Include version number
                'ai_insights_enabled': ai_insights_enabled  # Flag indicating if AI insights are available
            },
            'message': f'Analysis completed successfully. Generated reports for {len(clarified_counties)} counties and {len(years)} years.',
            'counties': clarified_counties,
            'years': years,
            'records': len(all_results)
        }
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        if progress_tracker:
            progress_tracker.complete(success=False, error=str(e))
        return {'success': False, 'error': f'Analysis failed: {str(e)}'}

