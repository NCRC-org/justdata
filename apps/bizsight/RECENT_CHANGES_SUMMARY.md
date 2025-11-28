# Recent Changes Summary (Last 24 Hours)

## Changes Made

### 1. Benchmark Loading (core.py)
- **Updated search order** to prioritize `apps/data/` where files were generated
- **Added debug logging** to show which benchmark files are being loaded
- **Fixed BigQuery queries** to use correct column names (`numsb_under_1m` instead of `numsbrev_under_1m`)

### 2. Report Template (report_template.html)
- **Added "New Analysis" button** at top of report page (line 253)
- Links back to home page (`/`) to start new analysis

### 3. Flask Configuration (app.py)
- **Added `TEMPLATES_AUTO_RELOAD = True`** to force template reload
- **Added `SEND_FILE_MAX_AGE_DEFAULT = 0`** to disable static file caching

### 4. BigQuery Client (utils/bigquery_client.py)
- **Fixed column names** in `get_state_benchmarks()` and `get_national_benchmarks()`
- Changed `numsbrev_under_1m` → `numsb_under_1m`
- Changed `amtsbrev_under_1m` → `amtsb_under_1m`

### 5. Benchmark Generation
- **Created `generate_benchmarks.py`** to generate all 52 state files + national file
- **Created `verify_and_backup_benchmarks.py`** to verify and backup files
- **Created `backup_benchmarks.py`** simple backup script

## Files Modified

1. `apps/bizsight/core.py` - Benchmark loading logic
2. `apps/bizsight/app.py` - Flask config for template reloading
3. `apps/bizsight/templates/report_template.html` - Added "New Analysis" button
4. `apps/bizsight/utils/bigquery_client.py` - Fixed column names in queries

## Cache Issues

If changes aren't appearing after restart:

1. **Clear Python cache:**
   ```powershell
   python apps/bizsight/clear_cache.py
   ```

2. **Enable DEBUG mode:**
   ```powershell
   $env:DEBUG='True'
   ```

3. **Restart Flask server:**
   ```powershell
   python -m apps.bizsight.app
   ```

## Verification

To verify changes are active:

1. Check "New Analysis" button appears on report page
2. Check server console shows debug messages about benchmark file loading
3. Check templates reload without restart (if DEBUG=True)

