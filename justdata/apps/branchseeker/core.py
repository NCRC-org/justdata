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
from justdata.shared.reporting.report_builder import build_report, save_excel_report


def parse_web_parameters(counties_str: str, years_str: str) -> tuple:
    """Parse parameters from web interface."""
    counties = [c.strip() for c in counties_str.split(";") if c.strip()]
    
    if years_str.lower() == "all":
        years = list(range(2017, 2025))
    else:
        years = [int(y.strip()) for y in years_str.split(",") if y.strip().isdigit()]
    
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


def run_analysis(counties_str: str, years_str: str, run_id: str = None, progress_tracker=None) -> Dict:
    """
    Run analysis for web interface - FULL IMPLEMENTATION.
    
    Args:
        counties_str: Semicolon-separated county names
        years_str: Comma-separated years or "all"
        run_id: Optional run ID for tracking
        progress_tracker: Optional progress tracker for real-time updates
    
    Returns:
        Dictionary with success status and results
    """
    try:
        # Initialize progress
        if progress_tracker:
            progress_tracker.update_progress('initializing')
        
        # Parse parameters
        counties, years = parse_web_parameters(counties_str, years_str)
        
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
        for county in counties:
            try:
                matches = find_exact_county_match(county)
                if not matches:
                    return {'success': False, 'error': f'No matching counties found for: {county}'}
                clarified_counties.append(matches[0])
                print(f"✅ Using county: {matches[0]}")
            except ValueError as e:
                return {'success': False, 'error': str(e)}
        
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
        
        print(f"\n📊 Building report with {len(all_results)} records...")
        report_data = build_report(all_results, clarified_counties, years)
        
        # Save Excel report
        if progress_tracker:
            progress_tracker.update_progress('building_report')
        
        excel_path = os.path.join(OUTPUT_DIR, 'fdic_branch_analysis.xlsx')
        save_excel_report(report_data, excel_path)
        print(f"✅ Excel report saved: {excel_path}")
        
        # Generate AI insights (optional if API key is configured)
        ai_insights = {}
        try:
            from .analysis import BranchSeekerAnalyzer
            from justdata.shared.analysis.ai_provider import convert_numpy_types
            
            # Prepare data for AI analysis
            ai_data = {
                'counties': clarified_counties,
                'years': years,
                'total_branches': len(all_results),
                'top_banks': report_data.get('by_bank', pd.DataFrame()).groupby('Bank Name')['Total Branches'].sum().nlargest(5).index.tolist() if not report_data.get('by_bank', pd.DataFrame()).empty else [],
                'summary_data': convert_numpy_types(report_data.get('summary', {}).to_dict('records') if not report_data.get('summary', pd.DataFrame()).empty else []),
                'trends_data': convert_numpy_types(report_data.get('trends', {}).to_dict('records') if not report_data.get('trends', pd.DataFrame()).empty else [])
            }
            
            if progress_tracker:
                progress_tracker.update_progress('generating_ai')
            
            analyzer = BranchSeekerAnalyzer()
            
            # Generate AI insights with progress tracking
            ai_insights = {}
            ai_insight_types = [
                ('executive_summary', 'Executive Summary'),
                ('key_findings', 'Key Findings'),
                ('trends_analysis', 'Trends Analysis'),
                ('bank_strategies', 'Bank Strategies'),
                ('community_impact', 'Community Impact')
            ]
            
            for i, (insight_key, insight_name) in enumerate(ai_insight_types, 1):
                if progress_tracker:
                    progress_tracker.update_ai_progress(i, len(ai_insight_types), insight_name)
                
                print(f"  Generating {insight_name}...")
                
                if insight_key == 'executive_summary':
                    ai_insights[insight_key] = analyzer.generate_executive_summary(ai_data)
                elif insight_key == 'key_findings':
                    ai_insights[insight_key] = analyzer.generate_key_findings(ai_data)
                elif insight_key == 'trends_analysis':
                    ai_insights[insight_key] = analyzer.generate_trends_analysis(ai_data)
                elif insight_key == 'bank_strategies':
                    ai_insights[insight_key] = analyzer.generate_bank_strategies_analysis(ai_data)
                elif insight_key == 'community_impact':
                    ai_insights[insight_key] = analyzer.generate_community_impact_analysis(ai_data)
            print("✅ AI insights generated successfully")
            
        except Exception as e:
            print(f"⚠️  AI analysis skipped: {e}")
            ai_insights = {
                'executive_summary': 'AI analysis not available - API key not configured or service unavailable.',
                'key_findings': 'AI analysis not available - API key not configured or service unavailable.',
                'trends_analysis': 'AI analysis not available - API key not configured or service unavailable.',
                'bank_strategies': 'AI analysis not available - API key not configured or service unavailable.',
                'community_impact': 'AI analysis not available - API key not configured or service unavailable.'
            }
        
        # Mark as completed
        if progress_tracker:
            progress_tracker.update_progress('completed')
        
        print("\n🎉 Analysis completed successfully!")
        
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
        print(f"\n❌ Error: {str(e)}")
        if progress_tracker:
            progress_tracker.complete(success=False, error=str(e))
        return {'success': False, 'error': f'Analysis failed: {str(e)}'}
