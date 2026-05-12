// dotlender_canvas.js
// Fabric.js canvas builder for DotLender PDF report.
// Canvas is rendered at 2x scale for legible export DPI; CSS sizes it back to
// screen pixels via the rule in dotlender_head.html. The live Mapbox map is
// NOT baked into the canvas at build time — a placeholder rect marks where
// the map will go, and dotlender_export.js composes the final PDF by laying
// the captured Mapbox image over the placeholder at export time.

import { RACE_COLORS, INCOME_BAND_COLORS, getCurrentMapData } from './dotlender_map.js';
import { getFilterState, getLastSummaryStats } from './dotlender_filters.js';

let fabricCanvas = null;

// 2x scale for canvas/print resolution. CSS in dotlender_head.html constrains
// the on-screen display back to 1056x816 so the canvas remains usable.
export const CANVAS_SCALE = 2;
export const CANVAS_W = 1056 * CANVAS_SCALE; // 2112
export const CANVAS_H = 816 * CANVAS_SCALE;  // 1632

// Scaling helper: write all literal pixel measurements in 1x ("design") units
// and apply s() to keep proportions correct after the 2x scale-up.
const s = (n) => n * CANVAS_SCALE;

const NCRC_LOGO = '/static/img/ncrc-logo-color.png';

// Stroke color used to identify the map placeholder so dotlender_export.js
// can hide it before composing the final PDF.
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

  const container = document.getElementById('dotlender-canvas-container');
  container.style.display = 'block';
  container.scrollIntoView({ behavior: 'smooth' });

  placeMapPlaceholder();
  placeTitle(state);
  await placeLogo();
  placeDotLegend();
  placeChoroplethLegend(state.overlay_mode);
  placeStatsTable();
  placeFilterSummary(state);
  placeMethodologyNote();
  placeDateStamp();

  fabricCanvas.renderAll();
}

function placeMapPlaceholder() {
  // Reserve space for the map; the actual Mapbox image is composited in at
  // PDF export time using window.dotlenderMapPlaceholder for positioning.
  const left = s(20);
  const top = s(60);
  const width = CANVAS_W - s(340);
  const height = CANVAS_H - s(220);

  // eslint-disable-next-line no-undef
  const rect = new fabric.Rect({
    left, top, width, height,
    fill: '#e8f0fe',
    stroke: MAP_PLACEHOLDER_STROKE,
    strokeWidth: s(2),
    selectable: true,
  });
  // eslint-disable-next-line no-undef
  const label = new fabric.Textbox(
    'Map will be captured from the live map above on Export PDF.\n' +
    'Pan and zoom the map to frame your view first.',
    {
      left: left + s(30),
      top: top + height / 2 - s(30),
      width: width - s(60),
      fontSize: s(20),
      fill: MAP_PLACEHOLDER_STROKE,
      fontStyle: 'italic',
      textAlign: 'center',
    },
  );
  fabricCanvas.add(rect, label);

  // Coords are in canvas-internal pixels (already at CANVAS_W resolution).
  // export.js scales these to PDF mm using the same CANVAS_W/H constants.
  window.dotlenderMapPlaceholder = {
    left, top, width, height,
    strokeColor: MAP_PLACEHOLDER_STROKE,
  };
}

function placeTitle(state) {
  const geoLabel = `${state.geography_type.charAt(0).toUpperCase() + state.geography_type.slice(1)} ${state.geography_value}`;
  const lenderLabel = state.lei ? state.lender_name : 'All Lenders';
  const yearLabel = state.year_start === state.year_end
    ? `${state.year_start}`
    : `${state.year_start}–${state.year_end}`;
  // eslint-disable-next-line no-undef
  const title = new fabric.Textbox(
    `HMDA Lending — ${geoLabel}\n${lenderLabel} | ${yearLabel}`,
    {
      left: s(20),
      top: s(10),
      width: s(700),
      fontSize: s(16),
      fontFamily: 'Arial',
      fontWeight: 'bold',
      fill: '#1a1a2e',
      lineHeight: 1.2,
    },
  );
  fabricCanvas.add(title);
}

async function placeLogo() {
  await new Promise((resolve) => {
    // eslint-disable-next-line no-undef
    fabric.Image.fromURL(NCRC_LOGO, (img) => {
      if (!img || !img.width) { resolve(); return; }
      const targetHeight = s(50);
      const scale = targetHeight / img.height;
      img.set({
        left: CANVAS_W - s(180),
        top: s(10),
        scaleX: scale,
        scaleY: scale,
      });
      fabricCanvas.add(img);
      resolve();
    }, { crossOrigin: 'anonymous' });
  });
}

