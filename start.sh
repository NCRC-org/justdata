#!/bin/bash
set -e

# Get the app name from environment variable
# Default to unified "justdata" app if not specified
APP_NAME=${APP_NAME:-justdata}

# Get port from environment (Cloud Run sets this)
PORT=${PORT:-8080}

# Ensure PYTHONPATH is set
export PYTHONPATH=/app

# Verify HUD data file exists (needed for Population Share calculations in Area Analysis)
HUD_FILE="/app/justdata/data/hud/ACS-2020-Low-Mod-Local-Gov-All.xlsx"
if [ -f "$HUD_FILE" ]; then
    echo "[STARTUP] HUD data file found: $HUD_FILE"
    ls -la "$HUD_FILE"
else
    echo "[STARTUP WARNING] HUD data file NOT found: $HUD_FILE"
    echo "[STARTUP WARNING] Population Share columns will be missing in Area Analysis income tables"
    echo "[STARTUP WARNING] Contents of /app/justdata/data/:"
    ls -la /app/justdata/data/ 2>/dev/null || echo "  (directory does not exist)"
    echo "[STARTUP WARNING] Contents of /app/justdata/data/hud/:"
    ls -la /app/justdata/data/hud/ 2>/dev/null || echo "  (directory does not exist)"
fi

# Determine the module path based on app name
if [ "$APP_NAME" = "justdata" ]; then
    # Unified app - use run_justdata module
    MODULE="run_justdata:app"
else
    # Individual app - use run_${APP_NAME} pattern
    MODULE="run_${APP_NAME}:app"
fi

# Start gunicorn with the appropriate app
# Use --preload to load the app before forking workers
# Cloud Run handles scaling, so we use 1-2 workers
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "${MODULE}"

