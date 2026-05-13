// dotlender_map.js
// Mapbox GL JS map initialization and layer management for DotLender.
// Mirrors BranchMapper's stack: mapbox-gl v3, jedlebi.census-tracts vector tileset.

import { getFilterState, initRenderButton } from './dotlender_filters.js';
import {
  addCountyMask, removeCountyMask, clearCachedCounty,
  addCityBoundaries, removeCityBoundaries,
  updateTitleOverlay, updateLegend,
  hideNonShieldLabels,
} from './dotlender_overlays.js';

// NCRC race/ethnicity color palette — keyed on the derived_race string returned
// by /api/map-data (built server-side from is_* flags in queries.DERIVED_RACE_SQL).
export const RACE_COLORS = {
  'Hispanic or Latino': '#e41a1c',
  'Black or African American': '#377eb8',
  'Asian': '#4daf4a',
  'American Indian or Alaska Native': '#984ea3',
  'Two or More Races': '#ff7f00',
  'White': '#a65628',
  'Unknown or Not Provided': '#999999',
};

// Default dot color when no race filter is active (all races combined).
export const RACE_ALL_COLOR = '#222222';

// "Other / Unknown" checkbox value expands to these race buckets.
const OTHER_RACE_BUCKETS = [
  'Unknown or Not Provided',
  'American Indian or Alaska Native',
  'Two or More Races',
];

// Jitter halfwidth in degrees applied around tract centroids (~890m N–S).
// Tight enough to keep dots inside most tract polygons.
const JITTER_DEGREES = 0.016;

// Income band fill colors (used for the spec's choropleth legend on the canvas;
// the live map uses the tileset's own pre-baked income_category coloring).
export const INCOME_BAND_COLORS = {
  low: '#d73027',
  moderate: '#fc8d59',
  middle: '#fee090',
  upper: '#e0f3f8',
  unknown: '#cccccc',
};

const MAPBOX_STYLE = 'mapbox://styles/jedlebi/cltg2vre600wz01p02c3jf3h3';
const CENSUS_TILESET_ID = 'jedlebi.census-tracts';
const CENSUS_SOURCE_LAYER = 'census_tracts';

const STATE_FIPS_TO_BOUNDS = {
  // minimal lookup for state-level fitBounds fallback (lng/lat); add more as needed
  // [west, south, east, north]
  '11': [-77.12, 38.79, -76.91, 39.00],   // DC
  '06': [-124.5, 32.5, -114.1, 42.1],     // CA
  '36': [-79.8, 40.5, -71.8, 45.0],       // NY
  '48': [-106.7, 25.8, -93.5, 36.5],      // TX
};

let map = null;
let mapLoaded = false;
let currentMapData = null;
let currentOverlayMode = 'minority';
let currentTooltipPopup = null;
// FIPS of the most recently rendered county, used by the county mask toggle.
let currentFips = null;

// --- Color expressions (mirror BranchMapper) ------------------------------

function incomeFillColor() {
  // Tileset property "income_category" values: 'Low','Moderate','Middle','Upper'
  return [
    'match',
    ['get', 'income_category'],
    'Low', INCOME_BAND_COLORS.low,
    'Moderate', INCOME_BAND_COLORS.moderate,
    'Middle', INCOME_BAND_COLORS.middle,
    'Upper', INCOME_BAND_COLORS.upper,
    INCOME_BAND_COLORS.unknown,
  ];
}

function minorityFillColor() {
  // Tileset property "minority_category" values: 'Q1 (Lowest 25%)' … 'Q4 (Highest 25%)'
  return [
    'match',
    ['get', 'minority_category'],
    'Q1 (Lowest 25%)', '#deebf7',
    'Q2 (25-50%)', '#9ecae1',
    'Q3 (50-75%)', '#3182bd',
    'Q4 (Highest 25%)', '#08519c',
    '#cccccc',
  ];
}

