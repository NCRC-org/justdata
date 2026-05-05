// LenderProfile Report - utility helpers (formatters, escape, DOM updates,
// PDF export). Moved verbatim from report_v2.js. Function bodies untouched.

// UTILITY FUNCTIONS
// =============================================================================

export function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined && value !== null) {
        el.textContent = value;
    }
}

export function formatNumber(value) {
    if (value === null || value === undefined) return '--';
    return value.toLocaleString();
}

export function formatCurrency(value) {
    if (value === null || value === undefined || value === 0) return '--';
    if (value >= 1e12) return '$' + (value / 1e12).toFixed(2) + 'T';
    if (value >= 1e9) return '$' + (value / 1e9).toFixed(2) + 'B';
    if (value >= 1e6) return '$' + (value / 1e6).toFixed(2) + 'M';
    if (value >= 1e3) return '$' + (value / 1e3).toFixed(1) + 'K';
    return '$' + value.toLocaleString();
}

export function formatCurrencyShort(value) {
    if (value >= 1e12) return '$' + (value / 1e12).toFixed(1) + 'T';
    if (value >= 1e9) return '$' + (value / 1e9).toFixed(0) + 'B';
    if (value >= 1e6) return '$' + (value / 1e6).toFixed(0) + 'M';
    if (value >= 1e3) return '$' + (value / 1e3).toFixed(0) + 'K';
    return '$' + value;
}

export function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
        return dateStr;
    }
}

export function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

export function exportToPDF() {
    window.print();
}

export function updateGrowthElement(id, value) {
    const el = document.getElementById(id);
    if (el && value !== null && value !== undefined) {
        const formatted = value > 0 ? `+${value.toFixed(1)}%` : `${value.toFixed(1)}%`;
        el.textContent = formatted;
        el.className = 'growth-val ' + (value > 0 ? 'positive' : (value < 0 ? 'negative' : ''));
    }
}
