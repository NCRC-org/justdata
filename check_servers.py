#!/usr/bin/env python3
"""
Check which NCRC application servers are running.
"""

import socket
import subprocess
import sys

# Application ports and names
APPS = {
    8080: "BranchSeeker",
    8082: "LendSight",
    8083: "MergerMeter",
    8084: "BranchMapper"
}

print("=" * 60)
print("NCRC Application Server Status")
print("=" * 60)
print()

def check_port(port):
    """Check if a port is listening."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def get_process_info(port):
    """Get process information for a port."""
    try:
        # Use netstat to find process ID
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    return pid
    except Exception:
        pass
    return None

running_servers = []
not_running = []

for port, app_name in APPS.items():
    if check_port(port):
        pid = get_process_info(port)
        running_servers.append((port, app_name, pid))
        status = "RUNNING"
        pid_info = f" (PID: {pid})" if pid else ""
        print(f"✅ {app_name:20} Port {port:4} - {status}{pid_info}")
    else:
        not_running.append((port, app_name))
        print(f"❌ {app_name:20} Port {port:4} - NOT RUNNING")

print()
print("=" * 60)
print("Summary")
print("=" * 60)
print(f"Running servers: {len(running_servers)}/{len(APPS)}")
print()

if running_servers:
    print("Access URLs:")
    for port, app_name, _ in running_servers:
        print(f"  {app_name:20} http://127.0.0.1:{port}")
    print()

if not_running:
    print("To start servers:")
    for port, app_name in not_running:
        script_name = f"run_{app_name.lower().replace(' ', '')}.py"
        print(f"  python {script_name}  # Starts {app_name} on port {port}")
    print()

print("=" * 60)

