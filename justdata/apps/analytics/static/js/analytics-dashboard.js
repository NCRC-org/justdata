/**
 * Analytics Dashboard JavaScript
 * Main dashboard functionality for loading and displaying summary data
 */

// Global state
let currentDays = 90;
let availableUserTypes = [];
let selectedUserTypes = []; // Empty means all
let excludedUserTypes = [];
let demoMode = false;
let syntheticData = null;

/**
 * Initialize dashboard on page load
 */
$(document).ready(function() {
    // Show demo toggle only for admin users
    if (window.justDataUserType === 'admin') {
        $('#demo-toggle-container').show();
    } else {
        // Non-admins can't use demo mode - force it off
        localStorage.removeItem('analyticsDemo');
        demoMode = false;
    }
    
    // Check for demo mode in localStorage (admin only)
    demoMode = localStorage.getItem('analyticsDemo') === 'true' && window.justDataUserType === 'admin';
    if (demoMode) {
        $('#demo-mode-toggle').prop('checked', true);
        $('#demo-mode-banner').show();
        // Wait for synthetic data to load before showing dashboard
        loadSyntheticData().then(function() {
            loadSummary();
            loadCoalitionPreview();
        });
    } else {
        // Load dashboard data immediately when not in demo mode
        loadSummary();
        loadCoalitionPreview();
    }

    // Load user types for filter dropdown
    loadUserTypes();

    // Handle time period changes
    $('#time-period').on('change', function() {
        currentDays = parseInt($(this).val());
        loadSummary();
        loadCoalitionPreview();
    });

    // Close dropdown when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.user-type-dropdown').length) {
            $('#user-type-menu').hide();
            $('.user-type-btn').removeClass('open');
        }
    });
});

/**
 * Toggle demo mode on/off (admin only)
 */
function toggleDemoMode() {
    // Only admins can use demo mode
    if (window.justDataUserType !== 'admin') {
        console.warn('Demo mode is admin-only');
        return;
    }
    
    demoMode = !demoMode;
    localStorage.setItem('analyticsDemo', demoMode);
    $('#demo-mode-toggle').prop('checked', demoMode);

    if (demoMode) {
        $('#demo-mode-banner').show();
        loadSyntheticData().then(function() {
            loadSummary();
            loadCoalitionPreview();
        });
    } else {
        $('#demo-mode-banner').hide();
        syntheticData = null;
        loadSummary();
        loadCoalitionPreview();
    }
}

/**
 * Load synthetic data from JSON file
 */
function loadSyntheticData() {
    return $.ajax({
        url: '/analytics/static/demo_data/synthetic_events.json',
        dataType: 'json',
        success: function(data) {
            syntheticData = data;
            console.log('Loaded synthetic data:', data.events.length, 'events');
        },
        error: function(xhr, status, error) {
            console.error('Failed to load synthetic data:', error);
            syntheticData = null;
        }
    });
}

/**
 * Get demo summary from synthetic data
 */
