// dotlender_filters.js
// Filter form logic for DotLender — year dropdowns, lender typeahead, render trigger.
// Exposes getFilterState() and initRenderButton(onRender) for the map module to consume.

const API = {
  maxYear: '/dotlender/api/max-year',
  lenderSearch: '/dotlender/api/lender-search',
  mapData: '/dotlender/api/map-data',
  summaryStats: '/dotlender/api/summary-stats',
};

let _lastSummaryStats = null;

async function initYearDropdowns() {
  const res = await fetch(API.maxYear);
  if (!res.ok) {
    console.error('[dotlender] /api/max-year failed', res.status);
    return;
  }
  const { max_year } = await res.json();
  const startEl = document.getElementById('dl-year-start');
  const endEl = document.getElementById('dl-year-end');
  for (let y = 2018; y <= max_year; y++) {
    startEl.add(new Option(String(y), String(y)));
    endEl.add(new Option(String(y), String(y)));
  }
  startEl.value = String(Math.max(max_year - 2, 2018));
  endEl.value = String(max_year);
}

function initAdvancedToggle() {
  const toggle = document.getElementById('dl-advanced-toggle');
  const panel = document.getElementById('dotlender-advanced-filters');
  toggle.addEventListener('click', () => {
    const open = panel.style.display !== 'none';
    panel.style.display = open ? 'none' : 'block';
    toggle.textContent = (open ? '▶' : '▼') + toggle.textContent.slice(1);
  });
}

function initLenderTypeahead() {
  const input = document.getElementById('dl-lender-search');
  const leiInput = document.getElementById('dl-lender-lei');
  const suggestions = document.getElementById('dl-lender-suggestions');
  let debounce;

  input.addEventListener('input', () => {
    clearTimeout(debounce);
    leiInput.value = '';
    if (input.value.length < 2) {
      suggestions.style.display = 'none';
      return;
    }
    debounce = setTimeout(async () => {
      const yearStart = document.getElementById('dl-year-start').value;
      const yearEnd = document.getElementById('dl-year-end').value;
      const url = `${API.lenderSearch}?q=${encodeURIComponent(input.value)}&year_start=${yearStart}&year_end=${yearEnd}`;
      const res = await fetch(url);
      if (!res.ok) {
        suggestions.style.display = 'none';
        return;
      }
      const data = await res.json();
      suggestions.innerHTML = '';
      if (!data.length) {
        suggestions.style.display = 'none';
        return;
      }
      data.forEach((item) => {
        const a = document.createElement('a');
        a.href = '#';
        a.className = 'list-group-item list-group-item-action small';
        a.textContent = `${item.respondent_name} (${item.loan_count.toLocaleString()} loans)`;
        a.addEventListener('click', (e) => {
          e.preventDefault();
          input.value = item.respondent_name;
          leiInput.value = item.lei;
          suggestions.style.display = 'none';
        });
        suggestions.appendChild(a);
      });
      suggestions.style.display = 'block';
    }, 300);
  });

  document.addEventListener('click', (e) => {
    if (!suggestions.contains(e.target) && e.target !== input) {
      suggestions.style.display = 'none';
    }
  });
}

export function getFilterState() {
  return {
    geography_type: document.getElementById('dl-geo-type').value,
    geography_value: document.getElementById('dl-geo-value').value.trim(),
    year_start: parseInt(document.getElementById('dl-year-start').value, 10),
    year_end: parseInt(document.getElementById('dl-year-end').value, 10),
    lei: document.getElementById('dl-lender-lei').value || null,
    lender_name: document.getElementById('dl-lender-search').value.trim() || 'All lenders',
    overlay_mode: document.getElementById('dl-overlay-mode').value,
    filters: {
      loan_purpose: document.getElementById('dl-loan-purpose').value,
      action_taken: document.getElementById('dl-action-taken').value,
      lien_status: document.getElementById('dl-lien-status').value,
      occupancy_type: document.getElementById('dl-occupancy-type').value,
      construction_method: document.getElementById('dl-construction-method').value,
      total_units: document.getElementById('dl-total-units').value,
      reverse_mortgage: document.getElementById('dl-reverse-mortgage').value,
    },
  };
}

export function getLastSummaryStats() {
  return _lastSummaryStats;
}

export function initRenderButton(onRender) {
  document.getElementById('dl-render-btn').addEventListener('click', async () => {
    const state = getFilterState();
    const errEl = document.getElementById('dl-map-error');
    if (!state.geography_value) {
      errEl.textContent = 'Please enter a geography value.';
      errEl.style.display = 'block';
      return;
    }
    if (state.year_start > state.year_end) {
      errEl.textContent = 'Year start must be ≤ year end.';
      errEl.style.display = 'block';
      return;
    }
    errEl.style.display = 'none';

    const spinner = document.getElementById('dl-spinner');
    const btn = document.getElementById('dl-render-btn');
    spinner.classList.add('active');
    btn.disabled = true;

    try {
      const [mapRes, statsRes] = await Promise.all([
        fetch(API.mapData, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(state),
        }),
        fetch(API.summaryStats, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(state),
        }),
      ]);
      if (!mapRes.ok) {
        const j = await mapRes.json().catch(() => ({}));
        throw new Error(j.detail || j.error || `Map data request failed: ${mapRes.status}`);
      }
      const mapData = await mapRes.json();
      const statsData = statsRes.ok ? await statsRes.json() : null;
      _lastSummaryStats = statsData;
      displaySummaryStats(statsData);
      onRender(mapData, state);
    } catch (err) {
      errEl.textContent = err.message;
      errEl.style.display = 'block';
    } finally {
      spinner.classList.remove('active');
      btn.disabled = false;
    }
  });
}

function displaySummaryStats(stats) {
  if (!stats) {
    document.getElementById('dl-summary-stats').style.display = 'none';
    return;
  }
  const el = document.getElementById('dl-stats-content');
  el.innerHTML = `
    <strong>${stats.total_loans?.toLocaleString() ?? '—'}</strong> loans<br/>
    <strong>${stats.tracts_with_lending?.toLocaleString() ?? '—'}</strong> tracts with lending<br/>
    <strong>${stats.lender_count?.toLocaleString() ?? '—'}</strong> lenders<br/>
    <strong>${stats.pct_lmi_tracts?.toFixed(1) ?? '—'}%</strong> in LMI tracts<br/>
    <strong>${stats.pct_majority_minority_tracts?.toFixed(1) ?? '—'}%</strong> in majority-minority tracts
  `;
  document.getElementById('dl-summary-stats').style.display = 'block';
}

document.addEventListener('DOMContentLoaded', () => {
  initYearDropdowns();
  initAdvancedToggle();
  initLenderTypeahead();
});
