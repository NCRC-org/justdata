#!/usr/bin/env python3
"""
Export lender qualification data to CSV in Downloads folder.

This script identifies lenders that have >= 1000 loans in consecutive years
and exports all disclosure data with qualification status to CSV.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import time

# Add the apps directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient


def get_downloads_folder():
    """Get the user's Downloads folder path."""
    # Windows
    if os.name == 'nt':
        downloads = Path.home() / 'Downloads'
    # macOS
    elif sys.platform == 'darwin':
        downloads = Path.home() / 'Downloads'
    # Linux
    else:
        downloads = Path.home() / 'Downloads'
    
    return downloads


def export_lender_qualification_data(min_loans: int = 1000, output_file: str = None, 
                                     years: list = None, max_rows: int = None,
                                     use_bq_table: bool = True, export_csv: bool = False):
    """
    Export lender disclosure data with qualification status.
    
    A lender "qualifies" if they have >= min_loans in consecutive years.
    
    Args:
        min_loans: Minimum number of loans required (default: 1000)
        output_file: Optional output filename (default: auto-generated with timestamp)
        years: Optional list of years to filter (default: [2018, 2019, 2020, 2021, 2022, 2023, 2024])
        max_rows: Optional maximum number of rows to fetch (for testing/limiting)
    """
    # Default to 2018-2024 if no years specified
    if years is None:
        years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
    
    print("=" * 80)
    print("LENDER QUALIFICATION DATA EXPORT")
    print("=" * 80)
    print(f"\nFinding lenders with >= {min_loans} loans in consecutive years...")
    print(f"Filtering to years: {years}")
    if max_rows:
        print(f"Limiting to {max_rows:,} rows")
    print("Querying BigQuery disclosure table...\n")
    
    try:
        # Initialize BigQuery client
        bq_client = BigQueryClient()
        
        if use_bq_table:
            # Faster method: Create table in BigQuery first, then export
            print("🚀 Using fast method: Creating table in BigQuery first...")
            print("   This is much faster for large datasets!")
            print("Excluding credit card lenders (average loan amount < $10,000)...")
            print()
            
            table_id, query_job = bq_client.create_lender_qualification_table(
                min_loans=min_loans,
                years=years,
                exclude_credit_card=True,
                min_avg_loan_amount=10000,
                table_name='1071_1k_lenders',
                dataset='misc'
            )
            
            print(f"⏳ Creating table: {table_id}")
            print("   This may take a few minutes...")
        else:
            # Original method: Fetch directly to Python
            print("Executing query (this may take a while for large datasets)...")
            print("Excluding credit card lenders (average loan amount < $10,000)...")
            print()
            
            query_job = bq_client.get_lender_qualification_data(
                min_loans=min_loans,
                years=years,
                max_rows=max_rows,
                exclude_credit_card=True,
                min_avg_loan_amount=10000
            )
            table_id = None
        
        # Monitor query progress
        print("⏳ Waiting for query to complete...")
        start_time = time.time()
        last_update = start_time
        
        while not query_job.done():
            elapsed = time.time() - start_time
            # Update every 5 seconds
            if time.time() - last_update >= 5:
                elapsed_min = int(elapsed // 60)
                elapsed_sec = int(elapsed % 60)
                print(f"   Query running... ({elapsed_min}m {elapsed_sec}s elapsed)", end='\r')
                last_update = time.time()
            time.sleep(1)
        
        # Wait for completion
        query_job.result()
        elapsed = time.time() - start_time
        elapsed_min = int(elapsed // 60)
        elapsed_sec = int(elapsed % 60)
        print(f"   ✓ Query completed in {elapsed_min}m {elapsed_sec}s")
        
        # Get total bytes processed for progress estimation
        try:
            total_bytes = query_job.total_bytes_processed
            if total_bytes:
                total_mb = total_bytes / (1024 * 1024)
                print(f"   Data processed: {total_mb:,.0f} MB")
        except:
            pass
        
        print()
        
        if use_bq_table:
            # Table creation method - much faster
            print("📊 Creating table in BigQuery...")
            fetch_start = time.time()
            
            # Wait for table creation to complete
            query_job.result()
            elapsed = time.time() - fetch_start
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)
            print(f"   ✓ Table created in {elapsed_min}m {elapsed_sec}s")
            
            # Get row count from table
            try:
                table = bq_client.client.get_table(table_id)
                row_count = table.num_rows
                print(f"   Table contains {row_count:,} rows")
                
                # Get some stats
                qualified_count_query = bq_client.query(f"SELECT COUNT(*) as cnt FROM `{table_id}` WHERE qualification_status = 'Qualifies'")
                qualified_result = qualified_count_query.result()
                qualified_count = list(qualified_result)[0].cnt if qualified_result else 0
                
                lender_count_query = bq_client.query(f"SELECT COUNT(DISTINCT respondent_id) as cnt FROM `{table_id}`")
                lender_result = lender_count_query.result()
                lender_count = list(lender_result)[0].cnt if lender_result else 0
                
                print(f"   Qualified records: {qualified_count:,}")
                print(f"   Unique lenders: {lender_count:,}")
            except Exception as e:
                print(f"   Could not get table stats: {e}")
                row_count = None
            
            print()
            print(f"✓ Table created successfully!")
            print(f"  Table location: {table_id}")
            print()
            print("You can now query this table in BigQuery:")
            print(f"  SELECT * FROM `{table_id}` LIMIT 100")
            print()
            
            # Only export CSV if requested
            if export_csv:
                print("💾 Exporting to CSV as requested...")
                fetch_start = time.time()
                
                # Fetch from table
                export_query = f"SELECT * FROM `{table_id}`"
                export_job = bq_client.query(export_query)
                df = export_job.to_dataframe()
                
                fetch_elapsed = time.time() - fetch_start
                fetch_min = int(fetch_elapsed // 60)
                fetch_sec = int(fetch_elapsed % 60)
                print(f"   ✓ Data exported in {fetch_min}m {fetch_sec}s")
                print()
            else:
                # Skip CSV export, just return table info
                print("(Skipping CSV export - table is ready in BigQuery)")
                print()
                return table_id
        else:
            # Original method: Fetch directly
            print("📥 Fetching results (this may take a while for large datasets)...")
            
            # Try to get row count estimate from query statistics
            estimated_rows = None
            try:
                query_job.reload()
                result = query_job.result()
                if hasattr(result, 'total_rows'):
                    estimated_rows = result.total_rows
            except:
                pass
            
            if estimated_rows:
                print(f"   Estimated rows to fetch: {estimated_rows:,}")
                print(f"   Note: Large datasets can take 1-2 minutes per 100K rows")
                estimated_minutes = max(1, int(estimated_rows / 100000 * 1.5))
                print(f"   Estimated time: ~{estimated_minutes} minutes")
                print()
            
            fetch_start = time.time()
            last_progress_update = fetch_start
            
            # Simple progress indicator with spinner
            spinner_chars = ['|', '/', '-', '\\']
            spinner_idx = 0
            
            # Fetch with progress indication
            if max_rows:
                print(f"   Fetching... {spinner_chars[spinner_idx]}", end='\r')
                df = query_job.to_dataframe(max_results=max_rows)
            else:
                # For large datasets, show periodic updates with spinner
                print("   Starting data fetch...", end='\r')
                
                # Use threading to show progress while fetching
                import threading
                
                fetch_complete = False
                fetch_error = None
                df_result = None
                
                def fetch_data():
                    nonlocal fetch_complete, fetch_error, df_result
                    try:
                        df_result = query_job.to_dataframe()
                        fetch_complete = True
                    except Exception as e:
                        fetch_error = e
                        fetch_complete = True
                
                # Start fetch in background
                fetch_thread = threading.Thread(target=fetch_data, daemon=True)
                fetch_thread.start()
                
                # Show progress while fetching with spinner and time estimates
                update_interval = 5  # Update every 5 seconds
                while not fetch_complete:
                    current_time = time.time()
                    if current_time - last_progress_update >= update_interval:
                        elapsed = current_time - fetch_start
                        elapsed_min = int(elapsed // 60)
                        elapsed_sec = int(elapsed % 60)
                        spinner_idx = (spinner_idx + 1) % len(spinner_chars)
                        
                        # Provide time estimate based on elapsed time
                        status_msg = f"   Fetching... {spinner_chars[spinner_idx]} ({elapsed_min}m {elapsed_sec}s elapsed) - Still working..."
                        if estimated_rows and elapsed > 60:
                            avg_speed = elapsed / max(1, estimated_rows / 100000) if estimated_rows else 0
                            if avg_speed > 0 and estimated_rows:
                                remaining_est = max(0, (estimated_rows / 100000 * avg_speed) - elapsed)
                                remaining_min = int(remaining_est // 60)
                                if remaining_min > 0:
                                    status_msg += f" (~{remaining_min}m remaining)"
                        
                        print(status_msg, end='\r', flush=True)
                        last_progress_update = current_time
                    time.sleep(0.5)
                
                # Wait for thread to complete
                fetch_thread.join(timeout=2)
                
                if fetch_error:
                    raise fetch_error
                
                df = df_result
            
            fetch_elapsed = time.time() - fetch_start
            fetch_min = int(fetch_elapsed // 60)
            fetch_sec = int(fetch_elapsed % 60)
            print(f"   ✓ Data fetched in {fetch_min}m {fetch_sec}s ({len(df):,} rows)")
            print()
        
        fetch_elapsed = time.time() - fetch_start
        fetch_min = int(fetch_elapsed // 60)
        fetch_sec = int(fetch_elapsed % 60)
        print(f"   ✓ Data fetched in {fetch_min}m {fetch_sec}s ({len(df):,} rows)")
        print()
        
        # Only proceed with CSV export if we have a dataframe (not using BQ table method or CSV requested)
        if not use_bq_table or export_csv:
            print(f"\nQuery completed! Found {len(df):,} records")
            print(f"Qualified lenders: {df[df['qualification_status'] == 'Qualifies']['respondent_id'].nunique():,}")
            print(f"Total unique lenders: {df['respondent_id'].nunique():,}")
            
            if export_csv:
                # Generate output filename if not provided
                if not output_file:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_file = f'lender_qualification_data_{timestamp}.csv'
                
                # Get Downloads folder
                downloads_folder = get_downloads_folder()
                output_path = downloads_folder / output_file
                
                # Ensure Downloads folder exists
                downloads_folder.mkdir(parents=True, exist_ok=True)
                
                # Export to CSV
                print("💾 Exporting to CSV...")
                export_start = time.time()
                df.to_csv(output_path, index=False)
                export_elapsed = time.time() - export_start
                
                file_size_mb = output_path.stat().st_size / 1024 / 1024
                print(f"   ✓ Export completed in {export_elapsed:.1f}s")
                print()
                print(f"✓ Successfully exported {len(df):,} records to CSV")
                print(f"  File: {output_path}")
                print(f"  File size: {file_size_mb:.2f} MB")
                return output_path
        
        # Print summary statistics (only if we have dataframe)
        if not use_bq_table or export_csv:
            print("\n" + "=" * 80)
            print("SUMMARY STATISTICS")
            print("=" * 80)
            
            qualified_df = df[df['qualification_status'] == 'Qualifies']
            if not qualified_df.empty:
                print(f"\nQualified Records: {len(qualified_df):,}")
                print(f"  Unique lenders: {qualified_df['respondent_id'].nunique():,}")
                print(f"  Years covered: {sorted(qualified_df['year'].unique())}")
                print(f"  Top 10 qualified lenders by record count:")
                top_lenders = qualified_df['lender_name'].value_counts().head(10)
                for lender, count in top_lenders.items():
                    print(f"    - {lender}: {count:,} records")
            
            print(f"\nAll Records: {len(df):,}")
            print(f"  Unique lenders: {df['respondent_id'].nunique():,}")
            print(f"  Years covered: {sorted(df['year'].unique())}")
            
            if export_csv:
                return output_path
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Export lender qualification data to CSV in Downloads folder'
    )
    parser.add_argument(
        '--min-loans',
        type=int,
        default=1000,
        help='Minimum number of loans required for qualification (default: 1000)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output filename (default: auto-generated with timestamp)'
    )
    parser.add_argument(
        '--years',
        type=str,
        default=None,
        help='Comma-separated list of years to filter (e.g., "2022,2023,2024"). Default: 2018-2024'
    )
    parser.add_argument(
        '--max-rows',
        type=int,
        default=None,
        help='Maximum number of rows to fetch (for testing/limiting large datasets)'
    )
    parser.add_argument(
        '--export-csv',
        action='store_true',
        help='Also export to CSV file (default: only create BigQuery table)'
    )
    parser.add_argument(
        '--no-bq-table',
        action='store_true',
        help='Use old method: fetch directly to Python (slower, but creates CSV)'
    )
    
    args = parser.parse_args()
    
    # Parse years if provided, otherwise use default (2018-2024)
    years = None
    if args.years:
        years = [int(y.strip()) for y in args.years.split(',')]
    # If not provided, will default to 2018-2024 in the function
    
    export_lender_qualification_data(
        min_loans=args.min_loans,
        output_file=args.output,
        years=years,
        max_rows=args.max_rows,
        use_bq_table=not args.no_bq_table,
        export_csv=args.export_csv
    )


if __name__ == '__main__':
    main()

