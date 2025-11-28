# How to Check Server Logs for Cache Issues

## What to Look For

When you start the server, you should see these messages in the console:

### 1. **On Server Startup:**
```
================================================================================
INITIALIZING FLASK APP - DISABLING JINJA2 BYTECODE CACHE
================================================================================
✓ Jinja2 bytecode_cache disabled: None
✓ Template folder: [path]
✓ Static folder: [path]
================================================================================

================================================================================
STARTING BIZSIGHT FLASK SERVER
================================================================================
Port: 8081
Host: 0.0.0.0
DEBUG mode: True
TEMPLATES_AUTO_RELOAD: True
Jinja2 bytecode_cache: None
Template folder: [path]
Static folder: [path]
================================================================================
```

### 2. **On First Request:**
```
DEBUG: Template cache cleared, bytecode_cache=None, auto_reload=True
DEBUG: Rendering analysis_template.html, bytecode_cache=None
```
or
```
DEBUG: Rendering report_template.html for job_id=[id], bytecode_cache=None
```

## If You DON'T See These Messages:

1. **Server is running old code** - The server needs to be restarted
2. **Python bytecode cache** - Old `.pyc` files are being loaded
3. **Server not restarted** - Changes won't appear until restart

## What to Do:

1. **Stop the server** (Ctrl+C or kill the process)

2. **Clear all caches:**
   ```batch
   clear_all_caches.bat
   ```

3. **Restart the server:**
   ```batch
   set DEBUG=True
   set FLASK_DEBUG=1
   python -m apps.bizsight.app
   ```

4. **Check the console output** - You should see the initialization messages above

5. **Make a request** - Navigate to the site and check for the "DEBUG: Rendering..." messages

## Verification Checklist:

- [ ] Server startup shows "Jinja2 bytecode_cache disabled: None"
- [ ] Server startup shows "TEMPLATES_AUTO_RELOAD: True"
- [ ] First request shows "DEBUG: Template cache cleared"
- [ ] Template rendering shows "bytecode_cache=None"
- [ ] No `.pyc` files in `templates/__pycache__/` directory

## If Still No Changes:

1. **Verify code is loaded:**
   ```python
   python apps/bizsight/verify_code_loaded.py
   ```

2. **Check browser cache:**
   - Open DevTools (F12)
   - Go to Network tab
   - Check "Disable cache"
   - Hard refresh: Ctrl+Shift+R

3. **Check if server is actually running the new code:**
   - Look for the startup messages
   - If you don't see them, the server is running old code

4. **Nuclear option - Delete all Python cache:**
   ```batch
   for /d /r apps\bizsight %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
   for /r apps\bizsight %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
   ```

