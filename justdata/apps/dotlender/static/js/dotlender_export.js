// dotlender_export.js
// PDF export composer for the DotLender canvas builder.
//
// Two-layer compose:
//   1. Live Mapbox map captured at click time, placed at PDF z-index 0
//      with aspect-correct contain-fit (centered, no stretch).
//   2. Fabric.js canvas captured with a transparent background so the
//      legend, north arrow, scale bar, and logo overlay the map.
//      The blue map placeholder rect/label are hidden during capture.

import { CANVAS_W, CANVAS_H, getFabricCanvas } from './dotlender_canvas.js';

async function captureMap() {
  const mapInstance = window.dotlenderMap;
  if (!mapInstance) return null;
  return new Promise((resolve) => {
    const grab = () => {
      try {
        const canvas = mapInstance.getCanvas();
        resolve({
          dataUrl: canvas.toDataURL('image/png', 1.0),
          width: canvas.width,
          height: canvas.height,
        });
      } catch (err) {
        console.warn('[dotlender] live-map capture failed', err);
        resolve(null);
      }
    };
    mapInstance.once('idle', grab);
    mapInstance.triggerRepaint();
  });
}

function isPlaceholderObject(obj, strokeColor) {
  if (!obj) return false;
  if (obj.type === 'rect' && obj.stroke === strokeColor) return true;
  if ((obj.type === 'textbox' || obj.type === 'text') && obj.fill === strokeColor) return true;
  return false;
}

function captureCanvasTransparentWithoutPlaceholder() {
  const fc = getFabricCanvas();
  if (!fc) return null;
  const ph = window.dotlenderMapPlaceholder;
  const strokeColor = ph?.strokeColor || '#4a90d9';
  const placeholderObjects = fc.getObjects().filter((o) => isPlaceholderObject(o, strokeColor));
  placeholderObjects.forEach((o) => o.set('visible', false));
  // Transparent background during capture so the map shows through
  // wherever the legend group doesn't paint pixels.
  const origBg = fc.backgroundColor;
  fc.setBackgroundColor(null, fc.renderAll.bind(fc));
  const dataUrl = fc.toDataURL({ format: 'png', multiplier: 1 });
  // Restore for the on-screen builder.
  fc.setBackgroundColor(origBg || '#ffffff', fc.renderAll.bind(fc));
  placeholderObjects.forEach((o) => o.set('visible', true));
  fc.renderAll();
  return dataUrl;
}

function fitImageContain(imgW, imgH, pageW, pageH) {
  // Aspect-correct contain fit: scale the image to fit inside the page,
  // letterbox the unused dimension, center the result. Prevents the
  // vertical stretch when the source canvas aspect ratio differs from
  // the PDF page aspect ratio.
  const pageAR = pageW / pageH;
  const imgAR = imgW / imgH;
  let w; let h; let x; let y;
  if (imgAR > pageAR) {
    w = pageW; h = pageW / imgAR; x = 0; y = (pageH - h) / 2;
  } else {
    h = pageH; w = pageH * imgAR; x = (pageW - w) / 2; y = 0;
  }
  return { x, y, w, h };
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('dl-export-pdf-btn')?.addEventListener('click', async () => {
    const pageSize = document.getElementById('dl-page-size').value;
    // eslint-disable-next-line no-undef
    const { jsPDF } = window.jspdf;
    const isLetter = pageSize === 'letter';
    const pdfW = isLetter ? 279.4 : 431.8; // landscape mm
    const pdfH = isLetter ? 215.9 : 279.4;

    const pdf = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: isLetter ? 'letter' : [pdfW, pdfH],
    });

    const mapCapture = await captureMap();
    const canvasDataUrl = captureCanvasTransparentWithoutPlaceholder();

    // Layer 1: map (z-index 0), aspect-correct contain fit.
    if (mapCapture && mapCapture.dataUrl) {
      const { x, y, w, h } = fitImageContain(mapCapture.width, mapCapture.height, pdfW, pdfH);
      pdf.addImage(mapCapture.dataUrl, 'PNG', x, y, w, h);
    }

    // Layer 2: canvas with transparent background — legends, north arrow,
    // scale bar, logo overlay the map. Canvas-internal coordinates already
    // span the full CANVAS_W × CANVAS_H so scaling to the full PDF page
    // preserves the legend positions.
    if (canvasDataUrl) {
      pdf.addImage(canvasDataUrl, 'PNG', 0, 0, pdfW, pdfH);
    }

    // Silence "imported but unused" lint by referencing the constants
    // (they're documented as the canvas resolution used to size positions).
    void CANVAS_W; void CANVAS_H;

    const filename = `dotlender_report_${new Date().toISOString().slice(0, 10)}.pdf`;
    pdf.save(filename);
  });
});
