/**
 * Lender Interest View JavaScript
 */

let map;
let lenderData = [];
let demoMode = false;
let syntheticData = null;

/**
 * Initialize on page load
 */
$(document).ready(function() {
    // Check for demo mode
    demoMode = localStorage.getItem('analyticsDemo') === 'true';

    // Initialize map
    map = initMap('lender-map');

    // Load data (with synthetic data if demo mode)
    if (demoMode) {
        loadSyntheticData().then(function() {
            loadData();
        });
    } else {
        loadData();
    }

    // Handle filter changes
    $('#time-period, #min-users').on('change', loadData);
});

/**
 * Load synthetic data from JSON file
 */
function loadSyntheticData() {
    return $.ajax({
        url: '/analytics/static/demo_data/synthetic_events.json',
        dataType: 'json',
        success: function(data) {
            syntheticData = data;
            console.log('Lender Interest: Loaded synthetic data:', data.events.length, 'events');
        },
        error: function(xhr, status, error) {
            console.error('Failed to load synthetic data:', error);
            syntheticData = null;
        }
    });
}

/**
 * Get demo lender interest data from synthetic events
 */
function getDemoLenderData(days, minUsers) {
    if (!syntheticData || !syntheticData.events) {
        return [];
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);
    const events = syntheticData.events.filter(function(e) {
        return new Date(e.event_timestamp) >= cutoff && e.lender_id;
    });

    // Group by lender + researcher state to match API format
    const lenderStateData = {};

    events.forEach(function(e) {
        const key = e.lender_id + '_' + (e.state || 'Unknown');
        if (!lenderStateData[key]) {
            lenderStateData[key] = {
                lender_id: e.lender_id,
                lender_name: e.lender_name || e.lender_id,
                researcher_state: e.state,
                researcher_city: e.county_name ? e.county_name.split(',')[0] : null,
                users: new Set(),
                event_count: 0,
                last_activity: e.event_timestamp
            };
        }
        if (e.user_id) lenderStateData[key].users.add(e.user_id);
        lenderStateData[key].event_count++;
        if (new Date(e.event_timestamp) > new Date(lenderStateData[key].last_activity)) {
            lenderStateData[key].last_activity = e.event_timestamp;
        }
    });

    // Convert to array format expected by renderTable/renderMap
    return Object.values(lenderStateData)
        .map(function(item) {
            return {
                lender_id: item.lender_id,
                lender_name: item.lender_name,
                researcher_state: item.researcher_state,
                researcher_city: item.researcher_city,
                unique_users: item.users.size,
                event_count: item.event_count,
                last_activity: item.last_activity
            };
        })
        .filter(function(item) {
            return item.unique_users >= minUsers;
        });
}

/**
 * Load lender interest data
 */
function loadData() {
    const days = parseInt($('#time-period').val()) || 90;
    const minUsers = parseInt($('#min-users').val()) || 1;

    // Show loading state
    $('#lender-tbody').html('<tr><td colspan="6" class="loading-cell">Loading lender data...</td></tr>');

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const demoData = getDemoLenderData(days, minUsers);
        lenderData = demoData;
        renderTable(lenderData);
        renderMap(lenderData);
        return;
    }

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

    // Aggregate by state with lender details
    const stateData = {};
    data.forEach(function(item) {
        const state = item.researcher_state;
        if (!state) return;

        if (!stateData[state]) {
            stateData[state] = {
                state: state,
                count: 0,
                lenders: {},
                cities: new Set()
            };
        }

        stateData[state].count += item.unique_users || 1;

        // Track which lenders are being researched from this state
        if (item.lender_id) {
            if (!stateData[state].lenders[item.lender_id]) {
                stateData[state].lenders[item.lender_id] = {
                    name: item.lender_name || item.lender_id,
                    count: 0
                };
            }
            stateData[state].lenders[item.lender_id].count += item.event_count || 1;
        }

        // Track cities/counties
        if (item.researcher_city) {
            stateData[state].cities.add(item.researcher_city);
        }
    });

    // Add markers for each state with research activity
    Object.values(stateData).forEach(function(info) {
        const stateAbbr = info.state;
        // Convert abbreviation to full name for STATE_CENTERS lookup
        const stateName = STATE_NAMES[stateAbbr] || stateAbbr;
        const center = STATE_CENTERS[stateName];
        if (!center) return;

        const radius = Math.min(Math.max(Math.sqrt(info.count) * 3.5, 8), 35);

        // High contrast purple markers
        L.circleMarker([center.lat, center.lng], {
            radius: radius,
            fillColor: '#6a1b9a',  // Darker purple
            color: '#1a1a1a',      // Dark border for contrast
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
        })
        .bindPopup(generateLenderMapPopup(info), {
            maxWidth: 320,
            className: 'lender-map-popup'
        })
        .addTo(map);
    });
}

/**
 * Generate popup content for lender map markers
 */
function generateLenderMapPopup(info) {
    const lenderCount = Object.keys(info.lenders).length;
    const topLenders = Object.entries(info.lenders)
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 5);

    let html = '<div class="lender-popup">';
    html += '<div class="popup-title"><strong>' + escapeHtml(info.state) + '</strong></div>';
    html += '<div class="popup-stats">';
    html += '<div>' + formatNumber(info.count) + ' researchers</div>';
    html += '<div>' + formatNumber(lenderCount) + ' lenders researched</div>';
    html += '</div>';

    if (topLenders.length > 0) {
        html += '<div class="popup-lenders">';
        html += '<div class="lenders-header">Top Lenders Researched:</div>';
        topLenders.forEach(function([id, lender]) {
            html += '<div class="lender-item">' + escapeHtml(lender.name) + ' (' + formatNumber(lender.count) + ')</div>';
        });
        if (lenderCount > 5) {
            html += '<div class="lender-more">+' + (lenderCount - 5) + ' more lenders</div>';
        }
        html += '</div>';
    }

    if (info.cities.size > 0) {
        const cityList = Array.from(info.cities).slice(0, 5).join(', ');
        html += '<div class="popup-cities">';
        html += '<span class="cities-label">From:</span> ' + escapeHtml(cityList);
        if (info.cities.size > 5) {
            html += ' +' + (info.cities.size - 5) + ' more';
        }
        html += '</div>';
    }

    html += '</div>';
    return html;
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
