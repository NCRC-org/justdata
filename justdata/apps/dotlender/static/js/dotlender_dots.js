// dotlender_dots.js
// Dot density math for DotLender.
// Owns: race color palette, tract polygon cache built from the rendered
// jedlebi.census-tracts tileset, random-point-in-polygon sampling, stable
// per-dot position cache, and the buildDotFeatures function that emits
// the final GeoJSON FeatureCollection consumed by the dl-dots-circles layer.
//
// dotlender_map.js owns the Mapbox map instance and the layer wiring; it
// imports from this module and calls collectTractPolygons / stableJitter
// at the right points in the render lifecycle.

// --- Race color palette --------------------------------------------------

export const RACE_COLORS = {
  'Hispanic or Latino': '#e41a1c',
  'Black or African American': '#377eb8',
  'Asian': '#4daf4a',
  'American Indian or Alaska Native': '#984ea3',
  'Two or More Races': '#ff7f00',
  'White': '#a65628',
  'Unknown or Not Provided': '#999999',
};

export const RACE_ALL_COLOR = '#222222';

// "Other / Unknown" checkbox expands to these race buckets.
export const OTHER_RACE_BUCKETS = [
  'Unknown or Not Provided',
  'American Indian or Alaska Native',
  'Two or More Races',
];

// --- Tract polygon cache --------------------------------------------------

// GEOID -> merged Feature (Polygon or MultiPolygon) built from queryRenderedFeatures.
let cachedTractPolygons = {};

export function getCachedTractPolygons() { return cachedTractPolygons; }
export function clearTractPolygonCache() { cachedTractPolygons = {}; }

// Collect rendered tract polygons from the choropleth fill layers and
// merge tile-clipped fragments by GEOID. Falls back to the largest
// fragment when turf.union throws on degenerate geometry.
export function collectTractPolygons(map) {
  if (!map) return cachedTractPolygons;
  let features = [];
  try {
    features = map.queryRenderedFeatures(undefined, {
      layers: ['dl-income-fill', 'dl-minority-fill'],
    });
  } catch (e) {
    console.warn('[dotlender] queryRenderedFeatures failed', e);
    return cachedTractPolygons;
  }
  const byGeoid = {};
  features.forEach((f) => {
    const geoid = f.properties?.GEOID || f.properties?.geoid || '';
    if (!geoid) return;
    if (!byGeoid[geoid]) byGeoid[geoid] = [];
    byGeoid[geoid].push(f);
  });
  const merged = {};
  Object.entries(byGeoid).forEach(([geoid, feats]) => {
    if (feats.length === 1) { merged[geoid] = feats[0]; return; }
    try {
      // eslint-disable-next-line no-undef
      if (typeof turf === 'undefined') {
        merged[geoid] = feats[0];
        return;
      }
      let union = feats[0];
      for (let i = 1; i < feats.length; i += 1) {
        // eslint-disable-next-line no-undef
        union = turf.union(union, feats[i]) || union;
      }
      merged[geoid] = union;
    } catch (err) {
      // Pick the fragment with the most coordinates as a best-effort fallback.
      merged[geoid] = feats.reduce((a, b) => {
        const aLen = (a.geometry?.coordinates || []).flat(Infinity).length;
        const bLen = (b.geometry?.coordinates || []).flat(Infinity).length;
        return aLen >= bLen ? a : b;
      });
    }
  });
  cachedTractPolygons = merged;
  return merged;
}

// Rejection-sample a random point inside a tract polygon. 10 attempts then
// fall back to the polygon centroid — keeps the synchronous path fast
// while still placing the dot somewhere inside (centroid is always inside
// for convex shapes; for concave tracts it may sit on a polygon edge but
// is still close enough to read as "inside").
const REJECTION_ATTEMPTS = 10;
const CENTROID_JITTER_DEG = 0.001; // ~110m fallback nudge

