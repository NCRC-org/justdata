// dotlender_filters.js
// Filter form logic for DotLender — year dropdowns, lender typeahead,
// geography search + county chips, render trigger.
// Exposes getFilterState() and initRenderButton(onRender) for the map.

const API = {
  maxYear: '/dotlender/api/max-year',
  lenderSearch: '/dotlender/api/lender-search',
  cbsaSearch: '/dotlender/api/cbsa-search',
  cbsaCounties: '/dotlender/api/cbsa-counties',
  stateCounties: '/dotlender/api/state-counties',
  mapData: '/dotlender/api/map-data',
  summaryStats: '/dotlender/api/summary-stats',
};

// 50 states + DC, sorted by name. Client-side only — no API call needed.
const STATE_LIST = [
  { state_fips: '01', name: 'Alabama' }, { state_fips: '02', name: 'Alaska' },
  { state_fips: '04', name: 'Arizona' }, { state_fips: '05', name: 'Arkansas' },
  { state_fips: '06', name: 'California' }, { state_fips: '08', name: 'Colorado' },
  { state_fips: '09', name: 'Connecticut' }, { state_fips: '10', name: 'Delaware' },
  { state_fips: '11', name: 'District of Columbia' }, { state_fips: '12', name: 'Florida' },
  { state_fips: '13', name: 'Georgia' }, { state_fips: '15', name: 'Hawaii' },
  { state_fips: '16', name: 'Idaho' }, { state_fips: '17', name: 'Illinois' },
  { state_fips: '18', name: 'Indiana' }, { state_fips: '19', name: 'Iowa' },
  { state_fips: '20', name: 'Kansas' }, { state_fips: '21', name: 'Kentucky' },
  { state_fips: '22', name: 'Louisiana' }, { state_fips: '23', name: 'Maine' },
  { state_fips: '24', name: 'Maryland' }, { state_fips: '25', name: 'Massachusetts' },
  { state_fips: '26', name: 'Michigan' }, { state_fips: '27', name: 'Minnesota' },
  { state_fips: '28', name: 'Mississippi' }, { state_fips: '29', name: 'Missouri' },
  { state_fips: '30', name: 'Montana' }, { state_fips: '31', name: 'Nebraska' },
  { state_fips: '32', name: 'Nevada' }, { state_fips: '33', name: 'New Hampshire' },
  { state_fips: '34', name: 'New Jersey' }, { state_fips: '35', name: 'New Mexico' },
  { state_fips: '36', name: 'New York' }, { state_fips: '37', name: 'North Carolina' },
  { state_fips: '38', name: 'North Dakota' }, { state_fips: '39', name: 'Ohio' },
  { state_fips: '40', name: 'Oklahoma' }, { state_fips: '41', name: 'Oregon' },
  { state_fips: '42', name: 'Pennsylvania' }, { state_fips: '44', name: 'Rhode Island' },
  { state_fips: '45', name: 'South Carolina' }, { state_fips: '46', name: 'South Dakota' },
  { state_fips: '47', name: 'Tennessee' }, { state_fips: '48', name: 'Texas' },
  { state_fips: '49', name: 'Utah' }, { state_fips: '50', name: 'Vermont' },
  { state_fips: '51', name: 'Virginia' }, { state_fips: '53', name: 'Washington' },
  { state_fips: '54', name: 'West Virginia' }, { state_fips: '55', name: 'Wisconsin' },
  { state_fips: '56', name: 'Wyoming' },
];

let _lastSummaryStats = null;

// Full county list for the current metro / state.
//   availableCounties: [{ geoid5, county_state }]
//   selectedCounties:  [{ geoid5, label }] — subset whose checkboxes are checked
let availableCounties = [];
let selectedCounties = [];

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

function initCollapsibleToggle(toggleId, panelId, chevronId) {
  const toggle = document.getElementById(toggleId);
  const panel = document.getElementById(panelId);
  const chevron = chevronId ? document.getElementById(chevronId) : null;
  if (!toggle || !panel) return;
  toggle.addEventListener('click', () => {
    const isOpen = panel.style.display !== 'none';
    panel.style.display = isOpen ? 'none' : 'block';
    if (chevron) chevron.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(90deg)';
  });
}

function updateCountyState() {
  // Mirror the current selection into a global the overlays + map modules
  // read from (city-boundary state filter, county-mask toggle).
  window.currentGeoidList = selectedCounties.map((c) => c.geoid5);
  const countEl = document.getElementById('dl-county-count');
  const totalEl = document.getElementById('dl-county-total');
  if (countEl) countEl.textContent = String(selectedCounties.length);
  if (totalEl) totalEl.textContent = String(availableCounties.length);
}