function getDemoSummary(days) {
    if (!syntheticData || !syntheticData.events) {
        return null;
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);
    const events = syntheticData.events.filter(function(e) {
        return new Date(e.event_timestamp) >= cutoff;
    });

    // Count unique values
    const users = new Set();
    const counties = new Set();
    const lenders = new Set();
    const appCounts = {};
    const countyReports = {};
    const lenderEvents = {};

    events.forEach(function(e) {
        if (e.user_id) users.add(e.user_id);
        if (e.county_fips) {
            counties.add(e.county_fips);
            if (!countyReports[e.county_fips]) {
                countyReports[e.county_fips] = {
                    county_fips: e.county_fips,
                    county_name: e.county_name,
                    state: e.state,
                    total_reports: 0
                };
            }
            countyReports[e.county_fips].total_reports++;
        }
        if (e.lender_id) {
            lenders.add(e.lender_id);
            if (!lenderEvents[e.lender_id]) {
                lenderEvents[e.lender_id] = {
                    lender_id: e.lender_id,
                    lender_name: e.lender_name,
                    total_events: 0
                };
            }
            lenderEvents[e.lender_id].total_events++;
        }

        // App usage
        if (!appCounts[e.event_name]) {
            appCounts[e.event_name] = { event_name: e.event_name, event_count: 0, unique_users: new Set() };
        }
        appCounts[e.event_name].event_count++;
        if (e.user_id) appCounts[e.event_name].unique_users.add(e.user_id);
    });

    // Format app usage
    const appUsage = Object.values(appCounts)
        .map(function(a) {
            return { event_name: a.event_name, event_count: a.event_count, unique_users: a.unique_users.size };
        })
        .sort(function(a, b) { return b.event_count - a.event_count; });

    // Top counties
    const topCounties = Object.values(countyReports)
        .sort(function(a, b) { return b.total_reports - a.total_reports; })
        .slice(0, 5);

    // Top lenders
    const topLenders = Object.values(lenderEvents)
        .sort(function(a, b) { return b.total_events - a.total_events; })
        .slice(0, 5);

    return {
        total_users: users.size,
        total_events: events.length,
        total_lenders: lenders.size,
        top_counties: topCounties,
        top_lenders: topLenders,
        app_usage: appUsage,
        days: days
    };
}

/**
 * Load available user types for filter
 */
function loadUserTypes() {
    $.ajax({
        url: '/analytics/api/user-types',
        success: function(response) {
            if (response.success && response.data) {
                availableUserTypes = response.data;
                renderUserTypeOptions();
            }
        },
        error: function() {
            console.error('Failed to load user types');
        }
    });
}

/**
 * Render user type checkboxes in dropdown
 */
function renderUserTypeOptions() {
    const container = $('#user-type-options');
    container.empty();

    // Select All option
    container.append(
        '<label class="user-type-option select-all">' +
        '<input type="checkbox" value="all" id="select-all-types" checked onchange="handleSelectAllTypes()">' +
        '<span>Select All</span>' +
        '</label>'
    );

    // Individual user types
    availableUserTypes.forEach(function(userType) {
        container.append(
            '<label class="user-type-option">' +
            '<input type="checkbox" value="' + escapeHtml(userType) + '" class="user-type-checkbox" checked>' +
            '<span>' + escapeHtml(userType) + '</span>' +
            '</label>'
        );
    });
}

/**
 * Toggle user type dropdown visibility
 */
function toggleUserTypeDropdown() {
    const menu = $('#user-type-menu');
    const btn = $('.user-type-btn');

    if (menu.is(':visible')) {
        menu.hide();
        btn.removeClass('open');
    } else {
        menu.show();
        btn.addClass('open');
    }
}

/**
 * Handle Select All checkbox
 */
function handleSelectAllTypes() {
    const selectAll = $('#select-all-types').is(':checked');
    $('.user-type-checkbox').prop('checked', selectAll);
}

/**
 * Apply user type filter and reload data
 */
function applyUserTypeFilter() {
    const allChecked = $('#select-all-types').is(':checked');
    const checkedTypes = $('.user-type-checkbox:checked').map(function() {
        return $(this).val();
    }).get();

    // Update label
    if (allChecked || checkedTypes.length === availableUserTypes.length) {
        $('#user-type-label').text('All Users');
        selectedUserTypes = [];
        excludedUserTypes = [];
    } else if (checkedTypes.length === 0) {
        $('#user-type-label').text('None Selected');
        selectedUserTypes = [];
        excludedUserTypes = availableUserTypes;
    } else if (checkedTypes.length <= 2) {
        $('#user-type-label').text(checkedTypes.join(', '));
        selectedUserTypes = checkedTypes;
        excludedUserTypes = [];
    } else {
        $('#user-type-label').text(checkedTypes.length + ' types');
        selectedUserTypes = checkedTypes;
        excludedUserTypes = [];
    }

    // Close dropdown
    $('#user-type-menu').hide();
    $('.user-type-btn').removeClass('open');

    // Reload data with new filter
    loadSummary();
    loadCoalitionPreview();
}

