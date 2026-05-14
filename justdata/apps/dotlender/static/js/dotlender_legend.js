// dotlender_legend.js
// PDF-canvas legend group: title, year, density, race rows, choropleth
// swatches, and the optional city-boundary entry. Built as a single
// draggable fabric.Group so the user can reposition the whole legend on
// the canvas before exporting the PDF.

import { CANVAS_H } from './dotlender_canvas.js';
import { INCOME_BAND_COLORS } from './dotlender_map.js';

const LEGEND_FONT = 'Arial';

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

export function placeMapLegend(fabricCanvas, state, activeRaces) {
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

  // City legend: 1 selected -> named "[City] City Boundary"; 2+ -> generic
  // "City Boundary" (per-city names appear as moveable labels on the map
  // canvas in placeCityLabels). 0 selected -> no legend entry at all.
  const selectedCities = window.dotlenderSelectedCities
    || window.dotlenderActiveCities || [];
  if (selectedCities.length > 0) {
    const cityLabel = selectedCities.length === 1
      ? `${selectedCities[0].name} City Boundary`
      : 'City Boundary';
    // eslint-disable-next-line no-undef
    objects.push(new fabric.Line([x, y + 8, x + 28, y + 8], {
      stroke: '#c0392b', strokeWidth: 3, selectable: false,
    }));
    addText(objects, cityLabel, {
      left: x + 36, top: y - 2, fontSize: 22, fontWeight: 'normal',
    });
    y += 32;
  }

  // eslint-disable-next-line no-undef
  const group = new fabric.Group(objects, { selectable: true, hasControls: true });
  fabricCanvas.add(group);
}
