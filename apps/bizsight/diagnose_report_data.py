#!/usr/bin/env python3
"""
Diagnostic script to check what data is actually stored in analysis results.
This will help identify if data is being generated but not displayed, or if it's not being generated at all.
"""

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.bizsight.utils.progress_tracker import analysis_results_store

def diagnose_latest_result():
    """Check the most recent analysis result."""
    print("=" * 80)
    print("DIAGNOSING ANALYSIS RESULTS")
    print("=" * 80)
    
    if not analysis_results_store:
        print("\n✗ No analysis results found in store.")
        print("   Run a new analysis first.")
        return
    
    print(f"\n✓ Found {len(analysis_results_store)} analysis result(s)")
    
    # Get the most recent result
    latest_job_id = list(analysis_results_store.keys())[-1]
    result = analysis_results_store[latest_job_id]
    
    print(f"\nLatest job_id: {latest_job_id}")
    print(f"Result keys: {list(result.keys())}")
    
    # Check comparison_table
    print("\n" + "-" * 80)
    print("COMPARISON TABLE CHECK")
    print("-" * 80)
    comparison_table = result.get('comparison_table', [])
    if comparison_table:
        print(f"✓ comparison_table exists with {len(comparison_table)} rows")
        if len(comparison_table) > 0:
            print(f"  First row keys: {list(comparison_table[0].keys())}")
            print(f"  First row sample: {comparison_table[0]}")
        else:
            print("  ⚠ comparison_table is empty list")
    else:
        print("✗ comparison_table is missing or None")
        if 'report_data' in result:
            report_data = result.get('report_data', {})
            if 'comparison_table' in report_data:
                comp_df = report_data['comparison_table']
                if hasattr(comp_df, 'empty'):
                    print(f"  Found in report_data: empty={comp_df.empty}, shape={comp_df.shape if hasattr(comp_df, 'shape') else 'N/A'}")
    
    # Check HHI
    print("\n" + "-" * 80)
    print("HHI CHECK")
    print("-" * 80)
    hhi = result.get('hhi', None)
    if hhi:
        print(f"✓ hhi exists: {hhi}")
        if isinstance(hhi, dict):
            print(f"  value: {hhi.get('value')}")
            print(f"  concentration_level: {hhi.get('concentration_level')}")
    else:
        print("✗ hhi is missing or None")
    
    # Check top_lenders_table
    print("\n" + "-" * 80)
    print("TOP LENDERS TABLE CHECK")
    print("-" * 80)
    top_lenders = result.get('top_lenders_table', [])
    if top_lenders:
        print(f"✓ top_lenders_table exists with {len(top_lenders)} rows")
        if len(top_lenders) > 0:
            print(f"  First row keys: {list(top_lenders[0].keys())}")
    else:
        print("✗ top_lenders_table is missing or empty")
    
    # Check summary_table income percentages
    print("\n" + "-" * 80)
    print("SUMMARY TABLE INCOME PERCENTAGES CHECK")
    print("-" * 80)
    summary_table = result.get('summary_table', {})
    income_fields = [
        'pct_loans_low_income', 'pct_loans_moderate_income', 
        'pct_loans_middle_income', 'pct_loans_upper_income',
        'pct_amount_low_income', 'pct_amount_moderate_income',
        'pct_amount_middle_income', 'pct_amount_upper_income'
    ]
    for field in income_fields:
        value = summary_table.get(field)
        if value is not None:
            print(f"✓ {field}: {value}")
        else:
            print(f"✗ {field}: missing")
    
    # Check metadata
    print("\n" + "-" * 80)
    print("METADATA CHECK")
    print("-" * 80)
    metadata = result.get('metadata', {})
    print(f"County: {metadata.get('county_name', 'N/A')}")
    print(f"State: {metadata.get('state_name', 'N/A')}")
    print(f"Year range: {metadata.get('year_range', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    diagnose_latest_result()

