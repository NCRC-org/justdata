#!/usr/bin/env python3
"""
Examine credit union call report zip files to understand structure.
"""

import zipfile
import os
from pathlib import Path

desktop_path = Path(r"C:\Users\jrichardson\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop")

# Find all call report zip files
zip_files = sorted(desktop_path.glob("call-report-data-*.zip"))

print("=" * 80)
print("CREDIT UNION CALL REPORT FILES - DETAILED EXAMINATION")
print("=" * 80)

# Focus on the most recent year first
latest_zip = zip_files[-1] if zip_files else None

if latest_zip:
    print(f"\nExamining: {latest_zip.name}")
    try:
        with zipfile.ZipFile(latest_zip, 'r') as z:
            # Key files to examine
            key_files = [
                "Credit Union Branch Information.txt",
                "FOICU.txt",
                "FOICUDES.txt"
            ]
            
            for key_file in key_files:
                if key_file in z.namelist():
                    print(f"\n{'='*80}")
                    print(f"File: {key_file}")
                    print(f"{'='*80}")
                    with z.open(key_file) as f:
                        # Read first 20 lines
                        lines = f.read().decode('utf-8', errors='ignore').split('\n')[:20]
                        print(f"First 20 lines:")
                        for i, line in enumerate(lines, 1):
                            # Show first 150 chars of each line
                            display_line = line[:150].replace('\r', '')
                            print(f"  {i:2}: {display_line}")
                        
                        # Try to detect delimiter
                        if lines:
                            first_line = lines[0]
                            if '\t' in first_line:
                                delimiter = '\t'
                                print(f"\nDelimiter: TAB")
                            elif '|' in first_line:
                                delimiter = '|'
                                print(f"\nDelimiter: PIPE")
                            elif ',' in first_line:
                                delimiter = ','
                                print(f"\nDelimiter: COMMA")
                            else:
                                delimiter = None
                                print(f"\nDelimiter: Unknown (possibly fixed-width)")
                            
                            if delimiter:
                                fields = first_line.split(delimiter)
                                print(f"Number of fields in header: {len(fields)}")
                                print(f"Sample field names (first 10): {fields[:10]}")
                else:
                    print(f"\nFile not found: {key_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
