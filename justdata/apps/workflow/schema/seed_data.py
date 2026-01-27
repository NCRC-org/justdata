"""
Seed workflow data from existing HTML file into BigQuery.
Usage: python -m justdata.apps.workflow.schema.seed_data
"""
import os
import sys
import random
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from justdata.shared.utils.unified_env import ensure_unified_env_loaded
from justdata.shared.utils.bigquery_client import get_bigquery_client

# Ensure environment is loaded
ensure_unified_env_loaded()

PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'hdma1-242116')
DATASET = 'justdata'
TASKS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_tasks'
POSITIONS_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_positions'
COUNTER_TABLE = f'{PROJECT_ID}.{DATASET}.workflow_task_counter'

# Canvas dimensions (must match the React app)
CANVAS_WIDTH = 1100
CANVAS_HEIGHT = 750

# Type zones for initial position calculation (must match React app)
TYPE_ZONES = {
    'legal': (0.12, 0.18),
    'infrastructure': (0.5, 0.06),
    'feature': (0.88, 0.2),
    'bug': (0.08, 0.82),
    'styling': (0.5, 0.96),
    'content': (0.92, 0.82),
}

COLLECTOR_POSITIONS = {
    'BUG_COMPLETE': (CANVAS_WIDTH * 0.18, CANVAS_HEIGHT * 0.72),
    'STYLE_COMPLETE': (CANVAS_WIDTH * 0.5, CANVAS_HEIGHT * 0.88),
    'CONTENT_COMPLETE': (CANVAS_WIDTH * 0.82, CANVAS_HEIGHT * 0.72),
}

GOAL_POSITION = (CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2)

# ============================================================
# TASK DATA - Extracted from justdata-workflow-v8.html
# ============================================================

