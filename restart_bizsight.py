#!/usr/bin/env python3
"""Restart BizSight server and copy logo if needed."""

import shutil
import subprocess
import sys
import time
import os
from pathlib import Path

def copy_logo():
    """Copy logo from user's location to static directory."""
    source = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Headshots and Other Frequently Used Items\NCRC color FINAL.jpg")
    dest_dir = Path(__file__).parent / 'apps' / 'bizsight' / 'static' / 'img'
    
    if not source.exists():
        print(f"Warning: Logo source not found: {source}")
        return False
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(source, dest_dir / 'ncrc-logo.jpg')
        shutil.copy2(source, dest_dir / 'ncrc-logo.png')
        print(f"✓ Logo copied to {dest_dir}")
        return True
    except Exception as e:
        print(f"Error copying logo: {e}")
        return False

def kill_server_on_port(port=8081):
    """Kill any process using the specified port."""
    try:
        # Use netstat to find process
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
            print(f"Stopping process {pid} on port {port}...")
            subprocess.run(['taskkill', '/F', '/PID', pid], shell=True, capture_output=True)
            time.sleep(1)
            return True
        return False
    except Exception as e:
        print(f"Could not check port: {e}")
        return False

def start_server():
    """Start the BizSight server."""
    repo_root = Path(__file__).parent.absolute()
    os.chdir(repo_root)
    
    cmd = [sys.executable, '-m', 'apps.bizsight.app']
    print(f"\nStarting server: {' '.join(cmd)}")
    print(f"Working directory: {repo_root}")
    print("Server will be available at: http://localhost:8081")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run(cmd, cwd=repo_root)
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == '__main__':
    print("=" * 60)
    print("BizSight Server Restart")
    print("=" * 60)
    
    # Copy logo
    print("\n[1/3] Copying logo...")
    copy_logo()
    
    # Kill existing server
    print("\n[2/3] Checking for existing server...")
    kill_server_on_port()
    
    # Start server
    print("\n[3/3] Starting server...")
    start_server()

