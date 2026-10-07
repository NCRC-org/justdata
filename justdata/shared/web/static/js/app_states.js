/**
 * AppStates: the shared results-panel states for analysis apps (spec 04 A6).
 *
 * app_page.html renders #results, #resultsBody and the <template>s this
 * clones. Apps call:
 *   const signal = AppStates.loading({ ref: jobId });  // AbortSignal
 *   AppStates.stage('Aggregating results');           // from SSE/polling
 *   AppStates.success(htmlOrNode, { citation: {...} });
 *   AppStates.empty(reason);
 *   AppStates.error(message, ref);
 * and AppStates.on('cancel' | 'retry' | 'reset' | 'export', fn) for actions.
 *
 * Citation format (Jad, 2026-10-07):
 *   NCRC JustData, <App>. <Dataset> <years>; <geography>; <lenders>.
 *   Generated <YYYY-MM-DD>. <report URL>
 * Fields the analysis does not have are left out.
 *
 * Timeouts (Jad, 2026-10-07): a run ends in the error state if no stage
 * update arrives for 60 s, or after 10 minutes in total even while it keeps
 * reporting progress. The stall clock restarts on every stage().
 */
(function (root) {
  'use strict';

  var FALLBACK_STAGES = [
    [0, 'Querying federal records'],
    [8, 'Aggregating results'],
    [20, 'Building charts and narrative']
  ];
  var STALL_TIMEOUT_S = 60;
  var MAX_RUN_S = 600;
  var TIMEOUT_MESSAGES = {
    stalled: 'The analysis stopped reporting progress. Your filters are saved; try again in a moment.',
    max: 'The analysis did not finish within 10 minutes. Your filters are saved; try again in a moment.'
  };

  /** 'stalled', 'max' or null, for a run started at startedMs whose last
   *  stage update was at lastUpdateMs. */
  function timeoutReason(nowMs, startedMs, lastUpdateMs) {
    if ((nowMs - startedMs) / 1000 >= MAX_RUN_S) return 'max';
    if ((nowMs - lastUpdateMs) / 1000 >= STALL_TIMEOUT_S) return 'stalled';
    return null;
  }

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  function isoDate(d) {
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }

  function present(v) {
    if (Array.isArray(v)) return v.filter(present).length > 0;
    return v !== undefined && v !== null && String(v).trim() !== '';
  }

  /** Build the one-line citation. c: {dataset, years, geography, lenders, url}. */
  function formatCitation(appName, c, now) {
    c = c || {};
    var parts = ['NCRC JustData, ' + appName + '.'];
    var data = [c.dataset, c.years].filter(present).join(' ');
    var lenders = Array.isArray(c.lenders) ? c.lenders.filter(present).join(', ') : c.lenders;
    var detail = [data, c.geography, lenders].filter(present).join('; ');
    if (detail) parts.push(detail + '.');
    parts.push('Generated ' + isoDate(now || new Date()) + '.');
    if (present(c.url)) parts.push(String(c.url));
    return parts.join(' ');
  }

  var el = {};
  var handlers = {};
  var run = null;          // {controller, timer, started, lastUpdate, stageFromServer, ref}
  var citation = null;

  function emit(name, detail) {
    (handlers[name] || []).forEach(function (fn) { fn(detail); });
  }

  function stopRun() {
    if (run) clearInterval(run.timer);
    run = null;
  }

  function show(templateId, fill) {
    var tpl = document.getElementById(templateId);
    if (!tpl || !el.body) return null;
    var node = tpl.content.firstElementChild.cloneNode(true);
    if (fill) fill(node);
    el.body.replaceChildren(node);
    return node;
  }

  function setBusy(busy) {
    if (el.results) el.results.setAttribute('aria-busy', busy ? 'true' : 'false');
    if (el.run) el.run.disabled = !!busy;
  }

  function setActions(visible) {
    if (el.actions) el.actions.hidden = !visible;
  }

  function setText(node, selector, text) {
    var t = node.querySelector(selector);
    if (t) t.textContent = text;
    return t;
  }

  function tick() {
    if (!run) return;
    var now = Date.now();
    var elapsed = Math.floor((now - run.started) / 1000);
    var counter = document.getElementById('loadingElapsed');
    if (counter) counter.textContent = String(elapsed);
    if (!run.stageFromServer) {
      var text = FALLBACK_STAGES[0][1];
      FALLBACK_STAGES.forEach(function (s) { if (elapsed >= s[0]) text = s[1]; });
      var stageEl = document.getElementById('loadingStage');
      if (stageEl && stageEl.textContent !== text) stageEl.textContent = text;
    }
    var reason = timeoutReason(now, run.started, run.lastUpdate);
    if (reason) {
      var ref = run.ref;
      run.controller.abort();
      api.error(TIMEOUT_MESSAGES[reason], ref);
    }
  }

  var api = {
    formatCitation: formatCitation,
    timeoutReason: timeoutReason,

    on: function (name, fn) {
      (handlers[name] = handlers[name] || []).push(fn);
      return api;
    },

    idle: function () {
      stopRun();
      citation = null;
      show('appStateIdle');
      setBusy(false);
      setActions(false);
    },

    /** Show the loading state; returns an AbortSignal that Cancel aborts. */
    loading: function (opts) {
      opts = opts || {};
      stopRun();
      citation = null;
      var now = Date.now();
      run = {
        controller: new AbortController(),
        started: now,
        lastUpdate: now,
        stageFromServer: false,
        ref: opts.ref || null
      };
      show('appStateLoading');
      setBusy(true);
      setActions(false);
      run.timer = setInterval(tick, 1000);
      return run.controller.signal;
    },

    /** Server-sent stage text; replaces the fallback stages for this run. */
    stage: function (text, ref) {
      if (!run) return;
      run.lastUpdate = Date.now();
      if (ref) run.ref = ref;
      if (!present(text)) return;
      run.stageFromServer = true;
      var stageEl = document.getElementById('loadingStage');
      if (stageEl) stageEl.textContent = text;
    },

    success: function (content, opts) {
      opts = opts || {};
      stopRun();
      if (el.body) {
        if (typeof content === 'string') el.body.innerHTML = content;
        else if (content) el.body.replaceChildren(content);
      }
      citation = opts.citation || null;
      setBusy(false);
      setActions(true);
    },

    empty: function (reason) {
      stopRun();
      show('appStateEmpty', function (node) {
        if (present(reason)) setText(node, '#emptyReason', reason);
      });
      setBusy(false);
      setActions(false);
    },

    error: function (message, ref) {
      stopRun();
      show('appStateError', function (node) {
        if (present(message)) setText(node, '#errorMessage', message);
        if (present(ref)) {
          setText(node, '#errorRef', ref);
          node.querySelector('#errorRefLine').hidden = false;
          node.querySelector('#errorReport').href = '/contact?ref=' + encodeURIComponent(ref);
        }
      });
      setBusy(false);
      setActions(false);
    },

    citation: function () {
      return formatCitation(el.appName, citation || {});
    },

    copyCitation: function () {
      var text = api.citation();
      var done = function () { api.hint('Citation copied.'); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text).then(done, function () {
          api.hint('Copy failed. Citation: ' + text);
        });
      }
      api.hint('Citation: ' + text);
      return Promise.resolve();
    },

    /** One line under the Run button (validation, copy confirmations). */
    hint: function (text) {
      if (el.hint) el.hint.textContent = text || '';
    }
  };

  function onClick(e) {
    var target = e.target.closest('[data-action], [data-export]');
    if (!target) return;
    var action = target.getAttribute('data-action');
    if (target.hasAttribute('data-export')) {
      emit('export', target.getAttribute('data-export'));
    } else if (action === 'cancel') {
      if (run) run.controller.abort();
      api.idle();
      emit('cancel');
    } else if (action === 'retry') {
      emit('retry');
      if (!handlers.retry && el.form) el.form.requestSubmit();
    } else if (action === 'reset') {
      if (run) run.controller.abort();
      if (el.form) el.form.reset();
      api.idle();
      api.hint('');
      emit('reset');
    } else if (action === 'copy-citation') {
      api.copyCitation();
    }
  }

  function init() {
    el.results = document.getElementById('results');
    if (!el.results) return;
    el.body = document.getElementById('resultsBody');
    el.actions = document.getElementById('resultsActions');
    el.run = document.getElementById('runBtn');
    el.hint = document.getElementById('runHint');
    el.appName = el.results.getAttribute('data-app-name') || '';
    el.form = document.getElementById(el.results.getAttribute('data-form') || '');
    document.addEventListener('click', function (e) {
      if (e.target.closest && (e.target.closest('.app-workbench'))) onClick(e);
    });
  }

  root.AppStates = api;
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
  }
})(typeof window !== 'undefined' ? window : globalThis);
