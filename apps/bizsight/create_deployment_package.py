#!/usr/bin/env python3
"""
BizSight Complete Deployment Package Creator
Creates a comprehensive deployment-ready package with all necessary files.
"""

import os
import shutil
import zipfile
import errno
import stat
from pathlib import Path
from datetime import datetime

def create_deployment_package():
    """Create a complete deployment package for BizSight."""
    
    # Get paths
    script_dir = Path(__file__).parent.absolute()
    repo_root = script_dir.parent.parent.absolute()
    
    # Use Downloads folder for final ZIP, temp directory in repo for building
    downloads_folder = Path.home() / 'Downloads'
    package_dir = repo_root / 'bizsight_deployment_temp'
    package_zip = downloads_folder / f'bizsight_deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    
    print("=" * 80)
    print("📦 Creating BizSight Complete Deployment Package")
    print("=" * 80)
    print(f"   Source: {script_dir}")
    print(f"   Package: {package_dir}")
    print(f"   Zip: {package_zip}")
    print()
    
    # Clean up old package directory (with error handling)
    # If cleanup fails, we'll just overwrite files since we use dirs_exist_ok=True
    if package_dir.exists():
        print("🗑️  Attempting to remove old package directory...")
        max_retries = 3
        removed = False
        for attempt in range(max_retries):
            try:
                # Try to remove, but handle permission errors gracefully
                def handle_remove_readonly(func, path, exc):
                    if func in (os.rmdir, os.remove, os.unlink):
                        try:
                            exc_info = exc[1] if len(exc) > 1 else None
                            if exc_info and hasattr(exc_info, 'errno') and exc_info.errno == errno.EACCES:
                                # Change permissions and retry
                                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                                func(path)
                        except:
                            # If we still can't remove it, just skip
                            pass
                
                shutil.rmtree(package_dir, onerror=handle_remove_readonly)
                removed = True
                print("   ✓ Old directory removed")
                break
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.5)  # Wait a bit and retry
                    continue
                else:
                    print(f"   ⚠️  Could not remove old directory (will overwrite files): {e}")
                    # Continue anyway - copytree with dirs_exist_ok will handle it
    
    # Create package structure
    print("📁 Creating package structure...")
    package_dir.mkdir(exist_ok=True)
    
    # Copy BizSight application files
    bizsight_dest = package_dir / 'apps' / 'bizsight'
    bizsight_dest.mkdir(parents=True, exist_ok=True)
    
    # All Python files to copy
    python_files = [
        '__init__.py',
        'app.py',
        'core.py',
        'config.py',
        'data_utils.py',
        'report_builder.py',
        'ai_analysis.py',
        'excel_export.py',
        'generate_benchmarks.py',
        'requirements.txt',
    ]
    
    print("📋 Copying application files...")
    for file in python_files:
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
        template_count = len(list(templates_src.glob('**/*.html')))
        print(f"   ✓ templates/ ({template_count} HTML files)")
    
    # Copy static files (CSS, JS, images)
    print("📋 Copying static files...")
    static_src = script_dir / 'static'
    static_dest = bizsight_dest / 'static'
    if static_src.exists():
        shutil.copytree(static_src, static_dest, dirs_exist_ok=True)
        # Count files
        css_files = len(list(static_src.glob('**/*.css')))
        js_files = len(list(static_src.glob('**/*.js')))
        img_files = len(list(static_src.glob('**/*.{jpg,png,gif,svg}')))
        print(f"   ✓ static/ ({css_files} CSS, {js_files} JS, {img_files} images)")
    
    # Copy utils directory
    print("📋 Copying utilities...")
    utils_src = script_dir / 'utils'
    utils_dest = bizsight_dest / 'utils'
    if utils_src.exists():
        # Copy files individually, excluding __pycache__
        utils_dest.mkdir(parents=True, exist_ok=True)
        for item in utils_src.iterdir():
            if item.name == '__pycache__':
                continue  # Skip __pycache__ directories
            if item.is_file() and item.suffix == '.py':
                shutil.copy2(item, utils_dest / item.name)
            elif item.is_dir() and item.name != '__pycache__':
                # Use copytree with ignore to exclude __pycache__
                def ignore_pycache(dir, names):
                    return [n for n in names if n == '__pycache__']
                try:
                    shutil.copytree(item, utils_dest / item.name, dirs_exist_ok=True, ignore=ignore_pycache)
                except Exception as e:
                    print(f"   ⚠️  Warning copying {item.name}: {e}")
        # Count Python files (excluding __pycache__)
        py_count = len([f for f in utils_src.rglob('*.py') if '__pycache__' not in str(f)])
        print(f"   ✓ utils/ ({py_count} Python files)")
    
    # Create data directory and copy benchmark files if they exist
    print("📋 Creating data directories...")
    data_dir = bizsight_dest / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create reports subdirectory
    reports_dir = data_dir / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / '.gitkeep').touch()
    print("   ✓ data/reports/")
    
    # Copy benchmark files if they exist
    print("📋 Checking for benchmark files...")
    repo_root = script_dir.parent.parent
    possible_benchmark_dirs = [
        repo_root / 'apps' / 'data',  # apps/data (primary location)
        repo_root / 'data',  # #JustData_Repo/data
        repo_root / 'data' / 'benchmarks',  # #JustData_Repo/data/benchmarks
        script_dir / 'data',  # apps/bizsight/data
    ]
    
    benchmark_files_copied = 0
    benchmark_dir_found = None
    
    # Find directory with benchmark files
    for bench_dir in possible_benchmark_dirs:
        if bench_dir.exists():
            # Check for national.json as indicator
            national_file = bench_dir / 'national.json'
            if national_file.exists():
                benchmark_dir_found = bench_dir
                break
    
    if benchmark_dir_found:
        print(f"   Found benchmark files in: {benchmark_dir_found}")
        # Copy all JSON files (state benchmarks, national, consolidated)
        for json_file in benchmark_dir_found.glob('*.json'):
            if json_file.name not in ['benchmarks.json']:  # Skip consolidated if individual files exist
                dest_file = data_dir / json_file.name
                shutil.copy2(json_file, dest_file)
                benchmark_files_copied += 1
                print(f"   ✓ {json_file.name}")
        
        # Also copy consolidated file if it exists and we didn't copy individual files
        consolidated_file = benchmark_dir_found / 'benchmarks.json'
        if consolidated_file.exists() and benchmark_files_copied == 0:
            shutil.copy2(consolidated_file, data_dir / 'benchmarks.json')
            benchmark_files_copied = 1
            print(f"   ✓ benchmarks.json (consolidated)")
        
        if benchmark_files_copied > 0:
            print(f"   ✓ Copied {benchmark_files_copied} benchmark file(s)")
        else:
            print("   ⚠️  No benchmark JSON files found in directory")
    else:
        print("   ⚠️  Benchmark files not found (application will query BigQuery as fallback)")
        print("   💡 To generate benchmarks, run: python apps/bizsight/generate_benchmarks.py")
    
    # Create credentials directory structure
    print("📋 Creating credentials directory...")
    creds_dir = package_dir / 'credentials'
    creds_dir.mkdir(exist_ok=True)
    (creds_dir / 'README.txt').write_text(
        "PLACE YOUR BIGQUERY CREDENTIALS HERE\n"
        "====================================\n\n"
        "1. Place your 'bigquery_service_account.json' file in this directory.\n\n"
        "2. Alternatively, set the GOOGLE_APPLICATION_CREDENTIALS environment variable\n"
        "   to point to your credentials file location.\n\n"
        "3. The service account must have the following BigQuery permissions:\n"
        "   - BigQuery Data Viewer\n"
        "   - BigQuery Job User\n\n"
        "4. To obtain credentials:\n"
        "   a. Go to Google Cloud Console\n"
        "   b. Navigate to IAM & Admin > Service Accounts\n"
        "   c. Create or select a service account\n"
        "   d. Create a JSON key and download it\n"
        "   e. Place the JSON file here as 'bigquery_service_account.json'\n",
        encoding='utf-8'
    )
    print("   ✓ credentials/")
    
    # Create .env.example
    print("📋 Creating .env.example...")
    env_example = package_dir / '.env.example'
    env_example.write_text("""# BizSight Configuration File
# Copy this file to .env and fill in your actual values
# DO NOT commit .env to version control!

# ============================================
# AI Provider Configuration
# ============================================
# Choose ONE: 'claude' or 'openai'
AI_PROVIDER=claude

# Claude API Key (if using Claude)
# Get from: https://console.anthropic.com/
CLAUDE_API_KEY=your_claude_api_key_here

# OpenAI API Key (if using OpenAI)
# Get from: https://platform.openai.com/
# OPENAI_API_KEY=your_openai_api_key_here

# ============================================
# Google Cloud / BigQuery Configuration
# ============================================
# Your Google Cloud Project ID
GCP_PROJECT_ID=hdma1-242116

# BigQuery Credentials (optional if using GOOGLE_APPLICATION_CREDENTIALS env var)
# Path relative to package root/credentials/
# GOOGLE_APPLICATION_CREDENTIALS=credentials/bigquery_service_account.json

# ============================================
# Flask Application Configuration
# ============================================
# Generate a secure secret key: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=change-this-to-a-random-secret-key-in-production

# Set to False in production
DEBUG=False

# Server port (default: 8081)
PORT=8081

# Server host (0.0.0.0 to accept connections from any IP)
HOST=0.0.0.0

# ============================================
# AI Model Configuration (Optional)
# ============================================
# Claude model name
CLAUDE_MODEL=claude-sonnet-4-20250514

# OpenAI model name
GPT_MODEL=gpt-4
""", encoding='utf-8')
    print("   ✓ .env.example")
    
    # Create comprehensive README
    print("📋 Creating README...")
    readme = package_dir / 'README.md'
    readme.write_text("""# BizSight - Small Business Lending Analysis Application

## Overview

BizSight is a web-based application for analyzing small business lending data at the county level. It provides comprehensive reports with interactive maps, tables, and AI-generated insights.

## Quick Start Guide

### 1. Prerequisites

- **Python 3.8+** (3.9+ recommended)
- **pip** (Python package manager)
- **Google Cloud Account** with BigQuery access
- **AI API Key** (Claude or OpenAI)

### 2. Installation

#### Windows:
```bash
# Run the installation script
install.bat
```

#### macOS/Linux:
```bash
# Make script executable and run
chmod +x install.sh
./install.sh
```

#### Manual Installation:
```bash
# Install Python dependencies
pip install -r apps/bizsight/requirements.txt

# Install Playwright browser (required for PDF export)
playwright install chromium
```

### 3. Configuration

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** and add your credentials:
   - `CLAUDE_API_KEY` or `OPENAI_API_KEY`
   - `GCP_PROJECT_ID` (if different from default)
   - `SECRET_KEY` (generate a secure random key)

3. **Place BigQuery credentials:**
   - Download your service account JSON key from Google Cloud Console
   - Place it in `credentials/bigquery_service_account.json`

4. **Generate Benchmark Data (if not included):**
   - If benchmark files (state and national) are not in `apps/data/`, generate them:
   ```bash
   python apps/bizsight/generate_benchmarks.py
   ```
   - This will create 52 state benchmark files plus a national benchmark file
   - The application can also query BigQuery directly if benchmarks are missing

### 4. Run the Application

#### Windows:
```bash
run_bizsight.bat
```

#### macOS/Linux:
```bash
./run_bizsight.sh
```

#### Manual:
```bash
cd "#JustData_Repo"
python -m apps.bizsight.app
```

### 5. Access the Application

Open your browser to: `http://localhost:8081`

## Required Credentials

### 1. BigQuery Service Account

**Location:** `credentials/bigquery_service_account.json`

**Required Permissions:**
- BigQuery Data Viewer
- BigQuery Job User

**How to Obtain:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **IAM & Admin > Service Accounts**
3. Create or select a service account
4. Click **Keys > Add Key > Create new key > JSON**
5. Download the JSON file
6. Place it in the `credentials/` directory

### 2. AI API Key

Choose ONE of the following:

#### Option A: Claude (Anthropic) - Recommended
- **Environment Variable:** `CLAUDE_API_KEY`
- **Get from:** [Anthropic Console](https://console.anthropic.com/)
- **Set in:** `.env` file

#### Option B: OpenAI
- **Environment Variable:** `OPENAI_API_KEY`
- **Get from:** [OpenAI Platform](https://platform.openai.com/)
- **Set in:** `.env` file

## Project Structure

```
bizsight_deployment/
├── apps/
│   └── bizsight/
│       ├── __init__.py
│       ├── app.py              # Main Flask application
│       ├── core.py              # Analysis logic
│       ├── config.py            # Configuration
│       ├── report_builder.py    # Report generation
│       ├── ai_analysis.py       # AI narrative generation
│       ├── excel_export.py      # Excel export functionality
│       ├── templates/           # HTML templates
│       ├── static/              # CSS, JS, images
│       ├── utils/               # Utility modules
│       └── requirements.txt     # Python dependencies
├── credentials/                 # Place BigQuery JSON here
├── .env.example                 # Environment template
├── README.md                    # This file
├── DEPLOYMENT_GUIDE.md          # Detailed deployment guide
├── install.bat                  # Windows installation script
├── install.sh                   # Unix installation script
├── run_bizsight.bat             # Windows run script
└── run_bizsight.sh              # Unix run script
```

## Configuration Options

All configuration is done via environment variables or the `.env` file:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AI_PROVIDER` | AI provider: 'claude' or 'openai' | 'claude' | Yes |
| `CLAUDE_API_KEY` | Claude API key | - | If using Claude |
| `OPENAI_API_KEY` | OpenAI API key | - | If using OpenAI |
| `GCP_PROJECT_ID` | Google Cloud Project ID | 'hdma1-242116' | Yes |
| `SECRET_KEY` | Flask secret key | Auto-generated | Recommended |
| `DEBUG` | Debug mode | False | No |
| `PORT` | Server port | 8081 | No |
| `HOST` | Server host | '0.0.0.0' | No |

## Features

- **Interactive Maps:** Visualize lending data by census tract
- **Comprehensive Tables:** County, state, and national comparisons
- **AI-Generated Insights:** Automated narrative analysis
- **Excel Export:** Download data in Excel format with multiple sheets
- **PDF Export:** Generate PDF reports with maps
- **Market Concentration Analysis:** HHI calculations and trends

## Troubleshooting

### Import Errors
- Ensure all dependencies are installed: `pip install -r apps/bizsight/requirements.txt`
- Check that Python version is 3.8 or higher

### BigQuery Connection Issues
- Verify credentials file is in `credentials/bigquery_service_account.json`
- Check that service account has required permissions
- Verify `GCP_PROJECT_ID` is correct

### AI API Errors
- Verify API key is set correctly in `.env` file
- Check API key has sufficient credits/quota
- Ensure `AI_PROVIDER` matches the API key type

### PDF Export Not Working
- Ensure Playwright is installed: `playwright install chromium`
- Check that Chromium browser is available

## Support

For detailed deployment instructions, see `DEPLOYMENT_GUIDE.md`.

For issues or questions, contact the development team.
""", encoding='utf-8')
    print("   ✓ README.md")
    
    # Create comprehensive deployment guide
    print("📋 Creating deployment guide...")
    deployment_guide = package_dir / 'DEPLOYMENT_GUIDE.md'
    deployment_guide.write_text("""# BizSight Deployment Guide

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Deployment Options](#deployment-options)
5. [Production Considerations](#production-considerations)
6. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **Python:** 3.8 or higher (3.9+ recommended)
- **RAM:** 4GB minimum (8GB+ recommended)
- **Disk Space:** 500MB for application + data storage
- **OS:** Windows 10+, macOS 10.14+, or Linux

### Required Software
1. **Python 3.8+** with pip
2. **Google Cloud SDK** (for BigQuery access)
3. **Playwright** (installed via pip for PDF generation)

## Installation

### Step 1: Extract Package

Extract the deployment package to your desired location:
```bash
unzip bizsight_deployment_YYYYMMDD_HHMMSS.zip
cd bizsight_deployment
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\\Scripts\\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

#### Using Installation Scripts:

**Windows:**
```bash
install.bat
```

**macOS/Linux:**
```bash
chmod +x install.sh
./install.sh
```

#### Manual Installation:
```bash
pip install --upgrade pip
pip install -r apps/bizsight/requirements.txt
playwright install chromium
```

### Step 4: Set Up Credentials

1. **BigQuery Credentials:**
   - Download service account JSON from Google Cloud Console
   - Place in `credentials/bigquery_service_account.json`

2. **Environment Configuration:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys and configuration.

## Configuration

### Environment Variables

Create a `.env` file in the package root:

```env
# AI Provider
AI_PROVIDER=claude
CLAUDE_API_KEY=your_key_here

# Google Cloud
GCP_PROJECT_ID=hdma1-242116

# Flask
SECRET_KEY=your_secret_key_here
DEBUG=False
PORT=8081
HOST=0.0.0.0
```

### Generate Secure Secret Key

```python
import secrets
print(secrets.token_hex(32))
```

## Deployment Options

### Option 1: Development Server

```bash
python -m apps.bizsight.app
```

Access at: `http://localhost:8081`

### Option 2: Production with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8081 "apps.bizsight.app:app"
```

### Option 3: Docker (if Dockerfile provided)

```bash
docker build -t bizsight .
docker run -p 8081:8081 bizsight
```

### Option 4: Cloud Platform Deployment

#### Google Cloud Run:
```bash
gcloud run deploy bizsight --source .
```

#### AWS Elastic Beanstalk:
- Create `Procfile`: `web: gunicorn -w 4 -b 0.0.0.0:8081 "apps.bizsight.app:app"`
- Deploy via EB CLI

#### Heroku:
- Create `Procfile`: `web: gunicorn -w 4 -b 0.0.0.0:$PORT "apps.bizsight.app:app"`
- Set environment variables in Heroku dashboard

## Production Considerations

### Security

1. **Change Secret Key:** Never use default secret key in production
2. **HTTPS:** Use reverse proxy (nginx/Apache) with SSL certificate
3. **Environment Variables:** Never commit `.env` file to version control
4. **API Keys:** Rotate API keys regularly
5. **Credentials:** Store BigQuery credentials securely

### Performance

1. **Caching:** Enable caching for static files
2. **Database Connection Pooling:** Configure BigQuery connection pooling
3. **Load Balancing:** Use multiple workers with Gunicorn
4. **CDN:** Serve static files via CDN

### Monitoring

1. **Logging:** Configure application logging
2. **Error Tracking:** Set up error tracking (Sentry, etc.)
3. **Health Checks:** Implement health check endpoints
4. **Metrics:** Monitor API usage and performance

## Troubleshooting

### Common Issues

#### Import Errors
- **Solution:** Ensure all dependencies installed and Python path correct

#### BigQuery Connection Failed
- **Solution:** Verify credentials file path and permissions

#### AI API Errors
- **Solution:** Check API key validity and quota

#### PDF Export Fails
- **Solution:** Ensure Playwright Chromium is installed

### Logs

Check application logs for detailed error messages:
- Console output (development)
- Log files (production)
- Cloud platform logs (if deployed)

## Support

For additional support, refer to:
- Application logs
- Google Cloud Console
- AI provider documentation
- Development team
""", encoding='utf-8')
    print("   ✓ DEPLOYMENT_GUIDE.md")
    
    # Create installation scripts
    print("📋 Creating installation scripts...")
    
    # Windows batch script
    install_bat = package_dir / 'install.bat'
    install_bat.write_text("""@echo off
echo ========================================
echo BizSight Installation Script
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Checking Python version...
python --version

echo.
echo [2/3] Installing Python packages...
pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip
    pause
    exit /b 1
)

pip install -r apps\\bizsight\\requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [3/3] Installing Playwright browser...
playwright install chromium
if errorlevel 1 (
    echo [WARNING] Playwright installation failed. PDF export may not work.
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Copy .env.example to .env
echo 2. Edit .env and add your API keys
echo 3. Place bigquery_service_account.json in credentials\\ directory
echo 4. Run: run_bizsight.bat
echo.
pause
""", encoding='utf-8')
    print("   ✓ install.bat")
    
    # Linux/macOS shell script
    install_sh = package_dir / 'install.sh'
    install_sh.write_text(r"""#!/bin/bash
echo "========================================"
echo "BizSight Installation Script"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[1/3] Checking Python version..."
python3 --version

echo ""
echo "[2/3] Installing Python packages..."
pip3 install --upgrade pip
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to upgrade pip"
    exit 1
fi

pip3 install -r apps/bizsight/requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

echo ""
echo "[3/3] Installing Playwright browser..."
playwright install chromium
if [ $? -ne 0 ]; then
    echo "[WARNING] Playwright installation failed. PDF export may not work."
fi

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Edit .env and add your API keys"
echo "3. Place bigquery_service_account.json in credentials/ directory"
echo "4. Run: ./run_bizsight.sh"
echo ""
""", encoding='utf-8')
    os.chmod(install_sh, 0o755)
    print("   ✓ install.sh")
    
    # Create run scripts
    run_bat = package_dir / 'run_bizsight.bat'
    run_bat.write_text("""@echo off
cd /d "%~dp0"
echo ========================================
echo Starting BizSight Application
echo ========================================
echo.
echo Access the application at: http://localhost:8081
echo Press Ctrl+C to stop the server
echo.
python -m apps.bizsight.app
pause
""", encoding='utf-8')
    print("   ✓ run_bizsight.bat")
    
    run_sh = package_dir / 'run_bizsight.sh'
    run_sh.write_text("""#!/bin/bash
cd "$(dirname "$0")"
echo "========================================"
echo "Starting BizSight Application"
echo "========================================"
echo ""
echo "Access the application at: http://localhost:8081"
echo "Press Ctrl+C to stop the server"
echo ""
python3 -m apps.bizsight.app
""", encoding='utf-8')
    os.chmod(run_sh, 0o755)
    print("   ✓ run_bizsight.sh")
    
    # Create zip file
    print()
    print("📦 Creating ZIP archive...")
    files_added = 0
    with zipfile.ZipFile(package_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            # Skip __pycache__ and other unnecessary directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', '.venv']]
            for file in files:
                # Skip unnecessary files
                if file.endswith(('.pyc', '.pyo', '.log', '.tmp')):
                    continue
                file_path = Path(root) / file
                # Skip if path contains __pycache__
                if '__pycache__' in str(file_path):
                    continue
                try:
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
                    files_added += 1
                except (PermissionError, OSError) as e:
                    print(f"   ⚠️  Skipping {file_path.name} (permission error)")
                    continue
    
    zip_size = package_zip.stat().st_size / (1024 * 1024)  # MB
    print(f"   ✓ Added {files_added} files to archive")
    print()
    print("=" * 80)
    print("✅ DEPLOYMENT PACKAGE CREATED SUCCESSFULLY!")
    print("=" * 80)
    print(f"   📦 ZIP File: {package_zip.name}")
    print(f"   📊 Size: {zip_size:.2f} MB")
    print(f"   📁 Directory: {package_dir}")
    print(f"   📄 Files: {files_added}")
    print()
    print("📝 Next Steps:")
    print("   1. Review package contents in the directory")
    print("   2. Test installation on a clean system")
    print("   3. Share ZIP file with deployment team")
    print("   4. Provide credentials separately (NOT in package)")
    print()
    print("⚠️  IMPORTANT:")
    print("   - DO NOT include credentials in the package")
    print("   - Share API keys and BigQuery credentials separately")
    print("   - Review .env.example for required configuration")
    print("=" * 80)

if __name__ == '__main__':
    try:
        create_deployment_package()
    except Exception as e:
        print(f"\n❌ Error creating package: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

