#!/usr/bin/env python3
"""Copy NCRC logo to DataExplorer static directory."""

import shutil
from pathlib import Path

# Source and destination paths
source = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Headshots and Other Frequently Used Items\NCRC color FINAL.jpg")
dest_dir = Path('apps/dataexplorer/static/img')
dest_logo = dest_dir / 'ncrc-logo.png'

print("Copying NCRC logo to DataExplorer...")
print(f"Source: {source}")
print(f"Destination: {dest_logo}")

# Create directory if it doesn't exist
dest_dir.mkdir(parents=True, exist_ok=True)

# Copy the logo
if source.exists():
    shutil.copy2(source, dest_logo)
    print(f"✓ Logo copied successfully to {dest_logo}")
else:
    print(f"✗ ERROR: Source logo not found at {source}")
    print("Creating placeholder...")
    # Create a simple placeholder
    dest_logo.write_text("NCRC Logo Placeholder")

print("Done!")

