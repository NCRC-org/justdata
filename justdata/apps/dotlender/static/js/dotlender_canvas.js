// dotlender_canvas.js
// Fabric.js canvas builder for DotLender PDF report.
// Uses html2canvas to capture the live Mapbox map into the report.

import { RACE_COLORS, INCOME_BAND_COLORS, getCurrentMapData, getMapElement } from './dotlender_map.js';
import { getFilterState, getLastSummaryStats } from './dotlender_filters.js';

let fabricCanvas = null;

// Letter landscape at 96 dpi screen resolution. jsPDF re-renders at print DPI.
const CANVAS_W = 1056; // 11" * 96
const CANVAS_H = 816;  //  8.5" * 96

const NCRC_LOGO = '/static/img/ncrc-logo-color.png';

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

export async function buildCanvas(mapData, state) {
  if (!fabricCanvas) initFabricCanvas();
  fabricCanvas.clear();
  fabricCanvas.setBackgroundColor('#ffffff', fabricCanvas.renderAll.bind(fabricCanvas));

  const container = document.getElementById('dotlender-canvas-container');
  container.style.display = 'block';
  container.scrollIntoView({ behavior: 'smooth' });

  await placeMapImage();
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

async function placeMapImage() {
  const mapEl = getMapElement();
  // eslint-disable-next-line no-undef
  if (typeof html2canvas === 'undefined' || !mapEl) {
    placeMapPlaceholder();
    return;
  }
  try {
    // eslint-disable-next-line no-undef
    const snapshot = await html2canvas(mapEl, { useCORS: true, allowTaint: false, logging: false });
    const dataUrl = snapshot.toDataURL('image/png');
    await new Promise((resolve) => {
      // eslint-disable-next-line no-undef
      fabric.Image.fromURL(dataUrl, (img) => {
        const targetW = CANVAS_W - 300;
        const targetH = CANVAS_H - 200;
        const scale = Math.min(targetW / img.width, targetH / img.height);
        img.set({ left: 20, top: 60, scaleX: scale, scaleY: scale });
        fabricCanvas.add(img);
        resolve();
      });
    });
  } catch (err) {
    console.warn('[dotlender] html2canvas map capture failed', err);
    placeMapPlaceholder();
  }
}

function placeMapPlaceholder() {
  // eslint-disable-next-line no-undef
  const rect = new fabric.Rect({
    left: 20, top: 60,
    width: CANVAS_W - 300, height: CANVAS_H - 200,
    fill: '#f0f0f0', stroke: '#cccccc', strokeWidth: 1,
  });
  // eslint-disable-next-line no-undef
  const label = new fabric.Text('Map capture unavailable', {
    left: 200, top: 300, fontSize: 14, fill: '#888',
  });
  fabricCanvas.add(rect, label);
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
    { left: 20, top: 10, width: 700, fontSize: 16, fontFamily: 'Arial', fontWeight: 'bold', fill: '#1a1a2e' },
  );
  fabricCanvas.add(title);
}

async function placeLogo() {
  await new Promise((resolve) => {
    // eslint-disable-next-line no-undef
    fabric.Image.fromURL(NCRC_LOGO, (img) => {
      if (!img || !img.width) { resolve(); return; }
      const scale = 50 / img.height;
      img.set({ left: CANVAS_W - 180, top: 10, scaleX: scale, scaleY: scale });
      fabricCanvas.add(img);
      resolve();
    }, { crossOrigin: 'anonymous' });
  });
}

function placeDotLegend() {
  let y = 80;
  const x = CANVAS_W - 200;
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text('Lending by Race/Ethnicity', {
    left: x, top: y, fontSize: 10, fontWeight: 'bold', fill: '#333',
  }));
  y += 18;
  Object.entries(RACE_COLORS).forEach(([label, color]) => {
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Circle({ left: x, top: y + 2, radius: 5, fill: color, stroke: color }));
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Text(label, { left: x + 14, top: y, fontSize: 9, fill: '#333' }));
    y += 16;
  });
}

function placeChoroplethLegend(overlayMode) {
  if (overlayMode === 'none') return;
  let y = CANVAS_H - 180;
  const x = 20;
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text('Tract Classification', {
    left: x, top: y, fontSize: 10, fontWeight: 'bold', fill: '#333',
  }));
  y += 16;
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
    fabricCanvas.add(new fabric.Rect({ left: x, top: y, width: 12, height: 12, fill: color, stroke: '#999', strokeWidth: 0.5 }));
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Text(label, { left: x + 16, top: y + 1, fontSize: 9, fill: '#333' }));
    y += 16;
  });
}

function placeStatsTable() {
  const summary = getLastSummaryStats();
  if (!summary) return;
  const x = CANVAS_W - 200;
  let y = CANVAS_H - 180;
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text('Summary', { left: x, top: y, fontSize: 10, fontWeight: 'bold', fill: '#333' }));
  y += 16;
  const rows = [
    ['Total loans', summary.total_loans?.toLocaleString()],
    ['Tracts with lending', summary.tracts_with_lending?.toLocaleString()],
    ['Lenders', summary.lender_count?.toLocaleString()],
    ['% in LMI tracts', summary.pct_lmi_tracts != null ? `${summary.pct_lmi_tracts.toFixed(1)}%` : null],
    ['% majority-minority', summary.pct_majority_minority_tracts != null ? `${summary.pct_majority_minority_tracts.toFixed(1)}%` : null],
  ];
  rows.forEach(([label, val]) => {
    // eslint-disable-next-line no-undef
    fabricCanvas.add(new fabric.Text(`${label}: ${val ?? '—'}`, { left: x, top: y, fontSize: 9, fill: '#333' }));
    y += 14;
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
    left: 20, top: CANVAS_H - 60, width: CANVAS_W - 220, fontSize: 8, fill: '#555', fontStyle: 'italic',
  }));
}

function placeMethodologyNote() {
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Textbox(
    'This map displays lending activity reported under HMDA and does not constitute a finding of discriminatory lending. ' +
    'Race/ethnicity classification follows NCRC methodology. Dot density is currently scaled by loan count only (housing-unit denominator pending).',
    { left: 20, top: CANVAS_H - 45, width: CANVAS_W - 40, fontSize: 7, fill: '#777' },
  ));
}

function placeDateStamp() {
  const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  // eslint-disable-next-line no-undef
  fabricCanvas.add(new fabric.Text(`Generated ${today}`, {
    left: CANVAS_W - 200, top: CANVAS_H - 20, fontSize: 8, fill: '#999',
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
