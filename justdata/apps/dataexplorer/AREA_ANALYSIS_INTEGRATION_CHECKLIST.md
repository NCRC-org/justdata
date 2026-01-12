# Area Analysis Integration Checklist

## Pre-Commit Checklist

This document outlines what has been fixed and what needs to be verified before committing the area analysis feature.

---

## ✅ Fixed Issues

### 1. Loan Purpose Mapping (FIXED)
- **Issue**: Loan purpose codes were incorrectly mapped (`'refinance' -> '2'` instead of `['31', '32']`)
- **Fix**: Updated `parse_wizard_parameters()` to correctly convert wizard format to LendSight format:
  - `'home-purchase'` → `'purchase'`
  - `'refinance'` → `'refinance'` (SQL query handles codes 31/32 internally)
  - `'home-equity'` → `'equity'` (SQL query handles codes 2/4 internally)
- **Location**: `apps/dataexplorer/core.py` lines 66-86

### 2. Years Parsing (FIXED)
- **Issue**: Years were hardcoded to 2020-2024
- **Fix**: Now checks for years in wizard data, falls back to 2020-2024 if not provided
- **Location**: `apps/dataexplorer/core.py` lines 41-48

### 3. Construction and Loan Type Filters (FIXED)
- **Issue**: Filters were parsed but not applied to `query_filters`
- **Fix**: Now properly added to `query_filters` dictionary
- **Location**: `apps/dataexplorer/core.py` lines 88-99

### 4. Total Units Filter (FIXED)
- **Issue**: Was using `property_type` key, but SQL expects `total_units`
- **Fix**: Changed to use `total_units` key and fixed the query call
- **Location**: `apps/dataexplorer/core.py` lines 89-94, 310

### 5. Loan Purpose Conversion Duplication (FIXED)
- **Issue**: Loan purpose was being converted twice (once in `parse_wizard_parameters`, once in `run_area_analysis`)
- **Fix**: Removed duplicate conversion in `run_area_analysis`, now uses `query_filters['loan_purpose']` directly
- **Location**: `apps/dataexplorer/core.py` lines 268-281

---

## 🔍 Verification Needed

### 1. End-to-End Flow Test
- [ ] Test wizard selection → area analysis → report display
- [ ] Verify all user selections are correctly passed through
- [ ] Check that report displays with correct filters applied

### 2. Filter Application Test
- [ ] Test with different loan purposes (home-purchase, refinance, home-equity)
- [ ] Test with different occupancy types (owner-occupied, second-home, investor)
- [ ] Test with different total units (1-4, 5+)
- [ ] Test with construction types (site-built, manufactured)
- [ ] Test with loan types (conventional, FHA, VA, RHS)
- [ ] Test with action taken (originations vs applications)
- [ ] Test with reverse mortgage exclusion

### 3. Report Route Verification
- [ ] Verify `/report/<job_id>` route works correctly
- [ ] Check that progress tracking works (SSE endpoint)
- [ ] Verify error handling for missing/invalid job IDs

### 4. Data Flow Verification
- [ ] Verify wizard data structure matches expected format
- [ ] Check that `parse_wizard_parameters()` correctly extracts all fields
- [ ] Verify `run_area_analysis()` receives correct parameters
- [ ] Check that SQL queries use correct filter values

---

## 📋 Integration Points

### Wizard → Backend
1. **Wizard sends data to**: `POST /api/generate-area-report`
2. **Data structure**: See `DATAEXPLORER_WIZARD_DATA_STRUCTURE.md`
3. **Response**: `{ success: true, report_id: "<job_id>" }`

### Backend → Report Display
1. **Report route**: `GET /report/<job_id>`
2. **Progress tracking**: `GET /progress/<job_id>` (Server-Sent Events)
3. **Report template**: `templates/area_report_template.html`

### Data Processing Flow
1. `app.py` → `generate_area_report()` → receives wizard data
2. `core.py` → `run_area_analysis()` → parses parameters
3. `core.py` → `parse_wizard_parameters()` → converts wizard format to query format
4. `data_utils.py` → `execute_mortgage_query_with_filters()` → applies filters to SQL
5. `area_report_builder.py` → `build_area_report()` → generates report tables
6. `app.py` → `show_report()` → renders report template

---

## 🚨 Known Issues / Limitations

1. **Years**: ✅ **FIXED** - Now defaults to the most recent 5 years (dynamic based on current year) if not provided in wizard data. Wizard may not send years yet.
2. **Total Units 5+**: ✅ **FIXED** - Now uses `NOT IN ('1','2','3','4')` to handle anything that's not 1-4 as 5+ units
3. **Loan Type Filter**: May need to be added to SQL template if not already present
4. **Construction Filter**: May need to be added to SQL template if not already present

---

## 📝 Next Steps

1. **Test the integration** with the actual wizard
2. **Verify all filters work** as expected
3. **Check for any missing error handling**
4. **Update documentation** if needed
5. **Commit and push** once verified

---

## 🔗 Related Files

- `apps/dataexplorer/app.py` - Flask routes and endpoints
- `apps/dataexplorer/core.py` - Main analysis logic and parameter parsing
- `apps/dataexplorer/data_utils.py` - SQL query execution with filters
- `apps/dataexplorer/area_report_builder.py` - Report table generation
- `apps/dataexplorer/templates/area_report_template.html` - Report display
- `apps/dataexplorer/static/js/api-client.js` - Wizard API client
- `apps/dataexplorer/static/js/wizard-steps.js` - Wizard step handlers

