"""Clear caches and restart server - simple version."""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Clear Python cache
bizsight = Path(__file__).parent / 'apps' / 'bizsight'
for pycache in bizsight.rglob('__pycache__'):
    if pycache.is_dir():
        shutil.rmtree(pycache, ignore_errors=True)
for pyc in bizsight.rglob('*.pyc'):
    pyc.unlink(missing_ok=True)

# Kill server on port 8081
try:
    result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, shell=True)
    for line in result.stdout.split('\n'):
        if ':8081' in line and 'LISTENING' in line:
            parts = line.split()
            if len(parts) > 4:
                subprocess.run(['taskkill', '/F', '/PID', parts[-1]], shell=True, capture_output=True)
                time.sleep(1)
                break
except:
    pass

# Start server with DEBUG=True
os.environ['DEBUG'] = 'True'
repo_root = Path(__file__).parent.absolute()
os.chdir(repo_root)
print("Starting server with DEBUG=True and cache cleared...")
subprocess.run([sys.executable, '-m', 'apps.bizsight.app'], cwd=repo_root)

