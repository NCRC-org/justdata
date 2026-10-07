"""Background analysis jobs and their progress stream."""

import json
import threading
import time
import uuid
from typing import Optional

from flask import Response, g, has_request_context

from justdata.shared.utils.progress_tracker import get_progress
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


def sse_response(job_id: str) -> Response:
    """Stream a job's progress as Server-Sent Events until it finishes."""
    def stream():
        last = None
        idle_polls = 0
        read_errors = 0
        yield ": connected\n\n"

        while True:
            try:
                progress = get_progress(job_id) or {}
                read_errors = 0
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
