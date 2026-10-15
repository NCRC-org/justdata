/**
 * MergerMeter assessment areas, per bank. Same behaviour as the former page:
 *   Enter:         name + counties (one per line, or MSA codes/names), any number
 *   Upload file:   JSON or CSV to /api/upload-assessment-areas
 *   From branches: /api/generate-assessment-areas-from-branches (RSSD, the SOD year)
 * An uploaded or generated list is shown collapsed ("84 counties selected in
 * 21 areas", app_choices.js) and opens to a checkbox per county; unticking a
 * county drops it (and an area with none left). What is sent is that list
 * followed by the entered areas, as before.
 *
 *   MergerMeter.areas.collect('acquirer') -> [{cbsa_name, counties, ...}]
 */
(function (root) {
  'use strict';

  var CFG = root.MERGERMETER || {};
  var BASE = CFG.baseUrl || '/mergermeter';
  var BRANCH_YEAR = CFG.sodYear;  // SOD_LATEST_YEAR, from the page
  var esc = root.AppReport.esc;
  var stored = { acquirer: null, target: null };    // as returned
  var filtered = { acquirer: [], target: [] };      // after unticked counties

  function $(id) { return document.getElementById(id); }

  /** Areas were added: the step's "add assessment areas" message no longer applies. */
  function clearNote(bank) {
    var note = $(bank + 'Areas').querySelector('.app-field-error');
    if (note) note.hidden = true;
  }

  function status(bank, text, kind) {
    var el = $(bank + 'AreaStatus');
    el.textContent = text || '';
    el.hidden = !text;
    el.className = 'mm-status' + (kind ? ' mm-status--' + kind : '');
  }

  function countyLabel(c) {
    if (c && typeof c === 'object') {
      return c.county_name && c.state_name ? c.county_name + ', ' + c.state_name
        : (c.county_name || String(c.state_code || '') + String(c.county_code || ''));
    }
    return String(c);
  }

  function applyTicks(bank) {
    var areas = stored[bank] || [];
    var preview = $(bank + 'AreaPreview');
    filtered[bank] = areas.map(function (aa, a) {
      var kept = (aa.counties || []).filter(function (c, k) {
        var box = preview.querySelector('input[data-aa="' + a + '"][data-county="' + k + '"]');
        return box && box.checked;
      });
      return kept.length ? Object.assign({}, aa, { counties: kept }) : null;
    }).filter(Boolean);
    var n = filtered[bank].length;
    preview.dataset.suffix = 'in ' + n + (n === 1 ? ' area' : ' areas');
    root.AppChoices.update(preview);
  }

  function showList(bank, areas) {
    stored[bank] = JSON.parse(JSON.stringify(areas));
    var preview = $(bank + 'AreaPreview');
    $(bank + 'AreaList').innerHTML = areas.map(function (aa, a) {
      var counties = aa.counties || [];
      return '<fieldset class="mm-area-item"><legend>' + esc(aa.cbsa_name || 'Unnamed area') +
        ' <span class="app-check-hint">' + counties.length + (counties.length === 1 ? ' county' : ' counties') + '</span></legend>' +
        counties.map(function (c, k) {
          return '<label class="mm-county"><input type="checkbox" checked data-aa="' + a + '" data-county="' + k + '">' +
            '<span>' + esc(countyLabel(c)) + '</span></label>';
        }).join('') + '</fieldset>';
    }).join('');
    preview.hidden = !areas.length;
    preview.open = false;
    applyTicks(bank);
    if (areas.length) clearNote(bank);
  }

  function setMode(bank, mode) {
    Array.prototype.forEach.call($(bank + 'Areas').querySelectorAll('.mm-mode-panel'), function (p) {
      p.hidden = p.dataset.mode !== mode;
    });
  }

  function addManual(bank) {
    var list = $(bank + 'ManualAreas');
    var n = list.children.length + 1;
    var id = bank + 'Manual' + Date.now();
    var entry = document.createElement('div');
    entry.className = 'mm-manual';
    entry.innerHTML =
      '<div class="app-field"><label for="' + id + 'Name">Area ' + n + ' name</label>' +
      '<input type="text" id="' + id + 'Name" class="mm-aa-name" placeholder="e.g. Denver-Boulder-Greeley CSA"></div>' +
      '<div class="app-field"><label for="' + id + 'Counties">Counties or MSA codes</label>' +
      '<textarea id="' + id + 'Counties" class="mm-aa-counties" rows="4" placeholder="Denver County, Colorado"></textarea></div>' +
      '<button type="button" class="btn btn-ghost btn-sm" data-remove-area>Remove area</button>';
    list.appendChild(entry);
    clearNote(bank);
    entry.querySelector('input').focus();
  }

  /** Entered areas, as the former page built them. */
  function manualAreas(bank) {
    var out = [];
    Array.prototype.forEach.call($(bank + 'ManualAreas').querySelectorAll('.mm-manual'), function (e) {
      var name = e.querySelector('.mm-aa-name').value.trim();
      var text = e.querySelector('.mm-aa-counties').value.trim();
      if (!name || !text) return;
      out.push({
        cbsa_name: name,
        counties: text.split('\n').map(function (c) { return c.trim(); }).filter(Boolean),
        has_msa_codes: /MSA\s+(\d+(?:\s*,\s*\d+)*)/i.test(text)
      });
    });
    return out;
  }

  function upload(bank, file) {
    var data = new FormData();
    data.append('file', file);
    data.append('bank_type', bank);
    status(bank, 'Uploading and reading the file…');
    $(bank + 'AreaPreview').hidden = true;
    fetch(BASE + '/api/upload-assessment-areas', { method: 'POST', credentials: 'same-origin', body: data })
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (res) {
        if (!res.success) { status(bank, res.error || 'The file could not be read.', 'error'); return; }
        var areas = res.assessment_areas || [];
        if (!areas.length) { status(bank, 'The file was read but has no assessment areas. Check its format.', 'warn'); return; }
        status(bank, 'Read ' + (res.count || areas.length) + ' assessment areas. Choose Change to leave out any county.', 'ok');
        showList(bank, areas);
      })
      .catch(function () { status(bank, 'Network error. Check your connection and try again.', 'error'); });
  }

  function fromBranches(bank, button) {
    var rssd = $(bank + '_rssd').value.trim();
    if (!rssd) {
      status(bank, 'Select the ' + (bank === 'acquirer' ? 'acquirer' : 'target') + ' in step 1 first; this needs its RSSD.', 'error');
      return;
    }
    button.disabled = true;
    status(bank, 'Finding branch locations…');
    fetch(BASE + '/api/generate-assessment-areas-from-branches', {
      method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rssd: rssd, bank_type: bank, year: BRANCH_YEAR, group_by_cbsa: true, min_branches: 1 })
    }).then(function (r) { return r.json().catch(function () { return {}; }); }).then(function (res) {
      if (!res.success) { status(bank, res.error || 'Assessment areas could not be generated.', 'error'); return; }
      var areas = res.assessment_areas || [];
      status(bank, 'Generated ' + (res.count || areas.length) + ' assessment areas from branch locations. Choose Change to leave out any county.', 'ok');
      if (areas.length) showList(bank, areas);
    }).catch(function () {
      status(bank, 'Network error. Check your connection and try again.', 'error');
    }).then(function () { button.disabled = false; });
  }

  ['acquirer', 'target'].forEach(function (bank) {
    var panel = $(bank + 'Areas');
    panel.addEventListener('change', function (e) {
      if (e.target.name === bank + '_aa_mode') setMode(bank, e.target.value);
      else if (e.target.dataset.aa !== undefined) applyTicks(bank);
      else if (e.target.id === bank + 'AreaFile' && e.target.files[0]) upload(bank, e.target.files[0]);
    });
    panel.addEventListener('click', function (e) {
      var btn = e.target.closest('button');
      if (!btn) return;
      if (btn.dataset.addArea) addManual(bank);
      else if (btn.hasAttribute('data-remove-area')) btn.closest('.mm-manual').remove();
      else if (btn.dataset.generateAreas) fromBranches(bank, btn);
    });
  });

  root.MergerMeter = root.MergerMeter || {};
  root.MergerMeter.areas = {
    collect: function (bank) { return filtered[bank].concat(manualAreas(bank)); },
    reset: function () {
      ['acquirer', 'target'].forEach(function (bank) {
        stored[bank] = null;
        filtered[bank] = [];
        $(bank + 'ManualAreas').innerHTML = '';
        $(bank + 'AreaList').innerHTML = '';
        $(bank + 'AreaPreview').hidden = true;
        root.AppChoices.close($(bank + 'AreaPreview'));
        $(bank + 'AreaFile').value = '';
        status(bank, '');
      });
    }
  };
})(window);
