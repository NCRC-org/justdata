#!/usr/bin/env python3
"""Simple script to backup benchmark files to multiple locations."""

import json
import shutil
from pathlib import Path

# Source location (where files were generated)
source = Path(__file__).parent / "apps" / "data"

# Backup locations
backups = [
    Path(__file__).parent / "data",
    Path(__file__).parent / "data" / "benchmarks",
    Path(__file__).parent / "apps" / "bizsight" / "data",
]

print("=" * 80)
print("BACKING UP BENCHMARK FILES")
print("=" * 80)
print(f"\nSource: {source}")

# Verify source exists
if not source.exists():
    print(f"\nERROR: Source directory does not exist: {source}")
    exit(1)

# Check national file
national_file = source / "national.json"
if national_file.exists():
    with open(national_file, 'r') as f:
        data = json.load(f)
    print(f"\n✓ National benchmark found:")
    print(f"  Total loans: {data.get('total_loans', 0):,}")
    print(f"  Total amount: ${data.get('total_amount', 0):,.0f}")
else:
    print("\n✗ National benchmark NOT found")

# Count state files
state_files = list(source.glob("??.json"))
print(f"\n✓ Found {len(state_files)} state benchmark files")

# Copy files to backup locations
print("\nCopying files to backup locations...")
for backup_dir in backups:
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy national
    if national_file.exists():
        shutil.copy2(national_file, backup_dir / "national.json")
    
    # Copy state files
    copied = 0
    for state_file in state_files:
        if state_file.name != "national.json" and state_file.name != "benchmarks.json":
            shutil.copy2(state_file, backup_dir / state_file.name)
            copied += 1
    
    # Copy consolidated if it exists
    consolidated = source / "benchmarks.json"
    if consolidated.exists():
        shutil.copy2(consolidated, backup_dir / "benchmarks.json")
    
    print(f"  ✓ {backup_dir} ({copied} state files + national)")

print("\n" + "=" * 80)
print("BACKUP COMPLETE")
print("=" * 80)
print("\nBenchmark files are now available in:")
for backup_dir in backups:
    if (backup_dir / "national.json").exists():
        print(f"  ✓ {backup_dir}")

