"""
Configuration for MergerMeter application.
"""

import os
from pathlib import Path

# Base directory for this application
BASE_DIR = Path(__file__).parent
# Base directory for justdata package (2 levels up from config.py: mergermeter -> apps -> root)
JUSTDATA_BASE = BASE_DIR.parent.parent

# Template and static directories
TEMPLATES_DIR = str(BASE_DIR / 'templates')
# Use shared static folder (same as BranchSeeker and LendSight)
STATIC_DIR = str(JUSTDATA_BASE / 'shared' / 'web' / 'static')
OUTPUT_DIR = BASE_DIR / 'output'

# Excel template file path (for matching original merger report format)
# Support multiple path options for flexibility across different environments
# 1. Check environment variable first (for CI/CD, Docker, etc.)
MERGER_REPORT_BASE_ENV = os.getenv('MERGER_REPORT_BASE')
if MERGER_REPORT_BASE_ENV:
    MERGER_REPORT_BASE = Path(MERGER_REPORT_BASE_ENV)
else:
    # 2. Try relative path from workspace root (for GitHub/main branch)
    # Look for 1_Merger_Report relative to the workspace root
    workspace_root = JUSTDATA_BASE.parent if JUSTDATA_BASE.name == '#JustData_Repo' else JUSTDATA_BASE.parent.parent
    relative_merger_path = workspace_root / '1_Merger_Report'
    
    # 3. Fallback to absolute path (for local development)
    absolute_merger_path = Path(r'C:\DREAM\1_Merger_Report')
    
    # Use whichever exists, preferring relative path
    if relative_merger_path.exists():
        MERGER_REPORT_BASE = relative_merger_path
    elif absolute_merger_path.exists():
        MERGER_REPORT_BASE = absolute_merger_path
    else:
        MERGER_REPORT_BASE = None

# Template files - set to None if base doesn't exist (will use fallback in excel_generator)
if MERGER_REPORT_BASE:
    TEMPLATE_FILE = MERGER_REPORT_BASE / 'reports' / '251101_PNC_Bank_FirstBank_Merger' / 'PNC Bank_FirstBank_Goal_Setting_Analysis.xlsx'
    CLEAN_TEMPLATE_FILE = MERGER_REPORT_BASE / 'reports' / '_shared' / 'templates' / 'clean_goal_setting_template.xlsx'
    
    # Only set if files actually exist
    if not TEMPLATE_FILE.exists():
        TEMPLATE_FILE = None
    if not CLEAN_TEMPLATE_FILE.exists():
        CLEAN_TEMPLATE_FILE = None
else:
    TEMPLATE_FILE = None
    CLEAN_TEMPLATE_FILE = None

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(exist_ok=True)

# BigQuery Project ID
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'hdma1-242116')

