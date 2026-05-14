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
import { placeScaleBar, placePageCutoffMarker } from './dotlender_scalebar.js';

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

  // Map image capture. Temporarily raise Mapbox's pixel ratio to 3 so the
  // captured PNG has 3x the display resolution — that's what kills the
  // white tile-seam smidges when the image is upscaled into the canvas.
  // We restore the original pixel ratio after capture.
  const mapInstance = window.dotlenderMap;
  if (mapInstance) {
    await new Promise((resolve) => {
      const originalPixelRatio = (typeof mapInstance.getPixelRatio === 'function'
        ? mapInstance.getPixelRatio()
        : (window.devicePixelRatio || 1));
      const canBumpRatio = typeof mapInstance.setPixelRatio === 'function';
      if (canBumpRatio) mapInstance.setPixelRatio(3);
      mapInstance.once('idle', () => {
        try {
          window.dotlenderMapCaptureDataUrl = mapInstance.getCanvas().toDataURL('image/png', 1.0);
        } catch (err) {
          console.warn('[dotlender] map capture failed', err);
          window.dotlenderMapCaptureDataUrl = null;
        }
        if (canBumpRatio) mapInstance.setPixelRatio(originalPixelRatio);
        resolve();
      });
      mapInstance.triggerRepaint();
    });
  }

  // Dashed red rectangle showing the selected printable page area, sent
  // to back so it sits behind all other canvas objects.
  placePageCutoffMarker();

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

  // County outline + name labels render on top of the map frame; city
  // labels render last so they sit above county names.
  placeCountyOutline();
  placeCountyLabels();
  placeCityLabels();

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
  // Save the pre-fit bbox origin so label-positioning code can map
  // canvas-fit projected coords through the same transform.
  countyPath._origBboxLeft = pathBbox.left;
  countyPath._origBboxTop = pathBbox.top;
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

// --- County + city name labels (moveable text on canvas) -----------------

function projectLngLatToCanvas(mapInstance, lng, lat, containerSize) {
  // Replicate projectCoords' uniform-fit math for a single point so that
  // labels live in the same canvas-fit space as the unscaled county path.
  const pt = mapInstance.project([lng, lat]);
  const scale = Math.min(CANVAS_W / containerSize.width, CANVAS_H / containerSize.height);
  const offsetX = (CANVAS_W - containerSize.width * scale) / 2;
  const offsetY = (CANVAS_H - containerSize.height * scale) / 2;
  return { x: pt.x * scale + offsetX, y: pt.y * scale + offsetY };
}

function applyOutlineTransform(canvasFitPt, outline) {
  // Map a canvas-fit projected point through the fitPathToFrame transform
  // that the outline received. Uses _origBboxLeft/Top saved at fit time.
  const bboxLeft = outline._origBboxLeft || 0;
  const bboxTop = outline._origBboxTop || 0;
  const sx = outline.scaleX || 1;
  const sy = outline.scaleY || 1;
  return {
    x: (canvasFitPt.x - bboxLeft) * sx + outline.left,
    y: (canvasFitPt.y - bboxTop) * sy + outline.top,
  };
}

function placeCountyLabels() {
  const mapInstance = window.dotlenderMap;
  const containerSize = getCachedMapContainerSize();
  const outline = window.dotlenderCountyOutline;
  const counties = window.dotlenderCountyGeojsonList || [];
  if (!mapInstance || !containerSize || !outline || !counties.length) return;
  counties.forEach(({ feature }) => {
    let nameRaw = feature.properties?.NAME || feature.properties?.name || '';
    nameRaw = String(nameRaw).replace(/\s+County$/i, '');
    const countyName = nameRaw ? `${nameRaw} County` : 'County';
    let centroid;
    try {
      // eslint-disable-next-line no-undef
      centroid = turf.centroid(feature);
    } catch (e) { return; }
    const [lng, lat] = centroid.geometry.coordinates;
    const canvasFit = projectLngLatToCanvas(mapInstance, lng, lat, containerSize);
    const finalPt = applyOutlineTransform(canvasFit, outline);
    // eslint-disable-next-line no-undef
    const label = new fabric.Text(countyName, {
      left: finalPt.x, top: finalPt.y,
      fontSize: 26, fontFamily: LEGEND_FONT, fontWeight: 'bold',
      fill: '#222', stroke: '#fff', strokeWidth: 3, paintFirst: 'stroke',
      originX: 'center', originY: 'center',
      selectable: true, hasControls: true,
    });
    fabricCanvas.add(label);
  });
}

function placeCityLabels() {
  const mapInstance = window.dotlenderMap;
  const containerSize = getCachedMapContainerSize();
  const outline = window.dotlenderCountyOutline;
  const cities = window.dotlenderCityCentroids || [];
  const selected = window.dotlenderSelectedCities || cities;
  if (!mapInstance || !containerSize || !outline) return;
  // Only show per-city labels when the user has 2+ cities selected; with
  // a single city the legend itself names the city.
  if (selected.length < 2) return;
  const selectedKeys = new Set(selected.map((c) => `${c.stateFp}:${c.name}`));
  cities
    .filter((c) => selectedKeys.has(`${c.stateFp}:${c.name}`))
    .forEach((city) => {
      const canvasFit = projectLngLatToCanvas(
        mapInstance, city.lng, city.lat, containerSize,
      );
      const finalPt = applyOutlineTransform(canvasFit, outline);
      // eslint-disable-next-line no-undef
      const label = new fabric.Text(city.name, {
        left: finalPt.x, top: finalPt.y,
        fontSize: 22, fontFamily: LEGEND_FONT, fontStyle: 'italic',
        fill: '#c0392b', stroke: '#fff', strokeWidth: 2, paintFirst: 'stroke',
        originX: 'center', originY: 'center',
        selectable: true, hasControls: true,
      });
      fabricCanvas.add(label);
    });
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

function buildArrowPrimitives() {
  // Upward-pointing arrow built from two Fabric primitives. Returns a
  // fabric.Group sized to roughly match a 180px-tall N letterform.
  // eslint-disable-next-line no-undef
  const head = new fabric.Triangle({
    width: 60, height: 60, fill: '#000',
    originX: 'center', originY: 'bottom', top: 0, left: 0,
  });
  // eslint-disable-next-line no-undef
  const shaft = new fabric.Rect({
    width: 14, height: 110, fill: '#000',
    originX: 'center', originY: 'top', top: 60, left: 0,
  });
  // eslint-disable-next-line no-undef
  return new fabric.Group([head, shaft], { originX: 'center', originY: 'top' });
}

function placeCombinedNorthArrow(nObject) {
  // Side-by-side: typographic N (left) + upward arrow (right), 30px gap.
  nObject.set({ left: 0, top: 0 });
  const nW = (nObject.width || 0) * (nObject.scaleX || 1);
  const arrowGroup = buildArrowPrimitives();
  arrowGroup.set({ left: nW + 30, top: 0 });
  // eslint-disable-next-line no-undef
  const combined = new fabric.Group([nObject, arrowGroup], {
    left: CANVAS_W - 320, top: CANVAS_H - 320,
    selectable: true, hasControls: true,
  });
  fabricCanvas.add(combined);
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
    img.scaleToHeight(180);
    placeCombinedNorthArrow(img);
    console.log('[dotlender] north arrow: image + arrow group added');
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
          const nLetter = fabric.util.groupSVGElements(objects, options);
          nLetter.scaleToHeight(180);
          placeCombinedNorthArrow(nLetter);
          console.log('[dotlender] north arrow: SVG + arrow group added');
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
