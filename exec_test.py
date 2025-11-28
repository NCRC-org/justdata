import subprocess
import sys
from pathlib import Path

dream = Path(r"C:\dream")
script_path = dream / "#JustData_Repo" / "execute_inline.py"

# Read and execute the script content directly
with open(script_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Execute it
exec(code)

