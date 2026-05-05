"""SQL template loader for the analytics app.

Loads .sql files from justdata/apps/analytics/sql_templates/ for use by
the per-domain query modules under bq/queries/.
"""
from pathlib import Path

_SQL_DIR = Path(__file__).parent / "sql_templates"


def load_sql(name: str) -> str:
    """Read a SQL template by filename (relative to sql_templates/)."""
    return (_SQL_DIR / name).read_text()
