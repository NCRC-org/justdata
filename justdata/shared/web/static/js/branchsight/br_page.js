/**
 * BranchSight page (spec 04 Part B): the BranchSight-specific parts only. Run,
 * progress, report loading, exports and the shareable URL are AppRun.
 */
(function (root) {
  'use strict';

  var CFG = root.BRANCHSIGHT || {};
  var BASE = CFG.baseUrl || '/branchsight';
  var NO_DATA = 'No data found for the specified parameters';  // core.run_analysis
  var form = document.getElementById('brForm');
  var geo = {
    state: document.getElementById('brState'),
    county: document.getElementById('brCounty'),
    statesUrl: BASE + '/states',
    countiesUrl: function (code) { return BASE + '/counties-by-state/' + encodeURIComponent(code); },
    stateValue: function (s) { return s.code || s.name; },   // the state name: /states uses names as codes
    countyValue: function (c) { return c.name; },             // exact county_state
    countyLabel: function (c) { return c.county_name || c.name; }
  };
  var picker = root.AppRun.geoPicker(geo);

  function validate() {
    root.AppRun.setInvalid(geo.state, geo.state.value ? '' : 'Choose a state.');
    root.AppRun.setInvalid(geo.county, geo.county.value ? '' : 'Choose a county.');
    var first = form.querySelector('.is-invalid select');
    if (first) { first.focus(); return false; }
    return true;
  }

  function body() {
    var refresh = document.getElementById('brForceRefresh');
    return {
      selection_type: 'county',
      state_code: geo.state.value,
      counties: geo.county.value,
      force_refresh: !!(refresh && refresh.checked)
    };
  }

  function render(jobId, res) {
    var md = res.metadata || {};
    var data = res.data || {};
    var years = root.BranchSight.report.yearsOf(data.summary || []);
    if (!years.length) years = (md.years || []).map(String).sort();
    var node = document.getElementById('brReportTemplate').content.firstElementChild.cloneNode(true);
    root.AppStates.success(node, { citation: {
      dataset: 'FDIC Summary of Deposits',
      years: years.length ? years[0] + ' to ' + years[years.length - 1] : '',
      geography: (md.counties || []).join('; '),
      url: root.AppRun.reportUrl(jobId)
    } });
    document.getElementById('resultsTitle').textContent = (md.counties || []).join('; ') || 'Results';
    return root.BranchSight.report.display(data, md);
  }

  root.AppRun.init({
    baseUrl: BASE,
    jobId: CFG.jobId,
    form: form,
    validate: validate,
    body: body,
    render: render,
    emptyWhen: function (message) { return message.indexOf(NO_DATA) === 0; },
    emptyText: 'No bank branches are reported for this county in ' +
      CFG.years[0] + ' to ' + CFG.years[CFG.years.length - 1] + '. Try another county.',
    exportFormats: { xlsx: 'excel', pdf: 'pdf' },
    onReset: function () { root.AppRun.clearInvalid(form); picker.reset(); }
  });
})(window);
