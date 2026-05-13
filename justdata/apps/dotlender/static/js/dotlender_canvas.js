// dotlender_canvas.js
// Fabric.js canvas builder for the DotLender PDF report.
// Canvas is rendered at 2x scale for legible export DPI; CSS in
// dotlender_head.html constrains the on-screen display back to 1056x816.
//
// The canvas no longer carries title/subtitle/summary/filter/date text —
// the exported PDF is the map + legend + scale + north arrow + logo only.
// The Mapbox map is composited at PDF export time (dotlender_export.js).

import { INCOME_BAND_COLORS, getCurrentMapData, getActiveRaceFilters } from './dotlender_map.js';
import { getFilterState } from './dotlender_filters.js';

let fabricCanvas = null;

export const CANVAS_SCALE = 2;
export const CANVAS_W = 1056 * CANVAS_SCALE; // 2112
export const CANVAS_H = 816 * CANVAS_SCALE;  // 1632

const NCRC_LOGO = '/static/img/ncrc-logo-color.png';
const NORTH_ARROW_SVG = '/dotlender/static/img/north-arrow.svg';

// Identifying stroke colors on the map placeholder so export.js can hide
// just those elements (the placeholder isn't part of the legend group).
const MAP_PLACEHOLDER_STROKE = '#4a90d9';

function initFabricCanvas() {
  const el = document.getElementById('dotlender-canvas');
  el.width = CANVAS_W;
  el.height = CANVAS_H;
  // eslint-disable-next-line no-undef
  fabricCanvas = new fabric.Canvas('dotlender-canvas', {
    width: CANVAS_W,
    height: CANVAS_H,
    backgroundColor: '#ffffff',
    selection: true,
  });

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

  placeMapPlaceholder();
  await placeLogo();
  placeMapLegend(state, getActiveRaceFilters());
  await placeScaleAndNorthGroup();

  fabricCanvas.renderAll();
}

function placeMapPlaceholder() {
  // Visual reminder of the area the captured map will occupy in the PDF.
  // dotlender_export.js paints the map image over the full page at export
  // time, so the placeholder is just an editing affordance.
  const left = 40;
  const top = 120;
  const width = CANVAS_W - 680;
  const height = CANVAS_H - 440;
  // eslint-disable-next-line no-undef
  const rect = new fabric.Rect({
    left, top, width, height,
    fill: '#e8f0fe',
    stroke: MAP_PLACEHOLDER_STROKE,
    strokeWidth: 4,
    selectable: true,
  });
  // eslint-disable-next-line no-undef
  const label = new fabric.Textbox(
    'Map area — pan/zoom the live map to frame your view, then click Export PDF.',
    {
      left: left + 60, top: top + height / 2 - 30, width: width - 120,
      fontSize: 22, fill: MAP_PLACEHOLDER_STROKE, fontStyle: 'italic', textAlign: 'center',
    },
  );
  fabricCanvas.add(rect, label);
  window.dotlenderMapPlaceholder = { left, top, width, height, strokeColor: MAP_PLACEHOLDER_STROKE };
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

function placeMapLegend(state, activeRaces) {
  // Build all legend objects with absolute coords, then collapse into a
  // single fabric.Group so the user can drag the whole legend as a unit.
  const objects = [];
  const x = 40;
  let y = CANVAS_H - 540;
  const lineH = 32;
  const dotR = 9;

  // eslint-disable-next-line no-undef
  objects.push(new fabric.Text('Home Mortgage Originations', {
    left: x, top: y, fontSize: 26, fontWeight: 'bold', fill: '#222',
  }));
  y += 34;

  const yearLabel = state.year_start === state.year_end
    ? `(${state.year_start})`
    : `(${state.year_start} – ${state.year_end})`;
  // eslint-disable-next-line no-undef
  objects.push(new fabric.Text(yearLabel, { left: x, top: y, fontSize: 22, fill: '#444' }));
  y += 32;

  const density = parseInt(document.getElementById('dl-density-value')?.value, 10) || 1;
  // eslint-disable-next-line no-undef
  objects.push(new fabric.Text(`1 Dot = ${density} Loan${density > 1 ? 's' : ''}`, {
    left: x, top: y, fontSize: 22, fontWeight: 'bold', fill: '#222',
  }));
  y += 38;

  const lenderLabel = state.lei ? state.lender_name : 'All Lenders';
  if (activeRaces === 'all') {
    // eslint-disable-next-line no-undef
    objects.push(new fabric.Circle({ left: x, top: y, radius: dotR, fill: '#222' }));
    // eslint-disable-next-line no-undef
    objects.push(new fabric.Text(`${lenderLabel} Originations`, {
      left: x + 24, top: y - 4, fontSize: 20, fill: '#222',
    }));
    y += lineH;
  } else {
    const seen = new Set();
    activeRaces.forEach((race) => {
      const isOther = ['American Indian or Alaska Native', 'Two or More Races', 'Unknown or Not Provided', 'other'].includes(race);
      const label = isOther ? 'Other / Unknown' : race;
      if (seen.has(label)) return;
      seen.add(label);
      const color = LEGEND_RACE_COLORS[race] || '#999';
      // eslint-disable-next-line no-undef
      objects.push(new fabric.Circle({ left: x, top: y, radius: dotR, fill: color }));
      // eslint-disable-next-line no-undef
      objects.push(new fabric.Text(label, { left: x + 24, top: y - 4, fontSize: 20, fill: '#222' }));
      y += lineH;
    });
  }

  y += 10;
  const overlayMode = state.overlay_mode;
  if (overlayMode && overlayMode !== 'none') {
    const choroTitle = overlayMode === 'income' ? 'Tract Income Band' : 'Minority Population';
    // eslint-disable-next-line no-undef
    objects.push(new fabric.Text(choroTitle, {
      left: x, top: y, fontSize: 22, fontWeight: 'bold', fill: '#222',
    }));
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
        left: x, top: y, width: 20, height: 20,
        fill: color, stroke: '#999', strokeWidth: 1,
      }));
      // eslint-disable-next-line no-undef
      objects.push(new fabric.Text(label, { left: x + 28, top: y - 2, fontSize: 20, fill: '#222' }));
      y += lineH;
    });
  }

  if (document.getElementById('dl-show-city-boundary')?.checked) {
    const cityName = window.currentCityName || 'City';
    // eslint-disable-next-line no-undef
    objects.push(new fabric.Line([x, y + 10, x + 24, y + 10], {
      stroke: '#c0392b', strokeWidth: 2,
    }));
    // eslint-disable-next-line no-undef
    objects.push(new fabric.Text(`${cityName} Boundary`, {
      left: x + 32, top: y, fontSize: 20, fill: '#222',
    }));
  }

  // eslint-disable-next-line no-undef
  const group = new fabric.Group(objects, { selectable: true, hasControls: true });
  fabricCanvas.add(group);
}

