/**
 * LendSight page (spec 04 Part B): the LendSight-specific parts only. Run,
 * progress, report loading, exports and the shareable URL are AppRun;
 * states are AppStates.
 */
(function (root) {
  'use strict';

  var CFG = root.LENDSIGHT || {};
  var BASE = CFG.baseUrl || '/lendsight';
  var NO_DATA = 'No data found for the specified parameters';  // core.run_analysis
  var form = document.getElementById('lsForm');
  var geo = {
    state: document.getElementById('lsState'),
    county: document.getElementById('lsCounty'),
    statesUrl: BASE + '/states',
    countiesUrl: function (code) { return BASE + '/counties-by-state/' + encodeURIComponent(code); },
    stateValue: function (s) { return s.code || s.name; },
    countyValue: function (c) { return c.name; },
    countyLabel: function (c) { return c.name; }
  };
  var picker = root.AppRun.geoPicker(geo);

  function purposes() {
    return Array.prototype.map.call(form.querySelectorAll('input[name="loan_purpose"]:checked'), function (i) { return i.value; });
  }

  function validate() {
    var purposeBox = form.querySelector('input[name="loan_purpose"]');
    root.AppRun.setInvalid(geo.state, geo.state.value ? '' : 'Choose a state.');
    root.AppRun.setInvalid(geo.county, geo.county.value ? '' : 'Choose a county.');
    root.AppRun.setInvalid(purposeBox, purposes().length ? '' : 'Choose at least one loan purpose.');
    var first = form.querySelector('.is-invalid select, .is-invalid input');
    if (first) { first.focus(); return false; }
    return true;
  }

  function body() {
    var c = root.AppRun.selectedCounty(geo) || {};
    var refresh = document.getElementById('lsForceRefresh');
    return {
      selection_type: 'county',
      state_code: geo.state.value,
      counties: geo.county.value,
      counties_data: [{ name: c.name, geoid5: c.geoid5, state_fips: c.state_fips, county_fips: c.county_fips }],
      loan_purpose: purposes(),
      force_refresh: !!(refresh && refresh.checked)
    };
  }

  function render(jobId, res) {
    var metadata = res.metadata || {};
    var span = root.LendSight.report.yearSpan(metadata.years);
    var node = document.getElementById('lsReportTemplate').content.firstElementChild.cloneNode(true);
    root.AppStates.success(node, { citation: {
      dataset: 'HMDA', years: span.text,
      geography: (metadata.counties || []).join('; '),
      url: root.AppRun.reportUrl(jobId)
    } });
    document.getElementById('resultsTitle').textContent = (metadata.counties || []).join('; ') || 'Results';
    return root.LendSight.report.display(res.data || {}, metadata);
  }

  form.addEventListener('change', function (e) {
    if (e.target.name === 'loan_purpose' && purposes().length) {
      root.AppRun.setInvalid(form.querySelector('input[name="loan_purpose"]'), '');
    }
  });

  root.AppRun.init({
    baseUrl: BASE,
    jobId: CFG.jobId,
    form: form,
    validate: validate,
    body: body,
    render: render,
    emptyWhen: function (message) { return message.indexOf(NO_DATA) === 0; },
    emptyText: 'No loan originations match this county and loan purpose in ' +
      CFG.years[0] + ' to ' + CFG.years[CFG.years.length - 1] + '. Try another loan purpose or county.',
    exportFormats: { xlsx: 'excel', pdf: 'pdf' },
    onReset: function () { root.AppRun.clearInvalid(form); picker.reset(); }
  });
})(window);
