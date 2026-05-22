// dotlender_breakpoints.js
// Sidebar UI for the race-overlay breakpoint editor. Hidden until a race
// overlay loads; window.dotlenderSetBreakpoints is the entry point used by
// dotlender_race_overlay.js to push computed quartiles in and reveal the
// panel. Apply button forwards the edited values to
// window.dotlenderApplyCustomBreakpoints (defined by the race overlay
// module). The overlay-mode <select> change handler hides the panel when
// the user picks a non-race overlay.

const RACE_OVERLAY_LABELS = {
  minority: '% Minority',
  race_black: '% Black',
  race_hispanic: '% Hispanic',
  race_black_hispanic: '% Black & Hispanic',
  race_asian: '% Asian',
  race_ai_an: '% AI/AN',
  race_nh_opi: '% NHPI',
  race_white: '% White',
};

let bpValues = [25, 50, 75];

function renderBreakpointInputs(count, values) {
  const container = document.getElementById('dl-bp-inputs');
  if (!container) return;
  container.innerHTML = '';
  for (let i = 0; i < count; i += 1) {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex; align-items:center; gap:8px;';
    const label = document.createElement('label');
    label.textContent = `Break ${i + 1}:`;
    label.style.cssText = 'font-size:0.8rem; color:#444; width:60px; flex-shrink:0;';
    const input = document.createElement('input');
    input.type = 'number';
    input.min = '0'; input.max = '100'; input.step = '1';
    input.value = values[i] ?? '';
    input.dataset.bpIndex = String(i);
    input.style.cssText = 'width:70px; padding:3px 6px; border-radius:4px; border:1px solid #ccc; font-size:0.8rem;';
    const pct = document.createElement('span');
    pct.textContent = '%';
    pct.style.fontSize = '0.8rem';
    row.appendChild(label);
    row.appendChild(input);
    row.appendChild(pct);
    container.appendChild(row);
  }
}

window.dotlenderSetBreakpoints = function (quartiles, overlayMode) {
  bpValues = Array.isArray(quartiles) && quartiles.length ? quartiles : [25, 50, 75];
  const countEl = document.getElementById('dl-bp-count');
  const desired = String(Math.min(6, Math.max(2, bpValues.length)));
  if (countEl) countEl.value = desired;
  renderBreakpointInputs(parseInt(desired, 10), bpValues);
  const panel = document.getElementById('dl-race-breakpoints-panel');
  if (panel) panel.style.display = 'block';
  const overlayLabel = document.getElementById('dl-bp-overlay-label');
  if (overlayLabel) overlayLabel.textContent = `— ${RACE_OVERLAY_LABELS[overlayMode] || ''}`;
  // Auto-expand the body so the user sees the controls without an extra
  // click on the freshly loaded overlay. The .dl-collapsible CSS drives
  // the smooth max-height/opacity transition.
  const body = document.getElementById('dl-bp-body');
  const chevron = document.getElementById('dl-bp-chevron');
  if (body) body.classList.add('dl-open');
  if (chevron) chevron.style.transform = 'rotate(180deg)';
};

export function initBreakpointPanel() {
  // Header click toggles the body collapse/expand. The chevron rotates
  // 180deg in the expanded state.
  document.getElementById('dl-bp-header')?.addEventListener('click', () => {
    const body = document.getElementById('dl-bp-body');
    const chevron = document.getElementById('dl-bp-chevron');
    if (!body) return;
    const willOpen = !body.classList.contains('dl-open');
    body.classList.toggle('dl-open', willOpen);
    if (chevron) chevron.style.transform = willOpen ? 'rotate(180deg)' : '';
  });
  document.getElementById('dl-bp-count')?.addEventListener('change', (e) => {
    const count = parseInt(e.target.value, 10);
    renderBreakpointInputs(count, bpValues);
  });
  document.getElementById('dl-bp-apply')?.addEventListener('click', () => {
    const inputs = document.querySelectorAll('#dl-bp-inputs input[data-bp-index]');
    const newBreaks = [];
    inputs.forEach((input) => {
      const val = parseFloat(input.value);
      if (Number.isFinite(val) && val >= 0 && val <= 100) newBreaks.push(val);
    });
    if (!newBreaks.length) return;
    bpValues = [...new Set(newBreaks.map((v) => Math.round(v)))].sort((a, b) => a - b);
    window.dotlenderCurrentBreakpoints = bpValues.slice();
    // Route to the right paint-property updater based on which overlay
    // is active. Race overlays use feature-state; minority uses the
    // tileset's minority_percentage property directly.
    const mode = document.getElementById('dl-overlay-mode')?.value || '';
    if (mode.startsWith('race_')
        && typeof window.dotlenderApplyCustomBreakpoints === 'function') {
      window.dotlenderApplyCustomBreakpoints(bpValues);
    } else if (mode === 'minority'
        && typeof window.dotlenderApplyMinorityBreakpoints === 'function') {
      window.dotlenderApplyMinorityBreakpoints(bpValues);
    }
    document.dispatchEvent(new CustomEvent('dotlender:breakpoints-updated', {
      detail: { overlayMode: mode, breakpoints: bpValues.slice() },
    }));
  });
  // Hide the panel when the user switches to income/none. Race and
  // minority both drive the breakpoints panel; map.js triggers
  // window.dotlenderSetBreakpoints for those modes so the panel reveals
  // itself with appropriate defaults.
  document.getElementById('dl-overlay-mode')?.addEventListener('change', (e) => {
    const mode = String(e.target.value || '');
    if (!mode.startsWith('race_') && mode !== 'minority') {
      const panel = document.getElementById('dl-race-breakpoints-panel');
      if (panel) panel.style.display = 'none';
    }
  });
}
