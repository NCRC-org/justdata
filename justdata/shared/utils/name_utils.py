"""Shared utilities for cleaning lender/bank names for display."""


def strip_trailing_punctuation(name):
    """Strip trailing commas and periods from lender/bank names.

    FFIEC source data includes trailing commas in legal entity names
    (e.g., "JPMORGAN CHASE BANK,"). This strips trailing commas and
    periods before display while preserving internal punctuation.
    """
    if not name or not isinstance(name, str):
        return name
    return name.rstrip(',').rstrip('.').strip()
