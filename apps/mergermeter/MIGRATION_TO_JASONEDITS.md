# MergerMeter Migration to JasonEdits Branch

This document outlines what needs to be done to move MergerMeter to the JasonEdits branch for GitHub.

## What Has Been Fixed

✅ **Hard-coded paths removed** - `config.py` now uses environment variables and relative paths
✅ **External dependencies handled gracefully** - `excel_generator.py` falls back if templates aren't available
✅ **README created** - Complete setup and troubleshooting guide
✅ **GitHub-compatible** - Works without external merger report files

## Files That Need to Be Committed to JasonEdits Branch

### Core MergerMeter Files
```
apps/mergermeter/
├── __init__.py
├── app.py
├── config.py (FIXED - no hard-coded paths)
├── excel_generator.py (FIXED - graceful fallback)
├── query_builders.py
├── hhi_calculator.py
├── branch_assessment_area_generator.py
├── county_mapper.py
├── README.md (NEW - setup guide)
├── ASSESSMENT_AREA_FORMAT.md
├── CODE_REVIEW_FIXES.md
├── HHI_CALCULATION_GUIDE.md
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
run_mergermeter.py (in #JustData_Repo root)
```

### Required Shared Dependencies (must be in repo)
```
shared/
├── web/
│   ├── app_factory.py
│   └── static/ (CSS, JS, images)
└── utils/
    ├── bigquery_client.py
    ├── progress_tracker.py
    └── __init__.py
```

### Configuration Files
```
requirements.txt (in #JustData_Repo root - should include all dependencies)
.env.example (optional - template for environment variables)
```

## Git Commands to Move to JasonEdits Branch

### Step 1: Check Current Branch
```bash
cd "#JustData_Repo"
git status
```

### Step 2: Switch to JasonEdits Branch (if not already on it)
```bash
git checkout JasonEdits
```

If the branch doesn't exist locally:
```bash
git fetch
git checkout -b JasonEdits origin/JasonEdits
```

### Step 3: Stage All MergerMeter Changes
```bash
# Add all mergermeter files
git add apps/mergermeter/
git add run_mergermeter.py

# Add any shared dependencies if they were modified
git add shared/

# Add requirements.txt if it was updated
git add requirements.txt
```

### Step 4: Commit the Changes
```bash
git commit -m "Fix MergerMeter for GitHub merge - remove hard-coded paths, add graceful fallbacks, add README"
```

### Step 5: Push to JasonEdits Branch
```bash
git push origin JasonEdits
```

## Verification Checklist

Before pushing, verify:

- [ ] All hard-coded paths removed from `config.py`
- [ ] `excel_generator.py` handles missing templates gracefully
- [ ] `shared/` directory exists with required modules
- [ ] `requirements.txt` includes all dependencies
- [ ] `README.md` exists in `apps/mergermeter/`
- [ ] `run_mergermeter.py` exists in root
- [ ] No references to `C:\DREAM\` paths (except as fallback)
- [ ] Environment variables are used where appropriate

## Testing After Migration

1. **Clone fresh from JasonEdits branch:**
   ```bash
   git clone <repo-url>
   cd <repo-name>
   git checkout JasonEdits
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables:**
   ```bash
   # Create .env file
   GCP_PROJECT_ID=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   ```

4. **Run MergerMeter:**
   ```bash
   python run_mergermeter.py
   ```

5. **Verify it works:**
   - Server starts without errors
   - Web interface loads at http://127.0.0.1:8083
   - Can submit a test analysis
   - Excel report generates successfully

## Key Changes Made for GitHub Compatibility

### 1. config.py
- **Before:** Hard-coded `C:\DREAM\1_Merger_Report` path
- **After:** Checks environment variable → relative path → absolute path (fallback)
- **Result:** Works in any environment

### 2. excel_generator.py
- **Before:** Required external merger report utilities
- **After:** Tries to import, falls back gracefully if not available
- **Result:** Works with or without external templates

### 3. README.md
- **New:** Complete setup guide
- **Includes:** Installation, configuration, troubleshooting
- **Result:** Clear instructions for new users

## Environment Variables Reference

```bash
# Required
GCP_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Optional (for enhanced template support)
MERGER_REPORT_BASE=/path/to/1_Merger_Report

# Optional (for AI features)
AI_PROVIDER=claude
CLAUDE_API_KEY=your-key
```

## Next Steps

1. Review the changes in this document
2. Run the git commands above to commit to JasonEdits
3. Test in a fresh clone to verify everything works
4. Create a pull request from JasonEdits to main when ready

## Support

If you encounter issues:
1. Check `apps/mergermeter/README.md` for troubleshooting
2. Verify all shared dependencies are present
3. Check that environment variables are set correctly
4. Review `CODE_REVIEW_FIXES.md` for known issues

