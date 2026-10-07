/**
 * LendSight tables (spec 04 Part B item 5): the year-by-year "unified"
 * tables (Section 1 and 2) and the sortable top-lenders table (Section 3).
 * Ported from the former report page. All values are escaped; dynamic sizes
 * (share-bar widths, heat-map strength) are CSS custom properties, styled in
 * lendsight.css.
 */
(function (root) {
  'use strict';

  function esc(v) {
    return String(v === null || v === undefined ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function pct(v) {
    if (v === null || v === undefined || v === '') return NaN;
    var s = String(v).trim();
    return s.slice(-1) === '%' ? parseFloat(s) : NaN;
  }

  function parseChange(v) {
    if (v === null || v === undefined || v === '') return null;
    var s = String(v).trim();
    var m = s.match(/^([+-]?)(\d+\.?\d*)\s*(pp|%)?$/);
    if (!m) return { value: 0, unit: 'pp', display: s };
    var n = parseFloat(m[2]);
    return { value: m[1] === '-' ? -n : n, unit: m[3] || 'pp', display: s };
  }

  function changeCell(v) {
    var c = parseChange(v);
    if (!c) return '<span class="ls-change">&mdash;</span>';
    if (Math.abs(c.value) < 0.05) return '<span class="ls-change">0.0' + esc(c.unit) + '</span>';
    var up = c.value > 0;
    return '<span class="ls-change ' + (up ? 'is-up' : 'is-down') + '">' +
      (up ? '&#9650; ' : '&#9660; ') + esc(c.display) + '</span>';
  }

  function sparkline(values) {
    if (!values || values.length < 2) return '';
    var w = 48, h = 18, p = 2, pw = w - p * 2, ph = h - p * 2;
    var mn = Math.min.apply(null, values), mx = Math.max.apply(null, values), rng = mx - mn || 1;
    var pts = values.map(function (v, i) {
      return (p + i / (values.length - 1) * pw).toFixed(1) + ',' + (p + ph - (v - mn) / rng * ph).toFixed(1);
    });
    var last = pts[pts.length - 1].split(',');
    var cls = values[values.length - 1] >= values[0] ? 'is-up' : 'is-down';
    return '<svg class="ls-spark ' + cls + '" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h +
      '" aria-hidden="true"><polyline points="' + pts.join(' ') + '"/><circle cx="' + last[0] + '" cy="' + last[1] + '" r="2.5"/></svg>';
  }

  function shareBar(pop, lend, max) {
    if (isNaN(pop) && isNaN(lend)) return '';
    var scale = 100 / ((max || 100) * 1.5);
    function row(v, cls) {
      if (isNaN(v)) return '<div class="ls-bar-row"></div>';
      return '<div class="ls-bar-row"><span class="ls-bar ' + cls + '" style="--w:' +
        Math.max(v * scale, 0.5).toFixed(1) + '%"></span><span class="ls-bar-label">' + v.toFixed(1) + '</span></div>';
    }
    return '<div class="ls-bars">' + row(pop, 'ls-bar--population') + row(lend, 'ls-bar--lending') + '</div>';
  }

  /**
   * Year-by-year table. opts: mode 'shareBar' (Section 1) or 'plain',
   * metricLabel, isAggregate(metric), isDetail(metric), shorten(metric),
   * hidePopShare.
   */
  function unified(table, data, opts) {
    if (!table || !data || !data.length) return;
    var cols = Object.keys(data[0]);
    var METRIC = 'Metric', POP = 'Population Share (%)';
    var hasPop = cols.indexOf(POP) >= 0 && !opts.hidePopShare;
    var changeCol = cols.filter(function (c) { return c === 'Change' || c.indexOf('Change Over Time') === 0; })[0];
    var years = cols.filter(function (c) {
      return c !== METRIC && c !== POP && c.indexOf('Change') !== 0 && !isNaN(parseInt(c, 10));
    }).sort(function (a, b) { return a - b; });
    var latest = years[years.length - 1];
    var has2022 = years.indexOf('2022') >= 0;
    var isAgg = opts.isAggregate || function () { return false; };
    var isDet = opts.isDetail || function () { return false; };
    var shorten = opts.shorten || function (m) { return m; };
    var bars = opts.mode === 'shareBar';

    var hMin = Infinity, hMax = -Infinity, barMax = 0;
    data.forEach(function (row) {
      if (row[METRIC] === 'Total Loans') return;
      years.forEach(function (y) { var v = pct(row[y]); if (!isNaN(v)) { hMin = Math.min(hMin, v); hMax = Math.max(hMax, v); } });
      if (bars) barMax = Math.max(barMax, pct(row[POP]) || 0, pct(row[latest]) || 0);
    });
    if (hMin === Infinity) { hMin = 0; hMax = 100; }

    function yearClass(y) {
      return 'num ls-year' + (y === latest ? ' is-latest' : '') + (y === '2022' ? ' ls-boundary' : '');
    }
    var head = '';
    if (has2022) {
      head += '<tr class="ls-boundary-row"><th></th>' + (hasPop ? '<th></th>' : '') + (bars ? '<th></th>' : '') +
        years.map(function (y) { return y === '2022' ? '<th class="ls-boundary">New census boundaries</th>' : '<th></th>'; }).join('') +
        '<th></th>' + (changeCol ? '<th></th>' : '') + '</tr>';
    }
    head += '<tr><th scope="col">' + esc(opts.metricLabel || 'Metric') + '</th>' +
      (hasPop ? '<th scope="col" class="num ls-pop">Pop. share</th>' : '') +
      (bars ? '<th scope="col" class="ls-bars-col">Pop. vs lending</th>' : '') +
      years.map(function (y) { return '<th scope="col" class="' + yearClass(y) + '">' + esc(y) + '</th>'; }).join('') +
      '<th scope="col" class="is-latest">Trend</th>' + (changeCol ? '<th scope="col" class="num is-latest">Change</th>' : '') + '</tr>';
    table.tHead.innerHTML = head;

    table.tBodies[0].innerHTML = data.map(function (row) {
      var metric = row[METRIC];
      var total = metric === 'Total Loans';
      var cls = total ? 'ls-total' : isAgg(metric) ? 'ls-aggregate' : isDet(metric) ? 'ls-detail' : '';
      var cells = '<th scope="row">' + esc(shorten(metric)) + '</th>';
      if (hasPop) cells += '<td class="num ls-pop">' + esc(row[POP]) + '</td>';
      if (bars) cells += '<td class="ls-bars-col">' + (total ? '' : shareBar(pct(row[POP]), pct(row[latest]), barMax)) + '</td>';
      var spark = [];
      years.forEach(function (y) {
        var val = row[y];
        if (val === null || val === undefined) val = total ? '0' : '0.0%';
        var p = pct(val);
        var heat = '';
        if (!total && !isNaN(p)) {
          spark.push(p);
          heat = ' style="--heat:' + (hMax === hMin ? 0 : (p - hMin) / (hMax - hMin)).toFixed(3) + '"';
        } else if (total) {
          var n = parseInt(String(val).replace(/,/g, ''), 10);
          if (!isNaN(n)) spark.push(n);
        }
        cells += '<td class="' + yearClass(y) + (heat ? ' ls-heat' : '') + '"' + heat + '>' + esc(val) + '</td>';
      });
      cells += '<td class="is-latest">' + sparkline(spark) + '</td>';
      if (changeCol) cells += '<td class="num is-latest">' + changeCell(row[changeCol]) + '</td>';
      return '<tr class="' + cls + '">' + cells + '</tr>';
    }).join('');
  }

  var RACE_ORDER = ['Hispanic (%)', 'Black (%)', 'White (%)', 'Asian (%)', 'Native American (%)', 'Hawaiian/Pacific Islander (%)'];
  var INDICATOR_ORDER = ['LMIB (%)', 'LMICT (%)', 'MMCT (%)'];
  var LENDERS_SHOWN = 10;

  function ordered(cols, order, test) {
    var hits = cols.filter(test);
    return order.filter(function (c) { return hits.indexOf(c) >= 0; })
      .concat(hits.filter(function (c) { return order.indexOf(c) < 0; }));
  }

  function shortCol(col) {
    var name = col.replace(' (%)', '');
    return { 'Native American': 'Native Am.', 'Hawaiian/Pacific Islander': 'Hawaiian/PI' }[name] || name;
  }

  function loans(row) { return parseInt(String(row['Total Loans']).replace(/,/g, ''), 10) || 0; }

  /** Top lenders: sortable headers, lender-type filter, show all / top 10. */
  function lenders(table, data, controls) {
    if (!table || !data || !data.length) return;
    var base = ['Lender Name', 'Lender Type', 'Total Loans'];
    var rest = Object.keys(data[0]).filter(function (c) { return base.indexOf(c) < 0; });
    var cols = ordered(rest, RACE_ORDER, function (c) { return /Hispanic|Black|White|Asian|Native American|Hawaiian/.test(c); })
      .concat(ordered(rest, INDICATOR_ORDER, function (c) { return /LMIB|LMICT|MMCT/.test(c); }));
    var columns = [{ key: 'Lender Name', label: 'Lender', type: 'text' },
                   { key: 'Lender Type', label: 'Type', type: 'text' },
                   { key: 'Total Loans', label: 'Total', type: 'number' }]
      .concat(cols.map(function (c) { return { key: c, label: shortCol(c), type: 'number' }; }));
    var state = { rows: data.slice(), sortKey: null, dir: 1, expanded: false };

    table.tHead.innerHTML = '<tr>' + columns.map(function (c, i) {
      return '<th scope="col" class="' + (c.type === 'number' ? 'num' : '') + '" aria-sort="none">' +
        '<button type="button" class="ls-sort" data-col="' + i + '">' + esc(c.label) + '</button></th>';
    }).join('') + '</tr>';

    function value(row, c) {
      var v = row[c.key];
      return c.type === 'number' ? (parseFloat(String(v).replace(/[%,]/g, '')) || 0) : String(v || '').toLowerCase();
    }

    function render() {
      var type = controls.type ? controls.type.value : 'all';
      var rows = state.rows.filter(function (r) { return type === 'all' || r['Lender Type'] === type; });
      if (state.sortKey) {
        var col = columns[state.sortKey];
        rows.sort(function (a, b) { var x = value(a, col), y = value(b, col); return x < y ? -state.dir : x > y ? state.dir : 0; });
      } else {
        rows.sort(function (a, b) { return loans(b) - loans(a); });
      }
      var shown = state.expanded ? rows : rows.slice(0, LENDERS_SHOWN);
      table.tBodies[0].innerHTML = shown.map(function (row) {
        return '<tr>' + columns.map(function (c, i) {
          var v = esc(row[c.key]);
          return i === 0 ? '<th scope="row">' + v + '</th>' : '<td class="' + (c.type === 'number' ? 'num' : '') + '">' + v + '</td>';
        }).join('') + '</tr>';
      }).join('');
      if (controls.expand) {
        controls.expand.hidden = rows.length <= LENDERS_SHOWN;
        controls.expand.textContent = state.expanded ? 'Show top 10 only' : 'Show all lenders';
        controls.expand.setAttribute('aria-expanded', state.expanded ? 'true' : 'false');
      }
    }

    table.tHead.addEventListener('click', function (e) {
      var btn = e.target.closest('.ls-sort');
      if (!btn) return;
      var idx = Number(btn.getAttribute('data-col'));
      state.dir = state.sortKey === idx ? -state.dir : 1;
      state.sortKey = idx;
      Array.prototype.forEach.call(table.tHead.querySelectorAll('th'), function (th, i) {
        th.setAttribute('aria-sort', i === idx ? (state.dir === 1 ? 'ascending' : 'descending') : 'none');
      });
      render();
    });
    if (controls.type) controls.type.addEventListener('change', function () { state.sortKey = null; render(); });
    if (controls.expand) controls.expand.addEventListener('click', function () { state.expanded = !state.expanded; render(); });
    render();
  }

  root.LendSight = root.LendSight || {};
  root.LendSight.tables = { unified: unified, lenders: lenders, esc: esc, pct: pct };
})(window);
