#!/usr/bin/env python3
"""
Quick Manual Fix for Known Wrong FEC IDs

This script fixes the 4 officials identified as having wrong FEC IDs:
1. Bill Foster - H2IL11124 -> H8IL14067 (has $1.37M in contributions)
2. Ed Markey - S4MA00028 -> H8MA07075 (needs verification)
3. Marlin Stutzman - H0IN03085 -> H2IN03076 (needs verification)
4. Gil Cisneros - S0CA00461 -> H8CA39103 (needs verification)

Usage:
    python fix_fec_ids.py          # Preview changes
    python fix_fec_ids.py --apply  # Apply changes to officials.json
"""

import json
import sys
from pathlib import Path

# Known wrong FEC ID mappings (old -> correct)
# Based on analysis of which IDs actually have contribution data
KNOWN_FIXES = {
    # Format: bioguide_id: (old_fec_id, correct_fec_id, name)
    'F000454': ('H2IL11124', 'H8IL14067', 'Bill Foster'),
    # These need verification - commenting out until confirmed
    # 'M000133': ('S4MA00028', 'H8MA07075', 'Ed Markey'),
    # 'S001196': ('H0IN03085', 'H2IN03076', 'Marlin Stutzman'),
    # 'C001123': ('S0CA00461', 'H8CA39103', 'Gil Cisneros'),
}

def main():
    apply_changes = '--apply' in sys.argv

    base_dir = Path(__file__).parent.parent
    officials_path = base_dir / 'data' / 'current' / 'officials.json'

    print("=" * 70)
    print("FEC ID Manual Fix Script")
    print("=" * 70)

    if not officials_path.exists():
        print(f"ERROR: Officials file not found: {officials_path}")
        return 1

    # Load officials
    with open(officials_path) as f:
        data = json.load(f)

    officials = data.get('officials', data.get('data', []))
    print(f"Loaded {len(officials)} officials\n")

    # Find and fix
    changes = []
    for official in officials:
        bioguide_id = official.get('bioguide_id')
        if bioguide_id in KNOWN_FIXES:
            old_id, new_id, name = KNOWN_FIXES[bioguide_id]
            current_id = official.get('fec_candidate_id')

            if current_id == old_id:
                changes.append({
                    'name': official.get('name'),
                    'bioguide_id': bioguide_id,
                    'old_fec_id': current_id,
                    'new_fec_id': new_id,
                })
                if apply_changes:
                    official['fec_candidate_id'] = new_id
            elif current_id == new_id:
                print(f"ALREADY FIXED: {official.get('name')} already has correct ID {new_id}")
            else:
                print(f"UNEXPECTED: {official.get('name')} has {current_id}, expected {old_id}")

    # Report
    if changes:
        print(f"\nFound {len(changes)} officials to fix:\n")
        for change in changes:
            print(f"  {change['name']}")
            print(f"    Bioguide: {change['bioguide_id']}")
            print(f"    Old FEC ID: {change['old_fec_id']}")
            print(f"    New FEC ID: {change['new_fec_id']}")
            print()

        if apply_changes:
            # Save changes
            from datetime import datetime
            data['last_updated'] = datetime.now().isoformat()
            with open(officials_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"APPLIED: Updated {len(changes)} officials in {officials_path}")
            print("\nNote: You still need to re-run the pipeline to fetch contribution data:")
            print("  python run_pipeline.py")
        else:
            print("DRY RUN: No changes applied. Run with --apply to save changes.")
    else:
        print("No officials found that need fixing.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
