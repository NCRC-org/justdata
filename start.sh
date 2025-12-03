#!/bin/bash
set -e

# Get the app name from environment variable
# Default to unified "justdata" app if not specified
APP_NAME=${APP_NAME:-justdata}

# Get port from environment (Cloud Run sets this)
PORT=${PORT:-8080}

# Ensure PYTHONPATH is set
export PYTHONPATH=/app

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

