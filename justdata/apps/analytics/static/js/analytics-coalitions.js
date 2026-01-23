/**
 * Coalition Opportunities JavaScript
 */

let coalitionData = [];

/**
 * Initialize on page load
 */
$(document).ready(function() {
    // Load initial data
    loadData();

    // Handle filter changes
    $('#time-period, #min-users, #entity-type').on('change', loadData);
});

/**
 * Load coalition opportunities data
 */
function loadData() {
    const days = $('#time-period').val() || 90;
    const minUsers = $('#min-users').val() || 3;
    const entityType = $('#entity-type').val() || '';

    // Show loading state
    $('#coalition-tbody').html('<tr><td colspan="6" class="loading-cell">Loading coalition data...</td></tr>');

    $.ajax({
        url: '/analytics/api/coalition-opportunities',
        data: {
            days: days,
            min_users: minUsers,
            entity_type: entityType
        },
        success: function(response) {
            if (response.success) {
                coalitionData = response.data;
                renderTable(coalitionData);
            } else {
                showError('Failed to load data: ' + response.error);
            }
        },
        error: function(xhr) {
            console.error('API error:', xhr.responseText);
            showError('Failed to connect to API');
        }
    });
}

/**
 * Render coalition opportunities table
 */
function renderTable(data) {
    const tbody = $('#coalition-tbody').empty();
    $('#coalition-count').text(data.length + ' opportunities');

    if (data.length === 0) {
        tbody.html('<tr><td colspan="6" class="loading-cell">No coalition opportunities found. Try lowering the minimum users filter.</td></tr>');
        return;
    }

    data.forEach(function(item) {
        const entityType = item.entity_type || 'unknown';
        const entityName = item.entity_name || item.entity_id || 'Unknown';

        // Organizations list
        const orgs = item.organizations || [];
        const orgTags = orgs.slice(0, 5).map(function(org) {
            return '<span class="org-tag">' + escapeHtml(org) + '</span>';
        }).join('');
        const moreOrgs = orgs.length > 5
            ? '<span class="org-tag">+' + (orgs.length - 5) + ' more</span>'
            : '';

        // Researcher states
        const states = item.researcher_states || [];
        const stateList = states.slice(0, 5).join(', ');
        const moreStates = states.length > 5
            ? ' +' + (states.length - 5) + ' more'
            : '';

        const row = $('<tr>')
            .append('<td><span class="type-badge ' + entityType + '">' + (entityType === 'county' ? 'County' : 'Lender') + '</span></td>')
            .append('<td><strong>' + escapeHtml(entityName) + '</strong>' +
                    (entityType === 'county' && item.entity_id ? '<br><small style="color: #888;">FIPS: ' + item.entity_id + '</small>' : '') +
                    '</td>')
            .append('<td><strong>' + formatNumber(item.unique_users) + '</strong></td>')
            .append('<td><div class="org-tags">' + orgTags + moreOrgs + '</div></td>')
            .append('<td>' + escapeHtml(stateList) + '<span style="color: #888;">' + moreStates + '</span></td>')
            .append('<td>' + formatDate(item.last_activity) + '</td>');

        tbody.append(row);
    });
}

/**
 * Export to CSV
 */
function exportToCSV() {
    if (!coalitionData || coalitionData.length === 0) {
        alert('No data to export');
        return;
    }

    const columns = [
        { key: 'entity_type', label: 'Type' },
        { key: 'entity_name', label: 'Entity Name' },
        { key: 'entity_id', label: 'Entity ID' },
        { key: 'unique_users', label: 'Unique Users' },
        { key: 'unique_organizations', label: 'Unique Organizations' },
        { key: 'organizations', label: 'Organizations' },
        { key: 'researcher_states', label: 'Researcher States' },
        { key: 'last_activity', label: 'Last Activity' }
    ];

    const filename = 'coalition-opportunities-' + new Date().toISOString().split('T')[0] + '.csv';
    exportTableToCSV(coalitionData, columns, filename);
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
    $('#coalition-tbody').html(
        '<tr><td colspan="6" class="loading-cell" style="color: #dc3545;">' +
        '<i class="fas fa-exclamation-triangle"></i> ' + escapeHtml(message) +
        '</td></tr>'
    );
}
