/**
 * Users Tab JavaScript
 * Individual user lookup and activity display
 */

let usersData = [];
let selectedUserId = null;
let searchTimeout = null;
let demoMode = false;
let syntheticData = null;

/**
 * Initialize on page load
 */
$(document).ready(function() {
    // Check for demo mode
    demoMode = localStorage.getItem('analyticsDemo') === 'true';

    // Check for user query parameter (deep link from Coalitions tab)
    const urlParams = new URLSearchParams(window.location.search);
    const linkedUserId = urlParams.get('user');

    // Load data (with synthetic data if demo mode)
    if (demoMode) {
        loadSyntheticData().then(function() {
            loadUsers().then(function() {
                if (linkedUserId) {
                    selectUser(linkedUserId);
                }
            });
        });
    } else {
        loadUsers().then(function() {
            if (linkedUserId) {
                selectUser(linkedUserId);
            }
        });
    }

    // Handle filter changes
    $('#time-period').on('change', loadUsers);

    // Handle search with debounce
    $('#search-input').on('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(loadUsers, 300);
    });

    // Handle row clicks
    $(document).on('click', '.users-table tbody tr', function() {
        const userId = $(this).data('user-id');
        if (userId) {
            selectUser(userId);
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
            console.log('Users: Loaded synthetic data:', data.events.length, 'events');
        },
        error: function(xhr, status, error) {
            console.error('Failed to load synthetic data:', error);
            syntheticData = null;
        }
    });
}

/**
 * Get demo users from synthetic data
 */
function getDemoUsers(days, search) {
    if (!syntheticData || !syntheticData.events) {
        return [];
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);
    const events = syntheticData.events.filter(function(e) {
        return new Date(e.event_timestamp) >= cutoff;
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
                total_reports: 0,
                counties: new Set(),
                lenders: new Set(),
                last_activity: e.event_timestamp,
                first_activity: e.event_timestamp
            };
        }
        users[e.user_id].total_reports++;
        if (e.county_fips) users[e.user_id].counties.add(e.county_fips);
        if (e.lender_id) users[e.user_id].lenders.add(e.lender_id);
        if (new Date(e.event_timestamp) > new Date(users[e.user_id].last_activity)) {
            users[e.user_id].last_activity = e.event_timestamp;
        }
        if (new Date(e.event_timestamp) < new Date(users[e.user_id].first_activity)) {
            users[e.user_id].first_activity = e.event_timestamp;
        }
    });

    // Convert to array and apply search filter
    let result = Object.values(users).map(function(u) {
        return {
            user_id: u.user_id,
            user_email: u.user_email,
            user_type: u.user_type,
            organization_name: u.organization_name,
            total_reports: u.total_reports,
            counties_researched: u.counties.size,
            lenders_researched: u.lenders.size,
            last_activity: u.last_activity,
            first_activity: u.first_activity
        };
    });

    // Apply search filter
    if (search) {
        const searchLower = search.toLowerCase();
        result = result.filter(function(u) {
            return (u.user_id && u.user_id.toLowerCase().includes(searchLower)) ||
                   (u.user_email && u.user_email.toLowerCase().includes(searchLower)) ||
                   (u.organization_name && u.organization_name.toLowerCase().includes(searchLower));
        });
    }

    return result.sort(function(a, b) {
        return b.total_reports - a.total_reports;
    });
}

/**
 * Get demo user activity
 */
