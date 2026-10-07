/**
 * AppReport: helpers every analysis app's report body uses (spec 04 A6).
 * Loaded by app_page.html after app_states.js.
 *
 *   AppReport.esc(value)                      escape for innerHTML
 *   AppReport.formatNarrative(text)           AI narrative -> HTML (escaped
 *                                             first; **bold**, [text](https://...)
 *                                             links and "•" bullets)
 *   AppReport.narrative(block, text, expected)
 *       Fill a narrative slot: <div class="app-narrative" hidden>
 *         <div class="report-prose" data-narrative-text></div>
 *         <p class="app-ai-caption">Above text is AI generated ...</p></div>
 *       With text: narrative plus caption. Without: an expected slot shows
 *       AppStates.NARRATIVE_MISSING and no caption; an optional one stays hidden.
 *   AppReport.charts.ready()                  lazy-loads Chart.js and the
 *                                             annotation plugin once
 *   AppReport.charts.token(name)              a tokens.css value
 *   AppReport.charts.thresholds(lines)        HHI-style dashed threshold lines
 *   AppReport.sortableTable(table, rows, columns, opts)
 *       Sortable header buttons (aria-sort), optional filter and a
 *       show-all / top-N toggle. columns: [{key, label, numeric, format(v, row)}];
 *       opts: {topN, expandButton, filter(row), defaultSort(a, b), labels}.
 *       Returns {render()} so callers can re-render after a filter changes.
 *       Numeric columns sort on the cell's leading number (AppReport.sortNumber).
 */
(function (root) {
  'use strict';

  function esc(v) {
    return String(v === null || v === undefined ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

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

  function narrative(block, text, expected) {
    if (!block) return;
    var target = block.querySelector('[data-narrative-text]');
    var caption = block.querySelector('.app-ai-caption');
    if (text && String(text).trim()) {
      target.innerHTML = formatNarrative(text);
      if (caption) caption.hidden = false;
    } else if (expected) {
      target.innerHTML = '<p class="app-narrative-missing">' + esc(root.AppStates.NARRATIVE_MISSING) + '</p>';
      if (caption) caption.hidden = true;
    } else {
      block.hidden = true;
      return;
    }
    block.hidden = false;
  }

  // ---- Charts -------------------------------------------------------------

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

  /** Chart.js is loaded only when a report renders, off the entry page's TTI. */
  function ready() {
    if (root.Chart) return Promise.resolve(root.Chart);
    if (!loading) {
      loading = addScript(CHART_JS).then(function () { return addScript(ANNOTATION_JS); }).then(function () {
        if (root.chartjsPluginAnnotation) root.Chart.register(root.chartjsPluginAnnotation);
        root.Chart.defaults.font.family = token('--font-body') || undefined;
        root.Chart.defaults.color = token('--color-fg-muted') || undefined;
        return root.Chart;
      });
    }
    return loading;
  }

  /** lines: [{value, label, color}] -> annotation config. */
  function thresholds(lines) {
    var out = {};
    lines.forEach(function (l, i) {
      out['t' + i] = {
        type: 'line', yMin: l.value, yMax: l.value, borderColor: l.color, borderWidth: 2, borderDash: [5, 5],
        label: { content: l.label, display: true, position: 'end', backgroundColor: l.color,
                 color: token('--ncrc-black'), font: { size: 11, weight: 'bold' }, padding: 4 }
      };
    });
    return { annotations: out };
  }

  var instances = {};
  function draw(canvas, config) {
    if (instances[canvas.id]) instances[canvas.id].destroy();
    instances[canvas.id] = new root.Chart(canvas, config);
    return instances[canvas.id];
  }

  // ---- Sortable table -----------------------------------------------------

  /** Leading number of a cell: "$1,234" -> 1234, "12 (34.5%)" -> 12. */
  function sortNumber(v) {
    if (typeof v === 'number') return v;
    var n = parseFloat(String(v === null || v === undefined ? '' : v).replace(/[$,\s]/g, ''));
    return isNaN(n) ? 0 : n;
  }

  function sortableTable(table, rows, columns, opts) {
    opts = opts || {};
    var labels = opts.labels || { more: 'Show all lenders', fewer: 'Show top 10 only' };
    var state = { key: null, dir: 1, expanded: false };

    table.tHead.innerHTML = '<tr>' + columns.map(function (c, i) {
      return '<th scope="col" class="' + (c.numeric ? 'num' : '') + '" aria-sort="none">' +
        '<button type="button" class="app-sort" data-col="' + i + '">' + esc(c.label) + '</button></th>';
    }).join('') + '</tr>';

    function sortValue(row, c) {
      var v = row[c.key];
      return c.numeric ? sortNumber(v) : String(v || '').toLowerCase();
    }

    function render() {
      var list = rows.filter(opts.filter || function () { return true; });
      if (state.key !== null) {
        var col = columns[state.key];
        list.sort(function (a, b) { var x = sortValue(a, col), y = sortValue(b, col); return x < y ? -state.dir : x > y ? state.dir : 0; });
      } else if (opts.defaultSort) {
        list.sort(opts.defaultSort);
      }
      var shown = (state.expanded || !opts.topN) ? list : list.slice(0, opts.topN);
      table.tBodies[0].innerHTML = shown.map(function (row) {
        return '<tr>' + columns.map(function (c, i) {
          var v = esc(c.format ? c.format(row[c.key], row) : row[c.key]);
          return i === 0 ? '<th scope="row">' + v + '</th>' : '<td class="' + (c.numeric ? 'num' : '') + '">' + v + '</td>';
        }).join('') + '</tr>';
      }).join('');
      var btn = opts.expandButton;
      if (btn) {
        btn.hidden = !opts.topN || list.length <= opts.topN;
        btn.textContent = state.expanded ? labels.fewer : labels.more;
        btn.setAttribute('aria-expanded', state.expanded ? 'true' : 'false');
      }
    }

    table.tHead.addEventListener('click', function (e) {
      var b = e.target.closest('.app-sort');
      if (!b) return;
      var idx = Number(b.getAttribute('data-col'));
      state.dir = state.key === idx ? -state.dir : 1;
      state.key = idx;
      Array.prototype.forEach.call(table.tHead.querySelectorAll('th'), function (th, i) {
        th.setAttribute('aria-sort', i === idx ? (state.dir === 1 ? 'ascending' : 'descending') : 'none');
      });
      render();
    });
    if (opts.expandButton) {
      opts.expandButton.addEventListener('click', function () { state.expanded = !state.expanded; render(); });
    }
    render();
    return { render: function () { state.key = null; render(); } };
  }

  root.AppReport = {
    esc: esc,
    formatNarrative: formatNarrative,
    narrative: narrative,
    charts: { ready: ready, token: token, thresholds: thresholds, draw: draw },
    sortableTable: sortableTable,
    sortNumber: sortNumber
  };
})(typeof window !== 'undefined' ? window : globalThis);
