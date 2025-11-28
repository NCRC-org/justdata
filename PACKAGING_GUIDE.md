# JustData Application Packaging Guide

This document explains how to package JustData applications (LendSight, BranchSeeker, BranchMapper) for deployment, based on the successful BizSight packaging process.

## Overview

The packaging process creates a self-contained deployment package that includes:
- All application source code
- Templates and static files
- Configuration files
- Installation and run scripts
- Documentation
- A ZIP archive for easy distribution

**Note:** Credentials, API keys, and environment-specific files are NOT included for security reasons.

---

## BizSight Packaging Process (Reference)

BizSight was successfully packaged using `apps/bizsight/package_bizsight.py`. The process includes:

### 1. Package Structure
```
{app}_deployment/
├── apps/
│   └── {app}/
│       ├── __init__.py
│       ├── app.py
│       ├── core.py
│       ├── config.py
│       ├── data_utils.py
│       ├── requirements.txt
│       ├── templates/
│       ├── utils/ (if exists)
│       └── sql_templates/ (if exists)
├── core/ (shared modules, if needed)
├── shared/ (shared modules, if needed)
├── credentials/ (empty, with README)
├── .env.example
├── README.md
├── DEPLOYMENT_PACKAGE.md
├── install.bat / install.sh
└── run_{app}.bat / run_{app}.sh
```

### 2. Key Steps

1. **Clean old package** - Remove existing deployment directory
2. **Create structure** - Set up directory hierarchy
3. **Copy application files** - All Python source files
4. **Copy directories** - templates, utils, sql_templates, static (if exists)
5. **Copy shared modules** - core/, shared/ if app depends on them
6. **Create credentials directory** - Empty with README
7. **Create .env.example** - Template for environment variables
8. **Create documentation** - README.md and DEPLOYMENT_PACKAGE.md
9. **Create installation scripts** - install.bat and install.sh
10. **Create run scripts** - run_{app}.bat and run_{app}.sh
11. **Create ZIP archive** - Compress everything into timestamped ZIP file

### 3. Files to Include

**Application Files:**
- All `.py` files in the app directory
- `requirements.txt` (if exists)
- `version.py` (if exists)

**Directories:**
- `templates/` - HTML templates
- `static/` - CSS, JS, images (if exists)
- `utils/` - Utility modules (if exists)
- `sql_templates/` - SQL query templates (if exists)
- `data/` - Empty data directories (if needed)

**Shared Modules (if app uses them):**
- `shared/` - Shared utilities and web components
- `core/` - Core configuration and utilities

**Configuration:**
- `.env.example` - Environment variable template
- Documentation files

**Scripts:**
- `install.bat` / `install.sh` - Installation scripts
- `run_{app}.bat` / `run_{app}.sh` - Run scripts

### 4. Files to Exclude

- `__pycache__/` directories
- `.pyc` and `.pyo` files
- `.log` files
- `.tmp` files
- `.git/` directory
- `venv/` or `.venv/` directories
- Credentials files (`.json` in credentials/)
- `.env` files (only `.env.example`)

---

## Packaging Each Application

### LendSight

**Location:** `apps/lendsight/`

**Files to Package:**
```
apps/lendsight/
├── __init__.py
├── app.py
├── analysis.py
├── core.py
├── config.py
├── data_utils.py
├── census_utils.py
├── mortgage_report_builder.py
├── templates/
│   ├── analysis_template.html
│   └── report_template.html
└── sql_templates/
    └── mortgage_report.sql
```

**Shared Dependencies:**
- `shared/web/app_factory.py` - Flask app factory
- `shared/utils/progress_tracker.py` - Progress tracking
- `shared/utils/bigquery_client.py` - BigQuery client (if used)

**Port:** 8082 (check config.py)

**Environment Variables Needed:**
- `GCP_PROJECT_ID` - Google Cloud Project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to BigQuery credentials
- `CENSUS_API_KEY` - US Census Bureau API key (if used)
- `SECRET_KEY` - Flask secret key
- `DEBUG` - Debug mode flag
- `PORT` - Server port (default: 8082)
- `HOST` - Server host (default: 0.0.0.0)

---

### BranchSeeker

**Location:** `apps/branchseeker/`

**Files to Package:**
```
apps/branchseeker/
├── __init__.py
├── app.py
├── analysis.py
├── core.py
├── config.py
├── data_utils.py
├── census_tract_utils.py
├── version.py
├── templates/ (if exists)
└── sql_templates/
    └── branch_report.sql
```

**Shared Dependencies:**
- `shared/web/app_factory.py` - Flask app factory
- `shared/utils/progress_tracker.py` - Progress tracking
- `shared/utils/bigquery_client.py` - BigQuery client (if used)

