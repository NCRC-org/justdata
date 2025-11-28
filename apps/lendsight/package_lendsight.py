#!/usr/bin/env python3
"""
LendSight Packaging Script
Creates a deployment-ready package with all necessary files.
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def create_deployment_package():
    """Create a deployment package for LendSight."""
    
    # Get paths
    script_dir = Path(__file__).parent.absolute()
    repo_root = script_dir.parent.parent.absolute()
    package_dir = repo_root / 'lendsight_deployment'
    package_zip = repo_root / f'lendsight_deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    
    print("[*] Creating LendSight Deployment Package")
    print(f"   Source: {script_dir}")
    print(f"   Package: {package_dir}")
    print(f"   Zip: {package_zip}")
    print()
    
    # Clean up old package directory
    if package_dir.exists():
        print("[*] Removing old package directory...")
        shutil.rmtree(package_dir)
    
    # Create package structure
    print("[*] Creating package structure...")
    package_dir.mkdir(exist_ok=True)
    
    # Copy LendSight application files
    lendsight_dest = package_dir / 'apps' / 'lendsight'
    lendsight_dest.mkdir(parents=True, exist_ok=True)
    
    files_to_copy = [
        '__init__.py',
        'app.py',
        'core.py',
        'config.py',
        'data_utils.py',
        'analysis.py',
        'census_utils.py',
        'mortgage_report_builder.py',
    ]
    
    print("[*] Copying application files...")
    for file in files_to_copy:
        src = script_dir / file
        if src.exists():
            shutil.copy2(src, lendsight_dest / file)
            print(f"   [OK] {file}")
        else:
            print(f"   [WARN] {file} not found (skipping)")
    
    # Copy templates directory
    print("[*] Copying templates...")
    templates_src = script_dir / 'templates'
    templates_dest = lendsight_dest / 'templates'
    if templates_src.exists():
        shutil.copytree(templates_src, templates_dest, dirs_exist_ok=True)
        print(f"   [OK] templates/ ({len(list(templates_src.glob('**/*')))} files)")
    
    # Copy sql_templates directory
    print("[*] Copying SQL templates...")
    sql_templates_src = script_dir / 'sql_templates'
    sql_templates_dest = lendsight_dest / 'sql_templates'
    if sql_templates_src.exists():
        shutil.copytree(sql_templates_src, sql_templates_dest, dirs_exist_ok=True)
        print(f"   [OK] sql_templates/ ({len(list(sql_templates_src.glob('**/*')))} files)")
    
    # Copy shared directory (LendSight depends on it)
    print("[*] Copying shared modules...")
    shared_src = repo_root / 'shared'
    if shared_src.exists():
        shared_dest = package_dir / 'shared'
        shutil.copytree(shared_src, shared_dest, dirs_exist_ok=True)
        # Remove __pycache__ directories
        for pycache in shared_dest.rglob('__pycache__'):
            shutil.rmtree(pycache)
        print(f"   [OK] shared/ ({len([f for f in shared_src.rglob('*.py')])} Python files)")
    
    # Create data/reports directory
    print("[*] Creating data directories...")
    data_dir = lendsight_dest / 'data' / 'reports'
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / '.gitkeep').touch()
    print("   [OK] data/reports/")
    
    # Create credentials directory structure
    print("[*] Creating credentials directory...")
    creds_dir = package_dir / 'credentials'
    creds_dir.mkdir(exist_ok=True)
    (creds_dir / 'README.txt').write_text(
        "Place your bigquery_service_account.json file here.\n\n"
        "Alternatively, set the GOOGLE_APPLICATION_CREDENTIALS environment variable\n"
        "to point to your credentials file location."
    )
    print("   [OK] credentials/")
    
    # Copy documentation
    print("[*] Copying documentation...")
    docs = [
        'MEMBER_REPORT_METHODOLOGY.md',
        'HMDA_DATA_SCHEMA.md',
    ]
    for doc in docs:
        src = script_dir / doc
        if src.exists():
            shutil.copy2(src, package_dir / doc)
            print(f"   [OK] {doc}")
    
    # Create requirements.txt if it doesn't exist
    print("[*] Creating requirements.txt...")
    requirements_src = script_dir / 'requirements.txt'
    if not requirements_src.exists():
        # Check root requirements.txt
        root_requirements = repo_root / 'requirements.txt'
        if root_requirements.exists():
            shutil.copy2(root_requirements, lendsight_dest / 'requirements.txt')
            print("   [OK] requirements.txt (copied from root)")
        else:
            # Create a basic requirements.txt
            requirements_dest = lendsight_dest / 'requirements.txt'
            requirements_dest.write_text("""flask>=2.3.0
