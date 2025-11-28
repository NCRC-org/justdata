#!/usr/bin/env python3
"""Import and run LendSight packaging directly."""

import sys
from pathlib import Path

# Add apps/lendsight to path
sys.path.insert(0, str(Path(__file__).parent / 'apps' / 'lendsight'))

# Import and run
from package_lendsight import create_deployment_package

if __name__ == '__main__':
    try:
        create_deployment_package()
    except Exception as e:
        print(f"\n[ERROR] Error creating package: {e}")
        import traceback
        traceback.print_exc()
        exit(1)












