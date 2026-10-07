/**
 * BizSight report body (spec 04 Part B items 5 to 7): fills the cloned
 * #bsReportTemplate from /report-data. Ported from the former report page;
 * years come from the data rather than literals.
 *
 * Summary strip: latest-year loans, amount, average loan, amount to
 * businesses under $1M revenue and amount in LMI tracts, each with its
 * change since the first year computed from that year's actual figures.
 * (The former page estimated the first-year LMI amount by applying the
 * latest year's LMI share; with no first-year figure the change is omitted.)
 *
 * Chart colours: HHI series --ncrc-blue-500; thresholds moderate (1,500)
 * --ncrc-gold and high (2,500) --ncrc-red.
 */
(function (root) {
  'use strict';

  var R = root.AppReport;
  var esc = R.esc;

  function $(id) { return document.getElementById(id); }

  function num(v) { var n = parseFloat(v); return isNaN(n) ? null : n; }

  function fmtInt(v) { var n = num(v); return n === null ? '-' : Math.round(n).toLocaleString(); }
  function fmtPct(v, digits) { var n = num(v); return n === null ? '-' : n.toFixed(digits === undefined ? 1 : digits) + '%'; }
  /** amounts in thousands of dollars */
  function fmtThousands(v) { var n = num(v); return n === null ? '-' : '$' + Math.round(n).toLocaleString(); }
  function fmtDollars(v) {
    var n = num(v);
    if (n === null) return '-';
    if (Math.abs(n) >= 1e6) return '$' + (n / 1e6).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + 'M';
    return '$' + Math.round(n).toLocaleString();
  }

  function yearsOf(rows) {
    var keys = Object.keys(rows[0] || {}).filter(function (k) { return /^\d{4}$/.test(k); });
    return keys.sort();
  }

  function rowFor(rows, variable) {
    return (rows || []).filter(function (r) { return (r.Variable || r.variable) === variable; })[0];
  }

  function pctChange(now, then) {
    if (now === null || then === null || !then) return null;
    return (now - then) / then * 100;
  }

  function changeNote(change, firstYear) {
    if (change === null || isNaN(change)) return '';
    return (change >= 0 ? '+' : '') + change.toFixed(1) + '% since ' + firstYear;
  }

  // ---- Summary strip --------------------------------------------------------

  function summary(s, county, years) {
    var first = years[0], last = years[years.length - 1];
    function at(variable, year) { var r = rowFor(county, variable); return r ? num(r[year]) : null; }
    var loans = num(s.total_loans), amount = num(s.total_loan_amount);       // amount in thousands
    var loans0 = at('Total Loans', first), amount0 = at('Total Loan Amount (in millions)', first); // also thousands
    var avg = loans && amount !== null ? amount * 1000 / loans : null;
    var avg0 = loans0 && amount0 !== null ? amount0 * 1000 / loans0 : null;
    var sb = num(s.amtsb_under_1m);
    var sbPct0 = at('Amount to Businesses Under $1M Revenue (% of Total)', first);
    var sb0 = amount0 !== null && sbPct0 !== null ? amount0 * sbPct0 / 100 : null;
    var lmi = num(s.lmi_tract_amount);
    var lmiPct0 = at('Amount to LMI Tracts (% of Total)', first);
    var lmi0 = amount0 !== null && lmiPct0 !== null ? amount0 * lmiPct0 / 100 : null;

    var items = [
      { figure: fmtInt(loans), label: 'Small business loans, ' + last, note: changeNote(pctChange(loans, loans0), first) },
      { figure: fmtDollars(amount === null ? null : amount * 1000), label: 'Amount of loans, ' + last, note: changeNote(pctChange(amount, amount0), first) },
      { figure: fmtDollars(avg), label: 'Average loan amount, ' + last, note: changeNote(pctChange(avg, avg0), first) },
      { figure: fmtDollars(sb === null ? null : sb * 1000), label: 'To businesses under $1M revenue, ' + last, note: changeNote(pctChange(sb, sb0), first) },
      { figure: lmi ? fmtDollars(lmi * 1000) : '$0', label: 'In LMI tracts, ' + last,
        note: lmi ? changeNote(pctChange(lmi, lmi0), first) : 'No LMI tracts in county' }
    ];
    $('bsSummary').innerHTML = items.map(function (i) {
      return '<div><p class="app-summary-figure">' + esc(i.figure) + '</p><p class="app-summary-label">' + esc(i.label) + '</p>' +
        (i.note ? '<p class="app-summary-note">' + esc(i.note) + '</p>' : '') + '</div>';
    }).join('');
  }

  // ---- Section 1 ------------------------------------------------------------

  function intro(md, years) {
    var place = (md.county_name || 'the selected county') + (md.state_name && (md.county_name || '').indexOf(md.state_name) < 0 ? ', ' + md.state_name : '');
    Array.prototype.forEach.call(document.querySelectorAll('[data-bs="place"]'), function (el) { el.textContent = place; });
    $('bsIntro').innerHTML = [
      'This report analyzes small business lending in ' + place + ' from ' + years[0] + ' to ' + years[years.length - 1] + '. ' +
        'The data is collected under the Community Reinvestment Act (CRA), which requires financial institutions to report information about small business loans. ' +
        'Small business loans are defined as loans with original amounts of $1 million or less for commercial and industrial purposes.',
      'The analysis examines lending patterns by loan size, revenue category of borrowers, and neighborhood income levels. ' +
        'Low- and Moderate-Income (LMI) tracts are census tracts where the median family income is less than 80% of the area median income. ' +
        'Loans to businesses with revenues under $1 million are considered lending to small businesses.'
    ].map(function (t) { return '<p>' + esc(t) + '</p>'; }).join('');
  }

  // ---- Section 2: county summary -------------------------------------------

  /** "Total Loan Amount (in millions)" holds thousands; shown in millions as before. */
  function millions(v) {
    var n = num(v);
    return n === null ? '-' : '$' + (n / 1000).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  }

  function countyValue(variable, v) {
    if (variable.indexOf('%') >= 0) return fmtPct(v);
    if (variable === 'Total Loans') return fmtInt(v);
    if (variable.indexOf('Total Loan Amount') >= 0) return millions(v);
    return fmtInt(v);
  }

  function countyChange(variable, a, b) {
    a = num(a); b = num(b);
    if (a === null || b === null) return '-';
    if (variable.indexOf('%') >= 0) { var pp = b - a; return (pp >= 0 ? '+' : '') + pp.toFixed(2) + ' pp'; }
    if (!a) return '-';
    var pc = (b - a) / a * 100;
    return (pc >= 0 ? '+' : '') + pc.toFixed(1) + '%';
  }

  function countyTable(table, rows, years) {
    var first = years[0], last = years[years.length - 1];
    table.tHead.innerHTML = '<tr><th scope="col">Variable</th>' + years.map(function (y) { return '<th scope="col" class="num">' + y + '</th>'; }).join('') +
      '<th scope="col" class="num">Change (' + first + '→' + last + ')</th></tr>';
    table.tBodies[0].innerHTML = rows.map(function (r) {
      var v = r.Variable || r.variable || '';
      return '<tr><th scope="row">' + esc(v) + '</th>' + years.map(function (y) { return '<td class="num">' + esc(countyValue(v, r[y])) + '</td>'; }).join('') +
        '<td class="num">' + esc(countyChange(v, r[first], r[last])) + '</td></tr>';
    }).join('');
  }

  // ---- Section 3: comparison ------------------------------------------------

  function comparisonValue(metric, v) {
    if (metric.indexOf('%') >= 0) return fmtPct(v);
    if (metric === 'Total Loans') return fmtInt(v);
    if (metric.indexOf('Total Loan Amount') >= 0) { var n = num(v); return n === null ? '-' : fmtDollars(n * 1000); }
    return fmtInt(v);
  }

  function comparisonTable(table, rows) {
    if (!rows.length) return;
    var keys = Object.keys(rows[0]);
    var cols = ['County', 'State', 'National'].map(function (p) { return keys.filter(function (k) { return k.indexOf(p + ' (') === 0; })[0]; })
      .filter(Boolean);
    table.tHead.innerHTML = '<tr><th scope="col">Metric</th>' + cols.map(function (c) { return '<th scope="col" class="num">' + esc(c) + '</th>'; }).join('') + '</tr>';
    table.tBodies[0].innerHTML = rows.map(function (r) {
      var m = r.Metric || r.metric || '';
      return '<tr><th scope="row">' + esc(m) + '</th>' + cols.map(function (c) { return '<td class="num">' + esc(comparisonValue(m, r[c])) + '</td>'; }).join('') + '</tr>';
    }).join('');
  }

  // ---- Section 4: top lenders -----------------------------------------------

  var INCOME_COLS = [['Low', 'Low Income'], ['Mod', 'Moderate Income'], ['Mid', 'Middle Income'], ['Upper', 'Upper Income']];

  function lenderColumns(kind) {
    var n = kind === 'number';
    return [{ key: 'Lender Name', label: 'Lender' },
            { key: n ? 'Num Total' : 'Amt Total', label: n ? 'Total' : '$000s', numeric: true, format: n ? fmtInt : fmtThousands },
            { key: (n ? 'Num' : 'Amt') + ' Under 100K %', label: '<100K', numeric: true, format: fmtPct },
            { key: (n ? 'Num' : 'Amt') + ' 100K 250K %', label: '100-250K', numeric: true, format: fmtPct },
            { key: (n ? 'Num' : 'Amt') + ' 250K 1M %', label: '250K-1M', numeric: true, format: fmtPct },
            { key: n ? 'Numsb Under 1M %' : 'Amtsb Under 1M %', label: 'Sm Biz', numeric: true, format: fmtPct }]
      .concat(INCOME_COLS.map(function (c) {
        return { key: c[1] + (n ? ' %' : ' Amt %'), label: c[0], numeric: true, format: fmtPct };
      }));
  }

  // ---- Section 5: HHI ---------------------------------------------------------

  function hhi(rows) {
    var data = (rows || []).filter(function (d) { var y = parseFloat(d.year); return Math.abs(y - Math.round(y)) < 0.01; })
      .sort(function (a, b) { return a.year - b.year; });
    if (!data.length) return Promise.resolve();
    $('section5').hidden = false;
    var C = R.charts, blue = C.token('--ncrc-blue-500');
    var values = data.map(function (d) { return num(d.hhi_value) || 0; });
    return C.ready().then(function () {
      C.draw($('bsHhiChart'), {
        type: 'line',
        data: { labels: data.map(function (d) { return String(Math.round(d.year)); }),
                datasets: [{ label: 'HHI', data: values, borderColor: blue, backgroundColor: blue, tension: 0.2, pointRadius: 4 }] },
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
  function display(res, citation) {
    var md = res.metadata || {};
    var county = res.county_summary_table || [];
    var years = yearsOf(county);
    if (!years.length) years = (md.years || []).map(String);
    var first = years[0], last = years[years.length - 1];
    var place = md.county_name || 'the county';
    function fill(attr, value) {
      Array.prototype.forEach.call(document.querySelectorAll('[data-bs="' + attr + '"]'), function (el) { el.textContent = value; });
    }
    fill('first-year', first); fill('last-year', last); fill('latest-year', last);

    summary(res.summary_table || {}, county, years);
    intro(md, years);

    var numberRows = county.filter(function (r) { var v = r.Variable || ''; return v.indexOf('Loans') >= 0 && v.indexOf('Amount') < 0; });
    var amountRows = county.filter(function (r) { return (r.Variable || '').indexOf('Amount') >= 0; });
    countyTable($('bsCountyNumberTable'), numberRows, years);
    countyTable($('bsCountyAmountTable'), amountRows, years);
    $('bsCountyNumberIntro').textContent = 'Table 1 presents the number of small business loans originated in ' + place + ' from ' + first + '-' + last + '. The data is broken down by loan size category and shows lending to businesses with revenue under $1 million. The rightmost column shows the percentage change comparing ' + last + ' to the ' + first + ' baseline.';
    $('bsCountyAmountIntro').textContent = 'Table 2 shows the dollar amount of small business loans (in thousands) originated in ' + place + ' from ' + first + '-' + last + '. The breakdown by loan size category reveals patterns in how lending volume is distributed. Note that 2020 and 2021 data may be influenced by Paycheck Protection Program (PPP) lending activity.';

    var comp = res.comparison_table || [];
    comparisonTable($('bsComparisonNumberTable'), comp.filter(function (r) { return (r.Metric || '').indexOf('Amount') < 0; }));
    comparisonTable($('bsComparisonAmountTable'), comp.filter(function (r) { return (r.Metric || '').indexOf('Amount') >= 0; }));
    $('bsComparisonNumberIntro').textContent = 'Table 1 compares the number of small business loans in ' + place + ' with state (' + (md.state_name || 'statewide') + ') and national benchmarks for ' + last + '. This comparison helps identify whether local lending patterns are consistent with broader trends or represent unique local market conditions.';
    $('bsComparisonAmountIntro').textContent = 'Table 2 compares the dollar amount of small business lending in ' + place + ' with state and national figures for ' + last + '. Loan amounts (in thousands) reveal how local lending volume compares to broader geographic benchmarks.';

    var lenders = res.top_lenders_table || [];
    var byLoans = function (a, b) { return (num(b['Num Total']) || 0) - (num(a['Num Total']) || 0); };
    R.sortableTable($('bsLendersNumberTable'), lenders, lenderColumns('number'), { topN: 10, expandButton: $('bsLendersNumberExpand'), defaultSort: byLoans });
    R.sortableTable($('bsLendersAmountTable'), lenders, lenderColumns('amount'), { topN: 10, expandButton: $('bsLendersAmountExpand'),
      defaultSort: function (a, b) { return (num(b['Amt Total']) || 0) - (num(a['Amt Total']) || 0); } });
    $('bsLendersNumberIntro').textContent = 'Table 1 ranks the top ' + Math.min(lenders.length, 10) + ' small business lenders in ' + place + ' by number of loans originated in ' + last + '. The table shows each lender\'s total loan count and the percentage distribution across loan size categories. The Small Biz column indicates the share of loans going to businesses with under $1 million in revenue.';
    $('bsLendersAmountIntro').textContent = 'Table 2 shows the same top lenders ranked by loan amounts (in thousands of dollars) for ' + last + '. Comparing this table to Table 1 reveals differences in lending patterns - some lenders may originate many small loans while others focus on fewer, larger transactions.';

    var ai = res.ai_insights || {};
    R.narrative($('bsCountyNumberNarrative'), ai.county_summary_number_discussion, true);
    R.narrative($('bsCountyAmountNarrative'), ai.county_summary_amount_discussion, true);
    R.narrative($('bsComparisonNumberNarrative'), ai.comparison_number_discussion, true);
    R.narrative($('bsComparisonAmountNarrative'), ai.comparison_amount_discussion, true);
    R.narrative($('bsLendersNumberNarrative'), ai.top_lenders_number_discussion, true);
    R.narrative($('bsLendersAmountNarrative'), ai.top_lenders_amount_discussion, true);
    R.narrative($('bsHhiNarrative'), ai.hhi_trends_discussion, true);

    $('bsCitation').textContent = root.AppStates.formatCitation('BizSight', citation);
    return hhi(res.hhi_by_year);
  }

  root.BizSight = root.BizSight || {};
  root.BizSight.report = { display: display, yearsOf: yearsOf };
})(window);
