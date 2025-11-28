#!/usr/bin/env python3
"""
BizSight Packaging Script
Creates a deployment-ready package with all necessary files.
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def create_deployment_package():
    """Create a deployment package for BizSight."""
    
    # Get paths
    script_dir = Path(__file__).parent.absolute()
    repo_root = script_dir.parent.parent.absolute()
    package_dir = repo_root / 'bizsight_deployment'
    package_zip = repo_root / f'bizsight_deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    
    print("📦 Creating BizSight Deployment Package")
    print(f"   Source: {script_dir}")
    print(f"   Package: {package_dir}")
    print(f"   Zip: {package_zip}")
    print()
    
    # Clean up old package directory
    if package_dir.exists():
        print("🗑️  Removing old package directory...")
        shutil.rmtree(package_dir)
    
    # Create package structure
    print("📁 Creating package structure...")
    package_dir.mkdir(exist_ok=True)
    
    # Copy BizSight application files
    bizsight_dest = package_dir / 'apps' / 'bizsight'
    bizsight_dest.mkdir(parents=True, exist_ok=True)
    
    files_to_copy = [
        '__init__.py',
        'app.py',
        'core.py',
        'config.py',
        'data_utils.py',
        'report_builder.py',
        'ai_analysis.py',
        'excel_export.py',
        'requirements.txt',
    ]
    
    print("📋 Copying application files...")
    for file in files_to_copy:
        src = script_dir / file
        if src.exists():
            shutil.copy2(src, bizsight_dest / file)
            print(f"   ✓ {file}")
        else:
            print(f"   ⚠️  {file} not found (skipping)")
    
    # Copy templates directory
    print("📋 Copying templates...")
    templates_src = script_dir / 'templates'
    templates_dest = bizsight_dest / 'templates'
    if templates_src.exists():
        shutil.copytree(templates_src, templates_dest, dirs_exist_ok=True)
        print(f"   ✓ templates/ ({len(list(templates_src.glob('**/*')))} files)")
    
    # Copy utils directory
    print("📋 Copying utilities...")
    utils_src = script_dir / 'utils'
    utils_dest = bizsight_dest / 'utils'
    if utils_src.exists():
        shutil.copytree(utils_src, utils_dest, dirs_exist_ok=True)
        # Remove __pycache__ directories
        for pycache in utils_dest.rglob('__pycache__'):
            shutil.rmtree(pycache)
        print(f"   ✓ utils/ ({len([f for f in utils_src.rglob('*.py')])} files)")
    
    # Create data/reports directory
    print("📋 Creating data directories...")
    data_dir = bizsight_dest / 'data' / 'reports'
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / '.gitkeep').touch()
    print("   ✓ data/reports/")
    
    # Copy core/config if it exists
    print("📋 Copying shared core modules...")
    core_config_src = repo_root / 'core' / 'config'
    if core_config_src.exists():
        core_config_dest = package_dir / 'core' / 'config'
        core_config_dest.mkdir(parents=True, exist_ok=True)
        for file in core_config_src.glob('*.py'):
            shutil.copy2(file, core_config_dest / file.name)
        print(f"   ✓ core/config/ ({len(list(core_config_src.glob('*.py')))} files)")
    
    # Create credentials directory structure
    print("📋 Creating credentials directory...")
    creds_dir = package_dir / 'credentials'
    creds_dir.mkdir(exist_ok=True)
    (creds_dir / 'README.txt').write_text(
        "Place your bigquery_service_account.json file here.\n\n"
        "Alternatively, set the GOOGLE_APPLICATION_CREDENTIALS environment variable\n"
        "to point to your credentials file location."
    )
    print("   ✓ credentials/")
    
    # Copy documentation
    print("📋 Copying documentation...")
    docs = [
        'DEPLOYMENT_PACKAGE.md',
    ]
    for doc in docs:
        src = script_dir / doc
        if src.exists():
            shutil.copy2(src, package_dir / doc)
            print(f"   ✓ {doc}")
    
    # Create .env.example
    print("📋 Creating .env.example...")
    env_example = package_dir / '.env.example'
    env_example.write_text("""# BizSight Configuration
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
# Path relative to #JustData_Repo/credentials/
# GOOGLE_APPLICATION_CREDENTIALS=credentials/bigquery_service_account.json

