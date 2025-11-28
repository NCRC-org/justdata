#!/usr/bin/env python3
"""Copy NCRC logo from user's OneDrive to BizSight static directory."""

import shutil
from pathlib import Path

# Source path (user provided)
source_logo = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Headshots and Other Frequently Used Items\NCRC color FINAL.jpg")

# Destination paths
dest_dir = Path(__file__).parent / 'static' / 'img'
dest_logo_jpg = dest_dir / 'ncrc-logo.jpg'
dest_logo_png = dest_dir / 'ncrc-logo.png'  # Also copy as PNG for compatibility

print("=" * 80)
print("COPYING NCRC LOGO FROM USER LOCATION")
print("=" * 80)
print(f"\nSource: {source_logo}")
print(f"Destination JPG: {dest_logo_jpg}")
print(f"Destination PNG: {dest_logo_png}")

# Check if source exists
if not source_logo.exists():
    print(f"\n✗ ERROR: Source logo not found at {source_logo}")
    exit(1)

# Create destination directory if it doesn't exist
dest_dir.mkdir(parents=True, exist_ok=True)
print(f"\n✓ Destination directory created/verified: {dest_dir}")

# Copy the logo as JPG
try:
    shutil.copy2(source_logo, dest_logo_jpg)
    print(f"✓ Logo copied successfully as JPG to {dest_logo_jpg}")
    
    # Also copy as PNG (same file, different extension) for templates that reference .png
    shutil.copy2(source_logo, dest_logo_png)
    print(f"✓ Logo also copied as PNG to {dest_logo_png}")
    
    # Verify files exist
    if dest_logo_jpg.exists():
        size_jpg = dest_logo_jpg.stat().st_size
        print(f"✓ Verification: JPG file exists ({size_jpg:,} bytes)")
    else:
        print("✗ ERROR: JPG file not found after copy")
        
    if dest_logo_png.exists():
        size_png = dest_logo_png.stat().st_size
        print(f"✓ Verification: PNG file exists ({size_png:,} bytes)")
    else:
        print("✗ ERROR: PNG file not found after copy")
        
except Exception as e:
    print(f"✗ ERROR copying logo: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 80)
print("LOGO COPY COMPLETE")
print("=" * 80)
print(f"\nLogo files are now available at:")
print(f"  - {dest_logo_jpg}")
print(f"  - {dest_logo_png}")
print()

