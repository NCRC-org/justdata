/**
 * Research Activity Map JavaScript
 */

let map;
let markersLayer;
let countyData = [];

/**
 * Initialize on page load
 */
$(document).ready(function() {
    // Initialize map
    map = initMap('research-map');

    // Populate state filter
    populateStateFilter('state-filter');

    // Load initial data
    loadData();

    // Handle filter changes
    $('#time-period, #state-filter, #app-filter').on('change', loadData);
});

/**
 * Load research activity data
 */
function loadData() {
    const days = $('#time-period').val() || 90;
    const state = $('#state-filter').val() || '';
    const app = $('#app-filter').val() || '';

    // Show loading state
    $('#county-list').html('<div class="loading-item">Loading counties...</div>');

    $.ajax({
        url: '/analytics/api/research-activity',
        data: {
            days: days,
            state: state,
            app: app
        },
        success: function(response) {
            if (response.success) {
                countyData = response.data;
                renderMap(countyData);
                renderCountyList(countyData);
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
 * Render markers on map
 */
function renderMap(data) {
    // Clear existing markers
    if (markersLayer) {
        map.removeLayer(markersLayer);
    }

    // Add new markers
    markersLayer = addCountyMarkers(map, data);

    // Fit bounds if we have data
    if (data.length > 0 && markersLayer.getLayers().length > 0) {
        try {
            map.fitBounds(markersLayer.getBounds().pad(0.1));
        } catch (e) {
            map.setView(US_CENTER, US_ZOOM);
        }
    }
}

/**
 * Render county list sidebar
 */
function renderCountyList(data) {
    const list = $('#county-list').empty();

    // Count unique counties
    const uniqueCounties = new Set(data.map(d => d.county_fips)).size;
    $('#county-count').text(uniqueCounties + ' counties');

    if (data.length === 0) {
        list.html('<div class="loading-item">No research activity found</div>');
        return;
    }

    // Aggregate by county
    const byCounty = {};
    data.forEach(function(item) {
        const fips = item.county_fips;
        if (!byCounty[fips]) {
            byCounty[fips] = {
                county_fips: fips,
                county_name: item.county_name,
                state: item.state,
                report_count: 0,
                unique_users: 0,
                apps: new Set()
            };
        }
        byCounty[fips].report_count += item.report_count || 0;
        byCounty[fips].unique_users = Math.max(byCounty[fips].unique_users, item.unique_users || 0);
        byCounty[fips].apps.add(item.app_name);
    });

    // Sort by report count
    const sorted = Object.values(byCounty).sort((a, b) => b.report_count - a.report_count);

    sorted.slice(0, 50).forEach(function(county) {
        const name = county.county_name || county.county_fips;
        const state = county.state || '';

        const item = $('<div class="county-item">')
            .html(
                '<div class="county-name"><strong>' + escapeHtml(name) + '</strong>' +
                (state ? ', ' + state : '') + '</div>' +
                '<div class="county-stats">' +
                '<span>' + formatNumber(county.report_count) + ' reports</span> &middot; ' +
                '<span>' + formatNumber(county.unique_users) + ' users</span>' +
                '</div>'
            );

        list.append(item);
    });
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
    $('#county-list').html(
        '<div class="loading-item" style="color: #dc3545;">' +
        '<i class="fas fa-exclamation-triangle"></i> ' + escapeHtml(message) +
        '</div>'
    );
}
