/**
 * Users Tab JavaScript
 * Individual user lookup and activity display
 */

let usersData = [];
let filteredUsersData = [];
let selectedUserId = null;
let searchTimeout = null;
let demoMode = false;
let syntheticData = null;
let allOrganizations = [];
let currentSort = { field: 'total_reports', direction: 'desc' };
let selectedTypes = ['REGISTERED', 'INSTITUTIONAL', 'MEDIA', 'MEMBER', 'OTHER', 'RESEARCH'];

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
    $('#org-filter').on('change', applyFilters);

    // Handle search with debounce
    $('#search-input').on('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(applyFilters, 300);
    });

    // Handle row clicks
    $(document).on('click', '.users-table tbody tr', function() {
        const userId = $(this).data('user-id');
        if (userId) {
            selectUser(userId);
        }
    });

    // Handle sortable column clicks
    $(document).on('click', '.users-table th.sortable', function() {
        const field = $(this).data('sort');
        if (currentSort.field === field) {
            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort.field = field;
            currentSort.direction = 'desc';
        }
        updateSortIcons();
        applyFilters();
    });

    // User type dropdown toggle
    $('#type-filter-btn').on('click', function(e) {
        e.stopPropagation();
        const menu = $('#type-filter-menu');
        const isVisible = menu.is(':visible');
        menu.toggle();
        $(this).toggleClass('open', !isVisible);
    });

    // Close dropdown when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.user-type-dropdown').length) {
            $('#type-filter-menu').hide();
            $('#type-filter-btn').removeClass('open');
        }
    });

    // Select all checkbox
    $('#type-select-all').on('change', function() {
        const isChecked = $(this).is(':checked');
        $('.type-checkbox').prop('checked', isChecked);
    });

    // Individual type checkboxes
    $('.type-checkbox').on('change', function() {
        const allChecked = $('.type-checkbox:checked').length === $('.type-checkbox').length;
        $('#type-select-all').prop('checked', allChecked);
    });

    // Apply type filter
    $('#type-apply-btn').on('click', function() {
        selectedTypes = [];
        $('.type-checkbox:checked').each(function() {
            selectedTypes.push($(this).val());
        });
        updateTypeFilterLabel();
        $('#type-filter-menu').hide();
        $('#type-filter-btn').removeClass('open');
        applyFilters();
    });

    // Clear filters button
    $('#clear-filters-btn').on('click', clearAllFilters);
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
                apps: new Set(),
                last_activity: e.event_timestamp,
                first_activity: e.event_timestamp
            };
        }
        users[e.user_id].total_reports++;
        if (e.county_fips) users[e.user_id].counties.add(e.county_fips);
        if (e.lender_id) users[e.user_id].lenders.add(e.lender_id);
        if (e.event_name) users[e.user_id].apps.add(e.event_name);
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
            apps_used: Array.from(u.apps || new Set()),
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
 * Extract unique organizations from users data
 */
function extractOrganizations(data) {
    const orgs = new Set();
    data.forEach(function(user) {
        if (user.organization_name && user.organization_name.trim()) {
            orgs.add(user.organization_name.trim());
        }
    });
    return Array.from(orgs).sort(function(a, b) {
        return a.toLowerCase().localeCompare(b.toLowerCase());
    });
}

/**
 * Populate organization dropdown
 */
function populateOrgDropdown(orgs) {
    const select = $('#org-filter');
    const currentVal = select.val();
    select.find('option:not(:first)').remove();
    orgs.forEach(function(org) {
        select.append('<option value="' + escapeHtml(org) + '">' + escapeHtml(org) + '</option>');
    });
    // Restore selection if it still exists
    if (currentVal && orgs.includes(currentVal)) {
        select.val(currentVal);
    }
}

/**
 * Update type filter label
 */
function updateTypeFilterLabel() {
    const total = 6; // Total number of type options
    if (selectedTypes.length === 0) {
        $('#type-filter-label').text('None selected');
    } else if (selectedTypes.length === total) {
        $('#type-filter-label').text('All Types');
    } else if (selectedTypes.length === 1) {
        $('#type-filter-label').text(selectedTypes[0]);
    } else {
        $('#type-filter-label').text(selectedTypes.length + ' selected');
    }
}

/**
 * Update sort icons in table header
 */
