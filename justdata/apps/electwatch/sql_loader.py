"""SQL template loader for the electwatch app.

Loads .sql files from justdata/apps/electwatch/sql_templates/.

Note (Phase 3.4): no electwatch queries were externalized in the initial
sweep — every triple-quoted SQL assignment in this app uses method-call
or function-call interpolation (e.g. self._table_ref('officials'),
escape_sql_string(...)) that doesn't translate cleanly to .format()
placeholders. Infrastructure is in place for follow-up work.
"""
from pathlib import Path

_SQL_DIR = Path(__file__).parent / "sql_templates"


def load_sql(name: str) -> str:
    """Read a SQL template by filename (relative to sql_templates/)."""
    return (_SQL_DIR / name).read_text()
