#!/usr/bin/env python3
"""
LendSight core analysis logic - Mortgage lending analysis.
Similar structure to BranchSeeker but for HMDA mortgage data.
"""

import os
import pandas as pd
from typing import Dict, List
from datetime import datetime
from .config import OUTPUT_DIR, PROJECT_ID
from .data_utils import find_exact_county_match, execute_mortgage_query
from .mortgage_report_builder import build_mortgage_report, save_mortgage_excel_report


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
    from .data_utils import expand_state_to_counties, expand_metro_to_counties, get_last_5_years_hmda
    
    # Parse years - if empty or None, automatically get last 5 years
    if not years_str or not years_str.strip():
        # Automatically get last 5 years from HMDA data
        years = get_last_5_years_hmda()
        print(f"✅ Automatically using last 5 HMDA years: {years}")
    elif years_str.lower() == "all":
        years = list(range(2018, 2024))  # HMDA data typically 2018-2023
    else:
        years = [int(y.strip()) for y in years_str.split(",") if y.strip().isdigit()]
    
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
            progress_tracker.update_progress('initializing')
        
        # Parse parameters with selection context
        counties, years = parse_web_parameters(counties_str, years_str, selection_type, state_code, metro_code)
        
        if progress_tracker:
            progress_tracker.update_progress('parsing_params')
        
        if not counties:
            return {'success': False, 'error': 'No counties provided'}
        
        if not years:
            return {'success': False, 'error': 'No years provided'}
        
        # Clarify county selections
        if progress_tracker:
            progress_tracker.update_progress('preparing_data')
        
        clarified_counties = []
        total_counties = len(counties)
        for idx, county in enumerate(counties, 1):
            try:
                if progress_tracker:
                    progress_tracker.update_progress('preparing_data', 
                        int(15 + (idx / total_counties) * 5),
                        f'Preparing data... Matching county {idx}/{total_counties}: {county}')
                
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
            progress_tracker.update_progress('connecting_db')
        
        sql_template = load_sql_template()
        
        # Execute BigQuery queries
        if progress_tracker:
            progress_tracker.update_progress('fetching_data', 20, 'Fetching mortgage data from database...')
        
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
                            20 + int((query_index / total_queries) * 30),
                            f'Fetching data: {county} ({year})...')
                    
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
        
        print(f"[DEBUG] Data fetch complete: {len(all_results)} total records")
        
        if not all_results:
            print(f"[ERROR] No data found for the specified parameters")
            return {'success': False, 'error': 'No data found for the specified parameters'}
        
        print(f"[DEBUG] Moving to Census data fetch...")
        # Fetch Census data FIRST (before building report) so it can be used in AI analysis
        if progress_tracker:
            print(f"[DEBUG] Updating progress to fetching_census_data")
            progress_tracker.update_progress('fetching_census_data', 50, 'Fetching Census demographic data...')
        
        census_data = {}
        try:
            print(f"[DEBUG] Importing census_utils...")
            from .census_utils import get_census_data_for_multiple_counties
            import os
            # Try to load .env file if it exists
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
            api_key = os.getenv('CENSUS_API_KEY')
            print(f"\n[DEBUG] Fetching Census demographic data for context...")
            if not api_key:
                print(f"  [WARNING] CENSUS_API_KEY not set - Census data will not be available")
            else:
                print(f"  [INFO] CENSUS_API_KEY is set")
            print(f"[DEBUG] Calling get_census_data_for_multiple_counties with {len(clarified_counties)} counties...")
            print(f"[DEBUG] This may take 30-60 seconds as it makes multiple API calls per county...")
            if progress_tracker:
                progress_tracker.update_progress('fetching_census_data', 50, f'Fetching Census data for {len(clarified_counties)} counties (this may take a minute)...')
            
            # Use FIPS codes if provided, otherwise look them up
            if counties_with_fips and len(counties_with_fips) > 0:
                # FIPS codes already provided from frontend
                print(f"  [INFO] Using FIPS codes provided from frontend for {len(counties_with_fips)} counties")
                census_data = get_census_data_for_multiple_counties(counties_with_fips, state_code, api_key, progress_tracker)
            else:
                # Fallback: Look up FIPS codes from BigQuery
                print(f"  [INFO] Looking up FIPS codes from BigQuery for {len(clarified_counties)} counties...")
                from justdata.shared.utils.bigquery_client import get_bigquery_client
                from .config import PROJECT_ID
                counties_with_fips_lookup = []
                client = get_bigquery_client(PROJECT_ID)
                
                for county_name in clarified_counties:
                    try:
                        query = f"""
                        SELECT DISTINCT county_state, geoid5
                        FROM geo.cbsa_to_county
                        WHERE county_state = '{county_name}'
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
                    census_data = get_census_data_for_multiple_counties(counties_with_fips_lookup, state_code, api_key, progress_tracker)
                else:
                    print(f"  [WARNING] No counties with valid FIPS codes found, skipping Census data...")
                    census_data = {}
            print(f"[DEBUG] get_census_data_for_multiple_counties returned successfully")
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
                census_data = {}  # Ensure it's an empty dict, not None
        except Exception as census_error:
            print(f"  [WARNING] Error fetching Census data: {census_error}")
            import traceback
            traceback.print_exc()
            census_data = {}
        
        print(f"[DEBUG] Census data fetch complete, moving to report building...")
        # Build report (pass census_data so it can be included in tables)
        if progress_tracker:
            print(f"[DEBUG] Updating progress to processing_data")
            progress_tracker.update_progress('processing_data', 60, 'Processing data and building report...')
        
        print(f"\n[DEBUG] Building report with {len(all_results)} records...")
        report_data = build_mortgage_report(all_results, clarified_counties, years, census_data=census_data, progress_tracker=progress_tracker)
        print(f"[DEBUG] Report building complete")
        
        # Add census data to report_data
        report_data['census_data'] = census_data
        
        # Save Excel report
        if progress_tracker:
            progress_tracker.update_progress('building_report')
        
        excel_path = os.path.join(OUTPUT_DIR, 'hmda_mortgage_analysis.xlsx')
        # Prepare metadata for Notes sheet
        excel_metadata = {
            'counties': clarified_counties,
            'years': years,
            'total_records': len(all_results),
            'generated_at': datetime.now().isoformat(),
            'loan_purpose': loan_purpose if loan_purpose else ['purchase', 'refinance', 'equity'],  # Include loan purpose in metadata
            'census_data': census_data  # Include Census data for Methods sheet
        }
        save_mortgage_excel_report(report_data, excel_path, metadata=excel_metadata)
        print(f"Excel report saved: {excel_path}")
        
        # Generate AI insights (optional if API key is configured)
        ai_insights = {}
        try:
            from .analysis import LendSightAnalyzer
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
            by_lender_df = report_data.get('by_lender', pd.DataFrame())
            by_lender_data = convert_numpy_types(by_lender_df.to_dict('records') if not by_lender_df.empty else [])
            
            # Prepare demographic overview data
            demographic_df = report_data.get('demographic_overview', pd.DataFrame())
            demographic_data = convert_numpy_types(demographic_df.to_dict('records') if not demographic_df.empty else [])
            
            # Prepare income and neighborhood indicators data
            income_neighborhood_df = report_data.get('income_neighborhood_indicators', pd.DataFrame())
            income_neighborhood_data = convert_numpy_types(income_neighborhood_df.to_dict('records') if not income_neighborhood_df.empty else [])
            
            # Prepare top lenders detailed data
            top_lenders_detailed_df = report_data.get('top_lenders_detailed', pd.DataFrame())
            top_lenders_detailed_data = convert_numpy_types(top_lenders_detailed_df.to_dict('records') if not top_lenders_detailed_df.empty else [])
            
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
                'income_neighborhood_indicators': income_neighborhood_data,
                'top_lenders_detailed': top_lenders_detailed_data,
                'trends_data': convert_numpy_types(report_data.get('trends', {}).to_dict('records') if not report_data.get('trends', pd.DataFrame()).empty else []),
                'hhi': convert_numpy_types(hhi_data),
                'county_data': convert_numpy_types(county_df.to_dict('records') if not county_df.empty else []),
                'by_lender': by_lender_data,
                'census_data': convert_numpy_types(census_data)  # Include Census data for context
            }
            
            if progress_tracker:
                progress_tracker.update_progress('generating_ai')
            
            # Initialize analyzer
            print(f"Initializing AI analyzer...")
            print(f"Counties for AI: {clarified_counties}")
            print(f"Years for AI: {years}")
            print(f"Final year origination count: {final_year_origination_count}")
            
            try:
                analyzer = LendSightAnalyzer()
                print("AI analyzer initialized successfully")
            except Exception as init_error:
                print(f"Failed to initialize AI analyzer: {init_error}")
                import traceback
                traceback.print_exc()
                raise Exception(f"AI analyzer initialization failed: {init_error}. Please check API key configuration.")
            
            # Generate AI insights with progress tracking
            # NOTE: demographic_overview_intro, income_neighborhood_intro, and top_lenders_detailed_intro
            # are hardcoded in JavaScript, so we don't need AI calls for those.
            ai_insights = {}
            
            # Combined call 1: All table discussions (reduces 3 calls to 1)
            if progress_tracker:
                progress_tracker.update_ai_progress(1, 3, 'Table Discussions (Combined)')
            print("  Generating all table discussions (combined call)...")
            try:
                discussions = analyzer.generate_all_table_discussions(ai_data)
                print(f"  [DEBUG] Discussions returned: {list(discussions.keys())}")
                print(f"  [DEBUG] demographic_overview_discussion length: {len(discussions.get('demographic_overview_discussion', ''))}")
                print(f"  [DEBUG] income_neighborhood_discussion length: {len(discussions.get('income_neighborhood_discussion', ''))}")
                print(f"  [DEBUG] top_lenders_detailed_discussion length: {len(discussions.get('top_lenders_detailed_discussion', ''))}")
                ai_insights['demographic_overview_discussion'] = discussions.get('demographic_overview_discussion', '')
                ai_insights['income_neighborhood_discussion'] = discussions.get('income_neighborhood_discussion', '')
                ai_insights['top_lenders_detailed_discussion'] = discussions.get('top_lenders_detailed_discussion', '')
                print("  [OK] All table discussions generated successfully")
                print(f"  [DEBUG] ai_insights keys after storing: {list(ai_insights.keys())}")
                print(f"  [DEBUG] Stored demographic_overview_discussion length: {len(ai_insights.get('demographic_overview_discussion', ''))}")
            except Exception as gen_error:
                print(f"  [ERROR] Error generating table discussions: {gen_error}")
                import traceback
                traceback.print_exc()
                # Fallback to individual calls if combined call fails
                print("  Falling back to individual discussion calls...")
                try:
                    ai_insights['demographic_overview_discussion'] = analyzer.generate_demographic_overview_discussion(ai_data)
                    ai_insights['income_neighborhood_discussion'] = analyzer.generate_income_neighborhood_discussion(ai_data)
                    ai_insights['top_lenders_detailed_discussion'] = analyzer.generate_top_lenders_detailed_discussion(ai_data)
                except Exception as fallback_error:
                    print(f"  [ERROR] Fallback also failed: {fallback_error}")
                    raise
            
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
                raise
            
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
                raise
            
            ai_insights['table_introductions'] = table_introductions
            ai_insights['table_narratives'] = table_narratives
            
            print("AI insights generated successfully")
            
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
        
        # Mark as completed
        if progress_tracker:
            progress_tracker.update_progress('completed')
        
        print("\nAnalysis completed successfully!")
        
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
                'census_data': census_data_serialized  # Include Census data for frontend display (serialized)
            },
            'message': f'Analysis completed successfully. Generated reports for {len(clarified_counties)} counties and {len(years)} years.',
            'counties': clarified_counties,
            'years': years,
            'records': len(all_results),
            'excel_file': excel_path
        }
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        if progress_tracker:
            progress_tracker.complete(success=False, error=str(e))
        return {'success': False, 'error': f'Analysis failed: {str(e)}'}