**Port:** Check config.py (likely 8083 or similar)

**Environment Variables Needed:**
- `GCP_PROJECT_ID` - Google Cloud Project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to BigQuery credentials
- `CENSUS_API_KEY` - US Census Bureau API key (if used)
- `SECRET_KEY` - Flask secret key
- `DEBUG` - Debug mode flag
- `PORT` - Server port
- `HOST` - Server host (default: 0.0.0.0)

---

### BranchMapper

**Location:** `apps/branchmapper/`

**Files to Package:**
```
apps/branchmapper/
├── __init__.py
├── app.py
├── core.py
├── config.py
├── data_utils.py
├── census_tract_utils.py
├── version.py
├── templates/
│   └── branch_mapper_template.html
└── sql_templates/
    └── branch_report.sql
```

**Shared Dependencies:**
- `shared/web/app_factory.py` - Flask app factory
- `shared/utils/bigquery_client.py` - BigQuery client (if used)

**Port:** Check config.py (likely 8084 or similar)

**Environment Variables Needed:**
- `GCP_PROJECT_ID` - Google Cloud Project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to BigQuery credentials
- `CENSUS_API_KEY` - US Census Bureau API key (required for census data)
- `SECRET_KEY` - Flask secret key
- `DEBUG` - Debug mode flag
- `PORT` - Server port
- `HOST` - Server host (default: 0.0.0.0)

---

## Creating Packaging Scripts

### Template Script Structure

Each app should have a `package_{app}.py` script in its directory. Use the BizSight script as a template:

**Key Components:**

1. **Path Setup:**
```python
script_dir = Path(__file__).parent.absolute()
repo_root = script_dir.parent.parent.absolute()
package_dir = repo_root / f'{app}_deployment'
package_zip = repo_root / f'{app}_deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
```

2. **File List:**
```python
files_to_copy = [
    '__init__.py',
    'app.py',
    'core.py',
    'config.py',
    'data_utils.py',
    # ... add all Python files
    'version.py',  # if exists
]
```

3. **Directory Copying:**
```python
# Templates
templates_src = script_dir / 'templates'
if templates_src.exists():
    shutil.copytree(templates_src, templates_dest, dirs_exist_ok=True)

# SQL Templates
sql_templates_src = script_dir / 'sql_templates'
if sql_templates_src.exists():
    shutil.copytree(sql_templates_src, sql_templates_dest, dirs_exist_ok=True)

# Utils (if exists)
utils_src = script_dir / 'utils'
if utils_src.exists():
    shutil.copytree(utils_src, utils_dest, dirs_exist_ok=True)
```

4. **Shared Modules:**
```python
# Copy shared/ directory if app uses it
shared_src = repo_root / 'shared'
if shared_src.exists() and app_uses_shared:
    shared_dest = package_dir / 'shared'
    shutil.copytree(shared_src, shared_dest, dirs_exist_ok=True)
    # Remove __pycache__
    for pycache in shared_dest.rglob('__pycache__'):
        shutil.rmtree(pycache)
```

5. **Environment Template:**
```python
env_example = package_dir / '.env.example'
env_example.write_text("""# {App Name} Configuration
# Copy this file to .env and fill in your values

# Google Cloud Project ID
GCP_PROJECT_ID=hdma1-242116

# BigQuery Credentials
# Place bigquery_service_account.json in credentials/ directory
# Or set GOOGLE_APPLICATION_CREDENTIALS environment variable

# Census API Key (if needed)
CENSUS_API_KEY=your_census_api_key_here

# Flask Configuration
SECRET_KEY=change-this-to-a-random-secret-key-in-production
DEBUG=False
PORT={port_number}
HOST=0.0.0.0
""")
```

6. **Installation Scripts:**
```python
# Windows
install_bat = package_dir / 'install.bat'
install_bat.write_text("""@echo off
echo Installing {App Name} Dependencies...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo Installing Python packages...
pip install --upgrade pip
pip install -r apps\\{app}\\requirements.txt

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env and fill in your API keys
echo 2. Place bigquery_service_account.json in credentials\\ directory
echo 3. Run: python -m apps.{app}.app
echo.
pause
""")

# Linux/macOS
install_sh = package_dir / 'install.sh'
install_sh.write_text("""#!/bin/bash
echo "Installing {App Name} Dependencies..."
echo

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r apps/{app}/requirements.txt

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in your API keys"
echo "2. Place bigquery_service_account.json in credentials/ directory"
echo "3. Run: python3 -m apps.{app}.app"
echo
""")
os.chmod(install_sh, 0o755)
```