python-dotenv>=1.0.0
pandas>=1.5.0
numpy>=1.21.0
google-cloud-bigquery>=3.0.0
anthropic>=0.7.0
openai>=1.0.0
openpyxl>=3.0.0
playwright>=1.40.0
reportlab>=4.0.0
Pillow>=10.0.0
requests>=2.31.0
""")
            print("   [OK] requirements.txt (created)")
    else:
        shutil.copy2(requirements_src, lendsight_dest / 'requirements.txt')
        print("   [OK] requirements.txt")
    
    # Create .env.example
    print("[*] Creating .env.example...")
    env_example = package_dir / '.env.example'
    env_example.write_text("""# LendSight Configuration
# Copy this file to .env and fill in your values

# AI Provider (claude or openai)
AI_PROVIDER=claude

# Claude API Key (if using Claude)
CLAUDE_API_KEY=your_claude_api_key_here

# OpenAI API Key (if using OpenAI)
# OPENAI_API_KEY=your_openai_api_key_here

# Google Cloud Project ID
GCP_PROJECT_ID=hdma1-242116

# BigQuery Credentials (optional if using GOOGLE_APPLICATION_CREDENTIALS env var)
# Path relative to package root/credentials/
# GOOGLE_APPLICATION_CREDENTIALS=credentials/bigquery_service_account.json

# Flask Configuration
SECRET_KEY=change-this-to-a-random-secret-key-in-production
DEBUG=False
PORT=8082
HOST=0.0.0.0

# AI Model Configuration (optional)
CLAUDE_MODEL=claude-sonnet-4-20250514
GPT_MODEL=gpt-4
""")
    print("   [OK] .env.example")
    
    # Create README
    print("[*] Creating README...")
    readme = package_dir / 'README.md'
    readme.write_text("""# LendSight Deployment Package

## Quick Start

1. **Extract this package** to your desired location

2. **Install Python dependencies**:
   ```bash
   pip install -r apps/lendsight/requirements.txt
   playwright install chromium
   ```

3. **Set up credentials**:
   - Place `bigquery_service_account.json` in `credentials/` directory
   - Copy `.env.example` to `.env` and fill in your API keys

4. **Run the application**:
   ```bash
   cd "#JustData_Repo"
   python -m apps.lendsight.app
   ```

5. **Open your browser** to `http://localhost:8082`

## Full Documentation

See `DEPLOYMENT_PACKAGE.md` for complete installation and configuration instructions.

## Required Credentials

- **BigQuery Service Account JSON**: Place in `credentials/bigquery_service_account.json`
- **AI API Key**: Set `CLAUDE_API_KEY` or `OPENAI_API_KEY` in `.env` file

## Support

For issues or questions, refer to `DEPLOYMENT_PACKAGE.md` or contact the development team.
""")
    print("   [OK] README.md")
    
    # Create installation script
    print("[*] Creating installation scripts...")
    
    # Windows batch script
    install_bat = package_dir / 'install.bat'
    install_bat.write_text("""@echo off
echo Installing LendSight Dependencies...
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
pip install -r apps\\lendsight\\requirements.txt

REM Install Playwright browser
echo Installing Playwright browser...
playwright install chromium

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env and fill in your API keys
echo 2. Place bigquery_service_account.json in credentials\\ directory
echo 3. Run: python -m apps.lendsight.app
echo.
pause
""")
    print("   [OK] install.bat")
    
    # Linux/macOS shell script
    install_sh = package_dir / 'install.sh'
    install_sh.write_text("""#!/bin/bash
echo "Installing LendSight Dependencies..."
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Install dependencies
echo "Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r apps/lendsight/requirements.txt

# Install Playwright browser
echo "Installing Playwright browser..."
playwright install chromium

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in your API keys"
echo "2. Place bigquery_service_account.json in credentials/ directory"
echo "3. Run: python3 -m apps.lendsight.app"
echo
""")
    os.chmod(install_sh, 0o755)
    print("   [OK] install.sh")
    
    # Create run script
    run_bat = package_dir / 'run_lendsight.bat'
    run_bat.write_text("""@echo off
cd /d "%~dp0"
echo Starting LendSight...
echo Access at: http://localhost:8082
python -m apps.lendsight.app
pause
""")
    print("   [OK] run_lendsight.bat")
    
    run_sh = package_dir / 'run_lendsight.sh'
    run_sh.write_text("""#!/bin/bash
cd "$(dirname "$0")"
echo "Starting LendSight..."
echo "Access at: http://localhost:8082"
python3 -m apps.lendsight.app
""")
    os.chmod(run_sh, 0o755)
    print("   [OK] run_lendsight.sh")
    
    # Create zip file
    print()
    print("[*] Creating ZIP archive...")
    with zipfile.ZipFile(package_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                file_path = Path(root) / file
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
    print("   3. Share the ZIP file with the deployment team")
    print()

if __name__ == '__main__':
    try:
        create_deployment_package()
    except Exception as e:
        print(f"\n[ERROR] Error creating package: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

