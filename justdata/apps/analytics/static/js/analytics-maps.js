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
 * Clear all markers from the map
 */
function clearMarkers() {
    activeMarkers.forEach(marker => marker.remove());
    activeMarkers = [];
}

/**
 * Create a circle marker element for Mapbox
 * @param {number} radius - Marker radius in pixels
 * @param {string} color - Fill color
 * @returns {HTMLElement} Marker element
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
 * Add circle markers for user locations
 * @param {mapboxgl.Map} map - Mapbox map instance
 * @param {Array} data - Location data array
 * @param {object} options - Marker options
 * @returns {Array} Array of markers
 */
function addUserMarkers(map, data, options = {}) {
    clearMarkers();
    
    const aggregatedData = aggregateByCounty(data);

    aggregatedData.forEach(function(location) {
        const coords = getValidCoordinates(location);
        if (!coords) {
            console.warn('Skipping location with no valid coordinates:', location.county_name || location.city, location.state);
            return;
        }

        const events = location.total_events || 1;
        const radius = Math.min(Math.max(Math.sqrt(events) * 4, 6), 35);
        const color = options.color || '#0d4a7c';

        const el = createCircleMarkerElement(radius, color);
        
        const popup = new mapboxgl.Popup({
            offset: 25,
            maxWidth: '320px',
            className: 'aggregated-popup-container'
        }).setHTML(generateAggregatedPopup(location));

        const marker = new mapboxgl.Marker(el)
            .setLngLat([coords.lng, coords.lat])
            .setPopup(popup)
            .addTo(map);
        
        // Store location data on marker for click handlers
        marker._locationData = location;
        
        activeMarkers.push(marker);
    });

    return activeMarkers;
}

/**
 * Add circle markers for county research activity
 * @param {mapboxgl.Map} map - Mapbox map instance
 * @param {Array} data - County research data
 * @returns {Array} Array of markers
 */
function addCountyMarkers(map, data) {
    clearMarkers();
    
    const aggregatedData = aggregateByCounty(data);

    function getColor(count) {
        return count > 50 ? '#023858' :
               count > 20 ? '#045a8d' :
               count > 10 ? '#0570b0' :
               count > 5  ? '#3690c0' :
               count > 1  ? '#74a9cf' :
                           '#a6bddb';
    }

    aggregatedData.forEach(function(county) {
        const coords = getValidCoordinates(county);
        if (!coords) {
            console.warn('Skipping county with no valid coordinates:', county.county_name, county.state);
            return;
        }

        const count = county.total_events || county.report_count || 0;
        const radius = Math.min(Math.max(Math.sqrt(count) * 3.5, 7), 30);

        const el = createCircleMarkerElement(radius, getColor(count));
        
        const popup = new mapboxgl.Popup({
            offset: 25,
            maxWidth: '320px',
            className: 'aggregated-popup-container'
        }).setHTML(generateAggregatedPopup(county));

        const marker = new mapboxgl.Marker(el)
            .setLngLat([coords.lng, coords.lat])
            .setPopup(popup)
            .addTo(map);
        
        marker._locationData = county;
        
        activeMarkers.push(marker);
    });

    return activeMarkers;
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
    if (!countyName) return state || 'Unknown';

    const statePattern = new RegExp(',\\s*' + state + '$', 'i');
    if (state && statePattern.test(countyName)) {
        return countyName;
    }

    if (countyName.includes(', ') && countyName.match(/, [A-Z]{2}$/)) {
        return countyName;
    }

    return state ? countyName + ', ' + state : countyName;
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