function placeDotLegend() {
  let y = s(80);
  const x = CANVAS_W - s(200);
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text('Lending by Race/Ethnicity', {
    left: x, top: y, fontSize: s(10), fontWeight: 'bold', fill: '#333',
  }));
  y += s(18);
  Object.entries(RACE_COLORS).forEach(([label, color]) => {
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Circle({
      left: x, top: y + s(2), radius: s(5), fill: color, stroke: color,
    }));
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Text(label, {
      left: x + s(14), top: y, fontSize: s(9), fill: '#333',
    }));
    y += s(16);
  });
}

function placeChoroplethLegend(overlayMode) {
  if (overlayMode === 'none') return;
  let y = CANVAS_H - s(180);
  const x = s(20);
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text('Tract Classification', {
    left: x, top: y, fontSize: s(10), fontWeight: 'bold', fill: '#333',
  }));
  y += s(16);
  let items;
  if (overlayMode === 'minority') {
    items = [
      ['Q4 — Highest 25% minority', '#08519c'],
      ['Q3 — 50–75%', '#3182bd'],
      ['Q2 — 25–50%', '#9ecae1'],
      ['Q1 — Lowest 25%', '#deebf7'],
    ];
  } else {
    items = [
      ['Low income (<50% AMI)', INCOME_BAND_COLORS.low],
      ['Moderate (50–80%)', INCOME_BAND_COLORS.moderate],
      ['Middle (80–120%)', INCOME_BAND_COLORS.middle],
      ['Upper (>120%)', INCOME_BAND_COLORS.upper],
    ];
  }
  items.forEach(([label, color]) => {
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Rect({
      left: x, top: y, width: s(12), height: s(12),
      fill: color, stroke: '#999', strokeWidth: s(0.5),
    }));
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Text(label, {
      left: x + s(16), top: y + s(1), fontSize: s(9), fill: '#333',
    }));
    y += s(16);
  });
}

function placeStatsTable() {
  const summary = getLastSummaryStats();
  if (!summary) return;
  const x = CANVAS_W - s(200);
  let y = CANVAS_H - s(180);
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text('Summary', {
    left: x, top: y, fontSize: s(10), fontWeight: 'bold', fill: '#333',
  }));
  y += s(16);
  const rows = [
    ['Total loans', summary.total_loans?.toLocaleString()],
    ['Tracts with lending', summary.tracts_with_lending?.toLocaleString()],
    ['Lenders', summary.lender_count?.toLocaleString()],
    ['% in LMI tracts', summary.pct_lmi_tracts != null ? `${summary.pct_lmi_tracts.toFixed(1)}%` : null],
    ['% majority-minority', summary.pct_majority_minority_tracts != null ? `${summary.pct_majority_minority_tracts.toFixed(1)}%` : null],
  ];
  rows.forEach(([label, val]) => {
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Text(`${label}: ${val ?? '—'}`, {
      left: x, top: y, fontSize: s(9), fill: '#333',
    }));
    y += s(14);
  });
}

function placeFilterSummary(state) {
  const f = state.filters;
  const isDefault = (
    f.loan_purpose === '1' && f.action_taken === '1' && f.lien_status === '1' &&
    f.occupancy_type === '1' && f.construction_method === '1' &&
    f.total_units === '1234' && f.reverse_mortgage === 'exclude'
  );
  const filterText = isDefault
    ? 'Filters: Home purchase, originated, first lien, principal residence, site-built, 1–4 units, no reverse mortgage'
    : `Filters: purpose=${f.loan_purpose}, action=${f.action_taken}, lien=${f.lien_status}, occupancy=${f.occupancy_type}, construction=${f.construction_method}, units=${f.total_units}, reverse_mortgage=${f.reverse_mortgage}`;
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Textbox(filterText, {
    left: s(20),
    top: CANVAS_H - s(60),
    width: CANVAS_W - s(220),
    fontSize: s(8),
    fill: '#555',
    fontStyle: 'italic',
  }));
}

function placeMethodologyNote() {
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Textbox(
    'This map displays lending activity reported under HMDA and does not constitute a finding of discriminatory lending. ' +
    'Race/ethnicity classification follows NCRC methodology. Dot density is currently scaled by loan count only (housing-unit denominator pending).',
    {
      left: s(20),
      top: CANVAS_H - s(45),
      width: CANVAS_W - s(40),
      fontSize: s(7),
      fill: '#777',
    },
  ));
}

function placeDateStamp() {
  const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text(`Generated ${today}`, {
    left: CANVAS_W - s(200), top: CANVAS_H - s(20), fontSize: s(8), fill: '#999',
  }));
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('dl-build-report-btn')?.addEventListener('click', () => {
    const mapData = getCurrentMapData();
    const state = getFilterState();
    if (mapData && state) buildCanvas(mapData, state);
  });
  document.getElementById('dl-canvas-close-btn')?.addEventListener('click', () => {
    document.getElementById('dotlender-canvas-container').style.display = 'none';
  });
});
