"""Background analysis jobs and their progress stream."""

import json
import threading
import time
import uuid

from flask import Response

from justdata.shared.utils.progress_tracker import get_progress

# How often the SSE loop polls the progress store, and how often it emits a
# comment line to stop idle proxies closing the connection.
_POLL_SECONDS = 0.5
_KEEPALIVE_EVERY = 20

# A read of the progress store can fail transiently. Ending the stream on the
# first error drops a running analysis the client can no longer follow, so retry
# a few times before giving up rather than either quitting at once or, as
# MergerMeter's version did, retrying forever on a permanent failure.
_MAX_CONSECUTIVE_READ_ERRORS = 5


def new_job_id() -> str:
    return str(uuid.uuid4())


def run_in_background(work) -> None:
    """Run an analysis callable off the request thread.

    The worker has no request context, so anything derived from the request
    (user identity, form values) must be captured by the caller first.
    """
    threading.Thread(target=work, daemon=True).start()


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
                    yield ": keepalive\n\n"
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
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )
