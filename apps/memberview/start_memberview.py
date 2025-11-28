#!/usr/bin/env python3
"""
Start MemberView using C:\\DREAM path with subprocess shell=False.
Uses C:\\DREAM symbolic link to avoid apostrophe issues in paths.
"""
import subprocess
import sys
from pathlib import Path

def start_memberview():
    # Try C:\DREAM path first (symbolic link)
    dream_path = Path(r"C:\DREAM\Cursor Agent Backups\MemberView_Standalone")
    script_path = dream_path / "run_memberview.py"
    
    # If C:\DREAM path doesn't work, fall back to actual path
    if not script_path.exists():
        # Use the actual path (current file's location)
        dream_path = Path(__file__).parent
        script_path = dream_path / "run_memberview.py"
        print("C:\\DREAM path not found, using actual path instead")
    
    python_exe = sys.executable

    print(f"Script: {script_path}")
    print(f"Python: {python_exe}")
    print()

    if not script_path.exists():
        print(f"ERROR: Script not found at {script_path}")
        print(f"Please verify the file exists")
        return False

    # Build command as list - this bypasses PowerShell
    cmd = [str(python_exe), str(script_path)]

    print(f"Executing: {' '.join(cmd)}")
    print("Starting MemberView on port 8082...")
    print()

    try:
        # Use subprocess with shell=False to bypass PowerShell entirely
        # Use the directory containing the script as working directory
        process = subprocess.Popen(
            cmd,
            shell=False,  # Critical: bypasses PowerShell wrapper
            cwd=str(script_path.parent),
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        print(f"✓ MemberView process started (PID: {process.pid})")
        print("Server should be available at: http://127.0.0.1:8082")
        print()
        print("Process is running. Press Ctrl+C to stop.")
        
        # Wait for the process
        process.wait()
        return True
    except KeyboardInterrupt:
        print("\nStopping MemberView...")
        process.terminate()
        process.wait()
        print("Stopped.")
        return True
    except Exception as e:
        print(f"ERROR: Could not start MemberView: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_memberview()

