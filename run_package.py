import subprocess
import sys
from pathlib import Path

script_path = Path(__file__).parent / 'do_package_lendsight.py'
subprocess.run([sys.executable, str(script_path)], shell=False)












