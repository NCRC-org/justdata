// dotlender_tooltip.js
// Hover popup for the income / minority choropleth fill layers. Reads
// per-tract loan counts from the map-data API response and combines them
// with the tileset's income_category / minority_category. Suppressed when
// the cursor is over the county mask (outside the clipped area).

import { getMapboxInstance } from './dotlender_map.js';

let currentTooltipPopup = null;

export function attachChoroplethTooltip(tractLoans) {
  const map = getMapboxInstance();
  if (!map) return;
  if (currentTooltipPopup) {
    currentTooltipPopup.remove();
    currentTooltipPopup = null;
  }
  ['dl-income-fill', 'dl-minority-fill'].forEach((layerId) => {
    map.off('mousemove', layerId);
    map.off('mouseleave', layerId);
  });
  // eslint-disable-next-line no-undef
  const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false });
  const onMove = (e) => {
    if (!e.features?.length) return;
    if (map.getLayer('dl-county-mask-fill')) {
      const outside = map.queryRenderedFeatures(e.point, { layers: ['dl-county-mask-fill'] });
      if (outside.length) {
        popup.remove();
        map.getCanvas().style.cursor = '';
        return;
      }
    }
    const props = e.features[0].properties || {};
    const tractId = props.GEOID || props.geoid || props.geoid11 || '';
    const lendingRow = tractLoans[tractId];
    const html = `
      <strong>Tract ${tractId}</strong><br/>
      Income: ${props.income_category ?? '—'}<br/>
      Minority quartile: ${props.minority_category ?? '—'}<br/>
      Loans this filter: ${lendingRow ? lendingRow.loan_count.toLocaleString() : '0'}
    `;
    popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
    map.getCanvas().style.cursor = 'pointer';
  };
  const onLeave = () => {
    popup.remove();
    map.getCanvas().style.cursor = '';
  };
  ['dl-income-fill', 'dl-minority-fill'].forEach((layerId) => {
    map.on('mousemove', layerId, onMove);
    map.on('mouseleave', layerId, onLeave);
  });
  currentTooltipPopup = popup;
}
