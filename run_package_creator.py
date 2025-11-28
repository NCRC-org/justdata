#!/usr/bin/env python3
"""Run the deployment package creator"""
import sys
from pathlib import Path

# Add the bizsight directory to path
bizsight_dir = Path(__file__).parent / 'apps' / 'bizsight'
sys.path.insert(0, str(bizsight_dir))

# Import and run
exec(open(bizsight_dir / 'create_deployment_package.py').read())


