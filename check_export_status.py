#!/usr/bin/env python3
"""
Quick script to check if the export is still running and show status.
Run this in a separate terminal while the export is running.
"""

import psutil
import sys

def check_python_processes():
    """Check if Python processes are running that might be the export script."""
    python_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'export_lender_qualification_data' in cmdline:
                    python_processes.append({
                        'pid': proc.info['pid'],
                        'cpu': proc.info['cpu_percent'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                        'cmdline': cmdline
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return python_processes

if __name__ == '__main__':
    print("=" * 80)
    print("EXPORT STATUS CHECK")
    print("=" * 80)
    print()
    
    processes = check_python_processes()
    
    if processes:
        print(f"✓ Found {len(processes)} export process(es) running:\n")
        for proc in processes:
            print(f"  PID: {proc['pid']}")
            print(f"  CPU: {proc['cpu']:.1f}%")
            print(f"  Memory: {proc['memory_mb']:.1f} MB")
            print(f"  Command: {proc['cmdline'][:100]}...")
            print()
        
        # Check if process is active
        active = any(p['cpu'] > 0.1 for p in processes)
        if active:
            print("✓ Process is ACTIVE (using CPU) - export is still running")
        else:
            print("⚠ Process is IDLE (not using CPU) - may be waiting or stuck")
    else:
        print("✗ No export process found running")
        print("  The export may have completed or not started yet")
    
    print()
    print("=" * 80)
    print("TIP: If it's been running >30 minutes, you may want to:")
    print("  1. Cancel (Ctrl+C) and try with --max-rows to test")
    print("  2. Check your internet connection")
    print("  3. Try filtering to fewer years (e.g., --years '2023,2024')")
    print("=" * 80)

