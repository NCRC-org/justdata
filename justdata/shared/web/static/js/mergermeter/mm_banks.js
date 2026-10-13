/**
 * MergerMeter bank pickers (acquirer and target). Same behaviour as the former
 * page: a name search against /api/search-banks (300 ms debounce, 15 results,
 * arrow keys and Enter to pick), then the selected bank's LEI, RSSD and Res ID
 * in editable fields, with "Change bank" to search again.
 *
 *   MergerMeter.banks.value('acquirer') -> {name, lei, rssd, sbId}
 *   MergerMeter.banks.clear('target')
 */
(function (root) {
  'use strict';

  var CFG = root.MERGERMETER || {};
  var BASE = CFG.baseUrl || '/mergermeter';
  var DELAY_MS = 300;
  var esc = root.AppReport.esc;

  function $(id) { return document.getElementById(id); }

  /** Assets are stored in thousands of dollars. */
  function formatAssets(assets) {
    if (!assets) return '';
    var dollars = assets * 1000;
    if (dollars >= 1e9) return '$' + (dollars / 1e9).toFixed(1) + 'B';
    if (dollars >= 1e6) return '$' + (dollars / 1e6).toFixed(0) + 'M';
    if (dollars >= 1e3) return '$' + (dollars / 1e3).toFixed(0) + 'K';
    return '$' + dollars;
  }

  function picker(bank) {
    var input = $(bank + '_search');
    var list = $(bank + '_search_results');
    var timer = null;
    var items = [];

    function close() {
      list.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
    }

    function open(html) {
      list.innerHTML = html;
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    function setActive(i) {
      var nodes = list.querySelectorAll('[role="option"]');
      Array.prototype.forEach.call(nodes, function (n, k) { n.classList.toggle('is-active', k === i); });
      if (nodes[i]) {
        input.setAttribute('aria-activedescendant', nodes[i].id);
        nodes[i].scrollIntoView({ block: 'nearest' });
      }
    }

    function activeIndex() {
      var nodes = Array.prototype.slice.call(list.querySelectorAll('[role="option"]'));
      return nodes.findIndex(function (n) { return n.classList.contains('is-active'); });
    }

    function search(query) {
      open('<li class="mm-results-note">Searching…</li>');
      root.AppRun.getJSON(BASE + '/api/search-banks?q=' + encodeURIComponent(query) + '&limit=15').then(function (res) {
        if (input.value.trim() !== query) return;
        var body = res.body || {};
        if (!body.success) { open('<li class="mm-results-note">' + esc(body.error || 'Search failed. Please try again.') + '</li>'); return; }
        items = body.banks || [];
        if (!items.length) { open('<li class="mm-results-note">No banks found matching your search.</li>'); return; }
        open(items.map(function (b, i) {
          var meta = [b.location || 'Location not available', formatAssets(b.assets)].filter(Boolean).join(' · ');
          return '<li role="option" id="' + bank + 'Opt' + i + '" data-index="' + i + '"' + (i === 0 ? ' class="is-active"' : '') + '>' +
            '<span class="mm-opt-name">' + esc(b.name) + '</span>' +
            '<span class="mm-opt-meta">' + esc(meta) + '</span>' +
            '<span class="mm-opt-ids">LEI ' + esc(b.lei || 'N/A') + ' · RSSD ' + esc(b.rssd || 'N/A') + ' · Res ID ' + esc(b.res_id || 'N/A') + '</span></li>';
        }).join(''));
        setActive(0);
      }).catch(function () { open('<li class="mm-results-note">Search failed. Please try again.</li>'); });
    }

    function select(i) {
      var b = items[i];
      if (!b) return;
      $(bank + '_lei').value = b.lei || '';
      $(bank + '_rssd').value = b.rssd || '';
      $(bank + '_name').value = b.name || '';
      // Res ID: filled from the result when it has one; otherwise a value the
      // user already typed is kept (former page).
      if (b.res_id) $(bank + '_sb_id').value = b.res_id;
      $(bank + '_name_display').textContent = b.name || '';
      $(bank + '_location_display').textContent = b.location || '';
      $(bank + 'SearchField').hidden = true;
      $(bank + '_selected').hidden = false;
      root.AppRun.setInvalid(input, '');
      close();
    }

    input.addEventListener('input', function () {
      var query = input.value.trim();
      clearTimeout(timer);
      if (query.length < 2) { close(); return; }
      timer = setTimeout(function () { search(query); }, DELAY_MS);
    });
    input.addEventListener('keydown', function (e) {
      if (list.hidden) return;
      var count = list.querySelectorAll('[role="option"]').length;
      var i = activeIndex();
      if (e.key === 'ArrowDown' && count) { e.preventDefault(); setActive((i + 1) % count); }
      else if (e.key === 'ArrowUp' && count) { e.preventDefault(); setActive(i <= 0 ? count - 1 : i - 1); }
      else if (e.key === 'Enter' && i >= 0) { e.preventDefault(); select(i); }
      else if (e.key === 'Escape') close();
    });
    list.addEventListener('mousedown', function (e) {
      var opt = e.target.closest('[role="option"]');
      if (opt) { e.preventDefault(); select(Number(opt.dataset.index)); }
    });
    document.addEventListener('click', function (e) {
      if (!input.contains(e.target) && !list.contains(e.target)) close();
    });

    return {
      clear: function () {
        ['_lei', '_rssd', '_sb_id', '_name', '_search'].forEach(function (s) { $(bank + s).value = ''; });
        $(bank + '_name_display').textContent = '';
        $(bank + '_location_display').textContent = '';
        $(bank + '_selected').hidden = true;
        $(bank + 'SearchField').hidden = false;
        close();
      },
      value: function () {
        return {
          name: $(bank + '_name').value.trim() || $(bank + '_name_display').textContent.trim(),
          lei: $(bank + '_lei').value.trim(),
          rssd: $(bank + '_rssd').value.trim(),
          sbId: $(bank + '_sb_id').value.trim()
        };
      },
      input: input
    };
  }

  var pickers = { acquirer: picker('acquirer'), target: picker('target') };
  Array.prototype.forEach.call(document.querySelectorAll('[data-change-bank]'), function (btn) {
    btn.addEventListener('click', function () {
      var bank = btn.dataset.changeBank;
      pickers[bank].clear();
      pickers[bank].input.focus();
    });
  });

  root.MergerMeter = root.MergerMeter || {};
  root.MergerMeter.banks = {
    value: function (bank) { return pickers[bank].value(); },
    clear: function (bank) { pickers[bank].clear(); },
    input: function (bank) { return pickers[bank].input; }
  };
})(window);
