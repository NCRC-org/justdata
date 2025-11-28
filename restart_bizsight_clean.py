#!/usr/bin/env python3
"""Clear all caches and restart BizSight server."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

def clear_python_cache():
    """Clear Python bytecode cache."""
    print("=" * 80)
    print("CLEARING PYTHON CACHE")
    print("=" * 80)
    
    bizsight_dir = Path(__file__).parent / 'apps' / 'bizsight'
    cache_dirs = list(bizsight_dir.rglob('__pycache__'))
    pyc_files = list(bizsight_dir.rglob('*.pyc'))
    
    for cache_dir in cache_dirs:
        try:
            shutil.rmtree(cache_dir, ignore_errors=True)
            print(f"✓ Removed: {cache_dir}")
        except Exception as e:
            print(f"✗ Error removing {cache_dir}: {e}")
    
    for pyc_file in pyc_files:
        try:
            pyc_file.unlink(missing_ok=True)
            print(f"✓ Removed: {pyc_file}")
        except Exception as e:
            print(f"✗ Error removing {pyc_file}: {e}")
    
    print(f"\nCleared {len(cache_dirs)} cache directories and {len(pyc_files)} .pyc files")

def kill_server(port=8081):
    """Find and kill process running on the given port."""
    print(f"\n{'=' * 80}")
    print(f"STOPPING SERVER ON PORT {port}")
    print("=" * 80)
    
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, shell=True)
        pid = None
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    break
        
        if pid:
            print(f"Found process with PID {pid} on port {port}. Killing...")
            subprocess.run(['taskkill', '/F', '/PID', pid], shell=True, capture_output=True)
            time.sleep(2)
            print(f"✓ Server stopped on port {port}")
            return True
        else:
            print(f"No process found listening on port {port}")
            return False
    except Exception as e:
        print(f"Error stopping server: {e}")
        return False

def start_server():
    """Start the Flask server."""
    print(f"\n{'=' * 80}")
    print("STARTING BIZSIGHT SERVER")
    print("=" * 80)
    
    repo_root = Path(__file__).parent.absolute()
    
    # Ensure the repo root is in sys.path for module imports
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    
    # Set DEBUG environment variable for Flask
    os.environ['FLASK_DEBUG'] = '1'
    os.environ['DEBUG'] = 'True'
    os.environ['FLASK_ENV'] = 'development'
    
    print(f"Working directory: {repo_root}")
    print(f"Python executable: {sys.executable}")
    print(f"Starting server with DEBUG=True...")
    
    # Change to repo root
    original_cwd = os.getcwd()
    try:
        os.chdir(repo_root)
        cmd = [sys.executable, '-m', 'apps.bizsight.app']
        print(f"Command: {' '.join(cmd)}")
        print("\n" + "=" * 80)
        print("SERVER STARTING - Check terminal for output")
        print("=" * 80 + "\n")
        
        # Run in foreground so user can see output
        subprocess.run(cmd, check=False, cwd=repo_root)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\n✗ Error starting server: {e}")
        import traceback
        traceback.print_exc()
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    repo_root = Path(__file__).parent.absolute()
    os.chdir(repo_root)
    print(f"Current working directory: {os.getcwd()}\n")
    
    clear_python_cache()
    kill_server()
    time.sleep(1)
    start_server()

