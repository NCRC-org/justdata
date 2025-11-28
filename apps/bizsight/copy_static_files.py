#!/usr/bin/env python3
"""Copy static files from shared directory to BizSight."""
import shutil
from pathlib import Path

# Get directories
bizsight_dir = Path(__file__).parent.absolute()
repo_root = bizsight_dir.parent.parent.absolute()
shared_static = repo_root / 'shared' / 'web' / 'static'
bizsight_static = bizsight_dir / 'static'

print(f"Copying static files from: {shared_static}")
print(f"To: {bizsight_static}")
print()

if not shared_static.exists():
    print(f"ERROR: Source directory not found: {shared_static}")
    exit(1)

# Ensure destination exists
bizsight_static.mkdir(parents=True, exist_ok=True)

# Copy files
copied = False
for item in ['css', 'js', 'img']:
    src = shared_static / item
    dst = bizsight_static / item
    if src.exists():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        file_count = len(list(src.rglob('*'))) - len(list(src.rglob('*.*')))  # Rough count
        print(f"  ✓ Copied {item}/ ({len(list(src.rglob('*.*')))} files)")
        copied = True
    else:
        print(f"  ⚠ {item}/ not found in source")

if copied:
    print("\n✓ Static files copied successfully!")
    print(f"   Static files are now in: {bizsight_static}")
else:
    print("\n⚠ No static files were copied. Check source directory.")

