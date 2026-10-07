/**
 * LendSight report body (spec 04 Part B items 5 to 7): fills the cloned
 * #lsReportTemplate from /report-data. Ported from the former report page;
 * wording is unchanged except where noted in the PR. AI narrative is escaped
 * before its light markdown (bold, links, bullets) is turned into HTML.
 */
(function (root) {
  'use strict';

  var T = root.LendSight.tables;
  var esc = T.esc;

  var PURPOSE_NAMES = {
    purchase: 'home purchase loans',
    refinance: 'refinance and cash-out refinance loans',
    equity: 'home equity lending'
  };
  var PURPOSE_CODES = {
    purchase: 'home purchase loans (loan purpose = 1)',
    refinance: 'refinance and cash-out refinance loans (loan purpose IN (31, 32))',
    equity: 'home equity lending (loan purpose IN (2, 4))'
  };
  var PURPOSE_ROWS = { purchase: 'Home Purchase', refinance: 'Refinance', equity: 'Home Equity' };

  function $(id) { return document.getElementById(id); }

  function list(items) {
    if (items.length < 2) return items.join('');
    if (items.length === 2) return items[0] + ' and ' + items[1];
    return items.slice(0, -1).join(', ') + ', and ' + items[items.length - 1];
  }

  function purposes(metadata) {
    var p = metadata.loan_purpose;
    p = (Array.isArray(p) ? p : [p || 'purchase']).filter(function (x) { return x && x !== 'all'; });
    var all = !p.length || ['purchase', 'refinance', 'equity'].every(function (x) { return p.indexOf(x) >= 0; });
    return { selected: p, all: all };
  }

  function yearSpan(years) {
    var ys = (years || []).map(Number).sort(function (a, b) { return a - b; });
    return { first: ys[0], last: ys[ys.length - 1], text: ys.length > 1 ? ys[0] + ' to ' + ys[ys.length - 1] : String(ys[0] || '') };
  }

  /** "**bold**", "[text](url)" and "•" bullets; everything else is text. */
  function formatNarrative(content) {
    return String(content || '').split('\n\n').map(function (para) {
      var lines = para.split('\n').filter(function (l) { return l.trim() && l.trim().indexOf('##') !== 0; });
      if (!lines.length) return '';
      var html = '', inList = false;
      lines.forEach(function (line) {
        var t = esc(line.trim())
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
        if (t.charAt(0) === '•') {
          if (!inList) { html += '<ul>'; inList = true; }
          html += '<li>' + t.slice(1).trim() + '</li>';
        } else {
          if (inList) { html += '</ul>'; inList = false; }
          html += '<p>' + t + '</p>';
        }
      });
      return html + (inList ? '</ul>' : '');
    }).join('');
  }

  /**
   * Fill one narrative slot. With text: the narrative and its "AI generated"
   * caption. Without: an expected slot shows AppStates.NARRATIVE_MISSING
   * (no caption, since nothing was generated); an optional slot stays hidden.
   */
  function narrative(id, text, expected) {
    var block = $(id);
    if (!block) return;
    var target = block.querySelector('[data-ls="text"]');
    var caption = block.querySelector('.ls-ai-caption');
    if (text) {
      target.innerHTML = formatNarrative(text);
      caption.hidden = false;
    } else if (expected) {
      target.innerHTML = '<p class="app-narrative-missing">' + esc(root.AppStates.NARRATIVE_MISSING) + '</p>';
      caption.hidden = true;
    } else {
      block.hidden = true;
      return;
    }
    block.hidden = false;
  }

  function intro(metadata, span, p) {
    var counties = metadata.counties || [];
    var what = p.all
      ? 'all loan purposes (home purchase loans, refinance and cash-out refinance loans, and home equity lending)'
      : list(p.selected.map(function (x) { return PURPOSE_NAMES[x] || x; }));
    $('lsIntro').innerHTML = '<p>' + esc('This report examines ' + what + ' in ' + list(counties) + ' from ' + span.text + '. ' +
      'The analysis includes only loans that were completed (originations) for owner-occupied properties, which means homes where the borrower actually lives rather than investment properties. ' +
      'The data is filtered to include only site-built homes (traditional homes constructed on-site, not manufactured or mobile homes), forward mortgages (regular mortgages where the borrower makes payments to the bank, not reverse mortgages where the bank pays the homeowner), and properties with 1-4 units (single-family homes, duplexes, triplexes, and four-unit buildings).') + '</p>';
  }

  /** Latest-year figures read from the report's own tables (no new statistics). */
  function summary(data, span) {
    var latest = String(span.last);
    function find(rows, test) { return (rows || []).filter(function (r) { return test(String(r.Metric || '')); })[0]; }
    var items = [];
    var total = find(data.demographic_overview, function (m) { return m === 'Total Loans'; });
    if (total && total[latest] !== undefined) {
      var change = Object.keys(total).filter(function (c) { return c.indexOf('Change') === 0; })[0];
      items.push({ figure: total[latest], label: 'Loan originations, ' + latest,
                   note: change && total[change] ? 'Change since ' + span.first + ': ' + total[change] : '' });
    }
    var lmib = find(data.income_borrowers, function (m) { return /Low[- ]to[- ]Moderate/.test(m); });
    if (lmib && lmib[latest] !== undefined) items.push({ figure: lmib[latest], label: 'To low- and moderate-income borrowers, ' + latest });
    var lmict = find(data.income_tracts, function (m) { return /Low[- ]to[- ]Moderate/.test(m); });
    if (lmict && lmict[latest] !== undefined) items.push({ figure: lmict[latest], label: 'In low- and moderate-income tracts, ' + latest });
    var mmct = find(data.minority_tracts, function (m) { return /Majority Minority/.test(m); });
    if (mmct && mmct[latest] !== undefined) items.push({ figure: mmct[latest], label: 'In majority-minority tracts, ' + latest });
    var box = $('lsSummary');
    box.innerHTML = items.map(function (i) {
      return '<div><p class="app-summary-figure">' + esc(i.figure) + '</p><p class="app-summary-label">' + esc(i.label) + '</p>' +
        (i.note ? '<p class="app-summary-note">' + esc(i.note) + '</p>' : '') + '</div>';
    }).join('');
    box.hidden = !items.length;
  }

  function tables(data, metadata, span) {
    $('lsDemographicIntro').textContent = 'This table shows lending activity by race and ethnicity over the time period ' + span.text + ', including the number and percentage of loans to each race and ethnic group. Percentages are calculated using loans with demographic data as the denominator (loans without race/ethnicity data are excluded from the calculation). The table includes a change column showing the increase or decrease of each group over the entire span of years in the report, with positive changes displayed in blue and negative changes in red.';
    T.unified($('lsDemographicTable'), data.demographic_overview, { mode: 'shareBar', hidePopShare: true, metricLabel: 'Race / Ethnicity' });
    $('lsDemographicCaption').innerHTML = '<strong>Source:</strong> Home Mortgage Disclosure Act (HMDA) data, compiled and maintained in NCRC\'s curated databases. ' +
      '<strong>Methodology:</strong> Percentages are calculated as (group loans / loans with demographic data) × 100. Groups &lt; 1% excluded. ' +
      '<strong>Note:</strong> Change column shows ' + esc(span.first) + ' through ' + esc(span.last) + '. | <strong>Counties:</strong> ' +
      esc((metadata.counties || []).join(', ')) + ' | <strong>Years:</strong> ' + esc(span.first + '-' + span.last);

    var lowMod = function (m) { return m.indexOf('Low-to-Moderate') >= 0 || m.indexOf('Low to Moderate') >= 0; };
    T.unified($('lsIncomeBorrowersTable'), data.income_borrowers, {
      metricLabel: 'Borrower Income', isAggregate: lowMod,
      isDetail: function (m) { return /^(Low|Moderate)\s+Income\s+Borrower/i.test(m); },
      shorten: function (m) { return m.replace(/\s+Income\s+Borrowers?/i, '').replace('Low-to-Moderate', 'Low to Moderate'); }
    });
    T.unified($('lsIncomeTractsTable'), data.income_tracts, {
      metricLabel: 'Tract Median Income', isAggregate: lowMod,
      isDetail: function (m) { return /^(Low|Moderate)\s+Income\s+Census/i.test(m); },
      shorten: function (m) { return m.replace(/\s+Income\s+Census\s+Tracts?\*?/i, '').replace('Low-to-Moderate', 'Low to Moderate'); }
    });
    T.unified($('lsMinorityTractsTable'), data.minority_tracts, {
      metricLabel: 'Tract Minority Population',
      isAggregate: function (m) { return m.indexOf('Majority Minority') >= 0; },
      isDetail: function (m) { return /^(Low|Moderate|Middle|High)\s+Minority/i.test(m); },
      shorten: function (m) {
        if (m.indexOf('Majority Minority') >= 0) return 'Majority Minority (≥50%)';
        var x = m.match(/^(\w+)\s+Minority\s+Census\s+Tracts?\s*(\(.*\))?/i);
        return x ? x[1] + (x[2] ? ' ' + x[2] : '') : m;
      }
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-ls="first-year"]'), function (el) { el.textContent = span.first; });
    Array.prototype.forEach.call(document.querySelectorAll('[data-ls="last-year"]'), function (el) { el.textContent = span.last; });

    var county = (metadata.counties || [])[0];
    var notes = [];
    function starred(rows, label) { return (rows || []).some(function (r) { return String(r.Metric || '').indexOf(label) >= 0; }); }
    if (county && starred(data.income_tracts, 'Low Income Census Tracts*')) {
      notes.push('<strong>Note:</strong> Columns marked with an asterisk * show 0% because ' + esc(county) + ' has no census tracts classified as Low Income based on Area Median Income (AMI).');
    }
    if (county && starred(data.minority_tracts, 'Majority Minority Census Tracts*')) {
      notes.push('<strong>Note:</strong> The asterisk * following "Majority Minority Census Tracts" indicates that ' + esc(county) + ' has no census tracts that meet the qualifications (≥50% minority population).');
    }
    if (notes.length) { $('lsAsteriskNote').innerHTML = notes.join(' '); $('lsAsteriskNote').hidden = false; }

    T.lenders($('lsLendersTable'), data.top_lenders_detailed, { type: $('lsLenderType'), expand: $('lsLendersExpand') });
    $('lsLendersCaption').innerHTML = '<strong>Source:</strong> Home Mortgage Disclosure Act (HMDA) data, compiled and maintained in NCRC\'s curated databases. ' +
      '<strong>Year:</strong> ' + esc(span.last) + ' (most recent year in report). <strong>Methodology:</strong> Lenders are sorted in descending order by total loans. ' +
      'Race/ethnicity percentages use denominator = loans with demographic data. Income and neighborhood indicator percentages use denominator = total loans. ' +
      'Only race/ethnicity groups representing ≥1% of overall lending are included. <strong>Note:</strong> All categories are in percentages. ' +
      '<strong>Abbreviations:</strong> Native Am. = Native American; Hawaiian/PI = Hawaiian/Pacific Islander. | <strong>Counties:</strong> ' + esc((metadata.counties || []).join(', '));
  }

  function concentration(data, metadata, p) {
    var rows = data.market_concentration || [];
    var years = (metadata.years || []).map(Number).sort(function (a, b) { return a - b; });
    if (!rows.length || !years.length) return null;
    var shown;
    if (p.all) {
      shown = rows.filter(function (r) { return ['All Loans', 'Home Purchase', 'Refinance', 'Home Equity'].indexOf(r['Loan Purpose']) >= 0; });
    } else {
      var names = p.selected.map(function (x) { return PURPOSE_ROWS[x]; });
      shown = rows.filter(function (r) { return names.indexOf(r['Loan Purpose']) >= 0; });
      if (!shown.length) shown = [rows[0]];
    }
    $('lsSection4').hidden = false;
    narrative('lsConcentrationNarrative', (metadata.ai_insights || {}).market_concentration_discussion, true);
    return root.LendSight.charts.hhi($('lsHhiChart'), shown, years);
  }

  function methods(metadata, p) {
    $('lsLoanPurposeCoverage').textContent = p.all
      ? 'The analysis includes all loan purposes: home purchase loans (loan purpose = 1), refinance and cash-out refinance loans (loan purpose IN (31, 32)), and home equity lending (loan purpose IN (2, 4)).'
      : 'The analysis includes ' + list(p.selected.map(function (x) { return PURPOSE_CODES[x] || x; })) + '.';
    var census = metadata.census_data || {};
    var first = census[Object.keys(census)[0]];
    if (first) {
      var acs = ((first.time_periods || {}).acs || {}).data_year || 'the most recent available ACS 5-year estimates';
      $('lsCensusSourceText').innerHTML = esc('Population demographic data is sourced from the U.S. Census Bureau. The Population Demographics table shows change over time using three data sources: (1) the most recent American Community Survey (ACS) 5-year estimates (' + acs + '), (2) the 2020 Decennial Census, and (3) the 2010 Decennial Census. Census data is used to provide context about the racial and ethnic composition of the selected geography and how it has changed over time. For more information about Census data, visit the ') +
        '<a href="https://www.census.gov/data/developers/data-sets.html" target="_blank" rel="noopener">U.S. Census Bureau Data API website</a>.';
    } else {
      $('lsCensusSourceText').textContent = 'Population demographic data from the U.S. Census Bureau was not available for the selected geography.';
    }
    var bounds = (document.getElementById('lsMinorityTractsTable').tBodies[0].textContent.match(/\(([0-9.]+)%?-([0-9.]+)%?\)/g) || [])
      .map(function (b) { return b.match(/-([0-9.]+)/)[1]; });
    if (bounds.length >= 3) {
      $('lsQuartiles').innerHTML = '<strong>Quartile breakpoints for this geography:</strong> 25th percentile = ' + esc(bounds[0]) +
        '%, 50th percentile = ' + esc(bounds[1]) + '%, 75th percentile = ' + esc(bounds[2]) + '%';
      $('lsQuartiles').hidden = false;
    }
    if (metadata.lendsight_version) $('lsVersion').textContent = 'LendSight v' + metadata.lendsight_version;
  }

  /** Fill the cloned report. Returns a promise that settles when charts are drawn. */
  function display(data, metadata) {
    var span = yearSpan(metadata.years);
    var p = purposes(metadata);
    var ai = metadata.ai_insights || {};
    intro(metadata, span, p);
    summary(data, span);
    tables(data, metadata, span);
    // Expected slots are the ones core.run_analysis always asks for; the three
    // per-table income narratives come only from its fallback path.
    narrative('lsKeyFindings', ai.key_findings, true);
    narrative('lsDemographicNarrative', ai.demographic_overview_discussion, true);
    narrative('lsIncomeBorrowersNarrative', ai.income_borrowers_discussion, false);
    narrative('lsIncomeTractsNarrative', ai.income_tracts_discussion, false);
    narrative('lsMinorityTractsNarrative', ai.minority_tracts_discussion, false);
    narrative('lsNeighborhoodOverview', ai.income_neighborhood_discussion, true);
    narrative('lsLendersNarrative', ai.top_lenders_detailed_discussion, true);
    methods(metadata, p);
    var charts = [
      root.LendSight.charts.census($('lsCensusChart'), metadata.census_data).then(function (drawn) {
        if (!drawn) { $('lsCensusChart').parentNode.hidden = true; $('lsCensusEmpty').hidden = false; return; }
        $('lsCensusCaption').innerHTML = '<strong>Source:</strong> U.S. Census Bureau - 2010 Decennial Census, 2020 Decennial Census, and American Community Survey. Population figures represent ' +
          esc(Object.keys(metadata.census_data)[0]) + '.';
      }),
      concentration(data, metadata, p)
    ];
    return Promise.all(charts);
  }

  root.LendSight.report = { display: display, formatNarrative: formatNarrative, yearSpan: yearSpan };
})(window);
