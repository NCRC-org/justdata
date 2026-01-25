/**
 * User Locations Map JavaScript
 */

let map;
let markersLayer;
let locationData = [];
let selectedLocation = null;
let demoMode = false;
let syntheticData = null;

/**
 * Initialize on page load
 */
$(document).ready(function() {
    // Check for demo mode
    demoMode = localStorage.getItem('analyticsDemo') === 'true';

    // Initialize map
    map = initMap('user-map');

    // Populate state filter
    populateStateFilter('state-filter');

    // Load data (with synthetic data if demo mode)
    if (demoMode) {
        loadSyntheticData().then(function() {
            loadData();
        });
    } else {
        loadData();
    }

    // Handle filter changes
    $('#time-period, #state-filter').on('change', loadData);

    // Close detail panel when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#location-detail-panel, .location-item, .leaflet-popup').length) {
            closeLocationDetail();
        }
    });
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
            console.log('User Map: Loaded synthetic data:', data.events.length, 'events');
        },
        error: function(xhr, status, error) {
            console.error('Failed to load synthetic data:', error);
            syntheticData = null;
        }
    });
}

/**
 * Get demo location data from synthetic events
 */
function getDemoLocationData(days, stateFilter) {
    if (!syntheticData || !syntheticData.events) {
        return [];
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);
    let events = syntheticData.events.filter(function(e) {
        return new Date(e.event_timestamp) >= cutoff && e.county_fips;
    });

    // Apply state filter
    if (stateFilter) {
        events = events.filter(function(e) {
            return e.state === stateFilter || STATE_NAMES[e.state] === stateFilter;
        });
    }

    // Group by county
    const counties = {};
    events.forEach(function(e) {
        const key = e.county_fips;
        if (!counties[key]) {
            counties[key] = {
                county_fips: e.county_fips,
                county_name: e.county_name,
                state: e.state,
                // Use coordinates from synthetic data if available, otherwise fall back to state center approximation
                latitude: e.latitude || getCountyLat(e.county_fips, e.state),
                longitude: e.longitude || getCountyLng(e.county_fips, e.state),
                users: new Set(),
                total_events: 0,
                apps: {},
                last_activity: e.event_timestamp
            };
        }
        if (e.user_id) counties[key].users.add(e.user_id);
        counties[key].total_events++;

        // Track app breakdown
        const appName = e.event_name || 'Report';
        counties[key].apps[appName] = (counties[key].apps[appName] || 0) + 1;

        if (new Date(e.event_timestamp) > new Date(counties[key].last_activity)) {
            counties[key].last_activity = e.event_timestamp;
        }
    });

    return Object.values(counties).map(function(c) {
        return {
            county_fips: c.county_fips,
            county_name: c.county_name,
            city: c.county_name,
            state: c.state,
            latitude: c.latitude,
            longitude: c.longitude,
            unique_users: c.users.size,
            total_events: c.total_events,
            apps: c.apps,
            last_activity: c.last_activity
        };
    });
}

/**
 * Get approximate latitude for a county (using state center with offset based on FIPS)
 */
function getCountyLat(countyFips, state) {
    const stateCenter = STATE_CENTERS[state] || STATE_CENTERS[STATE_NAMES[state]];
    if (!stateCenter) return 39.8;
    // Use FIPS code to create consistent offset
    const offset = (parseInt(countyFips.slice(-3)) % 100 - 50) / 50;
    return stateCenter.lat + offset;
}

/**
 * Get approximate longitude for a county
 */
function getCountyLng(countyFips, state) {
    const stateCenter = STATE_CENTERS[state] || STATE_CENTERS[STATE_NAMES[state]];
    if (!stateCenter) return -98.5;
    const offset = (parseInt(countyFips.slice(-3)) % 100 - 50) / 30;
    return stateCenter.lng + offset;
}

/**
 * Get demo researchers for a specific location
 */
function getDemoLocationResearchers(countyFips, days) {
    if (!syntheticData || !syntheticData.events) {
        return [];
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);

    // Filter events for this county
    const events = syntheticData.events.filter(function(e) {
        return e.county_fips === countyFips && new Date(e.event_timestamp) >= cutoff;
    });

    // Group by user
    const users = {};
    events.forEach(function(e) {
        if (!e.user_id) return;
        if (!users[e.user_id]) {
            users[e.user_id] = {
                user_id: e.user_id,
                user_email: e.user_email,
                user_type: e.user_type,
                organization_name: e.organization_name,
                report_count: 0,
                last_activity: e.event_timestamp
            };
        }
        users[e.user_id].report_count++;
        if (new Date(e.event_timestamp) > new Date(users[e.user_id].last_activity)) {
            users[e.user_id].last_activity = e.event_timestamp;
        }
    });

    return Object.values(users).sort(function(a, b) {
        return b.report_count - a.report_count;
    });
}

