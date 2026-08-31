"""Single source of truth for the HMDA activity years the platform exposes.

Every HMDA app (LendSight, MergerMeter, DataExplorer, DotLender) should derive
its available-year list, default analysis range, and
year validation from the helpers here instead of hardcoding year literals. That
way, rolling the platform forward to a new HMDA year is a **one-line change** to
``LATEST_HMDA_YEAR`` below rather than a hunt across every app.

Rollout rule (see docs/hmda_2025_sync_audit.md):
    Bump ``LATEST_HMDA_YEAR`` only AFTER the enriched ``de_hmda`` data for that
    year has been loaded from the full June **Snapshot** (not the March Modified
    LAR) and verified end to end. Do not expose a year whose data is still the
    degraded MLAR snapshot.
"""

from typing import List, Tuple

# Earliest HMDA activity year available in de_hmda.
EARLIEST_HMDA_YEAR = 2018

# Most recent HMDA year whose enriched de_hmda data is loaded AND verified.
#
# 2025 enabled 2026-07-17: the June Snapshot was loaded (13,543,606 rows), enrichment
# re-run and verified end to end (lender join, geography, race flags, pricing), and
# year-over-year continuity confirmed against 2024. See docs/hmda_2025_sync_audit.md.
LATEST_HMDA_YEAR = 2025

# How many of the most-recent years the default analysis range spans
# (e.g. 3 -> the last three available years). With LATEST_HMDA_YEAR = 2025 this
# yields the requested 2023-2025 default; the UI can still extend back to
# EARLIEST_HMDA_YEAR.
DEFAULT_RANGE_SPAN = 3


def available_hmda_years() -> List[int]:
    """All selectable HMDA years, ascending (EARLIEST..LATEST inclusive)."""
    return list(range(EARLIEST_HMDA_YEAR, LATEST_HMDA_YEAR + 1))


def default_hmda_year_range() -> Tuple[int, int]:
    """(start_year, end_year) for the default analysis range.

    The most recent DEFAULT_RANGE_SPAN years, clamped so it never starts before
    EARLIEST_HMDA_YEAR.
    """
    start = max(EARLIEST_HMDA_YEAR, LATEST_HMDA_YEAR - DEFAULT_RANGE_SPAN + 1)
    return start, LATEST_HMDA_YEAR


def default_hmda_years() -> List[int]:
    """The default analysis range expanded to a list of years, ascending."""
    start, end = default_hmda_year_range()
    return list(range(start, end + 1))


def is_valid_hmda_year(year: int) -> bool:
    """True if ``year`` is within the exposed HMDA range."""
    try:
        y = int(year)
    except (TypeError, ValueError):
        return False
    return EARLIEST_HMDA_YEAR <= y <= LATEST_HMDA_YEAR


def clamp_hmda_year(year: int) -> int:
    """Clamp ``year`` into [EARLIEST_HMDA_YEAR, LATEST_HMDA_YEAR]."""
    return max(EARLIEST_HMDA_YEAR, min(int(year), LATEST_HMDA_YEAR))
