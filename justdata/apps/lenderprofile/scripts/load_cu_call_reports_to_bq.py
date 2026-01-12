#!/usr/bin/env python3
"""
Load Credit Union Call Report data from zip files into BigQuery.
Processes branch information and main call report data.
"""

import zipfile
import csv
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.utils.unified_env import ensure_unified_env_loaded
from shared.utils.bigquery_client import get_bigquery_client
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

ensure_unified_env_loaded(verbose=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_year_from_filename(filename: str) -> int:
    """Extract year from filename like 'call-report-data-2025-06.zip'."""
    parts = filename.stem.split('-')
    for part in parts:
        if part.isdigit() and len(part) == 4:
            return int(part)
    return None


def parse_csv_from_zip(zip_path: Path, filename: str) -> List[Dict[str, Any]]:
    """Parse a CSV file from a zip archive."""
    rows = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            if filename not in z.namelist():
                logger.warning(f"File {filename} not found in {zip_path.name}")
                return rows
            
            with z.open(filename) as f:
                # Read as text
                content = f.read().decode('utf-8', errors='ignore')
                
                # Parse CSV
                reader = csv.DictReader(content.splitlines())
                for row in reader:
                    # Clean up values (remove quotes, whitespace)
                    cleaned_row = {}
                    for k, v in row.items():
                        if v:
                            # Remove surrounding quotes if present
                            v = v.strip().strip('"').strip("'")
                        cleaned_row[k.strip().strip('"')] = v if v else None
                    rows.append(cleaned_row)
        
        logger.info(f"Parsed {len(rows)} rows from {filename}")
        return rows
    except Exception as e:
        logger.error(f"Error parsing {filename} from {zip_path.name}: {e}", exc_info=True)
        return []


def create_bq_table_if_not_exists(client: bigquery.Client, project_id: str, dataset_id: str, 
                                   table_id: str, schema: List[bigquery.SchemaField]):
    """Create BigQuery dataset and table if they don't exist."""
    # Create dataset first if it doesn't exist
    dataset_ref = client.dataset(dataset_id, project=project_id)
    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset {dataset_id} already exists")
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = 'US'
        dataset = client.create_dataset(dataset)
        logger.info(f"Created dataset {dataset_id}")
    
    # Create table if it doesn't exist
    table_ref = dataset_ref.table(table_id)
    try:
        client.get_table(table_ref)
        logger.info(f"Table {table_id} already exists")
    except NotFound:
        table = bigquery.Table(table_ref, schema=schema)
        table = client.create_table(table)
        logger.info(f"Created table {table_id}")


def load_cu_branches_to_bq(zip_path: Path, project_id: str = 'hdma1-242116', 
                           dataset_id: str = 'credit_unions'):
    """
    Load credit union branch information from zip file to BigQuery.
    
    Args:
        zip_path: Path to the zip file
        project_id: GCP project ID
        dataset_id: BigQuery dataset ID
    """
    year = extract_year_from_filename(zip_path)
    if not year:
        logger.error(f"Could not extract year from {zip_path.name}")
        return
    
    logger.info(f"Processing {zip_path.name} (year: {year})")
    
    # Parse branch information
    branch_rows = parse_csv_from_zip(zip_path, "Credit Union Branch Information.txt")
    
    if not branch_rows:
        logger.warning(f"No branch data found in {zip_path.name}")
        return
    
    # Prepare data for BigQuery
    client = get_bigquery_client(project_id)
    
    # Define schema for branches table
    branch_schema = [
        bigquery.SchemaField("cu_number", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("cycle_date", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("join_number", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("site_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("cu_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("site_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("site_type_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("main_office", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("address_line1", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("address_line2", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("city", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("state", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("zip", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("county", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("year", "INTEGER", mode="REQUIRED"),
    ]
    
    # Create table if needed
    create_bq_table_if_not_exists(client, project_id, dataset_id, "cu_branches", branch_schema)
    
    # Prepare rows for insertion
    rows_to_insert = []
    for row in branch_rows:
        bq_row = {
            "cu_number": row.get("CU_NUMBER"),
            "cycle_date": row.get("CYCLE_DATE"),
            "join_number": row.get("JOIN_NUMBER"),
            "site_id": row.get("SiteId"),
            "cu_name": row.get("CU_NAME"),
            "site_name": row.get("SiteName"),
            "site_type_name": row.get("SiteTypeName"),
            "main_office": row.get("MainOffice"),
            "address_line1": row.get("PhysicalAddressLine1"),
            "address_line2": row.get("PhysicalAddressLine2"),
            "city": row.get("PhysicalCity") or row.get("City") or row.get("CITY"),
            "state": row.get("PhysicalState") or row.get("State") or row.get("STATE"),
            "zip": row.get("PhysicalZip") or row.get("Zip") or row.get("ZIP"),
            "county": row.get("PhysicalCounty") or row.get("County") or row.get("COUNTY"),
            "year": year,
        }
        rows_to_insert.append(bq_row)
    
    # Insert data in batches (BigQuery has a 10MB limit per request)
    dataset_ref = client.dataset(dataset_id, project=project_id)
    table_ref = dataset_ref.table("cu_branches")
    
    batch_size = 1000
    total_inserted = 0
    
    for i in range(0, len(rows_to_insert), batch_size):
        batch = rows_to_insert[i:i + batch_size]
        errors = client.insert_rows_json(table_ref, batch)
        if errors:
            logger.error(f"Errors inserting batch {i//batch_size + 1}: {errors}")
        else:
            total_inserted += len(batch)
            logger.info(f"Inserted batch {i//batch_size + 1} ({len(batch)} rows)")
    
    logger.info(f"Successfully inserted {total_inserted} branch records for year {year}")


def load_cu_call_reports_to_bq(zip_path: Path, project_id: str = 'hdma1-242116',
                               dataset_id: str = 'credit_unions'):
    """
    Load credit union main call report data from zip file to BigQuery.
    
    Args:
        zip_path: Path to the zip file
        project_id: GCP project ID
        dataset_id: BigQuery dataset ID
    """
    year = extract_year_from_filename(zip_path)
    if not year:
        logger.error(f"Could not extract year from {zip_path.name}")
        return
    
    logger.info(f"Processing {zip_path.name} (year: {year})")
    
    # Parse FOICU (main call report)
    cu_rows = parse_csv_from_zip(zip_path, "FOICU.txt")
    
    if not cu_rows:
        logger.warning(f"No call report data found in {zip_path.name}")
        return
    
    # Prepare data for BigQuery
    client = get_bigquery_client(project_id)
    
    # Define schema (simplified - add more fields as needed)
    cu_schema = [
        bigquery.SchemaField("cu_number", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("cycle_date", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("join_number", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("rssd", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("cu_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("cu_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("city", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("state", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("charter_state", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("state_code", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("zip_code", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("county_code", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("year", "INTEGER", mode="REQUIRED"),
    ]
    
    # Create table if needed
    create_bq_table_if_not_exists(client, project_id, dataset_id, "cu_call_reports", cu_schema)
    
    # Prepare rows for insertion
    rows_to_insert = []
    for row in cu_rows:
        bq_row = {
            "cu_number": row.get("CU_NUMBER"),
            "cycle_date": row.get("CYCLE_DATE"),
            "join_number": row.get("JOIN_NUMBER"),
            "rssd": row.get("RSSD"),
            "cu_type": row.get("CU_TYPE"),
            "cu_name": row.get("CU_NAME"),
            "city": row.get("CITY"),
            "state": row.get("STATE"),
            "charter_state": row.get("CharterState"),
            "state_code": row.get("STATE_CODE"),
            "zip_code": row.get("ZIP_CODE"),
            "county_code": row.get("COUNTY_CODE"),
            "year": year,
        }
        rows_to_insert.append(bq_row)
    
    # Insert data in batches
    dataset_ref = client.dataset(dataset_id, project=project_id)
    table_ref = dataset_ref.table("cu_call_reports")
    
    batch_size = 1000
    total_inserted = 0
    
    for i in range(0, len(rows_to_insert), batch_size):
        batch = rows_to_insert[i:i + batch_size]
        errors = client.insert_rows_json(table_ref, batch)
        if errors:
            logger.error(f"Errors inserting batch {i//batch_size + 1}: {errors}")
        else:
            total_inserted += len(batch)
            logger.info(f"Inserted batch {i//batch_size + 1} ({len(batch)} rows)")
    
    logger.info(f"Successfully inserted {total_inserted} call report records for year {year}")


def process_all_cu_call_reports(desktop_path: str = None, project_id: str = 'hdma1-242116'):
    """Process all credit union call report zip files."""
    if desktop_path is None:
        desktop_path = r"C:\Users\jrichardson\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop"
    
    desktop = Path(desktop_path)
    zip_files = sorted(desktop.glob("call-report-data-*.zip"))
    
    logger.info(f"Found {len(zip_files)} credit union call report zip files")
    
    for zip_file in zip_files:
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {zip_file.name}")
        logger.info(f"{'='*80}")
        
        # Load branch data
        load_cu_branches_to_bq(zip_file, project_id)
        
        # Load call report data
        load_cu_call_reports_to_bq(zip_file, project_id)
    
    logger.info("\n" + "="*80)
    logger.info("All credit union call report files processed!")
    logger.info("="*80)


if __name__ == '__main__':
    import sys
    desktop_path = sys.argv[1] if len(sys.argv) > 1 else None
    process_all_cu_call_reports(desktop_path)