function updateSortIcons() {
    $('.users-table th.sortable .sort-icon').removeClass('fa-sort-up fa-sort-down active').addClass('fa-sort');
    const th = $('.users-table th[data-sort="' + currentSort.field + '"]');
    const icon = th.find('.sort-icon');
    icon.removeClass('fa-sort').addClass('active');
    icon.addClass(currentSort.direction === 'asc' ? 'fa-sort-up' : 'fa-sort-down');
}

/**
 * Sort users data
 */
function sortUsers(data) {
    return data.slice().sort(function(a, b) {
        let valA = a[currentSort.field];
        let valB = b[currentSort.field];

        // Handle date sorting for last_activity
        if (currentSort.field === 'last_activity') {
            valA = valA ? new Date(valA).getTime() : 0;
            valB = valB ? new Date(valB).getTime() : 0;
        }

        // Handle null/undefined values
        if (valA == null) valA = 0;
        if (valB == null) valB = 0;

        if (currentSort.direction === 'asc') {
            return valA > valB ? 1 : valA < valB ? -1 : 0;
        } else {
            return valA < valB ? 1 : valA > valB ? -1 : 0;
        }
    });
}

/**
 * Apply all filters to users data
 */
function applyFilters() {
    const search = $('#search-input').val() ? $('#search-input').val().trim().toLowerCase() : '';
    const orgFilter = $('#org-filter').val();

    let filtered = usersData.slice();

    // Apply search filter
    if (search) {
        filtered = filtered.filter(function(u) {
            return (u.user_id && u.user_id.toLowerCase().includes(search)) ||
                   (u.user_email && u.user_email.toLowerCase().includes(search)) ||
                   (u.organization_name && u.organization_name.toLowerCase().includes(search));
        });
    }

    // Apply organization filter
    if (orgFilter) {
        filtered = filtered.filter(function(u) {
            return u.organization_name === orgFilter;
        });
    }

    // Apply type filter
    if (selectedTypes.length < 6) {
        filtered = filtered.filter(function(u) {
            return selectedTypes.includes(u.user_type) || (!u.user_type && selectedTypes.includes('OTHER'));
        });
    }

    // Apply sorting
    filtered = sortUsers(filtered);

    filteredUsersData = filtered;
    renderUsersTable(filtered);
    updateClearFiltersButton();
}

/**
 * Check if any filters are active and show/hide clear button
 */
function updateClearFiltersButton() {
    const hasSearch = $('#search-input').val() && $('#search-input').val().trim();
    const hasOrg = $('#org-filter').val();
    const hasTypeFilter = selectedTypes.length < 6;

    if (hasSearch || hasOrg || hasTypeFilter) {
        $('#clear-filters-btn').show();
    } else {
        $('#clear-filters-btn').hide();
    }
}

/**
 * Clear all filters
 */
function clearAllFilters() {
    // Clear search
    $('#search-input').val('');

    // Clear org filter
    $('#org-filter').val('');

    // Reset type filter
    selectedTypes = ['REGISTERED', 'INSTITUTIONAL', 'MEDIA', 'MEMBER', 'OTHER', 'RESEARCH'];
    $('#type-select-all').prop('checked', true);
    $('.type-checkbox').prop('checked', true);
    updateTypeFilterLabel();

    // Reapply filters
    applyFilters();
}

/**
 * Load users list
 * Returns a promise for chaining
 */
