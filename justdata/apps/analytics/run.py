"""
Standalone runner for Analytics application.

Usage:
    python -m justdata.apps.analytics.run
    python justdata/apps/analytics/run.py
"""

from .app import app
from .config import config

# Export for gunicorn
application = app

if __name__ == '__main__':
    print(f"Starting {config.APP_NAME} on port {config.PORT}")
    print(f"  Debug mode: {config.DEBUG}")
    print(f"  BigQuery project: {config.BIGQUERY_PROJECT}")
    app.run(
        host='0.0.0.0',
        port=config.PORT,
        debug=config.DEBUG
    )
