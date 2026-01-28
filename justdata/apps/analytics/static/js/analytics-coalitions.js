/**
 * Coalition Opportunities JavaScript
 */

let coalitionData = [];
let selectedEntity = null;
let demoMode = false;
let syntheticData = null;
let coalitionMap = null;
let mapMarkersLayer = null;
let currentView = 'table';

// US States for filter dropdown
const US_STATES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL',
    'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
    'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
    'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
    'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
];

/**
 * Initialize on page load
 */
$(document).ready(function() {
    // Check for demo mode
    demoMode = localStorage.getItem('analyticsDemo') === 'true';

    // Populate state filter
    const stateSelect = $('#state-filter');
    US_STATES.forEach(function(state) {
        stateSelect.append('<option value="' + state + '">' + state + '</option>');
    });

    // Load data (with synthetic data if demo mode)
    if (demoMode) {
        loadSyntheticData().then(function() {
            loadData();
        });
    } else {
        loadData();
    }

    // Handle filter changes
    $('#time-period, #min-users, #entity-type, #state-filter').on('change', loadData);

    // Close panel when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#entity-detail-panel, .coalition-row').length) {
            closeEntityDetail();
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
            console.log('Coalitions: Loaded synthetic data:', data.events.length, 'events');
        },
        error: function(xhr, status, error) {
            console.error('Failed to load synthetic data:', error);
            syntheticData = null;
        }
    });
}

/**
 * Get demo coalition data from synthetic events
 */
function getDemoCoalitions(days, minUsers, entityType, stateFilter) {
    if (!syntheticData || !syntheticData.events) {
        return [];
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);
    let events = syntheticData.events.filter(function(e) {
        return new Date(e.event_timestamp) >= cutoff;
    });

    // Apply state filter
    if (stateFilter) {
        events = events.filter(function(e) {
            return e.state === stateFilter;
        });
    }

    // Group by entity (county or lender)
    const entities = {};

    events.forEach(function(e) {
        // County entities
        if (e.county_fips && (!entityType || entityType === 'county')) {
            const key = 'county_' + e.county_fips;
            if (!entities[key]) {
                entities[key] = {
                    entity_type: 'county',
                    entity_id: e.county_fips,
                    entity_name: e.county_name + ', ' + e.state,
                    users: new Set(),
                    organizations: new Set(),
                    states: new Set(),
                    last_activity: e.event_timestamp
                };
            }
            if (e.user_id) entities[key].users.add(e.user_id);
            if (e.organization_name) entities[key].organizations.add(e.organization_name);
            if (e.state) entities[key].states.add(e.state);
            if (new Date(e.event_timestamp) > new Date(entities[key].last_activity)) {
                entities[key].last_activity = e.event_timestamp;
            }
        }

        // Lender entities
        if (e.lender_id && (!entityType || entityType === 'lender')) {
            const key = 'lender_' + e.lender_id;
            if (!entities[key]) {
                entities[key] = {
                    entity_type: 'lender',
                    entity_id: e.lender_id,
                    entity_name: e.lender_name || e.lender_id,
                    users: new Set(),
                    organizations: new Set(),
                    states: new Set(),
                    last_activity: e.event_timestamp
                };
            }
            if (e.user_id) entities[key].users.add(e.user_id);
            if (e.organization_name) entities[key].organizations.add(e.organization_name);
            if (e.state) entities[key].states.add(e.state);
            if (new Date(e.event_timestamp) > new Date(entities[key].last_activity)) {
                entities[key].last_activity = e.event_timestamp;
            }
        }
    });

    // Convert to array and filter by min users
    return Object.values(entities)
        .map(function(e) {
            return {
                entity_type: e.entity_type,
                entity_id: e.entity_id,
                entity_name: e.entity_name,
                unique_users: e.users.size,
                unique_organizations: e.organizations.size,
                organizations: Array.from(e.organizations),
                researcher_states: Array.from(e.states),
                last_activity: e.last_activity
            };
        })
        .filter(function(e) { return e.unique_users >= minUsers; })
        .sort(function(a, b) { return b.unique_users - a.unique_users; });
}

/**
 * Get demo users for an entity
 */
