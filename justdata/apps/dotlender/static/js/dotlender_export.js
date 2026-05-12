// dotlender_export.js
// PDF export composer for the DotLender canvas builder.
//
// Two-layer compose:
//   1. Canvas elements (title, legends, summary, filters, methodology, logo)
//      — rendered from Fabric.js with the map placeholder hidden so the
//      blue rect and instruction text don't bleed through.
//   2. Live Mapbox map — captured at click time via map.getCanvas().toDataURL()
//      and placed over the canvas at the placeholder's position so panning /
//      zooming the live map before export is reflected in the PDF.

import { CANVAS_W, CANVAS_H, getFabricCanvas } from './dotlender_canvas.js';

async function captureMap() {
  const mapInstance = window.dotlenderMap;
  if (!mapInstance) return null;
  return new Promise((resolve) => {
    const grab = () => {
      try {
        resolve(mapInstance.getCanvas().toDataURL('image/png', 1.0));
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

function captureCanvasWithoutPlaceholder() {
  const fc = getFabricCanvas();
  if (!fc) return null;
  const ph = window.dotlenderMapPlaceholder;
  const strokeColor = ph?.strokeColor || '#4a90d9';
  // Temporarily hide the placeholder rect + label
  const placeholderObjects = fc.getObjects().filter((o) => isPlaceholderObject(o, strokeColor));
  placeholderObjects.forEach((o) => o.set('visible', false));
  fc.renderAll();
  // Multiplier 1 because the canvas is already at 2x internal resolution.
  const dataUrl = fc.toDataURL({ format: 'png', multiplier: 1 });
  placeholderObjects.forEach((o) => o.set('visible', true));
  fc.renderAll();
  return dataUrl;
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('dl-export-pdf-btn')?.addEventListener('click', async () => {
    const pageSize = document.getElementById('dl-page-size').value;
    // eslint-disable-next-line no-undef
    const { jsPDF } = window.jspdf;
    const isLetter = pageSize === 'letter';
    // Landscape mm — letter: 279.4 × 215.9, tabloid: 431.8 × 279.4
    const pdfW = isLetter ? 279.4 : 431.8;
    const pdfH = isLetter ? 215.9 : 279.4;

    const pdf = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: isLetter ? 'letter' : [pdfW, pdfH],
    });

    const mapDataUrl = await captureMap();
    const canvasDataUrl = captureCanvasWithoutPlaceholder();

    // Layer 1: canvas frame (text + legends, no map). Cover the full page.
    if (canvasDataUrl) {
      pdf.addImage(canvasDataUrl, 'PNG', 0, 0, pdfW, pdfH);
    }

    // Layer 2: live map image positioned at placeholder bounds, converted
    // from canvas-internal pixels to PDF millimeters using the same
    // CANVAS_W/H constants the canvas was rendered at.
    if (mapDataUrl && window.dotlenderMapPlaceholder) {
      const ph = window.dotlenderMapPlaceholder;
      const scaleX = pdfW / CANVAS_W;
      const scaleY = pdfH / CANVAS_H;
      pdf.addImage(
        mapDataUrl,
        'PNG',
        ph.left * scaleX,
        ph.top * scaleY,
        ph.width * scaleX,
        ph.height * scaleY,
      );
    }

    const filename = `dotlender_report_${new Date().toISOString().slice(0, 10)}.pdf`;
    pdf.save(filename);
  });
});
