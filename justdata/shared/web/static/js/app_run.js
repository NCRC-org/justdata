/**
 * AppRun: run an analysis and load its report into the results column
 * (spec 04 A6). Loaded by app_page.html after app_report.js.
 *
 *   AppRun.init({
 *     baseUrl: '/lendsight',             // blueprint prefix
 *     jobId: null,                       // set when the page is /report?job_id=
 *     form: document.getElementById(...),
 *     validate: () => true,              // app's own field checks
 *     body: () => ({...}),               // JSON posted to /analyze
 *     render: (jobId, body) => Promise,  // fill the cloned report; body is /report-data
 *     emptyWhen: message => bool,        // a "no data" failure shows the empty state
 *     emptyText: '...',                  // reason shown in the empty state
 *     exportFormats: {xlsx: 'excel', pdf: 'pdf'},
 *     onReset: () => {}
 *   });
 *
 * After a run starts the address bar shows <baseUrl>/report?job_id=<id>,
 * which renders the same page and reloads that report.
 *
 * Form helpers: AppRun.setInvalid(el, message), AppRun.clearInvalid(form),
 * AppRun.geoPicker({...}) for the state-then-county picker, and
 * AppRun.selectedCounty(picker).
 */
(function (root) {
  'use strict';

  var UNAVAILABLE = 'This report is no longer available. Run the analysis again to rebuild it.';
  var cfg = null;
  var current = null;  // job id whose results are shown or loading

  // cache: 'no-store': results are per job and never come from the HTTP cache.
  function getJSON(url, signal) {
    return fetch(url, { credentials: 'same-origin', cache: 'no-store', signal: signal }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (body) { return { status: r.status, body: body }; });
    });
  }

  function setUrl(jobId) {
    var url = jobId ? cfg.baseUrl + '/report?job_id=' + encodeURIComponent(jobId) : cfg.baseUrl + '/';
    if (root.location.pathname + root.location.search !== url) root.history.replaceState(null, '', url);
  }

  function reportUrl(jobId) {
    return root.location.origin + cfg.baseUrl + '/report?job_id=' + encodeURIComponent(jobId);
  }

  function fail(message, ref) {
    if (message && cfg.emptyWhen && cfg.emptyWhen(message)) root.AppStates.empty(cfg.emptyText || null);
    else root.AppStates.error(message || null, ref);
  }

  /** /report-data can briefly answer 202 or 404 just after the job ends. */
  function fetchReport(jobId, signal, attempt) {
    attempt = attempt || 0;
    return getJSON(cfg.baseUrl + '/report-data?job_id=' + encodeURIComponent(jobId), signal).then(function (res) {
      if (res.status === 200 && res.body.success) return res.body;
      if ((res.status === 202 || res.status === 404) && attempt < 8) {
        return new Promise(function (r) { setTimeout(r, 1000); }).then(function () { return fetchReport(jobId, signal, attempt + 1); });
      }
      var err = new Error(res.body.error || '');
      err.status = res.status;
      throw err;
    });
  }

  function show(jobId, body) {
    if (current !== jobId) return null;
    return Promise.resolve(cfg.render(jobId, body)).catch(function (e) {
      root.AppStates.hint('Part of the report could not be drawn.');
      if (root.console) console.error(e);
    });
  }

  function load(jobId, signal) {
    return fetchReport(jobId, signal).then(function (body) { return show(jobId, body); }, function (err) {
      if (err.name === 'AbortError' || current !== jobId) return;
      if (err.status === 404) { root.AppStates.error(UNAVAILABLE, null); return; }
      var parts = root.AppProgress.splitRef(err.message);
      fail(parts.message, parts.ref);
    });
  }

  function follow(jobId, signal) {
    root.AppProgress.follow(cfg.baseUrl + '/progress/' + encodeURIComponent(jobId), {
      signal: signal,
      onDone: function () { load(jobId, signal); },
      onError: fail
    });
  }

  function run() {
    if (cfg.validate && !cfg.validate()) return;
    var signal = root.AppStates.loading();
    current = null;
    fetch(cfg.baseUrl + '/analyze', {
      method: 'POST', credentials: 'same-origin', signal: signal,
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg.body())
    }).then(function (r) { return r.json().catch(function () { return {}; }); }).then(function (res) {
      if (!res.success || !res.job_id) {
        var parts = root.AppProgress.splitRef(res.error);
        fail(parts.message, parts.ref);
        return;
      }
      current = res.job_id;
      setUrl(res.job_id);
      if (res.cached) load(res.job_id, signal);
      else follow(res.job_id, signal);
    }).catch(function (err) {
      if (err.name !== 'AbortError') root.AppStates.error(null, null);
    });
  }

  /** Page opened as /report?job_id=: show the report, or follow it if running. */
  function open(jobId) {
    current = jobId;
    var signal = root.AppStates.loading({ ref: jobId.slice(0, 8) });
    getJSON(cfg.baseUrl + '/report-data?job_id=' + encodeURIComponent(jobId), signal).then(function (res) {
      if (res.status === 200 && res.body.success) show(jobId, res.body);
      else if (res.status === 202) follow(jobId, signal);
      else if (res.status === 404 && res.body.progress && res.body.progress.error) {
        var parts = root.AppProgress.splitRef(res.body.progress.error);
        fail(parts.message, parts.ref);
      } else root.AppStates.error(UNAVAILABLE, null);
    }).catch(function (err) { if (err.name !== 'AbortError') root.AppStates.error(null, null); });
  }

  function init(options) {
    cfg = options;
    cfg.form.addEventListener('submit', function (e) { e.preventDefault(); run(); });
    root.AppStates.on('export', function (kind) {
      var format = (cfg.exportFormats || {})[kind];
      if (current && format) {
        root.location.href = cfg.baseUrl + '/download?format=' + format + '&job_id=' + encodeURIComponent(current);
      }
    });
    root.AppStates.on('cancel', function () { current = null; setUrl(null); });
    root.AppStates.on('reset', function () {
      current = null;
      setUrl(null);
      if (cfg.onReset) cfg.onReset();
    });
    if (cfg.jobId) open(cfg.jobId);
  }

  // ---- Form helpers -------------------------------------------------------

  /** Show or clear one field's error under its .app-field. */
  function setInvalid(el, message) {
    var field = el.closest('.app-field');
    var err = field.querySelector('.app-field-error');
    field.classList.toggle('is-invalid', !!message);
    if (message && !err) {
      err = document.createElement('p');
      err.className = 'app-field-error';
      err.id = el.id + 'Error';
      field.appendChild(err);
    }
    if (err) { err.textContent = message || ''; err.hidden = !message; }
    if (el.tagName === 'SELECT') {
      if (message) el.setAttribute('aria-describedby', el.id + 'Error'); else el.removeAttribute('aria-describedby');
      el.setAttribute('aria-invalid', message ? 'true' : 'false');
    }
  }

  function clearInvalid(form) {
    Array.prototype.forEach.call(form.querySelectorAll('.is-invalid'), function (f) { f.classList.remove('is-invalid'); });
    Array.prototype.forEach.call(form.querySelectorAll('.app-field-error'), function (p) { p.hidden = true; });
  }

  function option(value, text, data) {
    var o = document.createElement('option');
    o.value = value;
    o.textContent = text;
    if (data) o.dataset.item = JSON.stringify(data);
    return o;
  }

  /**
   * State then county. g: {state, county (selects), statesUrl,
   * countiesUrl(stateValue), stateValue(s), countyValue(c), countyLabel(c)}.
   * The selected county's full object is AppRun.selectedCounty(g).
   */
  function geoPicker(g) {
    function loadCounties(code) {
      g.county.disabled = true;
      g.county.replaceChildren(option('', code ? 'Loading counties…' : 'Select a state first'));
      if (!code) return Promise.resolve();
      return getJSON(g.countiesUrl(code)).then(function (res) {
        var list = Array.isArray(res.body) ? res.body : [];
        g.county.replaceChildren(option('', 'Select a county'));
        list.forEach(function (c) {
          if (typeof c === 'string') g.county.appendChild(option(c, c));
          else if (c && (c.name || c.county_name)) g.county.appendChild(option(g.countyValue(c), g.countyLabel(c), c));
        });
        g.county.disabled = false;
      }).catch(function () { g.county.replaceChildren(option('', 'Counties could not be loaded')); });
    }
    getJSON(g.statesUrl).then(function (res) {
      var states = Array.isArray(res.body) ? res.body : (res.body.states || []);
      g.state.replaceChildren(option('', 'Select a state'));
      states.forEach(function (s) { g.state.appendChild(option(g.stateValue(s), s.name)); });
    }).catch(function () { g.state.replaceChildren(option('', 'States could not be loaded')); });
    g.state.addEventListener('change', function () { setInvalid(g.state, ''); loadCounties(g.state.value); });
    g.county.addEventListener('change', function () { setInvalid(g.county, ''); });
    return { reset: function () { loadCounties(''); } };
  }

  function selectedCounty(g) {
    var opt = g.county.options[g.county.selectedIndex];
    return opt && opt.dataset.item ? JSON.parse(opt.dataset.item) : (g.county.value ? { name: g.county.value } : null);
  }

  root.AppRun = {
    init: init, reportUrl: reportUrl, getJSON: getJSON,
    setInvalid: setInvalid, clearInvalid: clearInvalid, geoPicker: geoPicker, selectedCounty: selectedCounty
  };
})(typeof window !== 'undefined' ? window : globalThis);
