/**
 * Coalition Opportunities JavaScript
 */

let coalitionData = [];
let selectedEntity = null;
let demoMode = false;
let syntheticData = null;

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
        url: '/analytics/analytics/static/demo_data/synthetic_events.json',
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
