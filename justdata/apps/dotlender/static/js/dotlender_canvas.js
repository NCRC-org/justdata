// dotlender_canvas.js
// Fabric.js canvas builder for the DotLender PDF report.
// Canvas is rendered at 2x internal resolution (CSS clamps the on-screen
// display back to 1056×816). Layout: county polygon outline + legend +
// north arrow + scale bar + NCRC logo. The live Mapbox map is captured
// inside the same map.once('idle') callback that draws the county outline
// so projection and capture share a single viewport snapshot.

import { INCOME_BAND_COLORS, getCurrentMapData, getActiveRaceFilters } from './dotlender_map.js';
import { getFilterState } from './dotlender_filters.js';
import { getCachedCountyGeojson, getCachedMapContainerSize } from './dotlender_overlays.js';

let fabricCanvas = null;

export const CANVAS_SCALE = 2;
export const CANVAS_W = 1056 * CANVAS_SCALE; // 2112
export const CANVAS_H = 816 * CANVAS_SCALE;  // 1632

const NCRC_LOGO = '/static/img/ncrc-logo-color.png';
const NORTH_ARROW_SVG = '/dotlender/static/img/north-arrow.svg';
const LEGEND_FONT = 'Arial';
const PLACEHOLDER_STROKE = '#4a90d9';

function initFabricCanvas() {
  const el = document.getElementById('dotlender-canvas');
  el.width = CANVAS_W;
  el.height = CANVAS_H;
  // eslint-disable-next-line no-undef
  fabricCanvas = new fabric.Canvas('dotlender-canvas', {
    width: CANVAS_W, height: CANVAS_H, backgroundColor: '#ffffff', selection: true,
  });
  window.dotlenderFabricCanvas = fabricCanvas;
  document.addEventListener('keydown', (e) => {
    if ((e.key === 'Delete' || e.key === 'Backspace') && fabricCanvas.getActiveObject()) {
      const t = document.activeElement?.tagName;
      if (t !== 'INPUT' && t !== 'SELECT' && t !== 'TEXTAREA') {
        fabricCanvas.remove(fabricCanvas.getActiveObject());
        fabricCanvas.renderAll();
        e.preventDefault();
      }
    }
  });
}

export function getFabricCanvas() { return fabricCanvas; }

export async function buildCanvas(mapData, state) {
  if (!fabricCanvas) initFabricCanvas();
  fabricCanvas.clear();
  fabricCanvas.setBackgroundColor('#ffffff', fabricCanvas.renderAll.bind(fabricCanvas));

  const modal = document.getElementById('dl-pdf-modal');
  if (modal) { modal.classList.add('active'); document.body.style.overflow = 'hidden'; }

  // Map image capture must happen on the current viewport (projection +
  // capture share the same map.once('idle') snapshot). Capture first so
  // it's done before any selectable overlays are added.
  const mapInstance = window.dotlenderMap;
  if (mapInstance) {
    await new Promise((resolve) => {
      mapInstance.once('idle', () => {
        try {
          window.dotlenderMapCaptureDataUrl = mapInstance.getCanvas().toDataURL('image/png', 1.0);
        } catch (err) {
          console.warn('[dotlender] map capture failed', err);
          window.dotlenderMapCaptureDataUrl = null;
        }
        resolve();
      });
      mapInstance.triggerRepaint();
    });
  }

  await placeLogo();
  placeMapLegend(state, getActiveRaceFilters());
  placeScaleBar(mapInstance);
  await placeNorthArrow();

  // County outline LAST so it renders on top of the other canvas elements.
  // The outline path uses the same map.project() that the capture above
  // used, so it stays aligned with the captured viewport.
  placeCountyOutline();

  fabricCanvas.renderAll();
}

// --- County outline -------------------------------------------------------

function projectCoords(coords, mapInstance, containerW, containerH) {
  // map.project([lng, lat]) → {x, y} in live-map CSS pixels. Use a UNIFORM
  // scale (contain-fit) so the projected polygon keeps its aspect ratio
  // instead of stretching when the canvas aspect differs from the live
  // map container aspect. Center the projection on the canvas.
  const scale = Math.min(CANVAS_W / containerW, CANVAS_H / containerH);
  const offsetX = (CANVAS_W - containerW * scale) / 2;
  const offsetY = (CANVAS_H - containerH * scale) / 2;
  return coords.map(([lng, lat]) => {
    const pt = mapInstance.project([lng, lat]);
    return { x: pt.x * scale + offsetX, y: pt.y * scale + offsetY };
  });
}

