"""Background jobs and the SSE progress stream."""

import json
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
    def _stream(self, app, progress_values):
        with patch("justdata.backend.jobs.get_progress", side_effect=progress_values), \
             patch("justdata.backend.jobs.time.sleep"):
            with app.test_request_context():
                resp = sse_response("job-1")
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
