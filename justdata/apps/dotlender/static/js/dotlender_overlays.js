// dotlender_overlays.js
// Map overlays for DotLender: county clip mask, county outline, city
// boundary tileset, dynamic legend box, and title overlay. Operates on
// window.dotlenderMap (set by dotlender_map.js) so no parameter plumbing
// is required.

const RACE_COLORS = {
  'Hispanic or Latino': '#e41a1c',
  'Black or African American': '#377eb8',
  'Asian': '#4daf4a',
  'American Indian or Alaska Native': '#984ea3',
  'Two or More Races': '#ff7f00',
  'White': '#a65628',
  'Unknown or Not Provided': '#999999',
};

const INCOME_BAND_COLORS = {
  low: '#d73027',
  moderate: '#fc8d59',
  middle: '#fee090',
  upper: '#e0f3f8',
  unknown: '#cccccc',
};

const CITY_BOUNDS_TILESET = 'jedlebi.dedh6og7';
const CITY_BOUNDS_SOURCE_LAYER = 'CITY_BOUNDS-7kbk2e';

// Cached county polygon for the currently rendered geography so we can rebuild
// the mask on toggle without a second ArcGIS round-trip.
let cachedCountyGeojson = null;
let cachedCountyFips = null;
// Map container size in CSS pixels at the moment the mask was built.
// Canvas.js uses this to scale map.project() screen coordinates from the
// live map container into the 2x canvas-internal space.
let cachedMapContainerSize = null;

export function getCachedCountyGeojson() { return cachedCountyGeojson; }
export function getCachedMapContainerSize() { return cachedMapContainerSize; }

function getMap() { return window.dotlenderMap || null; }

// --- Base-style label + road cleanup -------------------------------------

// Symbol layers kept: route shields (interstate / motorway exit numbers).
const KEEP_SYMBOL_LAYERS = new Set(['road-number-shield', 'road-exit-shield']);
// Road LINE/FILL layers kept: the motorway-trunk tier (interstates + US
// highways in this style). Plus the two shield symbol layers above
// participate via KEEP_SYMBOL_LAYERS. Everything else under `road-` is hidden.
const KEEP_ROAD_LAYERS = new Set([
  'road-motorway-trunk',
  'road-motorway-trunk-case',
  'road-number-shield',
  'road-exit-shield',
]);

export function hideNonShieldLabels() {
  const map = getMap();
  if (!map) return;
  try {
    (map.getStyle().layers || []).forEach((layer) => {
      const isRoad = layer.id.startsWith('road-');
      const isSymbol = layer.type === 'symbol';
      if (isRoad && !KEEP_ROAD_LAYERS.has(layer.id)) {
        try { map.setLayoutProperty(layer.id, 'visibility', 'none'); } catch (e) { /* ignore */ }
      } else if (isSymbol && !KEEP_SYMBOL_LAYERS.has(layer.id)) {
        try { map.setLayoutProperty(layer.id, 'visibility', 'none'); } catch (e) { /* ignore */ }
      }
    });
  } catch (e) { /* getStyle can throw mid-load */ }
}

// --- County clip mask -----------------------------------------------------

function buildMaskGeojson(countyGeojson) {
  if (!countyGeojson?.features?.length) return null;
  const worldRing = [[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]];
  const geom = countyGeojson.features[0].geometry;
  let holes = [];
  if (geom.type === 'MultiPolygon') {
    geom.coordinates.forEach((poly) => { if (poly[0]) holes.push(poly[0]); });
  } else if (geom.type === 'Polygon') {
    if (geom.coordinates[0]) holes = [geom.coordinates[0]];
  }
  return {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [worldRing, ...holes] },
    }],
  };
}

function fitToCountyBounds(countyGeojson) {
  const map = getMap();
  if (!map || !countyGeojson?.features?.length) return;
  const geom = countyGeojson.features[0].geometry;
  let coords = [];
  if (geom.type === 'MultiPolygon') coords = geom.coordinates.flat(2);
  else if (geom.type === 'Polygon') coords = geom.coordinates[0] || [];
  if (!coords.length) return;
  const lngs = coords.map((c) => c[0]);
  const lats = coords.map((c) => c[1]);
  map.fitBounds(
    [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
    { padding: 40, duration: 600 },
  );
}

async function fetchCountyGeojson(fips) {
  const url = `https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/USA_Census_Counties/FeatureServer/0/query?where=FIPS%3D%27${fips}%27&outFields=*&outSR=4326&f=geojson`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`county boundary fetch failed: ${resp.status}`);
  return resp.json();
}

