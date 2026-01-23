/**
 * Analytics Dashboard JavaScript
 * Main dashboard functionality for loading and displaying summary data
 */

// Global state
let currentDays = 90;
let availableUserTypes = [];
let selectedUserTypes = []; // Empty means all
let excludedUserTypes = [];

/**
 * Initialize dashboard on page load
 */
$(document).ready(function() {
    // Load user types for filter dropdown
    loadUserTypes();

    // Load dashboard data
    loadSummary();
    loadCoalitionPreview();

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
    $('#total-users, #total-events').html('<span class="loading-placeholder">...</span>');
    $('#top-counties, #top-lenders').html('<li class="loading-item">Loading...</li>');
    $('#app-usage').html('<div class="loading-item">Loading...</div>');

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
}

/**
 * Render summary data
 */
function renderSummary(data) {
    // Summary cards
    $('#total-users').text(formatNumber(data.total_users));
    $('#total-events').text(formatNumber(data.total_events));

    // Top counties
    const countiesList = $('#top-counties').empty();
    if (data.top_counties && data.top_counties.length > 0) {
        data.top_counties.forEach(function(county) {
            const name = county.county_name || county.county_fips;
            const state = county.state || '';
            countiesList.append(
                $('<li>').html(
                    '<span class="item-name">' + escapeHtml(name) + (state ? ', ' + state : '') + '</span>' +
                    '<span class="item-value">' + formatNumber(county.total_reports) + ' reports</span>'
                )
            );
        });
    } else {
        countiesList.append('<li class="loading-item">No data available</li>');
    }

    // Top lenders
    const lendersList = $('#top-lenders').empty();
    if (data.top_lenders && data.top_lenders.length > 0) {
        data.top_lenders.forEach(function(lender) {
            const name = lender.lender_name || lender.lender_id || 'Unknown';
            lendersList.append(
                $('<li>').html(
                    '<span class="item-name">' + escapeHtml(name) + '</span>' +
                    '<span class="item-value">' + formatNumber(lender.total_events) + ' events</span>'
                )
            );
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