function raceCircleColor() {
  // Match on Feature property "derived_race"
  return [
    'match',
    ['get', 'derived_race'],
    'Hispanic or Latino', RACE_COLORS['Hispanic or Latino'],
    'Black or African American', RACE_COLORS['Black or African American'],
    'Asian', RACE_COLORS['Asian'],
    'American Indian or Alaska Native', RACE_COLORS['American Indian or Alaska Native'],
    'Two or More Races', RACE_COLORS['Two or More Races'],
    'White', RACE_COLORS['White'],
    RACE_COLORS['Unknown or Not Provided'],
  ];
}

// --- Map init -------------------------------------------------------------

function initMap() {
  const token = window.DOTLENDER_MAPBOX_TOKEN;
  if (!token) {
    const errEl = document.getElementById('dl-map-error');
    errEl.textContent = 'MAPBOX_ACCESS_TOKEN is not configured — the map cannot render.';
    errEl.style.display = 'block';
    return;
  }
  // eslint-disable-next-line no-undef
  mapboxgl.accessToken = token;
  // eslint-disable-next-line no-undef
  map = new mapboxgl.Map({
    container: 'dotlender-map',
    style: MAPBOX_STYLE,
    center: [-96, 38.5],
    zoom: 3.5,
    // Required so getCanvas().toDataURL() returns a populated image instead
    // of a blank buffer (WebGL clears its drawing buffer between frames by
    // default). Used by the canvas builder to capture the map for PDF.
    preserveDrawingBuffer: true,
  });
  // Expose for the canvas module to capture the map natively.
  window.dotlenderMap = map;
  // eslint-disable-next-line no-undef
  map.addControl(new mapboxgl.NavigationControl(), 'top-right');
  // Note: scale bar + north arrow moved to the PDF canvas builder.
  // The live map relies on Mapbox's default zoom/rotate controls only.

  map.on('load', () => {
    addCensusLayers();
    addDotsLayer();
    hideNonShieldLabels();
    mapLoaded = true;
  });
  map.on('style.load', () => hideNonShieldLabels());
}

function addCensusLayers() {
  // Vector tileset — same source BranchMapper uses
  map.addSource('census-tileset', {
    type: 'vector',
    url: `mapbox://${CENSUS_TILESET_ID}`,
    minzoom: 5,
    maxzoom: 12,
  });
  // Insert choropleth under the road network: roads paint on top.
  const beforeChoropleth = map.getLayer('road-minor-case') ? 'road-minor-case' : undefined;

  map.addLayer({
    id: 'dl-income-fill', type: 'fill',
    source: 'census-tileset', 'source-layer': CENSUS_SOURCE_LAYER,
    paint: { 'fill-color': incomeFillColor(), 'fill-opacity': 0.45 },
    layout: { visibility: 'none' },
  }, beforeChoropleth);
  map.addLayer({
    id: 'dl-income-outline', type: 'line',
    source: 'census-tileset', 'source-layer': CENSUS_SOURCE_LAYER,
    paint: { 'line-color': '#666', 'line-width': 0.3, 'line-opacity': 0.4 },
    layout: { visibility: 'none' },
  }, beforeChoropleth);
  map.addLayer({
    id: 'dl-minority-fill', type: 'fill',
    source: 'census-tileset', 'source-layer': CENSUS_SOURCE_LAYER,
    paint: { 'fill-color': minorityFillColor(), 'fill-opacity': 0.45 },
    layout: { visibility: 'none' },
  }, beforeChoropleth);
  map.addLayer({
    id: 'dl-minority-outline', type: 'line',
    source: 'census-tileset', 'source-layer': CENSUS_SOURCE_LAYER,
    paint: { 'line-color': '#666', 'line-width': 0.3, 'line-opacity': 0.4 },
    layout: { visibility: 'none' },
  }, beforeChoropleth);
}