TASKS = [
    # LEGAL
    {'id': 'S1', 'title': 'Get final disclaimer language from Rose', 'type': 'legal', 'priority': 'critical', 'app': '', 'notes': 'Need legal-approved text for all reports and applications. BLOCKS EARLY ACCESS LAUNCH', 'dependencies': [], 'status': 'open'},
    {'id': 'S2', 'title': 'Get guidance on copyright requirements and implementation', 'type': 'legal', 'priority': 'critical', 'app': '', 'notes': 'What content needs copyright notices? How should they be displayed?', 'dependencies': [], 'status': 'open'},
    {'id': 'S3', 'title': 'Get legal clearance for early access launch', 'type': 'legal', 'priority': 'critical', 'app': '', 'notes': 'Rose must approve platform for external user testing before marketing announcement', 'dependencies': ['S1', 'S2'], 'status': 'open'},
    {'id': 'C13', 'title': 'Disclaimer language and placement review', 'type': 'legal', 'priority': 'medium', 'app': '', 'notes': 'Per Rose (corporate counsel). Implement after S1 approved.', 'dependencies': ['S1', 'S3'], 'status': 'open'},

    # INFRASTRUCTURE
    {'id': 'S5', 'title': 'Create uptime notification structure and status page', 'type': 'infrastructure', 'priority': 'high', 'app': '', 'notes': 'Implement monitoring alerts, public status page at status.justdata.org', 'dependencies': [], 'status': 'open'},
    {'id': 'S6', 'title': 'Deploy interactive project map visualization', 'type': 'infrastructure', 'priority': 'high', 'app': '', 'notes': 'This tool! Force-directed graph showing all tasks', 'dependencies': [], 'status': 'open'},
    {'id': 'I1', 'title': 'Add CENSUS_API_KEY environment variable to Cloud Run', 'type': 'infrastructure', 'priority': 'critical', 'app': 'DataExplorer', 'notes': 'Required for housing data tables to populate', 'dependencies': [], 'status': 'open'},
    {'id': 'I2', 'title': 'Enable Cloud Run Admin API', 'type': 'infrastructure', 'priority': 'high', 'app': '', 'notes': 'IMMEDIATE priority', 'dependencies': [], 'status': 'open'},
    {'id': 'I3', 'title': 'Grant BigQuery Data Viewer permission to service account', 'type': 'infrastructure', 'priority': 'high', 'app': '', 'notes': 'IMMEDIATE priority', 'dependencies': [], 'status': 'open'},
    {'id': 'I4', 'title': 'Deploy recent test changes to production', 'type': 'infrastructure', 'priority': 'high', 'app': '', 'notes': 'Deploy to justdata.org when ready', 'dependencies': ['S3', 'C1', 'C2', 'S5', 'I2', 'I3'], 'status': 'open'},
    {'id': 'I5', 'title': 'Enable Firebase to BigQuery export (daily/streaming)', 'type': 'infrastructure', 'priority': 'medium', 'app': 'Analytics', 'notes': 'Required for Analytics Dashboard', 'dependencies': [], 'status': 'open'},

    # FEATURES
    {'id': 'S4', 'title': 'Launch early access announcement with Alyssa', 'type': 'feature', 'priority': 'high', 'app': '', 'notes': 'Announce JustData availability for early access testing', 'dependencies': ['S3'], 'status': 'open'},
    {'id': 'C1', 'title': 'Analytics Dashboard - Connect real BigQuery data instead of mock data', 'type': 'feature', 'priority': 'high', 'app': 'Analytics', 'notes': 'Infrastructure exists with 284 backfilled events and API endpoints, but frontend not connected', 'dependencies': ['I5'], 'status': 'open'},
    {'id': 'C2', 'title': 'Fix HUD Low-Mod population data in Area Analysis', 'type': 'feature', 'priority': 'high', 'app': 'DataExplorer', 'notes': 'Section 2, Table 2.5 missing Low-to-Moderate Income population data', 'dependencies': ['I1'], 'status': 'open'},
    {'id': 'C9', 'title': 'Add cached reports feature for Lender and Area Analysis', 'type': 'feature', 'priority': 'medium', 'app': 'DataExplorer', 'notes': 'Save to BigQuery like LendSight does', 'dependencies': ['I4'], 'status': 'open'},
    {'id': 'C10', 'title': 'Tone down adjectives in AI-generated narrative text', 'type': 'feature', 'priority': 'medium', 'app': '', 'notes': 'Credibility and legal concern - need more professional, objective tone', 'dependencies': ['S4'], 'status': 'open'},
    {'id': 'C11', 'title': 'Add national trend data for context in reports', 'type': 'feature', 'priority': 'medium', 'app': '', 'notes': 'Helps users compare local metrics to national averages', 'dependencies': ['I4'], 'status': 'open'},
    {'id': 'S17', 'title': 'Cross-app lender linking - clickable lender names', 'type': 'feature', 'priority': 'low', 'app': '', 'notes': 'When apps mention a lender, make name clickable to open DataExplorer Lender Profile', 'dependencies': ['C1', 'I4'], 'status': 'open'},

    # BUGS
    {'id': 'C5', 'title': 'Hamburger menu navigation links incorrect/outdated', 'type': 'bug', 'priority': 'medium', 'app': '', 'notes': 'Some links (e.g., Admin) lead to wrong pages', 'dependencies': [], 'status': 'open'},
    {'id': 'C6', 'title': 'MergerMeter single bank selection missing assessment area options', 'type': 'bug', 'priority': 'medium', 'app': 'MergerMeter', 'notes': 'Should match merger analysis options (select specific AAs)', 'dependencies': [], 'status': 'open'},
    {'id': 'C7', 'title': 'BranchMapper census tract layers not loading reliably', 'type': 'bug', 'priority': 'medium', 'app': 'BranchMapper', 'notes': 'Income Levels layer fails inconsistently', 'dependencies': [], 'status': 'open'},
    {'id': 'C8', 'title': 'Gray out "CBSAs with >1% of branches" option for non-banks', 'type': 'bug', 'priority': 'medium', 'app': 'DataExplorer', 'notes': 'Check institution type before showing option', 'dependencies': [], 'status': 'open'},
    {'id': 'C16', 'title': 'Remove "(optional)" from ResID field label', 'type': 'bug', 'priority': 'low', 'app': 'MergerMeter', 'notes': 'Label cleanup', 'dependencies': [], 'status': 'open'},
    {'id': 'C17', 'title': 'NCRC logo appears all black in progress popup', 'type': 'bug', 'priority': 'low', 'app': 'LenderProfile', 'notes': 'Not blocking initial release', 'dependencies': [], 'status': 'open'},
    {'id': 'C18', 'title': "Lender search doesn't verify via GLEIF", 'type': 'bug', 'priority': 'low', 'app': 'LenderProfile', 'notes': 'Not in initial release', 'dependencies': [], 'status': 'open'},
    {'id': 'C19', 'title': 'Lender Interest map missing researcher count on markers', 'type': 'bug', 'priority': 'low', 'app': 'Analytics', 'notes': 'Numbers should show on map markers', 'dependencies': [], 'status': 'open'},
    {'id': 'C20', 'title': "Map controls don't auto-detect user's county", 'type': 'bug', 'priority': 'low', 'app': 'BranchMapper', 'notes': 'Currently only detects state', 'dependencies': [], 'status': 'open'},
    {'id': 'C21', 'title': 'Lender search takes too long to load', 'type': 'bug', 'priority': 'low', 'app': 'DataExplorer', 'notes': 'Performance optimization needed', 'dependencies': [], 'status': 'open'},

    # STYLING
    {'id': 'C3', 'title': 'Area Analysis Population Demographics chart does not expand to fill width', 'type': 'styling', 'priority': 'medium', 'app': 'DataExplorer', 'notes': 'Section 1 Table 1 - chart appears narrow/cramped. NEEDS RETEST', 'dependencies': [], 'status': 'open'},
    {'id': 'C4', 'title': 'Area Analysis tables overflow off right side of report cards', 'type': 'styling', 'priority': 'medium', 'app': 'DataExplorer', 'notes': 'Need responsive table design or horizontal scroll. NEEDS RETEST', 'dependencies': [], 'status': 'open'},
    {'id': 'C14', 'title': 'User workflow documentation and guided tours', 'type': 'styling', 'priority': 'medium', 'app': '', 'notes': 'Tooltips for first-time users', 'dependencies': [], 'status': 'open'},
    {'id': 'C15', 'title': 'Mobile and tablet responsiveness evaluation', 'type': 'styling', 'priority': 'medium', 'app': '', 'notes': 'Determine optimization feasibility', 'dependencies': [], 'status': 'open'},
    {'id': 'S8', 'title': 'Create AI narrative style guide', 'type': 'styling', 'priority': 'medium', 'app': '', 'notes': 'Document tone guidelines: professional, objective, less adjectives', 'dependencies': [], 'status': 'open'},
    {'id': 'C22', 'title': 'Bank Branch Analysis browser tab shows "BranchSeeker"', 'type': 'styling', 'priority': 'low', 'app': 'DataExplorer', 'notes': 'Update page title', 'dependencies': [], 'status': 'open'},
    {'id': 'C23', 'title': 'BranchMapper missing current JustData footer', 'type': 'styling', 'priority': 'low', 'app': 'BranchMapper', 'notes': 'Add standard footer component', 'dependencies': [], 'status': 'open'},
    {'id': 'C24', 'title': 'Favicons not uniform across all pages', 'type': 'styling', 'priority': 'low', 'app': '', 'notes': 'Standardize favicons', 'dependencies': [], 'status': 'open'},

    # CONTENT
    {'id': 'S7', 'title': 'Film how-to videos for all apps (single filming day)', 'type': 'content', 'priority': 'medium', 'app': '', 'notes': '2-3 min each for: LendSight, BizSight, BranchSight, BranchMapper, MergerMeter, DataExplorer, LenderProfile, Analytics, ElectWatch.', 'dependencies': ['S4'], 'status': 'open'},
    {'id': 'S9', 'title': 'Conduct user testing sessions with NCRC members', 'type': 'content', 'priority': 'high', 'app': '', 'notes': 'Get feedback on workflows, identify pain points. PART OF EARLY ACCESS', 'dependencies': ['S4'], 'status': 'open'},
    {'id': 'S10', 'title': 'Create tooltip/guided tour content for first-time users', 'type': 'content', 'priority': 'medium', 'app': '', 'notes': 'Write copy for in-app guidance', 'dependencies': ['C14'], 'status': 'open'},
    {'id': 'S11', 'title': 'Create one-page feature sheets for each app', 'type': 'content', 'priority': 'low', 'app': '', 'notes': 'Marketing materials for member outreach', 'dependencies': ['S4'], 'status': 'open'},
    {'id': 'S12', 'title': 'Draft launch announcement for JustData 1.0', 'type': 'content', 'priority': 'low', 'app': '', 'notes': 'Internal announcement to NCRC network', 'dependencies': ['S4'], 'status': 'open'},
    {'id': 'S13', 'title': 'Schedule training session for NCRC staff', 'type': 'content', 'priority': 'low', 'app': '', 'notes': 'Walk through all applications, Q&A', 'dependencies': ['S4', 'S7'], 'status': 'open'},
    {'id': 'S14', 'title': 'Create FAQ document based on common questions', 'type': 'content', 'priority': 'low', 'app': '', 'notes': 'Build from user testing feedback', 'dependencies': ['S9'], 'status': 'open'},

    # COMPLETED TASKS
    {'id': 'D1', 'title': 'Create shared footer component', 'type': 'styling', 'priority': 'medium', 'app': '', 'notes': 'Created apps/shared/templates/components/standard_footer.html', 'dependencies': [], 'status': 'done'},
    {'id': 'D2', 'title': 'Standardize homepage footer with dynamic version numbers', 'type': 'styling', 'priority': 'medium', 'app': '', 'notes': 'All apps now use standardized footer', 'dependencies': ['D1'], 'status': 'done'},
    {'id': 'D3', 'title': 'Remove "Back to New Analysis" button from reports', 'type': 'styling', 'priority': 'low', 'app': 'LendSight', 'notes': 'Removed from LendSight, BizSight, BranchSight reports', 'dependencies': [], 'status': 'done'},
    {'id': 'D4', 'title': 'Remove "Print Report" button from reports', 'type': 'styling', 'priority': 'low', 'app': '', 'notes': 'Removed from LendSight, BizSight, BranchSight reports', 'dependencies': [], 'status': 'done'},
    {'id': 'D5', 'title': 'Standardize report header colors to dark navy', 'type': 'styling', 'priority': 'medium', 'app': '', 'notes': 'Changed to #1e3a5f across all apps', 'dependencies': [], 'status': 'done'},
    {'id': 'D6', 'title': 'Fix BranchSight template loading issue', 'type': 'bug', 'priority': 'high', 'app': 'BranchSight', 'notes': 'Fixed Jinja2 ChoiceLoader configuration', 'dependencies': [], 'status': 'done'},
    {'id': 'D7', 'title': 'Update DataExplorer footers to match standard', 'type': 'styling', 'priority': 'medium', 'app': 'DataExplorer', 'notes': 'Footers now consistent with other apps', 'dependencies': ['D1'], 'status': 'done'},
    {'id': 'D8', 'title': 'Diagnose housing data issue root cause', 'type': 'bug', 'priority': 'high', 'app': 'DataExplorer', 'notes': 'Identified: Census API calls failing due to missing CENSUS_API_KEY', 'dependencies': [], 'status': 'done'},
    {'id': 'D9', 'title': 'Create HOUSING_DATA_ISSUE_DIAGNOSIS.md document', 'type': 'content', 'priority': 'medium', 'app': '', 'notes': 'Comprehensive diagnostic document created', 'dependencies': ['D8'], 'status': 'done'},
    {'id': 'D10', 'title': 'Verify frontend handles empty data correctly', 'type': 'bug', 'priority': 'medium', 'app': 'DataExplorer', 'notes': 'Frontend displays "No data available" when backend returns empty arrays', 'dependencies': ['D8'], 'status': 'done'},
    {'id': 'D11', 'title': 'Verify backend error handling for Census API', 'type': 'bug', 'priority': 'medium', 'app': 'DataExplorer', 'notes': 'Backend gracefully handles API failures', 'dependencies': ['D8'], 'status': 'done'},
    {'id': 'D12', 'title': 'Set up Firebase Authentication', 'type': 'infrastructure', 'priority': 'high', 'app': '', 'notes': 'Multi-tier user permissions implemented', 'dependencies': [], 'status': 'done'},
    {'id': 'D13', 'title': 'Migrate MergerMeter to GCS storage', 'type': 'infrastructure', 'priority': 'high', 'app': 'MergerMeter', 'notes': 'Resolved container instance persistence issues', 'dependencies': [], 'status': 'done'},
    {'id': 'D14', 'title': 'Set up BigQuery analytics views', 'type': 'infrastructure', 'priority': 'medium', 'app': 'Analytics', 'notes': 'Views created for coalition intelligence', 'dependencies': [], 'status': 'done'},
    {'id': 'D15', 'title': 'Backfill 284 analytics events to BigQuery', 'type': 'infrastructure', 'priority': 'medium', 'app': 'Analytics', 'notes': 'Historical data loaded for dashboard', 'dependencies': ['D14'], 'status': 'done'},
]

