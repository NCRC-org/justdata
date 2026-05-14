// dotlender_race_overlay.js
// Race-share choropleth overlays for DotLender. Architecture:
// - Separate Mapbox source 'race-overlay' that re-binds the same
//   jedlebi.census-tracts tileset with promoteId: { census_tracts: 'GEOID' }
//   so we can drive fill colors via setFeatureState.
// - One fill layer 'dl-race-fill' whose fill-color is a step expression
//   over ['feature-state', 'pct']. Default 3 breakpoints (quartiles); user
//   can override via the sidebar Breakpoints panel.
// - loadRaceOverlay() POSTs to /dotlender/api/race-choropleth, then for
//   each returned tract calls map.setFeatureState({source, sourceLayer, id:
//   geoid}, {pct}). Mapbox handles the fill in GPU.
//
// Exposed globals used by other modules:
//   window.dotlenderApplyCustomBreakpoints(breakpoints)
//   window.dotlenderCurrentBreakpoints
//   window.dotlenderCurrentRaceOverlay
//   window.dotlenderRaceFeatureStates (the {geoid: pct} cache)

import {
  getMapboxInstance, CENSUS_TILESET_ID, CENSUS_SOURCE_LAYER,
} from './dotlender_map.js';

const API = '/dotlender/api/race-choropleth';

// Sequential color ramps (5 stops each, light -> dark). Default ramp
// (blue-purple) is used for races that don't have a specific ramp; the
// warm ramps highlight historically over- or under-represented groups.
export const RACE_RAMP_DEFAULT = ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#084594'];
export const RACE_RAMP_BLACK    = ['#fff5eb', '#fdd0a2', '#fd8d3c', '#d94801', '#7f2704'];
export const RACE_RAMP_HISPANIC = ['#f7fcf5', '#c7e9c0', '#74c476', '#238b45', '#00441b'];
export const RACE_RAMP_WHITE    = ['#fcfbfd', '#dadaeb', '#9e9ac8', '#6a51a3', '#3f007d'];

export const RACE_RAMPS = {
  race_black:          RACE_RAMP_BLACK,
  race_hispanic:       RACE_RAMP_HISPANIC,
  race_black_hispanic: RACE_RAMP_BLACK,
  race_asian:          RACE_RAMP_DEFAULT,
  race_ai_an:          RACE_RAMP_DEFAULT,
  race_nh_opi:         RACE_RAMP_DEFAULT,
  race_white:          RACE_RAMP_WHITE,
};

// Module state — reflected onto window so legend.js (no import path) can read.
let currentRaceField = null;        // e.g. 'race_black'
let currentBreakpoints = [25, 50, 75];

function getMap() { return getMapboxInstance(); }

function raceFieldFromMode(mode) {
  // 'race_black' -> 'black', 'race_black_hispanic' -> 'black_hispanic'
  return String(mode || '').replace(/^race_/, '');
}

export function buildRaceColorExpression(breakpoints, ramp) {
  // Step expression over feature-state.pct. Returns ramp[0] when pct is
  // null/undefined (tracts without a feature-state entry) — that's the
  // light end of the ramp, which reads as "no/low concentration" for the
  // sequential color schemes we use.
  if (!breakpoints || !breakpoints.length) return ramp[0] || '#cccccc';
  const expr = ['step', ['coalesce', ['feature-state', 'pct'], 0], ramp[0]];
  breakpoints.forEach((bp, i) => {
    expr.push(bp);
    expr.push(ramp[i + 1] || ramp[ramp.length - 1]);
  });
  return expr;
}

export function addRaceLayer(beforeLayerId) {
  const map = getMap();
  if (!map) return;
  if (!map.getSource('race-overlay')) {
    map.addSource('race-overlay', {
      type: 'vector',
      url: `mapbox://${CENSUS_TILESET_ID}`,
      promoteId: { [CENSUS_SOURCE_LAYER]: 'GEOID' },
    });
  }
  if (map.getLayer('dl-race-fill')) return;
  map.addLayer({
    id: 'dl-race-fill',
    type: 'fill',
    source: 'race-overlay',
    'source-layer': CENSUS_SOURCE_LAYER,
    paint: {
      'fill-color': buildRaceColorExpression(currentBreakpoints, RACE_RAMP_DEFAULT),
      'fill-opacity': 0.7,
      'fill-antialias': false,
      'fill-outline-color': 'rgba(0,0,0,0)',
    },
    layout: { visibility: 'none' },
  }, beforeLayerId);
}

