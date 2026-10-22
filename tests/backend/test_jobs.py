"""Background jobs and the SSE progress stream."""

import itertools
import json
import time
from unittest.mock import patch

import pytest
from flask import Flask

from justdata.backend.jobs import new_job_id, run_in_background, sse_response


@pytest.fixture
def app():
    return Flask(__name__)


def _events(client_response_text):
    """Pull the JSON payloads out of an SSE body, ignoring comment lines."""
    return [
        json.loads(line[len("data: "):])
        for line in client_response_text.splitlines()
        if line.startswith("data: ")
    ]


def test_new_job_id_is_unique():
    assert new_job_id() != new_job_id()


def test_run_in_background_runs_the_work():
    import threading
    done = threading.Event()
    run_in_background(done.set)
    assert done.wait(timeout=5), "background work did not run"


class TestProgressStream:
    def _stream(self, app, progress_values, clock=None, **kw):
        with patch("justdata.backend.jobs.find_progress", side_effect=progress_values), \
             patch("justdata.backend.jobs.time.sleep"), \
             patch("justdata.backend.jobs._clock", side_effect=clock or itertools.repeat(0.0)):
            with app.test_request_context():
                resp = sse_response("job-1", **kw)
                return "".join(
                    chunk.decode() if isinstance(chunk, bytes) else chunk
                    for chunk in resp.response
                )

    def test_streams_until_done(self, app):
        body = self._stream(app, [
            {"percent": 10, "step": "Querying data...", "done": False},
            {"percent": 100, "step": "Complete", "done": True},
        ])
        events = _events(body)
        assert events[0]["percent"] == 10
        assert events[-1]["done"] is True

    def test_stops_on_error(self, app):
        body = self._stream(app, [
            {"percent": 0, "step": "Failed", "done": False, "error": "boom"},
        ])
        events = _events(body)
        assert events[-1]["error"] == "boom"

    def test_step_text_with_quotes_stays_parseable(self, app):
        """The apps built this JSON by hand and did not escape the step text.

        A quote or newline in an operator-written progress message produced an
        unparseable event and a stalled progress bar in the browser.
        """
        nasty = 'Analyzing "Prince George\'s County"\nsecond line'
        body = self._stream(app, [{"percent": 50, "step": nasty, "done": True}])

        events = _events(body)  # would raise if the payload were malformed
        assert events[-1]["step"] == nasty

    def test_emits_keepalive_before_the_first_update(self, app):
        body = self._stream(app, [{"percent": 0, "step": "Starting...", "done": True}])
        assert body.startswith(": connected")

    def test_long_unchanged_step_sends_named_heartbeats(self, app):
        """A long narrative call leaves progress unchanged for many polls. The
        stream sends a named heartbeat event so a client can tell the run is
        alive; onmessage handlers (unnamed events) never receive it."""
        same = {"percent": 88, "step": "Building charts and narrative", "done": False}
        body = self._stream(app, [same] * 45 + [{"percent": 100, "step": "Complete", "done": True}])
        assert body.count("event: heartbeat\ndata: {}\n\n") == 2
        blocks = [b for b in body.split("\n\n") if b.strip()]
        unnamed = [json.loads(b.split("data: ", 1)[1]) for b in blocks
                   if b.startswith("data: ")]
        assert [e["percent"] for e in unnamed] == [88, 100]

    def test_no_hop_by_hop_connection_header(self, app):
        """PEP 3333 forbids apps from setting Connection. Under the local
        werkzeug server it made Chrome reuse the finished stream's socket and
        strand the next request (the report fetch) indefinitely."""
        with app.test_request_context():
            resp = sse_response("job-1")
        assert "Connection" not in resp.headers
        assert resp.headers["Cache-Control"] == "no-cache"

    def test_survives_a_transient_read_failure(self, app):
        """A blip reading the progress store must not drop a running analysis."""
        body = self._stream(app, [
            {"percent": 10, "step": "Querying data...", "done": False},
            RuntimeError("transient"),
            {"percent": 100, "step": "Complete", "done": True},
        ])
        events = _events(body)
        assert events[-1]["done"] is True
        assert not any(e.get("error") for e in events)

    def test_gives_up_after_repeated_read_failures(self, app):
        """But a permanently broken store must end the stream, not spin forever."""
        body = self._stream(app, [RuntimeError("down")] * 10)
        events = _events(body)
        assert events[-1]["done"] is True
        assert events[-1]["error"] == "down"


