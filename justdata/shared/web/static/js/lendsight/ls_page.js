/**
 * LendSight page: controls, run, progress and results (spec 04 Part B).
 * Loading, empty and error states are AppStates; progress is AppProgress.
 * After a run starts the address bar shows /lendsight/report?job_id=<id>,
 * which renders this same page and reloads that report.
 */
(function (root) {
  'use strict';

  var CFG = root.LENDSIGHT || {};
  var BASE = CFG.baseUrl || '/lendsight';
  var NO_DATA = 'No data found for the specified parameters';  // core.run_analysis
  var form = document.getElementById('lsForm');
  var stateSel = document.getElementById('lsState');
  var countySel = document.getElementById('lsCounty');
  var current = null;  // job id whose results are shown or loading

  function $(id) { return document.getElementById(id); }

  function option(value, text, data) {
    var o = document.createElement('option');
    o.value = value;
    o.textContent = text;
    if (data) o.dataset.county = JSON.stringify(data);
    return o;
  }

  // cache: 'no-store': results are per job and must never come from the HTTP
  // cache, and it keeps Chrome's per-URL cache lock from queueing a request
  // behind an earlier identical one (seen when /report-data is requested
  // the moment the progress stream closes).
  function getJSON(url, signal) {
    return fetch(url, { credentials: 'same-origin', cache: 'no-store', signal: signal }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (body) { return { status: r.status, body: body }; });
    });
  }

  // ---- Controls -----------------------------------------------------------

  function loadStates() {
    return getJSON(BASE + '/states').then(function (res) {
      var states = Array.isArray(res.body) ? res.body : (res.body.states || []);
      stateSel.replaceChildren(option('', 'Select a state'));
      states.forEach(function (s) { stateSel.appendChild(option(s.code || s.name, s.name)); });
    }).catch(function () {
      stateSel.replaceChildren(option('', 'States could not be loaded'));
    });
  }

  function loadCounties(stateCode) {
    countySel.disabled = true;
    countySel.replaceChildren(option('', stateCode ? 'Loading counties…' : 'Select a state first'));
    if (!stateCode) return Promise.resolve();
    return getJSON(BASE + '/counties-by-state/' + encodeURIComponent(stateCode)).then(function (res) {
      var counties = Array.isArray(res.body) ? res.body : [];
      countySel.replaceChildren(option('', 'Select a county'));
      counties.forEach(function (c) {
        if (typeof c === 'string') countySel.appendChild(option(c, c));
        else if (c && c.name) countySel.appendChild(option(c.name, c.name, c));
      });
      countySel.disabled = false;
    }).catch(function () {
      countySel.replaceChildren(option('', 'Counties could not be loaded'));
    });
  }

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

  function purposes() {
    return Array.prototype.map.call(form.querySelectorAll('input[name="loan_purpose"]:checked'), function (i) { return i.value; });
  }

  function validate() {
    var purposeBox = form.querySelector('input[name="loan_purpose"]');
    setInvalid(stateSel, stateSel.value ? '' : 'Choose a state.');
    setInvalid(countySel, countySel.value ? '' : 'Choose a county.');
    setInvalid(purposeBox, purposes().length ? '' : 'Choose at least one loan purpose.');
    var first = form.querySelector('.is-invalid select, .is-invalid input');
    if (first) { first.focus(); return false; }
    return true;
  }

  function requestBody() {
    var opt = countySel.options[countySel.selectedIndex];
    var c = opt && opt.dataset.county ? JSON.parse(opt.dataset.county) : { name: countySel.value };
    var refresh = $('lsForceRefresh');
    return {
      selection_type: 'county',
      state_code: stateSel.value,
      counties: countySel.value,
      counties_data: [{ name: c.name, geoid5: c.geoid5, state_fips: c.state_fips, county_fips: c.county_fips }],
      loan_purpose: purposes(),
      force_refresh: !!(refresh && refresh.checked)
    };
  }

  // ---- Run and results ----------------------------------------------------

  function setUrl(jobId) {
    var url = jobId ? BASE + '/report?job_id=' + encodeURIComponent(jobId) : BASE + '/';
    if (root.location.pathname + root.location.search !== url) root.history.replaceState(null, '', url);
  }

  function citationFor(metadata, jobId) {
    var span = root.LendSight.report.yearSpan(metadata.years);
    return {
      dataset: 'HMDA',
      years: span.text,
      geography: (metadata.counties || []).join('; '),
      url: root.location.origin + BASE + '/report?job_id=' + encodeURIComponent(jobId)
    };
  }

  /** Fetch a finished report; /report-data can briefly 404 or 202 after done. */
  function fetchReport(jobId, signal, attempt) {
    attempt = attempt || 0;
    return getJSON(BASE + '/report-data?job_id=' + encodeURIComponent(jobId), signal).then(function (res) {
      if (res.status === 200 && res.body.success) return res.body;
      if ((res.status === 202 || res.status === 404) && attempt < 8) {
        return new Promise(function (r) { setTimeout(r, 1000); }).then(function () { return fetchReport(jobId, signal, attempt + 1); });
      }
      var err = new Error(res.body.error || '');
      err.status = res.status;
      throw err;
    });
  }

  function showReport(jobId, body) {
    if (current !== jobId) return null;
    var node = $('lsReportTemplate').content.firstElementChild.cloneNode(true);
    root.AppStates.success(node, { citation: citationFor(body.metadata || {}, jobId) });
    $('resultsTitle').textContent = (body.metadata.counties || []).join('; ') || 'Results';
    return root.LendSight.report.display(body.data || {}, body.metadata || {}).catch(function (e) {
      root.AppStates.hint('Charts could not be drawn.');
      if (root.console) console.error(e);
    });
  }

  function failRun(message, ref) {
    if (message && message.indexOf(NO_DATA) === 0) {
      root.AppStates.empty('No loan originations match this county and loan purpose in ' +
        CFG.years[0] + ' to ' + CFG.years[CFG.years.length - 1] + '. Try another loan purpose or county.');
    } else {
      root.AppStates.error(message || null, ref);
    }
  }

  function loadReport(jobId, signal) {
    return fetchReport(jobId, signal).then(function (body) { return showReport(jobId, body); }, function (err) {
      if (err.name === 'AbortError' || current !== jobId) return;
      if (err.status === 404) {
        root.AppStates.error('This report is no longer available. Run the analysis again to rebuild it.', null);
        return;
      }
      var parts = root.AppProgress.splitRef(err.message);
      failRun(parts.message, parts.ref);
    });
  }

  function follow(jobId, signal) {
    root.AppProgress.follow(BASE + '/progress/' + encodeURIComponent(jobId), {
      signal: signal,
      onDone: function () { loadReport(jobId, signal); },
      onError: failRun
    });
  }

  function run() {
    if (!validate()) return;
    var signal = root.AppStates.loading();
    current = null;
    fetch(BASE + '/analyze', {
      method: 'POST', credentials: 'same-origin', signal: signal,
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody())
    }).then(function (r) { return r.json().catch(function () { return {}; }); }).then(function (res) {
      if (!res.success || !res.job_id) {
        var parts = root.AppProgress.splitRef(res.error);
        failRun(parts.message, parts.ref);
        return;
      }
      current = res.job_id;
      setUrl(res.job_id);
      if (res.cached) loadReport(res.job_id, signal);
      else follow(res.job_id, signal);
    }).catch(function (err) {
      if (err.name !== 'AbortError') root.AppStates.error(null, null);
    });
  }

  /** /report?job_id=: load a finished report, or follow it if still running. */
  function openJob(jobId) {
    current = jobId;
    var signal = root.AppStates.loading({ ref: jobId.slice(0, 8) });
    getJSON(BASE + '/report-data?job_id=' + encodeURIComponent(jobId), signal).then(function (res) {
      if (res.status === 200 && res.body.success) showReport(jobId, res.body);
      else if (res.status === 202) follow(jobId, signal);
      else if (res.status === 404 && res.body.progress && res.body.progress.error) {
        var parts = root.AppProgress.splitRef(res.body.progress.error);
        failRun(parts.message, parts.ref);
      } else root.AppStates.error('This report is no longer available. Run the analysis again to rebuild it.', null);
    }).catch(function (err) { if (err.name !== 'AbortError') root.AppStates.error(null, null); });
  }

  // ---- Wiring -------------------------------------------------------------

  form.addEventListener('submit', function (e) { e.preventDefault(); run(); });
  stateSel.addEventListener('change', function () { setInvalid(stateSel, ''); loadCounties(stateSel.value); });
  countySel.addEventListener('change', function () { setInvalid(countySel, ''); });
  form.addEventListener('change', function (e) {
    if (e.target.name === 'loan_purpose' && purposes().length) setInvalid(form.querySelector('input[name="loan_purpose"]'), '');
  });

  root.AppStates.on('export', function (kind) {
    if (!current) return;
    var format = { xlsx: 'excel', pdf: 'pdf' }[kind];
    if (format) root.location.href = BASE + '/download?format=' + format + '&job_id=' + encodeURIComponent(current);
  });
  root.AppStates.on('cancel', function () { current = null; setUrl(null); });
  root.AppStates.on('reset', function () {
    current = null;
    setUrl(null);
    Array.prototype.forEach.call(form.querySelectorAll('.is-invalid'), function (f) { f.classList.remove('is-invalid'); });
    Array.prototype.forEach.call(form.querySelectorAll('.app-field-error'), function (p) { p.hidden = true; });
    loadCounties('');
  });

  loadStates();
  if (CFG.jobId) openJob(CFG.jobId);
})(window);
