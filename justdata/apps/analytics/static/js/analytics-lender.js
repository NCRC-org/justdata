/**
 * Lender Interest View JavaScript
 */

let map;
let lenderData = [];
let demoMode = false;
let syntheticData = null;
let selectedState = null;
let stateDataCache = {};

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

    // Close detail panel when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#state-detail-panel, .leaflet-popup, .btn-view-researchers').length) {
            closeStateDetail();
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
 * Navigate to lender detail page
 */
function navigateToLenderDetail(lenderId) {
    window.location.href = '/analytics/lender-interest/' + encodeURIComponent(lenderId);
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

        // Create clickable lender name link
        const nameLink = $('<a>')
            .attr('href', '/analytics/lender-interest/' + encodeURIComponent(lender.lender_id))
            .css({
                'color': '#0077B6',
                'text-decoration': 'none',
                'font-weight': 'bold',
                'cursor': 'pointer'
            })
            .text(name)
            .on('mouseenter', function() {
                $(this).css('text-decoration', 'underline');
            })
            .on('mouseleave', function() {
                $(this).css('text-decoration', 'none');
            });

        const row = $('<tr>')
            .addClass('clickable-row')
            .css('cursor', 'pointer')
            .append($('<td>').append(nameLink))
            .append('<td><code>' + escapeHtml(lender.lender_id) + '</code></td>')
            .append('<td>' + formatNumber(lender.unique_users) + '</td>')
            .append('<td>' + formatNumber(lender.event_count) + '</td>')
            .append('<td>' + escapeHtml(locations) + '<span style="color: #888;">' + moreLocations + '</span></td>')
            .append('<td>' + formatDate(lender.last_activity) + '</td>');

        // Make entire row clickable (except for direct link clicks)
        row.on('click', function(e) {
            // If clicking the link itself, let it handle navigation
            if ($(e.target).is('a')) return;
            navigateToLenderDetail(lender.lender_id);
        });

        tbody.append(row);
    });
}

/**
 * Render researcher locations on map - showing county-level markers
 */
function renderMap(data) {
    // Clear existing layers
    map.eachLayer(function(layer) {
        if (layer instanceof L.CircleMarker) {
            map.removeLayer(layer);
        }
    });

    // Aggregate by county (using coordinates from API) with lender details
    const countyData = {};
    // Also aggregate by state for items without county coordinates
    const stateData = {};

    data.forEach(function(item) {
        const state = item.researcher_state;
        if (!state) return;

        // If we have county-level coordinates, use them
        if (item.latitude && item.longitude && item.researcher_city) {
            const countyKey = item.researcher_county_fips || (item.researcher_city + '_' + state);

            if (!countyData[countyKey]) {
                countyData[countyKey] = {
                    county: item.researcher_city,
                    state: state,
                    latitude: item.latitude,
                    longitude: item.longitude,
                    count: 0,
                    lenders: {},
                    users: new Set()
                };
            }

            countyData[countyKey].count += item.unique_users || 1;

            // Track which lenders are being researched from this county
            if (item.lender_id) {
                if (!countyData[countyKey].lenders[item.lender_id]) {
                    countyData[countyKey].lenders[item.lender_id] = {
                        name: item.lender_name || item.lender_id,
                        count: 0
                    };
                }
                countyData[countyKey].lenders[item.lender_id].count += item.event_count || 1;
            }
        } else {
            // Fall back to state-level aggregation for items without coordinates
            if (!stateData[state]) {
                stateData[state] = {
                    state: state,
                    count: 0,
                    lenders: {},
                    cities: new Set()
                };
            }

            stateData[state].count += item.unique_users || 1;

            if (item.lender_id) {
                if (!stateData[state].lenders[item.lender_id]) {
                    stateData[state].lenders[item.lender_id] = {
                        name: item.lender_name || item.lender_id,
                        count: 0
                    };
                }
                stateData[state].lenders[item.lender_id].count += item.event_count || 1;
            }

            if (item.researcher_city) {
                stateData[state].cities.add(item.researcher_city);
            }
        }
    });

    // Add markers for each county with research activity
    Object.values(countyData).forEach(function(info) {
        const radius = Math.min(Math.max(Math.sqrt(info.count) * 3.5, 8), 35);

        // Purple markers for county-level data
        L.circleMarker([info.latitude, info.longitude], {
            radius: radius,
            fillColor: '#6a1b9a',  // Darker purple
            color: '#1a1a1a',      // Dark border for contrast
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
        })
        .bindPopup(generateCountyMapPopup(info), {
            maxWidth: 320,
            className: 'lender-map-popup'
        })
        .addTo(map);
    });

    // Add markers for state-level fallback data (lighter color to distinguish)
    Object.values(stateData).forEach(function(info) {
        const stateAbbr = info.state;
        const stateName = STATE_NAMES[stateAbbr] || stateAbbr;
        const center = STATE_CENTERS[stateName];
        if (!center) return;

        const radius = Math.min(Math.max(Math.sqrt(info.count) * 3.5, 8), 35);

        // Lighter purple for state-level aggregates
        L.circleMarker([center.lat, center.lng], {
            radius: radius,
            fillColor: '#9c27b0',  // Lighter purple for state-level
            color: '#1a1a1a',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.7
        })
        .bindPopup(generateLenderMapPopup(info), {
            maxWidth: 320,
            className: 'lender-map-popup'
        })
        .addTo(map);
    });
}

