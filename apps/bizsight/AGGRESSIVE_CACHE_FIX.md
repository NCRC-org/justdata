# Aggressive Flask Cache Fix - Jinja2 Bytecode Cache Disabled

## The Real Problem

Jinja2 (Flask's template engine) compiles templates to Python bytecode (`.pyc` files) and stores them in `__pycache__` directories. These compiled files persist on disk even after:
- Clearing in-memory cache
- Restarting the server
- Setting `TEMPLATES_AUTO_RELOAD = True`

This is why changes weren't appearing - Flask was loading the old compiled templates from disk.

## The Fix

**Disable Jinja2's bytecode cache completely:**

```python
app.jinja_env.bytecode_cache = None
```

This prevents Jinja2 from:
1. Compiling templates to `.pyc` files
2. Loading cached compiled templates from disk
3. Persisting any template compilation

## Changes Applied

1. **`app.py`**: Set `app.jinja_env.bytecode_cache = None` immediately after creating the Flask app
2. **`app.py`**: Also set it in `before_request` handler to ensure it stays disabled
3. **`app.py`**: Set it before each template render
4. **`clear_all_caches.bat`**: Added cleanup for Flask instance cache

## How to Apply

1. **Stop the server** (if running)
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
4. **Hard refresh browser:** `Ctrl+Shift+R`

## Verification

After restarting, check:
- Server console shows templates are being loaded (not from cache)
- Template changes appear immediately
- No `.pyc` files are created in `templates/__pycache__/`

## Why This Works

By setting `bytecode_cache = None`, Jinja2 will:
- Always compile templates from source on each request
- Never write compiled templates to disk
- Never load cached compiled templates
- Always use the latest template source code

This is the most aggressive cache-busting possible for Jinja2 templates.

