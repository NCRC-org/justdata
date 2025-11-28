#!/usr/bin/env python3
"""
Verify that the fixes are in place and working.
"""

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

def verify_tract_fix():
    """Verify the tract matching fix is in place."""
    print("=" * 80)
    print("VERIFYING TRACT MATCHING FIX")
    print("=" * 80)
    
    acs_utils_path = REPO_ROOT / 'apps' / 'dataexplorer' / 'acs_utils.py'
    
    if not acs_utils_path.exists():
        print("✗ acs_utils.py not found!")
        return False
    
    with open(acs_utils_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the critical section
    found_loop = False
    found_check = False
    check_inside_loop = False
    
    for i, line in enumerate(lines, 1):
        if 'for tract_info in tracts:' in line:
            found_loop = True
            loop_line = i
        if found_loop and 'if households > 0:' in line:
            found_check = True
            check_line = i
            # Check indentation - should be more indented than the loop
            if line.startswith('                        '):  # 24 spaces = inside loop
                check_inside_loop = True
                break
    
    if found_loop and found_check and check_inside_loop:
        print(f"[OK] Fix verified: 'if households > 0:' is INSIDE the loop")
        print(f"  Loop starts at line {loop_line}")
        print(f"  Check is at line {check_line} (inside loop)")
        return True
    else:
        print("[FAIL] Fix NOT verified!")
        if not found_loop:
            print("  - Could not find 'for tract_info in tracts:' loop")
        if not found_check:
            print("  - Could not find 'if households > 0:' check")
        if not check_inside_loop:
            print("  - Check is NOT inside the loop (indentation issue)")
        return False

def verify_expand_button_fix():
    """Verify the expand button fix is in place."""
    print("\n" + "=" * 80)
    print("VERIFYING EXPAND BUTTON FIX")
    print("=" * 80)
    
    dashboard_js_path = REPO_ROOT / 'apps' / 'dataexplorer' / 'static' / 'js' / 'dashboard.js'
    
    if not dashboard_js_path.exists():
        print("✗ dashboard.js not found!")
        return False
    
    with open(dashboard_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('hasMoreThan10', 'hasMoreThan10 check found'),
        ('btn-expand-lenders-header', 'Button class found'),
        ('data-action="expand-lenders-header"', 'Button action attribute found'),
        ('setProperty.*important', 'setProperty with important found'),
    ]
    
    all_found = True
    for pattern, description in checks:
        if pattern in content:
            print(f"[OK] {description}")
        else:
            print(f"[FAIL] {description} - NOT FOUND")
            all_found = False
    
    return all_found

def check_census_api_key():
    """Check if CENSUS_API_KEY is available."""
    print("\n" + "=" * 80)
    print("CHECKING CENSUS_API_KEY")
    print("=" * 80)
    
    import os
    try:
        from dotenv import load_dotenv
        dream_analysis_env = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\.env")
        if dream_analysis_env.exists():
            load_dotenv(dream_analysis_env, override=False)
    except ImportError:
        pass
    
    api_key = os.getenv('CENSUS_API_KEY')
    if api_key:
        print(f"[OK] CENSUS_API_KEY is set (length: {len(api_key)})")
        print(f"  First 10 chars: {api_key[:10]}...")
        return True
    else:
        print("[FAIL] CENSUS_API_KEY is NOT set")
        print("  This will prevent tract data from loading!")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("VERIFYING FIXES")
    print("=" * 80 + "\n")
    
    results = []
    
    results.append(("Tract Matching Fix", verify_tract_fix()))
    results.append(("Expand Button Fix", verify_expand_button_fix()))
    results.append(("Census API Key", check_census_api_key()))
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n[OK] All checks passed! Fixes are in place.")
        print("\nNext steps:")
        print("1. Restart the Flask server if it's running")
        print("2. Clear browser cache (Ctrl+F5)")
        print("3. Test with a geography that has multiple counties")
    else:
        print("\n[FAIL] Some checks failed. Please review the issues above.")
    
    print("=" * 80 + "\n")

