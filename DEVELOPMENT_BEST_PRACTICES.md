# Development Best Practices - Avoiding Repeated Errors

## The Problem

We keep encountering the same types of errors:
1. **Cache issues** - Changes not appearing due to Flask/browser caching
2. **Code duplication** - Same fixes applied inconsistently across reports
3. **Missing verification** - Changes made but not tested/verified
4. **Pattern inconsistency** - Different approaches to the same problem

## The Solution: Systematic Workflow

### 1. Always Verify After Changes

**Before declaring work done:**
```bash
# Run verification script
python apps/dataexplorer/verify_changes.py

# Or use the batch file
verify_dataexplorer.bat
```

This checks:
- ✓ Code changes are actually in the files
- ✓ Server is running and responding
- ✓ Cache-busting headers are active
- ✓ API endpoints work correctly

### 2. Use Shared Utilities (Don't Duplicate Code)

**Created shared utilities:**

#### Cache-Busting (`shared/web/flask_cache_busting.py`)
```python
from shared.web.flask_cache_busting import configure_flask_cache_busting, add_cache_busting_headers

# In app initialization:
configure_flask_cache_busting(app)

# In route handlers:
response = jsonify({'success': True, 'data': data})
return add_cache_busting_headers(response)
```

#### Census Tract Data (`shared/data_processing/census_tract_utils.py`)
```python
from shared.data_processing.census_tract_utils import (
    get_census_tract_join_clause,
    get_census_tract_fields,
    calculate_minority_breakdowns
)

# Use in queries instead of duplicating SQL
```

**Benefits:**
- ✅ Fix once, works everywhere
- ✅ Consistent behavior
- ✅ Easier maintenance
- ✅ Less code to review

### 3. Follow Established Patterns

**When fixing similar issues:**

1. **Check working examples first**
   - Look at mortgage/small business reports
   - See how they handle the same problem
   - Copy the working pattern

2. **Document the pattern**
   - Add to `DEVELOPMENT_WORKFLOW.md`
   - Create shared utility if used 3+ times
   - Update this file with the solution

3. **Apply consistently**
   - Use the same approach everywhere
   - Don't reinvent the wheel
   - Update all similar code at once

### 4. Test Immediately

**After making changes:**
1. Save all files
2. Run verification script
3. Hard refresh browser (`Ctrl+Shift+R`)
4. Check browser console for errors
5. Verify data is correct

**Don't move on until:**
- ✓ Verification script passes
- ✓ Changes visible in browser
- ✓ No console errors
- ✓ Data looks correct

### 5. Standard Development Workflow

```
1. Make code changes
   ↓
2. Save all files (Ctrl+S)
   ↓
3. Run verification: python apps/dataexplorer/verify_changes.py
   ↓
4. If server needs restart: Restart it
   ↓
5. Hard refresh browser: Ctrl+Shift+R
   ↓
6. Check console for errors
   ↓
7. Verify data is correct
   ↓
8. If issues found → Go back to step 1
   ↓
9. If all good → Document the pattern
```

## Common Issues & Quick Fixes

### Issue: Changes Not Appearing
**Checklist:**
- [ ] Files saved?
- [ ] Server restarted?
- [ ] Browser hard refreshed?
- [ ] Cache-busting headers present? (check Network tab)
- [ ] Verification script passes?

### Issue: Census Tract Data Missing
**Solution:**
- Use `shared/data_processing/census_tract_utils.py`
- Join with `geo.census` table
- Include `tract_minority_population_percent` field

### Issue: Data Format Wrong
**Solution:**
- Check if data is in thousands (multiply by 1000) or full dollars
- Verify query transformations
- Check how other reports handle same data type

### Issue: Table Not Rendering
**Solution:**
- Check JavaScript conditions (remove `dataType !== 'branches'` if needed)
- Verify data structure matches frontend expectations
- Check console logs for rendering errors

## Quick Reference Commands

| Task | Command |
|------|---------|
| Verify changes | `python apps/dataexplorer/verify_changes.py` |
| Quick verify | `verify_dataexplorer.bat` |
| Start server | `python run_dataexplorer.py` |
| Check server | `netstat -ano \| findstr :8085` |
| Kill server | `taskkill /F /PID <pid>` |
| Hard refresh | `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac) |

## Key Takeaways

1. **Always verify** - Don't assume changes are active
2. **Use shared code** - Don't duplicate, reuse
3. **Follow patterns** - Check working examples first
4. **Test immediately** - Catch issues before moving on
5. **Document solutions** - Help future you and others

## Files Created

1. **`apps/dataexplorer/verify_changes.py`** - Automated verification script
2. **`apps/dataexplorer/DEVELOPMENT_WORKFLOW.md`** - Detailed workflow guide
3. **`verify_dataexplorer.bat`** - Quick verification batch file
4. **`shared/web/flask_cache_busting.py`** - Shared cache-busting utilities
5. **`shared/data_processing/census_tract_utils.py`** - Shared census tract utilities
6. **`DEVELOPMENT_BEST_PRACTICES.md`** - This file

Use these tools to avoid the back-and-forth frustration!

