// dotlender_canvas.js
// Fabric.js canvas builder for the DotLender PDF report.
// Canvas is rendered at 2x internal resolution (CSS clamps the on-screen
// display back to 1056×816). Layout: county polygon outline + legend +
// north arrow + scale bar + NCRC logo. The live Mapbox map is captured
// inside the same map.once('idle') callback that draws the county outline
// so projection and capture share a single viewport snapshot.

import { getCurrentMapData, getActiveRaceFilters } from './dotlender_map.js';
import { getFilterState } from './dotlender_filters.js';
import { getCachedCountyGeojson, getCachedMapContainerSize } from './dotlender_overlays.js';
import { placeMapLegend } from './dotlender_legend.js';

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

  // Aspect-locked draggable map frame — this is what the user positions
  // to choose where the captured map screenshot lands on the PDF. The
  // dashed county outline (added LAST) rides inside the frame purely as
  // a visual guide; the screenshot itself already has the county shape
  // carved out by the dl-county-mask-fill white layer.
  placeMapFrame();

  await placeLogo();
  placeMapLegend(fabricCanvas, state, getActiveRaceFilters());
  placeScaleBar(mapInstance);
  await placeNorthArrow();

  // County outline LAST so it renders on top, fit inside the map frame.
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

// --- Map frame (aspect-locked, draggable) --------------------------------

function syncMapPlaceholderFromFrame(frame) {
  const b = frame.getBoundingRect();
  window.dotlenderMapPlaceholder = {
    left: b.left, top: b.top, width: b.width, height: b.height,
  };
}

function rebuildScaleBar() {
  const oldScale = fabricCanvas.getObjects().find((o) => (
    o.type === 'group' && (o._objects || o.getObjects?.() || [])
      .some((c) => c.type === 'text' && c.text === 'Miles')
  ));
  if (oldScale) fabricCanvas.remove(oldScale);
  placeScaleBar(window.dotlenderMap);
  fabricCanvas.renderAll();
}

function placeMapFrame() {
  // Aspect-locked rectangle that drives where the captured Mapbox PNG
  // lands on the exported PDF. Aspect matches the live Mapbox container
  // (= the PNG's aspect), so no vertical stretch when the export scales
  // the screenshot into these bounds.
  const containerSize = getCachedMapContainerSize();
  const aspect = containerSize
    ? containerSize.width / containerSize.height
    : 1.5;
  const frameW = Math.round(CANVAS_W * 0.6);
  const frameH = Math.round(frameW / aspect);
  const frameLeft = Math.round((CANVAS_W - frameW) / 2);
  const frameTop = Math.round((CANVAS_H - frameH) / 2);

  // eslint-disable-next-line no-undef
  const frame = new fabric.Rect({
    left: frameLeft, top: frameTop, width: frameW, height: frameH,
    fill: 'transparent',
    stroke: PLACEHOLDER_STROKE,
    strokeWidth: 2,
    strokeDashArray: [8, 4],
    selectable: true,
    hasControls: true,
    lockUniScaling: true,
    excludeFromExport: true,
  });
  fabricCanvas.add(frame);
  window.dotlenderMapFrame = frame;
  syncMapPlaceholderFromFrame(frame);

  frame.on('moving', () => {
    syncMapPlaceholderFromFrame(frame);
    updateCountyOutlineToFrame();
  });
  frame.on('scaling', () => {
    syncMapPlaceholderFromFrame(frame);
    updateCountyOutlineToFrame();
    rebuildScaleBar();
  });
  return frame;
}

// --- County outline (visual guide, rides inside the frame) ---------------

function fitPathToFrame(countyPath, frame) {
  // Scale the projected county path (which lives in Mapbox container px
  // space) into the current frame's actual rendered size, centered with
  // a uniform contain-fit so the shape's aspect is preserved.
  const pathBbox = countyPath.getBoundingRect(true);
  const frameW = frame.width * (frame.scaleX || 1);
  const frameH = frame.height * (frame.scaleY || 1);
  const scale = Math.min(frameW / pathBbox.width, frameH / pathBbox.height);
  const scaledW = pathBbox.width * scale;
  const scaledH = pathBbox.height * scale;
  const offsetX = (frameW - scaledW) / 2;
  const offsetY = (frameH - scaledH) / 2;
  countyPath.set({
    scaleX: scale,
    scaleY: scale,
    left: frame.left + offsetX - (pathBbox.left * scale),
    top: frame.top + offsetY - (pathBbox.top * scale),
  });
  countyPath.setCoords();
}

function updateCountyOutlineToFrame() {
  const countyPath = window.dotlenderCountyOutline;
  const frame = window.dotlenderMapFrame;
  if (countyPath && frame) {
    fitPathToFrame(countyPath, frame);
    fabricCanvas.renderAll();
  }
}