export async function addCountyMask(fipsList) {
  const map = getMap();
  if (!map) return;
  // Accept either a single FIPS string or an array.
  const list = Array.isArray(fipsList) ? fipsList : (fipsList ? [fipsList] : []);
  if (!list.length) return;
  removeCountyMask();
  try {
    const cacheKey = list.join(',');
    if (cachedCountyFips !== cacheKey || !cachedCountyGeojson) {
      const geojsons = await Promise.all(list.map((f) => fetchCountyGeojson(f)));
      const valid = geojsons.filter((g) => g?.features?.length);
      if (!valid.length) return;
      if (valid.length === 1) {
        cachedCountyGeojson = valid[0];
      } else {
        // Union all county polygons into one combined boundary so the mask
        // and outline cover the full multi-county selection as a single
        // shape (no internal county dividers).
        let combined = valid[0].features[0];
        for (let i = 1; i < valid.length; i += 1) {
          try {
            // eslint-disable-next-line no-undef
            const u = turf.union(combined, valid[i].features[0]);
            if (u) combined = u;
          } catch (e) {
            console.warn('[dotlender] county union failed for index', i, e);
          }
        }
        cachedCountyGeojson = { type: 'FeatureCollection', features: [combined] };
      }
      cachedCountyFips = cacheKey;
    }
    const maskGeojson = buildMaskGeojson(cachedCountyGeojson);
    if (!maskGeojson) return;
    map.addSource('dl-county-mask', { type: 'geojson', data: maskGeojson });
    map.addLayer({
      id: 'dl-county-mask-fill',
      type: 'fill',
      source: 'dl-county-mask',
      paint: { 'fill-color': '#ffffff', 'fill-opacity': 1 },
    });
    map.addSource('dl-county-outline', { type: 'geojson', data: cachedCountyGeojson });
    map.addLayer({
      id: 'dl-county-outline-line',
      type: 'line',
      source: 'dl-county-outline',
      paint: { 'line-color': '#1e3a5f', 'line-width': 2, 'line-opacity': 0.8 },
    });
    fitToCountyBounds(cachedCountyGeojson);
    // Capture the live map container's CSS dimensions so the canvas
    // builder can scale map.project() screen coords to canvas space.
    const mapEl = document.getElementById('dotlender-map');
    if (mapEl) {
      cachedMapContainerSize = { width: mapEl.offsetWidth, height: mapEl.offsetHeight };
    }
  } catch (err) {
    console.warn('[dotlender] county mask failed:', err);
  }
}

export function removeCountyMask() {
  const map = getMap();
  if (!map) return;
  ['dl-county-mask-fill', 'dl-county-outline-line'].forEach((id) => {
    if (map.getLayer(id)) map.removeLayer(id);
  });
  ['dl-county-mask', 'dl-county-outline'].forEach((id) => {
    if (map.getSource(id)) map.removeSource(id);
  });
}

export function clearCachedCounty() { cachedCountyGeojson = null; cachedCountyFips = null; }

// --- City boundaries ------------------------------------------------------

export function addCityBoundaries() {
  const map = getMap();
  if (!map) return;
  if (!map.getSource('dl-city-bounds')) {
    map.addSource('dl-city-bounds', { type: 'vector', url: `mapbox://${CITY_BOUNDS_TILESET}` });
  }
  if (!map.getLayer('dl-city-bounds-line')) {
    map.addLayer({
      id: 'dl-city-bounds-line',
      type: 'line',
      source: 'dl-city-bounds',
      'source-layer': CITY_BOUNDS_SOURCE_LAYER,
      paint: { 'line-color': '#c0392b', 'line-width': 1.5, 'line-opacity': 0.85 },
    });
  }
  // Clear any old NAME/STATEFP filter — we now keep all visible city
  // boundaries on the map and let the rendered NAMEs drive the sidebar
  // and canvas legend instead.
  map.setFilter('dl-city-bounds-line', null);

  // After the layer renders, collect the visible cities, dedupe by
  // STATEFP+NAME, and filter to the states that contain the user's
  // selected counties.
  map.once('idle', () => {
    if (!map.getLayer('dl-city-bounds-line')) return;
    const features = map.queryRenderedFeatures(undefined, {
      layers: ['dl-city-bounds-line'],
    });
    const selectedStateFips = new Set(
      (window.currentGeoidList || []).map((g) => String(g).substring(0, 2)),
    );
    const cityMap = {};
    features.forEach((f) => {
      const stateFp = f.properties?.STATEFP;
      const name = f.properties?.NAME;
      if (!name || !stateFp) return;
      if (selectedStateFips.size > 0 && !selectedStateFips.has(stateFp)) return;
      const key = `${stateFp}:${name}`;
      if (!cityMap[key]) cityMap[key] = { name, stateFp };
    });
    const cities = Object.values(cityMap).sort((a, b) => a.name.localeCompare(b.name));
    window.dotlenderActiveCities = cities;

    const span = document.getElementById('dl-city-boundary-label');
    if (!span) return;
    if (cities.length === 0) {
      span.textContent = 'City Boundaries (none in area)';
    } else if (cities.length === 1) {
      span.textContent = `${cities[0].name} Boundary`;
    } else if (cities.length <= 3) {
      span.textContent = `${cities.map((c) => c.name).join(', ')} Boundaries`;
    } else {
      span.textContent = `${cities.length} City Boundaries`;
    }
  });
}

