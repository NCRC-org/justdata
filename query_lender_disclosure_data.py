#!/usr/bin/env python3
"""
Example script showing how to access lender data from the disclosure table.

This script demonstrates various ways to query lender disclosure data using
the BigQueryClient.get_lender_disclosure_data() method.
"""

import sys
import os
import pandas as pd

# Add the apps directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient


def example_1_query_by_lender_name():
    """Example: Query all data for lenders matching a name pattern."""
    print("\n" + "="*80)
    print("Example 1: Query by Lender Name (partial match)")
    print("="*80)
    
    bq_client = BigQueryClient()
    
    # Query all data for lenders with "Chase" in their name
    query_result = bq_client.get_lender_disclosure_data(lender_name='Chase', years=[2024])
    df = query_result.to_dataframe()
    
    print(f"\nFound {len(df)} records for lenders matching 'Chase' in 2024")
    if not df.empty:
        print("\nSample columns:", df.columns.tolist()[:10])
        print(f"\nUnique lenders: {df['lender_name'].nunique()}")
        print(f"\nFirst few lender names:")
        for lender in df['lender_name'].unique()[:5]:
            print(f"  - {lender}")
    
    return df


def example_2_query_by_respondent_id():
    """Example: Query all data for a specific lender by respondent_id."""
    print("\n" + "="*80)
    print("Example 2: Query by Respondent ID")
    print("="*80)
    
    bq_client = BigQueryClient()
    
    # First, let's find a respondent_id to use
    # Query for a specific lender name to get their respondent_id
    sample_query = bq_client.get_lender_disclosure_data(lender_name='Bank', years=[2024])
    sample_df = sample_query.to_dataframe()
    
    if not sample_df.empty:
        # Get the first respondent_id
        respondent_id = sample_df.iloc[0]['respondent_id']
        lender_name = sample_df.iloc[0]['lender_name']
        
        print(f"\nQuerying data for lender: {lender_name} (respondent_id: {respondent_id})")
        
        # Now query by respondent_id
        query_result = bq_client.get_lender_disclosure_data(
            respondent_id=respondent_id, 
            years=[2023, 2024]
        )
        df = query_result.to_dataframe()
        
        print(f"\nFound {len(df)} records for this lender across 2023-2024")
        if not df.empty:
            print(f"\nCounties: {df['county_state'].nunique()}")
            print(f"Years: {sorted(df['year'].unique())}")
    
    return df if not sample_df.empty else pd.DataFrame()


def example_3_query_by_county():
    """Example: Query all lenders in a specific county."""
    print("\n" + "="*80)
    print("Example 3: Query All Lenders in a County")
    print("="*80)
    
    bq_client = BigQueryClient()
    
    # Query all lenders in Baltimore City, MD (GEOID5: 24510)
    geoid5 = '24510'
    query_result = bq_client.get_lender_disclosure_data(geoid5=geoid5, years=[2024])
    df = query_result.to_dataframe()
    
    print(f"\nFound {len(df)} records for {geoid5} in 2024")
    if not df.empty:
        print(f"\nCounty: {df.iloc[0]['county_state']}")
        print(f"Unique lenders: {df['lender_name'].nunique()}")
        print(f"\nTop 10 lenders by record count:")
        top_lenders = df['lender_name'].value_counts().head(10)
        for lender, count in top_lenders.items():
            print(f"  - {lender}: {count} records")
    
    return df


def example_4_query_combined_filters():
    """Example: Query with multiple filters combined."""
    print("\n" + "="*80)
    print("Example 4: Combined Filters (Lender + County + Years)")
    print("="*80)
    
    bq_client = BigQueryClient()
    
    # Query for a specific lender in a specific county for specific years
    query_result = bq_client.get_lender_disclosure_data(
        lender_name='Wells Fargo',
        geoid5='24031',  # Baltimore County, MD
        years=[2022, 2023, 2024]
    )
    df = query_result.to_dataframe()
    
    print(f"\nFound {len(df)} records for Wells Fargo in Baltimore County, MD (2022-2024)")
    if not df.empty:
        print(f"\nYears: {sorted(df['year'].unique())}")
        print(f"\nSample data:")
        print(df[['year', 'lender_name', 'county_state', 'numsbrev_under_1m', 'amtsbrev_under_1m']].head())
    
    return df


def example_5_get_all_lender_data():
    """Example: Query all lender data (no filters - use with caution!)."""
    print("\n" + "="*80)
    print("Example 5: Get All Lender Data (No Filters)")
    print("="*80)
    print("WARNING: This query may return a large amount of data!")
    print("="*80)
    
    # Uncomment to run (commented out by default to avoid large queries)
    # bq_client = BigQueryClient()
    # query_result = bq_client.get_lender_disclosure_data(years=[2024])
    # df = query_result.to_dataframe()
    # print(f"\nFound {len(df)} total records in 2024")
    # return df
    
    print("\n(Skipped - uncomment in code to run)")
    return pd.DataFrame()


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("LENDER DISCLOSURE DATA QUERY EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates how to access lender data from the disclosure table")
    print("using the BigQueryClient.get_lender_disclosure_data() method.")
    print("\nAvailable methods:")
    print("  - get_lender_disclosure_data(respondent_id='...')")
    print("  - get_lender_disclosure_data(lender_name='...')")
    print("  - get_lender_disclosure_data(geoid5='...')")
    print("  - get_lender_disclosure_data(years=[2023, 2024])")
    print("  - Any combination of the above filters")
    
    try:
        # Run examples
        example_1_query_by_lender_name()
        example_2_query_by_respondent_id()
        example_3_query_by_county()
        example_4_query_combined_filters()
        example_5_get_all_lender_data()
        
        print("\n" + "="*80)
        print("All examples completed!")
        print("="*80)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