function getDemoUserActivity(userId, days) {
    if (!syntheticData || !syntheticData.events) {
        return { error: 'No synthetic data' };
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);

    // Filter events for this user
    const events = syntheticData.events.filter(function(e) {
        return e.user_id === userId && new Date(e.event_timestamp) >= cutoff;
    });

    if (events.length === 0) {
        return { error: 'User not found' };
    }

    // Build user summary
    const user = {
        user_id: userId,
        user_email: events[0].user_email,
        user_type: events[0].user_type,
        organization_name: events[0].organization_name,
        total_reports: events.length,
        counties_researched: new Set(events.filter(e => e.county_fips).map(e => e.county_fips)).size,
        lenders_researched: new Set(events.filter(e => e.lender_id).map(e => e.lender_id)).size,
        last_activity: events[0].event_timestamp,
        first_activity: events[events.length - 1].event_timestamp
    };

    // Activity by app
    const byApp = {};
    events.forEach(function(e) {
        if (!byApp[e.event_name]) {
            byApp[e.event_name] = { event_name: e.event_name, count: 0 };
        }
        byApp[e.event_name].count++;
    });

    // Counties researched
    const counties = {};
    events.forEach(function(e) {
        if (!e.county_fips) return;
        if (!counties[e.county_fips]) {
            counties[e.county_fips] = {
                county_fips: e.county_fips,
                county_name: e.county_name,
                state: e.state,
                report_count: 0
            };
        }
        counties[e.county_fips].report_count++;
    });

    // Lenders researched
    const lenders = {};
    events.forEach(function(e) {
        if (!e.lender_id) return;
        if (!lenders[e.lender_id]) {
            lenders[e.lender_id] = {
                lender_id: e.lender_id,
                lender_name: e.lender_name,
                report_count: 0
            };
        }
        lenders[e.lender_id].report_count++;
    });

    // Recent reports
    const recentReports = events.slice(0, 20).map(function(e) {
        return {
            event_timestamp: e.event_timestamp,
            event_name: e.event_name,
            county_name: e.county_name,
            state: e.state,
            lender_name: e.lender_name,
            lender_id: e.lender_id
        };
    });

    return {
        user: user,
        by_app: Object.values(byApp).sort((a, b) => b.count - a.count),
        counties: Object.values(counties).sort((a, b) => b.report_count - a.report_count),
        lenders: Object.values(lenders).sort((a, b) => b.report_count - a.report_count),
        recent_reports: recentReports
    };
}

/**
 * Load users list
 * Returns a promise for chaining
 */
function loadUsers() {
    const days = parseInt($('#time-period').val()) || 90;
    const search = $('#search-input').val() ? $('#search-input').val().trim() : null;

    // Show loading state
    $('#users-tbody').html('<tr><td colspan="6" class="loading-cell">Loading users...</td></tr>');

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const demoUsers = getDemoUsers(days, search);
        usersData = demoUsers;
        renderUsersTable(demoUsers);
        return Promise.resolve();
    }

    return $.ajax({
        url: '/analytics/api/users',
        data: {
            days: days,
            search: search
        },
        success: function(response) {
            if (response.success) {
                usersData = response.data;
                renderUsersTable(usersData);
            } else {
                showError('Failed to load users: ' + response.error);
            }
        },
        error: function(xhr) {
            console.error('API error:', xhr.responseText);
            showError('Failed to connect to API');
        }
    });
}

/**
 * Render users table
 */
function renderUsersTable(data) {
    const tbody = $('#users-tbody').empty();
    $('#user-count').text(data.length + ' users');

    if (data.length === 0) {
        tbody.html('<tr><td colspan="6" class="loading-cell">No users found. Data will appear once users generate reports.</td></tr>');
        return;
    }

    data.forEach(function(user) {
        const userId = user.user_id || 'Unknown';
        const displayId = user.user_email || (userId.length > 20 ? userId.substring(0, 20) + '...' : userId);
        const userType = user.user_type || '-';
        const org = user.organization_name || '';
        const reports = user.total_reports || 0;
        const counties = user.counties_researched || 0;
        const lenders = user.lenders_researched || 0;
        const lastActivity = formatDate(user.last_activity);

        const row = $('<tr class="clickable-row">')
            .attr('data-user-id', userId)
            .addClass(selectedUserId === userId ? 'selected' : '')
            .append('<td title="' + escapeHtml(userId) + '">' +
                    '<div class="user-name">' + escapeHtml(displayId) + '</div>' +
                    (org ? '<div class="user-org-small">' + escapeHtml(org) + '</div>' : '') +
                    '</td>')
            .append('<td>' + (userType !== '-' ? '<span class="user-type-badge ' + userType + '">' + escapeHtml(userType) + '</span>' : '-') + '</td>')
            .append('<td><strong>' + formatNumber(reports) + '</strong></td>')
            .append('<td>' + formatNumber(counties) + '</td>')
            .append('<td>' + formatNumber(lenders) + '</td>')
            .append('<td>' + lastActivity + '</td>');

        tbody.append(row);
    });
}

