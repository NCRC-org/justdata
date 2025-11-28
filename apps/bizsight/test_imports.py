#!/usr/bin/env python3
"""Quick test to verify all imports work before starting server."""

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

print("Testing BizSight imports...")
print(f"Repo root: {REPO_ROOT}")
print()

errors = []

try:
    print("1. Testing config...")
    from apps.bizsight.config import BizSightConfig, TEMPLATES_DIR_STR, STATIC_DIR_STR
    print(f"   ✓ Config imported")
    print(f"   ✓ Templates: {TEMPLATES_DIR_STR}")
    print(f"   ✓ Static: {STATIC_DIR_STR}")
except Exception as e:
    errors.append(f"Config import failed: {e}")
    print(f"   ✗ Error: {e}")

try:
    print("\n2. Testing data_utils...")
    from apps.bizsight.data_utils import get_available_counties
    print("   ✓ data_utils imported")
except Exception as e:
    errors.append(f"data_utils import failed: {e}")
    print(f"   ✗ Error: {e}")

try:
    print("\n3. Testing core...")
    from apps.bizsight.core import run_analysis
    print("   ✓ core imported")
except Exception as e:
    errors.append(f"core import failed: {e}")
    print(f"   ✗ Error: {e}")

try:
    print("\n4. Testing report_builder...")
    from apps.bizsight.report_builder import create_top_lenders_table, create_county_summary_table
    print("   ✓ report_builder imported")
except Exception as e:
    errors.append(f"report_builder import failed: {e}")
    print(f"   ✗ Error: {e}")

try:
    print("\n5. Testing ai_analysis...")
    from apps.bizsight.ai_analysis import BizSightAnalyzer
    print("   ✓ ai_analysis imported")
except Exception as e:
    errors.append(f"ai_analysis import failed: {e}")
    print(f"   ✗ Error: {e}")

try:
    print("\n6. Testing utils...")
    from apps.bizsight.utils.bigquery_client import BigQueryClient
    from apps.bizsight.utils.progress_tracker import ProgressTracker
    from apps.bizsight.utils.ai_provider import AIProvider
    print("   ✓ utils imported")
except Exception as e:
    errors.append(f"utils import failed: {e}")
    print(f"   ✗ Error: {e}")

try:
    print("\n7. Testing Flask app...")
    from apps.bizsight.app import app
    print("   ✓ Flask app imported")
    print(f"   ✓ App name: {app.name}")
except Exception as e:
    errors.append(f"Flask app import failed: {e}")
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
if errors:
    print("❌ IMPORT ERRORS FOUND:")
    for error in errors:
        print(f"   - {error}")
    sys.exit(1)
else:
    print("✅ All imports successful!")
    print("\nServer should start without import errors.")
    sys.exit(0)