COLLECTORS = [
    {'id': 'BUG_COMPLETE', 'title': 'All Bug Fixes Complete', 'type': 'collector', 'priority': 'collector', 'notes': 'Milestone: All bug fixes resolved and verified.', 'dependencies': [], 'is_collector': True, 'collector_for': 'bug', 'status': 'open'},
    {'id': 'STYLE_COMPLETE', 'title': 'All Styling Complete', 'type': 'collector', 'priority': 'collector', 'notes': 'Milestone: All UI/styling improvements implemented.', 'dependencies': [], 'is_collector': True, 'collector_for': 'styling', 'status': 'open'},
    {'id': 'CONTENT_COMPLETE', 'title': 'All Content Complete', 'type': 'collector', 'priority': 'collector', 'notes': 'Milestone: All documentation, videos, and training materials ready.', 'dependencies': [], 'is_collector': True, 'collector_for': 'content', 'status': 'open'},
]

GOAL = {
    'id': 'GOAL',
    'title': 'JustData 1.0 Public Launch',
    'type': 'goal',
    'priority': 'goal',
    'notes': 'The ultimate objective: Full public launch of JustData 1.0 platform with all applications production-ready, documented, and tested.',
    'dependencies': ['S4', 'I4', 'S9', 'BUG_COMPLETE', 'STYLE_COMPLETE', 'CONTENT_COMPLETE'],
    'is_goal': True,
    'status': 'open'
}


