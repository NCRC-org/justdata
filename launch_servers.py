#!/usr/bin/env python3
"""
Launch JustData API server and LendSight app.
Uses subprocess with shell=False to bypass PowerShell wrapper.
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    python_exe = sys.executable
    
    print("=" * 80)
    print("Starting JustData API server and LendSight app")
    print("Using subprocess with shell=False to bypass PowerShell wrapper")
    print("=" * 80)
    print()
    
    # Start JustData API server
    print("Starting JustData API server on port 8000...")
    cmd1 = [
        "cmd.exe",
        "/k",
        f'title JustData API (Port 8000) && cd /d "{project_root}" && {python_exe} run.py'
    ]
    try:
        subprocess.Popen(cmd1, shell=False, cwd=str(project_root))
        print("✓ JustData API server started")
    except Exception as e:
        print(f"✗ Failed to start JustData API: {e}")
    
    time.sleep(2)
    
    # Start LendSight app
    print("Starting LendSight app on port 8082...")
    cmd2 = [
        "cmd.exe",
        "/k",
        f'title LendSight (Port 8082) && cd /d "{project_root}" && {python_exe} run_lendsight.py'
    ]
    try:
        subprocess.Popen(cmd2, shell=False, cwd=str(project_root))
        print("✓ LendSight app started")
    except Exception as e:
        print(f"✗ Failed to start LendSight: {e}")
    
    print()
    print("=" * 80)
    print("Servers started in separate windows")
    print()
    print("Server URLs:")
    print("  JustData API:  http://localhost:8000")
    print("  API Docs:      http://localhost:8000/docs")
    print("  LendSight:     http://127.0.0.1:8082")
    print("=" * 80)

if __name__ == "__main__":
    main()

