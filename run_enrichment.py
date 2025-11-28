"""Launcher for ProPublica enrichment - uses subprocess with shell=False"""
import subprocess
import sys
from pathlib import Path

# Use C:\dream symbolic link to avoid apostrophe issues
dream_root = Path(r"C:\dream")
script_path = dream_root / "#JustData_Repo" / "enrich_with_propublica.py"

if not script_path.exists():
    print(f"ERROR: Script not found: {script_path}")
    sys.exit(1)

python_exe = sys.executable
cmd = [str(python_exe), str(script_path)]

print("="*80)
print("Launching ProPublica Enrichment")
print("="*80)
print(f"Python: {python_exe}")
print(f"Script: {script_path}")
print("="*80)
print()

# Use subprocess with shell=False to bypass PowerShell wrapper
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
if result.returncode == 0:
    print("✓ Enrichment completed successfully!")
else:
    print(f"✗ Enrichment exited with code: {result.returncode}")
print("="*80)

sys.exit(result.returncode)
















