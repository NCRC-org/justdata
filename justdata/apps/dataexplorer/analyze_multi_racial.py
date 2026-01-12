#!/usr/bin/env python3
"""Analyze multi-racial borrower race combinations in test data."""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.utils.bigquery_client import get_bigquery_client
import json

def main():
    client = get_bigquery_client('hdma1-242116')
    
    # Read the SQL query
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file = os.path.join(script_dir, 'multi_racial_analysis.sql')
    with open(sql_file, 'r') as f:
        query = f.read()
    
    # Execute query
    print("Executing query to analyze multi-racial borrower race combinations...")
    results = client.query(query).result()
    
    # Convert to list of dicts
    rows = []
    for row in results:
        rows.append(dict(row))
    
    # Print results
    print("\n" + "="*80)
    print("MULTI-RACIAL BORROWER RACE COMBINATIONS")
    print("="*80)
    print(f"\nTotal combinations found: {len(rows)}\n")
    
    if rows:
        print(f"{'Race Combination':<50} {'Codes':<20} {'# Races':<10} {'Total Loans':<15} {'Years':<10}")
        print("-" * 105)
        
        total_loans = 0
        for row in rows:
            combination = row.get('race_combination', 'N/A')
            codes = row.get('race_codes', 'N/A')
            num_races = row.get('num_races', 0)
            loans = row.get('total_loans', 0)
            years = row.get('years_present', 0)
            total_loans += loans
            
            print(f"{combination:<50} {codes:<20} {num_races:<10} {loans:<15} {years:<10}")
        
        print("-" * 105)
        print(f"{'TOTAL':<50} {'':<20} {'':<10} {total_loans:<15} {'':<10}")
    else:
        print("No multi-racial borrowers found in test data.")
    
    # Also output as JSON for easy parsing
    print("\n\nJSON Output:")
    print(json.dumps(rows, indent=2))

if __name__ == '__main__':
    main()

