#!/usr/bin/env python3
"""
Verification script to check that DataExplorer changes are properly loaded.
Run this after making code changes to verify they're active.
"""

import sys
import requests
import json
from pathlib import Path

# Calculate repo root: verify_changes.py is in apps/dataexplorer/
# So we need to go up 2 levels: apps/dataexplorer -> apps -> repo root
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.dataexplorer.config import DataExplorerConfig

def check_server_running():
    """Check if the Flask server is running and responding."""
    try:
        url = f"http://127.0.0.1:{DataExplorerConfig.PORT}/"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            print(f"✓ Server is running on port {DataExplorerConfig.PORT}")
            return True
        else:
            print(f"✗ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Server is not running on port {DataExplorerConfig.PORT}")
        return False
    except Exception as e:
        print(f"✗ Error checking server: {e}")
        return False

def check_cache_headers():
    """Verify cache-busting headers are present."""
    try:
        url = f"http://127.0.0.1:{DataExplorerConfig.PORT}/"
        response = requests.get(url, timeout=2)
        headers = response.headers
        
        checks = {
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        all_good = True
        for header, expected in checks.items():
            actual = headers.get(header, '')
            if expected in actual or header == 'Expires' and actual == '0':
                print(f"✓ {header} header is correct")
            else:
                print(f"✗ {header} header missing or incorrect: {actual}")
                all_good = False
        
        if 'ETag' in headers:
            print(f"✓ ETag header present: {headers['ETag']}")
        else:
            print("✗ ETag header missing")
            all_good = False
        
        return all_good
    except Exception as e:
        print(f"✗ Error checking headers: {e}")
        return False

def check_api_endpoint():
    """Test a simple API endpoint to verify it's working."""
    try:
        url = f"http://127.0.0.1:{DataExplorerConfig.PORT}/api/states"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'data' in data:
                print(f"✓ API endpoint working, returned {len(data.get('data', []))} states")
                return True
            else:
                print(f"✗ API returned unexpected format: {data}")
                return False
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking API: {e}")
        return False

def check_code_changes():
    """Check that recent code changes are present in the files."""
    checks = [
        {
            'file': 'apps/dataexplorer/area_analysis_processor.py',
            'pattern': 'def create_branch_income_neighborhood_table',
            'description': 'Branch income neighborhood table function'
        },
        {
            'file': 'apps/dataexplorer/static/js/dashboard.js',
            'pattern': 'dataType === \'branches\' ? \'2025\' : \'2024\'',
            'description': '2025 data for branches in feature cards'
        },
        {
            'file': 'apps/dataexplorer/app.py',
            'pattern': 'add_cache_busting_headers',
            'description': 'Cache-busting helper function'
        },
        {
            'file': 'apps/dataexplorer/area_analysis_processor.py',
            'pattern': 'def clean_bank_name',
            'description': 'Bank name cleaning function'
        }
    ]
    
    all_good = True
    for check in checks:
        file_path = REPO_ROOT / check['file']
        if file_path.exists():
            content = file_path.read_text(encoding='utf-8')
            if check['pattern'] in content:
                print(f"✓ {check['description']} found in {check['file']}")
            else:
                print(f"✗ {check['description']} NOT found in {check['file']}")
                all_good = False
        else:
            print(f"✗ File not found: {check['file']}")
            all_good = False
    
    return all_good

def main():
    """Run all verification checks."""
    print("=" * 80)
    print("DataExplorer Change Verification")
    print("=" * 80)
    print()
    
    results = []
    
    print("1. Checking code changes...")
    results.append(('Code Changes', check_code_changes()))
    print()
    
    print("2. Checking server status...")
    results.append(('Server Running', check_server_running()))
    print()
    
    if results[-1][1]:  # If server is running
        print("3. Checking cache-busting headers...")
        results.append(('Cache Headers', check_cache_headers()))
        print()
        
        print("4. Testing API endpoint...")
        results.append(('API Endpoint', check_api_endpoint()))
        print()
    
    print("=" * 80)
    print("Summary:")
    print("=" * 80)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✓ All checks passed! Changes should be visible.")
        print("\nNext steps:")
        print("  1. Hard refresh browser: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)")
        print("  2. Or open DevTools → Network tab → Check 'Disable cache'")
    else:
        print("✗ Some checks failed. Please review the errors above.")
        print("\nCommon fixes:")
        print("  1. Restart the Flask server: python run_dataexplorer.py")
        print("  2. Clear browser cache")
        print("  3. Check that all code changes were saved")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