function geojsonToPath(geometry, mapInstance, w, h) {
  const rings = geometry.type === 'MultiPolygon'
    ? geometry.coordinates.flat(1)
    : (geometry.coordinates || []);
  let pathStr = '';
  rings.forEach((ring) => {
    const pts = projectCoords(ring, mapInstance, w, h);
    if (!pts.length) return;
    pathStr += `M ${pts[0].x} ${pts[0].y} `;
    for (let i = 1; i < pts.length; i += 1) pathStr += `L ${pts[i].x} ${pts[i].y} `;
    pathStr += 'Z ';
  });
  return pathStr.trim();
}

function placeFallbackPlaceholder() {
  const left = 40; const top = 120;
  const width = CANVAS_W - 680; const height = CANVAS_H - 440;
  // eslint-disable-next-line no-undef
  const rect = new fabric.Rect({
    left, top, width, height, fill: 'transparent',
    stroke: PLACEHOLDER_STROKE, strokeWidth: 3, strokeDashArray: [12, 6],
    selectable: true,
    excludeFromExport: true,
  });
  fabricCanvas.add(rect);
  window.dotlenderMapPlaceholder = { left, top, width, height };
}

function placeCountyOutline() {
  const mapInstance = window.dotlenderMap;
  const geojson = getCachedCountyGeojson();
  const containerSize = getCachedMapContainerSize();
  if (!mapInstance || !geojson?.features?.length || !containerSize) {
    placeFallbackPlaceholder();
    return;
  }
  const pathStr = geojsonToPath(
    geojson.features[0].geometry, mapInstance,
    containerSize.width, containerSize.height,
  );
  if (!pathStr) { placeFallbackPlaceholder(); return; }
  // eslint-disable-next-line no-undef
  const countyPath = new fabric.Path(pathStr, {
    fill: 'transparent',
    stroke: PLACEHOLDER_STROKE,
    strokeWidth: 3,
    strokeDashArray: [12, 6],
    selectable: true,
    evented: true,
    // Editor-only affordance: hide from PDF export so the dashed outline
    // doesn't bleed into the final report on top of the captured map.
    excludeFromExport: true,
  });
  fabricCanvas.add(countyPath);
  const bbox = countyPath.getBoundingRect();
  window.dotlenderMapPlaceholder = {
    left: bbox.left, top: bbox.top, width: bbox.width, height: bbox.height,
  };
}

async function placeLogo() {
  await new Promise((resolve) => {
    // eslint-disable-next-line no-undef
    fabric.Image.fromURL(NCRC_LOGO, (img) => {
      if (!img || !img.width) { resolve(); return; }
      const scale = 100 / img.height;
      img.set({ left: CANVAS_W - 360, top: 20, scaleX: scale, scaleY: scale });
      fabricCanvas.add(img);
      resolve();
    }, { crossOrigin: 'anonymous' });
  });
}

// --- Legend group ---------------------------------------------------------

const LEGEND_RACE_COLORS = {
  'Hispanic or Latino': '#e41a1c',
  'Black or African American': '#377eb8',
  'Asian': '#4daf4a',
  'White': '#a65628',
  'American Indian or Alaska Native': '#999',
  'Two or More Races': '#999',
  'Unknown or Not Provided': '#999',
  'other': '#999',
};
const OTHER_BUCKETS = ['American Indian or Alaska Native', 'Two or More Races', 'Unknown or Not Provided', 'other'];

function addText(objects, text, opts) {
  // eslint-disable-next-line no-undef
  objects.push(new fabric.Text(text, { fontFamily: LEGEND_FONT, fill: '#222', ...opts }));
}

