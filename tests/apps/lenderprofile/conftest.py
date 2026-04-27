"""Pytest configuration for lenderprofile tests.

The following files are CLI integration scripts (each has a `main()` and an
`if __name__ == "__main__":` entry point). They define `def test_*` functions
that pytest tries to auto-collect, but those functions take positional
arguments (e.g. `lender_name`, `identifiers`) that pytest cannot supply as
fixtures, which produces collection-time errors.

Skip them at collection time so CI runs that lack BigQuery / external API
credentials don't fail on fixture errors. The scripts can still be invoked
directly, e.g.:

    python tests/apps/lenderprofile/test_all_apis.py "Fifth Third Bank"
    python tests/apps/lenderprofile/test_fitb.py
"""
collect_ignore = [
    "test_all_apis.py",
    "test_fdic_branches.py",
    "test_fifth_third_cached.py",
    "test_fitb.py",
]