def compute_initial_position(task):
    """Compute initial position for a task based on its type."""
    if task.get('is_goal'):
        return GOAL_POSITION

    if task.get('is_collector'):
        return COLLECTOR_POSITIONS.get(task['id'], (CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2))

    type_zone = TYPE_ZONES.get(task['type'], (0.5, 0.5))
    # Add small random offset to prevent overlap
    x = type_zone[0] * CANVAS_WIDTH + (random.random() - 0.5) * 55
    y = type_zone[1] * CANVAS_HEIGHT + (random.random() - 0.5) * 35

    return (x, y)


def build_collector_dependencies(tasks):
    """Auto-populate collector dependencies based on task types."""
    bug_tasks = [t['id'] for t in tasks if t['type'] == 'bug' and t['status'] == 'open']
    styling_tasks = [t['id'] for t in tasks if t['type'] == 'styling' and t['status'] == 'open']
    content_tasks = [t['id'] for t in tasks if t['type'] == 'content' and t['status'] == 'open']

    for collector in COLLECTORS:
        if collector['collector_for'] == 'bug':
            collector['dependencies'] = bug_tasks
        elif collector['collector_for'] == 'styling':
            collector['dependencies'] = styling_tasks
        elif collector['collector_for'] == 'content':
            collector['dependencies'] = content_tasks