class TestStreamAlwaysEnds:
    """Each open stream holds a gunicorn thread, and Cloud Run keeps it open
    after the browser leaves. On 2026-10-20 four streams for a made-up job id
    ran for an hour each and the testing site stopped answering."""

    def _read(self, chunks, limit_s=2.0):
        """Read a streamed body, failing (not hanging) if it outlives limit_s."""
        started = time.monotonic()
        body = ""
        for chunk in chunks:
            body += chunk.decode() if isinstance(chunk, bytes) else chunk
            assert time.monotonic() - started < limit_s, f"stream still open: {body!r}"
        return body, time.monotonic() - started

    def test_unknown_job_ends_with_an_error_and_reference(self, app):
        with app.test_request_context():
            resp = sse_response(new_job_id())
            body, seconds = self._read(resp.response)
        events = _events(body)
        assert seconds < 1
        assert len(events) == 1 and events[0]["done"] is True
        assert events[0]["error"].startswith("This report is no longer available.")
        assert " Reference: " in events[0]["error"]

    @pytest.mark.parametrize("client_name", ["lendsight_client", "bizsight_client", "branchsight_client"])
    def test_unknown_job_route_closes_within_a_second(self, request, sign_in, client_name):
        client = request.getfixturevalue(client_name)
        sign_in(client, "member")
        resp = client.get(f"/progress/{new_job_id()}", buffered=False)
        body, seconds = self._read(resp.response)
        assert seconds < 1
        assert " Reference: " in _events(body)[-1]["error"]

    def test_a_job_recorded_by_analyze_is_not_unknown(self, app):
        """/analyze creates the tracker before it returns the id, so the
        stream finds the job even before the worker's first update."""
        from justdata.shared.utils.progress_tracker import (
            create_progress_tracker, find_progress, progress_store)
        job_id = new_job_id()
        try:
            create_progress_tracker(job_id)
            assert find_progress(job_id)["done"] is False
        finally:
            progress_store.pop(job_id, None)

    def test_record_that_vanishes_gets_ten_seconds(self, app):
        running = {"percent": 40, "step": "Querying data...", "done": False}
        # One clock reading per second; the record is gone after the first poll.
        body = TestProgressStream()._stream(
            app, [running] + [None] * 30, clock=itertools.count(0.0, 1.0))
        events = _events(body)
        assert events[0]["step"] == "Querying data..."
        assert events[-1]["error"].startswith("This report is no longer available.")
        assert len(events) == 2

    def test_record_that_comes_back_keeps_the_stream(self, app):
        running = {"percent": 40, "step": "Querying data...", "done": False}
        body = TestProgressStream()._stream(
            app, [running, None, None, {"percent": 100, "step": "Complete", "done": True}],
            clock=itertools.count(0.0, 1.0))
        events = _events(body)
        assert events[-1] == {"percent": 100, "step": "Complete", "done": True, "error": None}

    def test_stream_ends_at_the_run_cap_plus_a_minute(self, app):
        running = {"percent": 88, "step": "Building charts and narrative", "done": False}
        # Each poll reads the clock twice at most; 30 s per reading passes the
        # 600 + 60 s cap well inside 100 polls.
        body = TestProgressStream()._stream(
            app, itertools.repeat(running), clock=itertools.count(0.0, 30.0))
        events = _events(body)
        assert events[-1]["error"].startswith("The analysis did not finish in time.")

    def test_cap_follows_the_app(self, app):
        running = {"percent": 88, "step": "Building charts and narrative", "done": False}
        clock = itertools.chain([0.0], itertools.repeat(1859.0, 3), itertools.repeat(1860.0))
        body = TestProgressStream()._stream(
            app, itertools.repeat(running), clock=clock, max_run_seconds=1800)
        assert _events(body)[-1]["error"].startswith("The analysis did not finish in time.")
