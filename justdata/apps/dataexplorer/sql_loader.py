"""SQL template loader for the dataexplorer app.

Loads .sql files from justdata/apps/dataexplorer/sql_templates/.
"""
from pathlib import Path

_SQL_DIR = Path(__file__).parent / "sql_templates"


def load_sql(name: str) -> str:
    """Read a SQL template by filename (relative to sql_templates/)."""
    return (_SQL_DIR / name).read_text()
