/**
 * Lender Interest View JavaScript
 */

let map;
let lenderData = [];

/**
 * Initialize on page load
 */
$(document).ready(function() {
    // Initialize map
    map = initMap('lender-map');

    // Load initial data
    loadData();

    // Handle filter changes
    $('#time-period, #min-users').on('change', loadData);
});

/**
 * Load lender interest data
 */
function loadData() {
    const days = $('#time-period').val() || 90;
    const minUsers = $('#min-users').val() || 1;

    // Show loading state
    $('#lender-tbody').html('<tr><td colspan="6" class="loading-cell">Loading lender data...</td></tr>');

    $.ajax({
        url: '/analytics/api/lender-interest',
        data: {
            days: days,
            min_users: minUsers
        },
        success: function(response) {
            if (response.success) {
                lenderData = response.data;
                renderTable(lenderData);
                renderMap(lenderData);
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
 * Render lender table
 */
function renderTable(data) {
    const tbody = $('#lender-tbody').empty();

    // Count unique lenders
    const uniqueLenders = new Set(data.map(d => d.lender_id)).size;
    $('#lender-count').text(uniqueLenders + ' lenders');

    if (data.length === 0) {
        tbody.html('<tr><td colspan="6" class="loading-cell">No lender data found</td></tr>');
        return;
    }

    // Aggregate by lender
    const byLender = {};
    data.forEach(function(item) {
        const id = item.lender_id;
        if (!byLender[id]) {
            byLender[id] = {
                lender_id: id,
                lender_name: item.lender_name,
                unique_users: 0,
                event_count: 0,
                locations: [],
                last_activity: null
            };
        }
        byLender[id].unique_users += item.unique_users || 0;
        byLender[id].event_count += item.event_count || 0;

        if (item.researcher_state) {
            const loc = item.researcher_city
                ? item.researcher_city + ', ' + item.researcher_state
                : item.researcher_state;
            if (!byLender[id].locations.includes(loc)) {
                byLender[id].locations.push(loc);
            }
        }

        if (!byLender[id].last_activity || item.last_activity > byLender[id].last_activity) {
            byLender[id].last_activity = item.last_activity;
        }
    });

    // Sort by unique users
    const sorted = Object.values(byLender).sort((a, b) => b.unique_users - a.unique_users);

    sorted.forEach(function(lender) {
        const name = lender.lender_name || 'Unknown';
        const locations = lender.locations.slice(0, 3).join(', ');
        const moreLocations = lender.locations.length > 3
            ? ' +' + (lender.locations.length - 3) + ' more'
            : '';

        const row = $('<tr>')
            .append('<td><strong>' + escapeHtml(name) + '</strong></td>')
            .append('<td><code>' + escapeHtml(lender.lender_id) + '</code></td>')
            .append('<td>' + formatNumber(lender.unique_users) + '</td>')
            .append('<td>' + formatNumber(lender.event_count) + '</td>')
            .append('<td>' + escapeHtml(locations) + '<span style="color: #888;">' + moreLocations + '</span></td>')
            .append('<td>' + formatDate(lender.last_activity) + '</td>');

        tbody.append(row);
    });
}

/**
 * Render researcher locations on map
 */
function renderMap(data) {
    // Clear existing layers
    map.eachLayer(function(layer) {
        if (layer instanceof L.CircleMarker) {
            map.removeLayer(layer);
        }
    });

    // Aggregate locations
    const locationCounts = {};
    data.forEach(function(item) {
        const state = item.researcher_state;
        if (state && STATE_CENTERS[state]) {
            if (!locationCounts[state]) {
                locationCounts[state] = { count: 0, lenders: new Set() };
            }
            locationCounts[state].count += item.unique_users || 0;
            if (item.lender_id) {
                locationCounts[state].lenders.add(item.lender_id);
            }
        }
    });

    // Add markers for each state with research activity
    Object.entries(locationCounts).forEach(function([state, info]) {
        const center = STATE_CENTERS[state];
        if (!center) return;

        const radius = Math.min(Math.max(Math.sqrt(info.count) * 3, 8), 30);

        L.circleMarker([center.lat, center.lng], {
            radius: radius,
            fillColor: '#7b1fa2',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.7
        })
        .bindPopup(
            '<strong>' + escapeHtml(state) + '</strong><br>' +
            'Researchers: ' + formatNumber(info.count) + '<br>' +
            'Lenders researched: ' + info.lenders.size
        )
        .addTo(map);
    });
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
    $('#lender-tbody').html(
        '<tr><td colspan="6" class="loading-cell" style="color: #dc3545;">' +
        '<i class="fas fa-exclamation-triangle"></i> ' + escapeHtml(message) +
        '</td></tr>'
    );
}