/**
 * Load summary metrics
 */
function loadSummary() {
    const days = $('#time-period').val() || 90;

    // Show loading state
    $('#total-users, #total-events, #lenders-count').html('<span class="loading-placeholder">...</span>');
    $('#top-counties, #top-lenders').html('<li class="loading-item">Loading...</li>');
    $('#app-usage').html('<div class="loading-item">Loading...</div>');
    $('#bq-cost').html('<span class="loading-placeholder">...</span>');
    $('#bq-queries').html('<span class="loading-placeholder">-- queries</span>');
    $('#ai-cost').html('<span class="loading-placeholder">...</span>');
    $('#ai-requests').html('<span class="loading-placeholder">-- requests</span>');

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const demoSummary = getDemoSummary(parseInt(days));
        if (demoSummary) {
            renderSummary(demoSummary);
            fetchCountyCounts(days);
            // Show demo cost data
            $('#bq-cost').text('$12.34');
            $('#bq-queries').text('1,234 queries');
            $('#ai-cost').text('$8.76');
            $('#ai-requests').text('543 requests');
            return;
        }
    }

    $.ajax({
        url: '/analytics/api/summary',
        data: { days: days },
        success: function(response) {
            if (response.success) {
                renderSummary(response.data);
            } else {
                showError('Failed to load summary: ' + response.error);
            }
        },
        error: function(xhr) {
            console.error('API error:', xhr.responseText);
            showError('Failed to connect to analytics API');
        }
    });

    // Also fetch county and coalition counts
    fetchCountyCounts(days);
    
    // Fetch BigQuery costs (always 30 days for cost card)
    fetchCostSummary();
}

/**
 * Fetch BigQuery and AI cost summaries
 */
function fetchCostSummary() {
    // Fetch BigQuery costs
    $.ajax({
        url: '/analytics/api/costs',
        data: { days: 30 },
        success: function(response) {
            if (response.success && response.data) {
                const cost = response.data.estimated_cost_usd || 0;
                const queries = response.data.query_count || 0;
                $('#bq-cost').text(formatCostDisplay(cost));
                $('#bq-queries').text(formatNumber(queries) + ' queries');
            } else {
                $('#bq-cost').text('N/A');
                $('#bq-queries').text('Error loading costs');
            }
        },
        error: function(xhr) {
            console.error('Cost API error:', xhr.responseText);
            $('#bq-cost').text('N/A');
            $('#bq-queries').text('Error loading costs');
        }
    });
    
    // Fetch AI costs
    $.ajax({
        url: '/analytics/api/ai-costs',
        data: { days: 30 },
        success: function(response) {
            if (response.success && response.data) {
                const cost = response.data.total_cost_usd || 0;
                const requests = response.data.total_requests || 0;
                $('#ai-cost').text(formatCostDisplay(cost));
                $('#ai-requests').text(formatNumber(requests) + ' requests');
            } else {
                $('#ai-cost').text('$0.00');
                $('#ai-requests').text('No data yet');
            }
        },
        error: function(xhr) {
            console.error('AI Cost API error:', xhr.responseText);
            $('#ai-cost').text('$0.00');
            $('#ai-requests').text('Error loading');
        }
    });
}

/**
 * Format cost display - show cents for amounts < $0.01
 */
function formatCostDisplay(amount) {
    if (amount > 0 && amount < 0.01) {
        const cents = amount * 100;
        return cents.toFixed(2) + '¢';
    }
    return '$' + amount.toFixed(2);
}

/**
 * Render summary data
 */
