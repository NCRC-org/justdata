"""How JustData shows "no data" (Jad, 2026-11-17).

- No data, or a share whose denominator is zero, is None in the data and an
  em dash on screen, in the PDF and in Excel.
- A missing year is a gap: None in tables, never 0, and a gap in charts.
- No percent change when the base is zero or missing.

L5: Decisions/JustData no-data display and export time zone -- 2026-11-17.
"""

from typing import Optional

NO_DATA = '—'


def is_missing(value) -> bool:
    """True for None and NaN (pandas stores a None share as NaN)."""
    if value is None:
        return True
    try:
        return value != value   # NaN is the only value not equal to itself
    except Exception:
        return False


def share(part, total) -> Optional[float]:
    """part / total * 100, or None when the total is zero or missing."""
    try:
        total = float(total)
        part = float(part)
    except (TypeError, ValueError):
        return None
    if total == 0:
        return None
    return part / total * 100


def pct_change(current, base) -> Optional[float]:
    """Percent change from base to current, or None when either is missing or
    the base is zero."""
    try:
        base = float(base)
        current = float(current)
    except (TypeError, ValueError):
        return None
    if base == 0:
        return None
    return (current - base) / base * 100


def dash_missing(df):
    """A copy of a DataFrame with every missing cell shown as the em dash, for
    report sheets in Excel (not raw data sheets)."""
    return df.astype(object).where(df.notna(), NO_DATA)


# ---- Text cells, for tables built as preformatted strings (LendSight) -------

def fmt_share(value, digits: int = 1) -> str:
    """"12.3%", or the em dash for no data."""
    return NO_DATA if is_missing(value) else f"{value:.{digits}f}%"


def fmt_pp_change(first, last, digits: int = 1) -> str:
    """Change in a share, in percentage points: "+1.2pp", "-1.2pp", "0.0pp",
    or the em dash when either end has no data."""
    if is_missing(first) or is_missing(last):
        return NO_DATA
    change = last - first
    zero = f"{0:.{digits}f}"
    text = f"{change:.{digits}f}"
    if text in (zero, f"-{zero}"):
        return f"{zero}pp"
    return f"+{text}pp" if change > 0 else f"{text}pp"


def fmt_pct_change(first, last, digits: int = 1) -> str:
    """Percent change in a count: "+12.3%", or the em dash when either end is
    missing or the base is zero."""
    change = pct_change(last, first)
    if change is None:
        return NO_DATA
    text = f"{change:.{digits}f}"
    zero = f"{0:.{digits}f}"
    if text in (zero, f"-{zero}"):
        return f"{zero}%"
    return f"+{text}%" if change > 0 else f"{text}%"
