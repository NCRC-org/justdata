"""
Run BigQuery migrations for Workflow app.
Usage: python -m justdata.apps.workflow.schema.run_migration
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from justdata.shared.utils.unified_env import ensure_unified_env_loaded
from justdata.shared.utils.bigquery_client import get_bigquery_client

# Ensure environment is loaded
ensure_unified_env_loaded()

PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')


def run_migrations():
    """Execute all migration SQL statements."""
    print(f"Running Workflow migrations for project: {PROJECT_ID}")
    print("=" * 50)

    try:
        client = get_bigquery_client(PROJECT_ID)
        if not client:
            raise Exception("get_bigquery_client returned None")
    except Exception as e:
        print(f"Error connecting to BigQuery: {e}")
        print("Make sure GOOGLE_APPLICATION_CREDENTIALS_JSON is set in .env")
        return False

    # Read and execute schema
    schema_path = Path(__file__).parent / 'create_tables.sql'
    with open(schema_path, 'r') as f:
        sql = f.read().replace('{PROJECT_ID}', PROJECT_ID)

    # Remove comment lines and split by semicolon
    lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
    sql_cleaned = '\n'.join(lines)
    statements = [s.strip() for s in sql_cleaned.split(';') if s.strip()]

    print(f"Found {len(statements)} SQL statements to execute")

    success_count = 0
    for stmt in statements:
        # Get first line for display
        first_line = stmt.split('\n')[0][:60]
        try:
            print(f"\nExecuting: {first_line}...")
            client.query(stmt).result()
            print("  [OK] Success")
            success_count += 1
        except Exception as e:
            error_str = str(e)
            if 'Already Exists' in error_str:
                print(f"  [SKIP] Already exists")
                success_count += 1
            else:
                print(f"  [ERROR] {e}")

    # Initialize counter if not exists
    print("\nInitializing task counter...")
    try:
        check_sql = f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.justdata.workflow_task_counter`"
        result = list(client.query(check_sql).result())
        if result[0].cnt == 0:
            init_sql = f"""
            INSERT INTO `{PROJECT_ID}.justdata.workflow_task_counter` (counter_name, current_value)
            VALUES ('task_id', 0)
            """
            client.query(init_sql).result()
            print("  [OK] Counter initialized to 0")
        else:
            print("  [SKIP] Counter already exists")
    except Exception as e:
        print(f"  [ERROR] Initializing counter: {e}")

    print("\n" + "=" * 50)
    print(f"Migration complete. {success_count}/{len(statements)} statements successful.")
    return success_count == len(statements)


def verify_tables():
    """Verify all required tables exist."""
    print("\nVerifying tables...")

    try:
        client = get_bigquery_client(PROJECT_ID)
        if not client:
            raise Exception("get_bigquery_client returned None")
    except Exception as e:
        print(f"Error connecting to BigQuery: {e}")
        return False

    expected_tables = ['workflow_tasks', 'workflow_positions', 'workflow_task_counter']

    sql = f"""
    SELECT table_name
    FROM `{PROJECT_ID}.justdata.INFORMATION_SCHEMA.TABLES`
    WHERE table_name LIKE 'workflow%'
    """

    try:
        result = client.query(sql).result()
        found_tables = [row.table_name for row in result]

        all_found = True
        for table in expected_tables:
            if table in found_tables:
                print(f"  [OK] {table}")
            else:
                print(f"  [MISSING] {table}")
                all_found = False

        return all_found
    except Exception as e:
        print(f"  [ERROR] Verifying tables: {e}")
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run Workflow BigQuery migrations')
    parser.add_argument('--verify', action='store_true', help='Verify tables exist')
    args = parser.parse_args()

    if args.verify:
        verify_tables()
    else:
        run_migrations()
        verify_tables()
