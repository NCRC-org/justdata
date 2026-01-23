/**
 * Analytics Tables JavaScript
 * Shared table utilities
 */

/**
 * Format number with commas
 */
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}

/**
 * Format date for display
 */
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        return dateStr;
    }
}

/**
 * Export table data to CSV
 * @param {Array} data - Data array
 * @param {Array} columns - Column definitions
 * @param {string} filename - Output filename
 */
function exportTableToCSV(data, columns, filename) {
    if (!data || data.length === 0) {
        alert('No data to export');
        return;
    }

    // Build CSV content
    const headers = columns.map(c => '"' + c.label + '"').join(',');
    const rows = data.map(function(row) {
        return columns.map(function(col) {
            let value = row[col.key];
            if (Array.isArray(value)) {
                value = value.join('; ');
            }
            if (value === null || value === undefined) {
                value = '';
            }
            // Escape quotes and wrap in quotes
            return '"' + String(value).replace(/"/g, '""') + '"';
        }).join(',');
    });

    const csv = [headers, ...rows].join('\n');

    // Create download link
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
