"""BigQuery queries (placeholder).

The mortgage report builder operates on already-fetched HMDA data
(passed in as ``raw_data`` to ``build_mortgage_report``) rather than
running its own BigQuery queries. The HMDA fetch lives in
``justdata/apps/lendsight/core.py``. This module exists for parity with
the standard report_builder layout and is reserved for any future query
helpers specific to report assembly.
"""