/**
 * Select a user and show detail panel
 */
function selectUser(userId) {
    selectedUserId = userId;

    // Highlight selected row
    $('.users-table tbody tr').removeClass('selected');
    $('.users-table tbody tr[data-user-id="' + userId + '"]').addClass('selected');

    // Show detail panel with loading state
    $('#user-detail-panel').show();
    $('#detail-user-id').text('Loading...');
    $('#user-detail-content').html('<div class="loading-item">Loading user details...</div>');

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const days = parseInt($('#time-period').val()) || 90;
        const data = getDemoUserActivity(userId, days);
        renderUserDetail(data);
        return;
    }

    // Fetch user activity
    const days = $('#time-period').val() || 90;
    $.ajax({
        url: '/analytics/api/users/' + encodeURIComponent(userId) + '/activity',
        data: { days: days },
        success: function(response) {
            if (response.success) {
                renderUserDetail(response.data);
            } else {
                $('#user-detail-content').html('<div class="error-item">Failed to load user details</div>');
            }
        },
        error: function() {
            $('#user-detail-content').html('<div class="error-item">Error loading user details</div>');
        }
    });
}

/**
 * Render user detail panel
 */
function renderUserDetail(data) {
    if (data.error) {
        $('#detail-user-id').text('Error');
        $('#user-detail-content').html('<div class="error-item">' + escapeHtml(data.error) + '</div>');
        return;
    }

    const user = data.user || {};
    const displayName = user.user_email || (user.user_id || 'Unknown').substring(0, 25);
    $('#detail-user-id').text(displayName);

    let html = '';

    // User summary section
    html += '<div class="detail-section">';
    html += '<h4>Summary</h4>';
    html += '<div class="detail-grid">';
    html += '<div class="detail-item"><span class="label">User ID:</span><code>' + escapeHtml(user.user_id || '-') + '</code></div>';
    if (user.user_email) {
        html += '<div class="detail-item"><span class="label">Email:</span>' + escapeHtml(user.user_email) + '</div>';
    }
    if (user.user_type) {
        html += '<div class="detail-item"><span class="label">Type:</span><span class="user-type-badge ' + user.user_type + '">' + escapeHtml(user.user_type) + '</span></div>';
    }
    if (user.organization_name) {
        html += '<div class="detail-item"><span class="label">Organization:</span>' + escapeHtml(user.organization_name) + '</div>';
    }
    html += '<div class="detail-item"><span class="label">Total Reports:</span><strong>' + formatNumber(user.total_reports || 0) + '</strong></div>';
    html += '<div class="detail-item"><span class="label">Counties:</span>' + formatNumber(user.counties_researched || 0) + '</div>';
    html += '<div class="detail-item"><span class="label">Lenders:</span>' + formatNumber(user.lenders_researched || 0) + '</div>';
    html += '<div class="detail-item"><span class="label">First Activity:</span>' + formatDate(user.first_activity) + '</div>';
    html += '<div class="detail-item"><span class="label">Last Activity:</span>' + formatDate(user.last_activity) + '</div>';
    html += '</div>';
    html += '</div>';

    // Activity by app
    if (data.by_app && data.by_app.length > 0) {
        html += '<div class="detail-section">';
        html += '<h4>Reports by App</h4>';
        html += '<div class="app-breakdown">';
        const appNames = {
            'lendsight_report': 'LendSight',
            'bizsight_report': 'BizSight',
            'branchsight_report': 'BranchSight',
            'dataexplorer_area_report': 'DataExplorer (Area)',
            'dataexplorer_lender_report': 'DataExplorer (Lender)'
        };
        data.by_app.forEach(function(app) {
            const name = appNames[app.event_name] || app.event_name;
            html += '<div class="app-item"><span>' + escapeHtml(name) + '</span><strong>' + formatNumber(app.count) + '</strong></div>';
        });
        html += '</div>';
        html += '</div>';
    }

    // Counties researched
    if (data.counties && data.counties.length > 0) {
        html += '<div class="detail-section">';
        html += '<h4>Counties Researched (' + data.counties.length + ')</h4>';
        html += '<div class="entity-list">';
        data.counties.slice(0, 10).forEach(function(county) {
            const name = county.county_name || county.county_fips;
            const state = county.state || '';
            html += '<div class="entity-item">';
            html += '<span>' + escapeHtml(name) + (state ? ', ' + state : '') + '</span>';
            html += '<span class="count">' + formatNumber(county.report_count) + ' reports</span>';
            html += '</div>';
        });
        if (data.counties.length > 10) {
            html += '<div class="more-items">+' + (data.counties.length - 10) + ' more counties</div>';
        }
        html += '</div>';
        html += '</div>';
    }

    // Lenders researched
    if (data.lenders && data.lenders.length > 0) {
        html += '<div class="detail-section">';
        html += '<h4>Lenders Researched (' + data.lenders.length + ')</h4>';
        html += '<div class="entity-list">';
        data.lenders.slice(0, 10).forEach(function(lender) {
            const name = lender.lender_name || lender.lender_id;
            html += '<div class="entity-item">';
            html += '<span>' + escapeHtml(name) + '</span>';
            html += '<span class="count">' + formatNumber(lender.report_count) + ' reports</span>';
            html += '</div>';
        });
        if (data.lenders.length > 10) {
            html += '<div class="more-items">+' + (data.lenders.length - 10) + ' more lenders</div>';
        }
        html += '</div>';
        html += '</div>';
    }

    // Recent activity
    if (data.recent_reports && data.recent_reports.length > 0) {
        html += '<div class="detail-section">';
        html += '<h4>Recent Reports</h4>';
        html += '<div class="recent-list">';
        const appNames = {
            'lendsight_report': 'LendSight',
            'bizsight_report': 'BizSight',
            'branchsight_report': 'BranchSight',
            'dataexplorer_area_report': 'DataExplorer',
            'dataexplorer_lender_report': 'DataExplorer'
        };
        data.recent_reports.slice(0, 10).forEach(function(report) {
            const app = appNames[report.event_name] || report.event_name;
            const location = report.county_name ? report.county_name + (report.state ? ', ' + report.state : '') : '';
            const lender = report.lender_name || '';
            const date = formatDate(report.event_timestamp);
            html += '<div class="recent-item">';
            html += '<div class="recent-app">' + escapeHtml(app) + '</div>';
            html += '<div class="recent-detail">';
            if (location) html += '<span><i class="fas fa-map-marker-alt"></i> ' + escapeHtml(location) + '</span>';
            if (lender) html += '<span><i class="fas fa-university"></i> ' + escapeHtml(lender) + '</span>';
            html += '</div>';
            html += '<div class="recent-date">' + date + '</div>';
            html += '</div>';
        });
        html += '</div>';
        html += '</div>';
    }

    $('#user-detail-content').html(html);
}

/**
 * Close detail panel
 */
function closeDetailPanel() {
    selectedUserId = null;
    $('#user-detail-panel').hide();
    $('.users-table tbody tr').removeClass('selected');
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
    $('#users-tbody').html(
        '<tr><td colspan="6" class="loading-cell" style="color: #dc3545;">' +
        '<i class="fas fa-exclamation-triangle"></i> ' + escapeHtml(message) +
        '</td></tr>'
    );
}