function renderCountyList() {
  const list = document.getElementById('dl-county-list');
  if (!list) return;
  list.innerHTML = '';
  availableCounties.forEach(({ geoid5, label }) => {
    const row = document.createElement('label');
    row.style.cssText = 'display:flex; align-items:center; gap:6px; padding:3px 0; cursor:pointer;';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = geoid5;
    cb.checked = selectedCounties.some((c) => c.geoid5 === geoid5);
    cb.style.margin = '0';
    cb.addEventListener('change', () => {
      if (cb.checked) {
        if (!selectedCounties.some((c) => c.geoid5 === geoid5)) {
          selectedCounties.push({ geoid5, label });
        }
      } else {
        selectedCounties = selectedCounties.filter((c) => c.geoid5 !== geoid5);
      }
      updateCountyState();
    });
    const span = document.createElement('span');
    span.textContent = label;
    row.appendChild(cb);
    row.appendChild(span);
    list.appendChild(row);
  });
  updateCountyState();
}

function clearCountyList() {
  availableCounties = [];
  selectedCounties = [];
  renderCountyList();
}

async function loadCountiesForSelection(item) {
  const type = document.getElementById('dl-geo-type').value;
  let counties = [];
  if (type === 'metro') {
    const res = await fetch(`${API.cbsaCounties}/${item.cbsa_code}`);
    if (!res.ok) { showGeoError('Failed to load CBSA counties'); return; }
    counties = await res.json();
    window.currentCbsaCode = item.cbsa_code;
    window.currentPrincipalCity = item.principal_city || null;
    window.currentStateFp = counties[0]?.geoid5?.substring(0, 2) || null;
  } else {
    const res = await fetch(`${API.stateCounties}/${item.state_fips}`);
    if (!res.ok) { showGeoError('Failed to load state counties'); return; }
    counties = await res.json();
    window.currentCbsaCode = null;
    window.currentPrincipalCity = null;
    window.currentStateFp = item.state_fips;
  }
  availableCounties = counties.map((c) => ({
    geoid5: c.geoid5,
    label: c.county_state || c.geoid5,
  }));
  // Default: all counties checked.
  selectedCounties = availableCounties.map((c) => ({ geoid5: c.geoid5, label: c.label }));
  renderCountyList();
  updateCityBoundaryLabel();
}

function initSelectAllButtons() {
  document.getElementById('dl-select-all-btn')?.addEventListener('click', () => {
    selectedCounties = availableCounties.map((c) => ({ geoid5: c.geoid5, label: c.label }));
    renderCountyList();
  });
  document.getElementById('dl-deselect-all-btn')?.addEventListener('click', () => {
    selectedCounties = [];
    renderCountyList();
  });
}

function updateCityBoundaryLabel() {
  // Reset the city checkbox list back to its empty-state hint. The real
  // entries get populated by addCityBoundaries() in overlays.js after
  // the rendered tileset features have been intersect-filtered.
  if (typeof window.dotlenderSetAvailableCities === 'function') {
    window.dotlenderSetAvailableCities([]);
  }
}

// --- City boundary checkbox list -----------------------------------------

// Module-level state for the sidebar city list.
let availableCities = [];
let selectedCities = new Set();

function renderCityCheckboxes() {
  const list = document.getElementById('dl-city-list');
  if (!list) return;
  list.innerHTML = '';
  if (availableCities.length === 0) {
    list.innerHTML = '<div style="color:#999; font-style:italic; font-size:0.78rem;">Render a map to see available cities</div>';
    return;
  }
  availableCities.forEach((city) => {
    const key = `${city.stateFp}:${city.name}`;
    const row = document.createElement('label');
    row.style.cssText = 'display:flex; align-items:center; gap:6px; padding:3px 0; cursor:pointer;';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = key;
    cb.checked = selectedCities.has(key);
    cb.style.margin = '0';
    cb.addEventListener('change', () => {
      if (cb.checked) selectedCities.add(key);
      else selectedCities.delete(key);
      pushCitySelection();
    });
    const span = document.createElement('span');
    span.textContent = city.name;
    row.appendChild(cb);
    row.appendChild(span);
    list.appendChild(row);
  });
}

function pushCitySelection() {
  window.dotlenderSelectedCities = availableCities.filter(
    (c) => selectedCities.has(`${c.stateFp}:${c.name}`),
  );
  if (typeof window.dotlenderApplyCityFilter === 'function') {
    window.dotlenderApplyCityFilter();
  }
}

window.dotlenderSetAvailableCities = function (cities) {
  availableCities = cities || [];
  // Default selection = all available cities on each render.
  selectedCities = new Set(availableCities.map((c) => `${c.stateFp}:${c.name}`));
  renderCityCheckboxes();
  pushCitySelection();
};

function initCityListButtons() {
  document.getElementById('dl-city-select-all-btn')?.addEventListener('click', () => {
    selectedCities = new Set(availableCities.map((c) => `${c.stateFp}:${c.name}`));
    renderCityCheckboxes();
    pushCitySelection();
  });
  document.getElementById('dl-city-deselect-all-btn')?.addEventListener('click', () => {
    selectedCities = new Set();
    renderCityCheckboxes();
    pushCitySelection();
  });
}

