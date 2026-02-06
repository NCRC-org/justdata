/**
 * Analytics Maps JavaScript
 * Shared map utilities for analytics views using Mapbox GL JS
 */

// Mapbox configuration - read from server-provided config
const MAPBOX_TOKEN = (window.MAPBOX_CONFIG && window.MAPBOX_CONFIG.token) || '';
const MAPBOX_STYLE = (window.MAPBOX_CONFIG && window.MAPBOX_CONFIG.style) || 'mapbox://styles/mapbox/light-v11';

// US center coordinates [lng, lat] for Mapbox
const US_CENTER = [-98.5795, 39.8283];
const US_ZOOM = 3.5;

// Enable clustering by default
const USE_CLUSTERING = true;

// Store active markers for cleanup
let activeMarkers = [];

/**
 * Validate that coordinates are within reasonable US bounds
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {object} Validation result with 'valid' boolean and optional 'reason'
 */
function validateCoordinates(lat, lng) {
    if (lat === null || lat === undefined || lng === null || lng === undefined) {
        return { valid: false, reason: 'Missing coordinates' };
    }

    lat = parseFloat(lat);
    lng = parseFloat(lng);

    if (isNaN(lat) || isNaN(lng)) {
        return { valid: false, reason: 'Invalid number format' };
    }

    if (Math.abs(lat) > 90) {
        return { valid: false, reason: 'Latitude out of range (-90 to 90)' };
    }

    if (Math.abs(lng) > 180) {
        return { valid: false, reason: 'Longitude out of range (-180 to 180)' };
    }

    if (lat === 0 && lng === 0) {
        return { valid: false, reason: 'Coordinates are (0, 0) - null island' };
    }

    const inMainland = lat >= 24.0 && lat <= 49.5 && lng >= -125.0 && lng <= -66.0;
    const inAlaska = lat >= 51.0 && lat <= 72.0 && lng >= -180.0 && lng <= -129.0;
    const inHawaii = lat >= 18.0 && lat <= 23.0 && lng >= -161.0 && lng <= -154.0;
    const inPuertoRico = lat >= 17.5 && lat <= 18.6 && lng >= -68.0 && lng <= -65.0;

    if (!inMainland && !inAlaska && !inHawaii && !inPuertoRico) {
        return { valid: false, reason: 'Coordinates outside US bounds' };
    }

    return { valid: true };
}

/**
 * Get valid coordinates from location data, with fallback to state center
 * @param {object} location - Location data with latitude, longitude, state
 * @returns {object|null} {lat, lng} or null if no valid coordinates
 */
function getValidCoordinates(location) {
    if (location.latitude && location.longitude) {
        const validation = validateCoordinates(location.latitude, location.longitude);
        if (validation.valid) {
            return { lat: parseFloat(location.latitude), lng: parseFloat(location.longitude) };
        } else {
            console.warn('Invalid coordinates for', location.county_name || location.city, location.state + ':', validation.reason);
        }
    }

    const state = location.state;
    if (state) {
        const stateCenter = STATE_CENTERS[state] || STATE_CENTERS[STATE_NAMES[state]];
        if (stateCenter) {
            return {
                lat: stateCenter.lat + (Math.random() - 0.5) * 2,
                lng: stateCenter.lng + (Math.random() - 0.5) * 2
            };
        }
    }

    return null;
}

// State abbreviation to full name mapping
const STATE_NAMES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
};

// State FIPS code to full name mapping (2-digit FIPS codes)
const STATE_FIPS_TO_NAME = {
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
    '54': 'West Virginia', '55': 'Wisconsin', '56': 'Wyoming', '72': 'Puerto Rico'
};