function randomPointInPolygon(tractFeature) {
  // eslint-disable-next-line no-undef
  if (typeof turf === 'undefined' || !tractFeature) return null;
  let bbox;
  try {
    // eslint-disable-next-line no-undef
    bbox = turf.bbox(tractFeature);
  } catch (e) { return null; }
  const [minLng, minLat, maxLng, maxLat] = bbox;
  for (let attempt = 0; attempt < REJECTION_ATTEMPTS; attempt += 1) {
    const lng = minLng + Math.random() * (maxLng - minLng);
    const lat = minLat + Math.random() * (maxLat - minLat);
    try {
      // eslint-disable-next-line no-undef
      const inside = turf.booleanPointInPolygon(turf.point([lng, lat]), tractFeature);
      if (inside) return [lng, lat];
    } catch (e) { /* malformed polygon — fall through */ }
  }
  // Fallback: nudge the centroid slightly so multiple dots in the same
  // tract don't stack perfectly on top of each other.
  try {
    // eslint-disable-next-line no-undef
    const c = turf.centroid(tractFeature).geometry.coordinates;
    return [
      c[0] + (Math.random() - 0.5) * CENTROID_JITTER_DEG,
      c[1] + (Math.random() - 0.5) * CENTROID_JITTER_DEG,
    ];
  } catch (e) {
    return null;
  }
}

// Pre-compute stable random positions for every dot in every (tract,race)
// row. Positions inside the rendered tract polygon when available;
// otherwise we fall back to a small centroid jitter using the per-row
// centroid the API returned. Called once per render — density slider and
// race filter changes re-read these positions without re-sampling.
export function stableJitter(dotData, tractPolygons) {
  return (dotData || []).map((row) => {
    const tractFeature = tractPolygons?.[row.census_tract] || null;
    const count = row.dot_count || 0;
    const positions = new Array(count);
    for (let i = 0; i < count; i += 1) {
      let pos = null;
      if (tractFeature) pos = randomPointInPolygon(tractFeature);
      if (!pos) {
        const fallbackJitter = 0.008;
        pos = (row.centroid_lng != null && row.centroid_lat != null)
          ? [
              row.centroid_lng + (Math.random() - 0.5) * fallbackJitter,
              row.centroid_lat + (Math.random() - 0.5) * fallbackJitter,
            ]
          : null;
      }
      positions[i] = pos;
    }
    return { ...row, _positions: positions };
  });
}

// Non-blocking wrapper so a 15K-dot render doesn't freeze the UI thread.
export function stableJitterAsync(dotData, tractPolygons) {
  return new Promise((resolve) => {
    setTimeout(() => resolve(stableJitter(dotData, tractPolygons)), 0);
  });
}

// --- Build Features -------------------------------------------------------

// Render the cached _positions into a GeoJSON FeatureCollection. Color is
// baked into the feature property so the dl-dots-circles layer can use
// circle-color: ['get', 'color'] without setPaintProperty churn on filter
// changes. Race filter is applied here so unchecked races don't emit
// features at all (saves bytes + render time).
export function buildDotFeatures(dotData, densityRatio = 1, activeRaces = 'all') {
  const stride = Math.max(1, parseInt(densityRatio, 10) || 1);
  const features = [];
  let rawTotal = 0;
  (dotData || []).forEach((row) => {
    if (activeRaces !== 'all' && !activeRaces.includes(row.derived_race)) return;
    const color = activeRaces === 'all'
      ? RACE_ALL_COLOR
      : (RACE_COLORS[row.derived_race] || '#999999');
    const positions = row._positions || [];
    const n = positions.length;
    rawTotal += n;
    const count = Math.floor(n / stride);
    for (let k = 0; k < count; k += 1) {
      const p = positions[k * stride];
      if (!p) continue;
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: p },
        properties: { color, derived_race: row.derived_race, census_tract: row.census_tract },
      });
    }
  });
  // eslint-disable-next-line no-console
  console.log(`[dotlender] density stride=${stride}  raw dots=${rawTotal}  rendered=${features.length}`);
  return { type: 'FeatureCollection', features };
}