function renderSummary(data) {
    // Summary cards
    $('#total-users').text(formatNumber(data.total_users));
    $('#total-events').text(formatNumber(data.total_events));
    $('#lenders-count').text(formatNumber(data.total_lenders || 0));

    // Top counties - clickable
    const countiesList = $('#top-counties').empty();
    if (data.top_counties && data.top_counties.length > 0) {
        data.top_counties.forEach(function(county) {
            const name = county.county_name || county.county_fips;
            const state = county.state || '';
            const li = $('<li class="clickable-item">')
                .html(
                    '<span class="item-name">' + escapeHtml(name) + (state ? ', ' + state : '') + '</span>' +
                    '<span class="item-value">' + formatNumber(county.total_reports) + ' reports</span>'
                )
                .on('click', function() {
                    showDashboardDetail('county', county.county_fips, name + (state ? ', ' + state : ''));
                });
            countiesList.append(li);
        });
    } else {
        countiesList.append('<li class="loading-item">No data available</li>');
    }

    // Top lenders - clickable
    const lendersList = $('#top-lenders').empty();
    if (data.top_lenders && data.top_lenders.length > 0) {
        data.top_lenders.forEach(function(lender) {
            const name = lender.lender_name || lender.lender_id || 'Unknown';
            const li = $('<li class="clickable-item">')
                .html(
                    '<span class="item-name">' + escapeHtml(name) + '</span>' +
                    '<span class="item-value">' + formatNumber(lender.total_events) + ' events</span>'
                )
                .on('click', function() {
                    showDashboardDetail('lender', lender.lender_id, name);
                });
            lendersList.append(li);
        });
    } else {
        lendersList.append('<li class="loading-item">No data available</li>');
    }

    // App usage chart
    renderAppUsage(data.app_usage);
}

/**
 * Render app usage bar chart
 */
function renderAppUsage(appUsage) {
    const container = $('#app-usage').empty();

    if (!appUsage || appUsage.length === 0) {
        container.html('<div class="loading-item">No usage data available</div>');
        return;
    }

    // Find max for scaling
    const maxCount = Math.max(...appUsage.map(a => a.event_count));

    // App name mapping
    const appNames = {
        'lendsight_report': 'LendSight',
        'bizsight_report': 'BizSight',
        'branchsight_report': 'BranchSight',
        'branchmapper_report': 'BranchMapper',
        'mergermeter_report': 'MergerMeter',
        'dataexplorer_report': 'DataExplorer',
        'dataexplorer_area_report': 'DataExplorer',
        'dataexplorer_lender_report': 'DataExplorer',
        'lenderprofile_view': 'LenderProfile'
    };

    appUsage.forEach(function(app) {
        const name = appNames[app.event_name] || app.event_name;
        const percentage = (app.event_count / maxCount) * 100;

        const bar = $('<div class="app-bar">')
            .append('<span class="app-name">' + escapeHtml(name) + '</span>')
            .append(
                '<div class="bar-container">' +
                '<div class="bar-fill" style="width: ' + percentage + '%"></div>' +
                '</div>'
            )
            .append('<span class="bar-value">' + formatNumber(app.event_count) + '</span>');

        container.append(bar);
    });
}

/**
 * Fetch county research count
 */
function fetchCountyCounts(days) {
    // Use demo data if in demo mode
    if (demoMode && syntheticData && syntheticData.events) {
        const now = new Date();
        const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);
        const events = syntheticData.events.filter(function(e) {
            return new Date(e.event_timestamp) >= cutoff;
        });
        const uniqueCounties = new Set(events.filter(e => e.county_fips).map(e => e.county_fips)).size;
        $('#counties-count').text(formatNumber(uniqueCounties));
        return;
    }

    $.ajax({
        url: '/analytics/api/research-activity',
        data: { days: days },
        success: function(response) {
            if (response.success && response.data) {
                // Count unique counties
                const uniqueCounties = new Set(response.data.map(d => d.county_fips)).size;
                $('#counties-count').text(formatNumber(uniqueCounties));
            }
        }
    });
}

/**
 * Load coalition preview
 */
function loadCoalitionPreview() {
    const days = $('#time-period').val() || 90;

    // Use demo data if in demo mode
    if (demoMode && syntheticData && syntheticData.events) {
        const demoCoalitions = getDemoCoalitions(parseInt(days));
        renderCoalitionPreview(demoCoalitions);
        $('#coalition-count').text(formatNumber(demoCoalitions.length));
        return;
    }

    $.ajax({
        url: '/analytics/api/coalition-opportunities',
        data: { days: days, min_users: 3 },
        success: function(response) {
            if (response.success && response.data) {
                renderCoalitionPreview(response.data);
                $('#coalition-count').text(formatNumber(response.data.length));
            }
        }
    });
}