def seed_tasks(client):
    """Insert all tasks into BigQuery."""
    # Combine all task types
    build_collector_dependencies(TASKS)
    all_tasks = TASKS + COLLECTORS + [GOAL]

    now = datetime.utcnow()

    rows = []
    for task in all_tasks:
        rows.append({
            'id': task['id'],
            'title': task['title'],
            'type': task['type'],
            'priority': task['priority'],
            'status': task.get('status', 'open'),
            'app': task.get('app', ''),
            'notes': task.get('notes', ''),
            'dependencies': task.get('dependencies', []),
            'is_collector': task.get('is_collector', False),
            'is_goal': task.get('is_goal', False),
            'collector_for': task.get('collector_for'),
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'created_by': 'migration_script',
            'completed_at': now.isoformat() if task.get('status') == 'done' else None,
            'completed_by': 'migration_script' if task.get('status') == 'done' else None,
        })

    errors = client.insert_rows_json(TASKS_TABLE, rows)
    if errors:
        print(f"Errors inserting tasks: {errors}")
        raise Exception("Failed to insert tasks")

    print(f"  [OK] Inserted {len(rows)} tasks")
    return all_tasks


def seed_positions(client, tasks):
    """Insert initial positions for all tasks."""
    rows = []
    now = datetime.utcnow()

    for task in tasks:
        x, y = compute_initial_position(task)
        rows.append({
            'task_id': task['id'],
            'x': x,
            'y': y,
            'updated_at': now.isoformat(),
            'updated_by': 'migration_script',
        })

    errors = client.insert_rows_json(POSITIONS_TABLE, rows)
    if errors:
        print(f"Errors inserting positions: {errors}")
        raise Exception("Failed to insert positions")

    print(f"  [OK] Inserted {len(rows)} positions")


