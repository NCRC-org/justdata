#!/usr/bin/env python3
"""Copy NCRC logo to BizSight static directory."""

import shutil
from pathlib import Path

# Source and destination paths
repo_root = Path(__file__).parent.parent.parent
source_logo = repo_root / 'shared' / 'web' / 'static' / 'img' / 'ncrc-logo.png'
dest_dir = Path(__file__).parent / 'static' / 'img'
dest_logo = dest_dir / 'ncrc-logo.png'

print("=" * 80)
print("COPYING NCRC LOGO")
print("=" * 80)
print(f"\nSource: {source_logo}")
print(f"Destination: {dest_logo}")

# Check if source exists
if not source_logo.exists():
    print(f"\n✗ ERROR: Source logo not found at {source_logo}")
    print("  Please ensure the logo exists in shared/web/static/img/")
    exit(1)

# Create destination directory if it doesn't exist
dest_dir.mkdir(parents=True, exist_ok=True)
print(f"\n✓ Destination directory created/verified: {dest_dir}")

# Copy the logo
try:
    shutil.copy2(source_logo, dest_logo)
    print(f"✓ Logo copied successfully to {dest_logo}")
    
    # Verify it exists
    if dest_logo.exists():
        size = dest_logo.stat().st_size
        print(f"✓ Verification: Logo file exists ({size:,} bytes)")
    else:
        print("✗ ERROR: Logo file not found after copy")
        exit(1)
        
except Exception as e:
    print(f"✗ ERROR copying logo: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 80)
print("LOGO COPY COMPLETE")
print("=" * 80)
print()

