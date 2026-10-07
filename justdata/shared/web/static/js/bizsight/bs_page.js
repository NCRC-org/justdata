/**
 * BizSight page (spec 04 Part B): the BizSight-specific parts only. Run,
 * progress, report loading, exports and the shareable URL are AppRun.
 */
(function (root) {
  'use strict';

  var CFG = root.BIZSIGHT || {};
  var BASE = CFG.baseUrl || '/bizsight';
  var NO_DATA = 'No small business lending data found';  // core.run_analysis
  var form = document.getElementById('bsForm');
  var geo = {
    state: document.getElementById('bsState'),
    county: document.getElementById('bsCounty'),
    statesUrl: BASE + '/api/states',
    countiesUrl: function (code) { return BASE + '/api/counties-by-state/' + encodeURIComponent(code); },
    stateValue: function (s) { return s.fips || s.code; },
    countyValue: function (c) { return c.geoid5 || c.name; },
    countyLabel: function (c) { return (c.county_name || c.name) + (c.state_name ? ', ' + c.state_name : ''); }
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
    var county = root.AppRun.selectedCounty(geo) || {};
    if (!county.geoid5 && county.state_fips && county.county_fips) {
      county.geoid5 = (county.state_fips + county.county_fips).padStart(5, '0');
    }
    var refresh = document.getElementById('bsForceRefresh');
    return { county_data: county, force_refresh: !!(refresh && refresh.checked) };
  }

  function render(jobId, res) {
    var md = res.metadata || {};
    var years = root.BizSight.report.yearsOf(res.county_summary_table || []);
    if (!years.length) years = (md.years || []).map(String);
    var citation = {
      dataset: 'CRA small business',
      years: years.length ? years[0] + ' to ' + years[years.length - 1] : '',
      geography: md.county_name,
      url: root.AppRun.reportUrl(jobId)
    };
    var node = document.getElementById('bsReportTemplate').content.firstElementChild.cloneNode(true);
    root.AppStates.success(node, { citation: citation });
    document.getElementById('resultsTitle').textContent = md.county_name || 'Results';
    return root.BizSight.report.display(res, citation);
  }

  root.AppRun.init({
    baseUrl: BASE,
    jobId: CFG.jobId,
    form: form,
    validate: validate,
    body: body,
    render: render,
    emptyWhen: function (message) { return message.indexOf(NO_DATA) === 0; },
    emptyText: 'No CRA small business lending is reported for this county in ' +
      CFG.years[0] + ' to ' + CFG.years[CFG.years.length - 1] + '. Try another county.',
    exportFormats: { xlsx: 'excel', pdf: 'pdf' },
    onReset: function () { root.AppRun.clearInvalid(form); picker.reset(); }
  });
})(window);
