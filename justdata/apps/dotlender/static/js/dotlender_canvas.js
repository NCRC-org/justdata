// dotlender_canvas.js
// Fabric.js canvas builder for DotLender PDF report.
// Canvas is rendered at 2x scale for legible export DPI; CSS sizes it back to
// screen pixels via the rule in dotlender_head.html. The live Mapbox map is
// NOT baked into the canvas at build time — a placeholder rect marks where
// the map will go, and dotlender_export.js composes the final PDF by laying
// the captured Mapbox image over the placeholder at export time.

import { RACE_COLORS, INCOME_BAND_COLORS, getCurrentMapData, getActiveRaceFilters } from './dotlender_map.js';
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

  const modal = document.getElementById('dl-pdf-modal');
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  placeMapPlaceholder();
  placeTitle(state);
  await placeLogo();
  placeMapLegend(state, getActiveRaceFilters());
  placeNorthArrow();
  placeScaleBar();
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
  // Title and subtitle as separate textboxes so each gets its own size.
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Textbox(`HMDA Lending — ${geoLabel}`, {
    left: s(20), top: s(10), width: s(800),
    fontSize: s(18), fontFamily: 'Arial', fontWeight: 'bold', fill: '#1a1a2e',
  }));
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Textbox(`${lenderLabel} | ${yearLabel}`, {
    left: s(20), top: s(40), width: s(800),
    fontSize: s(14), fontFamily: 'Arial', fill: '#444',
  }));
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

// Unified legend block (bottom-left) — replaces the prior dot + choropleth
// legends. Layout follows the PNC-style reference: title, year range, dot
// ratio, dot key, choropleth key, optional city-boundary key.
function placeMapLegend(state, activeRaces) {
  const x = 20;
  let y = CANVAS_H - 420;
  const lineH = 28;
  const dotR = 7;

  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text('Home Mortgage Originations', {
    left: x, top: y, fontSize: 22, fontWeight: 'bold', fill: '#222',
  }));
  y += 30;

  const yearLabel = state.year_start === state.year_end
    ? `(${state.year_start})`
    : `(${state.year_start} – ${state.year_end})`;
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text(yearLabel, {
    left: x, top: y, fontSize: 20, fill: '#444',
  }));
  y += 28;

  const density = parseInt(document.getElementById('dl-density-value')?.value, 10) || 1;
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text(`1 Dot = ${density} Loan${density > 1 ? 's' : ''}`, {
    left: x, top: y, fontSize: 20, fontWeight: 'bold', fill: '#222',
  }));
  y += 32;

  const lenderLabel = state.lei ? state.lender_name : 'All Lenders';
  if (activeRaces === 'all') {
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Circle({ left: x, top: y, radius: dotR, fill: '#222' }));
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Text(`${lenderLabel} Originations`, {
      left: x + 20, top: y - 2, fontSize: 18, fill: '#222',
    }));
    y += lineH;
  } else {
    const LEGEND_COLORS = {
      'Hispanic or Latino': '#e41a1c',
      'Black or African American': '#377eb8',
      'Asian': '#4daf4a',
      'White': '#a65628',
      'American Indian or Alaska Native': '#999',
      'Two or More Races': '#999',
      'Unknown or Not Provided': '#999',
      'other': '#999',
    };
    const seen = new Set();
    activeRaces.forEach((race) => {
      const label = (['American Indian or Alaska Native', 'Two or More Races', 'Unknown or Not Provided', 'other'].includes(race))
        ? 'Other / Unknown' : race;
      if (seen.has(label)) return;
      seen.add(label);
      const color = LEGEND_COLORS[race] || '#999';
      // eslint-disable-next-line no-undef
      fabricCanvas.add(new fabric.Circle({ left: x, top: y, radius: dotR, fill: color }));
      // eslint-disable-next-line no-undef
      fabricCanvas.add(new fabric.Text(label, { left: x + 20, top: y - 2, fontSize: 18, fill: '#222' }));
      y += lineH;
    });
  }

  y += 8;
  const overlayMode = state.overlay_mode;
  if (overlayMode && overlayMode !== 'none') {
    const choroTitle = overlayMode === 'income' ? 'Tract Income Band' : 'Minority Population';
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Text(choroTitle, {
      left: x, top: y, fontSize: 20, fontWeight: 'bold', fill: '#222',
    }));
    y += 26;
    const items = overlayMode === 'income'
      ? [['Low (<50% AMI)', INCOME_BAND_COLORS.low],
         ['Moderate (50–80%)', INCOME_BAND_COLORS.moderate],
         ['Middle (80–120%)', INCOME_BAND_COLORS.middle],
         ['Upper (>120%)', INCOME_BAND_COLORS.upper]]
      : [['<25% minority', '#deebf7'], ['25–50%', '#9ecae1'],
         ['50–75%', '#3182bd'], ['>75%', '#08519c']];
    items.forEach(([label, color]) => {
      // eslint-disable-next-line no-undef
      fabricCanvas.add(new fabric.Rect({
        left: x, top: y, width: 16, height: 16,
        fill: color, stroke: '#999', strokeWidth: 1,
      }));
      // eslint-disable-next-line no-undef
      fabricCanvas.add(new fabric.Text(label, { left: x + 24, top: y, fontSize: 18, fill: '#222' }));
      y += lineH;
    });
  }

  if (document.getElementById('dl-show-city-boundary')?.checked) {
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Line([x, y + 8, x + 20, y + 8], {
      stroke: '#c0392b', strokeWidth: 2,
    }));
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Text('City Boundary', {
      left: x + 28, top: y, fontSize: 18, fill: '#222',
    }));
  }
}