export function removeCityBoundaries() {
  const map = getMap();
  if (!map) return;
  if (map.getLayer('dl-city-bounds-line')) map.removeLayer('dl-city-bounds-line');
  if (map.getSource('dl-city-bounds')) map.removeSource('dl-city-bounds');
  window.dotlenderActiveCities = [];
}

// --- Title + legend overlays ----------------------------------------------

export function updateTitleOverlay(state) {
  const el = document.getElementById('dl-overlay-title');
  if (!el || !state) return;
  const counties = state.selected_counties || [];
  let geoLabel;
  if (counties.length === 1) geoLabel = counties[0].label;
  else if (counties.length > 1) geoLabel = `${counties.length} counties`;
  else if (state.state_fips) geoLabel = `State FIPS ${state.state_fips}`;
  else geoLabel = '—';
  const lenderLabel = state.lei ? state.lender_name : 'All Lenders';
  const yearLabel = state.year_start === state.year_end
    ? `${state.year_start}`
    : `${state.year_start}–${state.year_end}`;
  el.textContent = `${geoLabel} · ${lenderLabel} · ${yearLabel}`;
  el.style.display = 'block';
}

function legendDotRow(label, color) {
  return `<div style="display:flex;align-items:center;gap:5px;margin-bottom:3px;">
    <span style="width:8px;height:8px;border-radius:50%;background:${color};display:inline-block;"></span>
    <span>${label}</span></div>`;
}

function legendSwatchRow(label, color) {
  return `<div style="display:flex;align-items:center;gap:5px;margin-bottom:3px;">
    <span style="width:10px;height:10px;background:${color};border:1px solid #999;display:inline-block;"></span>
    <span>${label}</span></div>`;
}

export function updateLegend(overlayMode, activeRaces) {
  const el = document.getElementById('dl-overlay-legend');
  if (!el) return;

  let html = '<div style="font-weight:600; margin-bottom:4px; font-size:0.82rem;">Loan Originations</div>';
  if (activeRaces === 'all') {
    html += legendDotRow('All races (combined)', '#222');
  } else {
    const labelFor = {
      'Hispanic or Latino': ['Hispanic or Latino', RACE_COLORS['Hispanic or Latino']],
      'Black or African American': ['Black or African American', RACE_COLORS['Black or African American']],
      'Asian': ['Asian', RACE_COLORS.Asian],
      'White': ['White', RACE_COLORS.White],
      'American Indian or Alaska Native': ['Other / Unknown', RACE_COLORS['Unknown or Not Provided']],
      'Two or More Races': ['Other / Unknown', RACE_COLORS['Unknown or Not Provided']],
      'Unknown or Not Provided': ['Other / Unknown', RACE_COLORS['Unknown or Not Provided']],
    };
    const seen = new Set();
    activeRaces.forEach((race) => {
      const entry = labelFor[race];
      if (!entry) return;
      const [label, color] = entry;
      if (seen.has(label)) return;
      seen.add(label);
      html += legendDotRow(label, color);
    });
  }

  if (overlayMode && overlayMode !== 'none') {
    if (overlayMode === 'income') {
      html += '<div style="font-weight:600; margin:8px 0 4px; font-size:0.82rem;">Tract Income Band</div>';
      [
        ['Low (<50% AMI)', INCOME_BAND_COLORS.low],
        ['Moderate (50–80%)', INCOME_BAND_COLORS.moderate],
        ['Middle (80–120%)', INCOME_BAND_COLORS.middle],
        ['Upper (>120%)', INCOME_BAND_COLORS.upper],
      ].forEach(([label, color]) => { html += legendSwatchRow(label, color); });
    }
    if (overlayMode === 'minority') {
      html += '<div style="font-weight:600; margin:8px 0 4px; font-size:0.82rem;">Minority Population</div>';
      [
        ['<25%', '#deebf7'], ['25–50%', '#9ecae1'],
        ['50–75%', '#3182bd'], ['>75%', '#08519c'],
      ].forEach(([label, color]) => { html += legendSwatchRow(label, color); });
    }
  }

  el.innerHTML = html;
  el.style.display = 'block';
}
