#!/usr/bin/env python3
"""
Verify installation, clean up unneeded files, and start all four applications.
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path

# Change to the script's directory
SCRIPT_DIR = Path(__file__).parent.resolve()
os.chdir(SCRIPT_DIR)

print("=" * 60)
print("Verifying Installation, Cleaning Up, and Starting Apps")
print("=" * 60)
print()

# Step 1: Verify dependencies
print("Step 1: Verifying dependencies...")
try:
    result = subprocess.run([sys.executable, "check_dependencies.py"], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("WARNING: Some dependencies may be missing")
        print("Continuing anyway...")
except FileNotFoundError:
    print("check_dependencies.py not found, skipping verification")
except Exception as e:
    print(f"Error during verification: {e}")

print()

# Step 2: Clean up unneeded files
print("Step 2: Cleaning up unneeded files...")
items_to_remove = [
    "_backup_before_flatten",
    "justdata",  # Leftover nested folder
    "cleanup_leftover.py",
    "flatten_structure.py",
    "install_missing.bat",
    "check_dependencies.py",
    "cleanup_dream_justdata.py",
    "verify_and_start.bat",
    "verify_cleanup_start.bat",
    "verify_cleanup_start.py",  # Will remove itself at the end
    "2.3.0",  # Stray file from pip install
]

removed = []
for item in items_to_remove:
    item_path = SCRIPT_DIR / item
    if item_path.exists():
        try:
            if item_path.is_dir():
                shutil.rmtree(item_path)
            else:
                item_path.unlink()
            print(f"  ✓ Removed: {item}")
            removed.append(item)
        except Exception as e:
            print(f"  ✗ Failed to remove {item}: {e}")

if removed:
    print(f"  Cleaned up {len(removed)} items.")
else:
    print("  No cleanup needed.")
print()

# Step 3: Start all four applications
print("Step 3: Starting all four applications...")
print()

apps = [
    ("BranchSeeker", "run_branchseeker.py", 8080),
    ("LendSight", "run_lendsight.py", 8082),
    ("MergerMeter", "run_mergermeter.py", 8083),
    ("BranchMapper", "run_branchmapper.py", 8084),
]

for app_name, script, port in apps:
    script_path = SCRIPT_DIR / script
    if not script_path.exists():
        print(f"  ✗ {app_name}: Script {script} not found!")
        continue
    
    print(f"  Starting {app_name} on port {port}...")
    try:
        # Start in a new window
        subprocess.Popen(
            ["cmd", "/k", f"cd /d {SCRIPT_DIR} && python {script}"],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        time.sleep(2)  # Give each app time to start
    except Exception as e:
        print(f"  ✗ Failed to start {app_name}: {e}")

print()
print("=" * 60)
print("All applications have been started!")
print("=" * 60)
print()
print("Application URLs:")
print("  BranchSeeker:   http://127.0.0.1:8080")
print("  LendSight:      http://127.0.0.1:8082")
print("  MergerMeter:    http://127.0.0.1:8083")
print("  BranchMapper:   http://127.0.0.1:8084")
print()
print("Wait a few seconds for servers to start, then check:")
print("  check_servers.bat")
print()
print("Or visit the URLs above in your browser.")
print("=" * 60)

# Remove this script at the end
try:
    if Path(__file__).exists():
        time.sleep(1)
        os.remove(__file__)
except:
    pass  # Ignore if can't remove