function placeCountyOutline() {
  const mapInstance = window.dotlenderMap;
  const geojson = getCachedCountyGeojson();
  const containerSize = getCachedMapContainerSize();
  const frame = window.dotlenderMapFrame;
  if (!mapInstance || !geojson?.features?.length || !containerSize || !frame) {
    return;
  }
  const pathStr = geojsonToPath(
    geojson.features[0].geometry, mapInstance,
    containerSize.width, containerSize.height,
  );
  if (!pathStr) return;
  // eslint-disable-next-line no-undef
  const countyPath = new fabric.Path(pathStr, {
    fill: 'transparent',
    stroke: PLACEHOLDER_STROKE,
    strokeWidth: 2,
    strokeDashArray: [12, 6],
    selectable: false,
    evented: false,
    excludeFromExport: true,
  });
  fitPathToFrame(countyPath, frame);
  fabricCanvas.add(countyPath);
  window.dotlenderCountyOutline = countyPath;
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

// --- Scale bar (independent draggable group) -----------------------------

function placeScaleBar(mapInstance) {
  if (!mapInstance) return;
  // Real-world width of the currently shown map viewport in meters.
  const bounds = mapInstance.getBounds();
  const west = bounds.getWest();
  const east = bounds.getEast();
  const centerLat = mapInstance.getCenter().lat;
  const lngDiff = east - west;
  const metersPerDegLng = 111320 * Math.cos((centerLat * Math.PI) / 180);
  const mapWidthMeters = lngDiff * metersPerDegLng;
  // Width of the map IMAGE on the canvas (= the placeholder/outline width
  // the user dragged into place). Falls back to 60% of canvas width when
  // no placeholder is registered yet.
  const placeholder = window.dotlenderMapPlaceholder;
  const mapCanvasWidth = placeholder?.width || (CANVAS_W * 0.6);
  const metersPerCanvasPx = mapWidthMeters / mapCanvasWidth;
  const mileInMeters = 1609.34;
  // Pick a clean base mile value where one unit ≈ 40–120 canvas pixels.
  let baseMiles = 1;
  while (baseMiles * mileInMeters / metersPerCanvasPx > 120) baseMiles /= 2;
  while (baseMiles * mileInMeters / metersPerCanvasPx < 40) baseMiles *= 2;
  if (baseMiles >= 2) baseMiles = Math.round(baseMiles);
  if (baseMiles < 1 && baseMiles > 0.4) baseMiles = 0.5;
  else if (baseMiles < 0.4) baseMiles = 0.25;

  const unitPx = Math.round(baseMiles * mileInMeters / metersPerCanvasPx);
  const totalPx = unitPx * 4;
  const tickH = 14;
  const objs = [];

  // eslint-disable-next-line no-undef
  objs.push(new fabric.Line([0, 0, totalPx, 0], { stroke: '#222', strokeWidth: 2.5 }));
  [0, 1, 2, 4].forEach((mult) => {
    const x = mult * unitPx;
    // eslint-disable-next-line no-undef
    objs.push(new fabric.Line([x, -tickH / 2, x, tickH / 2], {
      stroke: '#222', strokeWidth: 2,
    }));
    const milesVal = mult * baseMiles;
    const label = milesVal === 0
      ? '0'
      : `${Number.isInteger(milesVal) ? milesVal : milesVal.toFixed(2)} mi`;
    const offset = milesVal === 0 ? 4 : (label.length * 5);
    // eslint-disable-next-line no-undef
    objs.push(new fabric.Text(label, {
      left: x - offset, top: tickH / 2 + 4,
      fontSize: 18, fontFamily: LEGEND_FONT, fill: '#222',
    }));
  });
  // eslint-disable-next-line no-undef
  objs.push(new fabric.Text('Miles', {
    left: 0, top: -tickH / 2 - 28,
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

function addSimpleArrowFallback() {
  console.log('[dotlender] north arrow: using simple triangle fallback');
  // eslint-disable-next-line no-undef
  const arrow = new fabric.Triangle({
    width: 100, height: 130, fill: '#000',
    left: CANVAS_W - 280, top: CANVAS_H - 320,
    selectable: true, hasControls: true,
  });
  // eslint-disable-next-line no-undef
  const label = new fabric.Text('N', {
    fontSize: 60, fontWeight: 'bold', fontFamily: LEGEND_FONT, fill: '#000',
    left: CANVAS_W - 254, top: CANVAS_H - 200,
    selectable: true,
  });
  fabricCanvas.add(arrow);
  fabricCanvas.add(label);
}

function loadNorthArrowAsImage(resolve) {
  console.log('[dotlender] north arrow: loadNorthArrowAsImage starting');
  // eslint-disable-next-line no-undef
  fabric.Image.fromURL(NORTH_ARROW_SVG, (img) => {
    if (!img || !img.width) {
      console.warn('[dotlender] north arrow image load returned empty — using simple fallback');
      addSimpleArrowFallback();
      resolve();
      return;
    }
    img.scaleToHeight(200);
    img.set({
      left: CANVAS_W - 280, top: CANVAS_H - 320,
      selectable: true, hasControls: true,
    });
    fabricCanvas.add(img);
    console.log('[dotlender] north arrow: image added');
    resolve();
  }, { crossOrigin: 'anonymous' });
}

async function placeNorthArrow() {
  return new Promise((resolve) => {
    console.log('[dotlender] placeNorthArrow: fetching', NORTH_ARROW_SVG);
    fetch(NORTH_ARROW_SVG)
      .then((r) => {
        console.log('[dotlender] north arrow fetch status:', r.status);
        return r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`));
      })
      .then((svgString) => {
        console.log('[dotlender] north arrow SVG length:', svgString.length);
        // eslint-disable-next-line no-undef
        fabric.loadSVGFromString(svgString, (objects, options) => {
          console.log('[dotlender] north arrow parsed objects:', objects?.length || 0);
          if (!objects || !objects.length) {
            loadNorthArrowAsImage(resolve);
            return;
          }
          // eslint-disable-next-line no-undef
          const svg = fabric.util.groupSVGElements(objects, options);
          svg.scaleToHeight(200);
          svg.set({
            left: CANVAS_W - 280, top: CANVAS_H - 320,
            selectable: true, hasControls: true,
          });
          fabricCanvas.add(svg);
          console.log('[dotlender] north arrow: SVG added to canvas');
          resolve();
        });
      })
      .catch((err) => {
        console.error('[dotlender] north arrow load failed:', err);
        addSimpleArrowFallback();
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
