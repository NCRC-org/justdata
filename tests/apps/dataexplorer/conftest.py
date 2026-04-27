"""Pytest configuration for dataexplorer tests.

The following files are CLI integration scripts that hit BigQuery directly
to verify aggregated/template query behavior against known totals. Each
has a `main()` and an `if __name__ == "__main__":` entry point and is
intended to be run by hand against a credentialed environment, e.g.:

    python tests/apps/dataexplorer/test_aggregated_query.py
    python tests/apps/dataexplorer/test_mortgage_template.py
    python tests/apps/dataexplorer/test_simple_count.py

Skipped at collection time so CI runs without BigQuery credentials don't
treat them as tests. The actual smoke tests in
test_dataexplorer_smoke.py remain discoverable and run in CI.

Standalone helper scripts (ct_* and connecticut_normalization_standalone)
have neither `test_` prefixes nor `def test_*` functions, so pytest
ignores them naturally — no entry needed here for them.
"""
collect_ignore = [
    "test_aggregated_query.py",
    "test_mortgage_template.py",
    "test_simple_count.py",
]