function placeNorthArrow() {
  // Above the legend; arrow points up, "N" label below.
  const arrowX = 40;
  const arrowY = CANVAS_H - 280;
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Line([arrowX, arrowY + 40, arrowX, arrowY], {
    stroke: '#222', strokeWidth: 3,
  }));
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Triangle({
    left: arrowX - 8, top: arrowY - 2, width: 16, height: 16, fill: '#222', angle: 0,
  }));
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text('N', {
    left: arrowX - 6, top: arrowY + 44, fontSize: 24, fontWeight: 'bold', fill: '#222',
  }));
}

function getScaleBarInfo(mapInstance) {
  // Web-Mercator meters per pixel at the current zoom and center latitude.
  const zoom = mapInstance.getZoom();
  const lat = mapInstance.getCenter().lat;
  const metersPerPixel = (156543.03392 * Math.cos((lat * Math.PI) / 180)) / Math.pow(2, zoom);
  const barPixels = 100;
  const barMeters = metersPerPixel * barPixels;
  const units = barMeters >= 1609 ? 'mi' : 'ft';
  const barDist = units === 'mi'
    ? Math.round((barMeters / 1609) * 10) / 10
    : Math.round((barMeters * 3.28084) / 100) * 100;
  return { barPixels, barDist, units };
}

function placeScaleBar() {
  const mapInstance = window.dotlenderMap;
  if (!mapInstance) return;
  const scaleX = 20;
  const scaleY = CANVAS_H - 220;
  const { barPixels, barDist, units } = getScaleBarInfo(mapInstance);
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Line([scaleX, scaleY, scaleX + barPixels, scaleY], {
    stroke: '#222', strokeWidth: 3,
  }));
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Line([scaleX, scaleY - 6, scaleX, scaleY + 6], {
    stroke: '#222', strokeWidth: 2,
  }));
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Line(
    [scaleX + barPixels, scaleY - 6, scaleX + barPixels, scaleY + 6],
    { stroke: '#222', strokeWidth: 2 },
  ));
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text(`${barDist} ${units}`, {
    left: scaleX + barPixels / 2 - 20, top: scaleY + 8, fontSize: 20, fill: '#222',
  }));
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
    fontSize: s(9),
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
      fontSize: s(8),
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
  document.getElementById('dl-modal-close-btn')?.addEventListener('click', () => {
    const modal = document.getElementById('dl-pdf-modal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';
  });
  // Click on backdrop also dismisses
  document.getElementById('dl-pdf-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'dl-pdf-modal') {
      e.target.classList.remove('active');
      document.body.style.overflow = '';
    }
  });
});
