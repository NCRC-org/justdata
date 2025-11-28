#!/usr/bin/env python3
"""Standalone script to package DataExplorer - avoids PowerShell path issues."""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

# Get paths - use absolute paths to avoid issues
script_dir = Path(__file__).parent.absolute()
repo_root = script_dir
package_dir = repo_root / 'dataexplorer_deployment'
package_zip = repo_root / f'dataexplorer_deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
dataexplorer_src = repo_root / 'apps' / 'dataexplorer'

print("[*] Creating DataExplorer Deployment Package")
print(f"   Source: {dataexplorer_src}")
print(f"   Package: {package_dir}")
print(f"   Zip: {package_zip}")
print()

# Clean up old package directory
if package_dir.exists():
    print("[*] Removing old package directory...")
    try:
        shutil.rmtree(package_dir)
    except PermissionError:
        print("   [WARN] Could not remove old package directory (files may be in use)")
        print("   [INFO] Continuing anyway - files will be overwritten...")
    except Exception as e:
        print(f"   [WARN] Error removing old directory: {e}")
        print("   [INFO] Continuing anyway - files will be overwritten...")

# Create package structure
print("[*] Creating package structure...")
package_dir.mkdir(exist_ok=True)

# Copy DataExplorer application files
dataexplorer_dest = package_dir / 'apps' / 'dataexplorer'
dataexplorer_dest.mkdir(parents=True, exist_ok=True)

files_to_copy = [
    '__init__.py',
    'app.py',
    'config.py',
    'data_utils.py',
    'query_builders.py',
    'area_analysis_processor.py',
    'demographic_queries.py',
    'acs_utils.py',
    'mmct_utils.py',
    'excel_export.py',
    'lender_analysis_processor.py',
    'lender_excel_generator.py',
    'hud_data_processor.py',
    'powerpoint_export.py',
]

print("[*] Copying application files...")
for file in files_to_copy:
    src = dataexplorer_src / file
    if src.exists():
        shutil.copy2(src, dataexplorer_dest / file)
        print(f"   [OK] {file}")
    else:
        print(f"   [WARN] {file} not found (skipping)")

# Copy templates directory
print("[*] Copying templates...")
templates_src = dataexplorer_src / 'templates'
templates_dest = dataexplorer_dest / 'templates'
if templates_src.exists():
    if templates_dest.exists():
        shutil.rmtree(templates_dest, ignore_errors=True)
    shutil.copytree(templates_src, templates_dest, dirs_exist_ok=True)
    print(f"   [OK] templates/ ({len(list(templates_src.glob('**/*')))} files)")

# Copy static directory
print("[*] Copying static files...")
static_src = dataexplorer_src / 'static'
static_dest = dataexplorer_dest / 'static'
if static_src.exists():
    if static_dest.exists():
        shutil.rmtree(static_dest, ignore_errors=True)
    shutil.copytree(static_src, static_dest, dirs_exist_ok=True)
    # Remove __pycache__ directories
    for pycache in static_dest.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache, ignore_errors=True)
        except:
            pass
    print(f"   [OK] static/ ({len([f for f in static_src.rglob('*') if f.is_file()])} files)")

# Copy shared directory (DataExplorer depends on it)
print("[*] Copying shared modules...")
shared_src = repo_root / 'shared'
if shared_src.exists():
    shared_dest = package_dir / 'shared'
    if shared_dest.exists():
        shutil.rmtree(shared_dest, ignore_errors=True)
    shutil.copytree(shared_src, shared_dest, dirs_exist_ok=True)
    # Remove __pycache__ directories
    for pycache in shared_dest.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache, ignore_errors=True)
        except:
            pass
    print(f"   [OK] shared/ ({len([f for f in shared_src.rglob('*.py')])} Python files)")

# Copy run script
print("[*] Copying run script...")
run_script_src = repo_root / 'run_dataexplorer.py'
if run_script_src.exists():
    shutil.copy2(run_script_src, package_dir / 'run_dataexplorer.py')
    print("   [OK] run_dataexplorer.py")
