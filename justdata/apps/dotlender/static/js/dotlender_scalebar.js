// dotlender_scalebar.js
// Two canvas widgets extracted from dotlender_canvas.js:
//   placePageCutoffMarker — dashed red rectangle showing the chosen
//     printable page area (Letter or Tabloid landscape). Non-interactive,
//     excluded from export.
//   placeScaleBar — distance scale anchored to the live Mapbox bounds and
//     the current map placeholder width. Recomputes a "nice" mile unit so
//     the bar spans ~30% of the map width with 4-6 labeled ticks.

import { CANVAS_W, CANVAS_H, getFabricCanvas } from './dotlender_canvas.js';

const LEGEND_FONT = 'Arial';

// --- Page cutoff marker --------------------------------------------------

export function placePageCutoffMarker() {
  const fabricCanvas = getFabricCanvas();
  if (!fabricCanvas) return;
  const pageSize = document.getElementById('dl-page-size')?.value || 'letter';
  const pageW = pageSize === 'tabloid' ? 431.8 : 279.4;
  const pageH = pageSize === 'tabloid' ? 279.4 : 215.9;
  const scale = CANVAS_W / pageW;
  const markerW = pageW * scale;
  const markerH = pageH * scale;
  const left = 0;
  const top = (CANVAS_H - markerH) / 2;
  // eslint-disable-next-line no-undef
  const marker = new fabric.Rect({
    left, top, width: markerW, height: markerH,
    fill: 'transparent',
    stroke: '#c0392b',
    strokeWidth: 4,
    strokeDashArray: [16, 8],
    selectable: false,
    evented: false,
    excludeFromExport: true,
  });
  fabricCanvas.add(marker);
  fabricCanvas.sendToBack(marker);
  window.dotlenderPageMarker = marker;
}

export function refreshPageCutoffMarker() {
  const fabricCanvas = getFabricCanvas();
  if (!fabricCanvas) return;
  if (window.dotlenderPageMarker) {
    fabricCanvas.remove(window.dotlenderPageMarker);
    window.dotlenderPageMarker = null;
  }
  placePageCutoffMarker();
  fabricCanvas.renderAll();
}

window.dotlenderRefreshPageMarker = refreshPageCutoffMarker;

// --- Distance scale bar --------------------------------------------------

export function placeScaleBar(mapInstance) {
  const fabricCanvas = getFabricCanvas();
  if (!fabricCanvas || !mapInstance) return;
  const bounds = mapInstance.getBounds();
  const centerLat = mapInstance.getCenter().lat;
  const lngDiff = bounds.getEast() - bounds.getWest();
  const metersPerDegLng = 111320 * Math.cos((centerLat * Math.PI) / 180);
  const mapWidthMeters = lngDiff * metersPerDegLng;
  const placeholder = window.dotlenderMapPlaceholder;
  const mapCanvasWidth = placeholder?.width || (CANVAS_W * 0.6);
  const metersPerCanvasPx = mapWidthMeters / mapCanvasWidth;
  const mileInMeters = 1609.34;

  // Target ~30% of map width; pick a "nice" mile unit landing on 4-6 ticks.
  const targetTotalPx = mapCanvasWidth * 0.30;
  const targetTotalMiles = (targetTotalPx * metersPerCanvasPx) / mileInMeters;
  const niceSteps = [0.1, 0.25, 0.5, 1, 2, 2.5, 5, 10, 25, 50, 100];
  let baseMiles = 1;
  let numTicks = 4;
  for (let i = 0; i < niceSteps.length; i += 1) {
    const step = niceSteps[i];
    if (step * 4 <= targetTotalMiles && step * 6 >= targetTotalMiles) {
      baseMiles = step;
      numTicks = Math.min(6, Math.max(4, Math.floor(targetTotalMiles / step)));
      break;
    }
    if (step * 4 > targetTotalMiles) { baseMiles = step; numTicks = 4; break; }
  }

  const unitPx = Math.round((baseMiles * mileInMeters) / metersPerCanvasPx);
  const totalPx = unitPx * numTicks;
  const lineThickness = 4;
  const tickH = 22;
  const labelFontSize = 26;
  const headerFontSize = 28;
  const objs = [];

  // eslint-disable-next-line no-undef
  objs.push(new fabric.Line([0, 0, totalPx, 0], {
    stroke: '#222', strokeWidth: lineThickness,
  }));
  for (let i = 0; i <= numTicks; i += 1) {
    const x = i * unitPx;
    // eslint-disable-next-line no-undef
    objs.push(new fabric.Line([x, -tickH / 2, x, tickH / 2], {
      stroke: '#222', strokeWidth: 3,
    }));
    const val = i * baseMiles;
    const label = val === 0
      ? '0'
      : `${Number.isInteger(val) ? val : val.toFixed(2)}`;
    const offset = val === 0 ? 5 : label.length * 7;
    // eslint-disable-next-line no-undef
    objs.push(new fabric.Text(label, {
      left: x - offset, top: tickH / 2 + 6,
      fontSize: labelFontSize, fontFamily: LEGEND_FONT, fill: '#222',
    }));
  }
  // eslint-disable-next-line no-undef
  objs.push(new fabric.Text('Miles', {
    left: 0, top: -tickH / 2 - headerFontSize - 8,
    fontSize: headerFontSize, fontFamily: LEGEND_FONT, fontWeight: 'bold', fill: '#222',
  }));

  // eslint-disable-next-line no-undef
  const group = new fabric.Group(objs, {
    left: CANVAS_W - totalPx - 80, top: CANVAS_H - 140,
    selectable: true, hasControls: true,
  });
  fabricCanvas.add(group);
}
