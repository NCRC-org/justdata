"""Stage timings for an analysis (spec 04 A5).

Wrap each BigQuery call and narrative call in an app's analysis with
timed("bq:<query name>") / timed("narrative"). Each stage writes one
structured "justdata.perf" log line (readable later from Cloud Logging) and is
appended to the current run's stage list, which the app returns alongside its
results as {"perf": perf_stages(), "ref": request_id()}.

Analyses run in background threads with no Flask request context, so the stage
list and request id live in context variables, not flask.g. Call
start_perf(ref) at the top of the worker to begin a fresh list for that run.
"""

import contextvars
import logging
import time
import uuid
from contextlib import contextmanager
from typing import List, Optional

log = logging.getLogger("justdata.perf")

_stages: contextvars.ContextVar = contextvars.ContextVar("justdata_perf_stages", default=None)
_ref: contextvars.ContextVar = contextvars.ContextVar("justdata_perf_ref", default=None)
_app: contextvars.ContextVar = contextvars.ContextVar("justdata_perf_app", default=None)


def start_perf(app: Optional[str] = None, ref: Optional[str] = None) -> str:
    """Begin a fresh stage list for this run; returns its reference id."""
    _stages.set([])
    _app.set(app)
    _ref.set(ref or uuid.uuid4().hex[:8])
    return _ref.get()


def request_id() -> str:
    if not _ref.get():
        _ref.set(uuid.uuid4().hex[:8])
    return _ref.get()


def perf_stages() -> List[dict]:
    return list(_stages.get() or [])


@contextmanager
def timed(stage: str):
    """Time one stage of the current run."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        ms = round((time.perf_counter() - t0) * 1000)
        if _stages.get() is None:
            _stages.set([])
        _stages.get().append({"stage": stage, "ms": ms})
        log.info("perf", extra={"stage": stage, "ms": ms, "app": _app.get(), "req": request_id()})
