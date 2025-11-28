#!/usr/bin/env python3
"""
BranchSeeker core analysis logic - FULLY FUNCTIONAL.
"""

import os
import pandas as pd
from typing import Dict, List
from datetime import datetime
from .config import OUTPUT_DIR, PROJECT_ID
from .data_utils import find_exact_county_match, execute_branch_query
from .analysis import BranchSeekerAnalyzer
from shared.reporting.report_builder import build_report, save_excel_report


def parse_web_parameters(counties_str: str, years_str: str, selection_type: str = 'county', 
                        state_code: str = None, metro_code: str = None) -> tuple:
    """Parse parameters from web interface.image.png
    
    Args:
        counties_str: Semicolon-separated county names (for county selection)
        years_str: Comma-separated years or "all"
        selection_type: 'county', 'state', or 'metro'
        state_code: Two-digit state FIPS code (for state selection)
        metro_code: CBSA code (for metro selection)
    
    Returns:
        Tuple of (counties_list, years_list)
    """
    from .data_utils import expand_state_to_counties, expand_metro_to_counties
    
    # Parse years
    if years_str.lower() == "all":
        years = list(range(2017, 2026))  # Include 2025
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
        'branch_report.sql'
    )
    try:
        with open(sql_template_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise Exception(f"SQL template not found at {sql_template_path}")


def run_analysis(counties_str: str, years_str: str, run_id: str = None, progress_tracker=None, 
                 selection_type: str = 'county', state_code: str = None, metro_code: str = None) -> Dict:
    """
    Run analysis for web interface - FULL IMPLEMENTATION.
    
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
                    # This shouldn't happen with the fallback, but handle it anyway
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
            progress_tracker.update_progress('querying_data')
        
        all_results = []
        total_queries = len(clarified_counties) * len(years)
        query_index = 0
        
        for county in clarified_counties:
            for year in years:
                try:
                    print(f"  Querying {county} for year {year}...")
                    results = execute_branch_query(sql_template, county, year)
                    all_results.extend(results)
                    print(f"    Found {len(results)} records")
                    
                    # Update progress
                    query_index += 1
                    if progress_tracker:
                        progress_tracker.update_query_progress(query_index, total_queries)
                        
                except Exception as e:
                    print(f"    Error querying {county} {year}: {e}")
                    query_index += 1
                    continue
        
        if not all_results:
            return {'success': False, 'error': 'No data found for the specified parameters'}
        
        # Build report
        if progress_tracker:
            progress_tracker.update_progress('processing_data')
        
        print(f"\nBuilding report with {len(all_results)} records...")
        report_data = build_report(all_results, clarified_counties, years)
        
        # Save Excel report
        if progress_tracker:
            progress_tracker.update_progress('building_report')
        
        excel_path = os.path.join(OUTPUT_DIR, 'fdic_branch_analysis.xlsx')
        # Prepare metadata for Notes sheet
        excel_metadata = {
            'counties': clarified_counties,
            'years': years,
            'total_records': len(all_results),
            'generated_at': datetime.now().isoformat()
        }
        save_excel_report(report_data, excel_path, metadata=excel_metadata)
        print(f"Excel report saved: {excel_path}")
        
        # Generate AI insights (optional if API key is configured)
        ai_insights = {}
        try:
            from .analysis import BranchSeekerAnalyzer
            from shared.analysis.ai_provider import convert_numpy_types
            
            # Prepare data for AI analysis
            county_df = report_data.get('by_county', pd.DataFrame())
            hhi_data = report_data.get('hhi', {})
            raw_df = report_data.get('raw_data', pd.DataFrame())
            
            # Calculate final year's unique branch count (not summed across years)
            final_year_branch_count = 0
            if not raw_df.empty and 'year' in raw_df.columns and 'uninumbr' in raw_df.columns:
                final_year = max(years)
                final_year_df = raw_df[raw_df['year'] == final_year]
                final_year_branch_count = final_year_df['uninumbr'].nunique()
            
            # Prepare table data for AI analysis
            by_bank_df = report_data.get('by_bank', pd.DataFrame())
            by_bank_data = convert_numpy_types(by_bank_df.to_dict('records') if not by_bank_df.empty else [])
            
            # Safely get top banks list
            top_banks_list = []
            if not by_bank_df.empty and 'Bank Name' in by_bank_df.columns:
                top_banks_list = by_bank_df.head(5)['Bank Name'].tolist()
            
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
                'final_year_branch_count': final_year_branch_count,  # Use final year count, not total
                'top_banks': top_banks_list,
                'summary_data': convert_numpy_types(report_data.get('summary', {}).to_dict('records') if not report_data.get('summary', pd.DataFrame()).empty else []),
                'trends_data': convert_numpy_types(report_data.get('trends', {}).to_dict('records') if not report_data.get('trends', pd.DataFrame()).empty else []),
                'hhi': convert_numpy_types(hhi_data),
                'county_data': convert_numpy_types(county_df.to_dict('records') if not county_df.empty else []),
                'by_bank': by_bank_data
            }
            
            if progress_tracker:
                progress_tracker.update_progress('generating_ai')
            
            # Initialize analyzer - this may raise an exception if API key is missing
            print(f"Initializing AI analyzer...")
            print(f"Counties for AI: {clarified_counties}")
            print(f"Years for AI: {years}")
            print(f"Final year branch count: {final_year_branch_count}")
            
            try:
                analyzer = BranchSeekerAnalyzer()
                print("AI analyzer initialized successfully")
            except Exception as init_error:
                print(f"Failed to initialize AI analyzer: {init_error}")
                import traceback
                traceback.print_exc()
                raise Exception(f"AI analyzer initialization failed: {init_error}. Please check API key configuration.")
            
            # Generate AI insights: Key Findings and table narratives for the three report sections
            # Note: Executive Summary is now generated in JavaScript, not via AI
            ai_insights = {}
            
            # Generate Key Findings
            print("Generating Key Findings...")
            try:
                if progress_tracker:
                    progress_tracker.update_ai_progress(1, 4, 'Key Findings')
                ai_insights['key_findings'] = analyzer.generate_key_findings(ai_data)
                print(f"  [OK] Key Findings generated successfully")
            except Exception as key_findings_error:
                print(f"  [ERROR] Error generating Key Findings: {key_findings_error}")
                import traceback
                traceback.print_exc()
                # Don't raise - allow report to continue without key findings
                print("  [WARNING] Continuing without Key Findings due to error")
            
            # Generate table-specific narratives
            print("Generating table narratives...")
            table_narratives = {}
            
            # Generate table1 narrative
            if not report_data.get('summary', pd.DataFrame()).empty:
                try:
                    if progress_tracker:
                        progress_tracker.update_ai_progress(2, 4, 'Yearly Breakdown Analysis')
                    print("  Generating table1 narrative (Yearly Breakdown Analysis)...")
                    narrative1 = analyzer.generate_table_narrative('table1', ai_data)
                    if narrative1 and narrative1.strip():
                        table_narratives['table1'] = narrative1
                        print(f"  [OK] table1 narrative generated ({len(narrative1)} chars)")
                    else:
                        print("  [WARNING] table1 narrative is empty or None")
                except Exception as e:
                    print(f"  [ERROR] Failed to generate table1 narrative: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Generate table2 narrative
            if not report_data.get('by_bank', pd.DataFrame()).empty:
                try:
                    if progress_tracker:
                        progress_tracker.update_ai_progress(3, 4, 'Analysis by Bank')
                    print("  Generating table2 narrative (Analysis by Bank)...")
                    narrative2 = analyzer.generate_table_narrative('table2', ai_data)
                    if narrative2 and narrative2.strip():
                        table_narratives['table2'] = narrative2
                        print(f"  [OK] table2 narrative generated ({len(narrative2)} chars)")
                    else:
                        print("  [WARNING] table2 narrative is empty or None")
                except Exception as e:
                    print(f"  [ERROR] Failed to generate table2 narrative: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Generate table3 narrative
            if not report_data.get('by_county', pd.DataFrame()).empty and len(clarified_counties) > 1:
                try:
                    if progress_tracker:
                        progress_tracker.update_ai_progress(4, 4, 'County by County Analysis')
                    print("  Generating table3 narrative (County by County Analysis)...")
                    narrative3 = analyzer.generate_table_narrative('table3', ai_data)
                    if narrative3 and narrative3.strip():
                        table_narratives['table3'] = narrative3
                        print(f"  [OK] table3 narrative generated ({len(narrative3)} chars)")
                    else:
                        print("  [WARNING] table3 narrative is empty or None")
                except Exception as e:
                    print(f"  [ERROR] Failed to generate table3 narrative: {e}")
                    import traceback
                    traceback.print_exc()
            
            ai_insights['table_narratives'] = table_narratives
            
            # Debug: Print what we're storing
            print(f"Stored table_narratives keys: {list(table_narratives.keys())}")
            for key, value in table_narratives.items():
                if value:
                    print(f"  {key}: {len(value)} characters")
                else:
                    print(f"  {key}: EMPTY or None")
            
            # Methods section is hardcoded in the template (not AI-generated)
            print("AI insights generated successfully")
            
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            # Safely encode error message to avoid Unicode issues
            try:
                error_message = str(e).encode('ascii', 'replace').decode('ascii')
            except:
                error_message = "An error occurred during AI analysis"
            
            print(f"AI analysis skipped: {error_type}: {error_message}")
            print("Full traceback:")
            traceback.print_exc()  # Print full traceback for debugging
            
            # More specific error message based on error type
            if "API key" in error_message or "No API key" in error_message:
                error_msg = "AI analysis not available - API key not configured or service unavailable."
            elif "No counties" in error_message or "No years" in error_message:
                error_msg = f"AI analysis not available - {error_message}"
            else:
                error_msg = f"AI analysis not available - Error: {error_type}: {error_message}"
            
            ai_insights = {
                'key_findings': None,
                'table_narratives': {}
            }
        
        # Mark as completed
        if progress_tracker:
            progress_tracker.update_progress('completed')
        
        print("\nAnalysis completed successfully!")
        
        return {
            'success': True,
            'report_data': report_data,
            'ai_insights': ai_insights,
            'metadata': {
                'counties': clarified_counties,
                'years': years,
                'total_records': len(all_results),
                'generated_at': datetime.now().isoformat()
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
