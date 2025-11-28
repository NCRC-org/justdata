#!/usr/bin/env python3
"""
Aggressively clear all Flask and Python caches.
This script should be run before restarting the server to ensure all changes are loaded.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

def clear_python_cache():
    """Remove all __pycache__ directories and .pyc files."""
    repo_root = Path(__file__).parent.parent.parent.absolute()
    bizsight_dir = Path(__file__).parent
    
    print("=" * 80)
    print("CLEARING PYTHON BYTECODE CACHE")
    print("=" * 80)
    
    removed_count = 0
    for pycache_dir in bizsight_dir.rglob('__pycache__'):
        if pycache_dir.is_dir():
            print(f"  Removing: {pycache_dir}")
            try:
                shutil.rmtree(pycache_dir, ignore_errors=True)
                removed_count += 1
            except Exception as e:
                print(f"    Warning: {e}")
    
    for pyc_file in bizsight_dir.rglob('*.pyc'):
        print(f"  Removing: {pyc_file}")
        try:
            pyc_file.unlink(missing_ok=True)
            removed_count += 1
        except Exception as e:
            print(f"    Warning: {e}")
    
    print(f"\n✓ Removed {removed_count} cache items")
    return removed_count

def clear_jinja2_cache():
    """Clear Jinja2 template cache files if they exist."""
    bizsight_dir = Path(__file__).parent
    templates_dir = bizsight_dir / 'templates'
    
    print("\n" + "=" * 80)
    print("CLEARING JINJA2 TEMPLATE CACHE")
    print("=" * 80)
    
    # Jinja2 may cache compiled templates in __pycache__ under templates
    removed_count = 0
    for pycache_dir in templates_dir.rglob('__pycache__'):
        if pycache_dir.is_dir():
            print(f"  Removing: {pycache_dir}")
            try:
                shutil.rmtree(pycache_dir, ignore_errors=True)
                removed_count += 1
            except Exception as e:
                print(f"    Warning: {e}")
    
    for pyc_file in templates_dir.rglob('*.pyc'):
        print(f"  Removing: {pyc_file}")
        try:
            pyc_file.unlink(missing_ok=True)
            removed_count += 1
        except Exception as e:
            print(f"    Warning: {e}")
    
    print(f"\n✓ Removed {removed_count} template cache items")
    return removed_count

def kill_server(port=8081):
    """Find and kill process running on the given port."""
    print("\n" + "=" * 80)
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
            time.sleep(2)  # Give it time to terminate
            print(f"✓ Server stopped on port {port}")
            return True
        else:
            print(f"No process found listening on port {port}")
            return False
    except Exception as e:
        print(f"Error stopping server: {e}")
        return False

def print_instructions():
    """Print instructions for restarting the server."""
    print("\n" + "=" * 80)
    print("CACHE CLEARED - READY TO RESTART")
    print("=" * 80)
    print("\nTo restart the server with fresh code:")
    print("  1. Set DEBUG=True: set DEBUG=True")
    print("  2. Start server: python -m apps.bizsight.app")
    print("\nOr use the restart script:")
    print("  python restart_bizsight_clean.py")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent.parent.absolute()
    os.chdir(repo_root)
    
    clear_python_cache()
    clear_jinja2_cache()
    kill_server()
    print_instructions()