// State center coordinates
const STATE_CENTERS = {
    'Alabama': { lat: 32.806671, lng: -86.791130 },
    'Alaska': { lat: 61.370716, lng: -152.404419 },
    'Arizona': { lat: 33.729759, lng: -111.431221 },
    'Arkansas': { lat: 34.969704, lng: -92.373123 },
    'California': { lat: 36.116203, lng: -119.681564 },
    'Colorado': { lat: 39.059811, lng: -105.311104 },
    'Connecticut': { lat: 41.597782, lng: -72.755371 },
    'Delaware': { lat: 39.318523, lng: -75.507141 },
    'Florida': { lat: 27.766279, lng: -81.686783 },
    'Georgia': { lat: 33.040619, lng: -83.643074 },
    'Hawaii': { lat: 21.094318, lng: -157.498337 },
    'Idaho': { lat: 44.240459, lng: -114.478828 },
    'Illinois': { lat: 40.349457, lng: -88.986137 },
    'Indiana': { lat: 39.849426, lng: -86.258278 },
    'Iowa': { lat: 42.011539, lng: -93.210526 },
    'Kansas': { lat: 38.526600, lng: -96.726486 },
    'Kentucky': { lat: 37.668140, lng: -84.670067 },
    'Louisiana': { lat: 31.169546, lng: -91.867805 },
    'Maine': { lat: 44.693947, lng: -69.381927 },
    'Maryland': { lat: 39.063946, lng: -76.802101 },
    'Massachusetts': { lat: 42.230171, lng: -71.530106 },
    'Michigan': { lat: 43.326618, lng: -84.536095 },
    'Minnesota': { lat: 45.694454, lng: -93.900192 },
    'Mississippi': { lat: 32.741646, lng: -89.678696 },
    'Missouri': { lat: 38.456085, lng: -92.288368 },
    'Montana': { lat: 46.921925, lng: -110.454353 },
    'Nebraska': { lat: 41.125370, lng: -98.268082 },
    'Nevada': { lat: 38.313515, lng: -117.055374 },
    'New Hampshire': { lat: 43.452492, lng: -71.563896 },
    'New Jersey': { lat: 40.298904, lng: -74.521011 },
    'New Mexico': { lat: 34.840515, lng: -106.248482 },
    'New York': { lat: 42.165726, lng: -74.948051 },
    'North Carolina': { lat: 35.630066, lng: -79.806419 },
    'North Dakota': { lat: 47.528912, lng: -99.784012 },
    'Ohio': { lat: 40.388783, lng: -82.764915 },
    'Oklahoma': { lat: 35.565342, lng: -96.928917 },
    'Oregon': { lat: 44.572021, lng: -122.070938 },
    'Pennsylvania': { lat: 40.590752, lng: -77.209755 },
    'Rhode Island': { lat: 41.680893, lng: -71.511780 },
    'South Carolina': { lat: 33.856892, lng: -80.945007 },
    'South Dakota': { lat: 44.299782, lng: -99.438828 },
    'Tennessee': { lat: 35.747845, lng: -86.692345 },
    'Texas': { lat: 31.054487, lng: -97.563461 },
    'Utah': { lat: 40.150032, lng: -111.862434 },
    'Vermont': { lat: 44.045876, lng: -72.710686 },
    'Virginia': { lat: 37.769337, lng: -78.169968 },
    'Washington': { lat: 47.400902, lng: -121.490494 },
    'West Virginia': { lat: 38.491226, lng: -80.954453 },
    'Wisconsin': { lat: 44.268543, lng: -89.616508 },
    'Wyoming': { lat: 42.755966, lng: -107.302490 },
    'District of Columbia': { lat: 38.897438, lng: -77.026817 }
};

// Store current popup reference
let currentPopup = null;

// Store location data for click handlers
let locationDataMap = {};

/**
 * Initialize a Mapbox GL JS map
 * @param {string} elementId - DOM element ID for the map
 * @param {object} options - Optional map options
 * @returns {mapboxgl.Map} Mapbox map instance
 */
function initMap(elementId, options = {}) {
    // Set access token
    mapboxgl.accessToken = MAPBOX_TOKEN;
    
    // Create map
    const map = new mapboxgl.Map({
        container: elementId,
        style: MAPBOX_STYLE,
        center: options.center || US_CENTER,
        zoom: options.zoom || US_ZOOM
    });
    
    // Add navigation controls
    map.addControl(new mapboxgl.NavigationControl(), 'top-right');
    
    return map;
}