export function setRaceLayerVisible(visible) {
  const map = getMap();
  if (!map || !map.getLayer('dl-race-fill')) return;
  map.setLayoutProperty('dl-race-fill', 'visibility', visible ? 'visible' : 'none');
}

function applyRaceFeatureState(tracts) {
  const map = getMap();
  if (!map) return;
  // Cache so we can re-apply after a style swap if it ever happens.
  const cache = {};
  tracts.forEach(({ geoid, pct }) => {
    if (!geoid) return;
    cache[geoid] = pct;
    map.setFeatureState(
      { source: 'race-overlay', sourceLayer: CENSUS_SOURCE_LAYER, id: geoid },
      { pct },
    );
  });
  window.dotlenderRaceFeatureStates = cache;
}

function updateRaceFillColor() {
  const map = getMap();
  if (!map || !map.getLayer('dl-race-fill')) return;
  const ramp = RACE_RAMPS[currentRaceField] || RACE_RAMP_DEFAULT;
  const expr = buildRaceColorExpression(currentBreakpoints, ramp);
  map.setPaintProperty('dl-race-fill', 'fill-color', expr);
  window.dotlenderCurrentBreakpoints = currentBreakpoints.slice();
  window.dotlenderCurrentRaceOverlay = currentRaceField;
}

function computeQuartileBreakpoints(tracts) {
  // Empirical quartiles from the returned data. Skips zero/null pct so a
  // metro with mostly white tracts still produces useful breaks for a
  // minority race. Dedupes when the data is sparse.
  const pcts = (tracts || [])
    .map((t) => t.pct)
    .filter((p) => Number.isFinite(p) && p > 0)
    .sort((a, b) => a - b);
  if (!pcts.length) return [25, 50, 75];
  const q = (frac) => {
    const i = Math.min(Math.floor(pcts.length * frac), pcts.length - 1);
    return Math.round(pcts[i]);
  };
  const raw = [q(0.25), q(0.5), q(0.75)];
  // Dedupe ascending — when one quartile equals the next we drop the dup
  // so the step expression always has strictly increasing thresholds.
  return raw.filter((v, i, arr) => i === 0 || v > arr[i - 1]);
}

export async function loadRaceOverlay(overlayMode, geographyBody) {
  if (!overlayMode || !overlayMode.startsWith('race_')) return;
  const map = getMap();
  if (!map) return;
  const raceField = raceFieldFromMode(overlayMode);
  let resp;
  try {
    resp = await fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...(geographyBody || {}), race_field: raceField }),
    });
  } catch (e) {
    console.warn('[dotlender] race overlay fetch failed:', e);
    return;
  }
  if (!resp.ok) {
    console.warn('[dotlender] race-choropleth API error:', resp.status);
    return;
  }
  const data = await resp.json();
  const tracts = data.tracts || [];

  currentRaceField = overlayMode;
  currentBreakpoints = computeQuartileBreakpoints(tracts);
  window.dotlenderCurrentBreakpoints = currentBreakpoints.slice();
  window.dotlenderCurrentRaceOverlay = currentRaceField;

  // Notify the sidebar so the breakpoint panel pre-fills with quartiles
  // and exposes itself.
  if (typeof window.dotlenderSetBreakpoints === 'function') {
    window.dotlenderSetBreakpoints(currentBreakpoints, overlayMode);
  }

  applyRaceFeatureState(tracts);
  updateRaceFillColor();
}

export function applyCustomBreakpoints(breakpoints) {
  const cleaned = [...new Set(
    (breakpoints || [])
      .map((v) => Math.round(Number(v)))
      .filter((v) => Number.isFinite(v) && v >= 0 && v <= 100),
  )].sort((a, b) => a - b);
  if (!cleaned.length) return;
  currentBreakpoints = cleaned;
  updateRaceFillColor();
  // Legend reads window.dotlenderCurrentBreakpoints; refresh canvas if it
  // has already been built (the PDF report doesn't auto-rebuild on overlay
  // changes anyway, so this is a no-op until the user hits Build Report).
}

window.dotlenderApplyCustomBreakpoints = applyCustomBreakpoints;