function addDotsLayer() {
  map.addSource('dl-dots', { type: 'geojson', data: emptyFC() });
  // Dots above roads but below the shield labels so route shields stay
  // readable on top of the dot field.
  const beforeDots = map.getLayer('road-number-shield') ? 'road-number-shield' : undefined;
  map.addLayer({
    id: 'dl-dots-circles',
    type: 'circle',
    source: 'dl-dots',
    paint: {
      'circle-radius': 3,
      'circle-color': RACE_ALL_COLOR,
      'circle-opacity': 0.8,
      'circle-stroke-width': 0,
    },
  }, beforeDots);
}

function emptyFC() { return { type: 'FeatureCollection', features: [] }; }

// --- Render ---------------------------------------------------------------

function setOverlayVisibility(mode) {
  currentOverlayMode = mode;
  const showIncome = mode === 'income';
  const showMinority = mode === 'minority';
  ['dl-income-fill', 'dl-income-outline'].forEach((id) => {
    map.setLayoutProperty(id, 'visibility', showIncome ? 'visible' : 'none');
  });
  ['dl-minority-fill', 'dl-minority-outline'].forEach((id) => {
    map.setLayoutProperty(id, 'visibility', showMinority ? 'visible' : 'none');
  });
}

// Pre-compute per-dot jitter once per API response so density changes are
// purely additive (same dots, fewer of them) instead of re-randomizing.
function stableJitter(dotData) {
  return dotData.map((tract) => ({
    ...tract,
    _jitter: Array.from({ length: tract.dot_count || 0 }, () => ({
      dlat: (Math.random() - 0.5) * JITTER_DEGREES,
      dlng: (Math.random() - 0.5) * JITTER_DEGREES,
    })),
  }));
}

function buildDotFeatures(dotData, densityRatio = 1) {
  // True subsample: each tract emits floor(n / stride) dots at indices
  // [0, stride, 2*stride, ...]. A tract with 2 raw dots at stride=5
  // emits 0 dots — no per-tract minimum, so voids in lending stay visible.
  const features = [];
  let rawTotal = 0;
  const stride = Math.max(1, parseInt(densityRatio, 10) || 1);
  dotData.forEach((row) => {
    if (row.centroid_lat == null || row.centroid_lng == null) return;
    const n = row._jitter?.length || 0;
    rawTotal += n;
    for (let k = 0, count = Math.floor(n / stride); k < count; k += 1) {
      const j = row._jitter[k * stride];
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [row.centroid_lng + j.dlng, row.centroid_lat + j.dlat] },
        properties: { derived_race: row.derived_race, census_tract: row.census_tract },
      });
    }
  });
  // eslint-disable-next-line no-console
  console.log(`[dotlender] density stride=${stride}  raw dots=${rawTotal}  rendered=${features.length}`);
  return { type: 'FeatureCollection', features };
}

// --- Race filter wiring ---------------------------------------------------

export function getActiveRaceFilters() {
  const allCb = document.getElementById('dl-race-all');
  if (!allCb || allCb.checked) return 'all';
  const checked = [];
  document.querySelectorAll('.dl-race-cb:not(#dl-race-all):checked').forEach((cb) => {
    if (cb.value === 'other') {
      checked.push(...OTHER_RACE_BUCKETS);
    } else {
      checked.push(cb.value);
    }
  });
  // If user unchecks every specific box, fall back to 'all' so the layer
  // doesn't go blank.
  return checked.length ? checked : 'all';
}

function applyDotsStyle() {
  if (!map || !map.getLayer('dl-dots-circles')) return;
  const active = getActiveRaceFilters();
  if (active === 'all') {
    map.setFilter('dl-dots-circles', null);
    map.setPaintProperty('dl-dots-circles', 'circle-color', RACE_ALL_COLOR);
  } else {
    map.setFilter('dl-dots-circles', ['in', ['get', 'derived_race'], ['literal', active]]);
    map.setPaintProperty('dl-dots-circles', 'circle-color', raceCircleColor());
  }
  // Refresh the legend overlay so it mirrors the current race filter state.
  updateLegend(currentOverlayMode, active);
}

