#!/usr/bin/env python3
"""Force reload by clearing all caches and restarting server."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

def clear_all_caches():
    """Clear all Python and Flask caches."""
    repo_root = Path(__file__).parent.parent.parent.absolute()
    bizsight_dir = Path(__file__).parent
    
    print("=" * 80)
    print("CLEARING ALL CACHES")
    print("=" * 80)
    
    # Clear __pycache__
    count = 0
    for pycache in bizsight_dir.rglob('__pycache__'):
        if pycache.is_dir():
            print(f"  Removing: {pycache}")
            try:
                shutil.rmtree(pycache)
                count += 1
            except Exception as e:
                print(f"    Warning: {e}")
    
    # Clear .pyc files
    for pyc in bizsight_dir.rglob('*.pyc'):
        print(f"  Removing: {pyc}")
        try:
            pyc.unlink()
            count += 1
        except Exception as e:
            print(f"    Warning: {e}")
    
    print(f"\n✓ Cleared {count} cache items")
    return count

def kill_server(port=8081):
    """Kill server on port."""
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            shell=True
        )
        
        pid = None
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    break
        
        if pid:
            print(f"\nStopping server (PID {pid})...")
            subprocess.run(['taskkill', '/F', '/PID', pid], shell=True, capture_output=True)
            time.sleep(2)
            return True
        return False
    except Exception as e:
        print(f"Could not kill server: {e}")
        return False

def main():
    """Main function."""
    print("\n" + "=" * 80)
    print("FORCE RELOAD - CLEARING CACHES AND RESTARTING SERVER")
    print("=" * 80)
    
    # Clear caches
    clear_all_caches()
    
    # Kill server
    kill_server()
    
    # Set DEBUG mode
    os.environ['DEBUG'] = 'True'
    print("\n✓ DEBUG mode enabled")
    
    # Start server
    repo_root = Path(__file__).parent.parent.parent.absolute()
    os.chdir(repo_root)
    
    print("\n" + "=" * 80)
    print("STARTING SERVER WITH FORCED RELOAD")
    print("=" * 80)
    print(f"Working directory: {repo_root}")
    print("DEBUG=True (templates will auto-reload)")
    print("Server: http://localhost:8081")
    print("\nPress Ctrl+C to stop\n")
    
    cmd = [sys.executable, '-m', 'apps.bizsight.app']
    subprocess.run(cmd, cwd=repo_root, env=os.environ.copy())

if __name__ == '__main__':
    main()