function showGeoError(msg) {
  const el = document.getElementById('dl-geo-error');
  if (!el) return;
  el.textContent = msg;
  el.style.display = 'block';
}

function hideGeoError() {
  const el = document.getElementById('dl-geo-error');
  if (el) el.style.display = 'none';
}

function initGeoSearch() {
  const geoType = document.getElementById('dl-geo-type');
  const input = document.getElementById('dl-geo-search');
  const suggestions = document.getElementById('dl-geo-suggestions');
  if (!geoType || !input || !suggestions) return;
  let debounce;

  async function doSearch(q) {
    if (geoType.value === 'metro') {
      const res = await fetch(`${API.cbsaSearch}?q=${encodeURIComponent(q)}`);
      if (!res.ok) return [];
      return res.json();
    }
    const term = q.toLowerCase();
    return STATE_LIST.filter((s) => s.name.toLowerCase().includes(term)).slice(0, 10);
  }

  input.addEventListener('input', () => {
    clearTimeout(debounce);
    hideGeoError();
    if (input.value.length < 2) { suggestions.style.display = 'none'; return; }
    debounce = setTimeout(async () => {
      const results = await doSearch(input.value);
      suggestions.innerHTML = '';
      if (!results.length) { suggestions.style.display = 'none'; return; }
      results.forEach((item) => {
        const a = document.createElement('a');
        a.href = '#';
        a.style.cssText = 'padding:6px 10px; display:block; text-decoration:none; color:#333; font-size:0.82rem;';
        a.textContent = geoType.value === 'metro'
          ? `${item.cbsa_name} (${item.county_count} counties)`
          : item.name;
        a.addEventListener('click', async (e) => {
          e.preventDefault();
          suggestions.style.display = 'none';
          input.value = geoType.value === 'metro' ? item.cbsa_name : item.name;
          await loadCountiesForSelection(item);
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

  geoType.addEventListener('change', () => {
    input.value = '';
    clearCountyList();
    suggestions.style.display = 'none';
    window.currentCbsaCode = null;
    window.currentPrincipalCity = null;
    window.currentStateFp = null;
    updateCityBoundaryLabel();
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
    if (input.value.length < 2) { suggestions.style.display = 'none'; return; }
    debounce = setTimeout(async () => {
      const yearStart = document.getElementById('dl-year-start').value;
      const yearEnd = document.getElementById('dl-year-end').value;
      const url = `${API.lenderSearch}?q=${encodeURIComponent(input.value)}&year_start=${yearStart}&year_end=${yearEnd}`;
      const res = await fetch(url);
      if (!res.ok) { suggestions.style.display = 'none'; return; }
      const data = await res.json();
      suggestions.innerHTML = '';
      if (!data.length) { suggestions.style.display = 'none'; return; }
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
  const densityEl = document.getElementById('dl-density-value');
  const geoType = document.getElementById('dl-geo-type').value;
  return {
    geo_type: geoType,
    geoid5_list: selectedCounties.map((c) => c.geoid5),
    cbsa_code: window.currentCbsaCode || null,
    state_fips: window.currentStateFp || null,
    selected_counties: selectedCounties.slice(),
    year_start: parseInt(document.getElementById('dl-year-start').value, 10),
    year_end: parseInt(document.getElementById('dl-year-end').value, 10),
    lei: document.getElementById('dl-lender-lei').value || null,
    lender_name: document.getElementById('dl-lender-search').value.trim() || 'All lenders',
    overlay_mode: document.getElementById('dl-overlay-mode').value,
    dot_density: densityEl ? parseInt(densityEl.value, 10) : 1,
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

export function getLastSummaryStats() { return _lastSummaryStats; }

export function initRenderButton(onRender) {
  document.getElementById('dl-render-btn').addEventListener('click', async () => {
    const state = getFilterState();
    const errEl = document.getElementById('dl-map-error');
    if (!state.geoid5_list.length) {
      errEl.textContent = 'Please select a metro or state, then pick at least one county.';
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
    if (spinner) spinner.style.display = 'inline-block';
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
      if (spinner) spinner.style.display = 'none';
      btn.disabled = false;
    }
  });
}

function displaySummaryStats(stats) {
  if (!stats) {
    const el = document.getElementById('dl-summary-stats');
    if (el) el.style.display = 'none';
    return;
  }
  const el = document.getElementById('dl-stats-content');
  if (!el) return;
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
  initCollapsibleToggle('dl-advanced-toggle', 'dotlender-advanced-filters', 'dl-advanced-chevron');
  initCollapsibleToggle('dl-race-toggle', 'dl-race-filters', 'dl-race-chevron');
  initGeoSearch();
  initLenderTypeahead();
  initSelectAllButtons();
  initCityListButtons();
});