function getDensityRatio() {
  const el = document.getElementById('dl-density-value');
  if (!el) return 1;
  const v = parseInt(el.value, 10);
  return Number.isFinite(v) && v > 0 ? v : 1;
}

function rebuildDotsFromCache() {
  if (!map || !map.getSource('dl-dots') || !window.dotlenderDotData) return;
  const fc = buildDotFeatures(window.dotlenderDotData, getDensityRatio());
  map.getSource('dl-dots').setData(fc);
  applyDotsStyle();
}

function initRaceFilters() {
  document.querySelectorAll('.dl-race-cb').forEach((cb) => {
    cb.addEventListener('change', () => {
      // 'all' was clicked on → uncheck specifics
      if (cb.id === 'dl-race-all' && cb.checked) {
        document.querySelectorAll('.dl-race-cb:not(#dl-race-all)').forEach((c) => { c.checked = false; });
      }
      // A specific race was clicked on → uncheck 'all'
      if (cb.id !== 'dl-race-all' && cb.checked) {
        const allCb = document.getElementById('dl-race-all');
        if (allCb) allCb.checked = false;
      }
      applyDotsStyle();
    });
  });
}

function clampDensity(n) {
  const v = parseInt(n, 10);
  if (!Number.isFinite(v) || v < 1) return 1;
  if (v > 999) return 999;
  return v;
}

function setDensityLabel() {
  const label = document.getElementById('dl-density-label');
  const input = document.getElementById('dl-density-value');
  if (!label || !input) return;
  const v = clampDensity(input.value);
  label.textContent = v === 1 ? ' — 1 dot per loan' : ` — 1 dot per ${v} loans`;
}

function initDensityInput() {
  const input = document.getElementById('dl-density-value');
  if (!input) return;
  const step = (delta) => {
    input.value = clampDensity((parseInt(input.value, 10) || 1) + delta);
    setDensityLabel();
    rebuildDotsFromCache();
  };
  setDensityLabel();
  document.getElementById('dl-density-up')?.addEventListener('click', () => step(1));
  document.getElementById('dl-density-down')?.addEventListener('click', () => step(-1));
  input.addEventListener('change', () => {
    input.value = clampDensity(input.value);
    setDensityLabel();
    rebuildDotsFromCache();
  });
}

function fitToGeographyByFips(stateFips) {
  if (!stateFips) return;
  const b = STATE_FIPS_TO_BOUNDS[stateFips];
  if (b) map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 30, duration: 600 });
}

function fitToDots(dotsFC) {
  if (!dotsFC.features.length) return;
  let minLng = Infinity, minLat = Infinity, maxLng = -Infinity, maxLat = -Infinity;
  dotsFC.features.forEach((f) => {
    const [lng, lat] = f.geometry.coordinates;
    if (lng < minLng) minLng = lng; if (lat < minLat) minLat = lat;
    if (lng > maxLng) maxLng = lng; if (lat > maxLat) maxLat = lat;
  });
  const pad = 0.05;
  map.fitBounds(
    [[minLng - pad, minLat - pad], [maxLng + pad, maxLat + pad]],
    { padding: 30, duration: 600 },
  );
}

