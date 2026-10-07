/**
 * BranchSight report body (spec 04 Part B items 5 to 7): fills the cloned
 * #brReportTemplate from /report-data. Ported from the former report page;
 * years come from the data rather than literals.
 *
 * Summary strip: latest-year total, LMI only, MMCT only and both, from
 * Table 1's latest column, each with its net change since the first year.
 *
 * Geography Context: tract counts and population from /geography-context
 * (Census ACS 5-year, data_utils.tract_context). The former page called the
 * Census API from the browser without a key, which the API now refuses, so
 * the section never showed. The county comes from the branch rows' geoid5.
 *
 * Chart colours: HHI bars --ncrc-blue-500; thresholds moderate (1,500)
 * --ncrc-gold and high (2,500) --ncrc-red.
 */
(function (root) {
  'use strict';

  var R = root.AppReport;
  var esc = R.esc;
  function BASE() { return (root.BRANCHSIGHT || {}).baseUrl || '/branchsight'; }

  function $(id) { return document.getElementById(id); }
  function num(v) { return v === null || v === undefined || v === '' ? null : R.sortNumber(v); }
  function fmtInt(v) { var n = num(v); return n === null ? '-' : Math.round(n).toLocaleString(); }
  function signed(v) {
    var n = num(v);
    if (n === null) return '-';
    return (n > 0 ? '+' : '') + Math.round(n).toLocaleString();
  }
  function trendClass(v) { var n = num(v); return n > 0 ? ' br-up' : n < 0 ? ' br-down' : ''; }

  function fill(attr, value) {
    Array.prototype.forEach.call(document.querySelectorAll('[data-br="' + attr + '"]'), function (el) { el.textContent = value; });
  }

  function yearsOf(rows) {
    return Object.keys(rows[0] || {}).filter(function (k) { return /^\d{4}$/.test(k); }).sort();
  }

  function rowFor(rows, variable) {
    return (rows || []).filter(function (r) { return r.Variable === variable; })[0];
  }

  // ---- Summary strip --------------------------------------------------------

  var CATEGORIES = [['Total Branches', 'Branches'], ['LMI Only Branches', 'LMI only'],
                    ['MMCT Only Branches', 'MMCT only'], ['Both LMICT/MMCT Branches', 'Both LMICT and MMCT']];

  function summary(rows, years) {
    var first = years[0], last = years[years.length - 1];
    var total = num((rowFor(rows, 'Total Branches') || {})[last]);
    $('brSummary').innerHTML = CATEGORIES.map(function (c, i) {
      var r = rowFor(rows, c[0]);
      if (!r) return '';
      var n = num(r[last]);
      var share = i && total ? ' (' + (n / total * 100).toFixed(1) + '%)' : '';
      return '<div><p class="app-summary-figure">' + esc(fmtInt(n)) + '</p>' +
        '<p class="app-summary-label">' + esc(c[1] + ', ' + last + share) + '</p>' +
        '<p class="app-summary-note">' + esc(signed(r['Net Change']) + ' since ' + first) + '</p></div>';
    }).join('');
  }

  // ---- Executive summary ----------------------------------------------------

  function executiveSummary(place, years) {
    var first = years[0], last = years[years.length - 1];
    $('brExecutiveSummary').innerHTML = '<p>' + esc(
      'This report provides an analysis of bank branch locations and distribution patterns in ' + place + '. ' +
      'The analysis covers the period from ' + first + ' through ' + last + ' and examines branch distribution patterns, ' +
      'including the location of branches in Low-to-Moderate Income (LMI) census tracts and Majority-Minority Census Tracts (MMCT). ' +
      'The data for this report comes from the Federal Deposit Insurance Corporation (FDIC) Summary of Deposits (SOD), ' +
      'which is compiled annually by the FDIC and maintained in NCRC\'s curated databases. ' +
      'The report presents data in tables showing yearly breakdowns and analysis by bank.') + '</p>';
    $('brCensusNote').hidden = !(years.indexOf('2021') >= 0 && years.indexOf('2022') >= 0);
  }

  // ---- Geography context (Census ACS) --------------------------------------

  function geography(geoid5) {
    if (!/^\d{5}$/.test(geoid5 || '')) return Promise.resolve();
    return root.AppRun.getJSON(BASE() + '/geography-context/' + geoid5).then(function (res) {
      if (res.status !== 200 || !res.body.groups) throw new Error('no context');
      var g = res.body.groups, totalPop = g.all.population;
      var rows = [['All census tracts', 'all'], ['LMI tracts, majority white', 'lmi_only'],
                  ['Majority-minority tracts, middle or upper income', 'mmct_only'], ['Both LMI and majority-minority', 'both']];
      $('brGeographyTable').tBodies[0].innerHTML = rows.map(function (r) {
        var x = g[r[1]];
        return '<tr><th scope="row">' + esc(r[0]) + '</th><td class="num">' + x.tracts.toLocaleString() + '</td><td class="num">' +
          x.population.toLocaleString() + '</td><td class="num">' + (totalPop ? (x.population / totalPop * 100).toFixed(1) + '%' : '-') + '</td></tr>';
      }).join('');
      var y = res.body.acs_year;
      $('brGeographyCaption').textContent = 'Source: U.S. Census Bureau, ' + (y - 4) + '-' + y + ' American Community Survey 5-Year Estimates. ' +
        'LMI tracts are those with median family income at or below 80% of the county median ($' + Math.round(res.body.lmi_threshold).toLocaleString() + '). ' +
        'Majority-minority tracts are those where people other than non-Hispanic white residents are more than 50% of the population. Tracts with no population are left out.';
      $('brGeography').hidden = false;
    }).catch(function () { $('brGeography').hidden = true; });
  }

  // ---- Section 1: yearly breakdown -----------------------------------------

  function summaryTable(rows, years, place) {
    var first = years[0], last = years[years.length - 1];
    var table = $('brSummaryTable');
    table.tHead.innerHTML = '<tr><th scope="col">Variable</th>' + years.map(function (y) { return '<th scope="col" class="num">' + y + '</th>'; }).join('') +
      '<th scope="col" class="num">Net Change</th></tr>';
    table.tBodies[0].innerHTML = rows.map(function (r) {
      return '<tr><th scope="row">' + esc(r.Variable) + '</th>' + years.map(function (y) { return '<td class="num">' + esc(fmtInt(r[y])) + '</td>'; }).join('') +
        '<td class="num' + trendClass(r['Net Change']) + '">' + esc(signed(r['Net Change'])) + '</td></tr>';
    }).join('');
    $('brSummaryIntro').innerHTML = '<p>' + esc(
      'This table presents the yearly summary of bank branch activity in ' + place + ' from ' + first + ' to ' + last + '. ' +
      'The data shows total branch counts, as well as branches located in Low-to-Moderate Income (LMI) census tracts, ' +
      'Majority-Minority Census Tracts (MMCT), and tracts that qualify as both.') + '</p><p>' + esc(
      'The Net Change column shows the difference between the first and last year of the analysis period, ' +
      'helping identify overall trends in branch presence across different community types.') + '</p>';
    $('brSummaryCaption').textContent = 'Source: FDIC Summary of Deposits. County: ' + place + '. Years: ' + first + '-' + last + '.';
  }

  // ---- Section 2: bank networks ---------------------------------------------

  function bankTable(rows, years, place) {
    var first = years[0], last = years[years.length - 1];
    var columns = [
      { key: 'Bank Name', label: 'Bank' },
      { key: 'Total Branches', label: 'Branches', numeric: true, format: fmtInt },
      { key: 'Deposits ($ Millions)', label: 'Deposits ($M)', numeric: true, format: fmtInt },
      { key: 'LMI Only Branches', label: 'LMI only', numeric: true },
      { key: 'MMCT Only Branches', label: 'MMCT only', numeric: true },
      { key: 'Both LMICT/MMCT Branches', label: 'Both', numeric: true },
      { key: 'Net Change', label: 'Net change', numeric: true, format: signed }
    ];
    R.sortableTable($('brBankTable'), rows, columns, {
      topN: 10, expandButton: $('brBankExpand'),
      labels: { more: 'Show all banks', fewer: 'Show top 10 only' },
      defaultSort: function (a, b) { return num(b['Total Branches']) - num(a['Total Branches']); }
    });
    $('brBankIntro').innerHTML = '<p>' + esc(
      'This table shows the top bank networks by branch count in ' + place + ', ranked by total branches in the most recent year (' + last + '). ' +
      'The table includes branch distribution across LMI and majority-minority census tracts, as well as net changes over the analysis period.') +
      '</p><p><strong>Note on significant changes:</strong> ' + esc(
      'Large changes in branch counts may reflect mergers, acquisitions, divestitures, or branch network restructuring rather than organic growth or decline. ' +
      'Researchers should consult FDIC merger records for the ' + first + ' to ' + last + ' period to identify specific transactions that may have affected these figures.') + '</p>';
    $('brBankCaption').textContent = 'Source: FDIC Summary of Deposits. Year: ' + last + ' (most recent year in report). ' +
      'Deposits in millions of dollars. LMI only, MMCT only and Both show branches and their share of the bank\'s branches; ' +
      'Both means tracts that are LMI and majority-minority. Net change is ' + first + ' to ' + last + '.';
  }

  // ---- Section 3: HHI -------------------------------------------------------

  function hhi(rows) {
    var data = (rows || []).slice().sort(function (a, b) { return a.year - b.year; });
    if (!data.length) return Promise.resolve();
    $('brSection3').hidden = false;
    var C = R.charts, blue = C.token('--ncrc-blue-500');
    var values = data.map(function (d) { return num(d.hhi_value) || 0; });
    return C.ready().then(function () {
      C.draw($('brHhiChart'), {
        type: 'bar',
        data: { labels: data.map(function (d) { return String(d.year); }),
                datasets: [{ label: 'HHI', data: values, backgroundColor: blue, borderColor: blue, borderWidth: 1 }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: function (ctx) { return 'HHI: ' + Math.round(ctx.parsed.y).toLocaleString(); } } },
            annotation: C.thresholds([
              { value: 1500, label: 'Moderate (1,500)', color: C.token('--ncrc-gold') },
              { value: 2500, label: 'High (2,500)', color: C.token('--ncrc-red') }
            ])
          },
          scales: { y: { beginAtZero: true, max: Math.max(Math.max.apply(null, values.concat([2500])) * 1.15, 3000),
                         title: { display: true, text: 'HHI' }, ticks: { callback: function (v) { return v.toLocaleString(); } } },
                    x: { title: { display: true, text: 'Year' } } }
        }
      });
    });
  }

  /** Fill the cloned report; returns a promise that settles when the chart is drawn. */
  function display(data, md) {
    var rows = data.summary || [];
    var years = yearsOf(rows);
    if (!years.length) years = (md.years || []).map(String).sort();
    var place = (md.counties || []).join('; ') || 'the selected county';
    fill('place', place);

    summary(rows, years);
    executiveSummary(place, years);
    summaryTable(rows, years, place);
    bankTable(data.by_bank || [], years, place);

    var ai = md.ai_insights || {};
    var tn = ai.table_narratives || {};
    R.narrative($('brKeyFindings'), ai.key_findings, true);
    R.narrative($('brSummaryNarrative'), tn.table1, rows.length > 0);
    R.narrative($('brBankNarrative'), tn.table2, (data.by_bank || []).length > 0);
    R.narrative($('brHhiNarrative'), ai.hhi_trends_discussion || ai.market_concentration_discussion, (data.hhi_by_year || []).length > 0);

    var raw = data.raw_data || [];
    geography(raw.length ? String(raw[0].geoid5 || '') : '');
    return hhi(data.hhi_by_year);
  }

  root.BranchSight = root.BranchSight || {};
  root.BranchSight.report = { display: display, yearsOf: yearsOf };
})(window);
