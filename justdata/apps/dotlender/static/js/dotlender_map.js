// dotlender_map.js
// Mapbox GL JS map initialization and layer management for DotLender.
// Mirrors BranchMapper's stack: mapbox-gl v3, jedlebi.census-tracts vector tileset.

import { getFilterState, initRenderButton } from './dotlender_filters.js';
import {
  addCountyMask, removeCountyMask, clearCachedCounty,
  addCityBoundaries,
  updateTitleOverlay, updateLegend,
  hideNonShieldLabels,
} from './dotlender_overlays.js';
import {
  RACE_COLORS, RACE_ALL_COLOR, OTHER_RACE_BUCKETS,
  collectTractPolygons, getCachedTractPolygons,
  stableJitterAsync, buildDotFeatures,
} from './dotlender_dots.js';

// Re-export the palette so other modules (canvas legend, future overlays)
// keep a stable import path even though the constants live in dots.js now.
export { RACE_COLORS, RACE_ALL_COLOR };

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
// FIPS list of the most recently rendered counties, used by the county
// mask toggle. May be a single county or a multi-county metro selection.
let currentGeoidList = [];

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
    'rgba(0,0,0,0)',
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
    'rgba(0,0,0,0)',
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
  // Refresh the tract polygon cache after pan/zoom so a subsequent
  // Build Report sees the up-to-date set of rendered tracts. We do NOT
  // re-place dots here — dot positions stay stable for the user-visible
  // session; only polygon cache is refreshed.
  map.on('moveend', () => {
    if ((window.dotlenderRawDots || []).length) collectTractPolygons(map);
  });
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

  // Tract outlines removed — the choropleth reads as a clean color field
  // without per-tract borders. fill-outline-color is also omitted from the
  // paint spec (its absence is what removes the outline).
  map.addLayer({
    id: 'dl-income-fill', type: 'fill',
    source: 'census-tileset', 'source-layer': CENSUS_SOURCE_LAYER,
    paint: {
      'fill-color': incomeFillColor(),
      'fill-opacity': 0.45,
      // Suppress Mapbox's default 1px tract outline.
      'fill-outline-color': 'rgba(0,0,0,0)',
      // Disable antialiasing so adjacent tract polygons meet flush
      // instead of revealing a sub-pixel white seam at every edge.
      'fill-antialias': false,
    },
    layout: { visibility: 'none' },
  }, beforeChoropleth);
  map.addLayer({
    id: 'dl-minority-fill', type: 'fill',
    source: 'census-tileset', 'source-layer': CENSUS_SOURCE_LAYER,
    paint: {
      'fill-color': minorityFillColor(),
      'fill-opacity': 0.45,
      'fill-outline-color': 'rgba(0,0,0,0)',
      'fill-antialias': false,
    },
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
      // Color is baked into each feature's properties.color by
      // buildDotFeatures in dotlender_dots.js — read it directly here.
      'circle-color': ['get', 'color'],
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
  ['dl-income-fill'].forEach((id) => {
    map.setLayoutProperty(id, 'visibility', showIncome ? 'visible' : 'none');
  });
  ['dl-minority-fill'].forEach((id) => {
    map.setLayoutProperty(id, 'visibility', showMinority ? 'visible' : 'none');
  });
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
  // Color is baked into each Feature's properties.color (buildDotFeatures
  // emits it based on the active race filter). Filter changes trigger a
  // full feature rebuild via rebuildDotsFromCache rather than setFilter.
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
  const fc = buildDotFeatures(
    window.dotlenderDotData, getDensityRatio(), getActiveRaceFilters(),
  );
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

// Fit map to the lat/lng bounding box of the raw API centroid data. Used
// when no county mask applies, before deferred polygon-sampled dot
// placement has run (so we can't yet use the rendered point geometries).
function fitToRawCentroids(rawDots) {
  if (!rawDots?.length) return;
  let minLng = Infinity; let minLat = Infinity;
  let maxLng = -Infinity; let maxLat = -Infinity;
  let any = false;
  rawDots.forEach((r) => {
    if (r.centroid_lng == null || r.centroid_lat == null) return;
    any = true;
    if (r.centroid_lng < minLng) minLng = r.centroid_lng;
    if (r.centroid_lat < minLat) minLat = r.centroid_lat;
    if (r.centroid_lng > maxLng) maxLng = r.centroid_lng;
    if (r.centroid_lat > maxLat) maxLat = r.centroid_lat;
  });
  if (!any) return;
  const pad = 0.05;
  map.fitBounds(
    [[minLng - pad, minLat - pad], [maxLng + pad, maxLat + pad]],
    { padding: 30, duration: 600 },
  );
}

// Run polygon collection + async dot placement once the choropleth tiles
// have rendered at the current viewport. queryRenderedFeatures only
// returns features that have actually been painted, so this must be
// deferred until the next 'idle' event.
async function scheduleDotPlacement() {
  if (!map) return;
  const placeDots = async () => {
    collectTractPolygons(map);
    const polygons = getCachedTractPolygons();
    const raw = window.dotlenderRawDots || [];
    window.dotlenderDotData = await stableJitterAsync(raw, polygons);
    if (!map.getSource('dl-dots')) return;
    const fc = buildDotFeatures(
      window.dotlenderDotData, getDensityRatio(), getActiveRaceFilters(),
    );
    map.getSource('dl-dots').setData(fc);
    applyDotsStyle();
  };
  map.once('idle', placeDots);
  map.triggerRepaint();
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

async function renderMap(mapData, state) {
  if (!mapLoaded) {
    map.once('load', () => renderMap(mapData, state));
    return;
  }
  setOverlayVisibility(state.overlay_mode);

  // Defer dot placement until the choropleth tiles have actually rendered
  // at the current viewport — that's when queryRenderedFeatures will
  // return tract polygons we can sample. Collect polygons inside the idle
  // callback, then async-sample positions so the UI thread stays
  // responsive on big datasets.
  window.dotlenderRawDots = mapData.dots || [];
  scheduleDotPlacement();

  // County mask: single county or unioned multi-county selection. State-
  // level selections are too broad to mask (too many counties to fetch
  // and union), so we fit to raw centroids instead.
  const geoidList = state.geoid5_list || [];
  currentGeoidList = geoidList.slice();
  clearCachedCounty();
  removeCountyMask();
  if (geoidList.length && state.geo_type !== 'state') {
    const cbCb = document.getElementById('dl-show-county-boundary');
    if (!cbCb || cbCb.checked) addCountyMask(currentGeoidList);
    else fitToRawCentroids(window.dotlenderRawDots);
  } else if (state.geo_type === 'state' && state.state_fips) {
    fitToGeographyByFips(state.state_fips);
  } else {
    fitToRawCentroids(window.dotlenderRawDots);
  }

  // Title + legend overlays
  updateTitleOverlay(state);
  updateLegend(state.overlay_mode, getActiveRaceFilters());

  // City boundary layer + sidebar checkbox population. Adds the source/
  // layer once and pushes available cities to dotlender_filters.js; the
  // user toggles individual city visibility from the sidebar list.
  addCityBoundaries();

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
    if (!currentGeoidList.length) return;
    if (e.target.checked) addCountyMask(currentGeoidList); else removeCountyMask();
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