else:
    print("   [WARN] run_dataexplorer.py not found (creating default)")
    run_script = package_dir / 'run_dataexplorer.py'
    run_script.write_text("""#!/usr/bin/env python3
\"\"\"
Run DataExplorer dashboard application.
\"\"\"

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.dataexplorer.app import app
from apps.dataexplorer.config import DataExplorerConfig

if __name__ == '__main__':
    port = DataExplorerConfig.PORT
    print(f"Starting DataExplorer on http://127.0.0.1:{port}")
    print(f"Press Ctrl+C to stop")
    app.run(host='127.0.0.1', port=port, debug=True, use_reloader=True, use_debugger=True)
""")

# Create credentials directory structure
print("[*] Creating credentials directory...")
creds_dir = package_dir / 'credentials'
creds_dir.mkdir(exist_ok=True)
(creds_dir / 'README.txt').write_text(
    "Place your bigquery_service_account.json file here.\\n\\n"
    "Alternatively, set the GOOGLE_APPLICATION_CREDENTIALS environment variable\\n"
    "to point to your credentials file location."
)
print("   [OK] credentials/")

# Create requirements.txt if it doesn't exist
print("[*] Creating requirements.txt...")
requirements_src = dataexplorer_src / 'requirements.txt'
if not requirements_src.exists():
    # Check root requirements.txt
    root_requirements = repo_root / 'requirements.txt'
    if root_requirements.exists():
        shutil.copy2(root_requirements, dataexplorer_dest / 'requirements.txt')
        print("   [OK] requirements.txt (copied from root)")
    else:
        # Create a basic requirements.txt
        requirements_dest = dataexplorer_dest / 'requirements.txt'
        requirements_dest.write_text("""flask>=2.3.0
python-dotenv>=1.0.0
pandas>=1.5.0
numpy>=1.21.0
google-cloud-bigquery>=3.0.0
openpyxl>=3.0.0
requests>=2.31.0
census>=0.8.19
""")
        print("   [OK] requirements.txt (created)")
else:
    shutil.copy2(requirements_src, dataexplorer_dest / 'requirements.txt')
    print("   [OK] requirements.txt")

# Create .env.example
print("[*] Creating .env.example...")
env_example = package_dir / '.env.example'
env_example.write_text("""# DataExplorer Configuration
# Copy this file to .env and fill in your values

# Google Cloud Project ID
GCP_PROJECT_ID=hdma1-242116

# BigQuery Credentials (optional if using GOOGLE_APPLICATION_CREDENTIALS env var)
# Path relative to package root/credentials/
# GOOGLE_APPLICATION_CREDENTIALS=credentials/bigquery_service_account.json

# Census API Key (for ACS data)
CENSUS_API_KEY=your_census_api_key_here

# Flask Configuration
SECRET_KEY=change-this-to-a-random-secret-key-in-production
DEBUG=False
PORT=8085
HOST=0.0.0.0
""")
print("   [OK] .env.example")

# Copy documentation files
print("[*] Copying documentation...")
doc_files = [
    'README.md',
    'BRANCH_TABLE_SCHEMA.md',
    'DEVELOPMENT_WORKFLOW.md',
]
for doc_file in doc_files:
    src = dataexplorer_src / doc_file
    if src.exists():
        shutil.copy2(src, dataexplorer_dest / doc_file)
        print(f"   [OK] {doc_file}")

