"""SQL template loader for the lenderprofile app.

Loads .sql files from justdata/apps/lenderprofile/sql_templates/.

Note (Phase 3.4): the longest clean candidate queries in lenderprofile
live under scripts/ (admin scripts, out of scope for the consolidation
sweep). The handful of clean queries in services/ are short and don't
benefit much from externalization. Infrastructure is in place for
follow-up work.
"""
from pathlib import Path

_SQL_DIR = Path(__file__).parent / "sql_templates"


def load_sql(name: str) -> str:
    """Read a SQL template by filename (relative to sql_templates/)."""
    return (_SQL_DIR / name).read_text()
