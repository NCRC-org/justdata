"""Background analysis jobs and their progress stream."""

import json
import threading
import time
import uuid
from typing import Optional

from flask import Response, g, has_request_context

from justdata.shared.utils.error_ref import user_error
from justdata.shared.utils.progress_tracker import find_progress
from justdata.shared.utils.query_context import set_query_context

# How often the SSE loop polls the progress store, and how often it emits a
# comment line to stop idle proxies closing the connection.
_POLL_SECONDS = 0.5
_KEEPALIVE_EVERY = 20
# Sent every _KEEPALIVE_EVERY idle polls (10 s) while the progress values are
# unchanged, e.g. during one long narrative call. A named event, so
# EventSource.onmessage handlers never see it, while app_states.js listens for
# it to keep its 60 s no-progress timer from ending a run that is still alive.
# (An SSE comment would keep the connection open but is invisible to scripts.)
_HEARTBEAT = "event: heartbeat\ndata: {}\n\n"

# A read of the progress store can fail transiently. Ending the stream on the
# first error drops a running analysis the client can no longer follow, so retry
# a few times before giving up rather than either quitting at once or, as
# MergerMeter's version did, retrying forever on a permanent failure.
_MAX_CONSECUTIVE_READ_ERRORS = 5

# A stream must end on its own: Cloud Run keeps it open to the container after
# the browser leaves, and each open stream holds one of gunicorn's threads. On
# 2026-10-20 four streams for a made-up job id each ran to the 3,600 s request
# timeout and the testing site answered nothing for an hour (Jad, 2026-10-22).
# - A job with no progress record when the stream opens does not exist here:
#   /analyze records the job before it returns the id. The stream ends at once.
# - A record that disappears mid-run (evicted) gets _MISSING_GRACE_SECONDS to
#   come back.
# - Every stream ends by the app's run cap plus _CAP_MARGIN_SECONDS. The
#   default cap matches MAX_RUN_S in app_states.js; an app with a longer client
#   cap (MergerMeter) passes it.
_MISSING_GRACE_SECONDS = 10
DEFAULT_MAX_RUN_SECONDS = 600
_CAP_MARGIN_SECONDS = 60
_NOT_FOUND = "This report is no longer available. Run the analysis again to rebuild it."
_TOO_LONG = "The analysis did not finish in time. Your filters are saved; try again in a moment."
_clock = time.monotonic


def new_job_id() -> str:
    return str(uuid.uuid4())


def run_in_background(work, job_id: Optional[str] = None) -> None:
    """Run an analysis callable off the request thread.

    The worker has no request context, so anything derived from the request
    (user identity, form values) must be captured by the caller first. The
    BigQuery query context (app and force-refresh flag recorded on flask.g by
    lookup_cached_analysis, plus this job_id) is carried into the worker so
    its queries are labelled and, for a staff force refresh, skip BigQuery's
    result cache (shared/utils/query_context.py).
    """
    app = getattr(g, 'bq_app', None) if has_request_context() else None
    bypass = getattr(g, 'bq_bypass_cache', False) if has_request_context() else False

    def target():
        set_query_context(app=app, job_id=job_id, bypass_cache=bypass)
        work()

    threading.Thread(target=target, daemon=True).start()


def _event(percent, step, done, error) -> str:
    # json.dumps every field: step text is operator-written and has contained
    # quotes and apostrophes, which the apps' hand-built JSON strings did not
    # escape, producing an unparseable event and a stalled progress bar.
    payload = json.dumps({
        'percent': percent,
        'step': step,
        'done': bool(done),
        'error': error,
    })
    return f"data: {payload}\n\n"


def _failed(message: str, job_id: str, why: str) -> str:
    """The terminal error event, with a reference id logged next to the cause."""
    shown, _ref = user_error(message, context=f"progress stream job={job_id}: {why}")
    return _event(0, 'Error', True, shown)


def sse_response(job_id: str, max_run_seconds: int = DEFAULT_MAX_RUN_SECONDS) -> Response:
    """Stream a job's progress as Server-Sent Events until it finishes."""
    def stream():
        last = None
        idle_polls = 0
        read_errors = 0
        started = _clock()
        missing_since = None
        first_read = True
        last_progress = {}
        yield ": connected\n\n"

        while True:
            try:
                if _clock() - started >= max_run_seconds + _CAP_MARGIN_SECONDS:
                    yield _failed(_TOO_LONG, job_id, f"stream reached {max_run_seconds} s cap")
                    break
                progress = find_progress(job_id)
                read_errors = 0
                if progress is None:
                    if first_read:
                        yield _failed(_NOT_FOUND, job_id, "no progress record")
                        break
                    if missing_since is None:
                        missing_since = _clock()
                    elif _clock() - missing_since >= _MISSING_GRACE_SECONDS:
                        yield _failed(_NOT_FOUND, job_id, "progress record gone")
                        break
                    progress = last_progress
                else:
                    missing_since = None
                    last_progress = progress
                first_read = False
                percent = progress.get('percent', 0)
                step = progress.get('step', 'Starting...')
                done = progress.get('done', False)
                error = progress.get('error')

                current = (percent, step, done, error)
                if current != last or done or error:
                    yield _event(percent, step, done, error)
                    last = current
                    idle_polls = 0

                if done or error:
                    break

                idle_polls += 1
                if idle_polls >= _KEEPALIVE_EVERY:
                    yield _HEARTBEAT
                    idle_polls = 0

                time.sleep(_POLL_SECONDS)
            except GeneratorExit:
                break
            except Exception as e:
                read_errors += 1
                if read_errors >= _MAX_CONSECUTIVE_READ_ERRORS:
                    yield _event(0, f"Error: {e}", True, str(e))
                    break
                time.sleep(_POLL_SECONDS)

    return Response(
        stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
