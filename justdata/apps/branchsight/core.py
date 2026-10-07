#!/usr/bin/env python3
"""
BranchSight core analysis logic - FULLY FUNCTIONAL.
Adapted from ncrc-test-apps branchsight.
"""

import contextvars
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from typing import Dict
from datetime import datetime
from .config import SOD_YEARS
from .data_utils import find_exact_county_match, execute_branch_query
from justdata.shared.reporting.report_builder import build_report
from justdata.shared.utils.error_ref import GENERIC_ERROR
from justdata.shared.utils.perf import perf_stages, start_perf, timed


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
    from .data_utils import expand_state_to_counties, expand_metro_to_counties

    # Parse years
    if years_str.lower() == "all":
        years = list(SOD_YEARS)
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
    perf_ref = start_perf('branchsight')
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

        # Resolve each picked county to its exact county_state once.
        if progress_tracker:
            progress_tracker.update_progress('preparing_data')

        clarified_counties = []
        with timed('bq:county_match'):
            for county in counties:
                matches = find_exact_county_match(county)
                if not matches:
                    return {'success': False, 'error': 'No data found for the specified parameters'}
                clarified_counties.extend(matches)

        sql_template = load_sql_template()

        if progress_tracker:
            progress_tracker.update_progress('querying_data', 30, 'Querying federal records')

        # One job per county covers every year (branchsight.sod for the latest
        # year, sod_legacy before it).
        all_results = []
        try:
            with timed('bq:branch_report'):
                for idx, county in enumerate(clarified_counties, 1):
                    all_results.extend(execute_branch_query(sql_template, county, years))
                    if progress_tracker:
                        progress_tracker.update_query_progress(idx, len(clarified_counties))
        except Exception as e:
            print(f"Branch query failed for {clarified_counties}: {e}")
            return {'success': False, 'error': GENERIC_ERROR, 'exception': e}

        if not all_results:
            return {'success': False, 'error': 'No data found for the specified parameters'}

        # Build report
        if progress_tracker:
            progress_tracker.update_progress('processing_data')

        print(f"\nBuilding report with {len(all_results)} records...")
        with timed('build_report'):
            report_data = build_report(all_results, clarified_counties, years)

        # The workbook is built on download from the stored result.
        if progress_tracker:
            progress_tracker.update_progress('building_report', message='Aggregating results')

        # Generate AI insights (optional if API key is configured)
        ai_insights = {}
        try:
            from .analysis import BranchSightAnalyzer
            from justdata.shared.analysis.ai_provider import convert_numpy_types

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
                'hhi_by_year': convert_numpy_types(report_data.get('hhi_by_year', [])),
                'county_data': convert_numpy_types(county_df.to_dict('records') if not county_df.empty else []),
                'by_bank': by_bank_data
            }

            if progress_tracker:
                progress_tracker.update_progress('generating_ai')

            # Initialize analyzer - this may raise an exception if API key is missing
            print("Initializing AI analyzer...")
            print(f"Counties for AI: {clarified_counties}")
            print(f"Years for AI: {years}")
            print(f"Final year branch count: {final_year_branch_count}")

            try:
                analyzer = BranchSightAnalyzer()
                print("AI analyzer initialized successfully")
            except Exception as init_error:
                print(f"Failed to initialize AI analyzer: {init_error}")
                import traceback
                traceback.print_exc()
                raise Exception(f"AI analyzer initialization failed: {init_error}. Please check API key configuration.")

            # Generate AI insights: Key Findings and table narratives for the three report sections
            # Note: Executive Summary is now generated in JavaScript, not via AI
            ai_insights = {}

            # The narratives are independent calls, so they run in parallel.
            # Each runs in a copy of this context, so its timed() stage lands in
            # this run's perf list. A failed narrative is left out; the page
            # shows the missing-narrative line in its place.
            tasks = {'key_findings': lambda: analyzer.generate_key_findings(ai_data)}
            if not report_data.get('summary', pd.DataFrame()).empty:
                tasks['table1'] = lambda: analyzer.generate_table_narrative('table1', ai_data)
            if not report_data.get('by_bank', pd.DataFrame()).empty:
                tasks['table2'] = lambda: analyzer.generate_table_narrative('table2', ai_data)
            if not report_data.get('by_county', pd.DataFrame()).empty and len(clarified_counties) > 1:
                tasks['table3'] = lambda: analyzer.generate_table_narrative('table3', ai_data)
            if report_data.get('hhi_by_year'):
                tasks['hhi_trends'] = lambda: analyzer.generate_hhi_trends_narrative(ai_data)

            def run_narrative(name, fn):
                with timed(f'narrative:{name}'):
                    return fn()

            texts = {}
            with timed('narrative:all'), ThreadPoolExecutor(max_workers=len(tasks)) as pool:
                futures = {pool.submit(contextvars.copy_context().run, run_narrative, name, fn): name
                           for name, fn in tasks.items()}
                for done_count, future in enumerate(as_completed(futures), 1):
                    name = futures[future]
                    try:
                        text = future.result()
                        if text and text.strip():
                            texts[name] = text
                        else:
                            print(f"  [WARNING] {name} narrative is empty")
                    except Exception as e:
                        print(f"  [ERROR] {name} narrative failed: {e}")
                    if progress_tracker:
                        progress_tracker.update_ai_progress(done_count, len(tasks), 'Writing the narrative')

            ai_insights['key_findings'] = texts.get('key_findings')
            ai_insights['table_narratives'] = {k: texts[k] for k in ('table1', 'table2', 'table3') if k in texts}
            if 'hhi_trends' in texts:
                ai_insights['hhi_trends_discussion'] = texts['hhi_trends']

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

            ai_insights = {
                'key_findings': None,
                'table_narratives': {}
            }

        if progress_tracker:
            progress_tracker.update_progress('finalizing', 98, 'Aggregating results')
        print("Analysis completed successfully!")

        # The blueprint marks the job complete after the result is stored, so
        # "done" never reaches the page before /report-data can serve it.

        return {
            'success': True,
            'report_data': report_data,
            'ai_insights': ai_insights,
            'metadata': {
                'counties': clarified_counties,
                'years': years,
                'total_records': len(all_results),
                'generated_at': datetime.now().isoformat(),
                'perf': perf_stages(),
                'perf_ref': perf_ref,
            },
            'message': f'Analysis completed successfully. Generated reports for {len(clarified_counties)} counties and {len(years)} years.',
            'counties': clarified_counties,
            'years': years,
            'records': len(all_results),
        }

    except Exception as e:
        # The blueprint logs the exception under a reference; users see GENERIC_ERROR.
        return {'success': False, 'error': GENERIC_ERROR, 'exception': e}
