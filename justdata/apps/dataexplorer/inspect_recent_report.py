#!/usr/bin/env python3
"""
Inspect the most recent Manufacturers and Traders Trust report.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.utils.progress_tracker import analysis_results_store, get_analysis_result
import json
from datetime import datetime

# Known job ID from logs
job_id = "d0e12480-2ff2-4a0c-8906-13ef834df659"

print(f"Looking for report with job_id: {job_id}")
print(f"Total reports in store: {len(analysis_results_store)}")
print()

# Try to get the specific report
result = get_analysis_result(job_id)

if result:
    print("=" * 80)
    print("REPORT FOUND")
    print("=" * 80)
    print()
    
    # Get metadata
    metadata = result.get('metadata', {})
    lender_info = metadata.get('lender_info', {})
    
    print("LENDER INFORMATION:")
    print(f"  Name: {lender_info.get('name', 'N/A')}")
    print(f"  LEI: {lender_info.get('lei', 'N/A')}")
    print(f"  RSSD: {lender_info.get('rssd', 'N/A')}")
    print(f"  Type: {lender_info.get('type', 'N/A')}")
    print()
    
    # Get report data
    report_data = result.get('report_data', {})
    
    print("REPORT DATA KEYS:")
    for key in sorted(report_data.keys()):
        print(f"  - {key}")
    print()
    
    # Check Section 1 Table 1 data
    if 'section1_table1' in report_data:
        table1 = report_data['section1_table1']
        print("SECTION 1 TABLE 1 DATA:")
        if isinstance(table1, list):
            print(f"  Total rows: {len(table1)}")
            for row in table1:
                print(f"    Year {row.get('year', 'N/A')}: {row.get('total_originations', 0):,} loans")
        else:
            print(f"  Type: {type(table1)}")
            print(f"  Data: {table1}")
        print()
    
    # Check all_metros_data
    all_metros_data = result.get('all_metros_data', [])
    if all_metros_data:
        print(f"ALL METROS DATA: {len(all_metros_data)} rows")
        # Sum by year
        year_totals = {}
        for row in all_metros_data:
            year = row.get('year') or row.get('activity_year')
            total = row.get('total_originations', 0)
            if year:
                year_totals[year] = year_totals.get(year, 0) + total
        
        print("  Year totals from all_metros_data:")
        for year in sorted(year_totals.keys()):
            print(f"    {year}: {year_totals[year]:,} loans")
        print()
    
    # Check subject data
    subject_data = result.get('subject_hmda_data', [])
    if subject_data:
        print(f"SUBJECT HMDA DATA: {len(subject_data)} rows")
        # Sum by year
        year_totals = {}
        for row in subject_data:
            year = row.get('year') or row.get('activity_year')
            total = row.get('total_originations', 0)
            if year:
                year_totals[year] = year_totals.get(year, 0) + total
        
        print("  Year totals from subject_hmda_data:")
        for year in sorted(year_totals.keys()):
            print(f"    {year}: {year_totals[year]:,} loans")
        print()
    
    # Show wizard data if available
    wizard_data = result.get('wizard_data', {})
    if wizard_data:
        print("WIZARD DATA:")
        print(f"  Geography Scope: {wizard_data.get('geography_scope', 'N/A')}")
        print(f"  Years: {wizard_data.get('years', 'N/A')}")
        print()
    
    # Show timestamp
    job_data = analysis_results_store.get(job_id)
    if job_data and isinstance(job_data, dict) and 'timestamp' in job_data:
        timestamp = job_data['timestamp']
        dt = datetime.fromtimestamp(timestamp)
        print(f"Report timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
else:
    print("Report not found in memory store.")
    print()
    print("Available job IDs:")
    for jid in list(analysis_results_store.keys())[:10]:
        job_data = analysis_results_store.get(jid)
        if isinstance(job_data, dict) and 'timestamp' in job_data:
            timestamp = job_data['timestamp']
            dt = datetime.fromtimestamp(timestamp)
            print(f"  {jid} - {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"  {jid} - (no timestamp)")
    
    print()
    print("Note: Reports are stored in memory and may have been cleared.")
    print("If the server is running, the report may still be accessible via the /report/<job_id> endpoint.")

