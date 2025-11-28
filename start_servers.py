#!/usr/bin/env python3
"""
Start JustData API server and LendSight app using subprocess with shell=False
to bypass PowerShell wrapper issues with apostrophes in paths.

This workaround avoids the PowerShell parsing errors when paths contain apostrophes
like "Nat'l Community Reinvestment Coaltn".
"""

import subprocess
import sys
import time
from pathlib import Path

def start_server(script_name, window_title, port):
    """
    Start a server in a new window using subprocess with shell=False.
    
    Args:
        script_name: Name of the Python script to run (e.g., "run.py")
        window_title: Title for the command window
        port: Port number the server will run on
    """
    project_root = Path(__file__).parent
    script_path = project_root / script_name
    
    if not script_path.exists():
        print(f"ERROR: Script not found: {script_path}")
        return False
    
    # Get Python executable
    python_exe = sys.executable
    
    # Build command as a list (not string) to avoid shell interpretation
    # This is the key workaround: shell=False bypasses PowerShell wrapper
    cmd = [
        "cmd.exe",
        "/k",
        f'title {window_title} && cd /d "{project_root}" && {python_exe} {script_name}'
    ]
    
    print(f"Starting {window_title} on port {port}...")
    
    try:
        # Use subprocess with shell=False to bypass PowerShell entirely
        # This prevents apostrophe parsing issues in paths
        subprocess.Popen(
            cmd,
            shell=False,  # Critical: shell=False bypasses PowerShell wrapper
            cwd=str(project_root)
        )
        return True
    except Exception as e:
        print(f"ERROR: Could not start {script_name}: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("Starting JustData API server and LendSight app")
    print("Using subprocess with shell=False to bypass PowerShell wrapper")
    print("=" * 80)
    print()
    
    # Start JustData API server
    success1 = start_server("run.py", "JustData API (Port 8000)", 8000)
    time.sleep(2)  # Wait a moment between starts
    
    # Start LendSight app
    success2 = start_server("run_lendsight.py", "LendSight (Port 8082)", 8082)
    
    print()
    print("=" * 80)
    if success1 and success2:
        print("✓ Both servers have been started in separate windows")
        print()
        print("Server URLs:")
        print("  JustData API:  http://localhost:8000")
        print("  API Docs:      http://localhost:8000/docs")
        print("  LendSight:     http://127.0.0.1:8082")
        print()
        print("The servers will continue running in their own windows.")
        print("You can close this window.")
    else:
        print("✗ Some servers failed to start. Check the error messages above.")
    print("=" * 80)