function placeMapLegend(state, activeRaces) {
  const objects = [];
  const x = 40;
  let y = CANVAS_H - 540;
  const lineH = 32;
  const dotR = 9;

  addText(objects, 'Home Mortgage Originations', { left: x, top: y, fontSize: 28, fontWeight: 'bold' });
  y += 36;
  const yearLabel = state.year_start === state.year_end
    ? `(${state.year_start})`
    : `(${state.year_start} – ${state.year_end})`;
  addText(objects, yearLabel, { left: x, top: y, fontSize: 22, fontWeight: 'normal', fill: '#444' });
  y += 30;

  const density = parseInt(document.getElementById('dl-density-value')?.value, 10) || 1;
  addText(objects, `1 Dot = ${density} Loan${density > 1 ? 's' : ''}`, {
    left: x, top: y, fontSize: 24, fontWeight: 'bold',
  });
  y += 38;

  const lenderLabel = state.lei ? state.lender_name : 'All Lenders';
  if (activeRaces === 'all') {
    // eslint-disable-next-line no-undef
    objects.push(new fabric.Circle({ left: x, top: y, radius: dotR, fill: '#222' }));
    addText(objects, `${lenderLabel} Originations`, {
      left: x + 24, top: y - 4, fontSize: 22, fontWeight: 'normal',
    });
    y += lineH;
  } else {
    const seen = new Set();
    activeRaces.forEach((race) => {
      const label = OTHER_BUCKETS.includes(race) ? 'Other / Unknown' : race;
      if (seen.has(label)) return;
      seen.add(label);
      const color = LEGEND_RACE_COLORS[race] || '#999';
      // eslint-disable-next-line no-undef
      objects.push(new fabric.Circle({ left: x, top: y, radius: dotR, fill: color }));
      addText(objects, label, { left: x + 24, top: y - 4, fontSize: 22, fontWeight: 'normal' });
      y += lineH;
    });
  }

  y += 10;
  const overlayMode = state.overlay_mode;
  if (overlayMode && overlayMode !== 'none') {
    const choroTitle = overlayMode === 'income' ? 'Tract Income Band' : 'Minority Population';
    addText(objects, choroTitle, { left: x, top: y, fontSize: 24, fontWeight: 'bold' });
    y += 30;
    const items = overlayMode === 'income'
      ? [['Low (<50% AMI)', INCOME_BAND_COLORS.low],
         ['Moderate (50–80%)', INCOME_BAND_COLORS.moderate],
         ['Middle (80–120%)', INCOME_BAND_COLORS.middle],
         ['Upper (>120%)', INCOME_BAND_COLORS.upper]]
      : [['<25% minority', '#deebf7'], ['25–50%', '#9ecae1'],
         ['50–75%', '#3182bd'], ['>75%', '#08519c']];
    items.forEach(([label, color]) => {
      // eslint-disable-next-line no-undef
      objects.push(new fabric.Rect({
        left: x, top: y, width: 20, height: 20, fill: color, stroke: '#999', strokeWidth: 1,
      }));
      addText(objects, label, { left: x + 28, top: y - 2, fontSize: 20, fontWeight: 'normal' });
      y += lineH;
    });
  }

  if (document.getElementById('dl-show-city-boundary')?.checked) {
    const cityName = window.dotlenderActiveCityName || null;
    const labelText = cityName ? `${cityName} Boundary` : 'City Boundary';
    // eslint-disable-next-line no-undef
    objects.push(new fabric.Line([x, y + 10, x + 24, y + 10], {
      stroke: '#c0392b', strokeWidth: 2,
    }));
    addText(objects, labelText, { left: x + 32, top: y, fontSize: 20, fontWeight: 'normal' });
  }

  // eslint-disable-next-line no-undef
  const group = new fabric.Group(objects, { selectable: true, hasControls: true });
  fabricCanvas.add(group);
}

// --- Scale bar (independent draggable group) -----------------------------