function loadUsers() {
    const days = parseInt($('#time-period').val()) || 90;

    // Show loading state
    $('#users-tbody').html('<tr><td colspan="6" class="loading-cell">Loading users...</td></tr>');

    // Use demo data if in demo mode
    if (demoMode && syntheticData) {
        const demoUsers = getDemoUsers(days, null);
        usersData = demoUsers;
        allOrganizations = extractOrganizations(demoUsers);
        populateOrgDropdown(allOrganizations);
        applyFilters();
        return Promise.resolve();
    }

    return $.ajax({
        url: '/analytics/api/users',
        data: {
            days: days
        },
        success: function(response) {
            if (response.success) {
                usersData = response.data;
                allOrganizations = extractOrganizations(usersData);
                populateOrgDropdown(allOrganizations);
                applyFilters();
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
 * Check if a string is a valid email address
 */
function isValidEmail(str) {
    if (!str) return false;
    // Simple email pattern check
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(str);
}

/**
 * Check if a user ID represents an anonymous/system user
 * - GA4 client IDs: digits.digits (e.g., "1339126496.1769183487")
 * - Firebase UIDs without email: alphanumeric strings (e.g., "hHSWsbZ8xORF2DQLDsww31VeeSV2")
 */
function isAnonymousUserId(userId) {
    if (!userId) return true;
    // GA4 client ID pattern: digits.digits
    if (/^\d+\.\d+$/.test(userId)) return true;
    // Firebase UID pattern: alphanumeric, typically 20-32 characters, no @ symbol
    if (/^[a-zA-Z0-9]{20,40}$/.test(userId)) return true;
    return false;
}

/**
 * Format user display for the email column
 * Shows email if available, "Anonymous User" for anonymous IDs
 */
function formatUserDisplay(user) {
    const userId = user.user_id || '';
    const email = user.user_email || '';
    
    // If we have a valid email, show it
    if (isValidEmail(email)) {
        return {
            display: email,
            isAnonymous: false,
            cssClass: 'user-email'
        };
    }
    
    // If user_email looks like an email even if user_id is anonymous, show it
    if (email && email.includes('@')) {
        return {
            display: email,
            isAnonymous: false,
            cssClass: 'user-email'
        };
    }
    
    // Check if the user ID is anonymous (GA4 or Firebase UID without email)
    if (isAnonymousUserId(userId)) {
        return {
            display: 'Anonymous User',
            isAnonymous: true,
            cssClass: 'user-email anonymous-user'
        };
    }
    
    // Otherwise show the user ID (truncated if needed)
    return {
        display: userId.length > 25 ? userId.substring(0, 22) + '...' : userId,
        isAnonymous: false,
        cssClass: 'user-email'
    };
}

/**
 * Format apps_used array into compact display (LS, BS, MM, DE, etc.)
 */
function formatAppsUsed(apps) {
    if (!apps || apps.length === 0) return '-';

    const appAbbreviations = {
        'lendsight_report': 'LS',
        'bizsight_report': 'BS',
        'branchsight_report': 'BR',
        'mergermeter_report': 'MM',
        'dataexplorer_area_report': 'DE',
        'dataexplorer_lender_report': 'DE'
    };

    const appFullNames = {
        'lendsight_report': 'LendSight',
        'bizsight_report': 'BizSight',
        'branchsight_report': 'BranchSight',
        'mergermeter_report': 'MergerMeter',
        'dataexplorer_area_report': 'DataExplorer',
        'dataexplorer_lender_report': 'DataExplorer'
    };

    // Get unique abbreviations (DE appears twice but should show once)
    const seen = new Set();
    const abbrevs = [];
    const fullNames = [];

    apps.forEach(function(app) {
        const abbr = appAbbreviations[app] || app.substring(0, 2).toUpperCase();
        if (!seen.has(abbr)) {
            seen.add(abbr);
            abbrevs.push(abbr);
            fullNames.push(appFullNames[app] || app);
        }
    });

    const tooltip = fullNames.join(', ');
    return '<span class="apps-used" title="' + escapeHtml(tooltip) + '">' + abbrevs.join(' | ') + '</span>';
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
        const userDisplay = formatUserDisplay(user);
        const userType = user.user_type || '-';
        const org = user.organization_name || '-';
        const reports = user.total_reports || 0;
        const appsUsed = formatAppsUsed(user.apps_used);
        const lastActivity = formatDate(user.last_activity);

        const row = $('<tr class="clickable-row">')
            .attr('data-user-id', userId)
            .addClass(selectedUserId === userId ? 'selected' : '')
            .append('<td title="' + escapeHtml(userId) + '"><div class="' + userDisplay.cssClass + '">' + escapeHtml(userDisplay.display) + '</div></td>')
            .append('<td class="org-cell">' + escapeHtml(org) + '</td>')
            .append('<td>' + (userType !== '-' ? '<span class="user-type-badge ' + userType + '">' + escapeHtml(userType) + '</span>' : '-') + '</td>')
            .append('<td><strong>' + formatNumber(reports) + '</strong></td>')
            .append('<td>' + appsUsed + '</td>')
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
    const userDisplayInfo = formatUserDisplay(user);
    $('#detail-user-id').text(userDisplayInfo.display);
    if (userDisplayInfo.isAnonymous) {
        $('#detail-user-id').addClass('anonymous-user');
    } else {
        $('#detail-user-id').removeClass('anonymous-user');
    }

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
