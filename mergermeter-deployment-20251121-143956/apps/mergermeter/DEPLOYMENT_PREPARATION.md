# MergerMeter Deployment Package Preparation

This document outlines all modifications needed to create a clean, deployable ZIP package of MergerMeter for web deployment.

---

## 🔴 CRITICAL MODIFICATIONS REQUIRED

### 1. **Remove Hard-Coded Paths**

#### File: `apps/mergermeter/config.py`
**Current Issue (Line 32):**
```python
absolute_merger_path = Path(r'C:\DREAM\1_Merger_Report')
```

**Fix Required:**
- Remove this hard-coded path completely
- The `MERGER_REPORT_BASE` logic should only check:
  1. Environment variable `MERGER_REPORT_BASE`
  2. Relative path from workspace root
  3. Set to `None` if not found (which is fine since we don't use it anymore)

**Modified Code:**
```python
# Excel template file path (for matching original merger report format)
# Support multiple path options for flexibility across different environments
# 1. Check environment variable first (for CI/CD, Docker, etc.)
MERGER_REPORT_BASE_ENV = os.getenv('MERGER_REPORT_BASE')
if MERGER_REPORT_BASE_ENV:
    MERGER_REPORT_BASE = Path(MERGER_REPORT_BASE_ENV)
else:
    # 2. Try relative path from workspace root (for GitHub/main branch)
    workspace_root = JUSTDATA_BASE.parent if JUSTDATA_BASE.name == '#JustData_Repo' else JUSTDATA_BASE.parent.parent
    relative_merger_path = workspace_root / '1_Merger_Report'
    
    # Use relative path if it exists, otherwise None (we don't need it)
    if relative_merger_path.exists():
        MERGER_REPORT_BASE = relative_merger_path
    else:
        MERGER_REPORT_BASE = None
```

#### Files: `apps/mergermeter/debug_pnc_pdf.py` and `apps/mergermeter/parse_pnc_pdf.py`
**Current Issue:**
- Hard-coded OneDrive paths with apostrophes
- These are debug/utility scripts, not needed for deployment

**Fix Required:**
- **EXCLUDE** these files from deployment package (they're for local debugging only)

#### File: `shared/utils/bigquery_client.py`
**Current Issue (Lines 42-48):**
```python
possible_paths = [
    Path("C:/DREAM/config/credentials/hdma1-242116-74024e2eb88f.json"),
    Path("C:/DREAM/config/credentials/hdma1-242116-74024e2eb88f_20251102_180816.json"),
    Path("C:/DREAM/hdma1-242116-74024e2eb88f.json"),
    ...
]
```

**Fix Required:**
- Remove all `C:/DREAM/` hard-coded paths
- Keep only:
  - Environment variable path
  - Relative paths from project root
  - Standard credential locations

**Modified Code:**
```python
possible_paths = [
    Path("config/credentials/hdma1-242116-74024e2eb88f.json"),
    Path("hdma1-242116-74024e2eb88f.json"),
    Path(__file__).parent.parent.parent / "config" / "credentials" / "hdma1-242116-74024e2eb88f.json",
    Path(__file__).parent.parent.parent.parent / "config" / "credentials" / "hdma1-242116-74024e2eb88f.json",
]
```

---

## 📦 FILES TO INCLUDE IN DEPLOYMENT PACKAGE

### Core Application Files
```
apps/mergermeter/
├── __init__.py
├── app.py
├── config.py (AFTER removing hard-coded paths)
├── excel_generator.py
├── query_builders.py
├── hhi_calculator.py
├── branch_assessment_area_generator.py
├── county_mapper.py
├── version.py
├── templates/
│   ├── analysis_template.html
│   └── report_template.html
├── static/
│   ├── css/
│   └── js/
└── output/ (directory - will be created automatically)
```

### Entry Point
```
run_mergermeter.py (in root)
```

### Required Shared Dependencies
```
shared/
├── __init__.py
├── web/
│   ├── __init__.py
│   ├── app_factory.py
│   └── static/
│       ├── css/
│       │   └── style.css
│       ├── img/
│       │   └── ncrc-logo.png
│       └── js/
│           └── app.js
└── utils/
    ├── __init__.py
    ├── bigquery_client.py (AFTER removing hard-coded paths)
    └── progress_tracker.py
└── analysis/
    ├── __init__.py
    └── ai_provider.py (optional - for AI features)
```

### Documentation Files
```
apps/mergermeter/
├── README.md
├── ASSESSMENT_AREA_FORMAT.md
├── HHI_CALCULATION_GUIDE.md
├── BIGQUERY_DATASETS.md (BigQuery dataset documentation)
└── DEPLOYMENT_PREPARATION.md (this file)
```

### Configuration Files
```
requirements.txt (MergerMeter-specific, see below)
apps/mergermeter/.env.example (template for environment variables - COPY TO ROOT AS .env)
apps/mergermeter/setup_config.py (interactive setup script)
apps/mergermeter/check_config.py (configuration validation script)
```

**Configuration Setup:**
- `.env.example` - Template with all required and optional variables
- `setup_config.py` - Interactive script that prompts user for all configuration values
- `check_config.py` - Validates configuration before running the app
- `run_mergermeter.py` - Automatically checks config on startup and prompts if missing

**IMPORTANT NOTES:**
- `.env.example` is a TEMPLATE - users must copy it to `.env` and fill in actual values
- **NEVER include actual API keys or credentials** in the deployment package
- The `.env` file should be in the root directory (same level as `run_mergermeter.py`)
- Users must provide their own BigQuery credentials JSON file

---

## 🚫 FILES TO EXCLUDE FROM DEPLOYMENT PACKAGE

### Debug/Development Files
- `apps/mergermeter/debug_pnc_pdf.py` - Debug script with hard-coded paths
- `apps/mergermeter/parse_pnc_pdf.py` - Utility script with hard-coded paths
- `apps/mergermeter/template_populator.py` - Not used (legacy)
- `apps/mergermeter/template_populator_fixes.py` - Not used (legacy)
- `apps/mergermeter/excel_postprocessor.py` - Not used (legacy)
- `apps/mergermeter/statistical_analysis.py` - Not used (legacy)

### Documentation/History Files (Optional - can include if desired)
- `apps/mergermeter/CODE_REVIEW_FIXES.md` - Development notes
- `apps/mergermeter/MIGRATION_TO_JASONEDITS.md` - Migration notes
- `apps/mergermeter/CURRENT_STATUS_REPORT.md` - Status report

### Output Directory
- `apps/mergermeter/output/` - Should be empty or excluded (user will generate their own)

---

## 📝 CONFIGURATION FILES TO CREATE

### 1. `requirements.txt` (MergerMeter-Specific)

Create a standalone `requirements.txt` in the deployment package root:

```txt
# MergerMeter Dependencies
# Python 3.8 or higher required

# Web Framework
flask>=2.3.0

# Data Processing
pandas>=1.5.0
numpy>=1.21.0

# BigQuery
google-cloud-bigquery>=3.0.0

# Excel Generation
openpyxl>=3.0.0

# Environment Variables
python-dotenv>=1.0.0

# Optional - AI Features
anthropic>=0.7.0  # For Claude AI features (optional)
```

### 2. `.env.example`

**File Created:** `apps/mergermeter/.env.example`

This file is already created with all required and optional environment variables. It includes:
- Required BigQuery configuration (GCP_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS)
- Optional server configuration (PORT, SECRET_KEY)
- Optional AI features (AI_PROVIDER, CLAUDE_API_KEY, OPENAI_API_KEY)
- Advanced configuration (DEBUG, LOG_LEVEL, MAX_CONTENT_LENGTH)

**IMPORTANT:** This is a TEMPLATE file with placeholder values. Users must:
1. Copy `.env.example` to `.env` in the root directory
2. Fill in their actual credentials
3. Never commit the `.env` file with real credentials

### 3. `DEPLOYMENT_README.md`

Create a deployment guide:

```markdown
# MergerMeter Deployment Guide

## Quick Start

1. Extract the ZIP file
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure
4. Run: `python run_mergermeter.py`
5. Access: http://127.0.0.1:8083

## Configuration

See `.env.example` for required environment variables.

## BigQuery Setup

1. Create a GCP project
2. Enable BigQuery API
3. Create a service account with BigQuery access
4. Download credentials JSON
5. Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env`

## Full Documentation

See `apps/mergermeter/README.md` for complete documentation.
```

---

## 🔧 ADDITIONAL MODIFICATIONS

### 1. **Update `config.py` to Remove MERGER_REPORT_BASE Logic**

Since MergerMeter is completely standalone, we can simplify `config.py`:

```python
# Remove all MERGER_REPORT_BASE logic - we don't need it
# Template files - NO LONGER USED (we use simplified format only)
TEMPLATE_FILE = None
CLEAN_TEMPLATE_FILE = None
```

### 2. **Verify All Imports Are Relative or from `shared`**

Check that all imports in MergerMeter files use:
- Relative imports: `from .config import ...`
- Shared imports: `from shared.utils.bigquery_client import ...`
- Standard library imports: `from flask import ...`

No absolute paths or hard-coded module paths.

### 3. **Create `__init__.py` Files**

Ensure all package directories have `__init__.py`:
- `apps/__init__.py`
- `apps/mergermeter/__init__.py`
- `shared/__init__.py`
- `shared/web/__init__.py`
- `shared/utils/__init__.py`
- `shared/analysis/__init__.py`

---

## 📋 DEPLOYMENT PACKAGE STRUCTURE

The final ZIP should have this structure:

```
mergermeter-deployment/
├── apps/
│   └── mergermeter/
│       ├── __init__.py
│       ├── app.py
│       ├── config.py
│       ├── excel_generator.py
│       ├── query_builders.py
│       ├── hhi_calculator.py
│       ├── branch_assessment_area_generator.py
│       ├── county_mapper.py
│       ├── version.py
│       ├── README.md
│       ├── ASSESSMENT_AREA_FORMAT.md
│       ├── HHI_CALCULATION_GUIDE.md
│       ├── templates/
│       │   ├── analysis_template.html
│       │   └── report_template.html
│       └── static/
│           ├── css/
│           └── js/
├── shared/
│   ├── __init__.py
│   ├── web/
│   │   ├── __init__.py
│   │   ├── app_factory.py
│   │   └── static/
│   │       ├── css/
│   │       ├── img/
│   │       └── js/
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── bigquery_client.py
│   │   └── progress_tracker.py
│   └── analysis/
│       ├── __init__.py
│       └── ai_provider.py
├── run_mergermeter.py (checks config on startup, prompts if missing)
├── requirements.txt
├── apps/
│   └── mergermeter/
│       ├── .env.example (template - user copies to root as .env)
│       ├── setup_config.py (interactive setup script - prompts for all values)
│       ├── check_config.py (config validation script)
│       └── BIGQUERY_DATASETS.md (BigQuery dataset documentation)
└── DEPLOYMENT_README.md
```

---

## ✅ CHECKLIST BEFORE CREATING ZIP

### Code Modifications
- [ ] Remove all hard-coded `C:\DREAM\` paths from `config.py`
- [ ] Remove all hard-coded `C:\DREAM\` paths from `shared/utils/bigquery_client.py`
- [ ] Remove hard-coded OneDrive paths from debug files (or exclude them)

### Configuration Files
- [x] Create `.env.example` template in `apps/mergermeter/` (already created)
- [x] Create `setup_config.py` interactive setup script (already created)
- [x] Create `check_config.py` config validation script (already created)
- [x] Update `run_mergermeter.py` to check config on startup (already updated)
- [ ] Create standalone `requirements.txt` with only MergerMeter dependencies
- [ ] Create `DEPLOYMENT_README.md` with setup instructions

### Documentation
- [x] Create `BIGQUERY_DATASETS.md` documenting all datasets (already created)
- [ ] Document that users can run `setup_config.py` or manually create `.env` from `.env.example`

### File Cleanup
- [ ] Verify all `__init__.py` files exist in package directories
- [ ] Remove or exclude debug/utility files (debug_pnc_pdf.py, parse_pnc_pdf.py, etc.)
- [ ] Remove or exclude legacy files (template_populator.py, etc.)
- [ ] Verify `output/` directory is empty or excluded

### Testing
- [ ] Test that the app runs with only the files in the deployment structure
- [ ] Verify all imports work without external dependencies
- [ ] Check that no files reference `1_Merger_Report` or other external projects
- [ ] Test `setup_config.py` creates valid `.env` file
- [ ] Test `check_config.py` validates configuration correctly
- [ ] Test `run_mergermeter.py` prompts for missing config

---

## 🧪 TESTING THE DEPLOYMENT PACKAGE

After creating the ZIP, test it on a clean system:

1. Extract to a new directory
2. Create a virtual environment: `python -m venv venv`
3. Activate virtual environment
4. Install dependencies: `pip install -r requirements.txt`
5. Set up `.env` file with test credentials
6. Run: `python run_mergermeter.py`
7. Verify the app starts without errors
8. Test a simple analysis to ensure all functionality works

---

## 📌 NOTES

- The deployment package should be **completely standalone**
- No references to `1_Merger_Report` or other external projects
- All paths should be relative or environment-based
- BigQuery credentials should be provided by the user via `.env`
- The package should work on Windows, Linux, and macOS
- Python 3.8+ is required

---

**Last Updated:** Based on current codebase review
**Status:** Ready for modifications

