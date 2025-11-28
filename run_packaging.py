#!/usr/bin/env python3
"""Execute the deployment package creator directly"""
import sys
import os
from pathlib import Path

# Change to the bizsight directory
bizsight_path = Path(__file__).parent / 'apps' / 'bizsight'
os.chdir(bizsight_path)
sys.path.insert(0, str(bizsight_path))

# Import the function
import importlib.util
spec = importlib.util.spec_from_file_location("create_deployment_package", bizsight_path / "create_deployment_package.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Run it
module.create_deployment_package()


