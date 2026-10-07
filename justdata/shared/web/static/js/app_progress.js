/**
 * AppProgress: follow an analysis job's SSE stream into AppStates (spec 04 A6).
 *
 *   AppProgress.follow('/lendsight/progress/' + jobId, {
 *     signal,                       // from AppStates.loading(); aborting closes the stream
 *     onDone: () => loadResults(),  // job finished without an error
 *     onError: (message, ref) => {} // optional; default shows AppStates.error
 *   });
 *
 * Events are {percent, step, done, error} (backend/jobs.py). Each step text
 * goes to AppStates.stage(); the named "heartbeat" event the server sends
 * every 10 s while nothing changes also resets the no-progress timer.
 * Error text from the server ends in "Reference: <id>" (error_ref.py);
 * splitRef() separates the two for the error state.
 */
(function (root) {
  'use strict';

  var REF_RE = /\s*Reference:\s*([A-Za-z0-9_-]+)\s*$/;

  function splitRef(text) {
    var m = String(text || '').match(REF_RE);
    if (!m) return { message: String(text || ''), ref: null };
    return { message: String(text).slice(0, m.index), ref: m[1] };
  }

  function follow(url, opts) {
    opts = opts || {};
    var source = new EventSource(url);
    var finished = false;

    function close() {
      finished = true;
      source.close();
    }

    function fail(text) {
      close();
      var parts = splitRef(text);
      if (opts.onError) opts.onError(parts.message, parts.ref);
      else root.AppStates.error(parts.message || null, parts.ref);
    }

    if (opts.signal) {
      if (opts.signal.aborted) { close(); return source; }
      opts.signal.addEventListener('abort', close);
    }

    source.addEventListener('heartbeat', function () {
      if (!finished) root.AppStates.stage(null);
    });

    source.onmessage = function (e) {
      if (finished) return;
      var event;
      try { event = JSON.parse(e.data); } catch (err) { return; }
      if (event.error) { fail(event.error); return; }
      if (event.done) { close(); if (opts.onDone) opts.onDone(); return; }
      root.AppStates.stage(event.step || null);
    };

    source.onerror = function () {
      // EventSource retries on its own; only a closed stream is final.
      if (!finished && source.readyState === EventSource.CLOSED) {
        fail("We lost the connection to the analysis. Your filters are saved; try again in a moment.");
      }
    };
    return source;
  }

  root.AppProgress = { follow: follow, splitRef: splitRef };
})(typeof window !== 'undefined' ? window : globalThis);