// --- North arrow + scale bar group ---------------------------------------

function getScaleBarInfo(mapInstance) {
  const zoom = mapInstance.getZoom();
  const lat = mapInstance.getCenter().lat;
  const metersPerPixel = (156543.03392 * Math.cos((lat * Math.PI) / 180)) / Math.pow(2, zoom);
  return { metersPerPixel };
}

function buildScaleBarObjects() {
  const mapInstance = window.dotlenderMap;
  if (!mapInstance) return [];
  const { metersPerPixel } = getScaleBarInfo(mapInstance);
  const canvasPixelsPerMeter = 1 / metersPerPixel;
  const mileInMeters = 1609.34;
  // Choose the largest whole or half mile that fits inside ~120 canvas px.
  let miles = 1;
  while (miles * mileInMeters * canvasPixelsPerMeter > 120) miles = Math.max(0.5, miles / 2);
  while (miles * mileInMeters * canvasPixelsPerMeter < 40) miles *= 2;
  const barPixels = Math.round(miles * mileInMeters * canvasPixelsPerMeter);
  const x = 40;
  const y = CANVAS_H - 160;
  const tickH = 12;
  const fontSize = 20;
  const objs = [];
  // Two segments: white (0..miles), black (miles..2*miles)
  // eslint-disable-next-line no-undef
  objs.push(new fabric.Rect({
    left: x, top: y - tickH / 2, width: barPixels, height: tickH,
    fill: 'white', stroke: '#222', strokeWidth: 1.5,
  }));
  // eslint-disable-next-line no-undef
  objs.push(new fabric.Rect({
    left: x + barPixels, top: y - tickH / 2, width: barPixels, height: tickH,
    fill: '#222', stroke: '#222', strokeWidth: 1.5,
  }));
  // Labels: 0, miles, 2*miles
  const labelY = y + tickH / 2 + 6;
  [[0, x], [miles, x + barPixels], [miles * 2, x + barPixels * 2]].forEach(([val, lx]) => {
    const label = val === 0 ? '0' : `${val} mi`;
    // eslint-disable-next-line no-undef
    objs.push(new fabric.Text(label, {
      left: lx - (val === 0 ? 6 : 22), top: labelY, fontSize, fill: '#222',
    }));
  });
  // "Miles" unit label above bar
  // eslint-disable-next-line no-undef
  objs.push(new fabric.Text('Miles', {
    left: x, top: y - tickH / 2 - fontSize - 6,
    fontSize, fontWeight: 'bold', fill: '#222',
  }));
  return objs;
}

async function buildNorthArrowObjects() {
  // Load the SVG asynchronously and return its assembled group as an array
  // of one object (so it can be flattened into the scale+arrow group).
  return new Promise((resolve) => {
    // eslint-disable-next-line no-undef
    fabric.loadSVGFromURL(NORTH_ARROW_SVG, (objects, options) => {
      if (!objects || !objects.length) { resolve([]); return; }
      // eslint-disable-next-line no-undef
      const svg = fabric.util.groupSVGElements(objects, options);
      svg.scaleToWidth(120);
      // Position the arrow above the scale bar.
      svg.set({ left: 50, top: CANVAS_H - 360 });
      resolve([svg]);
    }, null, { crossOrigin: 'anonymous' });
  });
}

async function placeScaleAndNorthGroup() {
  const scaleObjs = buildScaleBarObjects();
  const arrowObjs = await buildNorthArrowObjects();
  const all = [...arrowObjs, ...scaleObjs];
  if (!all.length) return;
  // eslint-disable-next-line no-undef
  const group = new fabric.Group(all, { selectable: true, hasControls: true });
  fabricCanvas.add(group);
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
