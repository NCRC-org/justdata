/**
 * User Locations Map JavaScript
 */

let map;
let markersLayer;
let locationData = [];

/**
 * Initialize on page load
 */
$(document).ready(function() {
    // Initialize map
    map = initMap('user-map');

    // Populate state filter
    populateStateFilter('state-filter');

    // Load initial data
    loadData();

    // Handle filter changes
    $('#time-period, #state-filter').on('change', loadData);
});

/**
 * Load user location data
 */
function loadData() {
    const days = $('#time-period').val() || 90;
    const state = $('#state-filter').val() || '';

    // Show loading state
    $('#location-list').html('<div class="loading-item">Loading locations...</div>');

    $.ajax({
        url: '/analytics/api/user-locations',
        data: {
            days: days,
            state: state
        },
        success: function(response) {
            if (response.success) {
                locationData = response.data;
                renderMap(locationData);
                renderLocationList(locationData);
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
    markersLayer = addUserMarkers(map, data, { color: '#1a5a96' });

    // Fit bounds if we have data
    if (data.length > 0 && markersLayer.getLayers().length > 0) {
        try {
            map.fitBounds(markersLayer.getBounds().pad(0.1));
        } catch (e) {
            // Fall back to US view if bounds fail
            map.setView(US_CENTER, US_ZOOM);
        }
    }
}

/**
 * Render location list sidebar
 */
function renderLocationList(data) {
    const list = $('#location-list').empty();
    $('#location-count').text(data.length + ' locations');

    if (data.length === 0) {
        list.html('<div class="loading-item">No location data available</div>');
        return;
    }

    // Sort by user count
    const sorted = [...data].sort((a, b) => (b.unique_users || 0) - (a.unique_users || 0));

    sorted.slice(0, 50).forEach(function(location, index) {
        const city = location.city || 'Unknown';
        const state = location.state || '';
        const users = location.unique_users || 0;
        const events = location.total_events || 0;

        const item = $('<div class="location-item">')
            .attr('data-index', index)
            .html(
                '<div class="location-name"><strong>' + escapeHtml(city) + '</strong>' +
                (state ? ', ' + state : '') + '</div>' +
                '<div class="location-stats">' +
                '<span>' + formatNumber(users) + ' users</span> &middot; ' +
                '<span>' + formatNumber(events) + ' events</span>' +
                '</div>'
            )
            .on('click', function() {
                zoomToLocation(location);
            });

        list.append(item);
    });
}

/**
 * Zoom to a specific location
 */
function zoomToLocation(location) {
    if (location.latitude && location.longitude) {
        map.setView([location.latitude, location.longitude], 10);
    } else if (location.state && STATE_CENTERS[location.state]) {
        const center = STATE_CENTERS[location.state];
        map.setView([center.lat, center.lng], 7);
    }
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
    $('#location-list').html(
        '<div class="loading-item" style="color: #dc3545;">' +
        '<i class="fas fa-exclamation-triangle"></i> ' + escapeHtml(message) +
        '</div>'
    );
}