/**
 * Get demo coalitions from synthetic data
 */
function getDemoCoalitions(days) {
    if (!syntheticData || !syntheticData.events) {
        return [];
    }

    const now = new Date();
    const cutoff = days > 0 ? new Date(now - days * 24 * 60 * 60 * 1000) : new Date(0);
    const events = syntheticData.events.filter(function(e) {
        return new Date(e.event_timestamp) >= cutoff;
    });

    // Group by county
    const countyData = {};
    events.forEach(function(e) {
        if (!e.county_fips) return;
        if (!countyData[e.county_fips]) {
            countyData[e.county_fips] = {
                entity_id: e.county_fips,
                entity_name: e.county_name + ', ' + e.state,
                entity_type: 'county',
                users: new Set(),
                organizations: new Set()
            };
        }
        if (e.user_id) countyData[e.county_fips].users.add(e.user_id);
        if (e.organization_name) countyData[e.county_fips].organizations.add(e.organization_name);
    });

    // Convert to array and filter for multiple users
    return Object.values(countyData)
        .map(function(c) {
            return {
                entity_id: c.entity_id,
                entity_name: c.entity_name,
                entity_type: c.entity_type,
                unique_users: c.users.size,
                unique_organizations: c.organizations.size
            };
        })
        .filter(function(c) { return c.unique_users >= 3; })
        .sort(function(a, b) { return b.unique_users - a.unique_users; });
}

/**
 * Render coalition preview list
 */
function renderCoalitionPreview(data) {
    const list = $('#coalition-preview').empty();

    if (!data || data.length === 0) {
        list.append('<li class="loading-item">No coalition opportunities found</li>');
        return;
    }

    // Show top 5
    data.slice(0, 5).forEach(function(item) {
        const name = item.entity_name || item.entity_id;
        const type = item.entity_type === 'county' ? 'County' : 'Lender';
        const orgs = item.unique_organizations || 0;
        const users = item.unique_users || 0;

        list.append(
            $('<li>').html(
                '<div class="entity-name">' + escapeHtml(name) + '</div>' +
                '<div class="entity-meta">' +
                '<span class="type-badge ' + item.entity_type + '">' + type + '</span> ' +
                users + ' users from ' + orgs + ' organizations' +
                '</div>'
            )
        );
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
 * Escape HTML to prevent XSS
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
 * Show error message
 */
function showError(message) {
    console.error(message);
    // Could add toast notification here
}

/**
 * Show dashboard detail panel with researchers
 */
function showDashboardDetail(entityType, entityId, entityName) {
    const panel = $('#dashboard-detail-panel');
    const icon = entityType === 'county' ? 'fa-map-marker-alt' : 'fa-university';

    // Update panel header
    $('#detail-icon').attr('class', 'fas ' + icon);
    $('#dashboard-entity-name').text(entityName);
    $('#dashboard-detail-subtitle').text(
        entityType === 'county'
            ? 'Researchers working in this area:'
            : 'Researchers interested in this lender:'
    );

    // Show loading state
    $('#dashboard-users-list').html('<div class="loading-item">Loading researchers...</div>');

    // Show panel
    panel.fadeIn(200);

    // Load researchers
    loadDashboardResearchers(entityType, entityId);
}

/**
 * Load researchers for the dashboard detail panel
 */
function loadDashboardResearchers(entityType, entityId) {
    const days = parseInt($('#time-period').val()) || 0;

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const researchers = getDemoEntityResearchers(entityType, entityId, days);
        renderDashboardResearchers(researchers);
        return;
    }

    // Use entity-users API
    $.ajax({
        url: '/analytics/api/entity-users',
        data: {
            entity_type: entityType,
            entity_id: entityId,
            days: days
        },
        success: function(response) {
            if (response.success) {
                renderDashboardResearchers(response.data);
            } else {
                $('#dashboard-users-list').html('<div class="error-item">Failed to load researchers</div>');
            }
        },
        error: function() {
            $('#dashboard-users-list').html('<div class="error-item">Failed to connect to API</div>');
        }
    });
}

/**
 * Get demo researchers for an entity from synthetic data
 */
function getDemoEntityResearchers(entityType, entityId, days) {
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
                user_type: e.user_type,
                organization_name: e.organization_name,
                report_count: 0,
                apps: {},
                last_activity: e.event_timestamp
            };
        }
        users[e.user_id].report_count++;
        // Track which apps they used
        if (e.event_name) {
            users[e.user_id].apps[e.event_name] = (users[e.user_id].apps[e.event_name] || 0) + 1;
        }
        if (new Date(e.event_timestamp) > new Date(users[e.user_id].last_activity)) {
            users[e.user_id].last_activity = e.event_timestamp;
        }
    });

    return Object.values(users).sort(function(a, b) {
        return b.report_count - a.report_count;
    });
}

