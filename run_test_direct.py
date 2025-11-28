import subprocess
import sys
from pathlib import Path

dream_root = Path(r"C:\dream")
test_script = dream_root / "#JustData_Repo" / "execute_inline.py"

if not test_script.exists():
    print(f"ERROR: Script not found: {test_script}")
    sys.exit(1)

python_exe = sys.executable
cmd = [str(python_exe), str(test_script)]

print("="*80)
print("Executing ProPublica API Test")
print("="*80)
print(f"Python: {python_exe}")
print(f"Script: {test_script}")
print("="*80)

result = subprocess.run(
    cmd,
    shell=False,
    check=False,
    capture_output=False,
    text=True,
    cwd=str(dream_root / "#JustData_Repo")
)

sys.exit(result.returncode)

