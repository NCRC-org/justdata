# DataExplorer Development Workflow

## Problem: Changes Not Appearing

We've repeatedly encountered issues where code changes don't appear because of:
1. Flask template/static file caching
2. Browser caching
3. Server not reloading properly
4. Code changes not being saved/committed
5. Code duplication leading to inconsistent fixes

## Solution: Systematic Development Workflow

### Core Principles

1. **Always Verify**: Run verification script after changes
2. **Use Shared Utilities**: Don't duplicate code - use shared patterns
3. **Test Immediately**: Verify changes work before moving on
4. **Document Patterns**: Record what works for future reference

## Verification Workflow

### Step 1: Make Code Changes
- Edit files as needed
- Save all files (Ctrl+S or Cmd+S)

### Step 2: Verify Changes Are Saved
```bash
python apps/dataexplorer/verify_changes.py
```

This script checks:
- ✓ Code changes are present in files
- ✓ Server is running
- ✓ Cache-busting headers are active
- ✓ API endpoints are working

### Step 3: If Server Needs Restart
```bash
# Kill existing server (if needed)
taskkill /F /FI "WINDOWTITLE eq *dataexplorer*" 2>nul

# Start server
python run_dataexplorer.py
```

### Step 4: Hard Refresh Browser
- **Windows/Linux**: `Ctrl + Shift + R` or `Ctrl + F5`
- **Mac**: `Cmd + Shift + R`
- **Or**: Open DevTools (F12) → Network tab → Check "Disable cache"

## Best Practices

### 1. Always Verify After Changes
Run `verify_changes.py` after making changes to catch issues immediately.

### 2. Use Shared Patterns
When fixing similar issues across reports (HMDA, SB, Branches):
- Check how it's done in working reports first
- Create shared utility functions instead of duplicating code
- Document the pattern in this file

### 3. Cache-Busting Protocol
All Flask apps should have:
- `app.jinja_env.bytecode_cache = None`
- `TEMPLATES_AUTO_RELOAD = True`
- `SEND_FILE_MAX_AGE_DEFAULT = 0`
- Cache-busting headers on all responses
- `add_cache_busting_headers()` helper function

### 4. Test Immediately
After making changes:
1. Run verification script
2. Test in browser (hard refresh)
3. Check console for errors
4. Verify data is correct

### 5. Document Working Patterns
When you find a solution that works, document it:
- Add to this file
- Create shared utilities
- Update similar code to use the same pattern

## Common Issues & Solutions

### Issue: Changes Not Appearing
**Solution**: 
1. Run `verify_changes.py`
2. Restart server if needed
3. Hard refresh browser
4. Check browser console for errors

### Issue: Census Tract Data Missing
**Solution**: 
- Use `geo.census` table join (like mortgage/SB reports)
- Include `tract_minority_population_percent` in query
- Use `income_level` field from census table (1=low, 2=moderate, 3=middle, 4=upper)

### Issue: Data in Wrong Format
**Solution**:
- Check if data is in thousands (multiply by 1000) or full dollars
- Verify query transformations match expected format
- Check how other reports handle the same data type

### Issue: Table Not Rendering
**Solution**:
- Check JavaScript conditions (remove `dataType !== 'branches'` if needed)
- Verify data structure matches what frontend expects
- Check console logs for rendering errors

## Shared Code Patterns

### Census Tract Data (All Reports)
```python
# Query pattern:
LEFT JOIN `{project_id}.geo.census` c
    ON LPAD(CAST(b.geoid5 AS STRING), 5, '0') = SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 1, 5)
    AND LPAD(CAST(b.census_tract AS STRING), 6, '0') = SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 6, 6)

# Income flags:
CASE WHEN c.income_level = 1 THEN 1 ELSE 0 END as is_low_income_tract
CASE WHEN c.income_level = 2 THEN 1 ELSE 0 END as is_moderate_income_tract
CASE WHEN c.income_level = 3 THEN 1 ELSE 0 END as is_middle_income_tract
CASE WHEN c.income_level = 4 THEN 1 ELSE 0 END as is_upper_income_tract

# Minority percentage:
SAFE_DIVIDE(
    COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
    NULLIF(COALESCE(c.total_persons, 0), 0)
) * 100 as tract_minority_population_percent
```

### Cache-Busting Headers (All Flask Apps)
```python
def add_cache_busting_headers(response):
    """Add aggressive cache-busting headers to a Flask response."""
    import time
    timestamp = int(time.time())
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['ETag'] = f'"{timestamp}"'
    response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response
```

## Quick Reference

| Task | Command |
|------|---------|
| Verify changes | `python apps/dataexplorer/verify_changes.py` or `verify_dataexplorer.bat` |
| Start server | `python run_dataexplorer.py` |
| Check server | `netstat -ano \| findstr :8085` |
| Kill server | `taskkill /F /PID <pid>` |
| Hard refresh | `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac) |

## Shared Utilities

### Using Shared Code

Instead of duplicating code, use shared utilities:

**Cache-Busting** (all Flask apps):
```python
from shared.web.flask_cache_busting import configure_flask_cache_busting, add_cache_busting_headers

# In app initialization:
configure_flask_cache_busting(app)

# In route handlers:
response = jsonify({'success': True, 'data': data})
return add_cache_busting_headers(response)
```

**Census Tract Data** (all reports):
```python
from shared.data_processing.census_tract_utils import (
    get_census_tract_join_clause,
    get_census_tract_fields,
    calculate_minority_breakdowns
)

# In SQL queries:
query = f"""
SELECT ...
{get_census_tract_fields(project_id)}
FROM branch_data b
{get_census_tract_join_clause(project_id)}
"""
```

This ensures:
- ✅ Consistent behavior across all apps
- ✅ Fixes apply everywhere automatically
- ✅ Less code duplication
- ✅ Easier maintenance

