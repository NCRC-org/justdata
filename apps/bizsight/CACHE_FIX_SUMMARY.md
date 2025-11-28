# Flask Cache-Busting Fixes Applied

## Problem
Flask was caching templates and static files, preventing code changes from appearing even after server restarts. This was causing persistent issues where updates weren't visible.

## Solutions Implemented

### 1. Flask Configuration (app.py)
- **`DEBUG = True`**: Always enabled for development
- **`TEMPLATES_AUTO_RELOAD = True`**: Forces template reload on every request
- **`SEND_FILE_MAX_AGE_DEFAULT = 0`**: Disables static file caching
- **`EXPLAIN_TEMPLATE_LOADING = True`**: Debug template loading

### 2. Before Request Handler (app.py)
Added `clear_template_cache()` function that runs before every request:
- Clears Jinja2 template cache dictionary
- Sets `auto_reload = True`
- Attempts to call `cache.clear()` for additional clearing

### 3. Response Headers
Added aggressive cache-busting HTTP headers to all responses:
- **`Cache-Control: no-cache, no-store, must-revalidate, max-age=0`**
- **`Pragma: no-cache`**
- **`Expires: 0`**

Applied to:
- `/` (index page)
- `/report` (report page)
- `/report-data` (JSON data endpoint)

### 4. JavaScript Cache-Busting (report_template.html)
Added timestamp query parameter to `/report-data` fetch:
```javascript
const cacheBuster = new Date().getTime();
fetch(`/report-data?job_id=${jobId}&_t=${cacheBuster}`)
```

### 5. Template Cache Clearing on Render
Each route that renders a template now:
1. Clears Jinja2 cache before rendering
2. Adds cache-busting headers to response

### 6. Cache Clearing Scripts
Created utilities to clear Python bytecode cache:
- **`force_cache_clear.py`**: Python script to clear all caches
- **`clear_all_caches.bat`**: Batch file for Windows (bypasses PowerShell issues)

## How to Use

### Before Restarting Server:
1. **Run cache clear script:**
   ```batch
   clear_all_caches.bat
   ```
   Or manually:
   ```batch
   for /d /r apps\bizsight %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
   for /r apps\bizsight %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
   ```

2. **Stop the server** (if running):
   ```batch
   for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8081 ^| findstr LISTENING') do taskkill /F /PID %%a
   ```

3. **Restart with DEBUG mode:**
   ```batch
   set DEBUG=True
   set FLASK_DEBUG=1
   python -m apps.bizsight.app
   ```

### Browser Cache
If changes still don't appear:
1. **Hard refresh** the browser: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
2. **Clear browser cache** for localhost
3. **Open DevTools** and check "Disable cache" in Network tab

## Verification

After restarting, check:
1. Server console shows `DEBUG: True`
2. Template changes appear immediately
3. JavaScript console shows cache-busting timestamp in fetch URL
4. Network tab shows `Cache-Control: no-cache` headers

## Files Modified

1. `apps/bizsight/app.py`:
   - Added cache-busting configuration
   - Added `clear_template_cache()` before_request handler
   - Added cache headers to all route responses
   - Added template cache clearing before render

2. `apps/bizsight/templates/report_template.html`:
   - Added timestamp query parameter to `/report-data` fetch

3. Created utilities:
   - `apps/bizsight/force_cache_clear.py`
   - `clear_all_caches.bat`

## Notes

- The cache-busting is aggressive and may impact performance slightly in production
- For production, consider removing some of these measures and using proper cache headers
- The timestamp query parameter ensures browser doesn't cache the JSON response
- Python bytecode cache (`.pyc` files) must be cleared when Python code changes

