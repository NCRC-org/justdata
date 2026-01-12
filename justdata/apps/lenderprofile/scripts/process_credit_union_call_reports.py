#!/usr/bin/env python3
"""
Process Credit Union Call Report ZIP files and load into BigQuery.

The call report data contains credit union branch and financial information
that can be used for branch network analysis similar to bank SOD data.

Files are located at:
C:\Users\jrichardson\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\call-report-data-YYYY-06.zip
"""

import sys
import os
import zipfile
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.utils.unified_env import ensure_unified_env_loaded
from shared.utils.bigquery_client import get_bigquery_client
from google.cloud import bigquery

ensure_unified_env_loaded(verbose=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CreditUnionCallReportProcessor:
    """Process credit union call report ZIP files and load into BigQuery."""
    
    def __init__(self, project_id: str = None):
        """
        Initialize processor.
        
        Args:
            project_id: GCP project ID (defaults to environment variable)
        """
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID', 'hdma1-242116')
        self.client = get_bigquery_client(self.project_id)
        self.dataset_id = 'credit_unions'
        self.table_id = 'call_reports'
        
    def extract_zip(self, zip_path: str, extract_dir: str) -> List[str]:
        """
        Extract ZIP file and return list of extracted file paths.
        
        Args:
            zip_path: Path to ZIP file
            extract_dir: Directory to extract to
            
        Returns:
            List of extracted file paths
        """
        extracted_files = []
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            extracted_files = [os.path.join(extract_dir, f) for f in zip_ref.namelist()]
        
        logger.info(f"Extracted {len(extracted_files)} files from {zip_path}")
        return extracted_files
    
    def parse_call_report_file(self, file_path: str, year: int) -> List[Dict[str, Any]]:
        """
        Parse a call report file (CSV format).
        
        Credit union call reports contain:
        - "Credit Union Branch Information.txt" - branch locations
        - "FOICU.txt" - main credit union information (with RSSD)
        
        Args:
            file_path: Path to call report file
            year: Year of the data
            
        Returns:
            List of parsed records
        """
        records = []
        filename = os.path.basename(file_path).lower()
        
        # Skip documentation files
        if 'des' in filename or 'readme' in filename:
            return records
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first line to check format
                first_line = f.readline()
                f.seek(0)
                
                # Credit union files use CSV with quoted fields
                reader = csv.DictReader(f, quotechar='"')
                
                for row in reader:
                    # Clean up field names (remove quotes and spaces)
                    cleaned_row = {}
                    for key, value in row.items():
                        clean_key = key.strip().strip('"').replace(' ', '_').lower()
                        cleaned_row[clean_key] = value.strip('"') if isinstance(value, str) else value
                    
                    # Add year and source file info
                    cleaned_row['year'] = year
                    cleaned_row['source_file'] = os.path.basename(file_path)
                    
                    # Extract cycle date if available
                    if 'cycle_date' in cleaned_row:
                        try:
                            # Parse date like "6/30/2025 0:00:00"
                            date_str = cleaned_row['cycle_date'].split()[0]
                            cleaned_row['report_date'] = date_str
                        except:
                            pass
                    
                    records.append(cleaned_row)
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
        
        logger.info(f"Parsed {len(records)} records from {os.path.basename(file_path)}")
        return records
    
    def infer_schema(self, records: List[Dict[str, Any]]) -> List[bigquery.SchemaField]:
        """
        Infer BigQuery schema from records.
        
        Args:
            records: Sample records to infer schema from
            
        Returns:
            List of BigQuery schema fields
        """
        if not records:
            return []
        
        schema = []
        sample = records[0]
        
        for field_name, value in sample.items():
            field_type = 'STRING'  # Default
            
            if isinstance(value, (int, float)):
                if isinstance(value, int):
                    field_type = 'INT64'
                else:
                    field_type = 'FLOAT64'
            elif isinstance(value, bool):
                field_type = 'BOOL'
            elif isinstance(value, str):
                # Try to determine if it's a date or number
                try:
                    int(value)
                    field_type = 'INT64'
                except (ValueError, TypeError):
                    try:
                        float(value)
                        field_type = 'FLOAT64'
                    except (ValueError, TypeError):
                        field_type = 'STRING'
            
            schema.append(bigquery.SchemaField(
                field_name.replace(' ', '_').replace('-', '_').lower(),
                field_type,
                mode='NULLABLE'
            ))
        
        return schema
    
    def create_dataset_and_table(self, schema: List[bigquery.SchemaField], overwrite: bool = False):
        """
        Create BigQuery dataset and table if they don't exist.
        
        Args:
            schema: Table schema
            overwrite: If True, drop and recreate table
        """
        dataset_ref = self.client.dataset(self.dataset_id)
        
        # Create dataset if it doesn't exist
        try:
            self.client.get_dataset(dataset_ref)
            logger.info(f"Dataset {self.dataset_id} already exists")
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = 'US'
            dataset = self.client.create_dataset(dataset, exists_ok=True)
            logger.info(f"Created dataset {self.dataset_id}")
        
        table_ref = dataset_ref.table(self.table_id)
        
        # Create or recreate table
        if overwrite:
            try:
                self.client.delete_table(table_ref)
                logger.info(f"Dropped existing table {self.table_id}")
            except Exception:
                pass
        
        try:
            self.client.get_table(table_ref)
            if not overwrite:
                logger.info(f"Table {self.table_id} already exists (use overwrite=True to recreate)")
                return
        except Exception:
            pass
        
        table = bigquery.Table(table_ref, schema=schema)
        table = self.client.create_table(table)
        logger.info(f"Created table {self.table_id} with schema")
    
    def load_data_to_bigquery(self, records: List[Dict[str, Any]], schema: List[bigquery.SchemaField]):
        """
        Load records into BigQuery table.
        
        Args:
            records: Records to load
            schema: Table schema
        """
        if not records:
            logger.warning("No records to load")
            return
        
        # Normalize field names to match schema
        normalized_records = []
        schema_field_names = {f.name.lower(): f.name for f in schema}
        
        for record in records:
            normalized = {}
            for key, value in record.items():
                normalized_key = key.replace(' ', '_').replace('-', '_').lower()
                if normalized_key in schema_field_names:
                    normalized[normalized_key] = value
                else:
                    # Try to find close match
                    for schema_name in schema_field_names:
                        if normalized_key in schema_name or schema_name in normalized_key:
                            normalized[schema_field_names[schema_name]] = value
                            break
                    else:
                        normalized[normalized_key] = value
            normalized_records.append(normalized)
        
        table_ref = self.client.dataset(self.dataset_id).table(self.table_id)
        
        job_config = bigquery.LoadJobConfig(
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
        )
        
        # Convert to JSON lines format
        import json
        json_lines = '\n'.join([json.dumps(r) for r in normalized_records])
        
        job = self.client.load_table_from_string(
            json_lines,
            table_ref,
            job_config=job_config
        )
        
        job.result()  # Wait for job to complete
        logger.info(f"Loaded {len(normalized_records)} records into {self.dataset_id}.{self.table_id}")
    
    def process_year(self, zip_path: str, year: int, extract_dir: str = None) -> int:
        """
        Process a single year's call report ZIP file.
        
        Args:
            zip_path: Path to ZIP file
            year: Year of the data
            extract_dir: Directory to extract to (defaults to temp dir)
            
        Returns:
            Number of records processed
        """
        if extract_dir is None:
            extract_dir = os.path.join(os.path.dirname(zip_path), f'extracted_{year}')
        
        os.makedirs(extract_dir, exist_ok=True)
        
        # Extract ZIP
        extracted_files = self.extract_zip(zip_path, extract_dir)
        
        # Parse all files
        all_records = []
        for file_path in extracted_files:
            if os.path.isfile(file_path):
                try:
                    records = self.parse_call_report_file(file_path, year)
                    all_records.extend(records)
                except Exception as e:
                    logger.error(f"Error parsing {file_path}: {e}")
        
        if not all_records:
            logger.warning(f"No records found in {zip_path}")
            return 0
        
        # Infer schema from first batch
        schema = self.infer_schema(all_records[:1000])  # Use first 1000 records for schema
        
        # Create table (first time only)
        if year == min([2021, 2022, 2023, 2024, 2025]):  # First year processed
            self.create_dataset_and_table(schema, overwrite=False)
        
        # Load data
        self.load_data_to_bigquery(all_records, schema)
        
        return len(all_records)
    
    def process_all_years(self, base_path: str, years: List[int] = None):
        """
        Process all call report ZIP files.
        
        Args:
            base_path: Base directory containing ZIP files
            years: List of years to process (defaults to 2021-2025)
        """
        if years is None:
            years = [2021, 2022, 2023, 2024, 2025]
        
        total_records = 0
        
        for year in years:
            zip_filename = f'call-report-data-{year}-06.zip'
            zip_path = os.path.join(base_path, zip_filename)
            
            if not os.path.exists(zip_path):
                logger.warning(f"ZIP file not found: {zip_path}")
                continue
            
            logger.info(f"Processing {year} call report data...")
            try:
                count = self.process_year(zip_path, year)
                total_records += count
                logger.info(f"Processed {count} records for {year}")
            except Exception as e:
                logger.error(f"Error processing {year}: {e}", exc_info=True)
        
        logger.info(f"Total records processed: {total_records}")


def main():
    """Main entry point."""
    base_path = r"C:\Users\jrichardson\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop"
    
    processor = CreditUnionCallReportProcessor()
    processor.process_all_years(base_path)


if __name__ == '__main__':
    main()