# Flask Configuration
SECRET_KEY=change-this-to-a-random-secret-key-in-production
DEBUG=False
PORT=8081
HOST=0.0.0.0

# AI Model Configuration (optional)
CLAUDE_MODEL=claude-sonnet-4-20250514
GPT_MODEL=gpt-4
""")
    print("   ✓ .env.example")
    
    # Create README
    print("📋 Creating README...")
    readme = package_dir / 'README.md'
    readme.write_text("""# BizSight Deployment Package

## Quick Start

1. **Extract this package** to your desired location

2. **Install Python dependencies**:
   ```bash
   pip install -r apps/bizsight/requirements.txt
   playwright install chromium
   ```

3. **Set up credentials**:
   - Place `bigquery_service_account.json` in `credentials/` directory
   - Copy `.env.example` to `.env` and fill in your API keys

4. **Run the application**:
   ```bash
   cd "#JustData_Repo"
   python -m apps.bizsight.app
   ```

5. **Open your browser** to `http://localhost:8081`

## Full Documentation

See `DEPLOYMENT_PACKAGE.md` for complete installation and configuration instructions.

## Required Credentials

- **BigQuery Service Account JSON**: Place in `credentials/bigquery_service_account.json`
- **AI API Key**: Set `CLAUDE_API_KEY` or `OPENAI_API_KEY` in `.env` file

## Support

For issues or questions, refer to `DEPLOYMENT_PACKAGE.md` or contact the development team.
""")
    print("   ✓ README.md")
    
    # Create installation script
    print("📋 Creating installation scripts...")
    
    # Windows batch script
    install_bat = package_dir / 'install.bat'
    install_bat.write_text("""@echo off
echo Installing BizSight Dependencies...
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
pip install -r apps\\bizsight\\requirements.txt

REM Install Playwright browser
echo Installing Playwright browser...
playwright install chromium

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env and fill in your API keys
echo 2. Place bigquery_service_account.json in credentials\\ directory
echo 3. Run: python -m apps.bizsight.app
echo.
pause
""")
    print("   ✓ install.bat")
    
    # Linux/macOS shell script
    install_sh = package_dir / 'install.sh'
    install_sh.write_text("""#!/bin/bash
echo "Installing BizSight Dependencies..."
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Install dependencies
echo "Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r apps/bizsight/requirements.txt

# Install Playwright browser
echo "Installing Playwright browser..."
playwright install chromium

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in your API keys"
echo "2. Place bigquery_service_account.json in credentials/ directory"
echo "3. Run: python3 -m apps.bizsight.app"
echo
""")
    os.chmod(install_sh, 0o755)
    print("   ✓ install.sh")
    
    # Create run script
    run_bat = package_dir / 'run_bizsight.bat'
    run_bat.write_text("""@echo off
cd /d "%~dp0"
echo Starting BizSight...
python -m apps.bizsight.app
pause
""")
    print("   ✓ run_bizsight.bat")
    
    run_sh = package_dir / 'run_bizsight.sh'
    run_sh.write_text("""#!/bin/bash
cd "$(dirname "$0")"
echo "Starting BizSight..."
python3 -m apps.bizsight.app
""")
    os.chmod(run_sh, 0o755)
    print("   ✓ run_bizsight.sh")
    
    # Create zip file
    print()
    print("📦 Creating ZIP archive...")
    with zipfile.ZipFile(package_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
                print(f"   ✓ {arcname}")
    
    zip_size = package_zip.stat().st_size / (1024 * 1024)  # MB
    print()
    print(f"✅ Package created successfully!")
    print(f"   📦 ZIP: {package_zip}")
    print(f"   📊 Size: {zip_size:.2f} MB")
    print(f"   📁 Directory: {package_dir}")
    print()
    print("📝 Next steps:")
    print("   1. Review the package contents in the directory")
    print("   2. Test the package by extracting and running install scripts")
    print("   3. Share the ZIP file with the deployment team")
    print()

if __name__ == '__main__':
    try:
        create_deployment_package()
    except Exception as e:
        print(f"\n❌ Error creating package: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

