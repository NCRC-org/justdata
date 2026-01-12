#!/usr/bin/env python3
"""
LoanTrends core analysis logic - National quarterly mortgage lending trends analysis.
Similar structure to LendSight but for national-level quarterly data from CFPB API.
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from justdata.apps.loantrends.config import OUTPUT_DIR
from justdata.apps.loantrends.data_utils import fetch_multiple_graphs, parse_quarterly_data, filter_quarters, get_recent_12_quarters
from justdata.apps.loantrends.report_builder import build_trends_report
from justdata.apps.loantrends.analysis import LoanTrendsAnalyzer
from justdata.apps.loantrends.version import __version__
from justdata.shared.utils.unified_env import get_unified_config


def run_analysis(selected_endpoints: List[str], time_period: str = "all", 
                 start_quarter: Optional[str] = None, end_quarter: Optional[str] = None,
                 run_id: str = None, progress_tracker=None) -> Dict:
    """
    Run national quarterly trends analysis.
    
    Args:
        selected_endpoints: List of graph endpoint names to analyze
        time_period: Time period selection ("all", "recent", or "custom")
        start_quarter: Start quarter for custom period (e.g., "2020-Q1")
        end_quarter: End quarter for custom period (e.g., "2024-Q4")
        run_id: Optional run ID for tracking
        progress_tracker: Optional progress tracker for real-time updates
    
    Returns:
        Dictionary with success status and results
    """
    try:
        # Initialize progress
        if progress_tracker:
            progress_tracker.update_progress('initializing', 0, 'Initializing analysis... Getting ready to analyze national trends! 🚀')
        
        if not selected_endpoints:
            raise ValueError("No endpoints selected for analysis")
        
        if progress_tracker:
            progress_tracker.update_progress('fetching_data', 10, f'Fetching data for {len(selected_endpoints)} metrics from CFPB Quarterly API... 📊')
        
        # Fetch graph data from Quarterly API
        def progress_callback(status, current, total):
            if progress_tracker:
                percent = 10 + int((current / total) * 30)  # 10-40% for data fetching
                progress_tracker.update_progress('fetching_data', percent, status)
        
        print(f"[DEBUG] Fetching data for {len(selected_endpoints)} endpoints: {selected_endpoints}")
        graph_data = fetch_multiple_graphs(selected_endpoints, progress_callback)
        print(f"[DEBUG] Fetch complete. Graph data keys: {list(graph_data.keys())}")
        for ep, data in graph_data.items():
            print(f"[DEBUG]   - {ep}: {'data exists' if data is not None else 'None/failed'}")
            if data:
                print(f"[DEBUG]     - data type: {type(data)}")
                print(f"[DEBUG]     - data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
        
        # Filter out None values (failed fetches)
        successful_endpoints = [ep for ep, data in graph_data.items() if data is not None]
        print(f"[DEBUG] Successful endpoints: {successful_endpoints}")
        print(f"[DEBUG] Failed endpoints: {[ep for ep in selected_endpoints if ep not in successful_endpoints]}")
        if not successful_endpoints:
            raise ValueError("Failed to fetch data for any selected endpoints")
        
        if progress_tracker:
            progress_tracker.update_progress('processing_data', 45, 'Processing and structuring data... Organizing the numbers! 📈')
        
        # Determine filter params based on time period
        filter_params = None
        if time_period == "custom" and start_quarter and end_quarter:
            filter_params = {
                'start_quarter': start_quarter,
                'end_quarter': end_quarter
            }
        elif time_period == "all":
            # Default to most recent 12 quarters (3 years)
            start_12q, end_12q = get_recent_12_quarters()
            filter_params = {
                'start_quarter': start_12q,
                'end_quarter': end_12q
            }
        elif time_period == "recent":
            # Recent period - use same as "all" (12 quarters)
            start_12q, end_12q = get_recent_12_quarters()
            filter_params = {
                'start_quarter': start_12q,
                'end_quarter': end_12q
            }
        
        # Build report tables
        if progress_tracker:
            progress_tracker.update_progress('building_tables', 55, 'Building data tables... Creating structured views! 📋')
        
        # Filter quarters based on time period and prepare data for both tables and charts
        print(f"[DEBUG] Filtering quarters with params: {filter_params}")
        filtered_graph_data = {}  # For tables (API format)
        parsed_data_for_charts = {}  # For charts (parsed format with parsed_series)
        
        for endpoint, data in graph_data.items():
            print(f"[DEBUG] Processing endpoint {endpoint} for filtering")
            if data:
                parsed = parse_quarterly_data(data)
                print(f"[DEBUG]   - Parsed data keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'not a dict'}")
                print(f"[DEBUG]   - Parsed quarters count: {len(parsed.get('quarters', []))}")
                print(f"[DEBUG]   - Parsed series count: {len(parsed.get('parsed_series', {}))}")
                if filter_params:
                    print(f"[DEBUG]   - Filtering quarters: {filter_params['start_quarter']} to {filter_params['end_quarter']}")
                    parsed = filter_quarters(parsed, filter_params['start_quarter'], filter_params['end_quarter'])
                    print(f"[DEBUG]   - Filtered quarters count: {len(parsed.get('quarters', []))}")
                    print(f"[DEBUG]   - Filtered parsed_series keys: {list(parsed.get('parsed_series', {}).keys())}")
                
                # Store parsed data for charts (needs parsed_series)
                parsed_data_for_charts[endpoint] = parsed
                
                # Convert back to API format for build_trends_report
                filtered_graph_data[endpoint] = {
                    'title': parsed.get('title', ''),
                    'subtitle': parsed.get('subtitle', ''),
                    'xLabel': parsed.get('xLabel', 'Quarter'),
                    'yLabel': parsed.get('yLabel', 'Value'),
                    'series': parsed.get('series', [])
                }
                print(f"[DEBUG]   - Converted data has {len(filtered_graph_data[endpoint]['series'])} series")
            else:
                print(f"[DEBUG]   - Skipping {endpoint} (data is None)")
                filtered_graph_data[endpoint] = None
                parsed_data_for_charts[endpoint] = None
        
        # Build quarterly chart data (preserving all quarterly data points)
        print(f"[DEBUG] Building quarterly chart data from {len(parsed_data_for_charts)} endpoints...")
        from justdata.apps.loantrends.chart_builder import prepare_quarterly_chart_data
        chart_data = {}
        for endpoint, parsed in parsed_data_for_charts.items():
            if parsed and parsed.get('parsed_series'):
                chart_data[endpoint] = prepare_quarterly_chart_data(parsed)
                print(f"[DEBUG] Created chart data for {endpoint}: {len(chart_data[endpoint].get('quarters', []))} quarters, {len(chart_data[endpoint].get('series_data', {}))} series")
            else:
                print(f"[DEBUG] Skipping {endpoint} for chart data - parsed_series missing or empty")
        
        print(f"[DEBUG] Chart data built: {len(chart_data)} charts created")
        print(f"[DEBUG] Chart data keys: {list(chart_data.keys())}")
        
        # Also build tables for backward compatibility
        print(f"[DEBUG] Building report tables from {len(filtered_graph_data)} endpoints...")
        report_tables = build_trends_report(filtered_graph_data)
        print(f"[DEBUG] Report tables built: {len(report_tables)} tables created")
        print(f"[DEBUG] Report table keys: {list(report_tables.keys())}")
        for key, table in report_tables.items():
            if table:
                print(f"[DEBUG]   - {key}: {len(table)} rows")
            else:
                print(f"[DEBUG]   - {key}: None/empty")
        
        # Determine time period string for display
        if time_period == "custom" and start_quarter and end_quarter:
            time_period_str = f"{start_quarter} to {end_quarter}"
        elif time_period == "recent":
            if filter_params:
                time_period_str = f"{filter_params['start_quarter']} to {filter_params['end_quarter']} (last 2 years)"
            else:
                time_period_str = "last 2 years"
        else:  # "all" - most recent 12 quarters
            if filter_params:
                time_period_str = f"{filter_params['start_quarter']} to {filter_params['end_quarter']} (last 12 quarters)"
            else:
                time_period_str = "last 12 quarters"
        
        # Prepare data for AI analysis
        if progress_tracker:
            progress_tracker.update_progress('preparing_ai', 60, 'Preparing data for AI analysis... Setting up insights! 🤖')
        
        ai_data = {
            'selected_endpoints': successful_endpoints,
            'time_period': time_period_str,
            'graph_data': graph_data,
            'tables': report_tables,
            'metadata': {
                'run_id': run_id,
                'generated_at': datetime.now().isoformat(),
                'version': __version__
            }
        }
        
        # Generate AI insights
        ai_insights = {}
        ai_insights_enabled = False
        
        try:
            config = get_unified_config(verbose=False)
            claude_api_key = config.get('CLAUDE_API_KEY')
            
            # Also check environment directly
            if not claude_api_key:
                claude_api_key = os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
            
            print(f"[DEBUG] Claude API key check: {'Found' if claude_api_key else 'NOT FOUND'}")
            if claude_api_key:
                print(f"[DEBUG] API key length: {len(claude_api_key)}, starts with: {claude_api_key[:10]}...")
            
            if not claude_api_key:
                print("[WARNING] CLAUDE_API_KEY not set - AI insights will not be generated")
                ai_insights_enabled = False
            else:
                # Set in environment for AIAnalyzer to pick up
                os.environ['CLAUDE_API_KEY'] = claude_api_key
                os.environ['ANTHROPIC_API_KEY'] = claude_api_key  # Also set as ANTHROPIC_API_KEY for compatibility
                print(f"[DEBUG] Setting API key in environment, creating analyzer...")
                analyzer = LoanTrendsAnalyzer(api_key=claude_api_key)  # Pass directly to ensure it's used
                ai_insights_enabled = True
                print(f"[DEBUG] Analyzer created successfully")
                
                if progress_tracker:
                    progress_tracker.update_progress('generating_ai', 65, 'Generating AI insights... Creating narratives! ✍️')
                
                # Generate overall trends intro
                print("Generating overall trends introduction...")
                try:
                    ai_insights['overall_intro'] = analyzer.generate_overall_trends_intro(ai_data)
                    print("  [OK] Overall intro generated successfully")
                except Exception as e:
                    print(f"  [WARNING] Error generating overall intro: {e}")
                    ai_insights['overall_intro'] = ""
                
                # Generate section intros
                print("Generating section introductions...")
                section_intros = {}
                sections = ['Loan & Application Counts', 'Credit Metrics', 'Loan Characteristics', 
                           'Market Dynamics', 'Demographic Analysis']
                
                for section in sections:
                    # Check if section has any endpoints
                    has_endpoints = False
                    if section == 'Loan & Application Counts':
                        has_endpoints = any(ep in successful_endpoints for ep in ['applications', 'loans'])
                    elif section == 'Credit Metrics':
                        has_endpoints = any('credit' in ep for ep in successful_endpoints)
                    elif section == 'Loan Characteristics':
                        has_endpoints = any(ep in successful_endpoints for ep in ['ltv', 'dti'])
                    elif section == 'Market Dynamics':
                        has_endpoints = any(ep in successful_endpoints for ep in ['interest-rates', 'denials', 'tlc'])
                    elif section == 'Demographic Analysis':
                        has_endpoints = any('re' in ep for ep in successful_endpoints)
                    
                    if has_endpoints:
                        try:
                            section_intros[section] = analyzer.generate_section_intro(section, ai_data)
                            print(f"  [OK] {section} intro generated successfully")
                        except Exception as e:
                            print(f"  [WARNING] Error generating {section} intro: {e}")
                            section_intros[section] = ""
                
                ai_insights['section_intros'] = section_intros
                
                # Generate table intros and narratives
                print("Generating table introductions and narratives...")
                table_intros = {}
                table_narratives = {}
                
                for endpoint in successful_endpoints:
                    if graph_data[endpoint]:
                        table_data = report_tables.get(endpoint, [])
                        if table_data:
                            table_ai_data = {
                                **ai_data,
                                'endpoint': endpoint,
                                'table_data': table_data
                            }
                            
                            try:
                                table_intros[endpoint] = analyzer.generate_table_intro(endpoint, table_ai_data)
                                table_narratives[endpoint] = analyzer.generate_table_narrative(endpoint, table_ai_data)
                                print(f"  [OK] Table intro and narrative generated for {endpoint}")
                            except Exception as e:
                                print(f"  [WARNING] Error generating table content for {endpoint}: {e}")
                                table_intros[endpoint] = ""
                                table_narratives[endpoint] = ""
                
                ai_insights['table_intros'] = table_intros
                ai_insights['table_narratives'] = table_narratives
                
                # Generate overall summary
                if progress_tracker:
                    progress_tracker.update_progress('generating_ai', 90, 'Generating overall summary... Finalizing insights! 📝')
                
                print("Generating overall summary...")
                try:
                    ai_insights['overall_summary'] = analyzer.generate_overall_summary(ai_data)
                    print("  [OK] Overall summary generated successfully")
                except Exception as e:
                    print(f"  [WARNING] Error generating overall summary: {e}")
                    ai_insights['overall_summary'] = ""
                
                # Generate key findings
                print("Generating key findings...")
                try:
                    ai_insights['key_findings'] = analyzer.generate_key_findings(ai_data)
                    print("  [OK] Key findings generated successfully")
                except Exception as e:
                    print(f"  [WARNING] Error generating key findings: {e}")
                    ai_insights['key_findings'] = ""
                
                print("AI insights generated successfully")
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            try:
                error_message = str(e).encode('ascii', 'replace').decode('ascii')
            except:
                error_message = "An error occurred during AI analysis"
            
            print(f"AI analysis skipped: {error_type}: {error_message}")
            traceback.print_exc()
            
            ai_insights = {
                'overall_intro': f"AI analysis not available - {error_message}",
                'section_intros': {},
                'table_intros': {},
                'table_narratives': {},
                'overall_summary': f"AI analysis not available - {error_message}",
                'key_findings': f"AI analysis not available - {error_message}"
            }
            ai_insights_enabled = False
        
        # Finalize and complete
        if progress_tracker:
            progress_tracker.update_progress('completed', 100, 'Analysis complete! Report ready! ✅')
            import time
            time.sleep(0.5)  # Brief pause to ensure SSE message is sent
            progress_tracker.complete(success=True)
        
        print("Analysis completed successfully!")
        
        # Prepare final result
        print(f"[DEBUG] Preparing final result...")
        print(f"[DEBUG]   - successful_endpoints: {successful_endpoints}")
        print(f"[DEBUG]   - time_period_str: {time_period_str}")
        print(f"[DEBUG]   - report_tables count: {len(report_tables)}")
        print(f"[DEBUG]   - ai_insights keys: {list(ai_insights.keys())}")
        print(f"[DEBUG]   - ai_insights_enabled: {ai_insights_enabled}")
        
        result = {
            'success': True,
            'run_id': run_id,
            'metadata': {
                'selected_endpoints': successful_endpoints,
                'time_period': time_period_str,
                'generated_at': datetime.now().isoformat(),
                'version': __version__
            },
            'graph_data': graph_data,
            'tables': report_tables,
            'chart_data': chart_data,  # Add year-based chart data
            'ai_insights': ai_insights,
            'ai_insights_enabled': ai_insights_enabled
        }
        
        # Debug: Check result structure
        print(f"[DEBUG] Final result structure:")
        print(f"[DEBUG]   - result['success']: {result['success']}")
        print(f"[DEBUG]   - result['metadata']['selected_endpoints']: {result['metadata']['selected_endpoints']}")
        print(f"[DEBUG]   - result['tables'] keys: {list(result['tables'].keys())}")
        print(f"[DEBUG]   - result['chart_data'] keys: {list(result['chart_data'].keys())}")
        print(f"[DEBUG]   - result['chart_data'] count: {len(result['chart_data'])}")
        print(f"[DEBUG]   - result['ai_insights'] keys: {list(result['ai_insights'].keys())}")
        
        # Verify chart_data is serializable
        try:
            import json
            chart_data_json = json.dumps(result['chart_data'], default=str)
            print(f"[DEBUG] Chart data is JSON serializable, length: {len(chart_data_json)}")
        except Exception as e:
            print(f"[ERROR] Chart data is NOT JSON serializable: {e}")
        for key in result['tables'].keys():
            table = result['tables'][key]
            if table:
                print(f"[DEBUG]   - result['tables']['{key}']: {len(table)} rows, first row keys: {list(table[0].keys()) if table and len(table) > 0 else 'N/A'}")
            else:
                print(f"[DEBUG]   - result['tables']['{key}']: None/empty")
        for key in result['chart_data'].keys():
            chart = result['chart_data'][key]
            if chart:
                print(f"[DEBUG]   - result['chart_data']['{key}']: {len(chart.get('years', []))} years, {len(chart.get('series_data', {}))} series")
            else:
                print(f"[DEBUG]   - result['chart_data']['{key}']: None/empty")
        
        return result
        
    except Exception as e:
        import traceback
        error_type = type(e).__name__
        try:
            error_message = str(e).encode('ascii', 'replace').decode('ascii')
        except:
            error_message = "An error occurred during analysis"
        
        print(f"Analysis failed: {error_type}: {error_message}")
        traceback.print_exc()
        
        if progress_tracker:
            progress_tracker.complete(success=False, error=error_message)
        
        return {
            'success': False,
            'error': error_message,
            'error_type': error_type
        }




