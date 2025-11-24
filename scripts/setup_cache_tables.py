#!/usr/bin/env python3
"""
Script to create BigQuery tables for the analysis cache system.
Run this once to set up the cache tables in the justdata dataset.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import bigquery
from justdata.shared.utils.bigquery_client import get_bigquery_client

PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'hdma1-242116')
DATASET_ID = 'justdata'

def create_tables():
    """Create all cache tables in BigQuery."""
    client = get_bigquery_client(PROJECT_ID)
    
    # Read SQL file
    sql_file = Path(__file__).parent / 'create_cache_tables.sql'
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        return False
    
    with open(sql_file, 'r') as f:
        sql_content = f.read()
    
    # Split SQL into individual CREATE TABLE statements
    # Remove comments and split by semicolon
    lines = sql_content.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove full-line comments
        if line.strip().startswith('--'):
            continue
        # Remove inline comments (keep the line but remove comment part)
        if '--' in line:
            line = line[:line.index('--')]
        cleaned_lines.append(line)
    
    cleaned_sql = '\n'.join(cleaned_lines)
    statements = [s.strip() for s in cleaned_sql.split(';') if s.strip() and 'CREATE TABLE' in s.upper()]
    
    print(f"Creating cache tables in {PROJECT_ID}.{DATASET_ID}...")
    print()
    
    for i, statement in enumerate(statements, 1):
        if not statement:
            continue
        
        # Extract table name for logging
        table_name = 'unknown'
        if 'CREATE TABLE' in statement.upper():
            # Try to extract table name from backticks
            parts = statement.split('`')
            if len(parts) >= 2:
                full_table = parts[1]
                table_name = full_table.split('.')[-1]
        
        try:
            print(f"[{i}/{len(statements)}] Creating table: {table_name}...")
            # Execute the CREATE TABLE statement
            query_job = client.query(statement)
            query_job.result()  # Wait for completion
            print(f"   ✅ Created {table_name}")
        except Exception as e:
            error_str = str(e).lower()
            if 'already exists' in error_str or 'duplicate' in error_str or 'table already exists' in error_str:
                print(f"   ⚠️  Table {table_name} already exists (skipping)")
            else:
                print(f"   ❌ Error creating {table_name}: {e}")
                print(f"   Statement: {statement[:200]}...")
                return False
    
    print()
    print("✅ All cache tables created successfully!")
    print()
    print("Tables created:")
    print(f"  - {PROJECT_ID}.{DATASET_ID}.analysis_cache")
    print(f"  - {PROJECT_ID}.{DATASET_ID}.usage_log")
    print(f"  - {PROJECT_ID}.{DATASET_ID}.analysis_results")
    print(f"  - {PROJECT_ID}.{DATASET_ID}.analysis_result_sections")
    
    return True

if __name__ == '__main__':
    success = create_tables()
    sys.exit(0 if success else 1)

