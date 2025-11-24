#!/bin/bash
set -e

# Get the app name from environment variable
APP_NAME=${APP_NAME:-branchseeker}

# Get port from environment (Cloud Run sets this)
PORT=${PORT:-8080}

# Ensure PYTHONPATH is set
export PYTHONPATH=/app

# Start gunicorn with the appropriate app
# Use --preload to load the app before forking workers
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "run_${APP_NAME}:app"

