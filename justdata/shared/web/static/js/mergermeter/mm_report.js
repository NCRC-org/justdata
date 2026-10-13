/**
 * MergerMeter report: the generated workbook, read from /excel-data and shown
 * sheet by sheet with SheetJS, as the former page did. Number formats,
 * merged cells and the Validation sheet's warnings are read the same way;
 * cell text is now escaped. Sheets are tabs (arrow keys move between them).
 *
 *   MergerMeter.report.show(jobId, metadata) -> Promise
 *   MergerMeter.report.yearsText(metadata)
 */
(function (root) {
  'use strict';

  var CFG = root.MERGERMETER || {};
  var BASE = CFG.baseUrl || '/mergermeter';
  var VALIDATION_SHEETS = ['Validation', 'Validation Warnings'];
  var esc = root.AppReport.esc;

  function $(id) { return document.getElementById(id); }

  function span(years) {
    var list = (years || []).map(Number).filter(function (y) { return !isNaN(y); }).sort();
    if (!list.length) return '';
    return list[0] === list[list.length - 1] ? String(list[0]) : list[0] + ' to ' + list[list.length - 1];
  }

  function yearsText(md) {
    var parts = [];
    if (span(md.hmda_years)) parts.push('HMDA ' + span(md.hmda_years));
    if (span(md.sb_years)) parts.push('small business ' + span(md.sb_years));
    return parts.join('; ');
  }

  /** Validation sheet: warning text is in column D from row 5. */
  function warnings(ws) {
    var out = [];
    if (!ws || !ws['!ref']) return out;
    var range = root.XLSX.utils.decode_range(ws['!ref']);
    for (var r = 4; r <= range.e.r; r++) {
      var cell = ws[root.XLSX.utils.encode_cell({ r: r, c: 3 })];
      if (cell && cell.v) out.push(String(cell.v));
    }
    return out;
  }

  function cellText(cell) {
    var cls = '', val = '';
    if (cell.t === 'n') {
      cls = 'num';
      if (cell.z && cell.z.indexOf(',') >= 0) val = Math.round(cell.v).toLocaleString();
      else if (cell.z && cell.z.indexOf('%') >= 0) { val = (cell.v * 100).toFixed(2) + '%'; cls = 'pct'; }
      else if (cell.v < 1 && cell.v > -1 && cell.v !== 0) { val = (cell.v * 100).toFixed(2) + '%'; cls = 'pct'; }
      else if (cell.v === Math.floor(cell.v)) val = cell.v.toLocaleString();
      else val = cell.v.toFixed(2);
      if (cell.v < 0) cls += ' neg';
    } else if (cell.t === 's') {
      val = cell.v;
      if (val === '--') cls = 'empty';
    } else if (cell.w) {
      val = cell.w;
    } else if (cell.v != null) {
      val = String(cell.v);
    }
    if (typeof val === 'string' && val.indexOf('=IFERROR') === 0) val = '';
    return { cls: cls, val: val };
  }

  /** One sheet as a table; the first two rows are headers (former page). */
  function sheetTable(ws) {
    if (!ws || !ws['!ref']) return '<p class="app-state-elapsed">Empty sheet</p>';
    var X = root.XLSX.utils;
    var range = X.decode_range(ws['!ref']);
    var merges = ws['!merges'] || [];
    var html = '<table class="mm-sheet-table">';
    for (var r = range.s.r; r <= range.e.r; r++) {
      html += '<tr>';
      for (var c = range.s.c; c <= range.e.c; c++) {
        var skip = false, colspan = 1, rowspan = 1;
        for (var m = 0; m < merges.length; m++) {
          var mg = merges[m];
          if (r === mg.s.r && c === mg.s.c) { colspan = mg.e.c - mg.s.c + 1; rowspan = mg.e.r - mg.s.r + 1; }
          else if (r >= mg.s.r && r <= mg.e.r && c >= mg.s.c && c <= mg.e.c) skip = true;
        }
        if (skip) continue;
        var cell = ws[X.encode_cell({ r: r, c: c })];
        var t = cell ? cellText(cell) : { cls: '', val: '' };
        var tag = r <= 1 ? 'th' : 'td';
        html += '<' + tag + (colspan > 1 ? ' colspan="' + colspan + '"' : '') + (rowspan > 1 ? ' rowspan="' + rowspan + '"' : '') +
          (t.cls ? ' class="' + t.cls.trim() + '"' : '') + '>' + esc(t.val) + '</' + tag + '>';
      }
      html += '</tr>';
    }
    return html + '</table>';
  }

  function selectTab(index) {
    var tabs = $('mmTabs').querySelectorAll('[role="tab"]');
    Array.prototype.forEach.call(tabs, function (tab, i) {
      var on = i === index;
      tab.setAttribute('aria-selected', on ? 'true' : 'false');
      tab.tabIndex = on ? 0 : -1;
      $(tab.getAttribute('aria-controls')).hidden = !on;
    });
  }

  function renderWorkbook(wb) {
    var tabs = $('mmTabs');
    var sheets = $('mmSheets');
    var found = [];
    var shown = 0;
    wb.SheetNames.forEach(function (name) {
      if (VALIDATION_SHEETS.indexOf(name) >= 0) { found = found.concat(warnings(wb.Sheets[name])); return; }
      var i = shown++;
      var tab = document.createElement('button');
      tab.type = 'button';
      tab.setAttribute('role', 'tab');
      tab.id = 'mmTab' + i;
      tab.setAttribute('aria-controls', 'mmSheet' + i);
      tab.textContent = name;
      tab.addEventListener('click', function () { selectTab(i); });
      tabs.appendChild(tab);
      var panel = document.createElement('div');
      panel.className = 'mm-sheet app-table-wrap';
      panel.id = 'mmSheet' + i;
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', tab.id);
      panel.tabIndex = 0;
      panel.innerHTML = sheetTable(wb.Sheets[name]);
      sheets.appendChild(panel);
    });
    tabs.addEventListener('keydown', function (e) {
      var list = Array.prototype.slice.call(tabs.querySelectorAll('[role="tab"]'));
      var i = list.indexOf(document.activeElement);
      if (i < 0) return;
      var next = e.key === 'ArrowRight' ? (i + 1) % list.length : e.key === 'ArrowLeft' ? (i - 1 + list.length) % list.length : -1;
      if (next >= 0) { e.preventDefault(); selectTab(next); list[next].focus(); }
    });
    if (shown) selectTab(0);

    var note = $('mmValidation');
    note.hidden = false;
    if (found.length) {
      note.className = 'app-note app-note--caution';
      note.textContent = 'Data quality warnings found:';
      $('mmWarnings').innerHTML = found.map(function (w) { return '<li>' + esc(w) + '</li>'; }).join('');
      $('mmWarnings').hidden = false;
    } else {
      note.className = 'app-note';
      note.textContent = 'No data quality issues found.';
    }
    return shown;
  }

  function summary(md, sheetCount, bytes) {
    var items = [
      [md.acquirer_name || '-', 'Acquirer'],
      [md.target_name || 'None (single bank)', 'Target'],
      [span(md.hmda_years) || '-', 'HMDA years'],
      [span(md.sb_years) || '-', 'Small business years'],
      [String(sheetCount), 'Workbook sheets (' + Math.round(bytes / 1024).toLocaleString() + ' KB)']
    ];
    $('mmSummary').innerHTML = items.map(function (i) {
      return '<div><p class="app-summary-figure mm-summary-figure">' + esc(i[0]) + '</p><p class="app-summary-label">' + esc(i[1]) + '</p></div>';
    }).join('');
  }

  function show(jobId, md) {
    var url = BASE + '/excel-data?job_id=' + encodeURIComponent(jobId);
    return fetch(url, { credentials: 'same-origin', cache: 'no-store' }).then(function (res) {
      if (!res.ok) throw new Error('workbook ' + res.status);
      return res.arrayBuffer();
    }).then(function (data) {
      $('mmLoading').hidden = true;
      var wb = root.XLSX.read(data, { type: 'array', cellStyles: true, cellDates: true });
      summary(md, renderWorkbook(wb), data.byteLength);
    }).catch(function () {
      $('mmLoading').innerHTML = 'The workbook preview could not be loaded. Download the workbook from the toolbar instead.';
    });
  }

  root.MergerMeter = root.MergerMeter || {};
  root.MergerMeter.report = { show: show, yearsText: yearsText };
})(window);
