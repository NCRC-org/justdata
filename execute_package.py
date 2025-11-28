import sys
import os
from pathlib import Path

# Set the working directory
os.chdir(Path(__file__).parent / 'apps' / 'bizsight')

# Now import and run
sys.path.insert(0, str(Path(__file__).parent / 'apps' / 'bizsight'))

from create_deployment_package import create_deployment_package

if __name__ == '__main__':
    create_deployment_package()