/**
 * Generate popup content for county-level map markers
 */
function generateCountyMapPopup(info) {
    const lenderCount = Object.keys(info.lenders).length;
    const topLenders = Object.entries(info.lenders)
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 5);

    let html = '<div class="lender-popup">';
    html += '<div class="popup-title"><strong>' + escapeHtml(info.county) + ', ' + escapeHtml(info.state) + '</strong></div>';
    html += '<div class="popup-stats">';
    html += '<div>' + formatNumber(info.count) + ' researchers</div>';
    html += '<div>' + formatNumber(lenderCount) + ' lenders researched</div>';
    html += '</div>';

    if (topLenders.length > 0) {
        html += '<div class="popup-lenders">';
        html += '<div class="lenders-header">Top Lenders Researched:</div>';
        topLenders.forEach(function([id, lender]) {
            html += '<div class="lender-item">';
            html += '<a href="/analytics/lender-interest/' + encodeURIComponent(id) + '" class="lender-link" onclick="event.stopPropagation();">';
            html += escapeHtml(lender.name);
            html += '</a>';
            html += ' (' + formatNumber(lender.count) + ')';
            html += '</div>';
        });
        if (lenderCount > 5) {
            html += '<div class="lender-more">+' + (lenderCount - 5) + ' more lenders</div>';
        }
        html += '</div>';
    }

    html += '</div>';
    return html;
}

/**
 * Generate popup content for lender map markers
 */
function generateLenderMapPopup(info) {
    const lenderCount = Object.keys(info.lenders).length;
    const topLenders = Object.entries(info.lenders)
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 5);

    // Cache the state data for the detail panel
    stateDataCache[info.state] = info;

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
            // Make lender names clickable links
            html += '<div class="lender-item">';
            html += '<a href="/analytics/lender-interest/' + encodeURIComponent(id) + '" class="lender-link" onclick="event.stopPropagation();">';
            html += escapeHtml(lender.name);
            html += '</a>';
            html += ' (' + formatNumber(lender.count) + ')';
            html += '</div>';
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

    // Add View All Researchers button
    html += '<div class="popup-actions">';
    html += '<button class="btn-view-researchers" onclick="showStateResearchers(\'' + escapeHtml(info.state) + '\'); return false;">';
    html += '<i class="fas fa-users"></i> View All Researchers';
    html += '</button>';
    html += '</div>';

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

/**
 * Show state researchers detail panel
 */