7. **Run Scripts:**
```python
# Windows
run_bat = package_dir / f'run_{app}.bat'
run_bat.write_text("""@echo off
cd /d "%~dp0"
echo Starting {App Name}...
echo Access at: http://localhost:{port}
python -m apps.{app}.app
pause
""")

# Linux/macOS
run_sh = package_dir / f'run_{app}.sh'
run_sh.write_text("""#!/bin/bash
cd "$(dirname "$0")"
echo "Starting {App Name}..."
echo "Access at: http://localhost:{port}"
python3 -m apps.{app}.app
""")
os.chmod(run_sh, 0o755)
```

8. **ZIP Creation:**
```python
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
```

---

## Step-by-Step Packaging Process

### For Each Application:

1. **Create the packaging script:**
   - Copy `apps/bizsight/package_bizsight.py` as a template
   - Rename to `package_{app}.py` in the app directory
   - Update all references from "bizsight" to the app name
   - Update file lists to match the app's actual files
   - Update port numbers
   - Update environment variables

2. **Identify dependencies:**
   - Check `app.py` for imports from `shared/` or `core/`
   - List all Python files in the app directory
   - Identify which directories exist (templates, utils, sql_templates, static)

3. **Test the packaging script:**
   ```bash
   python apps/{app}/package_{app}.py
   ```

4. **Verify package contents:**
   - Check that all files are included
   - Verify no credentials or sensitive files are included
   - Test that the package structure is correct

5. **Create deployment documentation:**
   - Copy `apps/bizsight/DEPLOYMENT_PACKAGE.md` as template
   - Update app-specific information
   - Update port numbers
   - Update environment variables
   - Update any app-specific requirements

6. **Test installation:**
   - Extract the ZIP file
   - Run `install.bat` or `install.sh`
   - Verify dependencies install correctly
   - Test running the app

---

## Common Issues and Solutions

### Issue: Missing Shared Modules

**Problem:** App imports from `shared/` but package doesn't include it.

**Solution:** Add shared module copying to packaging script:
```python
shared_src = repo_root / 'shared'
if shared_src.exists():
    shared_dest = package_dir / 'shared'
    shutil.copytree(shared_src, shared_dest, dirs_exist_ok=True)
    # Clean up __pycache__
    for pycache in shared_dest.rglob('__pycache__'):
        shutil.rmtree(pycache)
```

### Issue: Missing Requirements File

**Problem:** App doesn't have `requirements.txt`.

**Solution:** 
1. Create `requirements.txt` in the app directory
2. List all dependencies (check imports in app files)
3. Or use the root `requirements.txt` if shared

### Issue: Static Files Not Included

**Problem:** App has CSS/JS/images but they're not packaged.

**Solution:** Add static directory copying:
```python
static_src = script_dir / 'static'
if static_src.exists():
    static_dest = bizsight_dest / 'static'
    shutil.copytree(static_src, static_dest, dirs_exist_ok=True)
```

### Issue: Port Conflicts

**Problem:** Multiple apps use the same port.

**Solution:** 
1. Check each app's `config.py` for port settings
2. Document the port in deployment docs
3. Make port configurable via `.env` file

---

## Checklist for Each App

Before packaging, verify:

- [ ] All Python source files are listed in `files_to_copy`
- [ ] All directories (templates, utils, sql_templates, static) are copied
- [ ] Shared modules are included if app uses them
- [ ] `requirements.txt` exists or is created
- [ ] `.env.example` includes all necessary variables
- [ ] Port number is correct in scripts and docs
- [ ] Installation scripts work correctly
- [ ] Run scripts use correct module path (`apps.{app}.app`)
- [ ] Documentation is updated with app-specific info
- [ ] ZIP file is created successfully
- [ ] Package can be extracted and installed
- [ ] No credentials or sensitive files are included

---

## Next Steps

1. **Create packaging scripts** for each app:
   - `apps/lendsight/package_lendsight.py`
   - `apps/branchseeker/package_branchseeker.py`
   - `apps/branchmapper/package_branchmapper.py`

2. **Create deployment documentation** for each app:
   - `apps/lendsight/DEPLOYMENT_PACKAGE.md`
   - `apps/branchseeker/DEPLOYMENT_PACKAGE.md`
   - `apps/branchmapper/DEPLOYMENT_PACKAGE.md`

3. **Test packaging** for each app

4. **Create packages** and verify they work

---

## Reference Files

- **BizSight Packaging Script:** `apps/bizsight/package_bizsight.py`
- **BizSight Deployment Docs:** `apps/bizsight/DEPLOYMENT_PACKAGE.md`
- **BizSight Packaging Instructions:** `apps/bizsight/PACKAGING_INSTRUCTIONS.md`

Use these as templates for the other applications.