/**
 * Clear GeoJSON layers and sources from map
 * @param {mapboxgl.Map} map - Mapbox map instance
 * @param {string} sourceId - Source ID to remove
 */
function clearGeoJSONLayer(map, sourceId) {
    // Remove all possible layers (including cluster layers)
    const layerIds = [
        sourceId + '-circles',
        sourceId + '-circles-stroke',
        sourceId + '-clusters',
        sourceId + '-cluster-count'
    ];
    
    layerIds.forEach(layerId => {
        if (map.getLayer(layerId)) {
            map.removeLayer(layerId);
        }
    });
    
    // Then remove source
    if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
    }
    // Close any open popup
    if (currentPopup) {
        currentPopup.remove();
        currentPopup = null;
    }
    // Clear location data
    locationDataMap = {};
}

/**
 * Legacy: Clear all HTML markers from the map
 */
function clearMarkers() {
    activeMarkers.forEach(marker => marker.remove());
    activeMarkers = [];
}

/**
 * Legacy: Create a circle marker element for Mapbox (kept for backward compatibility)
 */
function createCircleMarkerElement(radius, color) {
    const el = document.createElement('div');
    el.className = 'mapbox-circle-marker';
    el.style.width = (radius * 2) + 'px';
    el.style.height = (radius * 2) + 'px';
    el.style.backgroundColor = color;
    el.style.border = '2px solid #1a1a1a';
    el.style.borderRadius = '50%';
    el.style.opacity = '0.85';
    el.style.cursor = 'pointer';
    return el;
}

/**
 * Add GeoJSON circle layer for locations with optional clustering (high performance)
 * @param {mapboxgl.Map} map - Mapbox map instance
 * @param {Array} data - Location data array
 * @param {object} options - Layer options including clustering
 * @param {function} popupGenerator - Function to generate popup HTML
 * @param {function} onClickHandler - Optional click handler for detail panel
 */
