/**
 * MergerMeter page (spec 04 Part B): the MergerMeter-specific parts only. Run,
 * progress, report loading, export and the shareable URL are AppRun.
 *
 * The body posted to /analyze is a FormData with exactly the fields and
 * values the former page sent, so the analysis and its cache key are the
 * same: identifiers and names, assessment areas as JSON, the year, loan
 * purpose and peer group selections, and the HMDA filters as comma-joined
 * codes in option order.
 */
(function (root) {
  'use strict';

  var CFG = root.MERGERMETER || {};
  var BASE = CFG.baseUrl || '/mergermeter';
  var MAX_RUN_S = 1800;  // runs normally take 5 to 10 minutes; the former page had no limit
  var FILTERS = ['action_taken', 'occupancy_type', 'total_units', 'construction_method', 'not_reverse'];
  var YEAR_FIELDS = ['hmda_start_year', 'hmda_end_year', 'sb_start_year', 'sb_end_year',
                     'baseline_hmda_start_year', 'baseline_hmda_end_year', 'baseline_sb_start_year', 'baseline_sb_end_year'];
  var MM = root.MergerMeter;
  var form = document.getElementById('mmForm');
  var single = document.getElementById('mmSingleBank');
  var national = document.getElementById('mmNational');

  function $(id) { return document.getElementById(id); }

  function singleMode() { return single.checked; }

  function syncSingle() {
    var on = singleMode();
    $('targetBank').hidden = on;
    $('targetAreas').hidden = on;
    if (on) MM.banks.clear('target');  // the former page cleared Bank B
  }

  function syncNational() {
    $('mmAreaInputs').hidden = national.checked;
  }

  function filterValue(name) {
    return Array.prototype.filter.call($(name).querySelectorAll('input[type="checkbox"]'), function (b) { return b.checked; })
      .map(function (b) { return b.value; }).join(',');
  }

  function areaNote(bank, message) {
    var panel = $(bank + 'Areas');
    var note = panel.querySelector('.app-field-error');
    if (!note) {
      note = document.createElement('p');
      note.className = 'app-field-error';
      panel.insertBefore(note, panel.children[1]);
    }
    note.textContent = message || '';
    note.hidden = !message;
  }

  function validate() {
    root.AppRun.clearInvalid(form);
    areaNote('acquirer', '');
    areaNote('target', '');
    var problems = [];
    var banks = singleMode() ? ['acquirer'] : ['acquirer', 'target'];
    banks.forEach(function (bank) {
      var v = MM.banks.value(bank);
      var label = bank === 'acquirer' ? 'acquirer' : 'target';
      var input = MM.banks.input(bank);
      if (!v.name) {
        $(bank + 'SearchField').hidden = false;
        root.AppRun.setInvalid(input, 'Search for and select the ' + label + '.');
        problems.push(input);
      } else if (v.lei.replace(/\s+/g, '').length !== 20) {
        root.AppRun.setInvalid($(bank + '_lei'), 'Enter the ' + label + "'s 20-character LEI.");
        problems.push($(bank + '_lei'));
      }
    });
    if (!national.checked) {
      banks.forEach(function (bank) {
        if (!MM.areas.collect(bank).length) {
          areaNote(bank, 'Add, upload or generate assessment areas for the ' + bank + ', or use national data.');
          problems.push($(bank + 'Areas'));
        }
      });
    }
    FILTERS.forEach(function (name) {
      if (!filterValue(name)) {
        var box = $(name).querySelector('input');
        root.AppRun.setInvalid(box, 'Choose at least one.');
        problems.push(box);
      }
    });
    if (problems.length) {
      var first = problems[0];
      (first.matches('input, select, textarea') ? first : first.querySelector('input, button') || first).focus();
      root.AppStates.hint('Check the highlighted steps.');
      return false;
    }
    root.AppStates.hint('');
    return true;
  }

  function body() {
    var data = new FormData();
    var on = singleMode();
    var a = MM.banks.value('acquirer');
    var t = on ? { name: '', lei: '', rssd: '', sbId: '' } : MM.banks.value('target');
    data.append('acquirer_lei', a.lei);
    data.append('acquirer_rssd', a.rssd);
    data.append('acquirer_sb_id', a.sbId);
    data.append('target_lei', t.lei);
    data.append('target_rssd', t.rssd);
    data.append('target_sb_id', t.sbId);
    data.append('acquirer_name', a.name);
    data.append('target_name', on ? '' : t.name);
    data.append('single_bank_mode', on ? '1' : '0');
    data.append('use_national_data', national.checked ? '1' : '0');
    data.append('acquirer_assessment_areas', JSON.stringify(national.checked ? [] : MM.areas.collect('acquirer')));
    data.append('target_assessment_areas', JSON.stringify(national.checked || on ? [] : MM.areas.collect('target')));
    data.append('loan_purpose', $('loan_purpose').value || '');
    data.append('peer_group', $('peer_group').value || 'volume_50_200');
    FILTERS.forEach(function (name) { data.append(name, filterValue(name)); });
    YEAR_FIELDS.forEach(function (name) { data.append(name, $(name).value); });
    var refresh = $('mmForceRefresh');
    if (refresh && refresh.checked) data.append('force_refresh', '1');
    return data;
  }

  function render(jobId, res) {
    var md = res.metadata || {};
    var names = [md.acquirer_name, md.target_name].filter(Boolean);
    var node = $('mmReportTemplate').content.firstElementChild.cloneNode(true);
    root.AppStates.success(node, { citation: {
      dataset: 'HMDA, CRA small business and FDIC Summary of Deposits',
      years: MM.report.yearsText(md),
      geography: md.use_national_data ? 'National' : 'Assessment areas',
      lenders: names.join(' and '),
      url: root.AppRun.reportUrl(jobId)
    } });
    $('resultsTitle').textContent = names.join(' + ') || 'Results';
    // The controls column is long; bring the results into view if they are
    // above the screen (the Run button is at the bottom of the controls).
    var results = $('results');
    if (results.getBoundingClientRect().top < 0) results.scrollIntoView({ block: 'start' });
    return MM.report.show(jobId, md);
  }

  single.addEventListener('change', syncSingle);
  national.addEventListener('change', syncNational);
  form.addEventListener('change', function (e) {
    if (e.target.closest('.mm-filter')) root.AppRun.setInvalid(e.target, '');
  });

  root.AppRun.init({
    baseUrl: BASE,
    jobId: CFG.jobId,
    form: form,
    validate: validate,
    body: body,
    render: render,
    maxRunSeconds: MAX_RUN_S,
    exportFormats: { xlsx: 'excel' },
    onReset: function () {
      root.AppRun.clearInvalid(form);
      MM.banks.clear('acquirer');
      MM.banks.clear('target');
      MM.areas.reset();
      single.checked = false;
      national.checked = false;
      syncSingle();
      syncNational();
    }
  });
  syncSingle();
  syncNational();
})(window);