function showStateResearchers(stateAbbr) {
    selectedState = stateAbbr;
    const panel = $('#state-detail-panel');
    const stateName = STATE_NAMES[stateAbbr] || stateAbbr;

    // Update panel header
    $('#state-name-display').text(stateName + ' (' + stateAbbr + ')');

    // Show loading state
    $('#state-users-list').html('<div class="loading-item">Loading researchers...</div>');

    // Show panel
    panel.fadeIn(200);

    // Load researchers for this state
    loadStateResearchers(stateAbbr);
}

/**
 * Close state detail panel
 */
function closeStateDetail() {
    $('#state-detail-panel').fadeOut(200);
    selectedState = null;
}

/**
 * Load researchers for a specific state
 */
function loadStateResearchers(stateAbbr) {
    const days = parseInt($('#time-period').val()) || 90;

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const researchers = getDemoStateResearchers(stateAbbr, days);
        renderStateResearchers(researchers, stateAbbr);
        return;
    }

    // Call API for state researchers
    $.ajax({
        url: '/analytics/api/state-researchers',
        data: {
            state: stateAbbr,
            days: days
        },
        success: function(response) {
            if (response.success) {
                renderStateResearchers(response.data, stateAbbr);
            } else {
                $('#state-users-list').html('<div class="error-item">Failed to load researchers</div>');
            }
        },
        error: function() {
            // Fallback to building from lenderData if API not available
            const researchers = buildResearchersFromLenderData(stateAbbr);
            renderStateResearchers(researchers, stateAbbr);
        }
    });
}

/**
 * Get demo researchers for a specific state
 */
function getDemoStateResearchers(stateAbbr, days) {
    if (!syntheticData || !syntheticData.events) {
        return [];
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);

    // Filter events for this state with lender research
    const events = syntheticData.events.filter(function(e) {
        return e.state === stateAbbr &&
               e.lender_id &&
               new Date(e.event_timestamp) >= cutoff;
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
                lenders: {},
                counties: new Set(),
                last_activity: e.event_timestamp
            };
        }

        // Track lenders researched
        if (e.lender_id) {
            if (!users[e.user_id].lenders[e.lender_id]) {
                users[e.user_id].lenders[e.lender_id] = {
                    name: e.lender_name || e.lender_id,
                    count: 0
                };
            }
            users[e.user_id].lenders[e.lender_id].count++;
        }

        // Track counties
        if (e.county_name) {
            users[e.user_id].counties.add(e.county_name);
        }

        if (new Date(e.event_timestamp) > new Date(users[e.user_id].last_activity)) {
            users[e.user_id].last_activity = e.event_timestamp;
        }
    });

    // Convert to array and format for display
    return Object.values(users).map(function(u) {
        const lenderList = Object.values(u.lenders)
            .sort((a, b) => b.count - a.count)
            .map(l => l.name);
        return {
            user_id: u.user_id,
            user_email: u.user_email,
            user_type: u.user_type,
            organization_name: u.organization_name,
            lenders_researched: lenderList,
            lender_count: lenderList.length,
            counties: Array.from(u.counties),
            last_activity: u.last_activity
        };
    }).sort(function(a, b) {
        return b.lender_count - a.lender_count;
    });
}

/**
 * Build researchers list from cached lender data (fallback)
 */
function buildResearchersFromLenderData(stateAbbr) {
    // Group lenderData by user for this state
    const stateRecords = lenderData.filter(function(item) {
        return item.researcher_state === stateAbbr;
    });

    // Since we may not have user-level data in lenderData, return a summary
    const info = stateDataCache[stateAbbr];
    if (!info) return [];

    // Create synthetic researcher entries based on aggregate data
    // This is a fallback when we don't have real user data
    return [{
        user_id: 'summary',
        user_email: null,
        user_type: null,
        organization_name: null,
        lenders_researched: Object.values(info.lenders).map(l => l.name),
        lender_count: Object.keys(info.lenders).length,
        counties: Array.from(info.cities),
        last_activity: null,
        is_summary: true,
        researcher_count: info.count
    }];
}

/**
 * Render researchers in the state detail panel
 */