function renderMap(mapData, state) {
  if (!mapLoaded) {
    map.once('load', () => renderMap(mapData, state));
    return;
  }
  setOverlayVisibility(state.overlay_mode);

  // Cache raw dot rows augmented with stable per-dot jitter offsets so that
  // density changes (and race-filter changes) re-render against the same
  // dot positions instead of re-randomizing on every redraw.
  window.dotlenderDotData = stableJitter(mapData.dots || []);

  const dotsFC = buildDotFeatures(window.dotlenderDotData, getDensityRatio());
  map.getSource('dl-dots').setData(dotsFC);
  applyDotsStyle();

  // County mask only applies when exactly one county is selected. For
  // multi-county metros and state-level selections we skip the mask and
  // fit to the rendered dots instead (a true multi-county mask would
  // require unioning multiple ArcGIS polygons — out of scope for now).
  const geoidList = state.geoid5_list || [];
  if (geoidList.length === 1) {
    currentFips = geoidList[0];
    clearCachedCounty();
    removeCountyMask();
    const cbCb = document.getElementById('dl-show-county-boundary');
    if (!cbCb || cbCb.checked) addCountyMask(currentFips);
    else fitToDots(dotsFC);
  } else {
    currentFips = null;
    clearCachedCounty();
    removeCountyMask();
    if (state.geo_type === 'state' && state.state_fips) {
      fitToGeographyByFips(state.state_fips);
    } else {
      fitToDots(dotsFC);
    }
  }

  // Title + legend overlays
  updateTitleOverlay(state);
  updateLegend(state.overlay_mode, getActiveRaceFilters());

  // Choropleth tooltip — show per-tract loan count from server, joined by census_tract
  const tractLoans = {};
  (mapData.choropleth || []).forEach((t) => { tractLoans[t.census_tract] = t; });
  attachChoroplethTooltip(tractLoans);
}

function attachChoroplethTooltip(tractLoans) {
  if (currentTooltipPopup) {
    currentTooltipPopup.remove();
    currentTooltipPopup = null;
  }
  ['dl-income-fill', 'dl-minority-fill'].forEach((layerId) => {
    map.off('mousemove', layerId);
    map.off('mouseleave', layerId);
  });
  // eslint-disable-next-line no-undef
  const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false });
  const onMove = (e) => {
    if (!e.features?.length) return;
    // If a county mask is active, the mask fill covers everything OUTSIDE
    // the selected county. When the cursor is over the mask, we're outside
    // — suppress the popup.
    if (map.getLayer('dl-county-mask-fill')) {
      const outside = map.queryRenderedFeatures(e.point, { layers: ['dl-county-mask-fill'] });
      if (outside.length) {
        popup.remove();
        map.getCanvas().style.cursor = '';
        return;
      }
    }
    const props = e.features[0].properties || {};
    const tractId = props.GEOID || props.geoid || props.geoid11 || '';
    const lendingRow = tractLoans[tractId];
    const html = `
      <strong>Tract ${tractId}</strong><br/>
      Income: ${props.income_category ?? '—'}<br/>
      Minority quartile: ${props.minority_category ?? '—'}<br/>
      Loans this filter: ${lendingRow ? lendingRow.loan_count.toLocaleString() : '0'}
    `;
    popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
    map.getCanvas().style.cursor = 'pointer';
  };
  const onLeave = () => {
    popup.remove();
    map.getCanvas().style.cursor = '';
  };
  ['dl-income-fill', 'dl-minority-fill'].forEach((layerId) => {
    map.on('mousemove', layerId, onMove);
    map.on('mouseleave', layerId, onLeave);
  });
  currentTooltipPopup = popup;
}

export function getCurrentMapData() { return currentMapData; }
export function getMapboxInstance() { return map; }

function initOverlayToggles() {
  document.getElementById('dl-show-county-boundary')?.addEventListener('change', (e) => {
    if (!currentFips) return;
    if (e.target.checked) addCountyMask(currentFips); else removeCountyMask();
  });
  document.getElementById('dl-show-city-boundary')?.addEventListener('change', (e) => {
    if (e.target.checked) addCityBoundaries(); else removeCityBoundaries();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initRaceFilters();
  initDensityInput();
  initOverlayToggles();
  initRenderButton((mapData, state) => {
    currentMapData = mapData;
    renderMap(mapData, state);
    const btn = document.getElementById('dl-build-report-btn');
    if (btn) btn.style.display = 'block';
  });
});
