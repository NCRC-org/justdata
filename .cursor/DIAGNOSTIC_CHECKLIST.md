# Diagnostic Checklist - Why Updates Aren't Working

## Issue 1: Census Tract Data Not Loading

### Code Changes Made:
- Fixed indentation bug in `apps/dataexplorer/acs_utils.py` line 847-859
- The `if households > 0:` check is now INSIDE the `for tract_info in tracts:` loop

### What to Check:

1. **Is the function being called?**
   - Check server logs for: `[ACS Tract Distributions] Processing X counties`
   - Check for: `[AREA ANALYSIS] Tract distributions fetched`

2. **Are tracts being matched?**
   - Check logs for: `[ACS Tract Distributions] County XXXX: Matched X/Y tracts`
   - If you see "Matched 0/X tracts", the matching logic is still failing

3. **Is data being returned?**
   - Check logs for: `[ACS Tract Distributions] Final percentages - Income tracts: {...}, Minority tracts: {...}`
   - If both are empty `{}`, no data is being matched

4. **Potential Issues:**
   - Census API key not set or invalid
   - Tract code format mismatch between HMDA and Census API
   - Exception being caught silently (check for error logs)

### Debug Steps:
1. Restart the Flask server completely
2. Check `dataexplorer_debug.log` for detailed logs
3. Look for any exceptions in the logs
4. Verify `CENSUS_API_KEY` environment variable is set

---

## Issue 2: Expand Button Not Appearing

### Code Changes Made:
- Updated button creation in `renderTopLendersTable()` line 3226-3235
- Updated button visibility in `switchTopLendersTab()` line 3454-3470
- Added CSS rules in `dashboard.css` line 2417-2438

### What to Check:

1. **Is the button being created?**
   - Open browser DevTools → Elements tab
   - Search for `btn-expand-lenders-header`
   - If not found, `hasMoreThan10` is false or button creation is failing

2. **Is the button hidden?**
   - Check computed styles for the button
   - Look for `display: none` or `visibility: hidden`
   - Check if `shouldShowInitially` is false

3. **Is the condition correct?**
   - `hasMoreThan10` = `maxLenders > 10`
   - `shouldShowInitially` = `currentData.length > 10`
   - If `currentData.length <= 10`, button will be hidden

4. **Potential Issues:**
   - Button is created but immediately hidden by CSS
   - JavaScript is hiding it after render
   - Button is in DOM but not visible due to z-index or positioning

### Debug Steps:
1. Open browser console and run:
   ```javascript
   document.querySelectorAll('.btn-expand-lenders-header')
   ```
   - Should return at least one element if button exists

2. Check if button is visible:
   ```javascript
   const btn = document.querySelector('.btn-expand-lenders-header');
   console.log('Display:', window.getComputedStyle(btn).display);
   console.log('Visibility:', window.getComputedStyle(btn).visibility);
   ```

3. Check how many lenders exist:
   ```javascript
   document.querySelectorAll('.top-lenders-table tbody tr').length
   ```

---

## Critical: Server Restart Required

**Both fixes require a full server restart to take effect:**

1. **Python changes** (acs_utils.py) - Module needs to be reloaded
2. **JavaScript changes** (dashboard.js) - Browser cache may need clearing

### To Restart:
1. Stop the current Flask server (Ctrl+C)
2. Clear browser cache (Ctrl+Shift+Delete) or hard refresh (Ctrl+F5)
3. Restart the server
4. Test again

---

## Verification Commands

### Check if Python module loads:
```python
# In Python shell or test script
from apps.dataexplorer.acs_utils import get_tract_household_distributions_for_geoids
print("Module loaded successfully")
```

### Check server logs:
- Look for `[ACS Tract Distributions]` messages
- Look for `[AREA ANALYSIS] Tract distributions fetched`
- Check for any exceptions or errors

### Check browser console:
- Open DevTools (F12)
- Check Console tab for JavaScript errors
- Check Network tab to see if data is being returned from API

---

## Next Steps if Still Not Working

1. **Check actual server logs** - Look for exceptions or errors
2. **Verify environment variables** - CENSUS_API_KEY must be set
3. **Test with a simple case** - Try with a single county (e.g., Abilene, TX)
4. **Check data flow** - Verify data is being passed from backend to frontend
5. **Check browser cache** - Clear cache and hard refresh