/**
 * Render researchers in the dashboard detail panel
 */
function renderDashboardResearchers(researchers) {
    const container = $('#dashboard-users-list').empty();

    if (!researchers || researchers.length === 0) {
        container.html('<div class="no-data-item">No researcher details available</div>');
        return;
    }

    const appNames = {
        'lendsight_report': 'LendSight',
        'bizsight_report': 'BizSight',
        'branchsight_report': 'BranchSight',
        'dataexplorer_area_report': 'DataExplorer',
        'dataexplorer_lender_report': 'DataExplorer'
    };

    researchers.forEach(function(user) {
        const displayName = user.user_email || (user.user_id ? user.user_id.substring(0, 12) + '...' : 'Unknown');
        const orgName = user.organization_name || '';
        const userType = user.user_type || '';
        const reportCount = user.report_count || 0;

        // Format apps used
        let appsHtml = '';
        if (user.apps && Object.keys(user.apps).length > 0) {
            const appList = Object.entries(user.apps)
                .map(function([app, count]) {
                    return (appNames[app] || app) + ' (' + count + ')';
                })
                .join(', ');
            appsHtml = '<div class="user-apps"><i class="fas fa-laptop"></i> ' + escapeHtml(appList) + '</div>';
        }

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
            .append(appsHtml)
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
 * Close dashboard detail panel
 */
function closeDashboardDetail() {
    $('#dashboard-detail-panel').fadeOut(200);
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
 * Export analytics data to Excel
 * Downloads a multi-sheet Excel file with joinable data for offline analysis
 */
function exportAnalyticsData() {
    const days = $('#time-period').val() || 0;
    const btn = $('#export-btn');

    // Show loading state
    btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Exporting...');

    // Check if demo mode - warn user
    if (demoMode) {
        if (!confirm('You are in DEMO MODE. The export will contain real data from the database, not the synthetic demo data.\n\nContinue with export?')) {
            btn.prop('disabled', false).html('<i class="fas fa-file-excel"></i> Export');
            return;
        }
    }

    // Trigger download
    const exportUrl = '/analytics/api/export?days=' + days;

    // Use fetch to handle potential errors
    fetch(exportUrl)
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Export failed: ' + response.statusText);
            }
            return response.blob();
        })
        .then(function(blob) {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;

            // Generate filename
            const dateStr = new Date().toISOString().split('T')[0];
            const periodStr = days > 0 ? days + 'd' : 'all-time';
            a.download = 'analytics-export-' + periodStr + '-' + dateStr + '.xlsx';

            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Reset button
            btn.prop('disabled', false).html('<i class="fas fa-file-excel"></i> Export');
        })
        .catch(function(error) {
            console.error('Export error:', error);
            alert('Failed to export data: ' + error.message);
            btn.prop('disabled', false).html('<i class="fas fa-file-excel"></i> Export');
        });
}