def update_task_counter(client, tasks):
    """Set the task counter to the highest existing ID number."""
    # Find highest numeric suffix from existing IDs
    max_num = 0
    for task in tasks:
        # Extract number from IDs like S1, C5, D15, etc.
        id_str = task['id']
        if id_str not in ['GOAL', 'BUG_COMPLETE', 'STYLE_COMPLETE', 'CONTENT_COMPLETE']:
            try:
                num = int(''.join(filter(str.isdigit, id_str)))
                max_num = max(max_num, num)
            except ValueError:
                pass

    # Update counter
    sql = f"""
    UPDATE `{COUNTER_TABLE}`
    SET current_value = {max_num}
    WHERE counter_name = 'task_id'
    """
    client.query(sql).result()
    print(f"  [OK] Set task counter to {max_num}")


def main():
    print("Seeding Workflow data into BigQuery")
    print(f"Project: {PROJECT_ID}")
    print("=" * 50)

    try:
        client = get_bigquery_client(PROJECT_ID)
        if not client:
            raise Exception("get_bigquery_client returned None")
    except Exception as e:
        print(f"Error connecting to BigQuery: {e}")
        return False

    # Check if data already exists
    try:
        check_sql = f"SELECT COUNT(*) as cnt FROM `{TASKS_TABLE}`"
        result = list(client.query(check_sql).result())
        if result[0].cnt > 0:
            response = input(f"\nTable already has {result[0].cnt} rows. Delete and reseed? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                return False

            # Clear existing data
            print("\nClearing existing data...")
            client.query(f"DELETE FROM `{TASKS_TABLE}` WHERE TRUE").result()
            client.query(f"DELETE FROM `{POSITIONS_TABLE}` WHERE TRUE").result()
            print("  [OK] Cleared existing data")
    except Exception as e:
        print(f"Note: Could not check existing data: {e}")

    print("\nInserting tasks...")
    tasks = seed_tasks(client)

    print("\nInserting positions...")
    seed_positions(client, tasks)

    print("\nUpdating task counter...")
    update_task_counter(client, tasks)

    print("\n" + "=" * 50)
    print("Seed complete!")
    print(f"  - {len(TASKS)} tasks")
    print(f"  - {len(COLLECTORS)} collectors")
    print(f"  - 1 goal")
    print(f"  - Total: {len(tasks)} records")

    return True


if __name__ == '__main__':
    main()
