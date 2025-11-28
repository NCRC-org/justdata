#!/usr/bin/env python3
"""Copy logo and restart BizSight server automatically."""

import shutil
import subprocess
import sys
import time
import os
from pathlib import Path

# Source path (user provided)
source_logo = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Headshots and Other Frequently Used Items\NCRC color FINAL.jpg")

# Destination paths
dest_dir = Path(__file__).parent / 'static' / 'img'
dest_logo_jpg = dest_dir / 'ncrc-logo.jpg'
dest_logo_png = dest_dir / 'ncrc-logo.png'

print("=" * 80)
print("BIZSIGHT SETUP AND SERVER RESTART")
print("=" * 80)

# Step 1: Copy logo
print("\n[1/3] Copying logo file...")
if source_logo.exists():
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(source_logo, dest_logo_jpg)
        shutil.copy2(source_logo, dest_logo_png)
        print(f"✓ Logo copied to {dest_logo_jpg}")
        print(f"✓ Logo copied to {dest_logo_png}")
    except Exception as e:
        print(f"✗ Error copying logo: {e}")
        sys.exit(1)
else:
    print(f"⚠ Warning: Source logo not found at {source_logo}")
    print("  Continuing anyway...")

# Step 2: Kill existing server
print("\n[2/3] Checking for existing server on port 8081...")
try:
    # Windows: find process using port 8081
    result = subprocess.run(
        ['netstat', '-ano'],
        capture_output=True,
        text=True,
        shell=True
    )
    
    # Find PID using port 8081
    pid = None
    for line in result.stdout.split('\n'):
        if ':8081' in line and 'LISTENING' in line:
            parts = line.split()
            if len(parts) > 4:
                pid = parts[-1]
                break
    
    if pid:
        print(f"  Found process {pid} using port 8081, killing...")
        subprocess.run(['taskkill', '/F', '/PID', pid], shell=True, capture_output=True)
        time.sleep(2)  # Give it time to release the port
        print("✓ Server stopped")
    else:
        print("  No server found on port 8081")
except Exception as e:
    print(f"  Could not check/kill server: {e}")
    print("  Continuing anyway...")

# Step 3: Start server
print("\n[3/3] Starting BizSight server...")
repo_root = Path(__file__).parent.parent.parent.absolute()
os.chdir(repo_root)

# Start server in background
server_cmd = [sys.executable, '-m', 'apps.bizsight.app']
print(f"  Command: {' '.join(server_cmd)}")
print(f"  Working directory: {repo_root}")
print("\n" + "=" * 80)
print("SERVER STARTING...")
print("=" * 80)
print("\nServer will be available at: http://localhost:8081")
print("Press Ctrl+C to stop the server\n")

# Run server (this will block, which is what we want)
try:
    subprocess.run(server_cmd, cwd=repo_root)
except KeyboardInterrupt:
    print("\n\nServer stopped by user")

