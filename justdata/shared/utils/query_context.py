"""Per-analysis context for BigQuery jobs (spec 04 A5).

Every BigQuery job an analysis runs carries labels (app, env, job, refresh) so
bytes billed can be attributed to one run exactly from
INFORMATION_SCHEMA.JOBS, and a staff force-refresh run disables BigQuery's own
result cache so its timings and bytes are real.

How the context gets there:
  1. In the request thread, backend.lookup_cached_analysis() records the app
     and whether a force refresh was honoured on flask.g (request-scoped, so
     nothing leaks between requests on a reused thread).
  2. backend.run_in_background(work, job_id=...) reads those values and sets
     them as context variables inside the new worker thread only.
  3. get_bigquery_client() returns clients whose query() applies them
     (apply_to_job_config), so every app's queries are covered, including
     BizSight's wrapper that calls client.query directly.
Queries outside an analysis (dropdown lookups) get only the env label.
"""

import contextvars
import os
import re
from typing import Optional

_app = contextvars.ContextVar("justdata_bq_app", default=None)
_job = contextvars.ContextVar("justdata_bq_job", default=None)
_bypass_cache = contextvars.ContextVar("justdata_bq_bypass_cache", default=False)

_LABEL_RE = re.compile(r"[^a-z0-9_-]")


def _label(value) -> str:
    """BigQuery label values: lowercase letters, digits, _ and -, max 63."""
    return _LABEL_RE.sub("_", str(value).lower())[:63]


def set_query_context(app: Optional[str] = None, job_id: Optional[str] = None,
                      bypass_cache: bool = False) -> None:
    """Set the context for the current thread. Call only in a worker thread."""
    _app.set(app)
    _job.set(job_id)
    _bypass_cache.set(bool(bypass_cache))


def current_labels() -> dict:
    labels = {"env": _label(os.getenv("JUSTDATA_ENV") or "local")}
    if _app.get():
        labels["app"] = _label(_app.get())
    if _job.get():
        labels["job"] = _label(_job.get())
    if _bypass_cache.get():
        labels["refresh"] = "forced"
    return labels


def apply_to_job_config(job_config):
    """Add the current labels to a QueryJobConfig (or a new one) and, for a
    forced refresh, turn BigQuery's result cache off. Existing labels win."""
    from google.cloud.bigquery import QueryJobConfig
    job_config = job_config or QueryJobConfig()
    job_config.labels = {**current_labels(), **(job_config.labels or {})}
    if _bypass_cache.get():
        job_config.use_query_cache = False
    return job_config


def instrument_client(client):
    """Wrap client.query once so every job gets apply_to_job_config()."""
    if getattr(client, "_justdata_instrumented", False):
        return client
    original = client.query

    def query(sql, job_config=None, *args, **kwargs):
        return original(sql, apply_to_job_config(job_config), *args, **kwargs)

    client.query = query
    client._justdata_instrumented = True
    return client