function addGeoJSONCircleLayer(map, data, options = {}, popupGenerator, onClickHandler) {
    const sourceId = options.sourceId || 'locations';
    const color = options.color || '#0d4a7c';
    const minRadius = options.minRadius || 6;
    const maxRadius = options.maxRadius || 35;
    const radiusMultiplier = options.radiusMultiplier || 4;
    const enableClustering = options.cluster !== false; // Enable clustering by default
    const clusterRadius = options.clusterRadius || 50;
    const clusterMaxZoom = options.clusterMaxZoom || 14;
    
    // Clear existing layer
    clearGeoJSONLayer(map, sourceId);
    
    // Aggregate data
    const aggregatedData = aggregateByCounty(data);
    
    // Build GeoJSON features
    const features = [];
    const bounds = new mapboxgl.LngLatBounds();
    
    aggregatedData.forEach(function(location, index) {
        const coords = getValidCoordinates(location);
        if (!coords) {
            console.warn('Skipping location with no valid coordinates:', location.county_name || location.city, location.state);
            return;
        }
        
        const events = location.total_events || 1;
        const radius = Math.min(Math.max(Math.sqrt(events) * radiusMultiplier, minRadius), maxRadius);
        
        // Store location data with unique ID
        const featureId = 'loc_' + index;
        locationDataMap[featureId] = location;
        
        features.push({
            type: 'Feature',
            id: index,
            properties: {
                featureId: featureId,
                radius: radius,
                events: events,
                name: location.county_name || location.city || 'Unknown',
                state: location.state || ''
            },
            geometry: {
                type: 'Point',
                coordinates: [coords.lng, coords.lat]
            }
        });
        
        bounds.extend([coords.lng, coords.lat]);
    });
    
    if (features.length === 0) {
        console.warn('No valid features to display');
        return;
    }
    
    // Add GeoJSON source with optional clustering
    const sourceConfig = {
        type: 'geojson',
        data: {
            type: 'FeatureCollection',
            features: features
        }
    };
    
    if (enableClustering) {
        sourceConfig.cluster = true;
        sourceConfig.clusterMaxZoom = clusterMaxZoom;
        sourceConfig.clusterRadius = clusterRadius;
        sourceConfig.clusterProperties = {
            totalEvents: ['+', ['get', 'events']]
        };
    }
    
    map.addSource(sourceId, sourceConfig);
    
    if (enableClustering) {
        // Cluster circle layer
        map.addLayer({
            id: sourceId + '-clusters',
            type: 'circle',
            source: sourceId,
            filter: ['has', 'point_count'],
            paint: {
                'circle-color': [
                    'step', ['get', 'point_count'],
                    color,      // Default color
                    10, darkenColor(color, 10),   // 10+ points
                    50, darkenColor(color, 20),   // 50+ points
                    100, darkenColor(color, 30)   // 100+ points
                ],
                'circle-radius': [
                    'step', ['get', 'point_count'],
                    18,    // Default radius
                    10, 24,
                    50, 32,
                    100, 40
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
        
        // Unclustered points stroke
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
        
        // Unclustered points fill
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
        
        // Click on cluster to zoom in
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
        
        // Cursor for clusters
        map.on('mouseenter', sourceId + '-clusters', function() {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', sourceId + '-clusters', function() {
            map.getCanvas().style.cursor = '';
        });
    } else {
        // Non-clustered: just add circle layers
        map.addLayer({
            id: sourceId + '-circles-stroke',
            type: 'circle',
            source: sourceId,
            paint: {
                'circle-radius': ['get', 'radius'],
                'circle-color': 'transparent',
                'circle-stroke-width': 2,
                'circle-stroke-color': '#1a1a1a'
            }
        });
        
        map.addLayer({
            id: sourceId + '-circles',
            type: 'circle',
            source: sourceId,
            paint: {
                'circle-radius': ['get', 'radius'],
                'circle-color': color,
                'circle-opacity': 0.85
            }
        });
    }
    
    // Change cursor on hover for individual points
    map.on('mouseenter', sourceId + '-circles', function() {
        map.getCanvas().style.cursor = 'pointer';
    });
    
    map.on('mouseleave', sourceId + '-circles', function() {
        map.getCanvas().style.cursor = '';
    });
    
    // Handle clicks on individual points
    map.on('click', sourceId + '-circles', function(e) {
        if (!e.features || e.features.length === 0) return;
        
        const feature = e.features[0];
        const featureId = feature.properties.featureId;
        const location = locationDataMap[featureId];
        
        if (!location) return;
        
        // Close existing popup
        if (currentPopup) {
            currentPopup.remove();
        }
        
        // Create popup
        const popupHTML = popupGenerator ? popupGenerator(location) : generateAggregatedPopup(location);
        
        currentPopup = new mapboxgl.Popup({
            maxWidth: '320px',
            className: 'aggregated-popup-container'
        })
            .setLngLat(e.lngLat)
            .setHTML(popupHTML)
            .addTo(map);
        
        // Call optional click handler (for detail panel)
        if (onClickHandler) {
            onClickHandler(location);
        }
    });
    
    // Fit bounds
    if (!bounds.isEmpty()) {
        map.fitBounds(bounds, { padding: 50, maxZoom: 10 });
    }
    
    return features.length;
}

/**
 * Darken a hex color by a percentage
 */
function darkenColor(hex, percent) {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.max(0, (num >> 16) - amt);
    const G = Math.max(0, ((num >> 8) & 0x00FF) - amt);
    const B = Math.max(0, (num & 0x0000FF) - amt);
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
}

/**
 * Add circle markers for user locations (GeoJSON version - high performance)
 * @param {mapboxgl.Map} map - Mapbox map instance
 * @param {Array} data - Location data array
 * @param {object} options - Marker options
 * @param {function} popupGenerator - Optional custom popup generator
 * @param {function} onClickHandler - Optional click handler
 */
function addUserMarkers(map, data, options = {}, popupGenerator, onClickHandler) {
    return addGeoJSONCircleLayer(map, data, {
        sourceId: 'user-locations',
        color: options.color || '#0d4a7c',
        ...options
    }, popupGenerator, onClickHandler);
}

/**
 * Add circle markers for county research activity (GeoJSON version)
 * @param {mapboxgl.Map} map - Mapbox map instance
 * @param {Array} data - County research data
 * @param {function} popupGenerator - Optional custom popup generator
 * @param {function} onClickHandler - Optional click handler
 */
function addCountyMarkers(map, data, popupGenerator, onClickHandler) {
    return addGeoJSONCircleLayer(map, data, {
        sourceId: 'county-locations',
        color: '#0570b0',
        radiusMultiplier: 3.5,
        minRadius: 7,
        maxRadius: 30
    }, popupGenerator, onClickHandler);
}

/**
 * Populate state filter dropdown
 * @param {string} selectId - Select element ID
 */
function populateStateFilter(selectId) {
    const select = $('#' + selectId);
    const sortedStates = Object.entries(STATE_NAMES)
        .sort((a, b) => a[1].localeCompare(b[1]));

    sortedStates.forEach(function([abbr, name]) {
        select.append($('<option>').val(name).text(name));
    });
}

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
 * Aggregate data by county FIPS code
 */
function aggregateByCounty(data) {
    const countyMap = {};

    data.forEach(function(item) {
        const key = item.county_fips || item.city + '_' + item.state;
        if (!key) return;

        if (!countyMap[key]) {
            countyMap[key] = {
                county_fips: item.county_fips,
                county_name: item.county_name || item.city,
                state: item.state,
                latitude: item.latitude,
                longitude: item.longitude,
                unique_users: 0,
                total_events: 0,
                apps: {},
                last_activity: null,
                organization_name: item.organization_name,
                hubspot_contact_id: item.hubspot_contact_id,
                hubspot_company_id: item.hubspot_company_id
            };
        }

        const agg = countyMap[key];
        agg.unique_users += (item.unique_users || 1);
        agg.total_events += (item.total_events || item.report_count || 1);

        const appName = item.app_name || item.event_name || 'Report';
        agg.apps[appName] = (agg.apps[appName] || 0) + (item.report_count || item.total_events || 1);

        if (item.last_activity) {
            if (!agg.last_activity || new Date(item.last_activity) > new Date(agg.last_activity)) {
                agg.last_activity = item.last_activity;
            }
        }
    });

    return Object.values(countyMap);
}

/**
 * Format county name with state
 */
function formatCountyName(countyName, state) {
    if (!countyName) return getFullStateName(state) || 'Unknown';

    // Convert state to full name (handles abbreviations, FIPS codes, and full names)
    const fullStateName = getFullStateName(state);

    // Check if county name already ends with a valid state name
    const statePattern = new RegExp(',\\s*(' + fullStateName + '|' + state + ')$', 'i');
    if (state && statePattern.test(countyName)) {
        // Replace abbreviation/FIPS with full name if needed
        if (fullStateName && countyName.match(/, [A-Z]{2}$|, \d{2}$/)) {
            return countyName.replace(/, [A-Z]{2}$|, \d{2}$/, ', ' + fullStateName);
        }
        return countyName;
    }

    // If county name ends with 2-letter abbrev, convert to full name
    if (countyName.match(/, [A-Z]{2}$/)) {
        const abbrev = countyName.slice(-2);
        const stateName = STATE_NAMES[abbrev];
        if (stateName) {
            return countyName.slice(0, -2) + stateName;
        }
    }

    // If county name ends with 2-digit FIPS, convert to full name
    if (countyName.match(/, \d{2}$/)) {
        const fips = countyName.slice(-2);
        const stateName = STATE_FIPS_TO_NAME[fips];
        if (stateName) {
            return countyName.slice(0, -2) + stateName;
        }
    }

    return fullStateName ? countyName + ', ' + fullStateName : countyName;
}

/**
 * Convert state identifier to full state name
 * Handles: 2-letter abbreviation (CA), FIPS code (06), or full name (California)
 */
function getFullStateName(state) {
    if (!state) return null;

    // Already a full state name (check if it's a known state)
    if (Object.values(STATE_NAMES).includes(state) || Object.values(STATE_FIPS_TO_NAME).includes(state)) {
        return state;
    }

    // Check if it's a 2-letter abbreviation
    if (STATE_NAMES[state]) {
        return STATE_NAMES[state];
    }

    // Check if it's a 2-digit FIPS code
    if (STATE_FIPS_TO_NAME[state]) {
        return STATE_FIPS_TO_NAME[state];
    }

    // Check if it's a FIPS code without leading zero (e.g., "6" for California)
    const paddedFips = state.toString().padStart(2, '0');
    if (STATE_FIPS_TO_NAME[paddedFips]) {
        return STATE_FIPS_TO_NAME[paddedFips];
    }

    // Return original if no match (might be a partial state name or typo)
    return state;
}

/**
 * Generate popup content for aggregated county data
 */
function generateAggregatedPopup(location) {
    const name = formatCountyName(location.county_name || location.city, location.state);
    const totalEvents = location.total_events || 0;
    const uniqueUsers = location.unique_users || 0;
    const apps = location.apps || {};
    const lastActivity = location.last_activity ? formatDate(location.last_activity) : '';

    let html = '<div class="aggregated-popup">';
    html += '<div class="popup-title"><strong>' + escapeHtml(name) + '</strong></div>';
    html += '<div class="popup-stats">';
    html += '<div>' + formatNumber(totalEvents) + ' total reports</div>';
    html += '<div>' + formatNumber(uniqueUsers) + ' unique researchers</div>';
    html += '</div>';

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

    if (lastActivity) {
        html += '<div class="popup-activity">Last activity: ' + lastActivity + '</div>';
    }

    html += '<div class="popup-note"><em>Researcher details coming soon</em></div>';
    html += '</div>';

    return html;
}

/**
 * Generate user profile popup HTML
 */
function generateUserProfilePopup(user) {
    const name = user.display_name || user.name || user.email || 'Unknown User';
    const email = user.email || '';
    const organization = user.organization || user.company_name || '';
    const userType = user.user_type || '';
    const city = user.city || '';
    const state = user.state || '';
    const location = city && state ? city + ', ' + state : (city || state || '');
    const eventCount = user.total_events || user.event_count || 0;
    const lastActivity = user.last_activity ? formatDate(user.last_activity) : '';
    const hubspotLinked = user.hubspot_contact_id ? true : false;

    let html = '<div class="user-profile-popup">';
    html += '<div class="popup-header">';
    html += '<div class="popup-avatar"><i class="fas fa-user"></i></div>';
    html += '<div class="popup-name">';
    html += '<strong>' + escapeHtml(name) + '</strong>';
    if (userType) {
        html += '<span class="popup-badge">' + escapeHtml(userType) + '</span>';
    }
    html += '</div></div>';

    html += '<div class="popup-details">';
    if (email) html += '<div class="popup-row"><i class="fas fa-envelope"></i> ' + escapeHtml(email) + '</div>';
    if (organization) html += '<div class="popup-row"><i class="fas fa-building"></i> ' + escapeHtml(organization) + '</div>';
    if (location) html += '<div class="popup-row"><i class="fas fa-map-marker-alt"></i> ' + escapeHtml(location) + '</div>';
    if (eventCount > 0) html += '<div class="popup-row"><i class="fas fa-chart-bar"></i> ' + formatNumber(eventCount) + ' events</div>';
    if (lastActivity) html += '<div class="popup-row"><i class="fas fa-clock"></i> Last active: ' + lastActivity + '</div>';
    html += '</div>';

    html += '<div class="popup-hubspot">';
    html += '<div class="popup-hubspot-header"><i class="fab fa-hubspot"></i> HubSpot Integration</div>';
    if (hubspotLinked) {
        html += '<div class="popup-hubspot-linked"><i class="fas fa-check-circle"></i> Linked';
        if (user.hubspot_company_name) html += '<br><small>' + escapeHtml(user.hubspot_company_name) + '</small>';
        html += '</div>';
    } else {
        html += '<div class="popup-hubspot-pending"><i class="fas fa-link"></i> Link coming soon<br><small style="color: #888;">Organization data will appear here</small></div>';
    }
    html += '</div></div>';

    return html;
}
