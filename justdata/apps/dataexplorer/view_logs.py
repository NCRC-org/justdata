#!/usr/bin/env python3
"""View server logs in real-time"""
import sys
from pathlib import Path

log_file = Path(__file__).parent / 'logs' / 'dataexplorer.log'

if not log_file.exists():
    print(f"Log file not found: {log_file}")
    print("The server may not have started yet or no logs have been written.")
    sys.exit(1)

print(f"Viewing logs from: {log_file}")
print("=" * 80)
print("Press Ctrl+C to stop viewing logs")
print("=" * 80)
print()

try:
    with open(log_file, 'r', encoding='utf-8') as f:
        # Go to end of file
        f.seek(0, 2)
        
        # Tail the file
        import time
        while True:
            line = f.readline()
            if line:
                print(line.rstrip())
            else:
                time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopped viewing logs.")
except Exception as e:
    print(f"Error reading log file: {e}")