/**
 * Load user location data
 */
function loadData() {
    const days = parseInt($('#time-period').val()) || 90;
    const state = $('#state-filter').val() || '';

    // Show loading state
    $('#location-list').html('<div class="loading-item">Loading locations...</div>');

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const demoData = getDemoLocationData(days, state);
        locationData = demoData;
        renderMap(locationData);
        renderLocationList(locationData);
        return;
    }

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
 * Render markers on map with click handlers and clustering
 */
function renderMap(data) {
    // Clear existing markers
    if (markersLayer) {
        map.removeLayer(markersLayer);
    }

    // Aggregate data by county
    const aggregatedData = aggregateByCounty(data);

    // Check if clustering is enabled and available
    const useClustering = typeof USE_CLUSTERING !== 'undefined' && USE_CLUSTERING && typeof L.markerClusterGroup !== 'undefined';

    // Create markers layer (clustered or regular)
    if (useClustering) {
        markersLayer = L.markerClusterGroup({
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            disableClusteringAtZoom: 10,
            iconCreateFunction: function(cluster) {
                var count = cluster.getChildCount();
                var size = 'small';
                if (count >= 50) {
                    size = 'large';
                } else if (count >= 10) {
                    size = 'medium';
                }

                return L.divIcon({
                    html: '<div><span>' + count + '</span></div>',
                    className: 'marker-cluster marker-cluster-' + size,
                    iconSize: L.point(40, 40)
                });
            }
        });
    } else {
        markersLayer = L.layerGroup();
    }

    aggregatedData.forEach(function(location) {
        // Get validated coordinates with fallback to state center
        const coords = getValidCoordinates(location);
        if (!coords) {
            console.warn('Skipping location with no valid coordinates:', location.county_name || location.city, location.state);
            return;
        }

        // Calculate marker size - use smaller base for clustering
        const events = location.total_events || 1;
        const baseRadius = useClustering ? 3 : 4;
        const maxRadius = useClustering ? 20 : 35;
        const radius = Math.min(Math.max(Math.sqrt(events) * baseRadius, 5), maxRadius);

        // Create marker
        const marker = L.circleMarker([coords.lat, coords.lng], {
            radius: radius,
            fillColor: '#0d4a7c',
            color: '#1a1a1a',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
        });

        // Store location data on marker
        marker.locationData = location;

        // Add click handler to show detail panel
        marker.on('click', function() {
            showLocationDetail(location);
        });

        // Add popup with summary and "View Researchers" button
        const popupContent = generateClickablePopup(location);
        marker.bindPopup(popupContent, {
            maxWidth: 320,
            className: 'aggregated-popup-container'
        });

        markersLayer.addLayer(marker);
    });

    markersLayer.addTo(map);

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
 * Generate popup with View Researchers button
 */
function generateClickablePopup(location) {
    const name = formatCountyName(location.county_name || location.city, location.state);
    const totalEvents = location.total_events || 0;
    const uniqueUsers = location.unique_users || 0;
    const apps = location.apps || {};
    const countyFips = location.county_fips || '';

    let html = '<div class="aggregated-popup">';
    html += '<div class="popup-title"><strong>' + escapeHtml(name) + '</strong></div>';
    html += '<div class="popup-stats">';
    html += '<div>' + formatNumber(totalEvents) + ' total reports</div>';
    html += '<div>' + formatNumber(uniqueUsers) + ' unique researchers</div>';
    html += '</div>';

    // App breakdown
    if (Object.keys(apps).length > 0) {
        html += '<div class="popup-breakdown">';
        html += '<div class="breakdown-header">Report Breakdown:</div>';
        const appNames = {
            'lendsight_report': 'LendSight',
            'bizsight_report': 'BizSight',
            'branchsight_report': 'BranchSight',
            'dataexplorer_area_report': 'DataExplorer (Area)',
            'dataexplorer_lender_report': 'DataExplorer (Lender)'
        };
        for (const [app, count] of Object.entries(apps)) {
            const displayName = appNames[app] || app;
            html += '<div class="breakdown-item">' + escapeHtml(displayName) + ': ' + formatNumber(count) + '</div>';
        }
        html += '</div>';
    }

    // View Researchers button
    html += '<div class="popup-actions">';
    html += '<button class="btn-view-researchers" onclick="showLocationDetail(' + JSON.stringify(location).replace(/"/g, '&quot;') + '); return false;">';
    html += '<i class="fas fa-users"></i> View Researchers';
    html += '</button>';
    html += '</div>';

    html += '</div>';
    return html;
}

/**
 * Show location detail panel with researchers
 */
function showLocationDetail(location) {
    selectedLocation = location;
    const panel = $('#location-detail-panel');
    const name = formatCountyName(location.county_name || location.city, location.state);

    // Update panel header
    $('#location-name-display').text(name);

    // Show loading state
    $('#location-users-list').html('<div class="loading-item">Loading researchers...</div>');

    // Show panel
    panel.fadeIn(200);

    // Load researchers for this location
    loadLocationResearchers(location);
}

/**
 * Load researchers for a specific location
 */
function loadLocationResearchers(location) {
    const days = parseInt($('#time-period').val()) || 90;
    const countyFips = location.county_fips;

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const researchers = getDemoLocationResearchers(countyFips, days);
        renderLocationResearchers(researchers, location);
        return;
    }

    // Use entity-users API for county
    $.ajax({
        url: '/analytics/api/entity-users',
        data: {
            entity_type: 'county',
            entity_id: countyFips,
            days: days
        },
        success: function(response) {
            if (response.success) {
                renderLocationResearchers(response.data, location);
            } else {
                $('#location-users-list').html('<div class="error-item">Failed to load researchers</div>');
            }
        },
        error: function() {
            $('#location-users-list').html('<div class="error-item">Failed to connect to API</div>');
        }
    });
}

/**
 * Render researchers in the location detail panel
 */
function renderLocationResearchers(researchers, location) {
    const container = $('#location-users-list').empty();

    if (!researchers || researchers.length === 0) {
        container.html('<div class="no-data-item">No researcher details available</div>');
        return;
    }

    researchers.forEach(function(user) {
        const userName = user.user_name || user.user_email || user.user_id || 'Unknown User';
        const displayName = user.user_email || (user.user_id ? user.user_id.substring(0, 12) + '...' : 'Unknown');
        const orgName = user.organization_name || '';
        const userType = user.user_type || '';
        const reportCount = user.report_count || 0;

        const userCard = $('<div class="user-card">')
            .append(
                '<div class="user-card-header">' +
                '<a href="/analytics/users?user=' + encodeURIComponent(user.user_id) + '" class="user-name-link">' +
                '<i class="fas fa-user"></i> ' + escapeHtml(displayName) +
                '</a>' +
                (userType ? '<span class="user-type-badge ' + userType + '">' + escapeHtml(userType) + '</span>' : '') +
                '</div>'
            )
            .append(
                orgName
                    ? '<div class="user-org"><i class="fas fa-building"></i> ' + escapeHtml(orgName) + '</div>'
                    : ''
            )
            .append(
                '<div class="user-activity">' +
                '<span><i class="fas fa-file-alt"></i> ' + formatNumber(reportCount) + ' reports</span>' +
                (user.last_activity ? '<span><i class="fas fa-clock"></i> ' + formatDate(user.last_activity) + '</span>' : '') +
                '</div>'
            );

        container.append(userCard);
    });
}

/**
 * Close location detail panel
 */
function closeLocationDetail() {
    $('#location-detail-panel').fadeOut(200);
    selectedLocation = null;
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

    // Sort by event count (most active first)
    const sorted = [...data].sort((a, b) => (b.total_events || 0) - (a.total_events || 0));

    sorted.slice(0, 50).forEach(function(location, index) {
        const name = formatCountyName(location.county_name || location.city, location.state);
        const users = location.unique_users || 0;
        const events = location.total_events || 0;

        const item = $('<div class="location-item clickable-row">')
            .attr('data-index', index)
            .attr('data-county-fips', location.county_fips)
            .html(
                '<div class="location-name"><strong>' + escapeHtml(name) + '</strong></div>' +
                '<div class="location-stats">' +
                '<span>' + formatNumber(users) + ' researchers</span> &middot; ' +
                '<span>' + formatNumber(events) + ' reports</span>' +
                '</div>'
            )
            .on('click', function() {
                showLocationDetail(location);
                zoomToLocation(location);
            });

        list.append(item);
    });
}

/**
 * Zoom to a specific location
 */
function zoomToLocation(location) {
    const coords = getValidCoordinates(location);
    if (coords) {
        // If we have actual coordinates (not state center fallback), zoom in closer
        const hasActualCoords = location.latitude && location.longitude &&
                                validateCoordinates(location.latitude, location.longitude).valid;
        const zoomLevel = hasActualCoords ? 10 : 7;
        map.setView([coords.lat, coords.lng], zoomLevel);
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