function placeScaleBar(mapInstance) {
  if (!mapInstance) return;
  const zoom = mapInstance.getZoom();
  const lat = mapInstance.getCenter().lat;
  const metersPerMapPx = (156543.03392 * Math.cos((lat * Math.PI) / 180)) / Math.pow(2, zoom);
  const containerW = getCachedMapContainerSize()?.width || 900;
  const canvasPxPerMeter = (1 / metersPerMapPx) * (CANVAS_W / containerW);
  const mileInMeters = 1609.34;
  // Pick a base mile value where one segment is 40-120 canvas pixels.
  let baseMiles = 1;
  while (baseMiles * mileInMeters * canvasPxPerMeter > 120) baseMiles /= 2;
  while (baseMiles * mileInMeters * canvasPxPerMeter < 40) baseMiles *= 2;
  if (baseMiles >= 2) baseMiles = Math.round(baseMiles);

  const unitPx = Math.round(baseMiles * mileInMeters * canvasPxPerMeter);
  const totalPx = unitPx * 4;
  const tickH = 16;
  const objs = [];

  // eslint-disable-next-line no-undef
  objs.push(new fabric.Line([0, 0, totalPx, 0], { stroke: '#222', strokeWidth: 3 }));
  [0, 1, 2, 4].forEach((mult) => {
    const x = mult * unitPx;
    // eslint-disable-next-line no-undef
    objs.push(new fabric.Line([x, -tickH / 2, x, tickH / 2], {
      stroke: '#222', strokeWidth: 2,
    }));
    const milesVal = mult * baseMiles;
    const label = milesVal === 0 ? '0' : `${Number.isInteger(milesVal) ? milesVal : milesVal.toFixed(1)} mi`;
    const offset = milesVal === 0 ? 4 : (label.length * 5);
    // eslint-disable-next-line no-undef
    objs.push(new fabric.Text(label, {
      left: x - offset, top: tickH / 2 + 4,
      fontSize: 18, fontFamily: LEGEND_FONT, fill: '#222',
    }));
  });
  // eslint-disable-next-line no-undef
  objs.push(new fabric.Text('Miles', {
    left: 0, top: -tickH / 2 - 26,
    fontSize: 20, fontFamily: LEGEND_FONT, fontWeight: 'bold', fill: '#222',
  }));

  // eslint-disable-next-line no-undef
  const group = new fabric.Group(objs, {
    left: CANVAS_W - 420, top: CANVAS_H - 120,
    selectable: true, hasControls: true,
  });
  fabricCanvas.add(group);
}

// --- North arrow (independent draggable group) ---------------------------

function buildSimpleNorthArrow() {
  // Fabric primitive fallback used when the SVG can't be parsed.
  const objs = [
    // eslint-disable-next-line no-undef
    new fabric.Line([0, 60, 0, 5], {
      stroke: '#222', strokeWidth: 4, originX: 'center',
    }),
    // eslint-disable-next-line no-undef
    new fabric.Triangle({
      width: 20, height: 20, fill: '#222',
      originX: 'center', originY: 'bottom', top: 5, left: 0,
    }),
    // eslint-disable-next-line no-undef
    new fabric.Text('N', {
      fontSize: 26, fontFamily: LEGEND_FONT, fontWeight: 'bold', fill: '#222',
      originX: 'center', top: 64, left: 0,
    }),
  ];
  // eslint-disable-next-line no-undef
  const group = new fabric.Group(objs, {
    left: CANVAS_W - 260, top: CANVAS_H - 260,
    selectable: true, hasControls: true,
  });
  fabricCanvas.add(group);
  return group;
}

async function placeNorthArrow() {
  return new Promise((resolve) => {
    fetch(NORTH_ARROW_SVG)
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(r.status))))
      .then((svgString) => {
        // eslint-disable-next-line no-undef
        fabric.loadSVGFromString(svgString, (objects, options) => {
          if (!objects || !objects.length) {
            buildSimpleNorthArrow();
            resolve();
            return;
          }
          // eslint-disable-next-line no-undef
          const svg = fabric.util.groupSVGElements(objects, options);
          svg.scaleToWidth(80);
          svg.set({
            left: CANVAS_W - 260, top: CANVAS_H - 260,
            selectable: true, hasControls: true,
          });
          fabricCanvas.add(svg);
          resolve();
        });
      })
      .catch(() => {
        buildSimpleNorthArrow();
        resolve();
      });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('dl-build-report-btn')?.addEventListener('click', () => {
    const mapData = getCurrentMapData();
    const state = getFilterState();
    if (mapData && state) buildCanvas(mapData, state);
  });
  document.getElementById('dl-modal-close-btn')?.addEventListener('click', () => {
    const modal = document.getElementById('dl-pdf-modal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';
  });
  document.getElementById('dl-pdf-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'dl-pdf-modal') {
      e.target.classList.remove('active');
      document.body.style.overflow = '';
    }
  });
});
