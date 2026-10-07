/**
 * LendSight charts (spec 04 Part B item 5). Chart.js is loaded only when a
 * report renders, so it does not count against the entry page's time to
 * interactive.
 *
 * Colours come from tokens.css:
 *   series 1 --ncrc-blue-500, series 2 --ncrc-cyan-500,
 *   comparison or aggregate --ncrc-neutral-400, alert --ncrc-red.
 * Categorical palettes (documented, as the spec requires for extra hues):
 *   Race and ethnicity (population chart), in this order: blue-500, cyan-500,
 *   gold, purple, magenta, neutral-600, neutral-400.
 *   Loan purpose (HHI chart): All Loans neutral-400 (aggregate), Home
 *   Purchase blue-500, Refinance cyan-500, Home Equity gold.
 *   HHI thresholds: moderate (1,500) gold, high (2,500) red.
 */
(function (root) {
  'use strict';

  var CHART_JS = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
  var ANNOTATION_JS = 'https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js';
  var loading = null;

  function token(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function addScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = function () { reject(new Error('Could not load ' + src)); };
      document.head.appendChild(s);
    });
  }

  /** Resolves once Chart.js and the annotation plugin are available. */
  function ready() {
    if (root.Chart) return Promise.resolve(root.Chart);
    if (!loading) {
      loading = addScript(CHART_JS).then(function () { return addScript(ANNOTATION_JS); })
        .then(function () {
          if (root.chartjsPluginAnnotation) root.Chart.register(root.chartjsPluginAnnotation);
          root.Chart.defaults.font.family = token('--font-body') || undefined;
          root.Chart.defaults.color = token('--color-fg-muted') || undefined;
          return root.Chart;
        });
    }
    return loading;
  }

  var RACE_GROUPS = [
    { key: 'white_percentage', label: 'White', color: '--ncrc-blue-500' },
    { key: 'black_percentage', label: 'Black', color: '--ncrc-cyan-500' },
    { key: 'hispanic_percentage', label: 'Hispanic', color: '--ncrc-gold' },
    { key: 'asian_percentage', label: 'Asian', color: '--ncrc-purple' },
    { key: 'native_american_percentage', label: 'Native Am.', color: '--ncrc-magenta' },
    { key: 'hopi_percentage', label: 'Hawaiian/PI', color: '--ncrc-neutral-600' },
    { key: 'multi_racial_percentage', label: 'Multi-Racial', color: '--ncrc-neutral-400' }
  ];

  var PURPOSE_COLORS = {
    'All Loans': '--ncrc-neutral-400',
    'Home Purchase': '--ncrc-blue-500',
    'Refinance': '--ncrc-cyan-500',
    'Home Equity': '--ncrc-gold'
  };

  var instances = {};

  function draw(canvas, config) {
    if (instances[canvas.id]) instances[canvas.id].destroy();
    instances[canvas.id] = new root.Chart(canvas, config);
    return instances[canvas.id];
  }

  /**
   * Population by race for the 2010 Census, 2020 Census and latest ACS of
   * the first county. Returns false when there is no Census data.
   */
  function census(canvas, censusData) {
    var names = Object.keys(censusData || {});
    if (!names.length) return Promise.resolve(false);
    var periods = (censusData[names[0]] || {}).time_periods;
    if (!periods) return Promise.resolve(false);

    var vintages = [];
    if (periods.census2010 && periods.census2010.demographics) vintages.push({ label: '2010 Census', demo: periods.census2010.demographics });
    if (periods.census2020 && periods.census2020.demographics) vintages.push({ label: '2020 Census', demo: periods.census2020.demographics });
    if (periods.acs && periods.acs.demographics) vintages.push({ label: periods.acs.year || 'ACS', demo: periods.acs.demographics });
    if (!vintages.length) return Promise.resolve(false);

    // Groups at or above 1% in any vintage, as in the table captions.
    var groups = RACE_GROUPS.filter(function (g) {
      return Math.max.apply(null, vintages.map(function (v) { return v.demo[g.key] || 0; })) >= 1;
    });
    var maxCount = 0;
    var datasets = groups.map(function (g) {
      var color = token(g.color);
      var pcts = [];
      var counts = vintages.map(function (v) {
        var pct = v.demo[g.key] || 0;
        var count = Math.round(pct / 100 * (v.demo.total_population || 0));
        maxCount = Math.max(maxCount, count);
        pcts.push(Number(pct.toFixed(1)));
        return count;
      });
      return { label: g.label, data: counts, percentages: pcts, backgroundColor: color, borderColor: color, borderWidth: 1 };
    });
    var labels = vintages.map(function (v) {
      return [v.label, 'Pop: ' + (v.demo.total_population || 0).toLocaleString()];
    });

    return ready().then(function () {
      draw(canvas, {
        type: 'bar',
        data: { labels: labels, datasets: datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top' },
            tooltip: { callbacks: { label: function (ctx) {
              var pct = ctx.dataset.percentages[ctx.dataIndex];
              return ctx.dataset.label + ': ' + ctx.raw.toLocaleString() + ' persons (' + pct + '%)';
            } } }
          },
          scales: { y: {
            beginAtZero: true,
            max: Math.ceil(maxCount * 1.1 / 10000) * 10000 || undefined,
            title: { display: true, text: 'Population' },
            ticks: { callback: function (v) { return v.toLocaleString(); } }
          } }
        }
      });
      return true;
    });
  }

  /** HHI by year for the displayed loan-purpose rows, with threshold lines. */
  function hhi(canvas, rows, years) {
    var labels = years.map(String);
    var maxHHI = 2500;
    var datasets = rows.map(function (row) {
      var purpose = row['Loan Purpose'];
      var color = token(PURPOSE_COLORS[purpose] || '--ncrc-blue-500');
      var values = labels.map(function (y) {
        var v = parseFloat(row[y]);
        v = isNaN(v) ? 0 : v;
        maxHHI = Math.max(maxHHI, v);
        return v;
      });
      return { label: purpose, data: values, backgroundColor: color, borderColor: color, borderWidth: 1 };
    });
    var gold = token('--ncrc-gold');
    var red = token('--ncrc-red');
    function line(value, color, text) {
      return {
        type: 'line', yMin: value, yMax: value, borderColor: color, borderWidth: 2, borderDash: [5, 5],
        label: { content: text, display: true, position: 'end', backgroundColor: color,
                 color: token('--ncrc-black'), font: { size: 11, weight: 'bold' }, padding: 4 }
      };
    }
    return ready().then(function () {
      draw(canvas, {
        type: 'bar',
        data: { labels: labels, datasets: datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: rows.length > 1, position: 'top' },
            title: { display: true, text: rows.length === 1
              ? 'Market Concentration (HHI) — ' + rows[0]['Loan Purpose']
              : 'Market Concentration (HHI) by Loan Purpose' },
            tooltip: { callbacks: { label: function (ctx) {
              return (rows.length > 1 ? ctx.dataset.label + ': ' : '') + 'HHI: ' + Math.round(ctx.parsed.y).toLocaleString();
            } } },
            annotation: { annotations: {
              moderate: line(1500, gold, 'Moderate (1,500)'),
              high: line(2500, red, 'High (2,500)')
            } }
          },
          scales: {
            y: { beginAtZero: true, max: Math.min(Math.max(maxHHI * 1.15, 3000), 10000),
                 title: { display: true, text: 'HHI' },
                 ticks: { callback: function (v) { return v.toLocaleString(); } } },
            x: { title: { display: true, text: 'Year' } }
          }
        }
      });
    });
  }

  root.LendSight = root.LendSight || {};
  root.LendSight.charts = { census: census, hhi: hhi, token: token };
})(window);