function getDemoEntityUsers(entityType, entityId, days) {
    if (!syntheticData || !syntheticData.events) {
        return [];
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);

    // Filter events for this entity
    const events = syntheticData.events.filter(function(e) {
        if (new Date(e.event_timestamp) < cutoff) return false;
        if (entityType === 'county') return e.county_fips === entityId;
        if (entityType === 'lender') return e.lender_id === entityId;
        return false;
    });

    // Group by user
    const users = {};
    events.forEach(function(e) {
        if (!e.user_id) return;
        if (!users[e.user_id]) {
            users[e.user_id] = {
                user_id: e.user_id,
                user_email: e.user_email,
                user_name: e.user_email || e.user_id.substring(0, 12) + '...',
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
 * Load coalition opportunities data
 */
function loadData() {
    const days = parseInt($('#time-period').val()) || 90;
    const minUsers = parseInt($('#min-users').val()) || 3;
    const entityType = $('#entity-type').val() || '';
    const stateFilter = $('#state-filter').val() || '';

    // Show loading state
    $('#coalition-tbody').html('<tr><td colspan="6" class="loading-cell">Loading coalition data...</td></tr>');

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const demoData = getDemoCoalitions(days, minUsers, entityType, stateFilter);
        coalitionData = demoData;
        renderTable(demoData);
        if (currentView === 'map') {
            renderMapMarkers(demoData);
        }
        return;
    }

    $.ajax({
        url: '/analytics/api/coalition-opportunities',
        data: {
            days: days,
            min_users: minUsers,
            entity_type: entityType,
            state: stateFilter
        },
        success: function(response) {
            if (response.success) {
                coalitionData = response.data;
                renderTable(coalitionData);
                if (currentView === 'map') {
                    renderMapMarkers(coalitionData);
                }
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
        const orgs = (item.organizations || []).filter(function(org) { return org && org.trim(); });
        let orgContent;
        if (orgs.length > 0) {
            const orgTags = orgs.slice(0, 3).map(function(org) {
                return '<span class="org-tag">' + escapeHtml(org) + '</span>';
            }).join('');
            const moreOrgs = orgs.length > 3
                ? '<span class="org-tag more">+' + (orgs.length - 3) + ' more</span>'
                : '';
            orgContent = '<div class="org-tags">' + orgTags + moreOrgs + '</div>';
        } else {
            orgContent = '<span class="no-data">-</span>';
        }

        // Researcher states
        const states = (item.researcher_states || []).filter(function(s) { return s && s.trim(); });
        const stateList = states.slice(0, 5).join(', ');
        const moreStates = states.length > 5
            ? ' +' + (states.length - 5) + ' more'
            : '';

        const row = $('<tr class="coalition-row clickable-row">')
            .data('entity', item)
            .attr('data-entity-type', entityType)
            .attr('data-entity-id', item.entity_id)
            .append('<td><span class="type-badge ' + entityType + '">' + (entityType === 'county' ? 'County' : 'Lender') + '</span></td>')
            .append('<td><strong>' + escapeHtml(entityName) + '</strong>' +
                    (entityType === 'county' && item.entity_id ? '<br><small class="fips-code">FIPS: ' + item.entity_id + '</small>' : '') +
                    '</td>')
            .append('<td><strong>' + formatNumber(item.unique_users) + '</strong></td>')
            .append('<td>' + orgContent + '</td>')
            .append('<td>' + escapeHtml(stateList) + '<span class="more-indicator">' + moreStates + '</span></td>')
            .append('<td>' + formatDate(item.last_activity) + '</td>')
            .on('click', function() {
                showEntityDetail(item);
            });

        tbody.append(row);
    });
}

/**
 * Show entity detail panel with users
 */
function showEntityDetail(entity) {
    selectedEntity = entity;
    const panel = $('#entity-detail-panel');
    const entityType = entity.entity_type || 'unknown';
    const entityName = entity.entity_name || entity.entity_id || 'Unknown';

    // Update panel header
    $('#entity-name-display').text(entityName);
    $('#entity-detail-subtitle').text(
        entityType === 'county'
            ? 'Users researching this county:'
            : 'Users researching this lender:'
    );

    // Show loading state
    $('#entity-users-list').html('<div class="loading-item">Loading users...</div>');

    // Show panel
    panel.fadeIn(200);

    // Highlight selected row
    $('.coalition-row').removeClass('selected');
    $('.coalition-row[data-entity-id="' + entity.entity_id + '"]').addClass('selected');

    // Load users for this entity
    loadEntityUsers(entity);
}

/**
 * Load users for a specific entity
 */
function loadEntityUsers(entity) {
    const days = parseInt($('#time-period').val()) || 90;

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const users = getDemoEntityUsers(entity.entity_type, entity.entity_id, days);
        renderEntityUsers(users, entity);
        return;
    }

    $.ajax({
        url: '/analytics/api/entity-users',
        data: {
            entity_type: entity.entity_type,
            entity_id: entity.entity_id,
            days: days
        },
        success: function(response) {
            if (response.success) {
                renderEntityUsers(response.data, entity);
            } else {
                $('#entity-users-list').html('<div class="error-item">Failed to load users</div>');
            }
        },
        error: function() {
            $('#entity-users-list').html('<div class="error-item">Failed to connect to API</div>');
        }
    });
}

/**
 * Render users in the entity detail panel
 */
function renderEntityUsers(users, entity) {
    const container = $('#entity-users-list').empty();

    if (!users || users.length === 0) {
        container.html('<div class="no-data-item">No user details available</div>');
        return;
    }

    users.forEach(function(user) {
        const userName = user.user_name || user.user_email || user.user_id || 'Unknown User';
        const orgName = user.organization_name || '';
        const userType = user.user_type || '';
        const reportCount = user.report_count || 0;

        const userCard = $('<div class="user-card">')
            .append(
                '<div class="user-card-header">' +
                '<a href="/analytics/users?user=' + encodeURIComponent(user.user_id) + '" class="user-name-link">' +
                '<i class="fas fa-user"></i> ' + escapeHtml(userName) +
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
 * Close entity detail panel
 */
function closeEntityDetail() {
    $('#entity-detail-panel').fadeOut(200);
    $('.coalition-row').removeClass('selected');
    selectedEntity = null;
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

/**
 * Set view mode (table or map)
 */
function setView(view) {
    currentView = view;

    // Update toggle buttons
    $('.view-toggle .toggle-btn').removeClass('active');
    $('.view-toggle .toggle-btn[data-view="' + view + '"]').addClass('active');

    if (view === 'table') {
        $('.table-section').show();
        $('#map-section').hide();
    } else {
        $('.table-section').hide();
        $('#map-section').show();

        // Initialize map if not already done
        if (!coalitionMap) {
            initCoalitionMap();
        }

        // Render markers with current data
        renderMapMarkers(coalitionData);
    }
}

/**
 * Initialize the coalition map using Mapbox GL JS
 */
function initCoalitionMap() {
    if (coalitionMap) return;

    // Use initMap from analytics-maps.js (Mapbox GL JS)
    coalitionMap = initMap('coalition-map', {
        center: US_CENTER,
        zoom: US_ZOOM
    });

    // Wait for map to load before adding layers
    coalitionMap.on('load', function() {
        // Re-render markers after map loads
        if (coalitionData && coalitionData.length > 0) {
            renderMapMarkers(coalitionData);
        }
    });

    // Fix map rendering after container is shown
    setTimeout(function() {
        coalitionMap.resize();
    }, 100);
}

/**
 * Clear coalition map layers
 */
function clearCoalitionLayers() {
    if (!coalitionMap) return;
    
    // Clear GeoJSON layers for both counties and lenders
    clearGeoJSONLayer(coalitionMap, 'coalition-counties');
    clearGeoJSONLayer(coalitionMap, 'coalition-lenders');
}

/**
 * Render map markers for coalition data using Mapbox GL JS GeoJSON layers
 */
function renderMapMarkers(data) {
    if (!coalitionMap) return;
    
    // Make sure map is loaded
    if (!coalitionMap.isStyleLoaded()) {
        coalitionMap.once('style.load', function() {
            renderMapMarkers(data);
        });
        return;
    }

    // Clear existing layers
    clearCoalitionLayers();

    if (!data || data.length === 0) return;

    // Separate counties and lenders
    const counties = data.filter(d => d.entity_type === 'county');
    const lenders = data.filter(d => d.entity_type === 'lender');

    // Build GeoJSON features for counties
    const countyFeatures = [];
    const lenderFeatures = [];
    const bounds = new mapboxgl.LngLatBounds();
    
    // Store data for click handlers
    const coalitionDataMap = {};

    // Process county data
    counties.forEach(function(item, index) {
        const coords = getCoalitionCoordinates(item, 'county');
        if (!coords) return;
        
        const users = item.unique_users || 1;
        const radius = Math.min(Math.max(Math.sqrt(users) * 6, 10), 35);
        const featureId = 'county_' + index;
        coalitionDataMap[featureId] = item;
        
        countyFeatures.push({
            type: 'Feature',
            id: index,
            properties: {
                featureId: featureId,
                radius: radius,
                users: users,
                name: item.entity_name || item.entity_id || 'Unknown',
                type: 'county'
            },
            geometry: {
                type: 'Point',
                coordinates: [coords.lng, coords.lat]
            }
        });
        
        bounds.extend([coords.lng, coords.lat]);
    });

    // Process lender data
    lenders.forEach(function(item, index) {
        const coords = getCoalitionCoordinates(item, 'lender');
        if (!coords) return;
        
        const users = item.unique_users || 1;
        const radius = Math.min(Math.max(Math.sqrt(users) * 6, 10), 35);
        const featureId = 'lender_' + index;
        coalitionDataMap[featureId] = item;
        
        lenderFeatures.push({
            type: 'Feature',
            id: index,
            properties: {
                featureId: featureId,
                radius: radius,
                users: users,
                name: item.entity_name || item.entity_id || 'Unknown',
                type: 'lender'
            },
            geometry: {
                type: 'Point',
                coordinates: [coords.lng, coords.lat]
            }
        });
        
        bounds.extend([coords.lng, coords.lat]);
    });

    // Add county features layer with clustering
    if (countyFeatures.length > 0) {
        addCoalitionGeoJSONLayer(coalitionMap, 'coalition-counties', countyFeatures, '#0077B6', coalitionDataMap);
    }

    // Add lender features layer with clustering
    if (lenderFeatures.length > 0) {
        addCoalitionGeoJSONLayer(coalitionMap, 'coalition-lenders', lenderFeatures, '#2a9d8f', coalitionDataMap);
    }

    // Fit bounds if we have data
    if (!bounds.isEmpty()) {
        coalitionMap.fitBounds(bounds, { padding: 50, maxZoom: 10 });
    }
}

/**
 * Add GeoJSON layer with clustering for coalition data
 */
function addCoalitionGeoJSONLayer(map, sourceId, features, color, dataMap) {
    // Add source with clustering
    map.addSource(sourceId, {
        type: 'geojson',
        data: {
            type: 'FeatureCollection',
            features: features
        },
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
        clusterProperties: {
            totalUsers: ['+', ['get', 'users']]
        }
    });

    // Cluster layer
    map.addLayer({
        id: sourceId + '-clusters',
        type: 'circle',
        source: sourceId,
        filter: ['has', 'point_count'],
        paint: {
            'circle-color': color,
            'circle-radius': [
                'step', ['get', 'point_count'],
                18, 10, 24, 50, 32, 100, 40
            ],
            'circle-stroke-width': 2,
            'circle-stroke-color': '#1a1a1a',
            'circle-opacity': 0.9
        }
    });

    // Cluster count label
    map.addLayer({
        id: sourceId + '-cluster-count',
        type: 'symbol',
        source: sourceId,
        filter: ['has', 'point_count'],
        layout: {
            'text-field': '{point_count_abbreviated}',
            'text-font': ['DIN Pro Medium', 'Arial Unicode MS Bold'],
            'text-size': 12,
            'text-allow-overlap': true
        },
        paint: {
            'text-color': '#ffffff'
        }
    });

    // Individual point stroke
    map.addLayer({
        id: sourceId + '-circles-stroke',
        type: 'circle',
        source: sourceId,
        filter: ['!', ['has', 'point_count']],
        paint: {
            'circle-radius': ['get', 'radius'],
            'circle-color': 'transparent',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#1a1a1a'
        }
    });

    // Individual point fill
    map.addLayer({
        id: sourceId + '-circles',
        type: 'circle',
        source: sourceId,
        filter: ['!', ['has', 'point_count']],
        paint: {
            'circle-radius': ['get', 'radius'],
            'circle-color': color,
            'circle-opacity': 0.85
        }
    });

    // Click on cluster to zoom
    map.on('click', sourceId + '-clusters', function(e) {
        const features = map.queryRenderedFeatures(e.point, { layers: [sourceId + '-clusters'] });
        if (!features.length) return;
        
        const clusterId = features[0].properties.cluster_id;
        map.getSource(sourceId).getClusterExpansionZoom(clusterId, function(err, zoom) {
            if (err) return;
            map.easeTo({
                center: features[0].geometry.coordinates,
                zoom: zoom
            });
        });
    });

    // Click on individual point
    map.on('click', sourceId + '-circles', function(e) {
        if (!e.features || e.features.length === 0) return;
        
        const feature = e.features[0];
        const featureId = feature.properties.featureId;
        const item = dataMap[featureId];
        
        if (!item) return;
        
        // Generate popup
        const popupContent = generateCoalitionPopup(item, item.entity_type);
        
        new mapboxgl.Popup({ maxWidth: '280px' })
            .setLngLat(e.lngLat)
            .setHTML(popupContent)
            .addTo(map);
        
        // Show detail panel
        showEntityDetail(item);
    });

    // Cursor changes
    map.on('mouseenter', sourceId + '-clusters', function() {
        map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', sourceId + '-clusters', function() {
        map.getCanvas().style.cursor = '';
    });
    map.on('mouseenter', sourceId + '-circles', function() {
        map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', sourceId + '-circles', function() {
        map.getCanvas().style.cursor = '';
    });
}

/**
 * Get coordinates for coalition entity
 */
function getCoalitionCoordinates(item, type) {
    let lat, lng;

    if (type === 'county') {
        if (item.latitude && item.longitude) {
            lat = item.latitude;
            lng = item.longitude;
        } else if (item.entity_id) {
            const stateCode = item.entity_id.substring(0, 2);
            const stateName = getStateNameFromFips(stateCode);
            if (stateName && STATE_CENTERS[stateName]) {
                const center = STATE_CENTERS[stateName];
                lat = center.lat + (Math.random() - 0.5) * 1.5;
                lng = center.lng + (Math.random() - 0.5) * 1.5;
            }
        }
    } else if (type === 'lender') {
        const states = item.researcher_states || [];
        if (states.length > 0) {
            const primaryState = states[0];
            const stateName = STATE_NAMES[primaryState] || primaryState;
            if (STATE_CENTERS[stateName]) {
                const center = STATE_CENTERS[stateName];
                lat = center.lat + (Math.random() - 0.5) * 2;
                lng = center.lng + (Math.random() - 0.5) * 2;
            }
        }
    }

    if (!lat || !lng) return null;
    return { lat: lat, lng: lng };
}

/**
 * Generate popup HTML for coalition marker
 */
function generateCoalitionPopup(item, type) {
    const entityName = item.entity_name || item.entity_id || 'Unknown';
    const users = item.unique_users || 0;
    const orgs = item.unique_organizations || 0;
    const states = (item.researcher_states || []).slice(0, 5).join(', ');
    const lastActivity = item.last_activity ? formatDate(item.last_activity) : '';

    let html = '<div class="coalition-popup">';
    html += '<span class="popup-type ' + type + '">' + (type === 'county' ? 'County' : 'Lender') + '</span>';
    html += '<div class="popup-title">' + escapeHtml(entityName) + '</div>';

    html += '<div class="popup-stats">';
    html += '<div><span class="stat-value">' + formatNumber(users) + '</span> researchers</div>';
    if (orgs > 0) {
        html += '<div><span class="stat-value">' + formatNumber(orgs) + '</span> organizations</div>';
    }
    html += '</div>';

    if (states) {
        html += '<div class="popup-orgs">';
        html += '<i class="fas fa-map-marker-alt"></i> Researcher locations: ' + escapeHtml(states);
        html += '</div>';
    }

    if (lastActivity) {
        html += '<div style="font-size: 0.8rem; color: #888; margin-top: 6px;">';
        html += '<i class="fas fa-clock"></i> Last activity: ' + lastActivity;
        html += '</div>';
    }

    html += '<div class="popup-link">';
    html += '<a href="#" onclick="showEntityDetail(' + JSON.stringify(item).replace(/"/g, '&quot;') + '); return false;">';
    html += '<i class="fas fa-users"></i> View researchers</a>';
    html += '</div>';

    html += '</div>';
    return html;
}

/**
 * Get state name from FIPS code
 */
function getStateNameFromFips(fipsCode) {
    const fipsToState = {
        '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas',
        '06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware',
        '11': 'District of Columbia', '12': 'Florida', '13': 'Georgia', '15': 'Hawaii',
        '16': 'Idaho', '17': 'Illinois', '18': 'Indiana', '19': 'Iowa',
        '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana', '23': 'Maine',
        '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
        '28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska',
        '32': 'Nevada', '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico',
        '36': 'New York', '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio',
        '40': 'Oklahoma', '41': 'Oregon', '42': 'Pennsylvania', '44': 'Rhode Island',
        '45': 'South Carolina', '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas',
        '49': 'Utah', '50': 'Vermont', '51': 'Virginia', '53': 'Washington',
        '54': 'West Virginia', '55': 'Wisconsin', '56': 'Wyoming'
    };
    return fipsToState[fipsCode] || null;
}