# Create README
print("[*] Creating README...")
readme = package_dir / 'README.md'
readme.write_text("""# DataExplorer Deployment Package

## Quick Start

1. **Extract this package** to your desired location

2. **Install Python dependencies**:
   ```bash
   pip install -r apps/dataexplorer/requirements.txt
   ```

3. **Set up credentials**:
   - Place `bigquery_service_account.json` in `credentials/` directory
   - Copy `.env.example` to `.env` and fill in your values
   - Add your Census API key to `.env` for ACS data features

4. **Run the application**:
   ```bash
   python run_dataexplorer.py
   ```
   Or:
   ```bash
   python -m apps.dataexplorer.app
   ```

5. **Open your browser** to `http://localhost:8085`

## Features

- **Area Analysis**: Analyze mortgage, small business, and branch data by geography
- **Lender Analysis**: Compare lenders against peers across multiple data types
- **Excel Export**: Export comprehensive reports with multiple sheets
- **Interactive Dashboards**: Dynamic charts and tables with filtering

## Required Credentials

- **BigQuery Service Account JSON**: Place in `credentials/bigquery_service_account.json`
- **Census API Key**: Set `CENSUS_API_KEY` in `.env` file (for ACS demographic data)

## Configuration

The application uses the following default settings:
- **Port**: 8085
- **Project ID**: hdma1-242116
- **BigQuery Datasets**: hmda, sb, branches, geo

See `apps/dataexplorer/config.py` for all configuration options.

## Support

For issues or questions, refer to the documentation files in `apps/dataexplorer/` or contact the development team.
""")
print("   [OK] README.md")

# Create installation script
print("[*] Creating installation scripts...")

# Windows batch script
install_bat = package_dir / 'install.bat'
install_bat.write_text("""@echo off
echo Installing DataExplorer Dependencies...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing Python packages...
pip install --upgrade pip
pip install -r apps\\dataexplorer\\requirements.txt

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env and fill in your values
echo 2. Place bigquery_service_account.json in credentials\\ directory
echo 3. Add your Census API key to .env file
echo 4. Run: python run_dataexplorer.py
echo.
pause
""")
print("   [OK] install.bat")

# Linux/macOS shell script
install_sh = package_dir / 'install.sh'
install_sh.write_text("""#!/bin/bash
echo "Installing DataExplorer Dependencies..."
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Install dependencies
echo "Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r apps/dataexplorer/requirements.txt

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in your values"
echo "2. Place bigquery_service_account.json in credentials/ directory"
echo "3. Add your Census API key to .env file"
echo "4. Run: python3 run_dataexplorer.py"
echo
""")
os.chmod(install_sh, 0o755)
print("   [OK] install.sh")

# Create run script
run_bat = package_dir / 'run_dataexplorer.bat'
run_bat.write_text("""@echo off
cd /d "%~dp0"
echo Starting DataExplorer...
echo Access at: http://localhost:8085
python run_dataexplorer.py
pause
""")
print("   [OK] run_dataexplorer.bat")

run_sh = package_dir / 'run_dataexplorer.sh'
run_sh.write_text("""#!/bin/bash
cd "$(dirname "$0")"
echo "Starting DataExplorer..."
echo "Access at: http://localhost:8085"
python3 run_dataexplorer.py
""")
os.chmod(run_sh, 0o755)
print("   [OK] run_dataexplorer.sh")

# Create zip file
print()
print("[*] Creating ZIP archive...")
with zipfile.ZipFile(package_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(package_dir):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            # Skip unnecessary files
            if file.endswith(('.pyc', '.pyo', '.log', '.tmp')):
                continue
            file_path = Path(root) / file
            if '__pycache__' in str(file_path):
                continue
            arcname = file_path.relative_to(package_dir)
            zipf.write(file_path, arcname)

zip_size = package_zip.stat().st_size / (1024 * 1024)  # MB
print()
print(f"[SUCCESS] Package created successfully!")
print(f"   ZIP: {package_zip}")
print(f"   Size: {zip_size:.2f} MB")
print(f"   Directory: {package_dir}")
print()

# Copy to Downloads folder
downloads_path = Path.home() / 'Downloads'
if downloads_path.exists():
    zip_dest = downloads_path / package_zip.name
    shutil.copy2(package_zip, zip_dest)
    print(f"[OK] Copied to Downloads: {zip_dest}")
else:
    print("[WARN] Downloads folder not found, ZIP is in repo root")

print()
print("Next steps:")
print("   1. Review the package contents in the directory")
print("   2. Test the package by extracting and running install scripts")
print("   3. Share the ZIP file with Jad")
print()

