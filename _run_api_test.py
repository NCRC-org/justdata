import subprocess
import sys
from pathlib import Path

dream = Path(r"C:\dream")
script = dream / "#JustData_Repo" / "execute_inline.py"

subprocess.run([sys.executable, str(script)], shell=False, cwd=str(dream / "#JustData_Repo"))

