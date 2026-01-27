"""
Migration: Add monday_item_id column and sync_log table for Monday.com integration.

Run this migration to enable two-way sync between Monday.com and BigQuery.

Usage:
    python -m justdata.apps.workflow.schema.add_monday_sync
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from justdata.shared.utils.bigquery_client import get_bigquery_client


PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')
DATASET = 'justdata'


def run_migration():
    """Add monday_item_id column and sync_log table."""
    client = get_bigquery_client(PROJECT_ID)

    print(f"Running Monday sync migration on {PROJECT_ID}.{DATASET}...")

    # 1. Add monday_item_id column to workflow_tasks
    print("\n1. Adding monday_item_id column to workflow_tasks...")
    try:
        sql = f"""
        ALTER TABLE `{PROJECT_ID}.{DATASET}.workflow_tasks`
        ADD COLUMN IF NOT EXISTS monday_item_id STRING
        """
        client.query(sql).result()
        print("   [OK] monday_item_id column added (or already exists)")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            print("   [OK] monday_item_id column already exists")
        else:
            print(f"   [ERROR] {e}")

    # 2. Create sync_log table
    print("\n2. Creating workflow_sync_log table...")
    try:
        sql = f"""
        CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.{DATASET}.workflow_sync_log` (
            sync_id STRING NOT NULL,
            sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            direction STRING,
            items_created INT64,
            items_updated INT64,
            items_skipped INT64,
            errors ARRAY<STRING>,
            user_email STRING,
            details STRING
        )
        OPTIONS (
            description = 'Sync log for Monday.com ↔ BigQuery workflow synchronization'
        )
        """
        client.query(sql).result()
        print("   [OK] workflow_sync_log table created (or already exists)")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("   [OK] workflow_sync_log table already exists")
        else:
            print(f"   [ERROR] {e}")

    # 3. Create index on monday_item_id for faster lookups
    print("\n3. Note: BigQuery doesn't support indexes, but the column is ready for queries")

    print("\n" + "="*60)
    print("Migration complete!")
    print("\nNext steps:")
    print("1. Set MONDAY_API_KEY environment variable")
    print("2. Use /workflow/api/sync/from-monday to sync items")
    print("="*60)


if __name__ == '__main__':
    run_migration()
