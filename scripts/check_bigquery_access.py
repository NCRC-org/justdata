#!/usr/bin/env python3
"""
Check BigQuery access and dataset existence.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import bigquery
from justdata.shared.utils.bigquery_client import get_bigquery_client

PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'hdma1-242116')
DATASET_ID = 'justdata'

def check_access():
    """Check BigQuery access and dataset."""
    print("=" * 70)
    print("BigQuery Access Check")
    print("=" * 70)
    print()
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        print(f"✅ BigQuery client created successfully")
        print(f"   Project: {PROJECT_ID}")
        print()
        
        # Check if dataset exists
        try:
            dataset = client.get_dataset(f"{PROJECT_ID}.{DATASET_ID}")
            print(f"✅ Dataset '{DATASET_ID}' exists")
            print(f"   Location: {dataset.location}")
            print()
        except Exception as e:
            print(f"❌ Dataset '{DATASET_ID}' not found or not accessible")
            print(f"   Error: {e}")
            print()
            print("Please ensure:")
            print(f"   1. Dataset '{DATASET_ID}' exists in project '{PROJECT_ID}'")
            print(f"   2. Your service account has access to the dataset")
            return False
        
        # Check if we can list tables
        try:
            tables = list(client.list_tables(dataset))
            print(f"✅ Can list tables in dataset ({len(tables)} existing tables)")
            if tables:
                print("   Existing tables:")
                for table in tables[:10]:  # Show first 10
                    print(f"     - {table.table_id}")
                if len(tables) > 10:
                    print(f"     ... and {len(tables) - 10} more")
            print()
        except Exception as e:
            print(f"⚠️  Cannot list tables: {e}")
            print()
        
        # Check if we can create a test table
        test_table_id = f"{PROJECT_ID}.{DATASET_ID}.__test_table_access__"
        try:
            # Try to create a small test table
            schema = [
                bigquery.SchemaField("test_col", "STRING", mode="REQUIRED"),
            ]
            test_table = bigquery.Table(test_table_id, schema=schema)
            test_table = client.create_table(test_table)
            print("✅ Can create tables in dataset")
            # Clean up test table
            client.delete_table(test_table_id)
            print("   (Test table created and deleted)")
            print()
            return True
        except Exception as e:
            print(f"❌ Cannot create tables in dataset")
            print(f"   Error: {e}")
            print()
            print("Required permissions:")
            print("   - bigquery.tables.create")
            print("   - bigquery.tables.update")
            print("   - bigquery.tables.delete (for cleanup)")
            print()
            print("To grant permissions, run:")
            print(f"   gcloud projects add-iam-policy-binding {PROJECT_ID} \\")
            print(f"     --member='serviceAccount:YOUR_SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com' \\")
            print(f"     --role='roles/bigquery.dataEditor'")
            print()
            return False
            
    except Exception as e:
        print(f"❌ Error checking access: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = check_access()
    sys.exit(0 if success else 1)

