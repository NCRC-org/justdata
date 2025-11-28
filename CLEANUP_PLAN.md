# JustData Cleanup Plan

## Files to Remove

### 1. Duplicate/Unnecessary Files
- `env.template` - Keep `env.example` instead
- `copy_credentials.py` - No longer needed
- `Untitled-1` - Temporary file
- `justdata/apps/branchseeker/map_test.html` - Duplicate (keep `justdata/shared/web/static/map_test.html`)

### 2. Test Files (Move to tests/ or remove)
- `justdata/apps/lendsight/test_*.py` - Move to `tests/apps/lendsight/` or remove if not needed

### 3. Documentation Consolidation
Keep these in root:
- `README.md` - Main documentation
- `DEPLOYMENT_GUIDE.md` - Full deployment guide
- `DEPLOYMENT_SUMMARY.md` - Quick deployment reference
- `QUICK_DEPLOYMENT_CHECKLIST.md` - Deployment checklist

Move to `docs/`:
- `BRANCH_SWITCHING_GUIDE.md`
- `LIVE_DEVELOPMENT_GUIDE.md`
- `MAP_TESTING_GUIDE.md`
- `REPORT_SECTIONS_REFERENCE.md`
- `GIT_FOR_JAY.md.txt`

Move to `justdata/apps/branchseeker/docs/`:
- `CENSUS_TRACT_LAYERS_STRATEGY.md`
- `MAP_TEST_README.md`
- `UX_REVIEW_AND_RECOMMENDATIONS.md`
- `SERVICE_TYPE_DEFINITIONS.md`

## Standardization

### Application Names
- ✅ **LendSight** (already standardized)
- ✅ **BranchSeeker** (already standardized)
- ✅ **BranchMapper** (already standardized)
- ✅ **MergerMeter** (already standardized)

### File Structure
```
justdata/
├── apps/
│   ├── lendsight/          # LendSight application
│   ├── branchseeker/       # BranchSeeker application
│   ├── mergermeter/        # MergerMeter application
│   └── bizsight/           # BizSight application
├── shared/                 # Shared utilities
│   ├── web/               # Shared web templates/static
│   ├── reporting/         # Shared reporting utilities
│   └── utils/             # Shared utilities
└── core/                  # Core platform code
```

## Config Files

### Keep:
- `env.example` - Template for environment variables
- `justdata/core/config/app_config.py` - Core configuration
- `justdata/apps/branchseeker/config.py` - BranchSeeker config
- `justdata/apps/lendsight/config.py` - LendSight config

### Review:
- Check for duplicate configuration logic
- Consolidate common settings

## Cleanup Commands

```bash
# Remove duplicate/unnecessary files
rm -f env.template
rm -f copy_credentials.py
rm -f Untitled-1
rm -f justdata/apps/branchseeker/map_test.html

# Create docs directories
mkdir -p docs
mkdir -p justdata/apps/branchseeker/docs

# Move documentation
mv BRANCH_SWITCHING_GUIDE.md docs/
mv LIVE_DEVELOPMENT_GUIDE.md docs/
mv MAP_TESTING_GUIDE.md docs/
mv REPORT_SECTIONS_REFERENCE.md docs/
mv GIT_FOR_JAY.md.txt docs/

mv justdata/apps/branchseeker/CENSUS_TRACT_LAYERS_STRATEGY.md justdata/apps/branchseeker/docs/
mv justdata/apps/branchseeker/MAP_TEST_README.md justdata/apps/branchseeker/docs/
mv justdata/apps/branchseeker/UX_REVIEW_AND_RECOMMENDATIONS.md justdata/apps/branchseeker/docs/
mv justdata/apps/branchseeker/SERVICE_TYPE_DEFINITIONS.md justdata/apps/branchseeker/docs/

# Move test files (optional - review first)
# mv justdata/apps/lendsight/test_*.py tests/apps/lendsight/
```

## After Cleanup

1. Update `.gitignore` to ensure:
   - `.env` is ignored
   - `__pycache__/` is ignored
   - `*.pyc` is ignored
   - `data/reports/` is ignored

2. Update `README.md` with:
   - Clear application structure
   - Standardized names
   - Deployment instructions

3. Verify all imports still work after file moves

