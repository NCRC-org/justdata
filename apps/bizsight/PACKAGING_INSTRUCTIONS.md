# BizSight Packaging Instructions

## Quick Packaging Guide

To create a deployment package for BizSight:

### Step 1: Run the Packaging Script

From the `#JustData_Repo` directory:
```bash
python apps/bizsight/package_bizsight.py
```

This will create:
- `bizsight_deployment/` - Directory with all files
- `bizsight_deployment_YYYYMMDD_HHMMSS.zip` - ZIP archive

### Step 2: Verify Package Contents

The package should include:
- ✅ All Python source files (`app.py`, `core.py`, `config.py`, etc.)
- ✅ `templates/` directory with HTML templates
- ✅ `utils/` directory with utility modules
- ✅ `requirements.txt` with all dependencies
- ✅ `DEPLOYMENT_PACKAGE.md` documentation
- ✅ `.env.example` configuration template
- ✅ Installation scripts (`install.bat`, `install.sh`)
- ✅ Run scripts (`run_bizsight.bat`, `run_bizsight.sh`)
- ✅ `README.md` quick start guide

### Step 3: Manual Additions (Not Included in Package)

**IMPORTANT**: The following are NOT included and must be provided separately:

1. **BigQuery Credentials**
   - File: `bigquery_service_account.json`
   - Instructions: Place in `credentials/` directory
   - **DO NOT** include in package (security risk)

2. **Environment Variables**
   - File: `.env` (created from `.env.example`)
   - Contains: API keys, project IDs, etc.
   - **DO NOT** include in package (security risk)

3. **Python Virtual Environment**
   - Not included (too large, platform-specific)
   - Recipient will create their own

### Step 4: Pre-Deployment Checklist

Before handing off the package:

- [ ] Package created successfully
- [ ] All files included (check `bizsight_deployment/` directory)
- [ ] Documentation reviewed (`DEPLOYMENT_PACKAGE.md`)
- [ ] `.env.example` is complete and accurate
- [ ] Installation scripts tested (if possible)
- [ ] ZIP file created and verified
- [ ] **Credentials and API keys NOT included** (security check)

### Step 5: Handoff Instructions

Provide the recipient with:

1. **The ZIP file**: `bizsight_deployment_YYYYMMDD_HHMMSS.zip`

2. **Separate secure delivery** of:
   - BigQuery service account JSON file
   - API keys (Claude/OpenAI) - via secure channel

3. **Instructions to**:
   - Extract the ZIP file
   - Read `README.md` for quick start
   - Read `DEPLOYMENT_PACKAGE.md` for full instructions
   - Run installation scripts
   - Set up credentials and `.env` file

## Package Contents Summary

### Application Files
```
apps/bizsight/
├── __init__.py
├── app.py
├── core.py
├── config.py
├── data_utils.py
├── report_builder.py
├── ai_analysis.py
├── excel_export.py
├── requirements.txt
├── templates/
│   ├── analysis_template.html
│   └── report_template.html
├── utils/
│   ├── __init__.py
│   ├── bigquery_client.py
│   ├── progress_tracker.py
│   ├── ai_provider.py
│   └── tract_boundaries.py
└── data/
    └── reports/  (empty, created on first run)
```

### Shared Modules
```
core/config/
└── app_config.py  (if needed)
```

### Documentation & Scripts
- `DEPLOYMENT_PACKAGE.md` - Complete deployment guide
- `README.md` - Quick start guide
- `.env.example` - Environment variable template
- `install.bat` / `install.sh` - Installation scripts
- `run_bizsight.bat` / `run_bizsight.sh` - Run scripts

## Dependencies

All dependencies are listed in `requirements.txt`:
- flask>=2.3.0
- python-dotenv>=1.0.0
- pandas>=1.5.0
- numpy>=1.21.0
- google-cloud-bigquery>=3.0.0
- anthropic>=0.7.0 (for Claude)
- openai>=1.0.0 (for OpenAI)
- openpyxl>=3.0.0
- playwright>=1.40.0
- reportlab>=4.0.0
- Pillow>=10.0.0
- requests>=2.31.0
- user-agents>=2.2.0

## Required Credentials (Provide Separately)

1. **BigQuery Service Account JSON**
   - Location: `credentials/bigquery_service_account.json`
   - Permissions: BigQuery Data Viewer, Job User

2. **AI API Key** (one of):
   - `CLAUDE_API_KEY` - For Claude/Anthropic
   - `OPENAI_API_KEY` - For OpenAI

3. **Google Cloud Project ID**
   - Default: `hdma1-242116`
   - Can be changed in `.env` file

## Testing the Package

Before deployment, test the package:

1. Extract to a temporary location
2. Create virtual environment
3. Run `install.bat` or `install.sh`
4. Set up `.env` file with test credentials
5. Run `python -m apps.bizsight.app`
6. Verify application starts and can connect to BigQuery

## Troubleshooting Packaging Issues

### Import Errors in Package
- Ensure all files are copied (check `package_bizsight.py` file list)
- Verify `__init__.py` files exist in all directories

### Missing Files
- Check that source files exist before packaging
- Verify directory structure matches expected layout

### ZIP File Too Large
- Exclude `__pycache__` directories (already excluded)
- Exclude `.git` directories
- Exclude virtual environments
- Exclude test files

## Security Notes

⚠️ **CRITICAL**: Never include in the package:
- `.env` files with real API keys
- `bigquery_service_account.json` credentials
- Any files containing secrets or passwords
- `.git` directories (may contain history with secrets)

✅ **Safe to include**:
- `.env.example` (template only)
- Source code
- Documentation
- Requirements files

