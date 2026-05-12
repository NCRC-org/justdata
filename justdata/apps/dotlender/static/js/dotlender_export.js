// dotlender_export.js
// jsPDF export for the DotLender canvas.

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('dl-export-pdf-btn')?.addEventListener('click', () => {
    const canvas = document.getElementById('dotlender-canvas');
    if (!canvas) return;
    const pageSize = document.getElementById('dl-page-size').value;

    // jsPDF UMD attaches to window.jspdf
    // eslint-disable-next-line no-undef
    const { jsPDF } = window.jspdf;

    const isLetter = pageSize === 'letter';
    // Landscape orientation; mm units.
    // Letter landscape: 279.4 × 215.9 mm. Tabloid landscape: 431.8 × 279.4 mm.
    const pdfW = isLetter ? 279.4 : 431.8;
    const pdfH = isLetter ? 215.9 : 279.4;

    const pdf = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: isLetter ? 'letter' : [pdfW, pdfH],
    });

    const imgData = canvas.toDataURL('image/png', 1.0);
    pdf.addImage(imgData, 'PNG', 0, 0, pdfW, pdfH);

    const filename = `dotlender_report_${new Date().toISOString().slice(0, 10)}.pdf`;
    pdf.save(filename);
  });
});
