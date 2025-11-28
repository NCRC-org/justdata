"""Launch API test using subprocess with shell=False to bypass PowerShell"""
import subprocess
import sys
from pathlib import Path

# Use C:\dream symbolic link to avoid apostrophe issues
dream_root = Path(r"C:\dream")
script_path = dream_root / "#JustData_Repo" / "execute_inline.py"

if not script_path.exists():
    print(f"ERROR: Script not found: {script_path}")
    sys.exit(1)

# Get Python executable
python_exe = sys.executable

# Build command as a LIST (not string) - critical for bypassing PowerShell
cmd = [python_exe, str(script_path)]

print("="*80)
print("Launching ProPublica API Test")
print("="*80)
print(f"Python: {python_exe}")
print(f"Script: {script_path}")
print("="*80)
print()

try:
    # Use subprocess with shell=False to bypass PowerShell wrapper entirely
    result = subprocess.run(
        cmd,
        shell=False,  # CRITICAL: shell=False bypasses PowerShell
        check=False,
        capture_output=False,  # Show output in real-time
        text=True,
        cwd=str(dream_root / "#JustData_Repo")
    )
    
    print()
    print("="*80)
    if result.returncode == 0:
        print("✓ Test completed successfully!")
    else:
        print(f"✗ Test exited with code: {result.returncode}")
    print("="*80)
    
    sys.exit(result.returncode)
    
except Exception as e:
    print(f"ERROR: Could not execute script: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

