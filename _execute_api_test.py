"""Execute API test using subprocess workaround"""
import subprocess
import sys
from pathlib import Path

# Use C:\dream symbolic link
dream_root = Path(r"C:\dream")
test_script = dream_root / "#JustData_Repo" / "execute_inline.py"

if not test_script.exists():
    print(f"ERROR: Test script not found: {test_script}")
    sys.exit(1)

python_exe = sys.executable
cmd = [python_exe, str(test_script)]

print("="*80)
print("Executing ProPublica API Test")
print("="*80)
print(f"Command: {' '.join(cmd)}")
print("="*80)
print()

# Use subprocess with shell=False to bypass PowerShell
result = subprocess.run(
    cmd,
    shell=False,  # CRITICAL: bypasses PowerShell wrapper
    check=False,
    capture_output=False,  # Show output in real-time
    text=True,
    cwd=str(dream_root / "#JustData_Repo")
)

print()
print("="*80)
print(f"Exit code: {result.returncode}")
print("="*80)

sys.exit(result.returncode)