function renderStateResearchers(researchers, stateAbbr) {
    const container = $('#state-users-list').empty();

    if (!researchers || researchers.length === 0) {
        container.html('<div class="no-data-item">No researcher details available</div>');
        return;
    }

    // Check if this is summary data (fallback mode)
    if (researchers.length === 1 && researchers[0].is_summary) {
        const summary = researchers[0];
        let html = '<div class="summary-card">';
        html += '<div class="summary-header">';
        html += '<strong>' + formatNumber(summary.researcher_count) + ' researchers</strong> in this state';
        html += '</div>';
        html += '<div class="summary-section">';
        html += '<h5>Lenders Researched (' + summary.lender_count + '):</h5>';
        html += '<ul class="lender-list">';
        summary.lenders_researched.slice(0, 10).forEach(function(lender) {
            html += '<li>' + escapeHtml(lender) + '</li>';
        });
        if (summary.lenders_researched.length > 10) {
            html += '<li class="more-items">+' + (summary.lenders_researched.length - 10) + ' more</li>';
        }
        html += '</ul>';
        html += '</div>';
        if (summary.counties.length > 0) {
            html += '<div class="summary-section">';
            html += '<h5>Counties:</h5>';
            html += '<p>' + summary.counties.slice(0, 5).map(escapeHtml).join(', ');
            if (summary.counties.length > 5) {
                html += ' +' + (summary.counties.length - 5) + ' more';
            }
            html += '</p>';
            html += '</div>';
        }
        html += '</div>';
        container.html(html);
        return;
    }

    // Render individual researcher cards
    researchers.forEach(function(user) {
        const displayName = user.user_email || (user.user_id ? user.user_id.substring(0, 12) + '...' : 'Unknown');
        const orgName = user.organization_name || '';
        const userType = user.user_type || '';
        const lenderCount = user.lender_count || 0;
        const lenders = user.lenders_researched || [];
        const counties = user.counties || [];

        const userCard = $('<div class="user-card">');

        // Header with name and type badge
        let headerHtml = '<div class="user-card-header">';
        headerHtml += '<a href="/analytics/users?user=' + encodeURIComponent(user.user_id) + '" class="user-name-link">';
        headerHtml += '<i class="fas fa-user"></i> ' + escapeHtml(displayName);
        headerHtml += '</a>';
        if (userType) {
            headerHtml += '<span class="user-type-badge ' + userType + '">' + escapeHtml(userType) + '</span>';
        }
        headerHtml += '</div>';
        userCard.append(headerHtml);

        // Organization
        if (orgName) {
            userCard.append('<div class="user-org"><i class="fas fa-building"></i> ' + escapeHtml(orgName) + '</div>');
        }

        // Lenders researched
        if (lenders.length > 0) {
            let lenderHtml = '<div class="user-lenders">';
            lenderHtml += '<i class="fas fa-university"></i> ';
            lenderHtml += lenders.slice(0, 3).map(escapeHtml).join(', ');
            if (lenders.length > 3) {
                lenderHtml += ' <span class="more-indicator">+' + (lenders.length - 3) + ' more</span>';
            }
            lenderHtml += '</div>';
            userCard.append(lenderHtml);
        }

        // Counties
        if (counties.length > 0) {
            let countyHtml = '<div class="user-counties">';
            countyHtml += '<i class="fas fa-map-marker-alt"></i> ';
            countyHtml += counties.slice(0, 3).map(escapeHtml).join(', ');
            if (counties.length > 3) {
                countyHtml += ' <span class="more-indicator">+' + (counties.length - 3) + ' more</span>';
            }
            countyHtml += '</div>';
            userCard.append(countyHtml);
        }

        // Activity info
        let activityHtml = '<div class="user-activity">';
        activityHtml += '<span><i class="fas fa-university"></i> ' + formatNumber(lenderCount) + ' lenders</span>';
        if (user.last_activity) {
            activityHtml += '<span><i class="fas fa-clock"></i> ' + formatDate(user.last_activity) + '</span>';
        }
        activityHtml += '</div>';
        userCard.append(activityHtml);

        container.append(userCard);
    });
}
