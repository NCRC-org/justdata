#!/usr/bin/env python3
"""Simple wrapper to create BizSight deployment package"""
import sys
from pathlib import Path

# Add bizsight to path
bizsight_dir = Path(__file__).parent / 'apps' / 'bizsight'
sys.path.insert(0, str(bizsight_dir))

from create_deployment_package import create_deployment_package

if __name__ == '__main__':
    create_deployment_package()


