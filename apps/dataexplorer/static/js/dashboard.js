/**
 * DataExplorer Dashboard JavaScript
 * Handles tab navigation, filters, API calls, and data visualization
 */

// Global debug flag - set to true to enable console logging
const DEBUG = false;

// Debug logging helpers
function debugLog(...args) {
    if (DEBUG) {
        console.log('[DataExplorer]', ...args);
    }
}

function debugWarn(...args) {
    if (DEBUG) {
        console.warn('[DataExplorer]', ...args);
    }
}

function debugError(...args) {
    if (DEBUG) {
        console.error('[DataExplorer]', ...args);
    }
}

// Number formatting functions
function formatNumber(num) {
    // Format: #,### (numbers with thousands separators, no decimals)
    if (num === null || num === undefined || isNaN(num)) return '0';
    return Math.round(num).toLocaleString('en-US');
}

function formatCurrency(num) {
    // Format: $#,### (currency with thousands separators, no decimals)
    if (num === null || num === undefined || isNaN(num)) return '$0';
    return '$' + Math.round(num).toLocaleString('en-US');
}

function formatPercentage(num) {
    // Format: ##.##% (percentage with 2 decimal places)
    // num can be a decimal (0.15) or already a percentage (15)
    if (num === null || num === undefined || isNaN(num)) return '0.00%';
    // If num is less than 1, assume it's a decimal (0.15 = 15%)
    // If num is >= 1, assume it's already a percentage (15 = 15%)
    const percentage = num < 1 ? num * 100 : num;
    return percentage.toFixed(2) + '%';
}

// Default filters storage (can be saved to localStorage)
let defaultFilters = {
    loanPurpose: ['1', '2', '3'], // Home Purchase, Home Improvement/Equity, Refinance (always all three)
    actionTaken: ['1'],
    occupancyType: ['1'],
    totalUnits: ['1', '2', '3', '4'], // Always 1-4 units (hardcoded, not user-configurable)
    constructionMethod: ['1'],
    excludeReverseMortgages: true
};

// Load default filters from localStorage if available (must be called before DashboardState initialization)
function loadDefaultFilters() {
    const saved = localStorage.getItem('dataexplorer_default_filters');
    if (saved) {
        try {
            const parsed = JSON.parse(saved);
            // Merge saved filters with defaults, but ensure loanPurpose uses the new default (all three purposes)
            // This allows other saved filters to persist while updating loanPurpose to the new default
            defaultFilters = {
                ...defaultFilters,
                ...parsed,
                loanPurpose: ['1', '2', '3'] // Always use the new default for loan purpose
            };
        } catch (e) {
            console.warn('Could not parse saved default filters:', e);
        }
    }
}

// Save default filters to localStorage
function saveDefaultFiltersToStorage() {
    localStorage.setItem('dataexplorer_default_filters', JSON.stringify(defaultFilters));
}

// Update default filters UI with current default values
function updateDefaultFiltersUI(isLender = false) {
    const prefix = isLender ? '-lender' : '';
    
    // Populate default filters UI with current defaultFilters values
    // Note: Loan purpose is always ['1', '2', '3'] and total units is always ['1', '2', '3', '4'] - not user-configurable
    $(`#default-action-taken${prefix}`).val(defaultFilters.actionTaken).trigger('change');
    $(`#default-occupancy-type${prefix}`).val(defaultFilters.occupancyType).trigger('change');
    $(`#default-construction-method${prefix}`).val(defaultFilters.constructionMethod).trigger('change');
    $(`#default-exclude-reverse${prefix}`).prop('checked', defaultFilters.excludeReverseMortgages);
}

// Save default filters from UI to defaultFilters object
function saveDefaultFilters(isLender = false) {
    const prefix = isLender ? '-lender' : '';
    
    // Read values from UI (loan purpose is always ['1', '2', '3'] and total units is always ['1', '2', '3', '4'] - not user-configurable)
    defaultFilters.loanPurpose = ['1', '2', '3']; // Always all three purposes
    defaultFilters.totalUnits = ['1', '2', '3', '4']; // Always 1-4 units
    defaultFilters.actionTaken = $(`#default-action-taken${prefix}`).val() || ['1'];
    defaultFilters.occupancyType = $(`#default-occupancy-type${prefix}`).val() || ['1'];
    defaultFilters.constructionMethod = $(`#default-construction-method${prefix}`).val() || ['1'];
    defaultFilters.excludeReverseMortgages = $(`#default-exclude-reverse${prefix}`).prop('checked') !== false;
    
    // Save to localStorage
    saveDefaultFiltersToStorage();
    
    // Update DashboardState with new defaults (loan purpose and total units are always hardcoded)
    if (isLender) {
        DashboardState.lenderFilters.hmdaFilters = {
            loanPurpose: ['1', '2', '3'], // Always all three purposes
            actionTaken: defaultFilters.actionTaken,
            occupancyType: defaultFilters.occupancyType,
            totalUnits: ['1', '2', '3', '4'], // Always 1-4 units
            constructionMethod: defaultFilters.constructionMethod,
            excludeReverseMortgages: defaultFilters.excludeReverseMortgages
        };
    } else {
        DashboardState.areaFilters.hmdaFilters = {
            loanPurpose: ['1', '2', '3'], // Always all three purposes
            actionTaken: defaultFilters.actionTaken,
            occupancyType: defaultFilters.occupancyType,
            totalUnits: ['1', '2', '3', '4'], // Always 1-4 units
            constructionMethod: defaultFilters.constructionMethod,
            excludeReverseMortgages: defaultFilters.excludeReverseMortgages
        };
    }
    
    // Show success message
    showSuccess('Default filters saved successfully!');
}

// Load defaults immediately (before DashboardState initialization)
loadDefaultFilters();

// Global state
const DashboardState = {
    currentTab: 'area-analysis',
    currentDataType: 'hmda',
    areaFilters: {
        dataType: 'hmda',
        geoType: 'county',
        geoids: [],
        years: [],
        hmdaFilters: {
            loanPurpose: ['1', '2', '3'], // Always all three purposes: Home Purchase, Refinance, Home Equity
            actionTaken: defaultFilters.actionTaken,
            occupancyType: defaultFilters.occupancyType,
            totalUnits: ['1', '2', '3', '4'], // Always 1-4 units
            constructionMethod: defaultFilters.constructionMethod,
            excludeReverseMortgages: defaultFilters.excludeReverseMortgages
        }
    },
    lenderFilters: {
        dataType: 'hmda',
        geoType: 'county',
        geoids: [],
        years: [],
        subjectLender: null,
        enablePeerComparison: true,
        hmdaFilters: {
            loanPurpose: ['1', '2', '3'], // Always all three purposes: Home Purchase, Refinance, Home Equity
            actionTaken: defaultFilters.actionTaken,
            occupancyType: defaultFilters.occupancyType,
            totalUnits: ['1', '2', '3', '4'], // Always 1-4 units
            constructionMethod: defaultFilters.constructionMethod,
            excludeReverseMortgages: defaultFilters.excludeReverseMortgages
        }
    },
    charts: {},
    currentLenderAnalysis: {
        rawResults: null,
        assessmentAreas: null,
        subjectLenderName: null
    }
};

// Initialize on page load
$(document).ready(function() {
    loadDefaultFilters(); // Load saved default filters
    initializeTabs();
    initializeAreaAnalysis();
    initializeLenderTargeting();
    loadInitialData();
});

// Lender lookup state
let lenderLookupState = {
    isLookingUp: false,
    confirmedLender: null
};

// Tab Navigation
function initializeTabs() {
    $('.tab-btn').on('click', function() {
        const tabId = $(this).data('tab');
        switchTab(tabId);
    });
}

function switchTab(tabId) {
    // Update UI
    $('.tab-btn').removeClass('active');
    $(`.tab-btn[data-tab="${tabId}"]`).addClass('active');
    $('.tab-content').removeClass('active');
    $(`#${tabId}`).addClass('active');
    
    // Load lender names when lender analysis tab is shown
    if (tabId === 'lender-analysis') {
        if ($('#lender-name-select option').length <= 1) {
            loadHmdaLenderNames();
        }
    }
    
    DashboardState.currentTab = tabId;
}

// Area Analysis Tab
function setAreaAnalysisYears() {
    // Automatically set years to the last 5 years available based on data type
    const dataType = DashboardState.areaFilters.dataType;
    let years = [];
    
    if (dataType === 'hmda') {
        years = [2020, 2021, 2022, 2023, 2024]; // Last 5 years
    } else if (dataType === 'sb') {
        years = [2020, 2021, 2022, 2023, 2024]; // Last 5 years
    } else if (dataType === 'branches') {
        years = [2020, 2021, 2022, 2023, 2024, 2025]; // Last 5-6 years (2020-2024 or 2021-2025)
        // For branches, use the most recent 5 years (2021-2025 if 2025 is available, otherwise 2020-2024)
        if (years.length > 5) {
            years = years.slice(-5); // Take last 5: [2021, 2022, 2023, 2024, 2025]
        }
    }
    
    DashboardState.areaFilters.years = years;
    debugLog('Auto-set Area Analysis years to:', years, 'for data type:', dataType);
}

function initializeAreaAnalysis() {
    // Data type selection
    $('input[name="data-type"]').on('change', function() {
        DashboardState.areaFilters.dataType = $(this).val();
        updateDataTypeFilters('area');
        // Automatically set years to last 5 years for Area Analysis
        setAreaAnalysisYears();
    });
    
    // Set initial years to last 5 years
    setAreaAnalysisYears();
    
    // Geography type tabs
    $('.geo-tab-btn[data-geo-type]').on('click', function() {
        const geoType = $(this).data('geo-type');
        $('.geo-tab-btn').removeClass('active');
        $(this).addClass('active');
        $('.geo-selector').removeClass('active');
        $(`#geo-${geoType}-selector`).addClass('active');
        DashboardState.areaFilters.geoType = geoType;
        // Show loading when switching tabs
        if (geoType === 'metro') {
            showGeographyLoading('Loading metro areas...');
        } else if (geoType === 'county') {
            showGeographyLoading('Loading counties...');
        } else if (geoType === 'state') {
            showGeographyLoading('Loading states...');
        }
        loadGeographyOptions('area');
    });
    
    // State filter for counties
    $('#state-filter-area').on('change', function() {
        loadCounties('area', $(this).val());
    });
    
    // County selection
    $('#county-select-area').select2({
        placeholder: 'Select counties...',
        allowClear: true
    }).on('change', function() {
        DashboardState.areaFilters.geoids = $(this).val() || [];
        updateLenderOptions('area');
    });
    
    // Metro selection
    $('#metro-select-area').select2({
        placeholder: 'Select metro areas...',
        allowClear: true
    }).on('change', function() {
        const metroCodes = $(this).val() || [];
        if (metroCodes.length > 0) {
            loadCountiesForGeography('metro', metroCodes);
        } else {
            $('#metro-counties-display').hide();
            DashboardState.areaFilters.geoids = [];
        }
        updateLenderOptions('area');
    });
    
    // State selection
    $('#state-select-area').select2({
        placeholder: 'Select states...',
        allowClear: true
    }).on('change', function() {
        const stateCodes = $(this).val() || [];
        if (stateCodes.length > 0) {
            loadCountiesForGeography('state', stateCodes);
        } else {
            $('#state-counties-display').hide();
            DashboardState.areaFilters.geoids = [];
        }
        updateLenderOptions('area');
    });
    
    // County checkbox handlers for metro/state
    $(document).on('change', '.county-checkbox', function() {
        updateGeoidsFromCounties();
    });
    
    // Select All / Deselect All buttons
    $(document).on('click', '.btn-select-all-counties', function() {
        const context = $(this).data('context');
        $(`#${context}-counties-checkboxes .county-checkbox`).prop('checked', true);
        updateGeoidsFromCounties();
    });
    
    $(document).on('click', '.btn-deselect-all-counties', function() {
        const context = $(this).data('context');
        $(`#${context}-counties-checkboxes .county-checkbox`).prop('checked', false);
        updateGeoidsFromCounties();
    });
    
    // Year quick select
    $('.quick-select-btn').on('click', function() {
        const yearsType = $(this).data('years');
        selectYears('area', yearsType);
    });
    
    // Filters toggle button
    $('#filters-toggle-area').on('click', function() {
        const content = $('#filters-content-area');
        const isVisible = content.is(':visible');
        content.slideToggle(300);
        $(this).toggleClass('active', !isVisible);
    });
    
    // HMDA filters (loan purpose is always all three: Home Purchase, Refinance, Home Equity)
    $('#action-taken-area, #occupancy-type-area, #total-units-area, #construction-method-area').select2({
        placeholder: 'Select options...',
        allowClear: true
    }).on('change', function() {
        updateHmdaFilters('area');
    });
    
    $('#exclude-reverse-area').on('change', function() {
        updateHmdaFilters('area');
    });
    
    // Set initial filter values from defaults (loan purpose is always ['1', '2', '3'], total units is always ['1', '2', '3', '4'])
    DashboardState.areaFilters.hmdaFilters.loanPurpose = ['1', '2', '3'];
    DashboardState.areaFilters.hmdaFilters.totalUnits = ['1', '2', '3', '4'];
    $('#action-taken-area').val(defaultFilters.actionTaken).trigger('change');
    $('#occupancy-type-area').val(defaultFilters.occupancyType).trigger('change');
    $('#total-units-area').val(['1', '2', '3', '4']).trigger('change'); // Always 1-4 units
    $('#construction-method-area').val(defaultFilters.constructionMethod).trigger('change');
    $('#exclude-reverse-area').prop('checked', defaultFilters.excludeReverseMortgages);
    
    // Analyze button
    $('#analyze-area-btn').on('click', function() {
        analyzeArea();
    });
    
    // Clear filters
    $('#clear-area-filters-btn').on('click', function() {
        clearAreaFilters();
    });
    
    // Default filters toggle (expandable section)
    $(document).on('click', '#default-filters-toggle-btn, #default-filters-toggle-btn-lender', function() {
        const toggle = $(this);
        const content = toggle.next('.default-filters-content');
        const isVisible = content.is(':visible');
        
        // If opening, populate with current default values
        if (!isVisible) {
            updateDefaultFiltersUI($(this).attr('id').includes('lender'));
        }
        
        content.slideToggle(300);
        toggle.toggleClass('active', !isVisible);
    });
    
    // Save default filters
    $(document).on('click', '#save-default-filters-btn, #save-default-filters-btn-lender', function() {
        const isLender = $(this).attr('id').includes('lender');
        saveDefaultFilters(isLender);
    });
    
    // Initialize Select2 for default filters (area analysis) - loan purpose and total units are not user-configurable
    $('#default-action-taken, #default-occupancy-type, #default-construction-method').select2({
        width: '100%',
        placeholder: 'Select options...',
        allowClear: true
    });
    
    // Populate default filters UI with current values (area analysis)
    updateDefaultFiltersUI(false);
    
    // Initialize Select2 for default filters (lender analysis) - loan purpose and total units are not user-configurable
    $('#default-action-taken-lender, #default-occupancy-type-lender, #default-construction-method-lender').select2({
        width: '100%',
        placeholder: 'Select options...',
        allowClear: true
    });
    
    // Populate default filters UI with current values (lender analysis)
    updateDefaultFiltersUI(true);
    
    // Export all tables to Excel
    $('#export-area-btn').on('click', function() {
        exportAllTablesToExcel();
    });
    
    // Export lender analysis to Excel (use document.on for dynamically created elements)
    $(document).on('click', '#export-lender-btn', function() {
        exportLenderAnalysisToExcel();
    });
}

// Lender Targeting Tab
function initializeLenderTargeting() {
    // Data type selection
    $('input[name="data-type-lender"]').on('change', function() {
        DashboardState.lenderFilters.dataType = $(this).val();
        updateDataTypeFilters('lender');
        // Clear lender selection and geography when data type changes
        clearLenderSelection();
        // Update geography method options
        updateGeographyMethodOptions();
        
        // Load HMDA lenders if HMDA is selected
        const dataType = $(this).val();
        if (dataType === 'hmda') {
            loadHmdaLenderNames();
        }
    });
    
    // Initialize geography method options on page load
    updateGeographyMethodOptions();
    
    // Geography type tabs
    $('.geo-tab-btn[data-geo-type]').on('click', function() {
        const geoType = $(this).data('geo-type');
        if ($(this).closest('#lender-analysis').length) {
            $('.geo-tab-btn').not($(this)).removeClass('active');
            $(this).addClass('active');
            $(`#lender-analysis .geo-selector`).removeClass('active');
            $(`#geo-${geoType}-selector-lender`).addClass('active');
            DashboardState.lenderFilters.geoType = geoType;
            loadGeographyOptions('lender');
        }
    });
    
    // State filter for counties
    $('#state-filter-lender').on('change', function() {
        loadCounties('lender', $(this).val());
    });
    
    // Note: County and metro selectors for lender targeting are now replaced by target counties
    // These are kept for backward compatibility but not actively used in the new flow
    
    // Year quick select
    $('#lender-analysis .quick-select-btn').on('click', function() {
        const yearsType = $(this).data('years');
        selectYears('lender', yearsType);
    });
    
    // Load lenders when lender analysis tab is shown
    // This will be triggered by switchTab function
    
    // Lender name dropdown selection
    $('#lender-name-select').on('change', function() {
        const selectedOption = $(this).find('option:selected');
        const lenderName = selectedOption.text();
        const lenderLei = selectedOption.val();
        
        if (lenderLei && lenderName) {
            // Populate LEI immediately
            $('#lender-lei-display').text(lenderLei);
            $('#lender-rssd-display').html('<em>Loading...</em>');
            $('#lender-respondent-id-display').html('<em>Loading...</em>');
            $('#lender-details-display').show();
            $('#confirm-lender-btn').prop('disabled', false);
            
            // Look up associated identifiers (RSSD and Business Respondent ID)
            $.get(`/api/lender/identifiers/${lenderLei}`)
                .done(function(response) {
                    if (response.success && response.data) {
                        const data = response.data;
                        
                        // Update RSSD display
                        if (data.rssd) {
                            $('#lender-rssd-display').text(data.rssd).css('color', '#000');
                        } else {
                            $('#lender-rssd-display').html('<em>Not available</em>').css('color', '#999');
                        }
                        
                        // Update Business Respondent ID display
                        if (data.respondent_id) {
                            $('#lender-respondent-id-display').text(data.respondent_id).css('color', '#000');
                        } else {
                            $('#lender-respondent-id-display').html('<em>Not available</em>').css('color', '#999');
                        }
                        
                        // Store selected lender info with all identifiers
                        lenderLookupState.pendingLender = {
                            name: lenderName,
                            lei: lenderLei,
                            rssd: data.rssd || null,
                            respondent_id: data.respondent_id || null,
                            city: data.city || null,
                            state: data.state || null,
                            lender_type: data.lender_type || null,
                            data_type: 'hmda'
                        };
                    } else {
                        // If lookup fails, still store basic info
                        $('#lender-rssd-display').html('<em>Not available</em>').css('color', '#999');
                        $('#lender-respondent-id-display').html('<em>Not available</em>').css('color', '#999');
                        lenderLookupState.pendingLender = {
                            name: lenderName,
                            lei: lenderLei,
                            rssd: null,
                            respondent_id: null,
                            city: null,
                            state: null,
                            lender_type: null,
                            data_type: 'hmda'
                        };
                    }
                })
                .fail(function() {
                    // If lookup fails, still store basic info
                    $('#lender-rssd-display').html('<em>Not available</em>').css('color', '#999');
                    $('#lender-respondent-id-display').html('<em>Not available</em>').css('color', '#999');
                    lenderLookupState.pendingLender = {
                        name: lenderName,
                        lei: lenderLei,
                        rssd: null,
                        respondent_id: null,
                        data_type: 'hmda'
                    };
                });
        } else {
            $('#lender-details-display').hide();
            $('#confirm-lender-btn').prop('disabled', true);
            lenderLookupState.pendingLender = null;
        }
    });
    
    // Confirm lender button
    $('#confirm-lender-btn').on('click', function() {
        confirmLenderSelection();
    });
    
    // Change lender button
    $('#change-lender-btn').on('click', function() {
        clearLenderSelection();
    });
    
    // Branch Locations button
    // Geography method toggle buttons
    $('.geo-method-toggle-btn').on('click', function() {
        const method = $(this).data('method');
        
        // Update button styles
        $('.geo-method-toggle-btn').css({
            'background': '#e0e0e0',
            'color': '#333'
        });
        $(this).css({
            'background': 'var(--ncrc-secondary-blue)',
            'color': 'white'
        });
        
        // Show/hide appropriate sections
        if (method === 'manual') {
            $('#manual-geography-group').show();
            $('#auto-selection-group').hide();
        } else if (method === 'branches') {
            $('#manual-geography-group').hide();
            $('#auto-selection-group').show();
            // Trigger branch location generation if lender is confirmed
            if (lenderLookupState.confirmedLender && lenderLookupState.confirmedLender.rssd) {
                generateGeographyFromBranches();
            } else {
                $('#auto-selection-message').html('<i class="fas fa-info-circle"></i> Please confirm a lender with branch data (RSSD) first.');
            }
        } else if (method === 'lending_activity') {
            $('#manual-geography-group').hide();
            $('#auto-selection-group').show();
            // Trigger lending activity generation if lender is confirmed
            if (lenderLookupState.confirmedLender && lenderLookupState.confirmedLender.lei) {
                generateGeographyFromLendingActivity();
            } else {
                $('#auto-selection-message').html('<i class="fas fa-info-circle"></i> Please confirm a lender with HMDA data (LEI) first.');
            }
        }
    });
    
    // Back to manual button
    $('#btn-back-to-manual').on('click', function() {
        $('.geo-method-toggle-btn[data-method="manual"]').click();
    });
    
    // Generate geography from branches
    function generateGeographyFromBranches() {
        if (!lenderLookupState.confirmedLender || !lenderLookupState.confirmedLender.rssd) {
            showError('RSSD ID is not available for this lender. Branch locations cannot be determined without an RSSD.');
            return;
        }
        
        showLoading();
        $.ajax({
            url: '/api/lender/generate-assessment-areas-from-branches',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                rssd: lenderLookupState.confirmedLender.rssd,
                year: 2025,
                min_deposit_share: 0.01
            })
        })
        .done(function(response) {
            hideLoading();
            if (response.success && response.counties) {
                // Populate auto-county-select
                const countyOptions = response.counties.map(c => ({
                    id: c.geoid5,
                    text: `${c.county_name || c.geoid5}, ${c.state_name || ''}`
                }));
                
                // Destroy existing Select2 if it exists
                if ($('#auto-county-select').hasClass('select2-hidden-accessible')) {
                    $('#auto-county-select').select2('destroy');
                }
                
                $('#auto-county-select').empty();
                countyOptions.forEach(opt => {
                    $('#auto-county-select').append(new Option(opt.text, opt.id, true, true));
                });
                
                // Initialize Select2
                $('#auto-county-select').select2({
                    placeholder: 'Select counties...',
                    allowClear: true,
                    width: '100%'
                });
                
                $('#auto-county-select').prop('disabled', false);
                
                DashboardState.lenderFilters.geoids = response.counties.map(c => c.geoid5);
                // Store assessment areas for Excel export
                DashboardState.currentLenderAnalysis.assessmentAreas = {
                    counties: response.counties
                };
                $('#auto-selection-message').html(`<i class="fas fa-check-circle"></i> Found ${response.counties.length} counties based on branch locations.`);
            } else {
                showError('No counties found for this lender\'s branch network.');
            }
        })
        .fail(function(xhr) {
            hideLoading();
            showError('Failed to generate geography from branches: ' + (xhr.responseJSON?.error || 'Unknown error'));
        });
    }
    
    // Generate geography from lending activity
    function generateGeographyFromLendingActivity() {
        if (!lenderLookupState.confirmedLender || !lenderLookupState.confirmedLender.lei) {
            showError('LEI is not available for this lender. Lending activity cannot be determined without an LEI.');
            return;
        }
        
        showLoading();
        $.ajax({
            url: '/api/lender/target-counties',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                lender_id: lenderLookupState.confirmedLender.lei,
                data_type: 'hmda',
                selection_method: 'lending_activity',
                years: [2020, 2021, 2022, 2023, 2024]
            })
        })
        .done(function(response) {
            hideLoading();
            if (response.success && response.data) {
                // Populate auto-county-select
                const countyOptions = response.data.map(c => ({
                    id: c.geoid5,
                    text: `${c.county_name || c.geoid5}, ${c.state_name || ''}`
                }));
                
                // Destroy existing Select2 if it exists
                if ($('#auto-county-select').hasClass('select2-hidden-accessible')) {
                    $('#auto-county-select').select2('destroy');
                }
                
                $('#auto-county-select').empty();
                countyOptions.forEach(opt => {
                    $('#auto-county-select').append(new Option(opt.text, opt.id, true, true));
                });
                
                // Initialize Select2
                $('#auto-county-select').select2({
                    placeholder: 'Select counties...',
                    allowClear: true,
                    width: '100%'
                });
                
                $('#auto-county-select').prop('disabled', false);
                
                DashboardState.lenderFilters.geoids = response.data.map(c => c.geoid5);
                // Store assessment areas for Excel export
                DashboardState.currentLenderAnalysis.assessmentAreas = {
                    counties: response.data
                };
                $('#auto-selection-message').html(`<i class="fas fa-check-circle"></i> Found ${response.data.length} counties based on lending activity (≥1% threshold).`);
            } else {
                showError('No counties found for this lender\'s lending activity.');
            }
        })
        .fail(function(xhr) {
            hideLoading();
            showError('Failed to generate geography from lending activity: ' + (xhr.responseJSON?.error || 'Unknown error'));
        });
    }
    
    // Auto-selected counties
    $('#auto-county-select').select2({
        placeholder: 'Select counties...',
        allowClear: true
    }).on('change', function() {
        DashboardState.lenderFilters.geoids = $(this).val() || [];
    });
    
    // Manual geography selectors
    $('#county-select-lender').select2({
        placeholder: 'Select counties...',
        allowClear: true
    }).on('change', function() {
        updateManualGeographySelection();
    });
    
    $('#metro-select-lender').select2({
        placeholder: 'Select metro areas...',
        allowClear: true
    }).on('change', function() {
        updateManualGeographySelection();
    });
    
    $('#state-select-lender').select2({
        placeholder: 'Select states...',
        allowClear: true
    }).on('change', function() {
        updateManualGeographySelection();
    });
    
    // State filter for counties
    $('#state-filter-lender').on('change', function() {
        loadCounties('lender', $(this).val());
    });
    
    // Peer comparison toggle
    $('#enable-peer-comparison').on('change', function() {
        DashboardState.lenderFilters.enablePeerComparison = $(this).is(':checked');
    });
    
    // Filters toggle button
    $('#filters-toggle-lender').on('click', function() {
        const content = $('#filters-content-lender');
        const isVisible = content.is(':visible');
        content.slideToggle(300);
        $(this).toggleClass('active', !isVisible);
    });
    
    // HMDA filters
    // HMDA filters (loan purpose is always all three: Home Purchase, Refinance, Home Equity)
    $('#action-taken-lender, #occupancy-type-lender, #total-units-lender, #construction-method-lender').select2({
        placeholder: 'Select options...',
        allowClear: true
    }).on('change', function() {
        updateHmdaFilters('lender');
    });
    
    $('#exclude-reverse-lender').on('change', function() {
        updateHmdaFilters('lender');
    });
    
    // Set initial filter values from defaults (loan purpose is always ['1', '2', '3'], total units is always ['1', '2', '3', '4'])
    DashboardState.lenderFilters.hmdaFilters.loanPurpose = ['1', '2', '3'];
    DashboardState.lenderFilters.hmdaFilters.totalUnits = ['1', '2', '3', '4'];
    $('#action-taken-lender').val(defaultFilters.actionTaken).trigger('change');
    $('#occupancy-type-lender').val(defaultFilters.occupancyType).trigger('change');
    $('#total-units-lender').val(['1', '2', '3', '4']).trigger('change'); // Always 1-4 units
    $('#construction-method-lender').val(defaultFilters.constructionMethod).trigger('change');
    $('#exclude-reverse-lender').prop('checked', defaultFilters.excludeReverseMortgages);
    
    // Analyze button
    $('#analyze-lender-btn').on('click', function() {
        analyzeLender();
    });
    
    // Clear filters
    $('#clear-lender-filters-btn').on('click', function() {
        clearLenderFilters();
    });
}

// Load initial data
function loadInitialData() {
    // Sequence API calls to reduce parallel BigQuery connections
    // Load states first (fastest), then counties, then metros
    loadStates().then(function() {
        // Load counties for both contexts after states are loaded
        return Promise.all([
            loadCounties('area'),
            loadCounties('lender')
        ]);
    }).then(function() {
        // Load metros last
        return loadMetros();
    }).catch(function(error) {
        debugError('Error loading initial data:', error);
    });
    
    // Area Analysis years are set automatically (Lender Analysis doesn't use years)
    setAreaAnalysisYears();
}

// Load geography options
function loadStates() {
    // States load quickly, so we don't show loading overlay for them
    return $.get('/api/states')
        .done(function(response) {
            if (response.success) {
                const filterOptions = '<option value="">All States</option>' +
                    response.data.map(s => `<option value="${s.code}">${s.name}</option>`).join('');
                const selectOptions = response.data.map(s => 
                    `<option value="${s.code}">${s.name}</option>`
                ).join('');
                $('#state-filter-area, #state-filter-lender').html(filterOptions);
                $('#state-select-area, #state-select-lender').html(selectOptions);
            }
        })
        .fail(function() {
            showError('Failed to load states');
        });
}

function loadCounties(context, stateCode = '') {
    const selectorMap = {
        'area': '#county-select-area',
        'lender': '#county-select-lender'
    };
    
    const selector = selectorMap[context];
    if (!selector) return $.Deferred().resolve().promise();
    
    // Only show loading for area context (where the overlay exists)
    if (context === 'area') {
        showGeographyLoading('Loading counties...');
    }
    
    const url = stateCode ? `/api/counties?state_code=${stateCode}` : '/api/counties';
    
    return $.get(url)
        .done(function(response) {
            if (response.success) {
                const options = response.data.map(c => 
                    `<option value="${c.geoid5}">${c.county_state}</option>`
                ).join('');
                $(selector).html(options).trigger('change');
            }
            if (context === 'area') {
                hideGeographyLoading();
            }
        })
        .fail(function() {
            showError('Failed to load counties');
            if (context === 'area') {
                hideGeographyLoading();
            }
        });
}

function loadMetros() {
    showGeographyLoading('Loading metro areas...');
    return $.get('/api/metros')
        .done(function(response) {
            if (response.success) {
                const options = response.data.map(m => 
                    `<option value="${m.code}">${m.name}</option>`
                ).join('');
                $('#metro-select-area, #metro-select-lender').html(options);
            }
            hideGeographyLoading();
        })
        .fail(function() {
            showError('Failed to load metro areas');
            hideGeographyLoading();
        });
}

function loadCountiesForGeography(geoType, codes) {
    // geoType is 'metro' or 'state'
    const payload = {};
    if (geoType === 'metro') {
        payload.metro_codes = codes;
    } else if (geoType === 'state') {
        payload.state_codes = codes;
    }
    
    // Show loading overlay immediately using requestAnimationFrame to avoid forced reflow
    const loadingMessage = geoType === 'metro' 
        ? 'Loading counties for metro area...' 
        : 'Loading counties for state...';
    
    // Use requestAnimationFrame to show overlay after current frame, avoiding forced reflow
    requestAnimationFrame(function() {
        showGeographyLoading(loadingMessage);
    });
    
    $.ajax({
        url: '/api/geography/counties',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(payload)
    })
    .done(function(response) {
        if (response.success && response.data) {
            const counties = response.data;
            const displayId = `${geoType}-counties-display`;
            const checkboxesId = `${geoType}-counties-checkboxes`;
            
            // Show the display
            $(`#${displayId}`).show();
            
            // Build checkboxes HTML
            let html = '<div class="counties-checkbox-container">';
            counties.forEach(county => {
                html += `
                    <div class="county-checkbox-item">
                        <input type="checkbox" 
                               class="county-checkbox" 
                               id="county-${geoType}-${county.geoid5}" 
                               value="${county.geoid5}" 
                               data-geoid="${county.geoid5}"
                               checked>
                        <label for="county-${geoType}-${county.geoid5}">
                            ${county.county_state || `${county.name}, ${county.state}`}
                        </label>
                    </div>
                `;
            });
            html += '</div>';
            
            $(`#${checkboxesId}`).html(html);
            
            // Update geoids with all counties selected by default
            DashboardState.areaFilters.geoids = counties.map(c => c.geoid5);
            updateLenderOptions('area');
        }
        hideGeographyLoading();
    })
    .fail(function(xhr) {
        showError('Failed to load counties: ' + (xhr.responseJSON?.error || 'Unknown error'));
        hideGeographyLoading();
    });
}

function updateGeoidsFromCounties() {
    // Get all checked county checkboxes
    const checkedCounties = $('.county-checkbox:checked').map(function() {
        return $(this).val();
    }).get();
    
    DashboardState.areaFilters.geoids = checkedCounties;
    updateLenderOptions('area');
}

function loadGeographyOptions(context) {
    if (context === 'area') {
        if (DashboardState.areaFilters.geoType === 'county') {
            loadCounties('area');
        } else if (DashboardState.areaFilters.geoType === 'metro') {
            loadMetros();
        } else if (DashboardState.areaFilters.geoType === 'state') {
            loadStates();
            // States load quickly, hide loading after a brief delay
            setTimeout(hideGeographyLoading, 500);
        }
    } else if (context === 'lender') {
        if (DashboardState.lenderFilters.geoType === 'county') {
            loadCounties('lender');
        } else if (DashboardState.lenderFilters.geoType === 'metro') {
            loadMetros();
        } else if (DashboardState.lenderFilters.geoType === 'state') {
            loadStates();
        }
    }
}

// Update year selector
function updateYearSelector(context, defaultToLast5 = true) {
    let years = [];
    
    if (context === 'area') {
        const dataType = DashboardState.areaFilters.dataType;
        if (dataType === 'hmda') {
            years = [2020, 2021, 2022, 2023, 2024]; // Only 2020-2024
        } else if (dataType === 'sb') {
            years = [2020, 2021, 2022, 2023, 2024]; // Only 2020-2024
        } else if (dataType === 'branches') {
            years = [2020, 2021, 2022, 2023, 2024, 2025]; // Most recent 5-6 years
        }
    } else if (context === 'lender') {
        const dataType = DashboardState.lenderFilters.dataType;
        if (dataType === 'hmda') {
            years = [2020, 2021, 2022, 2023, 2024]; // Only 2020-2024
        } else if (dataType === 'sb') {
            years = [2020, 2021, 2022, 2023, 2024]; // Only 2020-2024
        } else if (dataType === 'branches') {
            years = [2020, 2021, 2022, 2023, 2024, 2025]; // Most recent 5-6 years
        }
    } else if (context === 'mortgage') {
        years = [2020, 2021, 2022, 2023, 2024]; // Only 2020-2024
    } else if (context === 'sb') {
        years = [2020, 2021, 2022, 2023, 2024]; // Only 2020-2024
    }
    
    const selectorMap = {
        'area': '#year-selector-area',
        'lender': '#year-selector-lender',
        'mortgage': '#year-selector-mortgage',
        'sb': '#year-selector-sb'
    };
    
    const selector = selectorMap[context];
    if (!selector) return;
    
    const html = years.map(year => `
        <div class="year-checkbox-item">
            <input type="checkbox" id="year-${context}-${year}" value="${year}" class="year-checkbox">
            <label for="year-${context}-${year}">${year}</label>
        </div>
    `).join('');
    
    $(selector).html(html);
    
    // Attach change handlers
    $(`${selector} .year-checkbox`).on('change', function() {
        updateSelectedYears(context);
    });
    
    // Default to last 5 years instead of all years
    const checkboxes = $(`${selector} .year-checkbox`);
    if (defaultToLast5 && checkboxes.length >= 5) {
        checkboxes.prop('checked', false);
        checkboxes.slice(-5).prop('checked', true);
    } else {
        // Select all by default if less than 5 years available
        checkboxes.prop('checked', true);
    }
    updateSelectedYears(context);
}

function selectYears(context, yearsType) {
    const selectorMap = {
        'area': '#year-selector-area',
        'lender': '#year-selector-lender',
        'mortgage': '#year-selector-mortgage',
        'sb': '#year-selector-sb'
    };
    
    const selector = selectorMap[context];
    if (!selector) return;
    
    const checkboxes = $(`${selector} .year-checkbox`);
    
    if (yearsType === 'all') {
        checkboxes.prop('checked', true);
    } else if (yearsType === 'recent3') {
        checkboxes.prop('checked', false);
        checkboxes.slice(-3).prop('checked', true);
    } else if (yearsType === 'recent5') {
        checkboxes.prop('checked', false);
        // Select last 5, or all if less than 5 available
        const count = Math.min(5, checkboxes.length);
        checkboxes.slice(-count).prop('checked', true);
    }
    
    updateSelectedYears(context);
}

function updateSelectedYears(context) {
    const selectorMap = {
        'area': '#year-selector-area',
        'lender': '#year-selector-lender',
        'mortgage': '#year-selector-mortgage',
        'sb': '#year-selector-sb'
    };
    
    const selector = selectorMap[context];
    if (!selector) return;
    
    const selected = $(`${selector} .year-checkbox:checked`).map(function() {
        return parseInt($(this).val());
    }).get();
    
    if (context === 'area') {
        DashboardState.areaFilters.years = selected;
        updateLenderOptions('area');
    } else if (context === 'lender') {
        DashboardState.lenderFilters.years = selected;
        updateLenderSelector();
    }
    // mortgage and sb contexts don't need to update state
}

// Update lender options based on filters
function updateLenderOptions(context) {
    // This would load available lenders based on current geography and year filters
    // For now, placeholder
}

function updateLenderSelector() {
    const filters = DashboardState.lenderFilters;
    
    // Load lenders based on data type only (no geography filter needed)
    showLoading();
    
    let url = '';
    if (filters.dataType === 'hmda') {
        url = '/api/lenders/hmda';
    } else if (filters.dataType === 'sb') {
        url = '/api/lenders/sb';
    } else if (filters.dataType === 'branches') {
        url = '/api/lenders/branches';
    }
    
    // Load all lenders (no geography filter)
    $.get(url, {})
        .done(function(response) {
            hideLoading();
            if (response.success) {
                const options = '<option value="">Select lender...</option>' +
                    response.data.map(l => {
                        const name = l.name || l.lei || l.rssd || l.respondent_id || l.sb_lender;
                        const id = l.lei || l.rssd || l.respondent_id || l.sb_resid;
                        return `<option value="${id}">${name}</option>`;
                    }).join('');
                $('#subject-lender-select').html(options).trigger('change');
            }
        })
        .fail(function() {
            hideLoading();
            showError('Failed to load lenders');
        });
}

// Load HMDA lender names from lenders18 table
function loadHmdaLenderNames() {
    // Don't show loading for this as it might be called during tab switch
    $.get('/api/lenders/hmda/names')
        .done(function(response) {
            if (response.success && response.data) {
                const options = '<option value="">Select a lender...</option>' +
                    response.data.map(lender => {
                        return `<option value="${lender.lei}">${lender.name}</option>`;
                    }).join('');
                
                // Destroy existing Select2 if it exists
                if ($('#lender-name-select').hasClass('select2-hidden-accessible')) {
                    $('#lender-name-select').select2('destroy');
                }
                
                // Update options
                $('#lender-name-select').html(options);
                
                // Initialize Select2
                $('#lender-name-select').select2({
                    placeholder: 'Select a lender...',
                    allowClear: true,
                    width: '100%',
                    dropdownAutoWidth: true
                });
            } else {
                showError('Failed to load lender names');
            }
        })
        .fail(function(xhr) {
            const errorMsg = xhr.responseJSON?.error || 'Error loading lender names';
            showError(errorMsg);
        });
}

// Lender lookup functions (kept for backward compatibility, but not used for HMDA)
function performLenderLookup() {
    if (lenderLookupState.isLookingUp) return;
    
    const name = $('#lender-name-input').val().trim();
    const lei = $('#lender-lei-input').val().trim();
    const rssd = $('#lender-rssd-input').val().trim();
    const respondentId = $('#lender-respondent-id-input').val().trim();
    
    // Don't lookup if all fields are empty
    if (!name && !lei && !rssd && !respondentId) {
        $('#lender-lookup-status').hide();
        $('#confirm-lender-btn').prop('disabled', true);
        return;
    }
    
    lenderLookupState.isLookingUp = true;
    $('#lender-lookup-status').hide();
    $('#confirm-lender-btn').prop('disabled', true);
    
    $.ajax({
        url: '/api/lender/lookup',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            name: name || null,
            lei: lei || null,
            rssd: rssd || null,
            respondent_id: respondentId || null
        })
    })
    .done(function(response) {
        lenderLookupState.isLookingUp = false;
        
        if (response.success && response.data) {
            const lender = response.data;
            
            // Auto-populate fields (only if they're empty or different)
            if (lender.name && !$('#lender-name-input').val()) {
                $('#lender-name-input').val(lender.name);
            }
            if (lender.lei && !$('#lender-lei-input').val()) {
                $('#lender-lei-input').val(lender.lei);
            }
            if (lender.rssd && !$('#lender-rssd-input').val()) {
                $('#lender-rssd-input').val(lender.rssd);
            }
            if (lender.respondent_id && !$('#lender-respondent-id-input').val()) {
                $('#lender-respondent-id-input').val(lender.respondent_id);
            }
            
            // Show success status
            $('#lender-lookup-status')
                .removeClass('error')
                .addClass('success')
                .html('<i class="fas fa-check-circle"></i> Lender found! Review the information and click Confirm.')
                .css({
                    'background-color': '#d4edda',
                    'color': '#155724',
                    'border': '1px solid #c3e6cb'
                })
                .show();
            
            // Enable confirm button
            $('#confirm-lender-btn').prop('disabled', false);
            
            // Store lookup result for confirmation
            lenderLookupState.pendingLender = lender;
        } else {
            // Show error status
            $('#lender-lookup-status')
                .removeClass('success')
                .addClass('error')
                .html('<i class="fas fa-exclamation-circle"></i> ' + (response.error || 'Lender not found. Please verify the identifier(s) and try again.'))
                .css({
                    'background-color': '#f8d7da',
                    'color': '#721c24',
                    'border': '1px solid #f5c6cb'
                })
                .show();
            
            $('#confirm-lender-btn').prop('disabled', true);
            lenderLookupState.pendingLender = null;
        }
    })
    .fail(function(xhr) {
        lenderLookupState.isLookingUp = false;
        const errorMsg = xhr.responseJSON?.error || 'Error looking up lender. Please try again.';
        $('#lender-lookup-status')
            .removeClass('success')
            .addClass('error')
            .html('<i class="fas fa-exclamation-circle"></i> ' + errorMsg)
            .css({
                'background-color': '#f8d7da',
                'color': '#721c24',
                'border': '1px solid #f5c6cb'
            })
            .show();
        $('#confirm-lender-btn').prop('disabled', true);
        lenderLookupState.pendingLender = null;
    });
}

function confirmLenderSelection() {
    // Use the pending lender info which should have all identifiers loaded
    const lender = lenderLookupState.pendingLender;
    
    if (!lender || !lender.lei) {
        showError('Please select a lender from the dropdown.');
        return;
    }
    
    // Store confirmed lender
    lenderLookupState.confirmedLender = lender;
    
    // Set lender ID (LEI for HMDA)
    DashboardState.lenderFilters.subjectLender = lender.lei;
    
    // Show confirmed lender info with all available identifiers
    const details = [];
    details.push('LEI: ' + lender.lei);
    if (lender.rssd) {
        details.push('RSSD: ' + lender.rssd);
    }
    if (lender.respondent_id) {
        details.push('Respondent ID: ' + lender.respondent_id);
    }
    
    // Add headquarters location if available
    if (lender.city && lender.state) {
        details.push('Headquarters: ' + lender.city + ', ' + lender.state);
    } else if (lender.city) {
        details.push('Headquarters: ' + lender.city);
    } else if (lender.state) {
        details.push('Headquarters: ' + lender.state);
    }
    
    // Add lender type if available
    if (lender.lender_type) {
        details.push('Type: ' + lender.lender_type);
    }
    
    $('#confirmed-lender-name').text(lender.name || 'Unknown Lender');
    $('#confirmed-lender-details').html(details.join(' | '));
    $('#confirmed-lender-info').show();
    $('#lender-lookup-form').hide();
    
    // Show geography method toggle
    $('#geography-method-toggle').show();
    
    // Show geography selection (manual by default)
    $('#manual-geography-group').show();
    $('#auto-selection-group').hide();
    
    // Load geography options
    loadStates();
    loadCounties('lender');
    loadMetros();
    
}

function clearLenderSelection() {
    // Clear dropdown selection
    $('#lender-name-select').val('').trigger('change');
    
    // Clear display fields
    $('#lender-lei-display').text('');
    $('#lender-details-display').hide();
    
    // Clear state
    lenderLookupState.confirmedLender = null;
    lenderLookupState.pendingLender = null;
    DashboardState.lenderFilters.subjectLender = null;
    DashboardState.lenderFilters.geoids = [];
    
    // Reset UI
    $('#confirm-lender-btn').prop('disabled', true);
    $('#confirmed-lender-info').hide();
    $('#lender-lookup-form').show();
    $('#geography-method-toggle').hide();
    $('#auto-selection-group').hide();
    $('#manual-geography-group').hide();
    
    // Reset geography toggle buttons
    $('.geo-method-toggle-btn').css({
        'background': '#e0e0e0',
        'color': '#333'
    });
    $('.geo-method-toggle-btn[data-method="manual"]').css({
        'background': 'var(--ncrc-secondary-blue)',
        'color': 'white'
    });
}

function updateGeographyMethodOptions() {
    // This function is kept for backward compatibility but is no longer used
    // Button visibility is now handled in confirmLenderSelection()
}

function handleGeographyMethodChange(method, lenderId) {
    // Hide all geography sections first
    $('#auto-selection-group').hide();
    $('#manual-geography-group').hide();
    
    if (!lenderId) {
        return;
    }
    
    if (method === 'manual') {
        // Show manual selection
        $('#manual-geography-group').show();
        // Load geography options
        loadStates();
        loadCounties('lender');
        loadMetros();
    } else {
        // Show auto-selection (branches or lending_activity)
        $('#auto-selection-group').show();
        loadAutoCounties(method, lenderId);
    }
}

function loadAutoCounties(method, lenderId) {
    const filters = DashboardState.lenderFilters;
    
    if (!lenderId) {
        return;
    }
    
    // Update the message based on method
    if (method === 'branches') {
        $('#auto-selection-message').html('<i class="fas fa-info-circle"></i> Counties identified based on branch locations.');
    } else if (method === 'lending_activity') {
        $('#auto-selection-message').html('<i class="fas fa-info-circle"></i> Counties identified based on lending activity (loan applications).');
    }
    
    showLoading();
    
    // For branch locations, we need to use RSSD instead of LEI
    let lenderIdentifier = lenderId;
    if (method === 'branches') {
        if (lenderLookupState.confirmedLender && lenderLookupState.confirmedLender.rssd) {
            lenderIdentifier = lenderLookupState.confirmedLender.rssd;
            debugLog(`Using RSSD ${lenderIdentifier} for branch locations`);
        } else {
            showError('RSSD ID is not available for this lender. Branch locations cannot be determined without an RSSD.');
            hideLoading();
            return;
        }
    }
    
    const payload = {
        lender_id: lenderIdentifier,
        data_type: filters.dataType,
        years: filters.years.length > 0 ? filters.years : null,
        selection_method: method
    };
    
    // For branch locations, override data_type to 'branches' and use only 2025
    // (lender analysis should show current branch network)
    if (method === 'branches') {
        payload.data_type = 'branches';
        payload.years = [2025];  // Always use 2025 for lender branch analysis
    }
    
    // For lending activity (loan applications), use only 2024 to set geographic boundaries
    if (method === 'lending_activity') {
        payload.years = [2024];  // Always use 2024 for assessment area based on loan applications
    }
    
    debugLog(`loadAutoCounties payload:`, payload);
    
    // For lending activity, include action_taken filter
    if (method === 'lending_activity' && filters.dataType === 'hmda') {
        payload.action_taken = ['1']; // Originations only
    }
    
    $.ajax({
        url: '/api/lender/target-counties',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(payload)
    })
    .done(function(response) {
        hideLoading();
        if (response.success && response.data.length > 0) {
            // Update info message
            let message = '';
            if (method === 'threshold') {
                message = '<i class="fas fa-info-circle"></i> <strong>1% Threshold:</strong> Counties where lender has ≥1% of total lending or branches.';
            } else if (method === 'branches') {
                message = '<i class="fas fa-info-circle"></i> <strong>Branch Locations:</strong> Counties where lender has at least one branch.';
            } else if (method === 'lending_activity') {
                message = '<i class="fas fa-info-circle"></i> <strong>Lending Activity:</strong> Counties where lender has loan applications (action_taken 1-5).';
            }
            $('#auto-selection-message').html(message);
            
            // Populate counties dropdown
            const options = response.data.map(c => {
                const displayName = c.county_state || `${c.county_name}, ${c.state_name}`;
                let suffix = '';
                if (c.pct_loans) {
                    suffix = ` (${c.pct_loans.toFixed(1)}%)`;
                } else if (c.application_count) {
                    suffix = ` (${formatNumber(c.application_count)} apps)`;
                }
                return `<option value="${c.geoid5}">${displayName}${suffix}</option>`;
            }).join('');
            
            $('#auto-county-select').html(options).prop('disabled', false).trigger('change');
            
            // Auto-select all counties
            const allGeoids = response.data.map(c => c.geoid5);
            $('#auto-county-select').val(allGeoids).trigger('change');
            DashboardState.lenderFilters.geoids = allGeoids;
        } else {
            // No counties found - provide more specific error message
            let errorMsg = 'No counties found for this lender using the selected method.';
            if (method === 'branches') {
                errorMsg = 'No branch locations found for this lender. This may mean:\n' +
                          '1. The RSSD ID is not associated with any branches in the selected years\n' +
                          '2. The RSSD ID may be incorrect or not available for this lender\n' +
                          '3. The lender may not have branches in the selected years\n\n' +
                          'RSSD used: ' + (payload.lender_id || 'Not available');
            } else if (method === 'lending_activity') {
                errorMsg = 'No lending activity found for this lender. This may mean:\n' +
                          '1. The lender has no loan applications in the selected years\n' +
                          '2. The lender has no activity in the selected geography';
            }
            debugWarn(`No counties found. Response:`, response);
            showError(errorMsg);
            // Show manual selection as fallback
            $('#auto-selection-group').hide();
            $('#manual-geography-group').show();
        }
    })
    .fail(function(xhr) {
        hideLoading();
        showError('Failed to load counties: ' + (xhr.responseJSON?.error || 'Unknown error'));
    });
}

function updateManualGeographySelection() {
    // Collect geoids from all manual selectors
    const counties = $('#county-select-lender').val() || [];
    const metros = $('#metro-select-lender').val() || [];
    const states = $('#state-select-lender').val() || [];
    
    // Combine all selections (will be expanded on backend)
    DashboardState.lenderFilters.geoids = [...counties, ...metros, ...states];
}

// Update data type specific filters
function updateDataTypeFilters(context) {
    const dataType = context === 'area' ? DashboardState.areaFilters.dataType : DashboardState.lenderFilters.dataType;
    const prefix = context === 'area' ? 'area' : 'lender';
    
    // Hide all filters
    $('.data-type-filters').removeClass('active');
    
    // Show relevant filters
    if (dataType === 'hmda') {
        $(`#hmda-filters-${prefix}`).addClass('active');
    }
}

function updateHmdaFilters(context) {
    if (context === 'area') {
        // Loan purpose is always all three: Home Purchase (1), Home Improvement/Equity (2), Refinance (3)
        DashboardState.areaFilters.hmdaFilters.loanPurpose = ['1', '2', '3'];
        // Total units is always 1-4 units
        DashboardState.areaFilters.hmdaFilters.totalUnits = ['1', '2', '3', '4'];
        // Expand comma-separated action taken values (e.g., "1,2,3,4,5" -> ['1','2','3','4','5'])
        const actionTakenRaw = $('#action-taken-area').val() || [];
        const actionTakenExpanded = [];
        actionTakenRaw.forEach(val => {
            if (val.includes(',')) {
                actionTakenExpanded.push(...val.split(','));
            } else {
                actionTakenExpanded.push(val);
            }
        });
        DashboardState.areaFilters.hmdaFilters.actionTaken = actionTakenExpanded;
        DashboardState.areaFilters.hmdaFilters.occupancyType = $('#occupancy-type-area').val() || [];
        DashboardState.areaFilters.hmdaFilters.constructionMethod = $('#construction-method-area').val() || [];
        DashboardState.areaFilters.hmdaFilters.excludeReverseMortgages = $('#exclude-reverse-area').is(':checked');
    } else {
        // Loan purpose is always all three: Home Purchase (1), Home Improvement/Equity (2), Refinance (3)
        DashboardState.lenderFilters.hmdaFilters.loanPurpose = ['1', '2', '3'];
        // Total units is always 1-4 units
        DashboardState.lenderFilters.hmdaFilters.totalUnits = ['1', '2', '3', '4'];
        // Expand comma-separated action taken values (e.g., "1,2,3,4,5" -> ['1','2','3','4','5'])
        const actionTakenRaw = $('#action-taken-lender').val() || [];
        const actionTakenExpanded = [];
        actionTakenRaw.forEach(val => {
            if (val.includes(',')) {
                actionTakenExpanded.push(...val.split(','));
            } else {
                actionTakenExpanded.push(val);
            }
        });
        DashboardState.lenderFilters.hmdaFilters.actionTaken = actionTakenExpanded;
        DashboardState.lenderFilters.hmdaFilters.occupancyType = $('#occupancy-type-lender').val() || [];
        DashboardState.lenderFilters.hmdaFilters.constructionMethod = $('#construction-method-lender').val() || [];
        DashboardState.lenderFilters.hmdaFilters.excludeReverseMortgages = $('#exclude-reverse-lender').is(':checked');
    }
}

// Analyze functions
function analyzeArea() {
    debugLog('analyzeArea called');
    const filters = DashboardState.areaFilters;
    debugLog('Current filters:', {
        geoids: filters.geoids,
        years: filters.years,
        dataType: filters.dataType,
        geoType: filters.geoType
    });
    
    if (!filters.geoids.length) {
        debugWarn('No geoids selected');
        showError('Please select at least one geographic area');
        return;
    }
    
    // Years are automatically set to last 5 years, so this check is not needed
    // But ensure years are set if somehow they're empty
    if (!filters.years.length) {
        debugWarn('No years selected, auto-setting to last 5 years');
        setAreaAnalysisYears();
        if (!DashboardState.areaFilters.years.length) {
            showError('Unable to determine years for analysis');
            return;
        }
    }
    
    debugLog('Starting analysis with', filters.geoids.length, 'geoids and', filters.years.length, 'years');
    showLoading();
    
    let url = '';
    let payload = {
        geoids: filters.geoids,
        years: filters.years,
        aggregate: true
    };
    
    if (filters.dataType === 'hmda') {
        // Use new comprehensive Area Analysis endpoint for HMDA
        url = '/api/area/hmda/analysis';
        payload.loan_purpose = filters.hmdaFilters.loanPurpose;
        payload.action_taken = filters.hmdaFilters.actionTaken;
        payload.occupancy_type = filters.hmdaFilters.occupancyType;
        payload.total_units = filters.hmdaFilters.totalUnits;
        payload.construction_method = filters.hmdaFilters.constructionMethod;
        payload.exclude_reverse_mortgages = filters.hmdaFilters.excludeReverseMortgages;
        // Remove fields not needed for area analysis
        delete payload.aggregate;
        delete payload.include_peer_comparison;
        delete payload.subject_lei;
    } else if (filters.dataType === 'sb') {
        // Use new comprehensive Area Analysis endpoint for Small Business
        url = '/api/area/sb/analysis';
        // Remove fields not needed for area analysis
        delete payload.aggregate;
        delete payload.include_peer_comparison;
        delete payload.subject_respondent_id;
        delete payload.respondent_ids;
    } else if (filters.dataType === 'branches') {
        // Use new comprehensive Area Analysis endpoint for Branches
        url = '/api/area/branches/analysis';
        // Remove fields not needed for area analysis
        delete payload.aggregate;
        delete payload.include_peer_comparison;
        delete payload.subject_rssd;
        delete payload.rssd_ids;
    }
    
    debugLog('Making API call to:', url);
    debugLog('Payload:', payload);
    
    $.ajax({
        url: url,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(payload)
    })
    .done(function(response) {
                debugLog('API response received:', response);
                debugLog('Response success:', response.success);
                debugLog('Response data keys:', response.data ? Object.keys(response.data) : 'No data');
                debugLog('Response data structure:', {
                    hasData: !!response.data,
                    dataKeys: response.data ? Object.keys(response.data) : [],
                    summaryLength: response.data?.summary?.length || 0,
                    summaryContent: response.data?.summary || [],
                    demographicsLength: response.data?.demographics?.length || 0,
                    hhi: response.data?.hhi || null
                });
                hideLoading();
                if (response.success) {
                    if (response.data && typeof response.data === 'object' && response.data.summary) {
                        // New comprehensive Area Analysis format (HMDA, SB, Branches)
                        debugLog('Displaying area analysis tables');
                        debugLog('Summary data:', response.data.summary);
                        // Log each table's content
                        Object.keys(response.data).forEach(key => {
                            const tableData = response.data[key];
                            if (Array.isArray(tableData)) {
                                debugLog(`Table '${key}': ${tableData.length} rows`, tableData.slice(0, 2));
                            } else {
                                debugLog(`Table '${key}':`, tableData);
                            }
                        });
                        displayAreaAnalysisTables(response.data, filters.dataType);
            } else if (response.data) {
                // Legacy format fallback
                debugLog('Using legacy display format');
                displayAreaResults(response.data, filters.dataType);
            } else {
                debugWarn('Response has no data');
                showError('No data returned from analysis');
            }
        } else {
            debugError('Analysis failed:', response.error);
            showError(response.error || 'Analysis failed');
        }
    })
    .fail(function(xhr) {
        debugError('API call failed:', xhr);
        debugError('Status:', xhr.status);
        debugError('Response text:', xhr.responseText);
        hideLoading();
        showError('Failed to analyze data: ' + (xhr.responseJSON?.error || xhr.statusText || 'Unknown error'));
    });
}

function analyzeLender() {
    const filters = DashboardState.lenderFilters;
    
    if (!filters.subjectLender) {
        showError('Please confirm a subject lender first');
        return;
    }
    
    // Get geoids from either auto-selection or manual selection
    // Check if auto-selection is visible (means user clicked branch/lending button)
    if ($('#auto-selection-group').is(':visible')) {
        filters.geoids = $('#auto-county-select').val() || [];
    } else {
        // Use manual selection
        updateManualGeographySelection();
    }
    
    if (!filters.geoids.length) {
        showError('Please select at least one geographic area');
        return;
    }
    
    // Get years - default to recent years if not specified
    let years = filters.years || [];
    if (!years.length) {
        if (filters.dataType === 'hmda') {
            years = [2020, 2021, 2022, 2023, 2024];
        } else if (filters.dataType === 'sb') {
            years = [2019, 2020, 2021, 2022, 2023];
        } else {
            years = [2021, 2022, 2023, 2024, 2025];
        }
    }
    
    showLoading();
    
    // Use new lender analysis endpoint
    const payload = {
        subject_lender_id: filters.subjectLender,
        data_type: filters.dataType,
        geoids: filters.geoids,
        years: years,
        enable_peer_comparison: filters.enablePeerComparison || false,
        custom_peers: filters.customPeers || [],
        include_all_data_types: true,  // Always include all three data types
        // HMDA filters
        loan_purpose: filters.hmdaFilters?.loanPurpose || [],
        action_taken: filters.hmdaFilters?.actionTaken || ['1', '2', '3', '4', '5'],
        occupancy_type: filters.hmdaFilters?.occupancyType || ['1'],
        total_units: filters.hmdaFilters?.totalUnits || ['1', '2', '3', '4'],
        construction_method: filters.hmdaFilters?.constructionMethod || ['1'],
        exclude_reverse_mortgages: filters.hmdaFilters?.excludeReverseMortgages !== false
    };
    
    $.ajax({
        url: '/api/lender/analysis',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(payload)
    })
    .done(function(response) {
        hideLoading();
        if (response.success) {
            // Store raw results and assessment areas for Excel export
            DashboardState.currentLenderAnalysis.rawResults = response.raw_results || null;
            
            // Build assessment areas from current selection
            // Try to get county info from the auto-selection dropdown if available
            const counties = [];
            filters.geoids.forEach(geoid => {
                const $countyOption = $(`#auto-county-select option[value="${geoid}"]`);
                if ($countyOption.length) {
                    const text = $countyOption.text();
                    // Parse "County Name, State Name" format
                    const parts = text.split(', ');
                    counties.push({
                        geoid5: geoid,
                        county_name: parts[0] || '',
                        state_name: parts[1] || '',
                        cbsa_code: $countyOption.data('cbsa-code') || '',
                        cbsa_name: $countyOption.data('cbsa-name') || ''
                    });
                } else {
                    // Fallback: just store geoid
                    counties.push({ geoid5: geoid });
                }
            });
            
            DashboardState.currentLenderAnalysis.assessmentAreas = {
                counties: counties
            };
            // Get subject lender name
            const $lenderOption = $(`#lender-name-select option[value="${filters.subjectLender}"]`);
            DashboardState.currentLenderAnalysis.subjectLenderName = $lenderOption.length ? $lenderOption.text() : 'Subject Lender';
            
            displayLenderResults(response.data, filters.dataType, filters.subjectLender);
        } else {
            showError(response.error || 'Analysis failed');
        }
    })
    .fail(function(xhr) {
        hideLoading();
        showError('Failed to analyze lender: ' + (xhr.responseJSON?.error || 'Unknown error'));
    });
}

// Display results
function displayAreaResults(data, dataType) {
    $('#area-results').show();
    const content = $('#area-results-content');
    
    if (!data || data.length === 0) {
        content.html('<p>No data found for the selected filters.</p>');
        return;
    }
    
    // Group data by year for year-over-year analysis
    const dataByYear = {};
    data.forEach(row => {
        const year = row.activity_year || row.year;
        if (!dataByYear[year]) {
            dataByYear[year] = [];
        }
        dataByYear[year].push(row);
    });
    
    const years = Object.keys(dataByYear).sort();
    
    // Create year-over-year chart
    let html = '<div class="data-summary">';
    html += '<h4>Year-Over-Year Trends</h4>';
    html += '<div class="chart-container"><canvas id="yoy-chart-area"></canvas></div>';
    
    // Prepare chart data
    const chartData = {
        labels: years,
        datasets: []
    };
    
    if (dataType === 'hmda') {
        // Aggregate by year
        const yearlyTotals = years.map(year => {
            const yearData = dataByYear[year];
            return {
                year: year,
                loans: yearData.reduce((sum, r) => sum + (r.loan_count || 0), 0),
                amount: yearData.reduce((sum, r) => sum + (r.total_amount || 0), 0),
                lmict: yearData.reduce((sum, r) => sum + (r.lmict_loans || 0), 0),
                mmct: yearData.reduce((sum, r) => sum + (r.mmct_loans || 0), 0)
            };
        });
        
        chartData.datasets.push({
            label: 'Total Loans',
            data: yearlyTotals.map(d => d.loans),
            borderColor: '#034ea0', // NCRC Dark Blue
            backgroundColor: 'rgba(3, 78, 160, 0.1)',
            yAxisID: 'y',
            borderWidth: 2
        });
        
        chartData.datasets.push({
            label: 'Total Amount',
            data: yearlyTotals.map(d => d.amount),
            borderColor: '#2fade3', // NCRC Secondary Blue
            backgroundColor: 'rgba(47, 173, 227, 0.1)',
            yAxisID: 'y1',
            borderWidth: 2
        });
        
        // Create chart
        setTimeout(() => {
            const ctx = document.getElementById('yoy-chart-area');
            if (ctx) {
                new Chart(ctx, {
                    type: 'line',
                    data: chartData,
                    options: {
                        responsive: true,
                        interaction: {
                            mode: 'index',
                            intersect: false,
                        },
                        scales: {
                            y: {
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {
                                    display: true,
                                    text: 'Number of Loans'
                                }
                            },
                            y1: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: {
                                    display: true,
                                    text: 'Amount ($)'
                                },
                                ticks: {
                                    callback: function(value) {
                                        return formatCurrency(value);
                                    }
                                },
                                grid: {
                                    drawOnChartArea: false,
                                },
                            }
                        }
                    }
                });
            }
        }, 100);
    }
    
    // Create summary table
    html += '<h4 style="margin-top: 32px;">Summary Statistics by Year</h4>';
    html += '<table class="data-table"><thead><tr>';
    
    // Build table based on data type
    if (dataType === 'hmda') {
        html += '<th>Year</th><th>Total Loans</th><th>Total Amount</th><th>LMI Loans</th><th>LMI %</th><th>MMCT Loans</th><th>MMCT %</th></tr></thead><tbody>';
        years.forEach(year => {
            const yearData = dataByYear[year];
            const totals = {
                loans: yearData.reduce((sum, r) => sum + (r.loan_count || 0), 0),
                amount: yearData.reduce((sum, r) => sum + (r.total_amount || 0), 0),
                lmict: yearData.reduce((sum, r) => sum + (r.lmict_loans || 0), 0),
                mmct: yearData.reduce((sum, r) => sum + (r.mmct_loans || 0), 0)
            };
            const lmictPct = totals.loans > 0 ? (totals.lmict / totals.loans * 100) : 0;
            const mmctPct = totals.loans > 0 ? (totals.mmct / totals.loans * 100) : 0;
            
            html += `<tr>
                <td><strong>${year}</strong></td>
                <td>${formatNumber(totals.loans)}</td>
                <td>${formatCurrency(totals.amount)}</td>
                <td>${formatNumber(totals.lmict)}</td>
                <td>${formatPercentage(lmictPct / 100)}</td>
                <td>${formatNumber(totals.mmct)}</td>
                <td>${formatPercentage(mmctPct / 100)}</td>
            </tr>`;
        });
    } else if (dataType === 'sb') {
        html += '<th>Year</th><th>Total Loans</th><th>Total Amount</th><th>LMI Loans</th></tr></thead><tbody>';
        years.forEach(year => {
            const yearData = dataByYear[year];
            const totals = {
                loans: yearData.reduce((sum, r) => sum + (r.sb_loans_count || 0), 0),
                amount: yearData.reduce((sum, r) => sum + (r.sb_loans_amount || 0), 0),
                lmict: yearData.reduce((sum, r) => sum + (r.lmict_loans_count || 0), 0)
            };
            html += `<tr>
                <td><strong>${year}</strong></td>
                <td>${formatNumber(totals.loans)}</td>
                <td>${formatCurrency(totals.amount)}</td>
                <td>${formatNumber(totals.lmict)}</td>
            </tr>`;
        });
    } else if (dataType === 'branches') {
        html += '<th>Year</th><th>Total Branches</th><th>Total Deposits</th><th>LMI Branches</th></tr></thead><tbody>';
        years.forEach(year => {
            const yearData = dataByYear[year];
            const totals = {
                branches: yearData.reduce((sum, r) => sum + (r.branch_count || 0), 0),
                deposits: yearData.reduce((sum, r) => sum + (r.total_deposits || 0), 0),
                lmi: yearData.reduce((sum, r) => sum + (r.lmi_branches || 0), 0)
            };
            html += `<tr>
                <td><strong>${year}</strong></td>
                <td>${formatNumber(totals.branches)}</td>
                <td>${formatCurrency(totals.deposits)}</td>
                <td>${formatNumber(totals.lmi)}</td>
            </tr>`;
        });
    }
    
    html += '</tbody></table></div>';
    content.html(html);
}

function displayLenderResults(data, dataType, subjectLender) {
    $('#lender-results').show();
    const content = $('#lender-results-content');
    
    if (!data) {
        content.html('<p>No data found for the selected lender.</p>');
        return;
    }
    
    // New data structure from lender analysis endpoint
    // data = { combined_summary: {}, hmda: {subject: {}, peer: {}, comparison: {}}, ... }
    
    // Create hybrid display with combined summary and tabs for each data type
    let html = '<div class="lender-analysis-container">';
    
    // CRA Commitment Card (combines HMDA and SB data)
    if ((data.hmda && data.hmda.subject) || (data.sb && data.sb.subject)) {
        html += '<div class="dashboard-card" style="margin-bottom: 20px;">';
        html += '<div class="card-header"><h2><i class="fas fa-handshake"></i> CRA Commitment</h2></div>';
        html += '<div class="card-content">';
        html += renderCRACommitmentCard(data);
        html += '</div></div>';
    }
    
    // Tabs for each data type
    html += '<div class="dashboard-card">';
    html += '<div class="card-header">';
    html += '<ul class="data-type-tabs" style="display: flex; list-style: none; padding: 0; margin: 0; border-bottom: 2px solid #ddd;">';
    html += '<li class="tab-btn active" data-tab="hmda"><i class="fas fa-home"></i> HMDA</li>';
    html += '<li class="tab-btn" data-tab="sb"><i class="fas fa-briefcase"></i> Small Business</li>';
    html += '<li class="tab-btn" data-tab="branches"><i class="fas fa-building"></i> Branches</li>';
    html += '</ul></div>';
    html += '<div class="card-content">';
    
    // HMDA Tab Content
    html += '<div id="lender-tab-hmda" class="lender-tab-content active">';
    if (data.hmda && data.hmda.subject) {
        html += renderLenderDataTypeResults(data.hmda, 'hmda', 'Subject Lender', 'Peer Average');
    } else {
        html += '<p>No HMDA data available for this lender.</p>';
    }
    html += '</div>';
    
    // Small Business Tab Content
    html += '<div id="lender-tab-sb" class="lender-tab-content" style="display: none;">';
    if (data.sb && data.sb.subject) {
        html += renderLenderDataTypeResults(data.sb, 'sb', 'Subject Lender', 'Peer Average');
    } else {
        html += '<p>No Small Business data available for this lender.</p>';
    }
    html += '</div>';
    
    // Branches Tab Content
    html += '<div id="lender-tab-branches" class="lender-tab-content" style="display: none;">';
    if (data.branches && data.branches.subject) {
        html += renderLenderDataTypeResults(data.branches, 'branches', 'Subject Lender', 'Peer Average');
    } else {
        html += '<p>No Branch data available for this lender.</p>';
    }
    html += '</div>';
    
    html += '</div></div></div>';
    
    content.html(html);
    
    // Set up tab switching
    $('.data-type-tabs .tab-btn').on('click', function() {
        const tab = $(this).data('tab');
        $('.data-type-tabs .tab-btn').removeClass('active');
        $(this).addClass('active');
        $('.lender-tab-content').hide();
        $(`#lender-tab-${tab}`).show();
    });
}

// Lender Analysis Rendering Functions
function renderCombinedLenderSummary(combinedSummary) {
    let html = '<div class="combined-summary-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">';
    
    // HMDA Summary
    if (combinedSummary.hmda && combinedSummary.hmda.length > 0) {
        const latest = combinedSummary.hmda[0];
        html += '<div class="summary-card" style="padding: 15px; background: #f8f9fa; border-radius: 6px;">';
        html += '<h4 style="margin: 0 0 10px 0; color: var(--ncrc-dark-blue);"><i class="fas fa-home"></i> HMDA</h4>';
        html += `<p style="margin: 5px 0;"><strong>Total Loans:</strong> ${formatNumber(latest.total_loans || 0)}</p>`;
        html += `<p style="margin: 5px 0;"><strong>Total Amount:</strong> ${formatCurrency(latest.total_amount || 0)}</p>`;
        html += '</div>';
    }
    
    // Small Business Summary
    if (combinedSummary.sb && combinedSummary.sb.length > 0) {
        const latest = combinedSummary.sb[0];
        html += '<div class="summary-card" style="padding: 15px; background: #f8f9fa; border-radius: 6px;">';
        html += '<h4 style="margin: 0 0 10px 0; color: var(--ncrc-dark-blue);"><i class="fas fa-briefcase"></i> Small Business</h4>';
        html += `<p style="margin: 5px 0;"><strong>Total Loans:</strong> ${formatNumber(latest.total_loans || 0)}</p>`;
        html += `<p style="margin: 5px 0;"><strong>Total Amount:</strong> ${formatCurrency(latest.total_amount || 0)}</p>`;
        html += '</div>';
    }
    
    // Branches Summary
    if (combinedSummary.branches && combinedSummary.branches.length > 0) {
        const latest = combinedSummary.branches[0];
        html += '<div class="summary-card" style="padding: 15px; background: #f8f9fa; border-radius: 6px;">';
        html += '<h4 style="margin: 0 0 10px 0; color: var(--ncrc-dark-blue);"><i class="fas fa-building"></i> Branches</h4>';
        html += `<p style="margin: 5px 0;"><strong>Total Branches:</strong> ${formatNumber(latest.total_branches || 0)}</p>`;
        html += `<p style="margin: 5px 0;"><strong>Total Deposits:</strong> ${formatCurrency(latest.total_deposits || 0)}</p>`;
        html += '</div>';
    }
    
    html += '</div>';
    return html;
}

function renderLenderDataTypeResults(dataTypeData, dataType, subjectLabel, peerLabel) {
    let html = '';
    
    // Render comparison cards based on data type (ONLY the specified tables)
    if (dataType === 'hmda') {
        html += renderHmdaComparisonCards(dataTypeData, subjectLabel, peerLabel);
    } else if (dataType === 'sb') {
        html += renderSbComparisonCards(dataTypeData, subjectLabel, peerLabel);
    } else if (dataType === 'branches') {
        html += renderBranchComparisonCards(dataTypeData, subjectLabel, peerLabel);
    }
    
    return html;
}

// Render HMDA Comparison Cards
function renderHmdaComparisonCards(dataTypeData, subjectLabel, peerLabel) {
    let html = '<div class="lender-comparison-cards" style="display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 30px;">';
    
    const years = [2020, 2021, 2022, 2023, 2024];
    const subjectSummary = dataTypeData.subject?.summary || [];
    const peerSummary = dataTypeData.comparison?.summary?.peer_average || {};
    const subjectDemo = dataTypeData.subject?.demographics || [];
    const peerDemo = dataTypeData.comparison?.demographics?.peer_average || [];
    const subjectIncome = dataTypeData.subject?.income_neighborhood || [];
    const peerIncome = dataTypeData.comparison?.income_neighborhood?.peer_average || [];
    
    // Card 1: Mortgage - Loans w/Demographic Data
    html += '<div class="comparison-card dashboard-card">';
    html += '<div class="card-header"><h3>Mortgage</h3><h4>number of Loans w/Demographic Data</h4></div>';
    html += '<div class="card-content">';
    html += renderComparisonTable({
        years: years,
        subjectLabel: subjectLabel,
        peerLabel: peerLabel,
        rows: [
            {
                label: 'number of Loans w/Demographic Data',
                getValue: (year, data) => getYearValue(data, year, 'total_loans'),
                format: 'number'
            },
            {
                label: '% of loans White (%)',
                getValue: (year, data) => getYearValue(data, year, 'white_percentage'),
                format: 'percent'
            },
            {
                label: '% of loans Black (%)',
                getValue: (year, data) => getYearValue(data, year, 'black_percentage'),
                format: 'percent'
            },
            {
                label: '% of loans Hispanic (%)',
                getValue: (year, data) => getYearValue(data, year, 'hispanic_percentage'),
                format: 'percent'
            },
            {
                label: '% of loans Asian (%)',
                getValue: (year, data) => getYearValue(data, year, 'asian_percentage'),
                format: 'percent'
            },
            {
                label: '% of loans Native American (%)',
                getValue: (year, data) => getYearValue(data, year, 'native_american_percentage'),
                format: 'percent'
            },
            {
                label: '% of loans Hawaiian or Pacific Islander (%)',
                getValue: (year, data) => getYearValue(data, year, 'hopi_percentage'),
                format: 'percent'
            }
        ],
        subjectData: subjectSummary,
        peerData: peerSummary
    });
    html += '</div></div>';
    
    // Card 2: Mortgage - Loans (Income/Borrower)
    html += '<div class="comparison-card dashboard-card">';
    html += '<div class="card-header"><h3>Mortgage</h3><h4>number of Loans</h4></div>';
    html += '<div class="card-content">';
    html += renderComparisonTable({
        years: years,
        subjectLabel: subjectLabel,
        peerLabel: peerLabel,
        rows: [
            {
                label: 'number of Loans',
                getValue: (year, data) => getYearValue(data, year, 'total_loans'),
                format: 'number'
            },
            {
                label: '% of loans Low or Moderate Census Tract (%)',
                getValue: (year, data) => getYearValue(data, year, 'lmict_percentage'),
                format: 'percent'
            },
            {
                label: '% of loans Low and Moderate Income Borrower',
                getValue: (year, data) => getYearValue(data, year, 'lmib_percentage'),
                format: 'percent'
            }
        ],
        subjectData: subjectSummary,
        peerData: peerSummary
    });
    html += '</div></div>';
    
    // Card 3: Mortgage - Loans (Minority Tract)
    html += '<div class="comparison-card dashboard-card">';
    html += '<div class="card-header"><h3>Mortgage</h3><h4>Loans</h4></div>';
    html += '<div class="card-content">';
    html += renderComparisonTable({
        years: years,
        subjectLabel: subjectLabel,
        peerLabel: peerLabel,
        rows: [
            {
                label: 'number of Loans',
                getValue: (year, data) => getYearValue(data, year, 'total_loans'),
                format: 'number'
            },
            {
                label: '% of loans Majority Minority Census Tract (%)',
                getValue: (year, data) => getYearValue(data, year, 'mmct_percentage'),
                format: 'percent'
            },
            {
                label: '% of loans High Minority Census Tract (%)',
                getValue: (year, data) => getYearValue(data, year, 'high_minority_percentage'),
                format: 'percent'
            }
        ],
        subjectData: subjectSummary,
        peerData: peerSummary
    });
    html += '</div></div>';
    
    html += '</div>';
    return html;
}

// Render Small Business Comparison Cards
function renderSbComparisonCards(dataTypeData, subjectLabel, peerLabel) {
    let html = '<div class="lender-comparison-cards" style="display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 30px;">';
    
    const years = [2020, 2021, 2022, 2023, 2024];
    const subjectSummary = dataTypeData.subject?.summary || [];
    const peerSummary = dataTypeData.comparison?.summary?.peer_average || {};
    
    // Card 4: Small Business - Total Loans
    html += '<div class="comparison-card dashboard-card">';
    html += '<div class="card-header"><h3>Small Business</h3><h4>total smal Total Loans</h4></div>';
    html += '<div class="card-content">';
    html += renderComparisonTable({
        years: years,
        subjectLabel: subjectLabel,
        peerLabel: peerLabel,
        rows: [
            {
                label: 'total smal Total Loans',
                getValue: (year, data) => getYearValue(data, year, 'total_loans'),
                format: 'number'
            },
            {
                label: '% of loans Loans in LMICT (%)',
                getValue: (year, data) => getYearValue(data, year, 'lmict_percentage'),
                format: 'percent'
            },
            {
                label: '% of loans Loans to Small Biz (%)',
                getValue: (year, data) => getYearValue(data, year, 'small_biz_percentage'),
                format: 'percent'
            }
        ],
        subjectData: subjectSummary,
        peerData: peerSummary
    });
    html += '</div></div>';
    
    // Card 5: Small Business - Total Loan Amount
    html += '<div class="comparison-card dashboard-card">';
    html += '<div class="card-header"><h3>Small Business</h3><h4>Total loan Total Loan Amount</h4></div>';
    html += '<div class="card-content">';
    html += renderComparisonTable({
        years: years,
        subjectLabel: subjectLabel,
        peerLabel: peerLabel,
        rows: [
            {
                label: 'Total loan Total Loan Amount',
                getValue: (year, data) => getYearValue(data, year, 'total_amount'),
                format: 'currency'
            },
            {
                label: '% of dolla Amount to LMICT (%)',
                getValue: (year, data) => getYearValue(data, year, 'lmict_amount_percentage'),
                format: 'percent'
            },
            {
                label: '% of dolla AMmount to Small Biz (%)',
                getValue: (year, data) => getYearValue(data, year, 'small_biz_amount_percentage'),
                format: 'percent'
            }
        ],
        subjectData: subjectSummary,
        peerData: peerSummary
    });
    html += '</div></div>';
    
    html += '</div>';
    return html;
}

// Render Branch Comparison Cards
function renderBranchComparisonCards(dataTypeData, subjectLabel, peerLabel) {
    let html = '<div class="lender-comparison-cards" style="display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 30px;">';
    
    const years = [2020, 2021, 2022, 2023, 2024];
    const subjectSummary = dataTypeData.subject?.summary || [];
    const peerSummary = dataTypeData.comparison?.summary?.peer_average || {};
    const subjectIncome = dataTypeData.subject?.income_neighborhood || [];
    const peerIncome = dataTypeData.comparison?.income_neighborhood?.peer_average || [];
    
    // Card: Bank Branches
    html += '<div class="comparison-card dashboard-card">';
    html += '<div class="card-header"><h3>Bank Branches</h3></div>';
    html += '<div class="card-content">';
    html += renderComparisonTable({
        years: years,
        subjectLabel: subjectLabel,
        peerLabel: peerLabel,
        rows: [
            {
                label: 'Number of Branches',
                getValue: (year, data) => {
                    // Use summary data - total_branches or total_loans (branches uses total_loans key)
                    return getYearValue(data, year, 'total_branches') || getYearValue(data, year, 'total_loans') || 0;
                },
                format: 'number'
            },
            {
                label: 'Percent of LMI Only Branches',
                getValue: (year, data, incomeData) => {
                    if (Array.isArray(incomeData)) {
                        const lmiOnlyRow = incomeData.find(d => {
                            const dYear = d.year || d.activity_year;
                            return String(dYear) === String(year) && 
                                   d.indicator === 'LMI Only Branches';
                        });
                        if (lmiOnlyRow && lmiOnlyRow[String(year)]) {
                            return lmiOnlyRow[String(year)].percent || 0;
                        }
                    }
                    return 0;
                },
                format: 'percent',
                useIncomeData: true
            },
            {
                label: 'Percent of MMCT Only Branches',
                getValue: (year, data, incomeData) => {
                    if (Array.isArray(incomeData)) {
                        const mmctOnlyRow = incomeData.find(d => {
                            const dYear = d.year || d.activity_year;
                            return String(dYear) === String(year) && 
                                   d.indicator === 'MMCT Only Branches';
                        });
                        if (mmctOnlyRow && mmctOnlyRow[String(year)]) {
                            return mmctOnlyRow[String(year)].percent || 0;
                        }
                    }
                    return 0;
                },
                format: 'percent',
                useIncomeData: true
            },
            {
                label: 'Deduped Percent of LMI and MMCT Branches',
                getValue: (year, data, incomeData) => {
                    if (Array.isArray(incomeData)) {
                        const bothRow = incomeData.find(d => {
                            const dYear = d.year || d.activity_year;
                            return String(dYear) === String(year) && 
                                   d.indicator === 'Both LMI and MMCT Branches';
                        });
                        if (bothRow && bothRow[String(year)]) {
                            return bothRow[String(year)].percent || 0;
                        }
                    }
                    return 0;
                },
                format: 'percent',
                useIncomeData: true
            }
        ],
        subjectData: subjectSummary,
        peerData: peerSummary,
        subjectIncomeData: subjectIncome,
        peerIncomeData: peerIncome
    });
    html += '</div></div>';
    
    html += '</div>';
    return html;
}

// Render CRA Commitment Card
function renderCRACommitmentCard(data) {
    const years = [2020, 2021, 2022, 2023, 2024];
    const hmdaSubject = data.hmda?.subject?.summary || [];
    const hmdaPeer = data.hmda?.comparison?.summary?.peer_average || {};
    const sbSubject = data.sb?.subject?.summary || [];
    const sbPeer = data.sb?.comparison?.summary?.peer_average || {};
    
    // Calculate CRA lending (HMDA + SB amounts)
    const getCRAAmount = (year, hmdaData, sbData) => {
        const hmdaAmt = getYearValue(hmdaData, year, 'total_amount') || 0;
        const sbAmt = getYearValue(sbData, year, 'total_amount') || 0;
        return hmdaAmt + sbAmt;
    };
    
    const getMortgagePct = (year, hmdaData, craTotal) => {
        const hmdaAmt = getYearValue(hmdaData, year, 'total_amount') || 0;
        return craTotal > 0 ? (hmdaAmt / craTotal * 100) : 0;
    };
    
    const getSBPct = (year, sbData, craTotal) => {
        const sbAmt = getYearValue(sbData, year, 'total_amount') || 0;
        return craTotal > 0 ? (sbAmt / craTotal * 100) : 0;
    };
    
    return renderComparisonTable({
        years: years,
        subjectLabel: 'Subject Lender',
        peerLabel: 'Peer Average',
        rows: [
            {
                label: 'Amounts 1 CRA Lending ($)',
                getValue: (year, data) => {
                    if (data === hmdaSubject || data === sbSubject) {
                        return getCRAAmount(year, hmdaSubject, sbSubject);
                    } else {
                        return getCRAAmount(year, hmdaPeer, sbPeer);
                    }
                },
                format: 'currency'
            },
            {
                label: '% of loan Mortgage (%)',
                getValue: (year, data) => {
                    const craTotal = data === hmdaSubject || data === sbSubject 
                        ? getCRAAmount(year, hmdaSubject, sbSubject)
                        : getCRAAmount(year, hmdaPeer, sbPeer);
                    return getMortgagePct(year, data === hmdaSubject || data === sbSubject ? hmdaSubject : hmdaPeer, craTotal);
                },
                format: 'percent'
            },
            {
                label: '% of loan Small Business (%)',
                getValue: (year, data) => {
                    const craTotal = data === hmdaSubject || data === sbSubject 
                        ? getCRAAmount(year, hmdaSubject, sbSubject)
                        : getCRAAmount(year, hmdaPeer, sbPeer);
                    return getSBPct(year, data === hmdaSubject || data === sbSubject ? sbSubject : sbPeer, craTotal);
                },
                format: 'percent'
            }
        ],
        subjectData: hmdaSubject, // Using as placeholder, will be handled in getValue
        peerData: hmdaPeer
    });
}

// Helper function to render comparison table
function renderComparisonTable({years, subjectLabel, peerLabel, rows, subjectData, peerData, subjectIncomeData, peerIncomeData}) {
    let html = '<table class="comparison-table" style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">';
    
    // Header row
    html += '<thead><tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">';
    html += '<th style="text-align: left; padding: 10px; border: 1px solid #ddd; font-weight: 600;">Metric</th>';
    years.forEach(year => {
        html += `<th colspan="3" style="text-align: center; padding: 10px; border: 1px solid #ddd; font-weight: 600;">${year}</th>`;
    });
    html += '<th colspan="4" style="text-align: center; padding: 10px; border: 1px solid #ddd; font-weight: 600;">Overall</th>';
    html += '</tr>';
    
    // Sub-header row
    html += '<tr style="background: #f9f9f9; border-bottom: 1px solid #ddd;">';
    html += '<th style="padding: 8px; border: 1px solid #ddd;"></th>';
    years.forEach(() => {
        html += '<th style="padding: 8px; border: 1px solid #ddd; font-weight: 500; font-size: 0.85rem;">Subject</th>';
        html += '<th style="padding: 8px; border: 1px solid #ddd; font-weight: 500; font-size: 0.85rem;">Peer</th>';
        html += '<th style="padding: 8px; border: 1px solid #ddd; font-weight: 500; font-size: 0.85rem;">Difference</th>';
    });
    html += '<th style="padding: 8px; border: 1px solid #ddd; font-weight: 500; font-size: 0.85rem;">Subject</th>';
    html += '<th style="padding: 8px; border: 1px solid #ddd; font-weight: 500; font-size: 0.85rem;">Peer</th>';
    html += '<th style="padding: 8px; border: 1px solid #ddd; font-weight: 500; font-size: 0.85rem;">Difference</th>';
    html += '<th style="padding: 8px; border: 1px solid #ddd; font-weight: 500; font-size: 0.85rem;">Difference Ratio</th>';
    html += '</tr></thead>';
    
    // Data rows
    html += '<tbody>';
    rows.forEach(row => {
        html += '<tr>';
        html += `<td style="padding: 8px; border: 1px solid #ddd; font-weight: 500;">${row.label}</td>`;
        
        // Year columns
        years.forEach(year => {
            // Pass income data if row needs it
            const subjectIncome = row.useIncomeData ? subjectIncomeData : null;
            const peerIncome = row.useIncomeData ? peerIncomeData : null;
            const subjectVal = row.getValue(year, subjectData, subjectIncome);
            const peerVal = row.getValue(year, peerData, peerIncome);
            const diff = (subjectVal || 0) - (peerVal || 0);
            
            html += `<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">${formatValue(subjectVal, row.format)}</td>`;
            html += `<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">${formatValue(peerVal, row.format)}</td>`;
            html += `<td style="padding: 8px; border: 1px solid #ddd; text-align: right; color: ${diff >= 0 ? '#28a745' : '#dc3545'};">${formatValue(diff, row.format)}</td>`;
        });
        
        // Overall columns
        const subjectIncome = row.useIncomeData ? subjectIncomeData : null;
        const peerIncome = row.useIncomeData ? peerIncomeData : null;
        const subjectOverall = calculateOverall(row, subjectData, years, subjectIncome);
        const peerOverall = calculateOverall(row, peerData, years, peerIncome);
        const diffOverall = (subjectOverall || 0) - (peerOverall || 0);
        const diffRatio = peerOverall ? ((subjectOverall || 0) / (peerOverall || 0) - 1).toFixed(1) + 'x' : 'N/A';
        
        html += `<td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-weight: 600;">${formatValue(subjectOverall, row.format)}</td>`;
        html += `<td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-weight: 600;">${formatValue(peerOverall, row.format)}</td>`;
        html += `<td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-weight: 600; color: ${diffOverall >= 0 ? '#28a745' : '#dc3545'};">
            ${formatValue(diffOverall, row.format)}</td>`;
        html += `<td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-weight: 600; color: ${diffOverall >= 0 ? '#28a745' : '#dc3545'};">
            ${diffRatio}</td>`;
        
        html += '</tr>';
    });
    html += '</tbody></table>';
    
    return html;
}

// Helper function to get value for a specific year
function getYearValue(data, year, field) {
    if (Array.isArray(data)) {
        const yearData = data.find(d => d.year === year || d.activity_year === year);
        return yearData ? (yearData[field] || 0) : 0;
    }
    return 0;
}

// Helper function to calculate overall value
function calculateOverall(row, data, years, incomeData) {
    if (Array.isArray(data) || incomeData) {
        // For counts/amounts, sum across years
        if (row.format === 'number' || row.format === 'currency') {
            return years.reduce((sum, year) => {
                const val = row.getValue(year, data, incomeData);
                return sum + (val || 0);
            }, 0);
        }
        // For percentages, calculate weighted average
        else if (row.format === 'percent') {
            let total = 0;
            let count = 0;
            years.forEach(year => {
                const val = row.getValue(year, data, incomeData);
                if (val !== null && val !== undefined) {
                    total += val;
                    count++;
                }
            });
            return count > 0 ? total / count : 0;
        }
    }
    return 0;
}

// Helper function to format values
function formatValue(value, format) {
    if (value === null || value === undefined || isNaN(value)) return '0';
    
    if (format === 'currency') {
        return formatCurrency(value);
    } else if (format === 'percent') {
        return value.toFixed(1);
    } else if (format === 'number') {
        return formatNumber(value);
    }
    return value;
}

function renderLenderCharts(dataTypeData, dataType) {
    if (!dataTypeData.subject || !dataTypeData.subject.summary) {
        return;
    }
    
    const subjectSummary = dataTypeData.subject.summary;
    const peerSummary = dataTypeData.comparison?.summary?.peer_average || {};
    
    setTimeout(() => {
        const ctx = document.getElementById(`lender-chart-${dataType}`);
        if (!ctx) return;
        
        const years = subjectSummary.map(s => s.year || s.activity_year).reverse();
        const subjectData = subjectSummary.map(s => dataType === 'branches' ? (s.total_branches || 0) : (s.total_loans || 0)).reverse();
        const peerData = years.map(() => dataType === 'branches' ? (peerSummary.total_branches || 0) : (peerSummary.total_loans || 0));
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: years,
                datasets: [
                    {
                        label: 'Subject Lender',
                        data: subjectData,
                        borderColor: '#034ea0',
                        backgroundColor: 'rgba(3, 78, 160, 0.1)',
                        borderWidth: 2
                    },
                    {
                        label: 'Peer Average',
                        data: peerData,
                        borderColor: '#2fade3',
                        backgroundColor: 'rgba(47, 173, 227, 0.1)',
                        borderWidth: 2,
                        borderDash: [5, 5]
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: dataType === 'branches' ? 'Number of Branches' : 'Number of Loans'
                        }
                    }
                }
            }
        });
    }, 100);
}

// Utility functions
function clearAreaFilters() {
    DashboardState.areaFilters = {
        dataType: 'hmda',
        geoType: 'county',
        geoids: [],
        years: [],
        hmdaFilters: {
            loanPurpose: ['1', '2', '3'], // Always all three purposes
            actionTaken: defaultFilters.actionTaken,
            occupancyType: defaultFilters.occupancyType,
            totalUnits: ['1', '2', '3', '4'], // Always 1-4 units
            constructionMethod: defaultFilters.constructionMethod,
            excludeReverseMortgages: defaultFilters.excludeReverseMortgages
        }
    };
    
    $('#county-select-area, #metro-select-area, #state-select-area').val(null).trigger('change');
    // Loan purpose is always ['1', '2', '3'] and total units is always ['1', '2', '3', '4'] - hardcoded
    $('#action-taken-area').val(defaultFilters.actionTaken).trigger('change');
    $('#occupancy-type-area').val(defaultFilters.occupancyType).trigger('change');
    $('#total-units-area').val(['1', '2', '3', '4']).trigger('change'); // Always 1-4 units
    $('#construction-method-area').val(defaultFilters.constructionMethod).trigger('change');
    $('#exclude-reverse-area').prop('checked', defaultFilters.excludeReverseMortgages);
    // Years are automatically set, no need to call updateYearSelector
    setAreaAnalysisYears();
    $('#area-results').hide();
}

function clearLenderFilters() {
    DashboardState.lenderFilters = {
        dataType: 'hmda',
        geoType: 'county',
        geoids: [],
        years: [],
        subjectLender: null,
        enablePeerComparison: true,
        hmdaFilters: {
            loanPurpose: ['1', '2', '3'], // Always all three purposes
            actionTaken: defaultFilters.actionTaken,
            occupancyType: defaultFilters.occupancyType,
            totalUnits: ['1', '2', '3', '4'], // Always 1-4 units
            constructionMethod: defaultFilters.constructionMethod,
            excludeReverseMortgages: defaultFilters.excludeReverseMortgages
        }
    };
    
    // Reset UI elements
    $('#county-select-lender, #metro-select-lender, #state-select-lender').val(null).trigger('change');
    // Loan purpose is always ['1', '2', '3'] and total units is always ['1', '2', '3', '4'] - hardcoded
    $('#action-taken-lender').val(defaultFilters.actionTaken).trigger('change');
    $('#occupancy-type-lender').val(defaultFilters.occupancyType).trigger('change');
    $('#total-units-lender').val(['1', '2', '3', '4']).trigger('change'); // Always 1-4 units
    $('#construction-method-lender').val(defaultFilters.constructionMethod).trigger('change');
    $('#exclude-reverse-lender').prop('checked', defaultFilters.excludeReverseMortgages);
    $('#lender-search-input').val('');
    $('#lender-results').empty();
    $('#lender-results-section').hide();
    setLenderAnalysisYears();
}

// Legacy function - kept for compatibility
function clearLenderFiltersOld() {
    DashboardState.lenderFilters = {
        dataType: 'hmda',
        geoType: 'county',
        geoids: [],
        years: [],
        subjectLender: null,
        enablePeerComparison: true,
        hmdaFilters: {
            loanPurpose: ['1', '2', '3'], // Always all three purposes: Home Purchase, Refinance, Home Equity
            actionTaken: ['1'], // Originations only (matches Tableau default)
            occupancyType: ['1'],
            totalUnits: ['1', '2', '3', '4'],
            constructionMethod: ['1'],
            excludeReverseMortgages: true
        }
    };
    
    $('#county-select-lender, #metro-select-lender').val(null).trigger('change');
    clearLenderSelection();
    // Loan purpose is always ['1', '2', '3'] - no UI element to update
    $('#action-taken-lender').val(['1,2,3,4,5']).trigger('change');
    $('#occupancy-type-lender').val(['1']).trigger('change');
    $('#total-units-lender').val(['1', '2', '3', '4']).trigger('change');
    $('#construction-method-lender').val(['1']).trigger('change');
    $('#exclude-reverse-lender').prop('checked', true);
    $('#enable-peer-comparison').prop('checked', true);
    // Years are not used in Lender Analysis
    $('#lender-results').hide();
}

function showLoading(message = 'Loading data...') {
    const overlay = $('#loading-overlay');
    const messageEl = $('#loading-message');
    if (messageEl.length) {
        messageEl.text(message);
    }
    overlay.attr('aria-label', message);
    overlay.show();
}

function hideLoading() {
    $('#loading-overlay').hide();
}

// Toast notification system
function showToast(message, type = 'error', duration = 5000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');
    
    const icon = type === 'success' ? 'fa-check-circle' : type === 'info' ? 'fa-info-circle' : 'fa-exclamation-circle';
    toast.innerHTML = `
        <i class="fas ${icon}" aria-hidden="true"></i>
        <span>${message}</span>
        <button class="toast-close" aria-label="Close notification" onclick="this.parentElement.remove()">
            <i class="fas fa-times" aria-hidden="true"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.animation = 'slideIn 0.3s ease-out reverse';
                setTimeout(() => toast.remove(), 300);
            }
        }, duration);
    }
    
    return toast;
}

function showError(message) {
    showToast(message, 'error', 7000);
}

function showSuccess(message) {
    showToast(message, 'success', 3000);
}

function showInfo(message) {
    showToast(message, 'info', 5000);
}

// Geography loading overlay functions - Rebuilt from scratch
function showGeographyLoading(message = 'Loading...') {
    const overlay = document.getElementById('geography-loading-overlay');
    const text = document.getElementById('geography-loading-text');
    
    if (!overlay) {
        console.warn('Geography loading overlay element not found');
        return;
    }
    
    // Update message
    if (text) {
        text.textContent = message;
    }
    
    // Close Select2 dropdowns
    if (window.$ && $.fn.select2) {
        $('.select2-container--open').select2('close');
    }
    
    // Use requestAnimationFrame to ensure DOM is ready
    requestAnimationFrame(() => {
        // Show overlay with both classes for maximum compatibility
        overlay.classList.add('is-visible');
        overlay.classList.add('show');
        overlay.style.display = 'flex';
        overlay.setAttribute('aria-label', message);
        overlay.setAttribute('aria-live', 'polite');
        
        // Ensure logo is visible
        const logo = document.getElementById('geography-loading-logo');
        if (logo) {
            logo.style.display = 'block';
            logo.style.visibility = 'visible';
            logo.style.opacity = '1';
        }
        
        // Disable interactive elements
        const card = overlay.closest('.filter-feature-card');
        if (card) {
            const interactiveElements = card.querySelectorAll('select, button, input');
            interactiveElements.forEach(el => {
                el.disabled = true;
            });
        }
    });
}

function hideGeographyLoading() {
    const overlay = document.getElementById('geography-loading-overlay');
    
    if (!overlay) {
        return;
    }
    
    // Hide overlay - remove all visibility classes
    overlay.classList.remove('is-visible');
    overlay.classList.remove('show');
    overlay.style.display = 'none';
    
    // Re-enable interactive elements
    const card = overlay.closest('.filter-feature-card');
    if (card) {
        const interactiveElements = card.querySelectorAll('select, button, input');
        interactiveElements.forEach(el => {
            el.disabled = false;
        });
    }
}

// Store current analysis data for export
let currentAnalysisData = null;
let currentDataType = null;

// Area Analysis Tables Display
function displayAreaAnalysisTables(analysisData, dataType) {
    debugLog('displayAreaAnalysisTables called with:', {
        hasData: !!analysisData,
        dataKeys: analysisData ? Object.keys(analysisData) : [],
        dataType: dataType
    });
    
    // Store for export
    currentAnalysisData = analysisData;
    currentDataType = dataType;
    
    $('#area-results').show();
    const content = $('#area-results-content');
    content.empty();
    
    if (!analysisData || Object.keys(analysisData).length === 0) {
        debugWarn('No analysis data provided');
        content.html('<div class="no-data-message"><p>No data found for the selected filters.</p></div>');
        return;
    }
    
    let html = '';
    
    // 0. Summary Cards (Overview Metrics)
    if (analysisData.summary && analysisData.summary.length > 0) {
        html += renderSummaryCards(analysisData.summary, analysisData.hhi, dataType, analysisData.summary_by_purpose, analysisData.branch_change_2021_2025);
    }
    
    // 1. Summary Chart/Table
    if (dataType === 'sb') {
        // For SB, show summary chart (similar to trends chart)
        if (analysisData.summary && analysisData.summary.length > 0) {
            html += renderTrendChart(analysisData.summary, dataType);
        }
    } else if (analysisData.summary_by_purpose && analysisData.summary_by_purpose.length > 0) {
        html += renderSummaryChartByPurpose(analysisData.summary_by_purpose, dataType);
    } else if (analysisData.summary && analysisData.summary.length > 0) {
        html += renderTrendChart(analysisData.summary, dataType);
    }
    
    // 2. Loan Size Distribution - Stacked Area Chart (SB only, position 3)
    if (dataType === 'sb' && analysisData.income_neighborhood && analysisData.income_neighborhood.length > 0) {
        html += renderLoanSizeDistributionChart(analysisData.income_neighborhood);
    }
    
    // 3. Small Business Loans by Business Size - Stacked Area Chart (SB only, before Income & Neighborhood Indicators)
    if (dataType === 'sb' && analysisData.income_neighborhood && analysisData.income_neighborhood.length > 0) {
        html += renderBusinessSizeChart(analysisData.income_neighborhood);
    }
    
    // 4. Demographic Overview Table (skip for branches and SB - SB doesn't have demographic data)
    if (dataType !== 'branches' && dataType !== 'sb' && (analysisData.demographics && analysisData.demographics.length > 0 || analysisData.demographics_by_purpose)) {
        html += renderDemographicsTable(analysisData.demographics, dataType, analysisData.demographics_by_purpose, analysisData.acs_data);
    }
    
    // 5. Income & Neighborhood Indicators Table (show for all data types including branches)
    if (analysisData.income_neighborhood && analysisData.income_neighborhood.length > 0 || analysisData.income_neighborhood_by_purpose) {
        html += renderIncomeNeighborhoodTable(analysisData.income_neighborhood, analysisData.income_neighborhood_by_purpose, analysisData.avg_minority_percentage, analysisData.household_income_data, analysisData.tract_distributions, dataType, analysisData.mmct_stats);
    }
    
    // 5. Top Lenders Table
    if (analysisData.top_lenders && analysisData.top_lenders.length > 0) {
        html += renderTopLendersTable(analysisData.top_lenders, dataType, analysisData.top_lenders_by_purpose, analysisData.acs_data);
    }
    
    // 6. HHI by Year Chart (grouped column chart by loan purpose or revenue category) - replaces the table
    if (dataType === 'branches' && analysisData.hhi_by_year_full && typeof analysisData.hhi_by_year_full === 'object' && analysisData.hhi_by_year_full.all_branches) {
        // Branches: use the new structure with all_branches, lmi_branches, etc.
        html += renderHHIByYearChart(analysisData.hhi_by_year_full, 'branches');
    } else if (dataType === 'sb' && analysisData.hhi_by_year_by_revenue && Object.keys(analysisData.hhi_by_year_by_revenue).length > 0) {
        html += renderHHIByYearChart(analysisData.hhi_by_year_by_revenue, 'sb');
    } else if (analysisData.hhi_by_year_by_purpose && Object.keys(analysisData.hhi_by_year_by_purpose).length > 0) {
        html += renderHHIByYearChart(analysisData.hhi_by_year_by_purpose, 'hmda');
    } else if (analysisData.hhi_by_year && Array.isArray(analysisData.hhi_by_year) && analysisData.hhi_by_year.length > 0) {
        // Fallback to single-purpose chart if by-purpose data not available
        html += renderHHIByYearChart({'all': analysisData.hhi_by_year}, dataType);
    }
    
    // 7. Trends Chart removed - now using summary chart instead
    
    // 9. Sources, Methodologies, and Definitions Card (combined)
    html += renderMethodsCard(dataType);
    
    content.html(html);
    
    // Initialize editable table functionality
    initializeEditableTables();
    
    // Initialize charts after DOM is ready
    // Use a longer timeout to ensure Chart.js is loaded and DOM is fully rendered
    setTimeout(() => {
        initializeCharts();
        // Show expand button if there are more than 10 lenders (like bizsight)
        showExpandButtonIfNeeded();
    }, 300);
}

function showExpandButtonIfNeeded() {
    // Expand button functionality disabled - always show only top 10 lenders in UI
    // All lenders are included in Excel export
    // This function is kept for compatibility but does nothing
    return;
}

function renderSummaryCards(summaryData, hhiData, dataType = 'hmda', summaryByPurpose = null, branchChange2021_2025 = null) {
    if (!summaryData || summaryData.length === 0) {
        return '';
    }
    
    // Calculate totals and averages from summary data
    const latestYear = summaryData[0]; // First item is latest year (sorted reverse)
    const firstYear = summaryData[summaryData.length - 1]; // Last item is first year
    
    // For branches, use 2025 data and compare to 2021; for other data types, use 2024 data
    const targetYear = dataType === 'branches' ? '2025' : '2024';
    const comparisonYear = dataType === 'branches' ? '2021' : '2023';
    
    const yearTarget = summaryData.find(y => y.year === targetYear) || summaryData[0]; // Fallback to latest if target year not found
    const yearComparison = summaryData.find(y => y.year === comparisonYear);
    
    // For Total Loans card: sum all loan purposes for target year
    let totalLoans = 0;
    if (summaryByPurpose && summaryByPurpose.length > 0) {
        // Sum all loan purposes for target year
        totalLoans = summaryByPurpose.reduce((sum, row) => {
            const yearTargetData = row[targetYear];
            return sum + (yearTargetData ? (yearTargetData.total_loans || 0) : 0);
        }, 0);
    } else if (yearTarget) {
        totalLoans = yearTarget.total_loans || 0;
    }
    
    // For total amount: branches already in full dollars, HMDA/SB need conversion from thousands
    let totalAmount = 0;
    if (summaryByPurpose && summaryByPurpose.length > 0) {
        totalAmount = summaryByPurpose.reduce((sum, row) => {
            const yearTargetData = row[targetYear];
            // All data types: amounts are already in full dollars from queries
            return sum + (yearTargetData ? (yearTargetData.total_amount || 0) : 0);
        }, 0);
    } else if (yearTarget) {
        // All data types: amounts are already in full dollars
        totalAmount = yearTarget.total_amount || 0;
    }
    
    // Average loan size for target year
    const avgLoanSizeTarget = totalAmount > 0 && totalLoans > 0 ? totalAmount / totalLoans : 0;
    
    // Average loan size for comparison year
    let avgLoanSizeComparison = 0;
    if (yearComparison) {
        // All data types: amounts are already in full dollars
        const totalAmountComparison = yearComparison.total_amount || 0;
        const totalLoansComparison = yearComparison.total_loans || 0;
        avgLoanSizeComparison = totalAmountComparison > 0 && totalLoansComparison > 0 ? totalAmountComparison / totalLoansComparison : 0;
    }
    
    // Calculate change for average loan size
    const avgLoanSizeChange = avgLoanSizeTarget - avgLoanSizeComparison;
    const avgLoanSizeChangePct = avgLoanSizeComparison > 0 
        ? ((avgLoanSizeTarget - avgLoanSizeComparison) / avgLoanSizeComparison * 100) 
        : 0;
    
    // Calculate year-over-year change for loans and amount
    const loanChange = yearTarget && yearComparison ? (yearTarget.total_loans || 0) - (yearComparison.total_loans || 0) : 0;
    const loanChangePct = yearComparison && yearComparison.total_loans > 0 
        ? (((yearTarget.total_loans || 0) - (yearComparison.total_loans || 0)) / yearComparison.total_loans * 100) 
        : 0;
    // Calculate amount change - all data types: amounts are already in full dollars
    const amountTarget = yearTarget ? (yearTarget.total_amount || 0) : 0;
    const amountComparison = yearComparison ? (yearComparison.total_amount || 0) : 0;
    const amountChange = amountTarget - amountComparison;
    const amountChangePct = amountComparison > 0 
        ? ((amountTarget - amountComparison) / amountComparison * 100) 
        : 0;
    
    // Count unique lenders from top_lenders if available
    const lenderCount = hhiData && hhiData.top_lenders ? hhiData.top_lenders.length : 0;
    
    const cards = [];
    
    // Card 1: Total Loans
    cards.push({
        label: dataType === 'branches' ? 'Total Branches' : 'Total Loans',
        value: formatNumber(totalLoans),
        change: loanChange,
        changePct: loanChangePct,
        icon: 'fas fa-file-invoice-dollar',
        ariaLabel: `${dataType === 'branches' ? 'Total Branches' : 'Total Loans'}: ${formatNumber(totalLoans)}`
    });
    
    // Card 2: Total Amount (full number, not thousands)
    cards.push({
        label: dataType === 'branches' ? 'Total Deposits' : 'Total Loan Amount',
        value: formatCurrency(totalAmount),
        change: amountChange,
        changePct: amountChangePct,
        icon: 'fas fa-dollar-sign',
        ariaLabel: `${dataType === 'branches' ? 'Total Deposits' : 'Total Loan Amount'}: ${formatCurrency(totalAmount)}`
    });
    
    // Card 3: Average Loan Size (with comparison) OR Branch Change 2021-2025
    if (dataType !== 'branches') {
        cards.push({
            label: 'Average Loan Size',
            value: formatCurrency(avgLoanSizeTarget),
            change: avgLoanSizeChange,
            changePct: avgLoanSizeChangePct,
            icon: 'fas fa-chart-line',
            ariaLabel: `Average Loan Size: ${formatCurrency(avgLoanSizeTarget)}`
        });
    } else {
        // For branches, show Average Deposits per Branch
        cards.push({
            label: 'Average Deposits per Branch',
            value: formatCurrency(avgLoanSizeTarget),
            change: avgLoanSizeChange,
            changePct: avgLoanSizeChangePct,
            icon: 'fas fa-building',
            ariaLabel: `Average Deposits per Branch: ${formatCurrency(avgLoanSizeTarget)}`
        });
    }
    
    // Market Concentration card removed per requirements
    
    let html = '<div class="summary-cards-container" role="region" aria-label="Summary Statistics">';
    html += '<div style="margin-bottom: 12px; padding: 8px 12px; background: #f0f7ff; border-left: 3px solid #2fade3; border-radius: 4px; font-size: 0.9rem; color: #333;">';
    html += '<i class="fas fa-info-circle" style="margin-right: 6px;"></i>';
    if (dataType === 'branches') {
        html += `<strong>Note:</strong> All feature cards display ${targetYear} data with changes since ${comparisonYear}.`;
    } else {
        html += `<strong>Note:</strong> All feature cards display ${targetYear} data.`;
    }
    html += '</div>';
    html += '<div class="summary-cards-grid">';
    
    cards.forEach((card, index) => {
        const changeClass = card.change !== null && card.change !== undefined
            ? (card.change >= 0 ? 'change-positive' : 'change-negative')
            : '';
        // Format change label: show comparison year to target year
        const changeDisplay = card.change !== null && card.change !== undefined
            ? `<div class="summary-card-change ${changeClass}" aria-label="Change from ${comparisonYear} to ${targetYear}: ${card.change >= 0 ? 'Increase' : 'Decrease'} of ${Math.abs(card.changePct).toFixed(1)}%">
                <i class="fas fa-${card.change >= 0 ? 'arrow-up' : 'arrow-down'}"></i>
                ${Math.abs(card.changePct).toFixed(1)}%
                <small style="display: block; font-size: 0.7em; margin-top: 2px; opacity: 0.8;">from ${comparisonYear} to ${targetYear}</small>
            </div>`
            : '';
        
        const valueStyle = card.color ? `style="color: ${card.color};"` : '';
        
        html += `<div class="summary-card" role="article" aria-labelledby="summary-card-${index}">`;
        html += `<div class="summary-card-icon" aria-hidden="true">`;
        html += `<i class="${card.icon}"></i>`;
        html += `</div>`;
        html += `<div class="summary-card-content">`;
        html += `<div class="summary-card-label" id="summary-card-${index}">${card.label}</div>`;
        html += `<div class="summary-card-value" ${valueStyle} aria-label="${card.ariaLabel}">${card.value}</div>`;
        if (card.concentrationLevel) {
            html += `<div class="summary-card-subtitle" style="color: ${card.color};">${card.concentrationLevel}</div>`;
        }
        if (changeDisplay) {
            html += changeDisplay;
        }
        html += `</div>`;
        html += `</div>`;
    });
    
    html += '</div></div>';
    return html;
}

function renderSummaryTable(data, dataType = 'hmda') {
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-line"></i> Summary Table</h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-table" data-table="summary" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-table" data-table="summary" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    html += '<div class="table-container">';
    html += '<table class="editable-table" data-table-id="summary">';
    html += '<thead><tr>';
    html += '<th>Year</th>';
    html += '<th>Total ' + (dataType === 'branches' ? 'Branches' : 'Loans') + '</th>';
    html += '<th>Total ' + (dataType === 'branches' ? 'Deposits' : 'Amount') + '</th>';
    html += '<th>Average ' + (dataType === 'branches' ? 'Deposits' : 'Amount') + '</th>';
    html += '</tr></thead>';
    html += '<tbody>';
    
    data.forEach(row => {
        html += '<tr>';
        html += `<td>${row.year}</td>`;
        html += `<td class="editable" data-field="total_loans" data-value="${row.total_loans}">${formatNumber(row.total_loans)}</td>`;
        html += `<td class="editable" data-field="total_amount" data-value="${row.total_amount}">${formatCurrency(row.total_amount)}</td>`;
        html += `<td class="editable" data-field="avg_amount" data-value="${row.avg_amount}">${formatCurrency(row.avg_amount)}</td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    html += '</div></div>';
    return html;
}

function renderSummaryChartByPurpose(data, dataType = 'hmda') {
    // Convert table to stacked area chart showing loan counts by year for each purpose
    const years = Object.keys(data[0] || {}).filter(k => k !== 'loan_purpose').sort();
    // Order: Home Equity at bottom, Refinance in middle, Home Purchase on top
    // For stacked charts, first in array = bottom layer, last = top layer
    const purposes = ['Home Equity', 'Refinance', 'Home Purchase'];
    const colors = {
        'Home Purchase': '#2fade3',
        'Refinance': '#ffc23a',
        'Home Equity': '#e82e2e'
    };
    
    // Calculate total counts per year for market share calculations
    const yearlyTotals = {};
    years.forEach(year => {
        yearlyTotals[year] = 0;
        purposes.forEach(purpose => {
            const row = data.find(r => r.loan_purpose === purpose);
            if (row && row[year]) {
                // The backend returns 'total_loans' in summary_by_purpose table
                yearlyTotals[year] += row[year].total_loans || row[year].count || 0;
            }
        });
    });
    
    // Prepare chart data - ensure all purposes are shown even if they have 0 data
    // Order: Home Equity first (bottom), Refinance second (middle), Home Purchase last (top)
    const datasets = [];
    purposes.forEach(purpose => {
        const row = data.find(r => r.loan_purpose === purpose);
        const countData = years.map(year => {
            if (row && row[year]) {
                // The backend returns 'total_loans' in summary_by_purpose table
                return row[year].total_loans || row[year].count || 0;
            }
            return 0;
        });
        
        // Use full color with opacity for fill, black for border
        // Higher opacity (E6 = 90%) to better match legend colors while still showing stacking
        const baseColor = colors[purpose] || '#818390';
        datasets.push({
            label: purpose,
            data: countData,
            borderColor: '#000000', // Black lines
            borderWidth: 2,
            backgroundColor: baseColor + 'E6', // Use E6 for ~90% opacity to better match legend colors
            tension: 0.4,
            fill: true,
            stack: 'stack0' // Stack all datasets together
        });
    });
    
    // Store raw data for Excel export
    if (!window.chartRawData) window.chartRawData = {};
    window.chartRawData['summary-by-purpose-chart'] = {
        data: data,
        years: years,
        purposes: purposes,
        yearlyTotals: yearlyTotals,
        metric: 'count' // Track that we're using counts, not amounts
    };
    
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-area"></i> Summary by Loan Purpose</h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-chart" data-chart="summary_by_purpose" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-chart" data-chart="summary_by_purpose" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    html += '<div class="chart-container" style="padding: 20px; position: relative; height: 400px;">';
    html += '<canvas id="summary-by-purpose-chart" width="400" height="400"></canvas>';
    html += '</div>';
    html += '</div>';
    
    // Store chart data for initialization
    if (!window.chartData) window.chartData = {};
    window.chartData['summary-by-purpose-chart'] = {
        type: 'line', // Stacked area chart
        data: {
            labels: years,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: { 
                        display: true, 
                        text: 'Number of Loans',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            },
            plugins: {
                legend: { 
                    display: true, 
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: { 
                    mode: 'index',
                    intersect: false,
                    itemSort: function(a, b) {
                        // Sort tooltip items: Home Purchase first, then Refinance, then Home Equity
                        const order = {
                            'Home Purchase': 0,
                            'Refinance': 1,
                            'Home Equity': 2
                        };
                        const orderA = order[a.dataset.label] !== undefined ? order[a.dataset.label] : 999;
                        const orderB = order[b.dataset.label] !== undefined ? order[b.dataset.label] : 999;
                        return orderA - orderB;
                    },
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y || 0;
                            const year = years[context.dataIndex];
                            const totalForYear = yearlyTotals[year] || 0;
                            const marketShare = totalForYear > 0 ? ((value / totalForYear) * 100).toFixed(1) : '0.0';
                            
                            // Format as number (loan count)
                            const formattedValue = formatNumber(value);
                            
                            return [
                                label + ': ' + formattedValue + ' loans',
                                'Market Share: ' + marketShare + '%'
                            ];
                        },
                        footer: function(tooltipItems) {
                            const year = years[tooltipItems[0].dataIndex];
                            const totalForYear = yearlyTotals[year] || 0;
                            const formattedTotal = formatNumber(totalForYear);
                            return 'Total Market: ' + formattedTotal + ' loans';
                        }
                    }
                },
                title: { display: false }
            }
        }
    };
    
    return html;
}

function renderHHIDisplay(hhiData, dataType = 'hmda') {
    if (!hhiData || hhiData.hhi === null) {
        return '';
    }
    
    const concentrationColors = {
        'Unconcentrated': '#2fade3',
        'Moderately Concentrated': '#ffc23a',
        'Highly Concentrated': '#e82e2e'
    };
    
    // For branches, show multiple HHI categories
    if (dataType === 'branches' && hhiData.all_branches) {
        let html = '<div class="hhi-display-card">';
        html += '<div class="hhi-header">';
        html += '<h4><i class="fas fa-chart-pie"></i> Market Concentration (HHI) - Deposits</h4>';
        html += `<span class="hhi-year">Year: ${hhiData.year}</span>`;
        html += '</div>';
        
        // All branches
        const allHhi = hhiData.all_branches;
        const allColor = concentrationColors[allHhi.concentration_level] || '#818390';
        const allHhiPercent = allHhi.hhi ? (allHhi.hhi / 10000 * 100).toFixed(1) : 0;
        const allTop5 = allHhi.top_lenders && allHhi.top_lenders.length > 0
            ? allHhi.top_lenders.reduce((sum, lender) => sum + lender.market_share, 0)
            : 0;
        
        html += '<div class="hhi-content">';
        html += '<div style="margin-bottom: 20px;">';
        html += '<h5 style="margin-bottom: 8px;">All Branches</h5>';
        html += '<div class="hhi-value">';
        html += `<div class="hhi-number" style="color: ${allColor}">${allHhi.hhi ? allHhi.hhi.toLocaleString() : 'N/A'}</div>`;
        html += `<div class="hhi-level" style="color: ${allColor}">${allHhi.concentration_level}</div>`;
        html += '</div>';
        html += '<div class="hhi-progress">';
        html += `<div class="hhi-bar" style="width: ${allHhiPercent}%; background: ${allColor}"></div>`;
        html += '</div>';
        html += `<p style="font-size: 0.85em; color: #666; margin: 8px 0;">Total Deposits: ${formatCurrency(allHhi.total_deposits || 0)} | Top 5: ${allTop5.toFixed(1)}%</p>`;
        html += '</div>';
        
        // LMI branches
        if (hhiData.lmi_branches && hhiData.lmi_branches.hhi !== null) {
            const lmiHhi = hhiData.lmi_branches;
            const lmiColor = concentrationColors[lmiHhi.concentration_level] || '#818390';
            const lmiHhiPercent = lmiHhi.hhi ? (lmiHhi.hhi / 10000 * 100).toFixed(1) : 0;
            html += '<div style="margin-bottom: 20px; padding-top: 20px; border-top: 1px solid #ddd;">';
            html += '<h5 style="margin-bottom: 8px;">Branches in LMI Neighborhoods</h5>';
            html += '<div class="hhi-value">';
            html += `<div class="hhi-number" style="color: ${lmiColor}">${lmiHhi.hhi.toLocaleString()}</div>`;
            html += `<div class="hhi-level" style="color: ${lmiColor}">${lmiHhi.concentration_level}</div>`;
            html += '</div>';
            html += '<div class="hhi-progress">';
            html += `<div class="hhi-bar" style="width: ${lmiHhiPercent}%; background: ${lmiColor}"></div>`;
            html += '</div>';
            html += `<p style="font-size: 0.85em; color: #666; margin: 8px 0;">Total Deposits: ${formatCurrency(lmiHhi.total_deposits || 0)}</p>`;
            html += '</div>';
        }
        
        // MMCT branches
        if (hhiData.mmct_branches && hhiData.mmct_branches.hhi !== null) {
            const mmctHhi = hhiData.mmct_branches;
            const mmctColor = concentrationColors[mmctHhi.concentration_level] || '#818390';
            const mmctHhiPercent = mmctHhi.hhi ? (mmctHhi.hhi / 10000 * 100).toFixed(1) : 0;
            html += '<div style="margin-bottom: 20px; padding-top: 20px; border-top: 1px solid #ddd;">';
            html += '<h5 style="margin-bottom: 8px;">Branches in Majority-Minority Neighborhoods</h5>';
            html += '<div class="hhi-value">';
            html += `<div class="hhi-number" style="color: ${mmctColor}">${mmctHhi.hhi.toLocaleString()}</div>`;
            html += `<div class="hhi-level" style="color: ${mmctColor}">${mmctHhi.concentration_level}</div>`;
            html += '</div>';
            html += '<div class="hhi-progress">';
            html += `<div class="hhi-bar" style="width: ${mmctHhiPercent}%; background: ${mmctColor}"></div>`;
            html += '</div>';
            html += `<p style="font-size: 0.85em; color: #666; margin: 8px 0;">Total Deposits: ${formatCurrency(mmctHhi.total_deposits || 0)}</p>`;
            html += '</div>';
        }
        
        // Both LMI and MMCT (deduplicated)
        if (hhiData.both_lmi_mmct_branches && hhiData.both_lmi_mmct_branches.hhi !== null) {
            const bothHhi = hhiData.both_lmi_mmct_branches;
            const bothColor = concentrationColors[bothHhi.concentration_level] || '#818390';
            const bothHhiPercent = bothHhi.hhi ? (bothHhi.hhi / 10000 * 100).toFixed(1) : 0;
            html += '<div style="margin-bottom: 20px; padding-top: 20px; border-top: 1px solid #ddd;">';
            html += '<h5 style="margin-bottom: 8px;">Branches in Both LMI & MMCT Neighborhoods</h5>';
            html += '<div class="hhi-value">';
            html += `<div class="hhi-number" style="color: ${bothColor}">${bothHhi.hhi.toLocaleString()}</div>`;
            html += `<div class="hhi-level" style="color: ${bothColor}">${bothHhi.concentration_level}</div>`;
            html += '</div>';
            html += '<div class="hhi-progress">';
            html += `<div class="hhi-bar" style="width: ${bothHhiPercent}%; background: ${bothColor}"></div>`;
            html += '</div>';
            html += `<p style="font-size: 0.85em; color: #666; margin: 8px 0;">Total Deposits: ${formatCurrency(bothHhi.total_deposits || 0)}</p>`;
            html += '</div>';
        }
        
        html += '<p class="hhi-explanation" style="font-size: 0.8em; color: #666; margin-top: 12px; font-style: italic;">';
        html += 'HHI measures market concentration by squaring each lender\'s market share (by deposits). ';
        html += 'HHI thresholds follow the 2023 U.S. Department of Justice and Federal Trade Commission Merger Guidelines: ';
        html += '&lt;1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), &gt;2,500 (Highly Concentrated).';
        html += '</p>';
        html += '</div></div>';
        return html;
    }
    
    // Original HHI display for HMDA/SB
    const color = concentrationColors[hhiData.concentration_level] || '#818390';
    const hhiPercent = (hhiData.hhi / 10000 * 100).toFixed(1);
    
    // Calculate top 5 concentration percentage
    const top5Concentration = hhiData.top_lenders && hhiData.top_lenders.length > 0
        ? hhiData.top_lenders.reduce((sum, lender) => sum + lender.market_share, 0)
        : 0;
    
    let html = '<div class="hhi-display-card">';
    html += '<div class="hhi-header">';
    html += '<h4><i class="fas fa-chart-pie"></i> Market Concentration (HHI)</h4>';
    html += `<span class="hhi-year">Year: ${hhiData.year}</span>`;
    html += '</div>';
    html += '<div class="hhi-content">';
    html += '<div class="hhi-value">';
    html += `<div class="hhi-number" style="color: ${color}">${hhiData.hhi.toLocaleString()}</div>`;
    html += `<div class="hhi-level" style="color: ${color}">${hhiData.concentration_level}</div>`;
    html += '</div>';
    html += '<div class="hhi-progress">';
    html += `<div class="hhi-bar" style="width: ${hhiPercent}%; background: ${color}"></div>`;
    html += '</div>';
    if (hhiData.top_lenders && hhiData.top_lenders.length > 0) {
        html += '<div class="hhi-top-lenders">';
        html += '<h5>Top 5 Lenders by Market Share</h5>';
        html += `<p class="hhi-note" style="font-size: 0.85em; color: #666; margin: 8px 0;">Top 5 lenders control <strong>${top5Concentration.toFixed(1)}%</strong> of the market</p>`;
        html += '<ul>';
        hhiData.top_lenders.forEach((lender, idx) => {
            html += `<li><span class="rank">${idx + 1}.</span> <span class="share">${lender.market_share}%</span> (${formatCurrency(lender.amount)})</li>`;
        });
        html += '</ul>';
        html += '<p class="hhi-explanation" style="font-size: 0.8em; color: #666; margin-top: 12px; font-style: italic;">';
        html += 'HHI measures market concentration by squaring each lender\'s market share. ';
        html += 'A market with many small lenders can have a low HHI even if the top 5 control a significant share. ';
        html += 'HHI thresholds follow the 2023 U.S. Department of Justice and Federal Trade Commission Merger Guidelines: ';
        html += '&lt;1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), &gt;2,500 (Highly Concentrated).';
        html += '</p>';
        html += '</div>';
    }
    html += '</div></div>';
    return html;
}

function renderDemographicsTable(data, dataType = 'hmda', dataByPurpose = null, acsData = null) {
    // Skip demographics table for branches (no demographic data)
    if (dataType === 'branches' || (!data || data.length === 0) && !dataByPurpose) {
        return '';
    }
    
    // Use dataByPurpose if available, otherwise fall back to data
    const useTabs = dataByPurpose && Object.keys(dataByPurpose).length > 0 && dataType !== 'sb'; // No tabs for SB
    const currentData = useTabs ? (dataByPurpose.all || data) : data;
    
    if (!currentData || currentData.length === 0) {
        return '';
    }
    
    // Calculate total loans with demographic information
    const years = Object.keys(currentData[0] || {}).filter(k => k !== 'group' && k !== 'change').sort();
    const latestYear = years[years.length - 1];
    const firstYear = years[0];
    
    // Use ACS data from backend if available
    const totalPersons2024 = acsData && acsData.total_population ? acsData.total_population : 0;
    const censusData = acsData && acsData.demographics ? acsData.demographics : {};
    
    // For SB, use household income distribution instead of demographics
    const isSB = dataType === 'sb';
    const tableTitle = isSB ? 'Income Groups' : 'Demographic Overview';
    const columnHeader = isSB ? 'Income Group' : 'Demographic Group';
    const censusColumnLabel = isSB ? 'Census ACS<br><small>(% of Households)</small>' : 'Census ACS<br><small>(% of Population)</small>';
    
    // Debug logging
    debugLog('Demographics table - ACS data:', {
        hasAcsData: !!acsData,
        totalPopulation: totalPersons2024,
        demographicsKeys: censusData ? Object.keys(censusData) : [],
        demographics: censusData,
        isSB: isSB
    });
    
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += `<h4><i class="fas fa-${isSB ? 'dollar-sign' : 'users'}"></i> ${tableTitle}</h4>`;
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-table" data-table="demographics" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-table" data-table="demographics" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    
    // Tab interface (only for HMDA, not SB)
    if (useTabs) {
        html += '<div class="purpose-tabs" style="display: flex; border-bottom: 2px solid #2fade3; margin-bottom: 0;">';
        html += '<button class="purpose-tab-btn active" data-purpose="all" data-action="switch-demographics-tab" aria-label="Show all loans for Demographic Overview" role="tab" aria-selected="true" tabindex="0" style="flex: 1; padding: 12px 20px; background: #2fade3; color: white; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">All Loans</button>';
        html += '<button class="purpose-tab-btn" data-purpose="Home Purchase" data-action="switch-demographics-tab" aria-label="Show home purchase loans for Demographic Overview" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Home Purchase</button>';
        html += '<button class="purpose-tab-btn" data-purpose="Refinance" data-action="switch-demographics-tab" aria-label="Show refinance loans for Demographic Overview" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Refinance</button>';
        html += '<button class="purpose-tab-btn" data-purpose="Home Equity" data-action="switch-demographics-tab" aria-label="Show home equity loans for Demographic Overview" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Home Equity</button>';
        html += '</div>';
    }
    
    // Render table for each purpose (or single table if no tabs)
    const purposes = useTabs ? ['all', 'Home Purchase', 'Refinance', 'Home Equity'] : ['all'];
    purposes.forEach((purpose, idx) => {
        const purposeData = useTabs ? (dataByPurpose[purpose] || []) : currentData;
        if (!purposeData || purposeData.length === 0) return;
        
        html += `<div class="purpose-tab-content demographics-tab-content ${idx === 0 ? 'active' : ''}" data-purpose="${purpose}" style="display: ${idx === 0 ? 'block' : 'none'};">`;
    html += '<div class="table-container">';
        html += '<table class="editable-table" data-table-id="demographics" data-purpose="' + purpose + '" style="table-layout: fixed; width: 100%;">';
    html += '<thead><tr>';
        html += `<th style="width: 25%;">${columnHeader}</th>`;
        html += `<th style="width: 12%; text-align: center;">${censusColumnLabel}</th>`;
    years.forEach(year => {
            html += `<th style="width: ${70 / (years.length + 1)}%;">${year}</th>`;
    });
        html += '<th style="width: 12%;">Change Over Time<br><small>(percentage points)</small></th>';
    html += '</tr></thead>';
    html += '<tbody>';
    
        // Top row: Total loans with demographic/income information - no ACS data shown
    html += '<tr class="total-row">';
        html += `<td class="group-name"><strong>Total Loans with ${isSB ? 'Income' : 'Demographic'} Information</strong></td>`;
        html += '<td style="text-align: center;">-</td>';
    years.forEach(year => {
        let yearTotal = 0;
            purposeData.forEach(row => {
            const yearData = row[year] || {};
            yearTotal += yearData.count || 0;
        });
        html += `<td><strong>${formatNumber(yearTotal)}</strong></td>`;
    });
    html += '<td>-</td>'; // No change for total
    html += '</tr>';
    
        // For SB, use household income distribution from ACS data
        // For HMDA, use demographics from ACS data
        let sortedPurposeData;
        if (isSB) {
            // For SB, get household income distribution from acsData
            const householdIncomeData = acsData && acsData.household_income_distribution ? acsData.household_income_distribution : {};
            // Map income groups to their ACS percentages
            const incomeGroupMap = {
                'Low Income': householdIncomeData['Low Income'] || null,
                'Moderate Income': householdIncomeData['Moderate Income'] || null,
                'Middle Income': householdIncomeData['Middle Income'] || null,
                'Upper Income': householdIncomeData['Upper Income'] || null
            };
            
            // Sort by ACS household percentage (descending)
            sortedPurposeData = [...purposeData].sort((a, b) => {
                const acsPercentA = incomeGroupMap[a.group] !== undefined ? incomeGroupMap[a.group] : -1;
                const acsPercentB = incomeGroupMap[b.group] !== undefined ? incomeGroupMap[b.group] : -1;
                if (acsPercentA >= 0 && acsPercentB >= 0) {
                    return acsPercentB - acsPercentA;
                }
                if (acsPercentA >= 0 && acsPercentB < 0) return -1;
                if (acsPercentA < 0 && acsPercentB >= 0) return 1;
                return 0;
            });
        } else {
            // Sort demographic groups by ACS population share (descending order)
            sortedPurposeData = [...purposeData].sort((a, b) => {
                const acsPercentA = censusData && censusData[a.group] !== undefined ? censusData[a.group] : -1;
                const acsPercentB = censusData && censusData[b.group] !== undefined ? censusData[b.group] : -1;
                if (acsPercentA >= 0 && acsPercentB >= 0) {
                    return acsPercentB - acsPercentA;
                }
                if (acsPercentA >= 0 && acsPercentB < 0) return -1;
                if (acsPercentA < 0 && acsPercentB >= 0) return 1;
                return 0;
            });
        }
        
        // Subsequent rows: percentages only, sorted by ACS share
        sortedPurposeData.forEach(row => {
        html += '<tr>';
            // Get ACS percentage - for SB use household income distribution, for HMDA use demographics
            let acsPercent = null;
            if (isSB) {
                const householdIncomeData = acsData && acsData.household_income_distribution ? acsData.household_income_distribution : {};
                acsPercent = householdIncomeData[row.group] !== undefined ? householdIncomeData[row.group] : null;
            } else {
                acsPercent = censusData && censusData[row.group] !== undefined ? censusData[row.group] : null;
            }
            html += `<td class="group-name">${row.group}</td>`;
            // ACS column: percentage only, centered
            html += `<td style="text-align: center;">${acsPercent !== null && acsPercent !== undefined && acsPercent >= 0 ? acsPercent.toFixed(1) + '%' : 'N/A'}</td>`;
        years.forEach(year => {
            const cellData = row[year] || {count: 0, percent: 0};
            html += `<td data-field="${year}" data-group="${row.group}" data-value='${JSON.stringify(cellData)}'>`;
            html += `${cellData.percent.toFixed(2)}%`;
            html += '</td>';
        });
        // Change over time: percentage point change
        if (row.change && years.length >= 2) {
            const firstYearData = row[firstYear] || {percent: 0};
            const lastYearData = row[latestYear] || {percent: 0};
            const pctPointChange = lastYearData.percent - firstYearData.percent;
            const changeClass = pctPointChange >= 0 ? 'positive' : 'negative';
            html += `<td class="change-cell ${changeClass}">`;
            html += `${pctPointChange >= 0 ? '+' : ''}${pctPointChange.toFixed(2)} pp`;
            html += '</td>';
        } else {
            html += '<td>-</td>';
        }
        html += '</tr>';
    });
    
    html += '</tbody></table>';
        html += '</div>';
        html += '</div>';
    });
    
    html += '</div>';
    return html;
}

// Tab switching function for demographics
function switchDemographicsTab(purpose) {
    // Update tab buttons
    document.querySelectorAll('.purpose-tab-btn[data-purpose]').forEach(btn => {
        if (btn.getAttribute('data-purpose') === purpose) {
            btn.classList.add('active');
            btn.style.background = '#2fade3';
            btn.style.color = 'white';
        } else {
            btn.classList.remove('active');
            btn.style.background = '#e0e0e0';
            btn.style.color = '#333';
        }
    });
    
    // Update tab content
    document.querySelectorAll('.demographics-tab-content').forEach(content => {
        if (content.getAttribute('data-purpose') === purpose) {
            content.style.display = 'block';
        } else {
            content.style.display = 'none';
        }
    });
}

function renderIncomeNeighborhoodTable(data, dataByPurpose = null, avgMinorityPercentage = null, householdIncomeData = null, tractDistributions = null, dataType = 'hmda', mmctStats = null) {
    // Use dataByPurpose if available, otherwise fall back to data
    const useTabs = dataByPurpose && Object.keys(dataByPurpose).length > 0;
    const currentData = useTabs ? (dataByPurpose.all || data) : data;
    
    // Debug logging
    debugLog('Income & Neighborhood table - Household income data:', {
        hasHouseholdIncomeData: !!householdIncomeData,
        distribution: householdIncomeData && householdIncomeData.household_income_distribution ? householdIncomeData.household_income_distribution : {},
        metroAmi: householdIncomeData && householdIncomeData.metro_ami ? householdIncomeData.metro_ami : null
    });
    debugLog('Income & Neighborhood table - Tract distributions:', {
        hasTractDistributions: !!tractDistributions,
        tractIncomeDistribution: tractDistributions && tractDistributions.tract_income_distribution ? tractDistributions.tract_income_distribution : {},
        tractMinorityDistribution: tractDistributions && tractDistributions.tract_minority_distribution ? tractDistributions.tract_minority_distribution : {}
    });
    
    if (!currentData || currentData.length === 0) {
        return '';
    }
    
    // Find total loans/branches row and separate income/neighborhood indicators
    const totalRow = currentData.find(row => row.indicator === 'Total Loans' || row.indicator === 'Total Branches');
    const incomeRows = currentData.filter(row => 
        ['Low Income', 'Moderate Income', 'Middle Income', 'Upper Income'].includes(row.indicator)
    );
    const neighborhoodRows = currentData.filter(row => 
        ['Low-to-Moderate Income Census Tract (LMICT)', 'Low Income Tracts', 'Moderate Income Tracts', 'Middle Income Tracts', 'Upper Income Tracts'].includes(row.indicator)
    );
    
    const years = Object.keys(currentData[0] || {}).filter(k => k !== 'indicator' && k !== 'change').sort();
    
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-home" aria-hidden="true"></i> Income & Neighborhood Indicators</h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-table" data-table="income_neighborhood" data-format="png" aria-label="Export Income & Neighborhood Indicators table as PNG image" title="Export as Image"><i class="fas fa-image" aria-hidden="true"></i> PNG</button>';
    html += '<button class="btn-share-table" data-table="income_neighborhood" aria-label="Share Income & Neighborhood Indicators table to social media" title="Share to Social Media"><i class="fas fa-share-alt" aria-hidden="true"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    
    // Tab interface for loan purposes (HMDA only)
    if (useTabs && dataType !== 'sb') {
        html += '<div class="purpose-tabs" style="display: flex; border-bottom: 2px solid #2fade3; margin-bottom: 0;">';
        html += '<button class="purpose-tab-btn active" data-purpose="all" data-action="switch-income-tab" aria-label="Show all loans for Income & Neighborhood Indicators" role="tab" aria-selected="true" tabindex="0" style="flex: 1; padding: 12px 20px; background: #2fade3; color: white; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">All Loans</button>';
        html += '<button class="purpose-tab-btn" data-purpose="Home Purchase" data-action="switch-income-tab" aria-label="Show home purchase loans for Income & Neighborhood Indicators" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Home Purchase</button>';
        html += '<button class="purpose-tab-btn" data-purpose="Refinance" data-action="switch-income-tab" aria-label="Show refinance loans for Income & Neighborhood Indicators" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Refinance</button>';
        html += '<button class="purpose-tab-btn" data-purpose="Home Equity" data-action="switch-income-tab" aria-label="Show home equity loans for Income & Neighborhood Indicators" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Home Equity</button>';
        html += '</div>';
    }
    
    // Tab interface for counts/amounts (SB only)
    if (dataType === 'sb') {
        html += '<div class="purpose-tabs" style="display: flex; border-bottom: 2px solid #2fade3; margin-bottom: 0;">';
        html += '<button class="purpose-tab-btn active" data-data-type="count" data-action="switch-income-data-type" aria-label="Show number of loans" role="tab" aria-selected="true" tabindex="0" style="flex: 1; padding: 12px 20px; background: #2fade3; color: white; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Number of Loans</button>';
        html += '<button class="purpose-tab-btn" data-data-type="amount" data-action="switch-income-data-type" aria-label="Show amount of loans" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Amount of Loans</button>';
        html += '</div>';
    }
    
    // Render table for each purpose (HMDA) or single table with counts/amounts tabs (SB)
    const purposes = (useTabs && dataType !== 'sb') ? ['all', 'Home Purchase', 'Refinance', 'Home Equity'] : ['all'];
    const dataTypes = dataType === 'sb' ? ['count', 'amount'] : ['count']; // SB has both, HMDA only has counts
    
    console.log(`[Income & Neighborhood] Rendering ${purposes.length} tabs, useTabs=${useTabs}, dataByPurpose keys:`, useTabs && dataByPurpose ? Object.keys(dataByPurpose) : 'N/A');
    
    purposes.forEach((purpose, purposeIdx) => {
        const purposeData = useTabs && dataType !== 'sb' ? (dataByPurpose[purpose] || []) : currentData;
        // Always render tab content structure, even if data is empty (prevents disappearing tabs)
        const hasData = purposeData && purposeData.length > 0;
        console.log(`[Income & Neighborhood] Rendering tab ${purposeIdx} (${purpose}), hasData=${hasData}, will create div`);
        
        // Debug logging for each purpose tab
        console.log(`[Income & Neighborhood] Tab: ${purpose}, hasData: ${hasData}, dataLength: ${purposeData ? purposeData.length : 0}`);
        if (hasData && purposeData.length > 0) {
            console.log(`[Income & Neighborhood] Tab: ${purpose}, indicators:`, purposeData.map(r => r.indicator));
        }
        
        // Get years from currentData (all loans) if purposeData is empty
        const purposeYears = hasData 
            ? Object.keys(purposeData[0] || {}).filter(k => k !== 'indicator' && k !== 'change').sort()
            : years;
        
        const purposeTotalRow = hasData ? purposeData.find(row => row.indicator === 'Total Loans' || row.indicator === 'Total Branches') : null;
        const purposeIncomeRows = hasData ? purposeData.filter(row => 
            ['Low Income', 'Moderate Income', 'Middle Income', 'Upper Income'].includes(row.indicator)
        ) : [];
        const purposeLMIBorrowersRow = hasData ? purposeData.find(row => row.indicator === 'Low & Moderate Income Borrowers') : null;
        const purposeNeighborhoodRows = hasData ? purposeData.filter(row => 
            (dataType === 'sb' ? 
                ['Low Income Tracts', 'Moderate Income Tracts', 'Middle Income Tracts', 'Upper Income Tracts'].includes(row.indicator) :
                ['Low Income Tracts', 'Moderate Income Tracts', 'Middle Income Tracts', 'Upper Income Tracts'].includes(row.indicator)
            )
        ) : [];
        const purposeLMITractsRow = hasData ? purposeData.find(row => row.indicator === 'Low & Moderate Income Census Tracts') : null;
        const purposeMMCTRow = hasData ? purposeData.find(row => row.indicator === 'Majority-Minority Census Tracts (MMCT)') : null;
        const purposeMMCTBreakdownRows = hasData ? purposeData.filter(row => 
            ['Low Minority Tracts', 'Moderate Minority Tracts', 'Middle Minority Tracts', 'High Minority Tracts'].includes(row.indicator)
        ) : [];
        
        // For SB, render both count and amount tabs
        dataTypes.forEach((dataTypeTab, dataTypeIdx) => {
            const isCountTab = dataTypeTab === 'count';
            const isActive = purposeIdx === 0 && (dataType === 'sb' ? dataTypeIdx === 0 : true);
            
            html += `<div class="purpose-tab-content income-neighborhood-tab-content ${isActive ? 'active' : ''}" data-purpose="${purpose}" data-data-type="${dataTypeTab}" style="display: ${isActive ? 'block' : 'none'};">`;
            html += '<div class="table-container income-neighborhood-table-container">';
            html += '<table class="editable-table" data-table-id="income_neighborhood" data-purpose="' + purpose + '" data-data-type="' + dataTypeTab + '">';
    html += '<thead><tr>';
    html += '<th>Indicator</th>';
            // Add ACS column for all data types - shows % of households in tract categories
            html += '<th style="text-align: center;">Census ACS<br><small>(% of Households)</small></th>';
            purposeYears.forEach(year => {
        html += `<th>${year}</th>`;
    });
    html += '</tr></thead>';
    html += '<tbody>';
    
    // Total Loans/Branches row
            if (purposeTotalRow) {
        html += '<tr class="total-row">';
        const totalLabel = dataType === 'branches' ? 'Total Branches' : 'Total Loans';
        html += `<td class="indicator-name"><strong>${totalLabel}</strong></td>`;
                // Add ACS column for all tabs - No ACS data for total loans
                html += '<td style="text-align: center;">—</td>';
                purposeYears.forEach(year => {
                    const cellData = purposeTotalRow[year] || {count: 0, percent: 0, amount: 0, amount_percent: 0};
                    if (dataType === 'sb' && !isCountTab) {
                        // Show amount for SB amount tab
                        html += `<td><strong>${formatCurrency(cellData.amount || 0)}</strong></td>`;
                    } else {
                        // Show count for HMDA or SB count tab
                        html += `<td><strong>${formatNumber(cellData.count || 0)}</strong></td>`;
                    }
                });
                html += '</tr>';
            } else if (!hasData) {
                // Show empty state message if no data for this purpose
                const colSpan = purposeYears.length + 2; // Indicator + ACS + years
                html += `<tr><td colspan="${colSpan}" style="text-align: center; padding: 40px; color: #666;">No data available${dataType === 'sb' && dataTypeTab === 'amount' ? ' for loan amounts' : dataType === 'sb' && dataTypeTab === 'count' ? ' for loan counts' : ' for this loan purpose'}</td></tr>`;
            } else {
                // hasData is true but purposeTotalRow is null - still render table structure
                // This can happen if data structure doesn't match expected format
                html += '<tr class="total-row">';
                const totalLabel = dataType === 'branches' ? 'Total Branches' : 'Total Loans';
                html += `<td class="indicator-name" style="font-size: 1em;"><strong>${totalLabel}</strong></td>`;
                html += '<td style="text-align: center;">—</td>';
                purposeYears.forEach(year => {
                    html += '<td><strong>0</strong></td>';
        });
        html += '</tr>';
    }
    
            // Low & Moderate Income Borrowers (expandable) - show combined percentage in header (HMDA only)
            if (purposeLMIBorrowersRow && dataType !== 'sb') {
                console.log(`[Income & Neighborhood] Tab ${purpose}: Rendering LMI Borrowers row`);
                const colSpan = purposeYears.length + 2; // Indicator + ACS + years
                html += `<tr class="section-divider"><td colspan="${colSpan}"></td></tr>`; // Visual separator
                html += '<tr class="expandable-header" data-expand="lmi-borrowers-' + purpose + '-' + dataTypeTab + '">';
    html += '<td class="indicator-name"><i class="fas fa-chevron-right expand-icon"></i> <strong>Low & Moderate Income Borrowers</strong></td>';
                // Add ACS column for all tabs (HMDA only)
                if (householdIncomeData && householdIncomeData.household_income_distribution) {
                    const lmiPct = (householdIncomeData.household_income_distribution['Low Income'] || 0) + 
                                  (householdIncomeData.household_income_distribution['Moderate Income'] || 0);
                    html += `<td style="text-align: center;">${lmiPct.toFixed(1)}%</td>`;
                } else {
                    html += '<td style="text-align: center;">N/A</td>';
                }
                purposeYears.forEach(year => {
                    const cellData = purposeLMIBorrowersRow[year] || {count: 0, percent: 0};
                    html += `<td><strong>${cellData.percent.toFixed(2)}%</strong></td>`;
                });
    html += '</tr>';
    
                // Expanded rows for LMI Borrowers (hidden by default) - show all income brackets
                purposeIncomeRows.forEach(row => {
                    html += `<tr class="expandable-row" data-expand="lmi-borrowers-${purpose}-${dataTypeTab}" style="display: none;">`;
        html += `<td class="indicator-name sub-indicator">${row.indicator}</td>`;
                    // Add ACS column for all tabs (HMDA only)
                    if (householdIncomeData && householdIncomeData.household_income_distribution) {
                        const acsPct = householdIncomeData.household_income_distribution[row.indicator] || null;
                        html += `<td style="text-align: center;">${acsPct !== null && acsPct !== undefined ? acsPct.toFixed(1) + '%' : 'N/A'}</td>`;
                    } else {
                        html += '<td style="text-align: center;">N/A</td>';
                    }
                    purposeYears.forEach(year => {
            const cellData = row[year] || {count: 0, percent: 0};
            html += `<td>${cellData.percent.toFixed(2)}%</td>`;
        });
        html += '</tr>';
    });
            }
        
            // Low & Moderate Income Census Tracts (expandable) - show combined percentage in header
            // Always show this section if we have neighborhood rows OR the LMI tracts row
            // For SB, we should only show this if we have the combined row, not the individual LMICT row
            // Always show for SB if we have any neighborhood data
            console.log(`[Income & Neighborhood] Tab ${purpose}: purposeLMITractsRow=${!!purposeLMITractsRow}, purposeNeighborhoodRows.length=${purposeNeighborhoodRows.length}`);
            if ((purposeLMITractsRow || purposeNeighborhoodRows.length > 0 || (dataType === 'sb' && purposeNeighborhoodRows.length >= 0)) && 
                !(dataType === 'sb' && purposeData.find(row => row.indicator === 'Low-to-Moderate Income Census Tract (LMICT)'))) {
                const colSpan = purposeYears.length + 2; // Indicator + ACS + years
                // Always create the header row if we have neighborhood rows or LMI tracts row
                html += `<tr class="section-divider"><td colspan="${colSpan}"></td></tr>`; // Visual separator
                html += '<tr class="expandable-header" data-expand="lmi-tracts-' + purpose + '-' + dataTypeTab + '">';
                html += '<td class="indicator-name"><i class="fas fa-chevron-right expand-icon"></i> <strong>Low & Moderate Income Census Tracts</strong></td>';
                // Add ACS column for all tabs - Use tract income distribution (households in tracts, not borrower income)
                if (tractDistributions && tractDistributions.tract_income_distribution) {
                    const lmiTractPct = (tractDistributions.tract_income_distribution['Low Income'] || 0) + 
                                       (tractDistributions.tract_income_distribution['Moderate Income'] || 0);
                    html += `<td style="text-align: center;">${lmiTractPct.toFixed(1)}%</td>`;
                } else {
                    html += '<td style="text-align: center;">N/A</td>';
                }
                purposeYears.forEach(year => {
                    const cellData = purposeLMITractsRow ? (purposeLMITractsRow[year] || {count: 0, percent: 0, amount: 0, amount_percent: 0}) : {count: 0, percent: 0, amount: 0, amount_percent: 0};
                    if (dataType === 'sb' && !isCountTab) {
                        html += `<td><strong>${cellData.amount_percent ? cellData.amount_percent.toFixed(2) + '%' : formatCurrency(cellData.amount || 0)}</strong></td>`;
                    } else {
                        html += `<td><strong>${cellData.percent.toFixed(2)}%</strong></td>`;
                    }
                });
                html += '</tr>';
                
                // Expanded rows for LMI Tracts (hidden by default) - show all income tract brackets
                // Always render these if we have the neighborhood rows, even if purposeLMITractsRow doesn't exist
                if (purposeNeighborhoodRows.length > 0) {
                    purposeNeighborhoodRows.forEach(row => {
                        html += `<tr class="expandable-row" data-expand="lmi-tracts-${purpose}-${dataTypeTab}" style="display: none;">`;
                        html += `<td class="indicator-name sub-indicator">${row.indicator}</td>`;
                        // Add ACS column for all tabs - Use tract income distribution (households in tracts)
                        let acsPct = null;
                        if (tractDistributions && tractDistributions.tract_income_distribution) {
                            // Map row indicator to tract income distribution key (remove " Tracts" suffix)
                            const acsKey = row.indicator.replace(' Tracts', '');
                            acsPct = tractDistributions.tract_income_distribution[acsKey];
                            // Handle case where value might be 0 (which is falsy but valid)
                            if (acsPct === null || acsPct === undefined) {
                                acsPct = null;
                            }
                        }
                        html += `<td style="text-align: center;">${acsPct !== null && acsPct !== undefined ? Number(acsPct).toFixed(1) + '%' : 'N/A'}</td>`;
                        purposeYears.forEach(year => {
                            const cellData = row[year] || {count: 0, percent: 0, amount: 0, amount_percent: 0};
                            if (dataType === 'sb' && !isCountTab) {
                                html += `<td>${cellData.amount_percent ? cellData.amount_percent.toFixed(2) + '%' : formatCurrency(cellData.amount || 0)}</td>`;
                            } else {
                                html += `<td>${cellData.percent.toFixed(2)}%</td>`;
                            }
                        });
                        html += '</tr>';
                    });
                } else {
                    // If no individual income tract rows exist, create placeholder rows to show structure
                    const incomeTractLabels = ['Low Income Tracts', 'Moderate Income Tracts', 'Middle Income Tracts', 'Upper Income Tracts'];
                    incomeTractLabels.forEach(label => {
                        html += `<tr class="expandable-row" data-expand="lmi-tracts-${purpose}-${dataTypeTab}" style="display: none;">`;
                        html += `<td class="indicator-name sub-indicator">${label}</td>`;
                        html += '<td style="text-align: center;">N/A</td>';
                        purposeYears.forEach(year => {
                            html += '<td>0.00%</td>';
                        });
                        html += '</tr>';
                    });
                }
            }
        
            // Majority-Minority Census Tracts (MMCT) - expandable section
            // Always show MMCT row if it exists in the data, even if values are zero
            // For SB, always show MMCT section (should always have MMCT data)
            console.log(`[Income & Neighborhood] Tab ${purpose}: purposeMMCTRow=${!!purposeMMCTRow}, purposeMMCTBreakdownRows.length=${purposeMMCTBreakdownRows.length}`);
            if (purposeMMCTRow || purposeMMCTBreakdownRows.length > 0 || dataType === 'sb') {
                const colSpan = purposeYears.length + 2; // Indicator + ACS + years
                html += `<tr class="section-divider"><td colspan="${colSpan}"></td></tr>`; // Visual separator
                html += '<tr class="expandable-header" data-expand="mmct-' + purpose + '-' + dataTypeTab + '">';
                html += '<td class="indicator-name"><i class="fas fa-chevron-right expand-icon"></i> <strong>Majority-Minority Census Tracts (MMCT)</strong></td>';
                // Add ACS column for all tabs - MMCT is % of households in tracts with minority % >= 50%
                if (tractDistributions && tractDistributions.mmct_percentage !== null && tractDistributions.mmct_percentage !== undefined) {
                    html += `<td style="text-align: center;">${tractDistributions.mmct_percentage.toFixed(1)}%</td>`;
                } else {
                    html += '<td style="text-align: center;">N/A</td>';
                }
                purposeYears.forEach(year => {
                    const cellData = purposeMMCTRow ? (purposeMMCTRow[year] || {count: 0, percent: 0, amount: 0, amount_percent: 0}) : {count: 0, percent: 0, amount: 0, amount_percent: 0};
                    if (dataType === 'sb' && !isCountTab) {
                        html += `<td><strong>${cellData.amount_percent ? cellData.amount_percent.toFixed(2) + '%' : formatCurrency(cellData.amount || 0)}</strong></td>`;
                    } else {
                        html += `<td><strong>${cellData.percent.toFixed(2)}%</strong></td>`;
                    }
                });
                html += '</tr>';
                
                // Expanded rows for MMCT breakdowns (hidden by default)
                // Always render breakdown rows if they exist, even if MMCT row doesn't
                // For SB, always create placeholder rows if breakdown rows don't exist
                if (purposeMMCTBreakdownRows.length > 0) {
                    purposeMMCTBreakdownRows.forEach(row => {
                    html += `<tr class="expandable-row" data-expand="mmct-${purpose}-${dataTypeTab}" style="display: none;">`;
                    
                    // Add percentage range to label based on mmctStats - always calculate and show ranges
                    let indicatorLabel = row.indicator;
                    let rangeText = '';
                    
                    if (mmctStats && purposeYears.length > 0) {
                        // Use the first year's stats (they should be similar across years)
                        const firstYear = purposeYears[0];
                        const yearStats = mmctStats[firstYear];
                        if (yearStats && yearStats.mean_minority !== null && yearStats.stddev_minority !== null && 
                            yearStats.mean_minority >= 0 && yearStats.stddev_minority >= 0) {
                            const mean = yearStats.mean_minority;
                            const stddev = yearStats.stddev_minority;
                            
                            if (row.indicator === 'Low Minority Tracts') {
                                const maxVal = Math.max(0, mean - stddev);
                                rangeText = ` (0-${maxVal.toFixed(1)}%)`;
                            } else if (row.indicator === 'Moderate Minority Tracts') {
                                const minVal = Math.max(0, mean - stddev);
                                rangeText = ` (${minVal.toFixed(1)}-${mean.toFixed(1)}%)`;
                            } else if (row.indicator === 'Middle Minority Tracts') {
                                rangeText = ` (${mean.toFixed(1)}-${(mean + stddev).toFixed(1)}%)`;
                            } else if (row.indicator === 'High Minority Tracts') {
                                const minVal = mean + stddev;
                                rangeText = ` (${minVal.toFixed(1)}-100%)`;
                            }
                        } else {
                            // Fallback to generic ranges if stats not available
                            if (row.indicator === 'Low Minority Tracts') {
                                rangeText = ' (0-10%)';
                            } else if (row.indicator === 'Moderate Minority Tracts') {
                                rangeText = ' (10-30%)';
                            } else if (row.indicator === 'Middle Minority Tracts') {
                                rangeText = ' (30-50%)';
                            } else if (row.indicator === 'High Minority Tracts') {
                                rangeText = ' (50-100%)';
                            }
                        }
                    } else {
                        // Fallback to generic ranges if mmctStats not available
                        if (row.indicator === 'Low Minority Tracts') {
                            rangeText = ' (0-10%)';
                        } else if (row.indicator === 'Moderate Minority Tracts') {
                            rangeText = ' (10-30%)';
                        } else if (row.indicator === 'Middle Minority Tracts') {
                            rangeText = ' (30-50%)';
                        } else if (row.indicator === 'High Minority Tracts') {
                            rangeText = ' (50-100%)';
                        }
                    }
                    
                    indicatorLabel = row.indicator + `<span style="font-style: italic; font-weight: normal; color: #666;">${rangeText}</span>`;
                    
                    html += `<td class="indicator-name sub-indicator">${indicatorLabel}</td>`;
                    // Add ACS column for all tabs - Use tract minority distribution
                    if (tractDistributions && tractDistributions.tract_minority_distribution) {
                        // Map row indicator to tract minority distribution key
                        const acsKey = row.indicator.replace(' Tracts', '');
                        const acsPct = tractDistributions.tract_minority_distribution[acsKey] || null;
                        html += `<td style="text-align: center;">${acsPct !== null && acsPct !== undefined ? acsPct.toFixed(1) + '%' : 'N/A'}</td>`;
                    } else {
                        html += '<td style="text-align: center;">N/A</td>';
                    }
                    purposeYears.forEach(year => {
                        const cellData = row[year] || {count: 0, percent: 0, amount: 0, amount_percent: 0};
                        if (dataType === 'sb' && !isCountTab) {
                            html += `<td>${cellData.amount_percent ? cellData.amount_percent.toFixed(2) + '%' : formatCurrency(cellData.amount || 0)}</td>`;
                        } else {
                            html += `<td>${cellData.percent.toFixed(2)}%</td>`;
                        }
                    });
                    html += '</tr>';
                    });
                } else {
                    // If no breakdown rows exist, create placeholder rows to show structure
                    // Calculate ranges from mmctStats if available
                    let breakdownLabels = [
                        {indicator: 'Low Minority Tracts', range: '0-10%'},
                        {indicator: 'Moderate Minority Tracts', range: '10-30%'},
                        {indicator: 'Middle Minority Tracts', range: '30-50%'},
                        {indicator: 'High Minority Tracts', range: '50-100%'}
                    ];
                    
                    // Update ranges from mmctStats if available
                    if (mmctStats && purposeYears.length > 0) {
                        const firstYear = purposeYears[0];
                        const yearStats = mmctStats[firstYear];
                        if (yearStats && yearStats.mean_minority !== null && yearStats.stddev_minority !== null && 
                            yearStats.mean_minority >= 0 && yearStats.stddev_minority >= 0) {
                            const mean = yearStats.mean_minority;
                            const stddev = yearStats.stddev_minority;
                            breakdownLabels = [
                                {indicator: 'Low Minority Tracts', range: `0-${Math.max(0, mean - stddev).toFixed(1)}%`},
                                {indicator: 'Moderate Minority Tracts', range: `${Math.max(0, mean - stddev).toFixed(1)}-${mean.toFixed(1)}%`},
                                {indicator: 'Middle Minority Tracts', range: `${mean.toFixed(1)}-${(mean + stddev).toFixed(1)}%`},
                                {indicator: 'High Minority Tracts', range: `${(mean + stddev).toFixed(1)}-100%`}
                            ];
                        }
                    }
                    
                    breakdownLabels.forEach(label => {
                        html += `<tr class="expandable-row" data-expand="mmct-${purpose}-${dataTypeTab}" style="display: none;">`;
                        html += `<td class="indicator-name sub-indicator">${label.indicator} <span style="font-style: italic; font-weight: normal; color: #666;">(${label.range})</span></td>`;
                        // Add ACS column for all tabs - Use tract minority distribution
                        if (tractDistributions && tractDistributions.tract_minority_distribution) {
                            // Map label indicator to tract minority distribution key
                            const acsKey = label.indicator.replace(' Tracts', '');
                            const acsPct = tractDistributions.tract_minority_distribution[acsKey] || null;
                            html += `<td style="text-align: center;">${acsPct !== null && acsPct !== undefined ? acsPct.toFixed(1) + '%' : 'N/A'}</td>`;
                        } else {
                            html += '<td style="text-align: center;">N/A</td>';
                        }
                        purposeYears.forEach(year => {
                            html += '<td>0.00%</td>';
                        });
                        html += '</tr>';
                    });
                }
            }
            
            // Note: Loan size categories (Under $100K, $100K-$250K, $250K-$1M) are NOT shown in Income & Neighborhood table
            // They are only displayed in the Top Lenders table
    
    html += '</tbody></table>';
            html += '</div>'; // Close table-container
            
            // Note: Caption text moved to methods card at bottom of report
            
            html += '</div>'; // Close purpose-tab-content div
        }); // End dataTypes.forEach
        console.log(`[Income & Neighborhood] Finished rendering tab ${purposeIdx} (${purpose}), HTML length so far: ${html.length}`);
    }); // End purposes.forEach
    
    html += '</div>'; // Close analysis-table-card
    
    // Debug: Count how many tab content divs are in the HTML string
    const tabContentMatches = html.match(/class="purpose-tab-content income-neighborhood-tab-content/g);
    const tabContentCount = tabContentMatches ? tabContentMatches.length : 0;
    console.log(`[Income & Neighborhood] Finished rendering all tabs, total HTML length: ${html.length}, tab content divs in HTML string: ${tabContentCount}`);
    
    return html;
}

// Tab switching function for income/neighborhood
function switchIncomeNeighborhoodTab(purpose) {
    console.log(`[Income & Neighborhood] Switching to tab: ${purpose}`);
    // Update tab buttons for income/neighborhood section
    const incomeNeighborhoodCard = Array.from(document.querySelectorAll('.analysis-table-card')).find(card => 
        card.querySelector('h4') && card.querySelector('h4').textContent.includes('Income & Neighborhood')
    );
    
    if (!incomeNeighborhoodCard) {
        console.warn('[Income & Neighborhood] Card not found');
        return;
    }
    
    // Debug: Check what tab content divs exist
    const allDivs = incomeNeighborhoodCard.querySelectorAll('[data-purpose]');
    console.log(`[Income & Neighborhood] All elements with data-purpose:`, Array.from(allDivs).map(d => ({element: d.className, purpose: d.getAttribute('data-purpose')})));
    
    incomeNeighborhoodCard.querySelectorAll('.purpose-tab-btn[data-purpose]').forEach(btn => {
        if (btn.getAttribute('data-purpose') === purpose) {
            btn.classList.add('active');
            btn.style.background = '#2fade3';
            btn.style.color = 'white';
        } else {
            btn.classList.remove('active');
            btn.style.background = '#e0e0e0';
            btn.style.color = '#333';
        }
    });
}

// Tab switching function for counts/amounts (SB only)
function switchIncomeNeighborhoodDataType(dataTypeTab) {
    console.log(`[Income & Neighborhood] Switching to data type tab: ${dataTypeTab}`);
    const incomeNeighborhoodCard = Array.from(document.querySelectorAll('.analysis-table-card')).find(card => 
        card.querySelector('h4') && card.querySelector('h4').textContent.includes('Income & Neighborhood')
    );
    
    if (!incomeNeighborhoodCard) {
        console.warn('[Income & Neighborhood] Card not found');
        return;
    }
    
    // Update tab buttons
    incomeNeighborhoodCard.querySelectorAll('.purpose-tab-btn[data-data-type]').forEach(btn => {
        if (btn.getAttribute('data-data-type') === dataTypeTab) {
            btn.classList.add('active');
            btn.style.background = '#2fade3';
            btn.style.color = 'white';
        } else {
            btn.classList.remove('active');
            btn.style.background = '#e0e0e0';
            btn.style.color = '#333';
        }
    });
    
    // Update tab content - show/hide based on data type
    incomeNeighborhoodCard.querySelectorAll('.income-neighborhood-tab-content[data-data-type]').forEach(content => {
        if (content.getAttribute('data-data-type') === dataTypeTab) {
            content.style.display = 'block';
            content.style.visibility = 'visible';
            content.classList.add('active');
        } else {
            content.style.display = 'none';
            content.classList.remove('active');
        }
    });
}

function renderTopLendersTable(data, dataType = 'hmda', dataByPurpose = null, acsData = null) {
    // Use dataByPurpose if available, otherwise fall back to data
    const useTabs = dataByPurpose && Object.keys(dataByPurpose).length > 0;
    const currentData = useTabs ? (dataByPurpose.all || data) : data;
    
    if (!currentData || currentData.length === 0) {
        return '';
    }
    
    // Limit display to top 10 lenders only (no expand functionality)
    // All lenders will be included in Excel export
    
    // Render two separate tables: Demographics first (skip for SB), then Income & Neighborhood Indicators
    let html = '';
    
    // ===== TABLE 1: Demographics (skip for SB and branches - data not available) =====
    if (dataType !== 'sb' && dataType !== 'branches') {
        html += '<div class="analysis-table-card">';
    html += '<div class="table-header">';
        html += '<h4><i class="fas fa-users"></i> Top Lenders - Demographics <small style="font-weight: normal; color: white; font-style: italic; font-size: 0.85em;">(2024 data, Top 10 shown)</small></h4>';
    html += '<div class="export-buttons">';
        html += '<button class="btn-export-table" data-table="top_lenders_demographics" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
        html += '<button class="btn-share-table" data-table="top_lenders_demographics" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
        
        // Tab interface
        if (useTabs) {
            html += '<div class="purpose-tabs" style="display: flex; border-bottom: 2px solid #2fade3; margin-bottom: 0;">';
            html += '<button class="purpose-tab-btn active" data-purpose="all" data-action="switch-top-lenders-tab" data-table-type="demographics" aria-label="Show all loans for Top Lenders Demographics" role="tab" aria-selected="true" tabindex="0" style="flex: 1; padding: 12px 20px; background: #2fade3; color: white; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">All Loans</button>';
            html += '<button class="purpose-tab-btn" data-purpose="Home Purchase" data-action="switch-top-lenders-tab" data-table-type="demographics" aria-label="Show home purchase loans for Top Lenders Demographics" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Home Purchase</button>';
            html += '<button class="purpose-tab-btn" data-purpose="Refinance" data-action="switch-top-lenders-tab" data-table-type="demographics" aria-label="Show refinance loans for Top Lenders Demographics" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Refinance</button>';
            html += '<button class="purpose-tab-btn" data-purpose="Home Equity" data-action="switch-top-lenders-tab" data-table-type="demographics" aria-label="Show home equity loans for Top Lenders Demographics" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Home Equity</button>';
            html += '</div>';
        }
        
        // Render table for each purpose - TABLE 1: Demographics
        const purposes = useTabs ? ['all', 'Home Purchase', 'Refinance', 'Home Equity'] : ['all'];
        purposes.forEach((purpose, idx) => {
            const purposeData = useTabs ? (dataByPurpose[purpose] || []) : currentData;
            if (!purposeData || purposeData.length === 0) return;
            
            const displayData = purposeData.slice(0, 10);
            
            html += `<div class="purpose-tab-content top-lenders-tab-content top-lenders-demographics ${idx === 0 ? 'active' : ''}" data-purpose="${purpose}" data-table-type="demographics" style="display: ${idx === 0 ? 'block' : 'none'};">`;
    html += '<div class="table-container">';
            html += '<table class="editable-table top-lenders-table" data-table-id="top_lenders_demographics" data-purpose="' + purpose + '" style="table-layout: fixed; width: 100%;">';
    html += '<thead><tr>';
            html += '<th class="sortable" data-sort="name" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="demographics" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by lender name" style="width: 25%; font-size: 0.7em;">Lender Name<span class="sort-arrow"></span></th>';
            html += '<th class="sortable" data-sort="type" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="demographics" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by lender type" style="width: 15%; font-size: 0.7em;">Type<span class="sort-arrow"></span></th>';
            html += '<th class="sortable" data-sort="total_loans" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="demographics" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by total ' + (dataType === 'branches' ? 'branches' : 'loans') + '" style="width: 15%; font-size: 0.7em;">Total ' + (dataType === 'branches' ? 'Branches' : 'Loans') + '<span class="sort-arrow"></span></th>';
            
            // Add demographic columns for HMDA
    if (dataType === 'hmda') {
                const demographicGroups = ['Hispanic', 'Black', 'White', 'Asian'];
                const demographicKeys = ['hispanic', 'black', 'white', 'asian'];
                // Only add Native American if >= 1% of geography
                if (acsData && acsData.demographics && acsData.demographics['Native American or Alaska Native'] >= 1.0) {
                    demographicGroups.push('Native American');
                    demographicKeys.push('native_american');
                }
                // Only add Native Hawaiian if >= 1% of geography
                if (acsData && acsData.demographics && acsData.demographics['Native Hawaiian or Other Pacific Islander'] >= 1.0) {
                    demographicGroups.push('Native Hawaiian or Other Pacific Islander');
                    demographicKeys.push('hawaiian_pacific_islander');
                }
                // Calculate width for demographic columns (remaining space divided equally)
                const numDemoCols = demographicGroups.length;
                const demoColWidth = numDemoCols > 0 ? `${Math.floor(45 / numDemoCols)}%` : '11%';
                demographicGroups.forEach((group, idx) => {
                    const key = demographicKeys[idx];
                    html += `<th class="sortable" data-sort="demo_${key}" data-action="sort-lenders" data-purpose="${purpose}" data-table-type="demographics" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by ${group} percentage" style="width: ${demoColWidth};">${group}<span class="sort-arrow"></span></th>`;
        });
    }
    
    html += '</tr></thead>';
    html += '<tbody>';
    
            // Render only top 10 lenders
            displayData.forEach((row, rowIndex) => {
        html += '<tr>';
                html += `<td>${(row.name || '').toUpperCase()}</td>`;
        html += `<td>${row.type || 'Unknown'}</td>`;
        html += `<td class="editable" data-field="total_loans" data-lei="${row.lei}" data-value="${row.total_loans}">${formatNumber(row.total_loans)}</td>`;
        
                // Render demographic columns - percentages only, no counts
        if (dataType === 'hmda') {
                    const demographicGroups = ['hispanic', 'black', 'white', 'asian'];
                    // Only show Native American if >= 1% of geography
                    if (acsData && acsData.demographics && acsData.demographics['Native American or Alaska Native'] >= 1.0) {
                        demographicGroups.push('native_american');
                    }
                    // Only show Native Hawaiian if >= 1% of geography
                    if (acsData && acsData.demographics && acsData.demographics['Native Hawaiian or Other Pacific Islander'] >= 1.0) {
                        demographicGroups.push('hawaiian_pacific_islander');
                    }
                    demographicGroups.forEach(group => {
                        const demo = row.demographics && row.demographics[group] ? row.demographics[group] : {count: 0, percent: 0};
                        html += `<td class="editable" data-field="${group}" data-lei="${row.lei}" data-value='${JSON.stringify(demo)}' style="text-align: center;">${demo.percent.toFixed(2)}%</td>`;
                    });
                }
                
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            html += '</div>';
            html += '</div>';
        });
        
        html += '</div>'; // Close first card (Demographics)
    }
    
    // ===== TABLE 2: Income & Neighborhood Indicators =====
    html += '<div class="analysis-table-card" style="margin-top: 30px;">';
    html += '<div class="table-header">';
    const dataYear = dataType === 'branches' ? '2025' : '2024';
    const tableTitle = dataType === 'branches' ? 'Top Bank Branch Networks' : 'Top Lenders';
    html += `<h4><i class="fas fa-building"></i> ${tableTitle} - Income & Neighborhood Indicators <small style="font-weight: normal; color: white; font-style: italic; font-size: 0.85em;">(${dataYear} data, Top 10 shown)</small></h4>`;
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-table" data-table="top_lenders_indicators" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-table" data-table="top_lenders_indicators" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    
    // Tab interface for loan purposes (HMDA only)
    if (useTabs && dataType !== 'sb') {
        html += '<div class="purpose-tabs" style="display: flex; border-bottom: 2px solid #2fade3; margin-bottom: 0;">';
        html += '<button class="purpose-tab-btn active" data-purpose="all" data-action="switch-top-lenders-tab" data-table-type="indicators" aria-label="Show all loans for Top Lenders" role="tab" aria-selected="true" tabindex="0" style="flex: 1; padding: 12px 20px; background: #2fade3; color: white; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">All Loans</button>';
        html += '<button class="purpose-tab-btn" data-purpose="Home Purchase" data-action="switch-top-lenders-tab" data-table-type="indicators" aria-label="Show home purchase loans for Top Lenders" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Home Purchase</button>';
        html += '<button class="purpose-tab-btn" data-purpose="Refinance" data-action="switch-top-lenders-tab" data-table-type="indicators" aria-label="Show refinance loans for Top Lenders" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Refinance</button>';
        html += '<button class="purpose-tab-btn" data-purpose="Home Equity" data-action="switch-top-lenders-tab" data-table-type="indicators" aria-label="Show home equity loans for Top Lenders" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Home Equity</button>';
        html += '</div>';
    }
    
    // Tab interface for counts/amounts (SB only)
    // For SB, there's only one "purpose" (all), so use 'all' for the purpose attribute
    if (dataType === 'sb') {
        html += '<div class="purpose-tabs" style="display: flex; border-bottom: 2px solid #2fade3; margin-bottom: 0;">';
        html += `<button class="purpose-tab-btn active" data-data-type="count" data-action="switch-top-lenders-data-type" data-purpose="all" data-table-type="indicators" aria-label="Show number of loans" role="tab" aria-selected="true" tabindex="0" style="flex: 1; padding: 12px 20px; background: #2fade3; color: white; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Number of Loans</button>`;
        html += `<button class="purpose-tab-btn" data-data-type="amount" data-action="switch-top-lenders-data-type" data-purpose="all" data-table-type="indicators" aria-label="Show amount of loans" role="tab" aria-selected="false" tabindex="-1" style="flex: 1; padding: 12px 20px; background: #e0e0e0; color: #333; border: none; cursor: pointer; font-size: 1rem; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;">Amount of Loans</button>`;
        html += '</div>';
    }
    
    // Render table for each purpose - TABLE 2: Income & Neighborhood Indicators
    // Define purposes here so it's available for both HMDA and SB data types
    const purposes = (useTabs && dataType !== 'sb') ? ['all', 'Home Purchase', 'Refinance', 'Home Equity'] : ['all'];
    const dataTypes = dataType === 'sb' ? ['count', 'amount'] : ['count']; // SB has both, HMDA only has counts
    
    purposes.forEach((purpose, purposeIdx) => {
        dataTypes.forEach((dataTypeTab, dataTypeIdx) => {
            const isCountTab = dataTypeTab === 'count';
            const isActive = purposeIdx === 0 && (dataType === 'sb' ? dataTypeIdx === 0 : true);
            
            const purposeData = useTabs && dataType !== 'sb' ? (dataByPurpose[purpose] || []) : currentData;
            if (!purposeData || purposeData.length === 0) return;
            
            // Limit display to top 10 only (no expand functionality)
            const displayData = purposeData.slice(0, 10);
            const purposeTotalCount = purposeData.length; // Store actual data count for reference
            
            html += `<div class="purpose-tab-content top-lenders-tab-content top-lenders-indicators ${isActive ? 'active' : ''}" data-purpose="${purpose}" data-data-type="${dataTypeTab}" data-total-lenders="${purposeTotalCount}" data-table-type="indicators" style="display: ${isActive ? 'block' : 'none'};">`;
            html += '<div class="table-container">';
            html += '<table class="editable-table top-lenders-table" data-table-id="top_lenders_indicators" data-purpose="' + purpose + '" data-data-type="' + dataTypeTab + '" style="table-layout: fixed; width: 100%;">';
            html += '<thead><tr>';
            // For branches, show Bank Name first
            if (dataType === 'branches') {
                html += '<th class="sortable" data-sort="name" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by bank name" style="width: 20%; font-size: 0.7em;">Bank Name<span class="sort-arrow"></span></th>';
            } else {
                html += '<th class="sortable" data-sort="name" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by lender name" style="width: ' + (dataType === 'sb' ? '25%' : '25%') + '; font-size: 0.7em;">Lender Name<span class="sort-arrow"></span></th>';
            }
            // Skip Type column for SB and branches
            if (dataType !== 'sb' && dataType !== 'branches') {
                html += '<th class="sortable" data-sort="type" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by lender type" style="width: 15%; font-size: 0.7em;">Type<span class="sort-arrow"></span></th>';
            }
            // For branches: show 2025 Branches, 2025 Deposits, Branches Changed, Deposits Changed
            if (dataType === 'branches') {
                html += '<th class="sortable" data-sort="total_loans" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by total branches" style="width: 12%; font-size: 0.7em;">2025 Branches<span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="total_amount" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by total deposits" style="width: 12%; font-size: 0.7em;">2025 Deposits<span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="branches_change_2021" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by branches changed since 2021" style="width: 12%; font-size: 0.7em;">Branches Changed<br><small>(Since 2021)</small><span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="deposits_change_2021" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by deposits changed since 2021" style="width: 12%; font-size: 0.7em;">Deposits Changed<br><small>(Since 2021)</small><span class="sort-arrow"></span></th>';
            } else {
                // Add thousands indicator for Total Amount column with line break
                const totalColumnLabel = isCountTab ? 'Loans' : 'Amount';
                let totalColumnLabelWithIndicator;
                if (dataType === 'sb' && !isCountTab) {
                    totalColumnLabelWithIndicator = 'Amount<br><small>(000s)</small>';
                } else {
                    totalColumnLabelWithIndicator = totalColumnLabel;
                }
                html += '<th class="sortable" data-sort="total_loans" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by total ' + (isCountTab ? 'loans' : 'amount') + '" style="width: ' + (dataType === 'sb' ? '10%' : '12%') + '; font-size: 0.7em; white-space: normal; line-height: 1.2;">Total ' + totalColumnLabelWithIndicator + '<span class="sort-arrow"></span></th>';
            }
            
            // Add Income & Neighborhood Indicator columns (only for HMDA data)
            if (dataType === 'hmda') {
                html += '<th class="sortable" data-sort="lmib" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by LMI Borrowers percentage" style="width: 15%; text-align: center; font-size: 0.7em;">LMI Borrowers<br><small>(%)</small><span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="lmict" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by LMI Census Tracts percentage" style="width: 15%; text-align: center; font-size: 0.7em;">LMI Census Tracts<br><small>(%)</small><span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="mmct" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by MMCT percentage" style="width: 15%; text-align: center; font-size: 0.7em;">MMCT<br><small>(%)</small><span class="sort-arrow"></span></th>';
            } else if (dataType === 'sb') {
                // SB-specific columns: LMICT, loan size categories, business revenue - smaller font to fit all headers
                html += '<th class="sortable" data-sort="lmict" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by LMICT percentage" style="width: 12%; text-align: center; font-size: 0.7em; white-space: normal; word-wrap: break-word; line-height: 1.2; padding: 8px 4px;">LMICT<br><small>(%)</small><span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="under_100k" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by Loans Under $100K percentage" style="width: 13%; text-align: center; font-size: 0.7em; white-space: normal; word-wrap: break-word; line-height: 1.2; padding: 8px 4px;">Loans<br>Under $100K<br><small>(%)</small><span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="100k_250k" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by Loans $100K-$250K percentage" style="width: 13%; text-align: center; font-size: 0.7em; white-space: normal; word-wrap: break-word; line-height: 1.2; padding: 8px 4px;">Loans<br>$100K-$250K<br><small>(%)</small><span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="250k_1m" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by Loans $250K-$1M percentage" style="width: 13%; text-align: center; font-size: 0.7em; white-space: normal; word-wrap: break-word; line-height: 1.2; padding: 8px 4px;">Loans<br>$250K-$1M<br><small>(%)</small><span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="rev_under_1m" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by Loans to Businesses Under $1M Revenue percentage" style="width: 15%; text-align: center; font-size: 0.7em; white-space: normal; word-wrap: break-word; line-height: 1.2; padding: 8px 4px;">Loans to Biz<br>Under $1M Rev<br><small>(%)</small><span class="sort-arrow"></span></th>';
            } else if (dataType === 'branches') {
                html += '<th class="sortable" data-sort="demo_lmi" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by LMI Tract percentage" style="width: 10%; text-align: center; font-size: 0.7em;">LMI Share<br><small>(%)</small><span class="sort-arrow"></span></th>';
                html += '<th class="sortable" data-sort="demo_mmct" data-action="sort-lenders" data-purpose="' + purpose + '" data-table-type="indicators" aria-sort="none" role="columnheader" tabindex="0" aria-label="Sort by MMCT Tract percentage" style="width: 10%; text-align: center; font-size: 0.7em;">MMCT Share<br><small>(%)</small><span class="sort-arrow"></span></th>';
            }
            
            html += '</tr></thead>';
            html += '<tbody>';
            
            // Render only top 10 lenders (no expand functionality)
            displayData.forEach((row, rowIndex) => {
                html += '<tr>';
                // For branches, show Bank Name first
                if (dataType === 'branches') {
                    html += `<td>${(row.name || '').toUpperCase()}</td>`;
                } else {
                    html += `<td>${(row.name || '').toUpperCase()}</td>`;
                }
                // Skip Type column for SB and branches
                if (dataType !== 'sb' && dataType !== 'branches') {
                    html += `<td>${row.type || 'Unknown'}</td>`;
                }
                
                // For branches: show 2025 Branches, 2025 Deposits, Branches Changed, Deposits Changed
                if (dataType === 'branches') {
                    html += `<td class="editable" data-field="total_loans" data-lei="${row.lei}" data-value="${row.total_loans}">${formatNumber(row.total_loans)}</td>`;
                    html += `<td class="editable" data-field="total_amount" data-lei="${row.lei}" data-value="${row.total_amount || 0}">${formatCurrency(row.total_amount || 0)}</td>`;
                    const branchesChange = row.branches_change_2021 || 0;
                    const branchesChangeSign = branchesChange >= 0 ? '+' : '';
                    const branchesChangeColor = branchesChange >= 0 ? '#2fade3' : '#e82e2e';
                    html += `<td style="color: ${branchesChangeColor}; font-weight: bold;">${branchesChangeSign}${formatNumber(branchesChange)}</td>`;
                    const depositsChange = row.deposits_change_2021 || 0;
                    const depositsChangeSign = depositsChange >= 0 ? '+' : '';
                    const depositsChangeColor = depositsChange >= 0 ? '#2fade3' : '#e82e2e';
                    html += `<td style="color: ${depositsChangeColor}; font-weight: bold;">${depositsChangeSign}${formatCurrency(depositsChange)}</td>`;
                } else {
                    // Show count or amount based on tab
                    if (dataType === 'sb' && !isCountTab) {
                        html += `<td class="editable" data-field="total_amount" data-lei="${row.lei}" data-value="${row.total_amount || 0}">${formatCurrency(row.total_amount || 0)}</td>`;
                    } else {
                        html += `<td class="editable" data-field="total_loans" data-lei="${row.lei}" data-value="${row.total_loans}">${formatNumber(row.total_loans)}</td>`;
                    }
                }
                
                // Render Income & Neighborhood Indicator columns
                if (dataType === 'hmda' && row.performance_indicators) {
                    const lmib = row.performance_indicators.lmib || {count: 0, percent: 0};
                    html += `<td class="editable" data-field="lmib" data-lei="${row.lei}" data-value='${JSON.stringify(lmib)}' style="text-align: center;">${lmib.percent.toFixed(2)}%</td>`;
                    
                    const lmict = row.performance_indicators.lmict || {count: 0, percent: 0};
                    html += `<td class="editable" data-field="lmict" data-lei="${row.lei}" data-value='${JSON.stringify(lmict)}' style="text-align: center;">${lmict.percent.toFixed(2)}%</td>`;
                    
                    const mmct = row.performance_indicators.mmct || {count: 0, percent: 0};
                    html += `<td class="editable" data-field="mmct" data-lei="${row.lei}" data-value='${JSON.stringify(mmct)}' style="text-align: center;">${mmct.percent.toFixed(2)}%</td>`;
                } else if (dataType === 'sb' && row.performance_indicators) {
                    // SB-specific performance indicators - use different percentages for counts vs amounts
                    if (isCountTab) {
                        // Count-based percentages
                        const lmict = row.performance_indicators.lmict_percent || 0;
                        html += `<td class="editable" data-field="lmict" data-lei="${row.lei}" data-value="${lmict}" style="text-align: center;">${lmict.toFixed(2)}%</td>`;
                        
                        const under_100k = row.performance_indicators.under_100k_percent || 0;
                        html += `<td class="editable" data-field="under_100k" data-lei="${row.lei}" data-value="${under_100k}" style="text-align: center;">${under_100k.toFixed(2)}%</td>`;
                        
                        const loans_100k_250k = row.performance_indicators['100k_250k_percent'] || 0;
                        html += `<td class="editable" data-field="100k_250k" data-lei="${row.lei}" data-value="${loans_100k_250k}" style="text-align: center;">${loans_100k_250k.toFixed(2)}%</td>`;
                        
                        const loans_250k_1m = row.performance_indicators['250k_1m_percent'] || 0;
                        html += `<td class="editable" data-field="250k_1m" data-lei="${row.lei}" data-value="${loans_250k_1m}" style="text-align: center;">${loans_250k_1m.toFixed(2)}%</td>`;
                        
                        const rev_under_1m = row.performance_indicators.rev_under_1m_percent || 0;
                        html += `<td class="editable" data-field="rev_under_1m" data-lei="${row.lei}" data-value="${rev_under_1m}" style="text-align: center;">${rev_under_1m.toFixed(2)}%</td>`;
                    } else {
                        // Amount-based percentages
                        const lmict = row.performance_indicators.lmict_amount_percent || 0;
                        html += `<td class="editable" data-field="lmict" data-lei="${row.lei}" data-value="${lmict}" style="text-align: center;">${lmict.toFixed(2)}%</td>`;
                        
                        const under_100k = row.performance_indicators.under_100k_amount_percent || 0;
                        html += `<td class="editable" data-field="under_100k" data-lei="${row.lei}" data-value="${under_100k}" style="text-align: center;">${under_100k.toFixed(2)}%</td>`;
                        
                        const loans_100k_250k = row.performance_indicators['100k_250k_amount_percent'] || 0;
                        html += `<td class="editable" data-field="100k_250k" data-lei="${row.lei}" data-value="${loans_100k_250k}" style="text-align: center;">${loans_100k_250k.toFixed(2)}%</td>`;
                        
                        const loans_250k_1m = row.performance_indicators['250k_1m_amount_percent'] || 0;
                        html += `<td class="editable" data-field="250k_1m" data-lei="${row.lei}" data-value="${loans_250k_1m}" style="text-align: center;">${loans_250k_1m.toFixed(2)}%</td>`;
                        
                        const rev_under_1m = row.performance_indicators.rev_under_1m_amount_percent || 0;
                        html += `<td class="editable" data-field="rev_under_1m" data-lei="${row.lei}" data-value="${rev_under_1m}" style="text-align: center;">${rev_under_1m.toFixed(2)}%</td>`;
                    }
        } else if (dataType === 'branches') {
            ['lmi', 'mmct'].forEach(group => {
                        const demo = row.demographics && row.demographics[group] ? row.demographics[group] : {count: 0, percent: 0};
                        html += `<td class="editable" data-field="${group}" data-lei="${row.lei}" data-value='${JSON.stringify(demo)}' style="text-align: center;">${demo.percent.toFixed(2)}%</td>`;
            });
        }
        
        html += '</tr>';
    });
    
    html += '</tbody></table>';
            html += '</div>';
            html += '</div>';
        }); // End dataTypes.forEach
    }); // End purposes.forEach
    
    html += '</div>'; // Close second card (Income & Neighborhood Indicators)
    return html;
}

// Tab switching function for top lenders
function switchTopLendersTab(purpose, tableType) {
    // Update tab buttons for both top lenders tables (indicators and demographics)
    // Find both table cards
    const indicatorsCard = Array.from(document.querySelectorAll('.analysis-table-card')).find(card => 
        card.querySelector('h4') && card.querySelector('h4').textContent.includes('Income & Neighborhood Indicators')
    );
    const demographicsCard = Array.from(document.querySelectorAll('.analysis-table-card')).find(card => 
        card.querySelector('h4') && card.querySelector('h4').textContent.includes('Demographics')
    );
    
    // Update tabs in the clicked card (or both if tableType not specified)
    const cardsToUpdate = tableType === 'indicators' ? [indicatorsCard] : 
                          tableType === 'demographics' ? [demographicsCard] : 
                          [indicatorsCard, demographicsCard].filter(c => c);
    
    cardsToUpdate.forEach(card => {
        if (!card) return;
        
        // Update tab buttons
        card.querySelectorAll('.purpose-tab-btn[data-purpose]').forEach(btn => {
            if (btn.getAttribute('data-purpose') === purpose) {
                btn.classList.add('active');
                btn.style.background = '#2fade3';
                btn.style.color = 'white';
            } else {
                btn.classList.remove('active');
                btn.style.background = '#e0e0e0';
                btn.style.color = '#333';
            }
        });
        
        // Update tab content
        card.querySelectorAll('.top-lenders-tab-content').forEach(content => {
            if (content.getAttribute('data-purpose') === purpose) {
                content.style.display = 'block';
            } else {
                content.style.display = 'none';
            }
        });
    });
    
    // If switching one table, also switch the other to keep them in sync
    if (tableType && indicatorsCard && demographicsCard) {
        const otherTableType = tableType === 'indicators' ? 'demographics' : 'indicators';
        const otherCard = tableType === 'indicators' ? demographicsCard : indicatorsCard;
        
        // Update tab buttons in the other card
        otherCard.querySelectorAll('.purpose-tab-btn[data-purpose]').forEach(btn => {
            if (btn.getAttribute('data-purpose') === purpose) {
                btn.classList.add('active');
                btn.style.background = '#2fade3';
                btn.style.color = 'white';
            } else {
                btn.classList.remove('active');
                btn.style.background = '#e0e0e0';
                btn.style.color = '#333';
            }
        });
        
        // Update tab content in the other card
        otherCard.querySelectorAll('.top-lenders-tab-content').forEach(content => {
            if (content.getAttribute('data-purpose') === purpose) {
                content.style.display = 'block';
            } else {
                content.style.display = 'none';
            }
        });
    }
}

// Tab switching function for counts/amounts (Top Lenders - SB only)
function switchTopLendersDataType(purpose, tableType, dataTypeTab) {
    console.log(`[Top Lenders] Switching to data type tab: ${dataTypeTab} for purpose: ${purpose}, tableType: ${tableType}`);
    
    // Find the correct card - look for "Income & Neighborhood Indicators" in Top Lenders section
    const topLendersCard = Array.from(document.querySelectorAll('.analysis-table-card')).find(card => {
        const h4 = card.querySelector('h4');
        return h4 && h4.textContent.includes('Top Lenders') && h4.textContent.includes('Income & Neighborhood Indicators');
    });
    
    if (!topLendersCard) {
        console.warn('[Top Lenders] Card not found for Income & Neighborhood Indicators');
        return;
    }
    
    // Update tab buttons - find buttons within the correct purpose and table type
    const tabButtons = topLendersCard.querySelectorAll(`.purpose-tab-btn[data-data-type][data-purpose="${purpose}"][data-table-type="${tableType}"]`);
    console.log(`[Top Lenders] Found ${tabButtons.length} tab buttons for purpose=${purpose}, tableType=${tableType}`);
    
    tabButtons.forEach(btn => {
        if (btn.getAttribute('data-data-type') === dataTypeTab) {
            btn.classList.add('active');
            btn.style.background = '#2fade3';
            btn.style.color = 'white';
            btn.setAttribute('aria-selected', 'true');
            btn.setAttribute('tabindex', '0');
        } else {
            btn.classList.remove('active');
            btn.style.background = '#e0e0e0';
            btn.style.color = '#333';
            btn.setAttribute('aria-selected', 'false');
            btn.setAttribute('tabindex', '-1');
        }
    });
    
    // Update tab content - show/hide based on data type, purpose, and table type
    const tabContents = topLendersCard.querySelectorAll(`.top-lenders-tab-content[data-data-type][data-purpose="${purpose}"][data-table-type="${tableType}"]`);
    console.log(`[Top Lenders] Found ${tabContents.length} tab content divs for purpose=${purpose}, tableType=${tableType}`);
    
    tabContents.forEach(content => {
        if (content.getAttribute('data-data-type') === dataTypeTab) {
            content.style.display = 'block';
            content.style.visibility = 'visible';
            content.classList.add('active');
            console.log(`[Top Lenders] Showing tab content with data-type=${dataTypeTab}`);
        } else {
            content.style.display = 'none';
            content.classList.remove('active');
            console.log(`[Top Lenders] Hiding tab content with data-type=${content.getAttribute('data-data-type')}`);
        }
    });
}

// Sorting function for top lenders table
function sortTopLendersTable(purpose, sortColumn, tableType) {
    // Find the correct card first
    const cardTitle = tableType === 'indicators' 
        ? 'Income & Neighborhood Indicators'
        : tableType === 'demographics'
        ? 'Demographics'
        : 'Top Lenders';
    const topLendersCard = Array.from(document.querySelectorAll('.analysis-table-card')).find(card => 
        card.querySelector('h4') && card.querySelector('h4').textContent.includes('Top Lenders') && 
        (tableType === 'indicators' ? card.querySelector('h4').textContent.includes('Income & Neighborhood Indicators') :
         tableType === 'demographics' ? card.querySelector('h4').textContent.includes('Demographics') : true)
    );
    
    if (!topLendersCard) {
        console.warn(`[Sort] Card not found for tableType=${tableType}`);
        return;
    }
    
    // Find the active tab content (for SB, need to check data-type attribute)
    let tabContent = null;
    if (tableType === 'indicators') {
        // Find active tab content with matching purpose
        const allTabContents = topLendersCard.querySelectorAll(`.top-lenders-indicators[data-purpose="${purpose}"]`);
        // For SB, find the one that's currently visible (active)
        tabContent = Array.from(allTabContents).find(tc => {
            const style = window.getComputedStyle(tc);
            return style.display !== 'none' && tc.classList.contains('active');
        }) || allTabContents[0]; // Fallback to first if none active
    } else if (tableType === 'demographics') {
        tabContent = topLendersCard.querySelector(`.top-lenders-demographics[data-purpose="${purpose}"]`);
    } else {
        tabContent = topLendersCard.querySelector(`.top-lenders-tab-content[data-purpose="${purpose}"]`);
    }
    
    if (!tabContent) {
        console.warn(`[Sort] Tab content not found for purpose=${purpose}, tableType=${tableType}`);
        return;
    }
    
    const $table = $(tabContent).find('table');
    if (!$table.length) {
        console.warn(`[Sort] Table not found in tab content`);
        return;
    }
    
    // Reset all sortable headers
    $table.find('[data-action="sort-lenders"]').attr('aria-sort', 'none').find('.sort-arrow').removeClass('asc desc');
    
    // Find the clicked header
    const $clickedHeader = $table.find(`[data-sort="${sortColumn}"][data-action="sort-lenders"]`);
    if (!$clickedHeader.length) {
        console.warn(`[Sort] Header not found for sortColumn=${sortColumn}`);
        return;
    }
    
    const table = $table[0];
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    const rows = Array.from(tbody.querySelectorAll('tr'));
    if (rows.length === 0) return;
    
    // Get current sort state
    const header = table.querySelector(`th[data-sort="${sortColumn}"]`);
    if (!header) return;
    
    const isAsc = header.classList.contains('sort-asc');
    const newSortDirection = isAsc ? 'desc' : 'asc';
    
    // Reset all sort classes
    table.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Set new sort class and aria-sort
    header.classList.add('sort-' + newSortDirection);
    $clickedHeader.attr('aria-sort', newSortDirection);
    
    // Update sort arrow
    $clickedHeader.find('.sort-arrow').addClass(newSortDirection);
    
    // Find column index for the sort column
    const headers = Array.from(table.querySelectorAll('th'));
    const columnIndex = headers.findIndex(th => th.getAttribute('data-sort') === sortColumn);
    
    if (columnIndex === -1) return;
    
    // Sort rows
    rows.sort((a, b) => {
        let aValue, bValue;
        const aCell = a.cells[columnIndex];
        const bCell = b.cells[columnIndex];
        
        if (!aCell || !bCell) return 0;
        
        if (sortColumn === 'name' || sortColumn === 'type') {
            aValue = aCell.textContent.trim().toLowerCase();
            bValue = bCell.textContent.trim().toLowerCase();
        } else if (sortColumn === 'total_loans') {
            aValue = parseFloat(aCell.getAttribute('data-value') || aCell.textContent.replace(/,/g, '')) || 0;
            bValue = parseFloat(bCell.getAttribute('data-value') || bCell.textContent.replace(/,/g, '')) || 0;
        } else if (sortColumn === 'total_amount') {
            aValue = parseFloat(aCell.getAttribute('data-value') || aCell.textContent.replace(/[$,]/g, '')) || 0;
            bValue = parseFloat(bCell.getAttribute('data-value') || bCell.textContent.replace(/[$,]/g, '')) || 0;
        } else if (sortColumn.startsWith('demo_')) {
            // Demographic columns - extract percentage from text
            const aText = aCell.textContent.trim();
            const bText = bCell.textContent.trim();
            aValue = parseFloat(aText.replace('%', '')) || 0;
            bValue = parseFloat(bText.replace('%', '')) || 0;
        } else if (sortColumn === 'lmict' || sortColumn === 'lmib' || sortColumn === 'mmct' || 
                   sortColumn === 'under_100k' || sortColumn === '100k_250k' || sortColumn === '250k_1m' || 
                   sortColumn === 'rev_under_1m') {
            // Performance indicator columns - extract percentage from text or data-value
            const aText = aCell.textContent.trim();
            const bText = bCell.textContent.trim();
            aValue = parseFloat(aText.replace(/[%,$]/g, '')) || parseFloat(aCell.getAttribute('data-value') || 0) || 0;
            bValue = parseFloat(bText.replace(/[%,$]/g, '')) || parseFloat(bCell.getAttribute('data-value') || 0) || 0;
        } else {
            return 0;
        }
        
        // Compare values
        if (typeof aValue === 'string') {
            if (newSortDirection === 'asc') {
                return aValue.localeCompare(bValue);
            } else {
                return bValue.localeCompare(aValue);
            }
        } else {
            if (newSortDirection === 'asc') {
                return aValue - bValue;
            } else {
                return bValue - aValue;
            }
        }
    });
    
    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

// Expand/collapse function for lenders (from header button)
function toggleExpandLendersFromHeader(purpose) {
    // Expand button functionality disabled - always show only top 10 lenders in UI
    // All lenders are included in Excel export
    // This function is kept for compatibility but does nothing
    return;
}

// Expand/collapse function for lenders (legacy - kept for compatibility)
function toggleExpandLenders(purpose) {
    toggleExpandLendersFromHeader(purpose);
}

function renderHHIByYearTable(data) {
    if (!data || data.length === 0) {
        return '';
    }
    
    const concentrationColors = {
        'Unconcentrated': '#2fade3',
        'Moderately Concentrated': '#ffc23a',
        'Highly Concentrated': '#e82e2e',
        'Not Available': '#818390'
    };
    
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-pie"></i> Market Concentration (HHI) by Year</h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-table" data-table="hhi_by_year" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-table" data-table="hhi_by_year" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    html += '<div class="table-container">';
    html += '<table class="editable-table" data-table-id="hhi_by_year">';
    html += '<thead><tr>';
    html += '<th>Year</th>';
    html += '<th>HHI Value</th>';
    html += '<th>Concentration Level</th>';
    html += '<th>Total Amount</th>';
    html += '<th>Top 5 Lenders Market Share</th>';
    html += '<th>Year-over-Year Change</th>';
    html += '</tr></thead>';
    html += '<tbody>';
    
    data.forEach((row, index) => {
        const color = concentrationColors[row.concentration_level] || '#818390';
        const prevRow = index > 0 ? data[index - 1] : null;
        const hhiChange = prevRow && row.hhi !== null && prevRow.hhi !== null 
            ? row.hhi - prevRow.hhi 
            : null;
        const hhiChangePct = prevRow && row.hhi !== null && prevRow.hhi !== null && prevRow.hhi > 0
            ? ((row.hhi - prevRow.hhi) / prevRow.hhi * 100)
            : null;
        
        // Calculate combined market share of top 5 lenders
        const top5MarketShare = row.top_lenders && row.top_lenders.length > 0
            ? row.top_lenders.reduce((sum, lender) => sum + lender.market_share, 0)
            : 0;
        
        html += '<tr>';
        html += `<td>${row.year}</td>`;
        html += `<td class="editable" data-field="hhi" data-value="${row.hhi || ''}" style="color: ${color}; font-weight: bold;">`;
        html += row.hhi !== null ? row.hhi.toLocaleString() : 'N/A';
        html += '</td>';
        html += `<td style="color: ${color};">${row.concentration_level}</td>`;
        html += `<td class="editable" data-field="total_amount" data-value="${row.total_amount}">${formatCurrency(row.total_amount)}</td>`;
        html += `<td>${top5MarketShare.toFixed(2)}%</td>`;
        html += '<td>';
        if (hhiChange !== null) {
            const changeClass = hhiChange >= 0 ? 'change-positive' : 'change-negative';
            html += `<span class="${changeClass}">`;
            html += `${hhiChange >= 0 ? '+' : ''}${hhiChange.toFixed(2)}`;
            if (hhiChangePct !== null) {
                html += ` (${hhiChangePct >= 0 ? '+' : ''}${hhiChangePct.toFixed(2)}%)`;
            }
            html += '</span>';
        } else {
            html += '-';
        }
        html += '</td>';
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    html += '</div>';
    
    // Add note about HHI interpretation
    html += '<div class="table-note" style="margin-top: 12px; padding: 12px; background: #f0f7ff; border-radius: 6px; border-left: 3px solid var(--ncrc-primary-blue);">';
    html += '<p style="margin: 0; font-size: 0.9em; color: #333;">';
    html += '<i class="fas fa-info-circle"></i> <strong>HHI Interpretation:</strong> ';
    html += 'HHI values range from 0 to 10,000. Markets with HHI below 1,500 are considered unconcentrated, ';
    html += 'between 1,500 and 2,500 are moderately concentrated, and above 2,500 are highly concentrated. ';
    html += 'Higher HHI values indicate greater market concentration.';
    html += '</p>';
    html += '</div>';
    
    html += '</div>';
    return html;
}

function renderTrendsTable(data) {
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-line"></i> Year-over-Year Trends</h4>';
    html += '</div>';
    html += '<div class="table-container">';
    html += '<table class="editable-table" data-table-id="trends">';
    html += '<thead><tr>';
    html += '<th>Period</th>';
    html += '<th>Loans Change</th>';
    html += '<th>Amount Change</th>';
    html += '</tr></thead>';
    html += '<tbody>';
    
    data.forEach(row => {
        const loansClass = row.loans.percent >= 0 ? 'positive' : 'negative';
        const amountClass = row.amount.percent >= 0 ? 'positive' : 'negative';
        
        html += '<tr>';
        html += `<td>${row.period}</td>`;
        html += `<td class="change-cell ${loansClass}">`;
        html += `${row.loans.percent >= 0 ? '+' : ''}${row.loans.percent.toFixed(2)}%`;
        html += ` <small>(${row.loans.change >= 0 ? '+' : ''}${formatNumber(row.loans.change)})</small>`;
        html += '</td>';
        html += `<td class="change-cell ${amountClass}">`;
        html += `${row.amount.percent >= 0 ? '+' : ''}${row.amount.percent.toFixed(2)}%`;
        html += ` <small>(${row.amount.change >= 0 ? '+' : ''}${formatCurrency(row.amount.change)})</small>`;
        html += '</td>';
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    html += '</div></div>';
    return html;
}

function renderTopLendersTableByPurpose(dataByPurpose, dataType = 'hmda') {
    // Calculate total area lending to filter <1% columns
    const allLenders = dataByPurpose.all || [];
    const totalAreaLending = allLenders.reduce((sum, lender) => sum + (lender.total_amount || 0), 0);
    
    // Calculate total lenders for expand button
    const totalLenders = Math.max(...Object.values(dataByPurpose).map(arr => arr ? arr.length : 0));
    const hasMoreThan10 = totalLenders > 10;
    
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-building"></i> Top Lenders <small style="font-weight: normal; color: white; font-style: italic; font-size: 0.85em;">(2024 data)</small></h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-table" data-table="top_lenders" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-table" data-table="top_lenders" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    
    // Tab interface
    html += '<div class="purpose-tabs">';
    html += '<button class="purpose-tab-btn active" data-purpose="all">All Loans</button>';
    html += '<button class="purpose-tab-btn" data-purpose="Home Purchase">Home Purchase</button>';
    html += '<button class="purpose-tab-btn" data-purpose="Refinance">Refinance</button>';
    html += '<button class="purpose-tab-btn" data-purpose="Home Equity">Home Equity</button>';
    html += '</div>';
    
    // Render table for each purpose
    const purposes = ['all', 'Home Purchase', 'Refinance', 'Home Equity'];
    purposes.forEach((purpose, idx) => {
        const data = dataByPurpose[purpose] || [];
        html += `<div class="purpose-tab-content ${idx === 0 ? 'active' : ''}" data-purpose="${purpose}">`;
        html += '<div class="table-container">';
        html += '<table class="editable-table" data-table-id="top_lenders" data-purpose="' + purpose + '">';
        html += '<thead><tr>';
        html += '<th>Lender Name</th>';
        html += '<th>Type</th>';
        html += '<th>Total Loans</th>';
        html += '<th>Total Amount</th>';
        
        // Add demographic columns, filtering <1%
        if (dataType === 'hmda') {
            const demoGroups = ['hispanic', 'black', 'white', 'asian', 'native_american'];
            const demoLabels = ['Hispanic', 'Black', 'White', 'Asian', 'Native American'];
            
            demoGroups.forEach((group, i) => {
                // Check if this group represents >=1% of total area lending
                const groupTotal = allLenders.reduce((sum, lender) => {
                    const demo = lender.demographics[group] || {amount: 0};
                    return sum + (demo.amount || 0);
                }, 0);
                const groupPct = totalAreaLending > 0 ? (groupTotal / totalAreaLending * 100) : 0;
                
                if (groupPct >= 1.0) {
                    html += `<th>${demoLabels[i]}</th>`;
                }
            });
        }
        
        html += '</tr></thead>';
        html += '<tbody>';
        
        data.forEach(row => {
            html += '<tr>';
            html += `<td>${(row.name || '').toUpperCase()}</td>`;
            html += `<td>${row.type || 'Unknown'}</td>`;
            html += `<td>${formatNumber(row.total_loans)}</td>`;
            html += `<td>${formatCurrency(row.total_amount)}</td>`;
            
            // Render demographic columns (percentages only, filtered)
            if (dataType === 'hmda') {
                const demoGroups = ['hispanic', 'black', 'white', 'asian', 'native_american'];
                demoGroups.forEach(group => {
                    const groupTotal = allLenders.reduce((sum, lender) => {
                        const demo = lender.demographics[group] || {amount: 0};
                        return sum + (demo.amount || 0);
                    }, 0);
                    const groupPct = totalAreaLending > 0 ? (groupTotal / totalAreaLending * 100) : 0;
                    
                    if (groupPct >= 1.0) {
                        const demo = row.demographics[group] || {count: 0, percent: 0};
                        html += `<td>${demo.percent.toFixed(2)}%</td>`;
                    }
                });
            }
            
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        html += '</div>';
        html += '</div>';
    });
    
    html += '</div>';
    return html;
}

function renderHHIByYearTableByPurpose(dataByPurpose) {
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-pie"></i> Market Concentration (HHI) by Year</h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-table" data-table="hhi_by_year" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-table" data-table="hhi_by_year" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    
    // Tab interface
    html += '<div class="purpose-tabs">';
    html += '<button class="purpose-tab-btn active" data-purpose="all">All Loans</button>';
    html += '<button class="purpose-tab-btn" data-purpose="Home Purchase">Home Purchase</button>';
    html += '<button class="purpose-tab-btn" data-purpose="Refinance">Refinance</button>';
    html += '<button class="purpose-tab-btn" data-purpose="Home Equity">Home Equity</button>';
    html += '</div>';
    
    // Render table for each purpose (reuse existing renderHHIByYearTable logic)
    const purposes = ['all', 'Home Purchase', 'Refinance', 'Home Equity'];
    purposes.forEach((purpose, idx) => {
        const data = dataByPurpose[purpose] || [];
        html += `<div class="purpose-tab-content ${idx === 0 ? 'active' : ''}" data-purpose="${purpose}">`;
        if (data.length > 0) {
            html += renderHHIByYearTable(data).replace('<div class="analysis-table-card">', '').replace('</div>', '');
        } else {
            html += '<div class="table-container"><p>No data available for this loan purpose.</p></div>';
        }
        html += '</div>';
    });
    
    html += '</div>';
    return html;
}

function renderHHIByYearChart(hhiByYearByPurpose, dataType = 'hmda') {
    if (!hhiByYearByPurpose || Object.keys(hhiByYearByPurpose).length === 0) {
        return '';
    }
    
    // Debug: Log available purposes/categories
    console.log('[HHI Chart] Available categories in data:', Object.keys(hhiByYearByPurpose));
    Object.keys(hhiByYearByPurpose).forEach(key => {
        const data = hhiByYearByPurpose[key];
        if (Array.isArray(data)) {
            console.log(`[HHI Chart] ${key}: ${data.length} items`, data);
        } else {
            console.log(`[HHI Chart] ${key}:`, typeof data, data);
        }
    });
    
    // Get all years from all purposes/categories (2020-2024)
    const allYears = [];
    Object.values(hhiByYearByPurpose).forEach(purposeData => {
        if (Array.isArray(purposeData)) {
            purposeData.forEach(row => {
                const year = parseInt(row.year);
                if (year >= 2020 && year <= 2024 && !allYears.includes(year)) {
                    allYears.push(year);
                }
            });
        }
    });
    const years = allYears.sort();
    
    if (years.length === 0) {
        return '';
    }
    
    // Find the maximum HHI value across all purposes/categories and years for dynamic y-axis
    let maxHHI = 0;
    Object.values(hhiByYearByPurpose).forEach(purposeData => {
        if (Array.isArray(purposeData)) {
            purposeData.forEach(row => {
                if (row.hhi !== null && row.hhi !== undefined) {
                    maxHHI = Math.max(maxHHI, row.hhi);
                }
            });
        }
    });
    
    // Set y-axis max to be at least 3000 (to show threshold at 2500), or 20% above max value, whichever is higher
    const yAxisMax = Math.max(3000, Math.ceil(maxHHI * 1.2));
    
    // NCRC colors - different for branches, mortgage (loan purpose), and SB (revenue category)
    const colors = dataType === 'branches' ? {
        'all_branches': '#000000',              // Black for All Branches
        'lmi_branches': '#2fade3',              // NCRC secondary blue
        'mmct_branches': '#552d87',             // NCRC purple
        'both_lmi_mmct_branches': '#034ea0'     // NCRC dark blue
    } : dataType === 'sb' ? {
        'all': '#000000',                    // Black for All Loans
        'Under $1M Revenue': '#2fade3',     // NCRC secondary blue
        'Over $1M Revenue': '#552d87'       // NCRC purple
    } : {
        'all': '#000000',           // Black for All Loans
        'Home Purchase': '#2fade3',  // NCRC secondary blue
        'Refinance': '#552d87',     // NCRC purple
        'Home Equity': '#034ea0'     // NCRC dark blue
    };
    
    // Concentration threshold colors (for background shading)
    // Per 2023 DOJ/FTC Merger Guidelines: <1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), >2,500 (Highly Concentrated)
    const thresholdColors = {
        'Unconcentrated': '#2fade3',      // Blue (HHI < 1,500)
        'Moderately Concentrated': '#ffc23a', // Gold (HHI 1,500-2,500)
        'Highly Concentrated': '#e82e2e'     // Red (HHI > 2,500)
    };
    
    // Prepare datasets for each purpose/category with color based on concentration level
    let categories, categoryLabels;
    if (dataType === 'branches') {
        categories = ['all_branches', 'lmi_branches', 'mmct_branches', 'both_lmi_mmct_branches'];
        categoryLabels = {
            'all_branches': 'All Branches',
            'lmi_branches': 'LMI Branches',
            'mmct_branches': 'MMCT Branches',
            'both_lmi_mmct_branches': 'Both LMI & MMCT'
        };
    } else if (dataType === 'sb') {
        categories = ['all', 'Under $1M Revenue', 'Over $1M Revenue'];
        categoryLabels = {
            'all': 'All Loans',
            'Under $1M Revenue': 'Under $1M Revenue',
            'Over $1M Revenue': 'Over $1M Revenue'
        };
    } else {
        categories = ['all', 'Home Purchase', 'Refinance', 'Home Equity'];
        categoryLabels = {
            'all': 'All Loans',
            'Home Purchase': 'Home Purchase',
            'Refinance': 'Refinance',
            'Home Equity': 'Home Equity'
        };
    }
    
    const datasets = [];
    
    categories.forEach(category => {
        const categoryData = hhiByYearByPurpose[category] || [];
        console.log(`[HHI Chart] Processing category: ${category}, data length: ${categoryData.length}`, categoryData);
        
        const hhiData = years.map(year => {
            const yearData = categoryData.find(row => parseInt(row.year) === year);
            return yearData && yearData.hhi !== null && yearData.hhi !== undefined ? yearData.hhi : null;
        });
        
        // Use category color for all bars (not concentration level color)
        const categoryColor = colors[category] || '#818390';
        
        // Always add dataset (so categories show up even if empty or all null)
        datasets.push({
            label: categoryLabels[category] || category,
            data: hhiData,
            backgroundColor: categoryColor,
            borderColor: categoryColor,
            borderWidth: 2,
            hidden: false,
            // Ensure it shows in legend even if all values are null
            showInLegend: true
        });
    });
    
    // Threshold lines will be added via annotation plugin (see options.plugins.annotation below)
    
    // Store chart data for initialization
    if (!window.chartData) window.chartData = {};
    window.chartData['hhi-by-year-chart'] = {
        type: 'bar',
        data: {
            labels: years.map(y => y.toString()),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Year',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    max: yAxisMax, // Dynamic max based on highest HHI value, with minimum of 3000 to show thresholds
                    title: {
                        display: true,
                        text: 'HHI Value',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12
                        },
                        filter: function(legendItem) {
                            // Hide threshold lines from legend (they're just visual guides)
                            return !legendItem.text.includes('Threshold');
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.y;
                            if (value === null) return 'No data';
                            const datasetLabel = context.dataset.label || '';
                            // Find the category key from the label
                            let categoryKey = null;
                            if (dataType === 'branches') {
                                const labelToKey = {
                                    'All Branches': 'all_branches',
                                    'LMI Branches': 'lmi_branches',
                                    'MMCT Branches': 'mmct_branches',
                                    'Both LMI & MMCT': 'both_lmi_mmct_branches'
                                };
                                categoryKey = labelToKey[datasetLabel];
                            } else if (dataType === 'sb') {
                                categoryKey = datasetLabel === 'All Loans' ? 'all' : datasetLabel;
                            } else {
                                categoryKey = datasetLabel === 'All Loans' ? 'all' : datasetLabel;
                            }
                            const yearData = categoryKey ? (hhiByYearByPurpose[categoryKey] || []) : [];
                            const yearRow = yearData.find(row => parseInt(row.year) === parseInt(context.label));
                            const level = yearRow ? yearRow.concentration_level : '';
                            return `${datasetLabel}: ${value.toLocaleString()} (${level})`;
                        }
                    }
                },
                annotation: {
                    annotations: {
                        line1500: {
                            type: 'line',
                            yMin: 1500,
                            yMax: 1500,
                            borderColor: '#666666',
                            borderWidth: 2,
                            borderDash: [8, 4],
                            label: {
                                content: 'Unconcentrated (<1,500)',
                                enabled: true,
                                position: 'end',
                                backgroundColor: 'rgba(255,255,255,0.8)',
                                color: '#666666',
                                font: { size: 11, weight: 'bold' },
                                xAdjust: 0,
                                yAdjust: -10
                            }
                        },
                        line2500: {
                            type: 'line',
                            yMin: 2500,
                            yMax: 2500,
                            borderColor: '#666666',
                            borderWidth: 2,
                            borderDash: [8, 4],
                            label: {
                                content: 'Highly Concentrated (>2,500)',
                                enabled: true,
                                position: 'end',
                                backgroundColor: 'rgba(255,255,255,0.8)',
                                color: '#666666',
                                font: { size: 11, weight: 'bold' },
                                xAdjust: 0,
                                yAdjust: -10
                            }
                        }
                    }
                }
            }
        }
    };
    
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-bar"></i> Market Concentration (HHI) by Year</h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-chart" data-chart="hhi_by_year" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-chart" data-chart="hhi_by_year" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    if (dataType !== 'branches') {
        html += '<div style="padding: 10px 20px; background: #f0f7ff; border-left: 3px solid #2fade3; font-size: 0.9em; color: #333;">';
        html += '<i class="fas fa-info-circle" style="margin-right: 6px;"></i>';
        html += '<strong>Note:</strong> HHI is calculated using loan amounts (dollar volume), not loan counts.';
        html += '</div>';
    } else {
        html += '<div style="padding: 10px 20px; background: #f0f7ff; border-left: 3px solid #2fade3; font-size: 0.9em; color: #333;">';
        html += '<i class="fas fa-info-circle" style="margin-right: 6px;"></i>';
        html += '<strong>Note:</strong> HHI is calculated using deposits (dollar volume), not branch counts.';
        html += '</div>';
    }
    html += '<div class="chart-container" style="padding: 20px; position: relative; height: 450px;">';
    html += '<canvas id="hhi-by-year-chart" width="400" height="450"></canvas>';
    html += '</div>';
    html += '<div class="chart-legend" style="padding: 0 20px 20px 20px; font-size: 0.85em; color: #666;">';
    html += '<p style="margin: 0;"><strong>Concentration Levels (per 2023 DOJ/FTC Merger Guidelines):</strong> ';
    html += '<span style="color: #2fade3;">●</span> Unconcentrated (HHI &lt; 1,500), ';
    html += '<span style="color: #ffc23a;">●</span> Moderately Concentrated (HHI 1,500-2,500), ';
    html += '<span style="color: #e82e2e;">●</span> Highly Concentrated (HHI &gt; 2,500)';
    html += '</p>';
    html += '</div>';
    html += '</div>';
    
    return html;
}

function renderTrendsChartByPurpose(dataByPurpose) {
    // Need to get summary data to build year-over-year chart
    // For now, use the trends data structure which has period-based changes
    // We'll need to reconstruct the actual year values from summary data
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-line"></i> Year-over-Year Trends</h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-chart" data-chart="trends" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-chart" data-chart="trends" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    
    // Tab interface
    html += '<div class="purpose-tabs">';
    html += '<button class="purpose-tab-btn active" data-purpose="all">All Loans</button>';
    html += '<button class="purpose-tab-btn" data-purpose="Home Purchase">Home Purchase</button>';
    html += '<button class="purpose-tab-btn" data-purpose="Refinance">Refinance</button>';
    html += '<button class="purpose-tab-btn" data-purpose="Home Equity">Home Equity</button>';
    html += '</div>';
    
    // Render chart for each purpose
    // Note: Trends data structure uses period format (e.g., "2020→2021")
    // We need to extract years and build cumulative values
    const purposes = ['all', 'Home Purchase', 'Refinance', 'Home Equity'];
    purposes.forEach((purpose, idx) => {
        const trendsData = dataByPurpose[purpose] || [];
        html += `<div class="purpose-tab-content ${idx === 0 ? 'active' : ''}" data-purpose="${purpose}">`;
        html += `<canvas id="trends-chart-${purpose.replace(/\s+/g, '-')}" width="400" height="200"></canvas>`;
        html += '</div>';
        
        // Extract years from periods and build cumulative data
        // For trends, we need to reconstruct the actual values
        // This is a simplified version - in production, we'd use summary_by_purpose data
        const periods = trendsData.map(row => row.period);
        const loanChanges = trendsData.map(row => row.loans?.change || 0);
        const amountChanges = trendsData.map(row => (row.amount?.change || 0) / 1000);
        
        // Store chart data for initialization
        if (!window.chartData) window.chartData = {};
        window.chartData[`trends-chart-${purpose.replace(/\s+/g, '-')}`] = {
            type: 'line',
            data: {
                labels: periods,
                datasets: [{
                    label: 'Total Loans Change',
                    data: loanChanges,
                    borderColor: '#2fade3',
                    backgroundColor: 'rgba(47, 173, 227, 0.1)',
                    yAxisID: 'y',
                    tension: 0.4
                }, {
                    label: 'Total Amount Change (thousands)',
                    data: amountChanges,
                    borderColor: '#ffc23a',
                    backgroundColor: 'rgba(255, 194, 58, 0.1)',
                    yAxisID: 'y1',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    y: { 
                        type: 'linear', 
                        position: 'left', 
                        title: { display: true, text: 'Number of Loans' },
                        beginAtZero: false
                    },
                    y1: { 
                        type: 'linear', 
                        position: 'right', 
                        title: { display: true, text: 'Amount (thousands)' }, 
                        grid: { drawOnChartArea: false },
                        beginAtZero: false
                    }
                }
            }
        };
    });
    
    html += '</div>';
    return html;
}

function renderSourcesCard(dataType) {
    const isSB = dataType === 'sb';
    let html = '<div class="analysis-table-card methods-card" style="margin-top: 32px;">';
    html += '<div class="table-header" style="background: #2fade3; color: white;">';
    html += '<h4><i class="fas fa-book"></i> Methods, Definitions & Calculations</h4>';
    html += '</div>';
    html += '<div class="methods-content" style="padding: 20px;">';
    
    // Formulas & Calculations
    html += '<h5 style="color: #2fade3; margin-bottom: 12px; font-size: 1.1rem;">Formulas & Calculations</h5>';
    html += '<ul style="line-height: 1.8; color: #333;">';
    html += '<li><strong>Average Loan Size:</strong> Total Loan Amount ÷ Total Number of Loans</li>';
    html += '<li><strong>Market Concentration (HHI):</strong> Sum of squared market shares (as percentages) × 10,000. HHI = Σ(market_share²) × 10,000</li>';
    html += '<li><strong>Market Share:</strong> (Lender\'s Total Loan Amount ÷ Total Area Loan Amount) × 100</li>';
    html += '<li><strong>Year-over-Year Change:</strong> ((Current Year Value - Previous Year Value) ÷ Previous Year Value) × 100</li>';
    html += '<li><strong>Percentage Point Change:</strong> Current Year Percentage - Previous Year Percentage</li>';
    html += '</ul>';
    
    // Definitions
    html += '<h5 style="color: #2fade3; margin-bottom: 12px; font-size: 1.1rem; margin-top: 24px;">Definitions</h5>';
    html += '<ul style="line-height: 1.8; color: #333;">';
    if (!isSB) {
        html += '<li><strong>Home Purchase:</strong> Loan purpose code 1</li>';
        html += '<li><strong>Refinance:</strong> Loan purpose codes 31 (Refinance) and 32 (Cash-out Refinance) combined</li>';
        html += '<li><strong>Home Equity:</strong> Loan purpose codes 2 (Home Improvement) and 4 (Other) combined</li>';
    }
    html += '<li><strong>Low & Moderate Income (LMI):</strong> ' + (isSB ? 'Census tracts' : 'Borrowers or census tracts') + ' with income ≤ 80% of area median income</li>';
    html += '<li><strong>LMI Census Tract (LMICT):</strong> Census tract where median income ≤ 80% of area median income</li>';
    html += '<li><strong>MMCT:</strong> Majority-Minority Census Tract (tract where ≥50% of residents are minority)</li>';
    if (isSB) {
        html += '<li><strong>Loan Size Categories:</strong> Under $100K, $100K-$250K, $250K-$1M</li>';
        html += '<li><strong>Business Revenue Categories:</strong> Under $1M Revenue, Over $1M Revenue</li>';
        html += '<li><strong>Neighborhood Income Groups:</strong> Low Income (≤50% AMI), Moderate Income (50-80% AMI), Middle Income (80-120% AMI), Upper Income (>120% AMI) - based on census tract income, not borrower income</li>';
    }
    html += '</ul>';
    
    // Data Sources
    html += '<h5 style="color: #2fade3; margin-bottom: 12px; font-size: 1.1rem; margin-top: 24px;">Data Sources</h5>';
    html += '<ul style="line-height: 1.8; color: #333;">';
    if (isSB) {
        html += '<li><strong>Small Business Lending Data:</strong> Community Reinvestment Act (CRA) small business lending data from federal banking regulators.</li>';
    } else {
        html += '<li><strong>HMDA Data:</strong> Home Mortgage Disclosure Act (HMDA) data from the Consumer Financial Protection Bureau (CFPB).</li>';
    }
    html += '<li><strong>Census Data:</strong> Demographic and household income data from the U.S. Census Bureau\'s American Community Survey (ACS) 5-Year Estimates (2018-2022). ';
    html += 'Specific datasets used: ';
    html += '<ul style="margin-top: 8px; margin-left: 20px;">';
    if (!isSB) {
        html += '<li><strong>Demographic Overview:</strong> ACS Table B02001 (Race) and B03003 (Hispanic or Latino Origin) for population percentages by racial/ethnic group.</li>';
    }
    html += '<li><strong>Household Income Distribution:</strong> HUD Low and Moderate Income Summary Data (derived from ACS special tabulations) or ACS Table B19001 (Income in the Past 12 Months) for household income brackets relative to Area Median Income (AMI).</li>';
    html += '<li><strong>Tract Income Distribution:</strong> ACS Table B11001 (Households) combined with ' + (isSB ? 'SB' : 'HMDA') + ' tract-to-MSA income percentage classifications to calculate the share of households living in low, moderate, middle, and upper income census tracts.</li>';
    html += '<li><strong>Tract Minority Distribution:</strong> ACS Table B11001 (Households) combined with ' + (isSB ? 'SB' : 'HMDA') + ' tract minority population percentages to calculate the share of households living in low, moderate, middle, and high minority census tracts using standard deviation methodology. ';
    html += 'Tracts are categorized based on the mean and standard deviation of minority population percentage across all tracts in the geography: ';
    html += '<ul style="margin-top: 8px; margin-left: 20px;">';
    html += '<li><strong>Low Minority Tracts:</strong> Minority population &lt; (mean - standard deviation)</li>';
    html += '<li><strong>Moderate Minority Tracts:</strong> Minority population between (mean - standard deviation) and mean</li>';
    html += '<li><strong>Middle Minority Tracts:</strong> Minority population between mean and (mean + standard deviation)</li>';
    html += '<li><strong>High Minority Tracts:</strong> Minority population &gt; (mean + standard deviation)</li>';
    html += '</ul>';
    html += 'The specific percentage ranges for each category are displayed in the table (shown in italics).</li>';
    html += '</ul>';
    html += '</li>';
    html += '<li><strong>Geographic Data:</strong> U.S. Census Bureau geographic crosswalk files for county, metro area, and census tract boundaries.</li>';
    html += '</ul>';
    
    // Methodology Notes
    html += '<h5 style="color: #2fade3; margin-bottom: 12px; font-size: 1.1rem; margin-top: 24px;">Methodology Notes</h5>';
    html += '<ul style="line-height: 1.8; color: #333;">';
    html += '<li>All loan amounts are displayed in ($000s)</li>';
    if (!isSB) {
        html += '<li>Demographic percentages are calculated as: (Loans to Group ÷ Total Loans with Demographic Data) × 100</li>';
    } else {
        html += '<li>Neighborhood income group percentages are calculated as: (Loans to Neighborhood Income Group ÷ Total Loans) × 100</li>';
    }
    html += '<li>Top lenders are ranked by total number of loans in the most recent year</li>';
    html += '<li>Columns representing less than 1% of total area lending are omitted from Top Lenders table</li>';
    html += '<li>HHI calculations use total loan amounts (dollar volume) for market share determination</li>';
    html += '<li>HHI = Σ(market_share²) × 10,000, where market_share is each lender\'s dollar volume ÷ total market dollar volume</li>';
    if (isSB) {
        html += '<li>For Small Business data, loan size category percentages (Under $100K, $100K-$250K, $250K-$1M) are calculated as percentages of the sum of all three categories to ensure they add up to 100%</li>';
        html += '<li>HHI is calculated separately for all loans, loans to businesses under $1M revenue, and loans to businesses over $1M revenue</li>';
    }
    html += '<li>HHI thresholds (2023 DOJ/FTC Merger Guidelines): &lt;1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), &gt;2,500 (Highly Concentrated). ';
    html += 'Source: <a href="https://www.justice.gov/d9/2023-12/2023%20Merger%20Guidelines.pdf" target="_blank">U.S. DOJ and FTC, 2023 Merger Guidelines</a>.</li>';
    html += '<li><strong>Important:</strong> HHI can appear low even when the top 5 lenders control a significant share (e.g., 45%) if many small lenders exist. The top 5 concentration percentage is shown alongside HHI to provide additional context.</li>';
    html += '</ul>';
    
    html += '</div>';
    html += '</div>';
    return html;
}

function renderMethodsCard(dataType = 'hmda') {
    const isSB = dataType === 'sb';
    let html = '<div class="analysis-table-card methods-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-book"></i> Methods, Definitions & Calculations</h4>';
    html += '</div>';
    html += '<div class="methods-content">';
    html += '<h5>Formulas & Calculations</h5>';
    html += '<ul>';
    html += '<li><strong>Average Loan Size:</strong> Total Loan Amount ÷ Total Number of Loans</li>';
    html += '<li><strong>Market Concentration (HHI):</strong> Sum of squared market shares (as percentages) × 10,000. HHI = Σ(market_share²) × 10,000</li>';
    html += '<li><strong>Market Share:</strong> (Lender\'s Total Loan Amount ÷ Total Area Loan Amount) × 100</li>';
    html += '<li><strong>Year-over-Year Change:</strong> ((Current Year Value - Previous Year Value) ÷ Previous Year Value) × 100</li>';
    html += '<li><strong>Percentage Point Change:</strong> Current Year Percentage - Previous Year Percentage</li>';
    html += '</ul>';
    html += '<h5>Definitions</h5>';
    html += '<ul>';
    if (!isSB) {
    html += '<li><strong>Home Purchase:</strong> Loan purpose code 1</li>';
    html += '<li><strong>Refinance:</strong> Loan purpose codes 31 (Refinance) and 32 (Cash-out Refinance) combined</li>';
    html += '<li><strong>Home Equity:</strong> Loan purpose codes 2 (Home Improvement) and 4 (Other) combined</li>';
    }
    html += '<li><strong>Low & Moderate Income (LMI):</strong> Borrowers or census tracts with income ≤ 80% of area median income</li>';
    html += '<li><strong>LMI Census Tract (LMICT):</strong> Census tract where median income ≤ 80% of area median income</li>';
    html += '<li><strong>Low & Moderate Income Census Tracts:</strong> Combined percentage of loans in Low Income and Moderate Income census tracts. Click to expand and view individual income tract categories (Low, Moderate, Middle, Upper Income Tracts).</li>';
    html += '<li><strong>MMCT (Majority-Minority Census Tracts):</strong> Census tracts where ≥50% of residents are minority (strictly 50% or more). Click to expand and view minority tract breakdowns with geography-specific percentage ranges calculated from the mean and standard deviation of minority percentages in the selected geography.</li>';
    html += '<li><strong>Minority Tract Categories (calculated dynamically for each geography):</strong>';
    html += '<ul style="margin-top: 0.5em; margin-bottom: 0.5em;">';
    html += '<li><strong>Low Minority Tracts:</strong> Minority population from 0% to (mean - standard deviation). The exact range is displayed in the table for the selected geography.</li>';
    html += '<li><strong>Moderate Minority Tracts:</strong> Minority population from (mean - standard deviation) to mean. The exact range is displayed in the table for the selected geography.</li>';
    html += '<li><strong>Middle Minority Tracts:</strong> Minority population from mean to (mean + standard deviation). The exact range is displayed in the table for the selected geography.</li>';
    html += '<li><strong>High Minority Tracts:</strong> Minority population from (mean + standard deviation) to 100%. The exact range is displayed in the table for the selected geography.</li>';
    html += '</ul>';
    html += '</li>';
    if (isSB) {
        html += '<li><strong>Loan Size Categories:</strong> Under $100K, $100K-$250K, $250K-$1M. These categories are displayed in the Top Lenders table only, not in the Income & Neighborhood Indicators table.</li>';
        html += '<li><strong>Loan Size Percentage Calculations:</strong> Percentages for loan size categories are calculated using the sum of all three categories (Under $100K + $100K-$250K + $250K-$1M) as the denominator, ensuring they sum to 100% within their group.</li>';
        html += '<li><strong>Business Revenue Categories:</strong> Under $1M Revenue, Over $1M Revenue</li>';
        html += '<li><strong>Income Groups:</strong> Low Income (≤50% AMI), Moderate Income (50-80% AMI), Middle Income (80-120% AMI), Upper Income (>120% AMI)</li>';
        html += '<li><strong>Count vs Amount Tabs:</strong> For Small Business data, you can switch between "Number of Loans" and "Amount of Loans" views in both the Income & Neighborhood Indicators table and the Top Lenders table. Each tab shows percentages calculated using the appropriate denominator (count-based or amount-based).</li>';
    }
    html += '</ul>';
    html += '<h5>Data Sources</h5>';
    html += '<ul>';
    if (isSB) {
        html += '<li>Small Business Lending data from CRA Small Business Lending Survey (Federal Financial Institutions Examination Council)</li>';
    } else {
    html += '<li>HMDA data from Consumer Financial Protection Bureau</li>';
    }
    html += '<li>Census demographic and household data from U.S. Census Bureau American Community Survey (ACS) 5-Year Estimates (2018-2022):';
    html += '<ul>';
    if (!isSB) {
        html += '<li>Demographic percentages: ACS Tables B02001 (Race) and B03003 (Hispanic or Latino Origin)</li>';
    }
    html += '<li>Household income distribution: HUD Low and Moderate Income Summary Data or ACS Table B19001 (Income in the Past 12 Months)</li>';
    html += '<li>Tract distributions: ACS Table B11001 (Households) combined with ' + (isSB ? 'SB' : 'HMDA') + ' tract classifications</li>';
    html += '</ul>';
    html += '</li>';
    html += '<li>Geographic boundaries use 5-digit FIPS county codes</li>';
    html += '</ul>';
    html += '<h5>Methodology Notes</h5>';
    html += '<ul>';
    html += '<li>All loan amounts are displayed in ($000s)</li>';
    if (!isSB) {
    html += '<li>Demographic percentages are calculated as: (Loans to Group ÷ Total Loans with Demographic Data) × 100</li>';
    } else {
        html += '<li>Income group percentages are calculated as: (Loans to Income Group ÷ Total Loans with Income Data) × 100</li>';
    }
    html += '<li>Top lenders are ranked by total number of loans in the most recent year</li>';
    html += '<li>Columns representing less than 1% of total area lending are omitted from Top Lenders table</li>';
    html += '<li>HHI calculations use total loan amounts (dollar volume) for market share determination</li>';
    html += '<li>HHI = Σ(market_share²) × 10,000, where market_share is each lender\'s dollar volume ÷ total market dollar volume</li>';
    html += '<li>HHI thresholds (2023 DOJ/FTC Merger Guidelines): &lt;1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), &gt;2,500 (Highly Concentrated)</li>';
    html += '<li><strong>Important:</strong> HHI can appear low even when the top 5 lenders control a significant share (e.g., 45%) if many small lenders exist. The top 5 concentration percentage is shown alongside HHI to provide additional context.</li>';
    html += '</ul>';
    html += '</div>';
    html += '</div>';
    return html;
}

function initializeEditableTables() {
    // Editable functionality removed per user request - tables are now read-only
    // Keeping function for compatibility but removing edit handlers
    
    // Export table buttons (replaced Reset buttons)
    $('.btn-export-table').on('click', function() {
        const tableId = $(this).data('table');
        const format = $(this).data('format'); // 'excel' or 'png'
        const $tableCard = $(this).closest('.analysis-table-card');
        const $table = $tableCard.find(`.editable-table[data-table-id="${tableId}"]`);
        
        try {
        if (format === 'excel') {
            exportTableToExcel($table, tableId);
                showSuccess(`Table exported to Excel successfully`);
        } else if (format === 'png') {
            exportTableToPNG($tableCard, tableId);
                showSuccess(`Table exported as PNG image successfully`);
            }
        } catch (error) {
            showError(`Failed to export table: ${error.message}`);
        }
    });
    
    // Export chart buttons
    $(document).on('click', '.btn-export-chart', function() {
        const chartId = $(this).data('chart');
        const format = $(this).data('format'); // 'excel' or 'png'
        const $chartCard = $(this).closest('.analysis-table-card');
        
        try {
        if (format === 'excel') {
            exportChartToExcel(chartId);
                showSuccess(`Chart exported to Excel successfully`);
        } else if (format === 'png') {
            exportChartToPNG($chartCard, chartId);
                showSuccess(`Chart exported as PNG image successfully`);
            }
        } catch (error) {
            showError(`Failed to export chart: ${error.message}`);
        }
    });
    
    // Share table buttons
    $(document).on('click', '.btn-share-table', function() {
        const tableId = $(this).data('table');
        const $tableCard = $(this).closest('.analysis-table-card');
        shareTableToSocial($tableCard, tableId);
    });
    
    // Share chart buttons
    $(document).on('click', '.btn-share-chart', function() {
        const chartId = $(this).data('chart');
        const $chartCard = $(this).closest('.analysis-table-card');
        shareChartToSocial($chartCard, chartId);
    });
    
    // Purpose tab switching (delegated for dynamically added content)
    $(document).on('click', '.purpose-tab-btn', function() {
        const purpose = $(this).data('purpose');
        const $card = $(this).closest('.analysis-table-card');
        
        // Update active tab
        $card.find('.purpose-tab-btn').removeClass('active');
        $(this).addClass('active');
        
        // Show/hide content - use both class and display style
        $card.find('.purpose-tab-content').removeClass('active').css('display', 'none');
        const $targetContent = $card.find(`.purpose-tab-content[data-purpose="${purpose}"]`);
        $targetContent.addClass('active').css('display', 'block');
    });
    
    // Event delegation for dynamically generated buttons (replaces inline onclick handlers)
    $(document).on('click', '[data-action="switch-income-tab"]', function(e) {
        e.preventDefault();
        const purpose = $(this).data('purpose');
        switchIncomeNeighborhoodTab(purpose);
    });
    
    $(document).on('click', '[data-action="switch-income-data-type"]', function(e) {
        e.preventDefault();
        const dataTypeTab = $(this).data('data-type');
        switchIncomeNeighborhoodDataType(dataTypeTab);
    });
    
    $(document).on('click', '[data-action="switch-demographics-tab"]', function(e) {
        e.preventDefault();
        const purpose = $(this).data('purpose');
        switchDemographicsTab(purpose);
    });
    
    $(document).on('click', '[data-action="switch-top-lenders-tab"]', function(e) {
        e.preventDefault();
        const purpose = $(this).data('purpose');
        const tableType = $(this).data('table-type') || null;
        switchTopLendersTab(purpose, tableType);
    });
    
    $(document).on('click', '[data-action="switch-top-lenders-data-type"]', function(e) {
        e.preventDefault();
        const dataTypeTab = $(this).data('data-type');
        const purpose = $(this).data('purpose') || 'all';
        const tableType = $(this).data('table-type') || 'indicators';
        switchTopLendersDataType(purpose, tableType, dataTypeTab);
    });
    
    // Keyboard navigation for tab buttons
    $(document).on('keydown', '[role="tab"]', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            $(this).click();
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault();
            const tabs = $(this).closest('.purpose-tabs').find('[role="tab"]');
            const currentIndex = tabs.index(this);
            let nextIndex;
            if (e.key === 'ArrowLeft') {
                nextIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
            } else {
                nextIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
            }
            tabs.eq(nextIndex).focus().click();
        }
    });
    
    // Keyboard navigation for buttons (Enter/Space)
    $(document).on('keydown', 'button:not([type="submit"]):not([type="reset"])', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            $(this).click();
        }
    });
    
    // Event delegation for sortable table headers
    $(document).on('click', '[data-action="sort-lenders"]', function(e) {
        e.preventDefault();
        const purpose = $(this).data('purpose');
        const sortColumn = $(this).data('sort');
        const tableType = $(this).data('table-type') || null;
        sortTopLendersTable(purpose, sortColumn, tableType);
    });
    
    $(document).on('keydown', '[data-action="sort-lenders"]', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            $(this).click();
        }
    });
    
    // Expand button functionality disabled - always show only top 10 lenders in UI
    // All lenders are included in Excel export
    // Event handler removed - button no longer exists
    
    // Expandable rows for Income & Neighborhood (delegated for dynamically added content)
    $(document).on('click', '.expandable-header', function(e) {
        e.preventDefault();
        e.stopPropagation();
        const expandId = $(this).data('expand');
        const $icon = $(this).find('.expand-icon');
        
        // Find the tab content container that contains this header
        const $tabContent = $(this).closest('.purpose-tab-content, .income-neighborhood-tab-content, .table-container');
        
        // Scope the search to the current tab content to avoid finding rows in hidden tabs
        // First try within the table container
        let $rows = $tabContent.length > 0 
            ? $tabContent.find(`.expandable-row[data-expand="${expandId}"]`)
            : $(`.expandable-row[data-expand="${expandId}"]`);
        
        console.log(`[Expand Rows] Clicked expandable header with expandId: ${expandId}, found ${$rows.length} expandable rows, tab content: ${$tabContent.length > 0 ? 'found' : 'not found'}`);
        
        // If no rows found in tab content, try searching in the table that contains this header
        if ($rows.length === 0) {
            const $table = $(this).closest('table');
            if ($table.length > 0) {
                $rows = $table.find(`.expandable-row[data-expand="${expandId}"]`);
                console.log(`[Expand Rows] Found ${$rows.length} rows in table`);
            }
        }
        
        // If still no rows found, try searching in the entire document (for backwards compatibility)
        if ($rows.length === 0) {
            console.warn(`[Expand Rows] No expandable rows found in tab content for expandId: ${expandId}, searching document`);
            $rows = $(`.expandable-row[data-expand="${expandId}"]`);
            console.log(`[Expand Rows] Found ${$rows.length} rows in document`);
        }
        
        if ($rows.length === 0) {
            console.warn(`[Expand Rows] No expandable rows found for expandId: ${expandId}`);
            console.warn(`[Expand Rows] Available expandable rows:`, $('.expandable-row').map((i, el) => $(el).attr('data-expand')).get());
            return;
        }
        
        // Check visibility using computed style (works even for hidden tabs)
        // Check the first row to determine current state
        const firstRow = $rows[0];
        let isVisible = false;
        if (firstRow) {
            const computedStyle = window.getComputedStyle(firstRow);
            isVisible = computedStyle.display !== 'none';
        }
        
        // Also check if any row is visible (for cases where some might be hidden)
        if (!isVisible && $rows.length > 0) {
            isVisible = Array.from($rows).some(row => {
                const style = window.getComputedStyle(row);
                return style.display !== 'none';
            });
        }
        
        console.log(`[Expand Rows] Current state - isVisible: ${isVisible}, rows count: ${$rows.length}`);
        
        if (isVisible) {
            // Collapse: hide all rows
            $rows.each(function() {
                this.style.display = 'none';
            });
            $icon.removeClass('fa-chevron-down').addClass('fa-chevron-right');
            console.log(`[Expand Rows] Collapsed rows for ${expandId}`);
        } else {
            // Expand: show all rows
            $rows.each(function() {
                this.style.display = '';
            });
            $icon.removeClass('fa-chevron-right').addClass('fa-chevron-down');
            console.log(`[Expand Rows] Expanded rows for ${expandId}`);
        }
    });
}

// Helper function to generate unique Excel sheet names (max 31 chars, must be unique)
function generateUniqueSheetName(baseName, purpose = '', existingNames = []) {
    // Excel sheet names are limited to 31 characters and must be unique
    let sheetName = purpose ? `${baseName} - ${purpose}` : baseName;
    
    // Truncate to 31 characters if needed
    if (sheetName.length > 31) {
        // Calculate how much we can keep from baseName
        const purposePart = purpose ? ` - ${purpose}` : '';
        const maxBaseLength = 31 - purposePart.length;
        if (maxBaseLength > 0) {
            sheetName = baseName.substring(0, maxBaseLength) + purposePart;
        } else {
            // If purpose is too long, use abbreviations
            const purposeAbbr = {
                'all': 'All',
                'Home Purchase': 'HP',
                'Refinance': 'Refi',
                'Home Equity': 'HE'
            };
            const abbr = purposeAbbr[purpose] || purpose.substring(0, 3);
            sheetName = `${baseName} - ${abbr}`;
            if (sheetName.length > 31) {
                sheetName = sheetName.substring(0, 31);
            }
        }
    }
    
    // Ensure uniqueness by appending a number if needed
    let finalName = sheetName;
    let counter = 1;
    while (existingNames.includes(finalName)) {
        const suffix = ` (${counter})`;
        const maxLength = 31 - suffix.length;
        finalName = sheetName.substring(0, maxLength) + suffix;
        counter++;
    }
    
    return finalName;
}

// Helper function to generate export filenames
function generateExportFilename(prefix, extension = 'xlsx') {
    const appName = 'DataExplorer';
    
    // Get geography name from selected filters
    let geographyName = 'Area';
    const geoType = DashboardState.areaFilters.geoType;
    const geoids = DashboardState.areaFilters.geoids || [];
    
    if (geoids.length > 0) {
        if (geoType === 'county') {
            // Get county name from select2 dropdown
            const $countySelect = $('#county-select-area');
            const selectedText = $countySelect.find('option:selected').first().text();
            if (selectedText) {
                // Extract county name (before comma if present)
                geographyName = selectedText.split(',')[0].trim();
            } else {
                // Fallback: try to get from metro/state counties display
                const $firstChecked = $('.county-checkbox:checked').first();
                if ($firstChecked.length) {
                    const label = $firstChecked.next('label').text();
                    geographyName = label.split(',')[0].trim();
                }
            }
        } else if (geoType === 'metro') {
            // Get metro name from select2 dropdown
            const $metroSelect = $('#metro-select-area');
            const selectedText = $metroSelect.find('option:selected').first().text();
            if (selectedText) {
                geographyName = selectedText.trim();
            }
        } else if (geoType === 'state') {
            // Get state name from select2 dropdown
            const $stateSelect = $('#state-select-area');
            const selectedText = $stateSelect.find('option:selected').first().text();
            if (selectedText) {
                geographyName = selectedText.trim();
            }
        }
    }
    
    // Sanitize geography name for filename (remove special characters, replace spaces)
    geographyName = geographyName
        .replace(/[<>:"/\\|?*]/g, '') // Remove invalid filename characters
        .replace(/\s+/g, '_') // Replace spaces with underscores
        .substring(0, 50); // Limit length
    
    // If geography name is still empty or just "Area", use a timestamp-based fallback
    if (!geographyName || geographyName === 'Area' || geographyName.trim() === '') {
        geographyName = 'Area';
    }
    
    // Generate unique timestamp using epoch milliseconds + random component
    // This ensures absolute uniqueness even if called multiple times in quick succession
    const epochTimestamp = Date.now();
    const randomComponent = Math.random().toString(36).substring(2, 8).toUpperCase(); // 6 random alphanumeric chars
    
    // Format: YYYYMMDD_HHMMSS_epoch_random (compact format to avoid long filenames)
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0].replace(/-/g, ''); // YYYYMMDD
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const timeStr = `${hours}${minutes}${seconds}`;
    
    // Construct filename: AppName_GeographyName_Date_Time_Epoch_Random_Prefix.extension
    // Keep it under 200 chars to avoid Windows path length issues
    let filename = `${appName}_${geographyName}_${dateStr}_${timeStr}_${epochTimestamp}_${randomComponent}_${prefix}.${extension}`;
    
    // Ensure filename doesn't exceed reasonable length (Windows has 260 char path limit)
    // If too long, truncate geography name but keep unique components
    const maxLength = 200;
    if (filename.length > maxLength) {
        const excess = filename.length - maxLength;
        const truncatedGeo = geographyName.substring(0, Math.max(10, geographyName.length - excess - 3)) + '...';
        filename = `${appName}_${truncatedGeo}_${dateStr}_${timeStr}_${epochTimestamp}_${randomComponent}_${prefix}.${extension}`;
        console.warn('[Export Filename] Filename too long, truncated:', filename);
    }
    
    // Debug logging
    console.log('[Export Filename] Generated:', filename);
    console.log('[Export Filename] Length:', filename.length, 'Geography:', geographyName, 'Type:', geoType);
    console.log('[Export Filename] Epoch:', epochTimestamp, 'Random:', randomComponent);
    
    return filename;
}

// Comprehensive Export Function - Export All Tables to Excel
function exportAllTablesToExcel() {
    if (typeof XLSX === 'undefined') {
        showError('Excel export library not loaded. Please refresh the page.');
        return;
    }
    
    if (!currentAnalysisData) {
        showError('No analysis data available to export. Please run an analysis first.');
        return;
    }
    
    try {
        const wb = XLSX.utils.book_new();
        const usedSheetNames = []; // Track used sheet names to ensure uniqueness
        
        // 1. Summary Table
        if (currentAnalysisData.summary && currentAnalysisData.summary.length > 0) {
            const summaryData = [];
            summaryData.push(['Year', 'Total Loans', 'Total Amount ($000s)', 'Average Amount ($000s)']);
            currentAnalysisData.summary.forEach(row => {
                summaryData.push([
                    row.year || row.activity_year,
                    row.total_loans || 0,
                    (row.total_amount || 0) / 1000,
                    (row.avg_amount || 0) / 1000
                ]);
            });
            const ws = XLSX.utils.aoa_to_sheet(summaryData);
            XLSX.utils.book_append_sheet(wb, ws, 'Summary');
        }
        
        // 2. Summary by Purpose (if available - HMDA only, not SB)
        if (currentDataType !== 'sb' && currentAnalysisData.summary_by_purpose && currentAnalysisData.summary_by_purpose.length > 0) {
            const purposeData = [];
            const years = Object.keys(currentAnalysisData.summary_by_purpose[0] || {})
                .filter(k => k !== 'loan_purpose' && !isNaN(parseInt(k)))
                .sort();
            
            purposeData.push(['Loan Purpose', ...years, 'Total Amount ($000s)']);
            currentAnalysisData.summary_by_purpose.forEach(row => {
                const rowData = [row.loan_purpose || 'Unknown'];
                let totalAmount = 0;
                years.forEach(year => {
                    const yearData = row[year];
                    if (yearData) {
                        rowData.push(yearData.total_loans || 0);
                        totalAmount += (yearData.total_amount || 0);
                    } else {
                        rowData.push(0);
                    }
                });
                rowData.push(totalAmount / 1000);
                purposeData.push(rowData);
            });
            const ws = XLSX.utils.aoa_to_sheet(purposeData);
            XLSX.utils.book_append_sheet(wb, ws, 'Summary by Purpose');
        }
        
        // 3. Demographics and Income & Neighborhood tables are exported by purpose below
        // (Sections 6 and 7) - removed redundant "all" versions since "All Loans" purpose covers this
        
        // 4. Top Lenders - Income & Neighborhood Indicators (ALL lenders included in export, not just top 10)
        if (currentAnalysisData.top_lenders && currentAnalysisData.top_lenders.length > 0) {
            const isSB = currentDataType === 'sb';
            const isBranches = currentDataType === 'branches';
            const hasIndicators = currentAnalysisData.top_lenders[0] && currentAnalysisData.top_lenders[0].performance_indicators;
            
            if (isBranches) {
                // Branches: Export ALL bank networks (not just top 10) with bank name, 2025 branches, 2025 deposits, branches changed, deposits changed, LMI share, MMCT share
                // Calculate all banks from raw_data
                const bankData = {};
                const latestYear = Math.max(...(currentAnalysisData.years || []));
                const latestYearStr = String(latestYear);
                const year2021Str = '2021';
                const has2021 = (currentAnalysisData.years || []).includes(2021);
                
                if (currentAnalysisData.raw_data && currentAnalysisData.raw_data.length > 0) {
                    currentAnalysisData.raw_data.forEach(row => {
                        const year = String(row.year || '');
                        const rssd = row.rssd || '';
                        const bankName = (row.bank_name || `Bank ${rssd.substring(0, 8) || 'Unknown'}`).toUpperCase();
                        const deposits = parseFloat(row.deposits || 0);
                        const isLMI = row.is_lmi_tract || 0;
                        const isMMCT = row.is_mmct_tract || 0;
                        
                        if (!bankData[rssd]) {
                            bankData[rssd] = {
                                name: bankName,
                                branches2025: 0,
                                deposits2025: 0,
                                branches2021: 0,
                                deposits2021: 0,
                                lmiBranches: 0,
                                mmctBranches: 0
                            };
                        }
                        
                        if (year === latestYearStr) {
                            bankData[rssd].branches2025 += 1;
                            bankData[rssd].deposits2025 += deposits;
                            if (isLMI) bankData[rssd].lmiBranches += 1;
                            if (isMMCT) bankData[rssd].mmctBranches += 1;
                        } else if (year === year2021Str && has2021) {
                            bankData[rssd].branches2021 += 1;
                            bankData[rssd].deposits2021 += deposits;
                        }
                    });
                }
                
                // Convert to array and sort by 2025 branches
                const allBanks = Object.keys(bankData).map(rssd => {
                    const data = bankData[rssd];
                    return {
                        rssd: rssd,
                        name: data.name,
                        branches2025: data.branches2025,
                        deposits2025: data.deposits2025,
                        branches2021: data.branches2021,
                        deposits2021: data.deposits2021,
                        branchesChange: data.branches2025 - data.branches2021,
                        depositsChange: data.deposits2025 - data.deposits2021,
                        lmiShare: data.branches2025 > 0 ? (data.lmiBranches / data.branches2025 * 100) : 0,
                        mmctShare: data.branches2025 > 0 ? (data.mmctBranches / data.branches2025 * 100) : 0
                    };
                }).sort((a, b) => b.branches2025 - a.branches2025);
                
                const lenderData = [];
                lenderData.push(['Rank', 'Bank Name', '2025 Branches', '2025 Deposits', 'Branches Changed (Since 2021)', 'Deposits Changed (Since 2021)', 'LMI Share (%)', 'MMCT Share (%)']);
                allBanks.forEach((bank, idx) => {
                    lenderData.push([
                        idx + 1,
                        bank.name,
                        bank.branches2025,
                        bank.deposits2025,
                        bank.branchesChange,
                        bank.depositsChange,
                        Math.round(bank.lmiShare * 100) / 100,
                        Math.round(bank.mmctShare * 100) / 100
                    ]);
                });
                const ws = XLSX.utils.aoa_to_sheet(lenderData);
                XLSX.utils.book_append_sheet(wb, ws, 'Top Bank Branch Networks');
            } else if (isSB && hasIndicators) {
                // SB: Export both count and amount tabs
                // Count tab
                const lenderDataCount = [];
                lenderDataCount.push(['Rank', 'Lender Name', 'Total Loans', 'LMICT (%)', 'Loans <$100K (%)', 'Loans $100K-$250K (%)', 'Loans $250K-$1M (%)', 'Loans to Biz <$1M Rev (%)']);
                currentAnalysisData.top_lenders.forEach((lender, idx) => {
                    const row = [
                        idx + 1,
                        (lender.name || lender.lender_name || 'Unknown').toUpperCase(),
                        lender.total_loans || 0
                    ];
                    if (lender.performance_indicators) {
                        row.push(
                            lender.performance_indicators.lmict_percent || 0,
                            lender.performance_indicators.under_100k_percent || 0,
                            lender.performance_indicators['100k_250k_percent'] || 0,
                            lender.performance_indicators['250k_1m_percent'] || 0,
                            lender.performance_indicators.rev_under_1m_percent || 0
                        );
                    }
                    lenderDataCount.push(row);
                });
                const wsCount = XLSX.utils.aoa_to_sheet(lenderDataCount);
                XLSX.utils.book_append_sheet(wb, wsCount, 'Top Lenders - Indicators (Count)');
                
                // Amount tab
                const lenderDataAmount = [];
                lenderDataAmount.push(['Rank', 'Lender Name', 'Total Amount', 'LMICT (%)', 'Loans <$100K (%)', 'Loans $100K-$250K (%)', 'Loans $250K-$1M (%)', 'Loans to Biz <$1M Rev (%)']);
                currentAnalysisData.top_lenders.forEach((lender, idx) => {
                    const row = [
                        idx + 1,
                        (lender.name || lender.lender_name || 'Unknown').toUpperCase(),
                        lender.total_amount || 0
                    ];
                    if (lender.performance_indicators) {
                        row.push(
                            lender.performance_indicators.lmict_amount_percent || 0,
                            lender.performance_indicators.under_100k_amount_percent || 0,
                            lender.performance_indicators['100k_250k_amount_percent'] || 0,
                            lender.performance_indicators['250k_1m_amount_percent'] || 0,
                            lender.performance_indicators.rev_under_1m_amount_percent || 0
                        );
                    }
                    lenderDataAmount.push(row);
                });
                const wsAmount = XLSX.utils.aoa_to_sheet(lenderDataAmount);
                XLSX.utils.book_append_sheet(wb, wsAmount, 'Top Lenders - Indicators (Amount)');
            } else if (hasIndicators) {
                // HMDA-specific columns
                const lenderData = [];
                lenderData.push(['Rank', 'Lender Name', 'Type', 'Total Loans', 'LMI Borrowers (%)', 'LMI Census Tracts (%)', 'MMCT (%)']);
                currentAnalysisData.top_lenders.forEach((lender, idx) => {
                    const row = [
                        idx + 1,
                        (lender.name || lender.lender_name || 'Unknown').toUpperCase(),
                        lender.type || 'Unknown',
                        lender.total_loans || 0
                    ];
                    if (lender.performance_indicators) {
                        row.push(
                            (lender.performance_indicators.lmib && lender.performance_indicators.lmib.percent) || 0,
                            (lender.performance_indicators.lmict && lender.performance_indicators.lmict.percent) || 0,
                            (lender.performance_indicators.mmct && lender.performance_indicators.mmct.percent) || 0
                        );
                    }
                    lenderData.push(row);
                });
                const ws = XLSX.utils.aoa_to_sheet(lenderData);
                XLSX.utils.book_append_sheet(wb, ws, 'Top Lenders - Indicators');
            } else {
                const lenderData = [];
                lenderData.push(['Rank', 'Lender Name', 'Type', 'Total Loans']);
                currentAnalysisData.top_lenders.forEach((lender, idx) => {
                    lenderData.push([
                        idx + 1,
                        (lender.name || lender.lender_name || 'Unknown').toUpperCase(),
                        lender.type || 'Unknown',
                        lender.total_loans || 0
                    ]);
                });
                const ws = XLSX.utils.aoa_to_sheet(lenderData);
                XLSX.utils.book_append_sheet(wb, ws, 'Top Lenders - Indicators');
            }
        }
        
        // 5b. Top Lenders - Demographics (ALL lenders included in export, not just top 10) - HMDA only
        if (currentDataType !== 'sb' && currentAnalysisData.top_lenders && currentAnalysisData.top_lenders.length > 0) {
            const lenderData = [];
            // Check if we have demographics (HMDA data)
            const hasDemographics = currentAnalysisData.top_lenders[0] && currentAnalysisData.top_lenders[0].demographics;
            if (hasDemographics) {
                lenderData.push(['Rank', 'Lender Name', 'Type', 'Total Loans', 'Hispanic (%)', 'Black (%)', 'White (%)', 'Asian (%)']);
            } else {
                lenderData.push(['Rank', 'Lender Name', 'Type', 'Total Loans']);
            }
            // Export ALL lenders, not just top 10
            currentAnalysisData.top_lenders.forEach((lender, idx) => {
                const row = [
                    idx + 1,
                    (lender.name || lender.lender_name || 'Unknown').toUpperCase(),
                    lender.type || 'Unknown',
                    lender.total_loans || 0
                ];
                if (hasDemographics && lender.demographics) {
                    row.push(
                        (lender.demographics.hispanic && lender.demographics.hispanic.percent) || 0,
                        (lender.demographics.black && lender.demographics.black.percent) || 0,
                        (lender.demographics.white && lender.demographics.white.percent) || 0,
                        (lender.demographics.asian && lender.demographics.asian.percent) || 0
                    );
                }
                lenderData.push(row);
            });
            const ws = XLSX.utils.aoa_to_sheet(lenderData);
            XLSX.utils.book_append_sheet(wb, ws, 'Top Lenders - Demographics');
        }
        
        // 6. Demographics (HMDA by Purpose, SB single table with income groups)
        if (currentDataType === 'sb' && currentAnalysisData.demographics && currentAnalysisData.demographics.length > 0) {
            // SB: Export income groups (single table, no purposes)
            const demoData = [];
            const firstRow = currentAnalysisData.demographics[0];
            const demoYears = Object.keys(firstRow)
                .filter(k => k !== 'group' && !isNaN(parseInt(k)))
                .map(k => parseInt(k))
                .sort();
            
            const header = ['Income Group', ...demoYears];
            demoData.push(header);
            
            currentAnalysisData.demographics.forEach(row => {
                const rowData = [row.group || 'Unknown'];
                demoYears.forEach(year => {
                    const yearData = row[year.toString()];
                    if (yearData) {
                        rowData.push(yearData.percent || 0);
                    } else {
                        rowData.push(0);
                    }
                });
                demoData.push(rowData);
            });
            const ws = XLSX.utils.aoa_to_sheet(demoData);
            XLSX.utils.book_append_sheet(wb, ws, 'Income Groups');
        } else if (currentAnalysisData.demographics_by_purpose) {
            // HMDA: Demographics by Purpose (all tabs)
            const purposes = ['all', 'Home Purchase', 'Refinance', 'Home Equity'];
            purposes.forEach(purpose => {
                const purposeData = currentAnalysisData.demographics_by_purpose[purpose];
                if (purposeData && purposeData.length > 0) {
                    const demoData = [];
                    // Extract years from first row
                    const firstRow = purposeData[0];
                    const demoYears = Object.keys(firstRow)
                        .filter(k => k !== 'group' && !isNaN(parseInt(k)))
                        .map(k => parseInt(k))
                        .sort();
                    
                    const header = ['Group', ...demoYears];
                    demoData.push(header);
                    
                    purposeData.forEach(row => {
                        const rowData = [row.group || 'Unknown'];
                        demoYears.forEach(year => {
                            const yearData = row[year.toString()];
                            if (yearData) {
                                rowData.push(yearData.percent || 0);
                            } else {
                                rowData.push(0);
                            }
                        });
                        demoData.push(rowData);
                    });
                    const ws = XLSX.utils.aoa_to_sheet(demoData);
                    const purposeLabel = purpose === 'all' ? 'All Loans' : purpose;
                    const sheetName = generateUniqueSheetName('Demographics', purposeLabel, usedSheetNames);
                    usedSheetNames.push(sheetName);
                    XLSX.utils.book_append_sheet(wb, ws, sheetName);
                }
            });
        }
        
        // 7. Income & Neighborhood (HMDA by Purpose, SB single table with count and amount tabs)
        if (currentDataType === 'sb' && currentAnalysisData.income_neighborhood && currentAnalysisData.income_neighborhood.length > 0) {
            // SB: Export both count and amount tabs
            const incomeYears = [...new Set(currentAnalysisData.income_neighborhood.map(d => {
                const keys = Object.keys(d).filter(k => k !== 'indicator' && !isNaN(parseInt(k)));
                return keys;
            }))].flat().filter((v, i, a) => a.indexOf(v) === i).sort();
            
            // Count tab
            const incomeDataCount = [];
            incomeDataCount.push(['Indicator', ...incomeYears]);
            currentAnalysisData.income_neighborhood.forEach(row => {
                const rowData = [row.indicator || 'Unknown'];
                incomeYears.forEach(year => {
                    const yearData = row[year];
                    if (yearData) {
                        rowData.push(yearData.percent || 0);
                    } else {
                        rowData.push(0);
                    }
                });
                incomeDataCount.push(rowData);
            });
            const wsCount = XLSX.utils.aoa_to_sheet(incomeDataCount);
            XLSX.utils.book_append_sheet(wb, wsCount, 'Income & Neighborhood (Count)');
            
            // Amount tab
            const incomeDataAmount = [];
            incomeDataAmount.push(['Indicator', ...incomeYears]);
            currentAnalysisData.income_neighborhood.forEach(row => {
                const rowData = [row.indicator || 'Unknown'];
                incomeYears.forEach(year => {
                    const yearData = row[year];
                    if (yearData) {
                        rowData.push(yearData.amount_percent || 0);
                    } else {
                        rowData.push(0);
                    }
                });
                incomeDataAmount.push(rowData);
            });
            const wsAmount = XLSX.utils.aoa_to_sheet(incomeDataAmount);
            XLSX.utils.book_append_sheet(wb, wsAmount, 'Income & Neighborhood (Amount)');
        } else if (currentAnalysisData.income_neighborhood_by_purpose) {
            // HMDA: Income & Neighborhood by Purpose (all tabs)
            const purposes = ['all', 'Home Purchase', 'Refinance', 'Home Equity'];
            purposes.forEach(purpose => {
                const purposeData = currentAnalysisData.income_neighborhood_by_purpose[purpose];
                if (purposeData && purposeData.length > 0) {
                    const incomeData = [];
                    const incomeYears = [...new Set(purposeData.map(d => {
                        // Extract years from row keys
                        const keys = Object.keys(d).filter(k => k !== 'indicator' && !isNaN(parseInt(k)));
                        return keys;
                    }))].flat().filter((v, i, a) => a.indexOf(v) === i).sort();
                    
                    const header = ['Indicator', ...incomeYears];
                    incomeData.push(header);
                    
                    purposeData.forEach(row => {
                        const rowData = [row.indicator || 'Unknown'];
                        incomeYears.forEach(year => {
                            const yearData = row[year];
                            if (yearData) {
                                rowData.push(yearData.percent || 0);
                            } else {
                                rowData.push(0);
                            }
                        });
                        incomeData.push(rowData);
                    });
                    const ws = XLSX.utils.aoa_to_sheet(incomeData);
                    const purposeLabel = purpose === 'all' ? 'All Loans' : purpose;
                    const sheetName = generateUniqueSheetName('Income & Neighborhood', purposeLabel, usedSheetNames);
                    usedSheetNames.push(sheetName);
                    XLSX.utils.book_append_sheet(wb, ws, sheetName);
                }
            });
        }
        
        // 8. Top Lenders by Purpose - Income & Neighborhood Indicators (all tabs) - ALL lenders included in export, not just top 10 - HMDA only
        if (currentDataType !== 'sb' && currentAnalysisData.top_lenders_by_purpose) {
            const purposes = ['all', 'Home Purchase', 'Refinance', 'Home Equity'];
            purposes.forEach(purpose => {
                const purposeData = currentAnalysisData.top_lenders_by_purpose[purpose];
                if (purposeData && purposeData.length > 0) {
                    const lenderData = [];
                    // Check if we have performance indicators (HMDA data)
                    const hasIndicators = purposeData[0] && purposeData[0].performance_indicators;
                    if (hasIndicators) {
                        lenderData.push(['Rank', 'Lender Name', 'Type', 'Total Loans', 'LMI Borrowers (%)', 'LMI Census Tracts (%)', 'MMCT (%)']);
                    } else {
                        lenderData.push(['Rank', 'Lender Name', 'Type', 'Total Loans']);
                    }
                    // Export ALL lenders for this purpose, not just top 10
                    purposeData.forEach((lender, idx) => {
                        const row = [
                            idx + 1,
                            (lender.name || lender.lender_name || 'Unknown').toUpperCase(),
                            lender.type || 'Unknown',
                            lender.total_loans || 0
                        ];
                        if (hasIndicators && lender.performance_indicators) {
                            row.push(
                                (lender.performance_indicators.lmib && lender.performance_indicators.lmib.percent) || 0,
                                (lender.performance_indicators.lmict && lender.performance_indicators.lmict.percent) || 0,
                                (lender.performance_indicators.mmct && lender.performance_indicators.mmct.percent) || 0
                            );
                        }
                        lenderData.push(row);
                    });
                    const ws = XLSX.utils.aoa_to_sheet(lenderData);
                    const purposeLabel = purpose === 'all' ? 'All Loans' : purpose;
                    const sheetName = generateUniqueSheetName('Top Lenders Indicators', purposeLabel, usedSheetNames);
                    usedSheetNames.push(sheetName);
                    XLSX.utils.book_append_sheet(wb, ws, sheetName);
                }
            });
        }
        
        // 8b. Top Lenders by Purpose - Demographics (all tabs) - ALL lenders included in export, not just top 10 - HMDA only
        if (currentDataType !== 'sb' && currentAnalysisData.top_lenders_by_purpose) {
            const purposes = ['all', 'Home Purchase', 'Refinance', 'Home Equity'];
            purposes.forEach(purpose => {
                const purposeData = currentAnalysisData.top_lenders_by_purpose[purpose];
                if (purposeData && purposeData.length > 0) {
                    const lenderData = [];
                    // Check if we have demographics (HMDA data)
                    const hasDemographics = purposeData[0] && purposeData[0].demographics;
                    if (hasDemographics) {
                        lenderData.push(['Rank', 'Lender Name', 'Type', 'Total Loans', 'Hispanic (%)', 'Black (%)', 'White (%)', 'Asian (%)']);
                    } else {
                        lenderData.push(['Rank', 'Lender Name', 'Type', 'Total Loans']);
                    }
                    // Export ALL lenders for this purpose, not just top 10
                    purposeData.forEach((lender, idx) => {
                        const row = [
                            idx + 1,
                            (lender.name || lender.lender_name || 'Unknown').toUpperCase(),
                            lender.type || 'Unknown',
                            lender.total_loans || 0
                        ];
                        if (hasDemographics && lender.demographics) {
                            row.push(
                                (lender.demographics.hispanic && lender.demographics.hispanic.percent) || 0,
                                (lender.demographics.black && lender.demographics.black.percent) || 0,
                                (lender.demographics.white && lender.demographics.white.percent) || 0,
                                (lender.demographics.asian && lender.demographics.asian.percent) || 0
                            );
                        }
                        lenderData.push(row);
                    });
                    const ws = XLSX.utils.aoa_to_sheet(lenderData);
                    const purposeLabel = purpose === 'all' ? 'All Loans' : purpose;
                    const sheetName = generateUniqueSheetName('Top Lenders Demographics', purposeLabel, usedSheetNames);
                    usedSheetNames.push(sheetName);
                    XLSX.utils.book_append_sheet(wb, ws, sheetName);
                }
            });
        }
        
        // 9. HHI by Year
        if (currentDataType === 'branches' && currentAnalysisData.hhi_by_year_full) {
            // Branches: Export HHI for all categories (all, LMI, MMCT, both)
            const categories = ['all_branches', 'lmi_branches', 'mmct_branches', 'both_lmi_mmct_branches'];
            const categoryLabels = {
                'all_branches': 'All Branches',
                'lmi_branches': 'LMI Branches',
                'mmct_branches': 'MMCT Branches',
                'both_lmi_mmct_branches': 'Both LMI & MMCT Branches'
            };
            
            categories.forEach(category => {
                const categoryData = currentAnalysisData.hhi_by_year_full[category];
                if (categoryData && categoryData.length > 0) {
                    const hhiData = [];
                    hhiData.push(['Year', 'HHI', 'Concentration Level', 'Total Deposits', 'Total Branches', 'Top 5 Market Share (%)']);
                    categoryData.forEach(row => {
                        const top5Share = row.top_lenders && row.top_lenders.length > 0
                            ? row.top_lenders.reduce((sum, lender) => sum + (lender.market_share || 0), 0)
                            : 0;
                        hhiData.push([
                            row.year || '',
                            row.hhi || null,
                            row.concentration_level || 'Not Available',
                            row.total_amount || 0,
                            row.total_branches || 0,
                            top5Share
                        ]);
                    });
                    const ws = XLSX.utils.aoa_to_sheet(hhiData);
                    const sheetName = generateUniqueSheetName('HHI by Year', categoryLabels[category], usedSheetNames);
                    usedSheetNames.push(sheetName);
                    XLSX.utils.book_append_sheet(wb, ws, sheetName);
                }
            });
        } else if (currentAnalysisData.hhi_by_year && currentAnalysisData.hhi_by_year.length > 0) {
            // HMDA/SB: Standard HHI export
            const hhiData = [];
            hhiData.push(['Year', 'HHI', 'Concentration Level', 'Top 5 Market Share (%)']);
            currentAnalysisData.hhi_by_year.forEach(row => {
                hhiData.push([
                    row.year || row.activity_year,
                    row.hhi || 0,
                    row.concentration_level || 'Unknown',
                    row.top5_market_share || 0
                ]);
            });
            const ws = XLSX.utils.aoa_to_sheet(hhiData);
            XLSX.utils.book_append_sheet(wb, ws, 'Market Concentration (HHI)');
        }
        
        // 10. HHI by Year by Purpose (HMDA) or by Revenue (SB)
        if (currentDataType === 'sb' && currentAnalysisData.hhi_by_year_by_revenue) {
            // SB: HHI by Revenue Category
            const revenueCategories = ['all', 'Under $1M Revenue', 'Over $1M Revenue'];
            revenueCategories.forEach(category => {
                const categoryData = currentAnalysisData.hhi_by_year_by_revenue[category];
                if (categoryData && categoryData.length > 0) {
                    const hhiData = [];
                    hhiData.push(['Year', 'HHI', 'Concentration Level', 'Total Amount ($000s)']);
                    categoryData.forEach(row => {
                        hhiData.push([
                            row.year || '',
                            row.hhi || null,
                            row.concentration_level || 'Not Available',
                            row.total_amount ? (row.total_amount / 1000) : 0
                        ]);
                    });
                    const ws = XLSX.utils.aoa_to_sheet(hhiData);
                    const categoryLabel = category === 'all' ? 'All Loans' : category;
                    const sheetName = generateUniqueSheetName('HHI by Year', categoryLabel, usedSheetNames);
                    usedSheetNames.push(sheetName);
                    XLSX.utils.book_append_sheet(wb, ws, sheetName);
                }
            });
        } else if (currentAnalysisData.hhi_by_year_by_purpose) {
            // HMDA: HHI by Year by Purpose (all tabs)
            const purposes = ['all', 'Home Purchase', 'Refinance', 'Home Equity'];
            purposes.forEach(purpose => {
                const purposeData = currentAnalysisData.hhi_by_year_by_purpose[purpose];
                if (purposeData && purposeData.length > 0) {
                    const hhiData = [];
                    hhiData.push(['Year', 'HHI', 'Concentration Level', 'Total Amount ($000s)']);
                    purposeData.forEach(row => {
                        hhiData.push([
                            row.year || '',
                            row.hhi || null,
                            row.concentration_level || 'Not Available',
                            row.total_amount ? (row.total_amount / 1000) : 0
                        ]);
                    });
                    const ws = XLSX.utils.aoa_to_sheet(hhiData);
                    const purposeLabel = purpose === 'all' ? 'All Loans' : purpose;
                    const sheetName = generateUniqueSheetName('HHI by Year', purposeLabel, usedSheetNames);
                    usedSheetNames.push(sheetName);
                    XLSX.utils.book_append_sheet(wb, ws, sheetName);
                }
            });
        }
        
        // 11. Top 10 Lenders Over Time (2020-2024) - Excel Export Only
        if (currentAnalysisData.top_lenders_by_year && Object.keys(currentAnalysisData.top_lenders_by_year).length > 0) {
            const topLendersOverTime = [];
            const exportYears = [2020, 2021, 2022, 2023, 2024];
            const availableYears = exportYears.filter(y => currentAnalysisData.top_lenders_by_year[y.toString()]);
            
            if (availableYears.length > 0) {
                // Get all unique lender names across all years (from top 10 of each year)
                const allLenderNames = new Set();
                availableYears.forEach(year => {
                    const yearLenders = currentAnalysisData.top_lenders_by_year[year.toString()] || [];
                    yearLenders.forEach(lender => {
                        const name = (lender.lender_name || lender.name || 'Unknown').toUpperCase();
                        allLenderNames.add(name);
                    });
                });
                
                // Get top 10 lenders from the latest year to determine which lenders to show
                const latestYear = Math.max(...availableYears);
                const latestYearLenders = currentAnalysisData.top_lenders_by_year[latestYear.toString()] || [];
                const top10LenderNames = latestYearLenders.slice(0, 10).map(l => 
                    (l.lender_name || l.name || 'Unknown').toUpperCase()
                );
                
                // Header row: Lender Name, then years for loans, then years for amounts
                const headerRow = ['Lender Name', ...availableYears.map(y => `${y} Loans`), ...availableYears.map(y => `${y} Amount ($000s)`)];
                topLendersOverTime.push(headerRow);
                
                // For each top 10 lender from latest year, get their data for all years
                top10LenderNames.forEach(lenderName => {
                    const lenderRow = [lenderName];
                    
                    // Add loan counts for each year
                    availableYears.forEach(year => {
                        const yearLenders = currentAnalysisData.top_lenders_by_year[year.toString()] || [];
                        const lender = yearLenders.find(l => 
                            (l.lender_name || l.name || 'Unknown').toUpperCase() === lenderName
                        );
                        lenderRow.push(lender ? (lender.total_loans || 0) : 0);
                    });
                    
                    // Add loan amounts for each year (in thousands)
                    availableYears.forEach(year => {
                        const yearLenders = currentAnalysisData.top_lenders_by_year[year.toString()] || [];
                        const lender = yearLenders.find(l => 
                            (l.lender_name || l.name || 'Unknown').toUpperCase() === lenderName
                        );
                        lenderRow.push(lender ? ((lender.total_amount || 0) / 1000) : 0);
                    });
                    
                    topLendersOverTime.push(lenderRow);
                });
                
                const wsTopLendersTime = XLSX.utils.aoa_to_sheet(topLendersOverTime);
                XLSX.utils.book_append_sheet(wb, wsTopLendersTime, 'Top 10 Lenders Over Time');
            }
        }
        
        // 12. Raw Data Sheet (Branches only)
        if (currentDataType === 'branches' && currentAnalysisData.raw_data && currentAnalysisData.raw_data.length > 0) {
            const rawData = [];
            // Get all unique keys from the first row
            const firstRow = currentAnalysisData.raw_data[0];
            const headers = Object.keys(firstRow);
            rawData.push(headers);
            
            // Add all rows
            currentAnalysisData.raw_data.forEach(row => {
                const rowData = headers.map(header => {
                    const value = row[header];
                    // Handle null/undefined
                    if (value === null || value === undefined) {
                        return '';
                    }
                    // Return as-is (numbers, strings, etc.)
                    return value;
                });
                rawData.push(rowData);
            });
            
            const ws = XLSX.utils.aoa_to_sheet(rawData);
            XLSX.utils.book_append_sheet(wb, ws, 'Raw Branch Data (sod25)');
        }
        
        // 12. Methods and Definitions Sheet
        const isSB = currentDataType === 'sb';
        const methodsData = [
            ['Methods, Definitions & Calculations'],
            [''],
            ['Formulas & Calculations'],
            ['Average Loan Size', 'Total Loan Amount ÷ Total Number of Loans'],
            ['Market Concentration (HHI)', 'Sum of squared market shares (as percentages) × 10,000. HHI = Σ(market_share²) × 10,000'],
            ['Market Share', '(Lender\'s Total Loan Amount ÷ Total Area Loan Amount) × 100'],
            ['Year-over-Year Change', '((Current Year Value - Previous Year Value) ÷ Previous Year Value) × 100'],
            ['Percentage Point Change', 'Current Year Percentage - Previous Year Percentage'],
            ['']
        ];
        
        if (isSB) {
            // SB-specific definitions
            methodsData.push(
                ['Definitions - Small Business Lending'],
                ['Loan Size Categories', 'Under $100K: Loans less than $100,000; $100K-$250K: Loans between $100,000 and $250,000; $250K-$1M: Loans between $250,000 and $1,000,000'],
                ['Business Revenue Categories', 'Under $1M Revenue: Loans to businesses with annual revenue under $1,000,000; Over $1M Revenue: Loans to businesses with annual revenue $1,000,000 or more'],
                ['Income Groups', 'Low Income: ≤50% of area median income; Moderate Income: 50-80% of area median income; Middle Income: 80-120% of area median income; Upper Income: >120% of area median income'],
                ['Low & Moderate Income Census Tract (LMICT)', 'Census tract where median income ≤ 80% of area median income'],
                ['MMCT', 'Majority-Minority Census Tract: Census tract where ≥50% of residents are minority'],
                ['Minority Tract Categories', 'Low Minority: <(mean - stddev); Moderate Minority: (mean - stddev) to mean; Middle Minority: mean to (mean + stddev); High Minority: >(mean + stddev)'],
                [''],
                ['Data Sources'],
                ['Small Business Lending Data', 'CRA Small Business Lending Survey (Consumer Financial Protection Bureau)'],
                ['Census Household Income Data', 'HUD Low and Moderate Income Summary Data or ACS Table B19001 (Income in the Past 12 Months)'],
                ['Census Tract Distribution Data', 'ACS Table B11001 (Households) combined with tract classifications'],
                ['Geographic Boundaries', 'Use 5-digit FIPS county codes'],
                [''],
                ['Methodology Notes'],
                ['Loan Amounts', 'All loan amounts are displayed in ($000s)'],
                ['Income Group Percentages', 'Calculated as: (Loans to Income Group ÷ Total Loans with Income Data) × 100'],
                ['Top Lenders', 'Ranked by total number of loans in the most recent year'],
                ['HHI Calculations', 'Use total loan amounts (dollar volume) for market share determination'],
                ['HHI Formula', 'HHI = Σ(market_share²) × 10,000, where market_share is each lender\'s dollar volume ÷ total market dollar volume'],
                ['HHI Thresholds', '<1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), >2,500 (Highly Concentrated)'],
                ['HHI Thresholds Source', '2023 DOJ/FTC Merger Guidelines'],
                ['Loan Size Category Percentages', 'Calculated as percentage of loans within the three size categories (Under $100K, $100K-$250K, $250K-$1M), not as percentage of total loans']
            );
        } else {
            // HMDA-specific definitions
            methodsData.push(
                ['Definitions - HMDA Mortgage Lending'],
                ['Home Purchase', 'Loan purpose code 1'],
                ['Refinance', 'Loan purpose codes 31 (Refinance) and 32 (Cash-out Refinance) combined'],
                ['Home Equity', 'Loan purpose codes 2 (Home Improvement) and 4 (Other) combined'],
                ['Low & Moderate Income (LMI)', 'Borrowers or census tracts with income ≤ 80% of area median income'],
                ['LMI Census Tract (LMICT)', 'Census tract where median income ≤ 80% of area median income'],
                ['MMCT', 'Majority-Minority Census Tract: Census tract where ≥50% of residents are minority'],
                ['Minority Tract Categories', 'Low Minority: <(mean - stddev); Moderate Minority: (mean - stddev) to mean; Middle Minority: mean to (mean + stddev); High Minority: >(mean + stddev)'],
                [''],
                ['Data Sources'],
                ['HMDA Data', 'Consumer Financial Protection Bureau'],
                ['Census Demographic Data', 'U.S. Census Bureau American Community Survey (ACS) 5-Year Estimates (2018-2022), Tables B02001 (Race) and B03003 (Hispanic or Latino Origin)'],
                ['Census Household Income Data', 'HUD Low and Moderate Income Summary Data or ACS Table B19001 (Income in the Past 12 Months)'],
                ['Census Tract Distribution Data', 'ACS Table B11001 (Households) combined with HMDA tract classifications'],
                ['Geographic Boundaries', 'Use 5-digit FIPS county codes'],
                [''],
                ['Methodology Notes'],
                ['Loan Amounts', 'All loan amounts are displayed in ($000s)'],
                ['Demographic Percentages', 'Calculated as: (Loans to Group ÷ Total Loans with Demographic Data) × 100'],
                ['Top Lenders', 'Ranked by total number of loans in the most recent year'],
                ['Lender Columns', 'Columns representing less than 1% of total area lending are omitted from Top Lenders table'],
                ['HHI Calculations', 'Use total loan amounts (dollar volume) for market share determination'],
                ['HHI Formula', 'HHI = Σ(market_share²) × 10,000, where market_share is each lender\'s dollar volume ÷ total market dollar volume'],
                ['HHI Thresholds', '<1,500 (Unconcentrated), 1,500-2,500 (Moderately Concentrated), >2,500 (Highly Concentrated)'],
                ['HHI Thresholds Source', '2023 DOJ/FTC Merger Guidelines'],
                ['HHI Context', 'HHI can appear low even when the top 5 lenders control a significant share (e.g., 45%) if many small lenders exist. The top 5 concentration percentage is shown alongside HHI to provide additional context.']
            );
        }
        const methodsWs = XLSX.utils.aoa_to_sheet(methodsData);
        XLSX.utils.book_append_sheet(wb, methodsWs, 'Methods & Definitions');
        
        // Generate filename using helper function (includes timestamp and random component)
        const filename = generateExportFilename('AllTables', 'xlsx');
        
        // Write file - XLSX.writeFile triggers download
        // The filename includes epoch timestamp and random component to ensure uniqueness
        try {
        XLSX.writeFile(wb, filename);
            console.log('[Excel Export] File saved with filename:', filename);
            showSuccess(`All tables exported successfully`);
    } catch (error) {
            console.error('[Excel Export] Error:', error);
            showError('Failed to export Excel file: ' + error.message);
            // Log the error details for debugging
            console.error('[Excel Export] Full error:', error);
        }
    } catch (error) {
        debugError('Error exporting all tables to Excel:', error);
        showError('Failed to export tables to Excel: ' + error.message);
    }
}

// Export Lender Analysis to Excel
function exportLenderAnalysisToExcel() {
    const filters = DashboardState.lenderFilters;
    const lenderAnalysis = DashboardState.currentLenderAnalysis;
    
    if (!filters.subjectLender) {
        showError('Please run an analysis first before exporting');
        return;
    }
    
    if (!lenderAnalysis.rawResults) {
        showError('No analysis data available. Please run an analysis first.');
        return;
    }
    
    // Get geoids
    let geoids = filters.geoids || [];
    if (!geoids.length) {
        if ($('#auto-selection-group').is(':visible')) {
            geoids = $('#auto-county-select').val() || [];
        } else {
            updateManualGeographySelection();
            geoids = filters.geoids || [];
        }
    }
    
    if (!geoids.length) {
        showError('Please select at least one geographic area');
        return;
    }
    
    // Get years
    let years = filters.years || [];
    if (!years.length) {
        if (filters.dataType === 'hmda') {
            years = [2020, 2021, 2022, 2023, 2024];
        } else if (filters.dataType === 'sb') {
            years = [2019, 2020, 2021, 2022, 2023];
        } else {
            years = [2021, 2022, 2023, 2024, 2025];
        }
    }
    
    showLoading('Generating Excel export...');
    
    // Prepare payload for Excel export
    const payload = {
        subjectLenderId: filters.subjectLender,
        subjectLenderName: lenderAnalysis.subjectLenderName || 'Subject Lender',
        geoids: geoids,
        years: years,
        dataType: filters.dataType,
        enablePeerComparison: filters.enablePeerComparison || false,
        customPeers: filters.customPeers || [],
        includeAllDataTypes: true,
        assessmentAreas: lenderAnalysis.assessmentAreas || {},
        rawResults: lenderAnalysis.rawResults,
        // HMDA filters
        filters: {
            loanPurpose: filters.hmdaFilters?.loanPurpose || [],
            actionTaken: filters.hmdaFilters?.actionTaken || ['1', '2', '3', '4', '5'],
            occupancyType: filters.hmdaFilters?.occupancyType || ['1'],
            totalUnits: filters.hmdaFilters?.totalUnits || ['1', '2', '3', '4'],
            constructionMethod: filters.hmdaFilters?.constructionMethod || ['1'],
            excludeReverseMortgages: filters.hmdaFilters?.excludeReverseMortgages !== false
        }
    };
    
    // Use fetch API for file download
    fetch('/api/lender/export-excel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        hideLoading();
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.error || 'Export failed');
            });
        }
        return response.blob();
    })
    .then(blob => {
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${lenderAnalysis.subjectLenderName || 'Lender'}_Analysis.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showSuccess('Excel export downloaded successfully');
    })
    .catch(error => {
        hideLoading();
        showError('Failed to export Excel: ' + error.message);
        console.error('Excel export error:', error);
    });
}

// Export Functions
function exportTableToExcel($table, tableId) {
    if (typeof XLSX === 'undefined') {
        showError('Excel export library not loaded. Please refresh the page.');
        return;
    }
    
    try {
        // Get table data
        const data = [];
        const headers = [];
        
        // Get headers
        $table.find('thead th').each(function() {
            headers.push($(this).text().trim());
        });
        data.push(headers);
        
        // Get rows
        $table.find('tbody tr').each(function() {
            const row = [];
            $(this).find('td').each(function() {
                // Get text content, removing formatting
                let cellText = $(this).text().trim();
                // Try to extract numeric value if it's a formatted number
                const numericMatch = cellText.match(/[\d,]+\.?\d*/);
                if (numericMatch) {
                    cellText = numericMatch[0].replace(/,/g, '');
                }
                row.push(cellText);
            });
            data.push(row);
        });
        
        // Create workbook
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(data);
        XLSX.utils.book_append_sheet(wb, ws, tableId);
        
        // Generate filename using helper function (includes timestamp and random component)
        const filename = generateExportFilename(tableId, 'xlsx');
        
        // Write file - XLSX.writeFile triggers download
        // The filename includes epoch timestamp and random component to ensure uniqueness
        try {
        XLSX.writeFile(wb, filename);
            console.log('[Excel Export] File saved with filename:', filename);
            showSuccess(`Table exported successfully`);
        } catch (error) {
            console.error('[Excel Export] Error:', error);
            showError('Failed to export Excel file: ' + error.message);
            // Log the error details for debugging
            console.error('[Excel Export] Full error:', error);
        }
    } catch (error) {
        console.error('Error exporting to Excel:', error);
        showError('Failed to export table to Excel: ' + error.message);
    }
}

function exportTableToPNG($tableCard, tableId) {
    if (typeof html2canvas === 'undefined') {
        showError('Image export library not loaded. Please refresh the page.');
        return;
    }
    
    try {
        // Detect mobile device and adjust scale accordingly
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const scale = isMobile ? 3 : 2; // Higher scale for mobile for better quality
        
        html2canvas($tableCard[0], {
            backgroundColor: '#ffffff',
            scale: scale,
            logging: false,
            useCORS: true,
            allowTaint: true,
            width: $tableCard[0].scrollWidth,
            height: $tableCard[0].scrollHeight
        }).then(function(canvas) {
            // Convert canvas to blob
            canvas.toBlob(function(blob) {
                // Create download link
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                // Generate filename using helper function
                link.download = generateExportFilename(tableId, 'png');
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }, 'image/png', 0.95); // High quality PNG
        });
    } catch (error) {
        console.error('Error exporting to PNG:', error);
        showError('Failed to export table as image: ' + error.message);
    }
}

function exportChartToExcel(chartId) {
    if (typeof XLSX === 'undefined') {
        showError('Excel export library not loaded. Please refresh the page.');
        return;
    }
    
    try {
        const rawData = window.chartRawData && window.chartRawData[chartId];
        if (!rawData) {
            showError('Chart data not available for export.');
            return;
        }
        
        const { data, years, purposes } = rawData;
        
        // Build Excel data: rows are purposes, columns are years + Total Amount
        const excelData = [];
        
        // Header row
        const headers = ['Loan Purpose', ...years, 'Total Amount'];
        excelData.push(headers);
        
        // Data rows
        purposes.forEach(purpose => {
            const row = data.find(r => r.loan_purpose === purpose);
            const rowData = [purpose];
            
            let totalLoans = 0;
            let totalAmount = 0;
            
            years.forEach(year => {
                if (row && row[year]) {
                    const loans = row[year].total_loans || 0;
                    const amount = row[year].total_amount || 0;
                    rowData.push(loans);
                    totalLoans += loans;
                    totalAmount += amount;
                } else {
                    rowData.push(0);
                }
            });
            
            // Add total amount in thousands
            rowData.push(totalAmount / 1000);
            
            excelData.push(rowData);
        });
        
        // Create workbook
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(excelData);
        
        // Set column widths
        const colWidths = [{ wch: 20 }, ...years.map(() => ({ wch: 12 })), { wch: 15 }];
        ws['!cols'] = colWidths;
        
        XLSX.utils.book_append_sheet(wb, ws, 'Summary by Purpose');
        
        // Generate filename using helper function (includes timestamp and random component)
        const filename = generateExportFilename(chartId, 'xlsx');
        
        // Write file - XLSX.writeFile triggers download
        // The filename includes epoch timestamp and random component to ensure uniqueness
        try {
        XLSX.writeFile(wb, filename);
            console.log('[Excel Export] File saved with filename:', filename);
            showSuccess(`Chart exported successfully`);
        } catch (error) {
            console.error('[Excel Export] Error:', error);
            showError('Failed to export Excel file: ' + error.message);
            // Log the error details for debugging
            console.error('[Excel Export] Full error:', error);
        }
    } catch (error) {
        console.error('Error exporting chart to Excel:', error);
        showError('Failed to export chart to Excel: ' + error.message);
    }
}

function exportChartToPNG($chartCard, chartId) {
    if (typeof Chart === 'undefined') {
        showError('Chart.js library not loaded. Please refresh the page.');
        return;
    }
    
    try {
        // Map chartId to canvas ID
        // Chart IDs like 'hhi_by_year' map to canvas IDs like 'hhi-by-year-chart'
        const canvasIdMap = {
            'hhi_by_year': 'hhi-by-year-chart',
            'summary_by_purpose': 'summary-by-purpose-chart',
            'trends': 'trends-chart-all', // May need to handle active tab
            'yoy_chart_area': 'yoy-chart-area',
            'yoy_chart_lender': 'yoy-chart-lender'
        };
        
        // Find the canvas element - try mapped ID first, then search within card
        let $canvas = null;
        if (canvasIdMap[chartId]) {
            $canvas = $(`#${canvasIdMap[chartId]}`);
        }
        
        // If not found, search for canvas within the card
        if (!$canvas || $canvas.length === 0) {
            $canvas = $chartCard.find('canvas').first();
        }
        
        if (!$canvas || $canvas.length === 0) {
            showError('Chart canvas not found.');
            return;
        }
        
        // Get Chart.js instance
        const chartInstance = Chart.getChart($canvas[0]);
        if (!chartInstance) {
            showError('Chart instance not found.');
            return;
        }
        
        // Get the chart's canvas element (Chart.js renders directly to this)
        const chartCanvas = chartInstance.canvas;
        
        // Create a new canvas to add logo
        const finalCanvas = document.createElement('canvas');
        const ctx = finalCanvas.getContext('2d');
        
        // Set canvas size - same as chart canvas
        finalCanvas.width = chartCanvas.width;
        finalCanvas.height = chartCanvas.height;
        
        // Fill white background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, finalCanvas.width, finalCanvas.height);
        
        // Draw the chart canvas
        ctx.drawImage(chartCanvas, 0, 0);
        
        // Add NCRC logo in upper right corner
        addLogoToChartCanvas(finalCanvas, ctx, function(finalCanvasWithLogo) {
            // Convert canvas to blob
            finalCanvasWithLogo.toBlob(function(blob) {
                // Create download link
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                // Generate filename using helper function
                link.download = generateExportFilename(chartId, 'png');
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }, 'image/png', 0.95); // High quality PNG
        });
    } catch (error) {
        console.error('Error exporting chart to PNG:', error);
        showError('Failed to export chart as image: ' + error.message);
    }
}

function addLogoToChartCanvas(canvas, ctx, callback) {
    // Load NCRC logo
    const logo = new Image();
    logo.crossOrigin = 'anonymous';
    logo.onload = function() {
        // Logo dimensions - place in upper right corner above the chart data
        const logoHeight = 40; // Smaller logo for chart
        const logoWidth = (logo.width / logo.height) * logoHeight;
        const padding = 10;
        const logoX = canvas.width - logoWidth - padding;
        const logoY = padding;
        
        // Draw logo in upper right corner
        ctx.drawImage(logo, logoX, logoY, logoWidth, logoHeight);
        
        callback(canvas);
    };
    logo.onerror = function() {
        // If logo fails to load, just use chart without logo
        console.warn('NCRC logo not found, exporting chart without logo');
        callback(canvas);
    };
    // Try to load logo from static directory
    logo.src = '/static/img/ncrc-logo.png';
}

// Share Functions with NCRC Logo
function shareTableToSocial($tableCard, tableId) {
    if (typeof html2canvas === 'undefined') {
        showError('Image export library not loaded. Please refresh the page.');
        return;
    }
    
    try {
        // Detect mobile device and adjust scale accordingly
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const scale = isMobile ? 3 : 2; // Higher scale for mobile for better quality
        
        html2canvas($tableCard[0], {
            backgroundColor: '#ffffff',
            scale: scale,
            logging: false,
            useCORS: true,
            allowTaint: true,
            width: $tableCard[0].scrollWidth,
            height: $tableCard[0].scrollHeight
        }).then(function(canvas) {
            addLogoToCanvas(canvas, function(finalCanvas) {
                showShareDialog(finalCanvas, `DataExplorer_${tableId}`);
            });
        });
    } catch (error) {
        console.error('Error sharing table:', error);
        showError('Failed to share table: ' + error.message);
    }
}

function shareChartToSocial($chartCard, chartId) {
    if (typeof html2canvas === 'undefined') {
        showError('Image export library not loaded. Please refresh the page.');
        return;
    }
    
    try {
        // Detect mobile device and adjust scale accordingly
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const scale = isMobile ? 3 : 2; // Higher scale for mobile for better quality
        
        html2canvas($chartCard[0], {
            backgroundColor: '#ffffff',
            scale: scale,
            logging: false,
            useCORS: true,
            allowTaint: true,
            width: $chartCard[0].scrollWidth,
            height: $chartCard[0].scrollHeight
        }).then(function(canvas) {
            addLogoToCanvas(canvas, function(finalCanvas) {
                showShareDialog(finalCanvas, `DataExplorer_${chartId}`);
            });
        });
    } catch (error) {
        console.error('Error sharing chart:', error);
        showError('Failed to share chart: ' + error.message);
    }
}

function addLogoToCanvas(canvas, callback) {
    // Load NCRC logo
    const logo = new Image();
    logo.crossOrigin = 'anonymous';
    logo.onload = function() {
        // Create a new canvas with space for logo
        const finalCanvas = document.createElement('canvas');
        const ctx = finalCanvas.getContext('2d');
        
        // Set canvas size (original + padding for logo)
        const padding = 20;
        const logoHeight = 60; // Logo height
        finalCanvas.width = canvas.width;
        finalCanvas.height = canvas.height + logoHeight + padding;
        
        // Fill white background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, finalCanvas.width, finalCanvas.height);
        
        // Draw original canvas
        ctx.drawImage(canvas, 0, 0);
        
        // Draw logo at bottom right
        const logoWidth = (logo.width / logo.height) * logoHeight;
        const logoX = finalCanvas.width - logoWidth - padding;
        const logoY = canvas.height + padding;
        ctx.drawImage(logo, logoX, logoY, logoWidth, logoHeight);
        
        callback(finalCanvas);
    };
    logo.onerror = function() {
        // If logo fails to load, just use original canvas
        console.warn('NCRC logo not found, sharing without logo');
        callback(canvas);
    };
    // Try to load logo from static directory
    logo.src = '/static/img/ncrc-logo.png';
}

function showShareDialog(canvas, filename) {
    // Convert canvas to blob
    canvas.toBlob(function(blob) {
        const imageUrl = URL.createObjectURL(blob);
        
        // Detect mobile device
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        // Create share dialog with mobile-responsive styling
        const dialog = $(`
            <div class="share-dialog-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: ${isMobile ? '10px' : '20px'}; overflow-y: auto;">
                <div class="share-dialog" style="background: white; padding: ${isMobile ? '20px' : '30px'}; border-radius: 8px; max-width: ${isMobile ? '100%' : '500px'}; width: 100%; text-align: center; box-sizing: border-box;">
                    <h3 style="margin-top: 0; font-size: ${isMobile ? '1.2rem' : '1.5rem'};">Share to Social Media</h3>
                    <div style="margin: 20px 0;">
                        <img src="${imageUrl}" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px;" alt="Preview">
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: ${isMobile ? '8px' : '10px'}; justify-content: center; margin: 20px 0;">
                        <button class="btn-share-twitter" style="background: #1DA1F2; color: white; border: none; padding: ${isMobile ? '8px 16px' : '10px 20px'}; border-radius: 4px; cursor: pointer; font-size: ${isMobile ? '0.9rem' : '1rem'}; flex: ${isMobile ? '1 1 calc(33% - 8px)' : 'none'}; min-width: ${isMobile ? '0' : '120px'};">
                            <i class="fab fa-twitter"></i> ${isMobile ? '' : 'Twitter'}
                        </button>
                        <button class="btn-share-facebook" style="background: #4267B2; color: white; border: none; padding: ${isMobile ? '8px 16px' : '10px 20px'}; border-radius: 4px; cursor: pointer; font-size: ${isMobile ? '0.9rem' : '1rem'}; flex: ${isMobile ? '1 1 calc(33% - 8px)' : 'none'}; min-width: ${isMobile ? '0' : '120px'};">
                            <i class="fab fa-facebook"></i> ${isMobile ? '' : 'Facebook'}
                        </button>
                        <button class="btn-share-linkedin" style="background: #0077b5; color: white; border: none; padding: ${isMobile ? '8px 16px' : '10px 20px'}; border-radius: 4px; cursor: pointer; font-size: ${isMobile ? '0.9rem' : '1rem'}; flex: ${isMobile ? '1 1 calc(33% - 8px)' : 'none'}; min-width: ${isMobile ? '0' : '120px'};">
                            <i class="fab fa-linkedin"></i> ${isMobile ? '' : 'LinkedIn'}
                        </button>
                    </div>
                    <div style="margin: 20px 0; display: flex; flex-wrap: wrap; gap: ${isMobile ? '8px' : '10px'}; justify-content: center;">
                        <button class="btn-download-shared" style="background: #555; color: white; border: none; padding: ${isMobile ? '8px 16px' : '10px 20px'}; border-radius: 4px; cursor: pointer; font-size: ${isMobile ? '0.9rem' : '1rem'}; flex: ${isMobile ? '1 1 calc(50% - 4px)' : 'none'}; min-width: ${isMobile ? '0' : '120px'};">
                            <i class="fas fa-download"></i> Download
                        </button>
                        <button class="btn-close-share" style="background: #ccc; color: #333; border: none; padding: ${isMobile ? '8px 16px' : '10px 20px'}; border-radius: 4px; cursor: pointer; font-size: ${isMobile ? '0.9rem' : '1rem'}; flex: ${isMobile ? '1 1 calc(50% - 4px)' : 'none'}; min-width: ${isMobile ? '0' : '120px'};">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `);
        
        // Add to page
        $('body').append(dialog);
        
        // Twitter share
        dialog.find('.btn-share-twitter').on('click', function() {
            canvas.toBlob(function(blob) {
                const formData = new FormData();
                formData.append('image', blob, `${filename}.png`);
                // For Twitter, we'll use a data URL approach
                const reader = new FileReader();
                reader.onload = function() {
                    const dataUrl = reader.result;
                    // Note: Twitter's share URL doesn't support images directly
                    // User will need to upload manually or we'd need a backend service
                    window.open(`https://twitter.com/intent/tweet?text=Check%20out%20this%20data%20from%20%40NCRC%20DataExplorer&url=${encodeURIComponent(window.location.href)}`, '_blank');
                };
                reader.readAsDataURL(blob);
            });
        });
        
        // Facebook share
        dialog.find('.btn-share-facebook').on('click', function() {
            window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(window.location.href)}`, '_blank');
        });
        
        // LinkedIn share
        dialog.find('.btn-share-linkedin').on('click', function() {
            window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(window.location.href)}`, '_blank');
        });
        
        // Download
        dialog.find('.btn-download-shared').on('click', function() {
            canvas.toBlob(function(blob) {
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                // Generate filename using helper function
                link.download = generateExportFilename(filename, 'png');
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            });
        });
        
        // Close
        dialog.find('.btn-close-share, .share-dialog-overlay').on('click', function(e) {
            if (e.target === this || $(e.target).hasClass('btn-close-share')) {
                dialog.remove();
                URL.revokeObjectURL(imageUrl);
            }
        });
    }, 'image/png');
}

function saveCellEdit($cell, newValue, field) {
    const originalValue = $cell.data('value');
    const numValue = parseFloat(newValue) || 0;
    
    // Update the cell
    if (typeof originalValue === 'object') {
        // For demographic cells, update count and recalculate percent
        const total = getTotalForCell($cell);
        const newPercent = total > 0 ? (numValue / total * 100) : 0;
        const newData = {count: numValue, percent: newPercent};
        $cell.data('value', newData);
        $cell.removeClass('editing').html(`${formatNumber(numValue)} (${newPercent.toFixed(2)}%)`);
        $cell.addClass('edited');
    } else {
        $cell.data('value', numValue);
        if (field.includes('amount') || field === 'avg_amount' || field === 'total_amount') {
            $cell.removeClass('editing').text(formatCurrency(numValue));
        } else {
            $cell.removeClass('editing').text(formatNumber(numValue));
        }
        $cell.addClass('edited');
    }
}

function getTotalForCell($cell) {
    // Get total from the row or table context
    // This is a simplified version - may need refinement
    const $row = $cell.closest('tr');
    const $table = $cell.closest('table');
    // For now, return a default - this would need proper calculation
    return 1000; // Placeholder
}

// Chart Rendering Functions

function renderTrendChart(summaryData, dataType = 'hmda') {
    if (!summaryData || summaryData.length === 0) {
        return '';
    }
    
    // Sort data by year ascending for chart
    const sortedData = [...summaryData].reverse();
    const years = sortedData.map(row => row.year);
    const loans = sortedData.map(row => row.total_loans || 0);
    // All data types: amounts are already in full dollars from queries
    const amounts = sortedData.map(row => row.total_amount || 0);
    
    const chartId = `trend-chart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-line"></i> ' + (dataType === 'branches' ? 'Branch Network Trends' : 'Lending Trends Over Time') + '</h4>';
    html += '</div>';
    html += '<div class="chart-container" role="img" aria-label="Trend chart showing ' + (dataType === 'branches' ? 'branch' : 'lending') + ' data over time">';
    html += `<canvas id="${chartId}" aria-label="Line chart showing trends from ${years[0]} to ${years[years.length - 1]}"></canvas>`;
    html += '</div>';
    html += '</div>';
    
    // Store chart data for initialization
    if (!window.chartData) {
        window.chartData = {};
    }
    window.chartData[chartId] = {
        type: 'line',
        data: {
            labels: years,
            datasets: [
                {
                    label: dataType === 'branches' ? 'Total Branches' : 'Total Loans',
                    data: loans,
                    borderColor: 'rgb(47, 173, 227)', // NCRC Secondary Blue
                    backgroundColor: 'rgba(47, 173, 227, 0.1)',
                    yAxisID: 'y',
                    tension: 0.3,
                    fill: true
                },
                {
                    label: dataType === 'branches' ? 'Total Deposits' : 'Total Amount',
                    data: amounts,
                    borderColor: 'rgb(85, 45, 135)', // NCRC Primary Blue/Purple
                    backgroundColor: 'rgba(85, 45, 135, 0.1)',
                    yAxisID: 'y1',
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    }
                },
                tooltip: {
                    enabled: true,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: '600'
                    },
                    bodyFont: {
                        size: 12
                    },
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            if (label.includes('Amount') || label.includes('Deposits')) {
                                // Value is already in full dollars (converted from thousands)
                                return label + ': ' + formatCurrency(value);
                            }
                            return label + ': ' + formatNumber(value);
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Year',
                        font: {
                            size: 12,
                            weight: '600'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: dataType === 'branches' ? 'Number of Branches' : 'Number of Loans',
                        font: {
                            size: 12,
                            weight: '600'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: dataType === 'branches' ? 'Deposits ($)' : 'Loan Amount ($)',
                        font: {
                            size: 12,
                            weight: '600'
                        }
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                    ticks: {
                        callback: function(value) {
                            // Format with commas and appropriate scale - more dynamic and readable
                            const absValue = Math.abs(value);
                            if (absValue >= 1000000000) {
                                // For billions: always show 1 decimal place (e.g., $61.0B)
                                const billions = value / 1000000000;
                                return '$' + billions.toFixed(1) + 'B';
                            } else if (absValue >= 1000000) {
                                // For millions: show 1 decimal if >= 10M, otherwise 1 decimal
                                const millions = value / 1000000;
                                return '$' + millions.toFixed(absValue >= 10000000 ? 0 : 1) + 'M';
                            } else if (absValue >= 1000) {
                                // For thousands: show 1 decimal if >= 10K, otherwise 1 decimal
                                const thousands = value / 1000;
                                return '$' + thousands.toFixed(absValue >= 10000 ? 0 : 1) + 'K';
                            }
                            return '$' + Math.round(value).toLocaleString();
                        },
                        maxTicksLimit: 8
                    }
                }
            }
        }
    };
    
    return html;
}

function renderLoanSizeDistributionChart(incomeNeighborhoodData) {
    if (!incomeNeighborhoodData || incomeNeighborhoodData.length === 0) {
        return '';
    }
    
    // Find loan size categories from income_neighborhood data
    // The data structure should have indicators like "Loans Under $100K", "Loans $100K-$250K", "Loans $250K-$1M"
    const loanSizeCategories = [
        { key: 'under_100k', label: 'Under $100K', search: ['loans', 'under', '100'], exactMatch: 'Loans Under $100K' },
        { key: '100k_250k', label: '$100K-$250K', search: ['loans', '100', '250'], exactMatch: 'Loans $100K-$250K' },
        { key: '250k_1m', label: '$250K-$1M', search: ['loans', '250', '1m'], exactMatch: 'Loans $250K-$1M' }
    ];
    
    // Get years from first row
    const firstRow = incomeNeighborhoodData[0] || {};
    const years = Object.keys(firstRow).filter(k => k !== 'indicator' && k !== 'change' && !isNaN(parseInt(k)));
    years.sort();
    
    if (years.length === 0) {
        return '';
    }
    
    // Find rows matching loan size categories - try exact match first, then search terms
    const categoryData = {};
    incomeNeighborhoodData.forEach(row => {
        const indicator = row.indicator || '';
        const indicatorLower = indicator.toLowerCase();
        
        loanSizeCategories.forEach(category => {
            // Try exact match first
            let matches = indicator === category.exactMatch;
            
            // If no exact match, try search terms
            if (!matches) {
                matches = category.search.every(term => indicatorLower.includes(term.toLowerCase()));
            }
            
            if (matches) {
                if (!categoryData[category.key]) {
                    categoryData[category.key] = {};
                }
                years.forEach(year => {
                    if (row[year] && typeof row[year] === 'object') {
                        // Use amount instead of count for loan size distribution
                        categoryData[category.key][year] = row[year].amount || row[year].count || 0;
                    } else if (row[year]) {
                        categoryData[category.key][year] = parseFloat(row[year]) || 0;
                    } else {
                        categoryData[category.key][year] = 0;
                    }
                });
            }
        });
    });
    
    // Debug: Log what we found
    console.log('[Loan Size Chart] Category data found:', categoryData);
    console.log('[Loan Size Chart] Available indicators:', incomeNeighborhoodData.map(r => r.indicator));
    
    // Calculate total counts per year for market share calculations
    const yearlyTotals = {};
    years.forEach(year => {
        yearlyTotals[year] = 0;
        loanSizeCategories.forEach(category => {
            yearlyTotals[year] += categoryData[category.key] ? (categoryData[category.key][year] || 0) : 0;
        });
    });
    
    const chartId = `loan-size-chart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // NCRC colors for loan size categories
    const colors = {
        'Under $100K': '#2fade3',      // NCRC Secondary Blue
        '$100K-$250K': '#552d87',      // NCRC Purple
        '$250K-$1M': '#ffc23a'         // NCRC Gold
    };
    
    // Check if we found any data
    const hasData = Object.keys(categoryData).length > 0 && 
                    Object.values(categoryData).some(cat => Object.values(cat).some(val => val > 0));
    
    if (!hasData) {
        console.warn('[Loan Size Chart] No loan size category data found in income_neighborhood table');
        console.warn('[Loan Size Chart] Available indicators:', incomeNeighborhoodData.map(r => r.indicator));
        // Still render the chart structure but with zero data so user can see the framework
    }
    
    // Order: Under $100K (bottom), $100K-$250K (middle), $250K-$1M (top)
    // For stacked charts, first in array = bottom layer, last = top layer
    const datasets = loanSizeCategories.map((category) => {
        const data = years.map(year => {
            if (categoryData[category.key] && categoryData[category.key][year] !== undefined) {
                return categoryData[category.key][year] || 0;
            }
            return 0;
        });
        const baseColor = colors[category.label] || '#818390';
        
        return {
            label: category.label,
            data: data,
            borderColor: '#000000', // Black lines
            borderWidth: 2,
            backgroundColor: baseColor + 'E6', // Use E6 for ~90% opacity
            tension: 0.4,
            fill: true,
            stack: 'stack0' // Stack all datasets together
        };
    });
    
    // Store raw data for Excel export
    if (!window.chartRawData) window.chartRawData = {};
    window.chartRawData[chartId] = {
        data: incomeNeighborhoodData,
        years: years,
        categories: loanSizeCategories.map(c => c.label),
        yearlyTotals: yearlyTotals,
        metric: 'amount'
    };
    
    
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-area"></i> Loan Size Distribution</h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-chart" data-chart="loan_size_distribution" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-chart" data-chart="loan_size_distribution" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    
    html += '<div class="chart-container" style="padding: 20px; position: relative; height: 400px;">';
    html += `<canvas id="${chartId}" aria-label="Chart showing loan distribution by size category from ${years[0]} to ${years[years.length - 1]}"></canvas>`;
    html += '</div>';
    html += '</div>';
    
    // Store chart data for initialization
    if (!window.chartData) {
        window.chartData = {};
    }
    
    window.chartData[chartId] = {
        type: 'line', // Stacked area chart
        data: {
            labels: years,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Year',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Loan Amount ($)',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            },
            plugins: {
                legend: { 
                    display: true, 
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: { 
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y || 0;
                            const year = years[context.dataIndex];
                            const totalForYear = yearlyTotals[year] || 0;
                            const marketShare = totalForYear > 0 ? ((value / totalForYear) * 100).toFixed(1) : '0.0';
                            
                            // Format as currency (loan amount)
                            const formattedValue = formatCurrency(value);
                            
                            return [
                                label + ': ' + formattedValue,
                                'Market Share: ' + marketShare + '%'
                            ];
                        },
                        footer: function(tooltipItems) {
                            const year = years[tooltipItems[0].dataIndex];
                            const totalForYear = yearlyTotals[year] || 0;
                            const formattedTotal = formatCurrency(totalForYear);
                            return 'Total Market: ' + formattedTotal;
                        }
                    }
                },
                title: { display: false }
            }
        }
    };
    
    // Store chart data for initialization
    window.chartData[chartId] = {
        type: 'line', // Stacked area chart
        data: {
            labels: years,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Year',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Loan Amount ($)',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            },
            plugins: {
                legend: { 
                    display: true, 
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: { 
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y || 0;
                            const year = years[context.dataIndex];
                            const totalForYear = yearlyTotals[year] || 0;
                            const marketShare = totalForYear > 0 ? ((value / totalForYear) * 100).toFixed(1) : '0.0';
                            
                            // Format as currency (loan amount)
                            const formattedValue = formatCurrency(value);
                            
                            return [
                                label + ': ' + formattedValue,
                                'Market Share: ' + marketShare + '%'
                            ];
                        },
                        footer: function(tooltipItems) {
                            const year = years[tooltipItems[0].dataIndex];
                            const totalForYear = yearlyTotals[year] || 0;
                            const formattedTotal = formatCurrency(totalForYear);
                            return 'Total Market: ' + formattedTotal;
                        }
                    }
                },
                title: { display: false }
            }
        }
    };
    
    return html;
}

function renderBusinessSizeChart(incomeNeighborhoodData) {
    if (!incomeNeighborhoodData || incomeNeighborhoodData.length === 0) {
        return '';
    }
    
    // Find business revenue category rows from income_neighborhood data
    const revenueCategories = [
        { key: 'rev_under_1m', label: 'Loans to Businesses Under $1M Revenue', search: ['loans', 'businesses', 'under', '1m', 'revenue'] },
        { key: 'rev_over_1m', label: 'Loans to Businesses Over $1M Revenue', search: ['loans', 'businesses', 'over', '1m', 'revenue'] }
    ];
    
    // Get years from first row
    const firstRow = incomeNeighborhoodData[0] || {};
    const years = Object.keys(firstRow).filter(k => k !== 'indicator' && k !== 'change' && !isNaN(parseInt(k)));
    years.sort();
    
    if (years.length === 0) {
        return '';
    }
    
    // Find rows matching revenue categories
    const categoryData = {};
    incomeNeighborhoodData.forEach(row => {
        const indicator = (row.indicator || '').toLowerCase();
        
        revenueCategories.forEach(category => {
            // Check if indicator matches the category
            const matches = category.search.every(term => indicator.includes(term.toLowerCase()));
            
            if (matches) {
                if (!categoryData[category.key]) {
                    categoryData[category.key] = {};
                }
                years.forEach(year => {
                    if (row[year] && typeof row[year] === 'object') {
                        // Use amount for business size chart
                        categoryData[category.key][year] = row[year].amount || 0;
                    } else if (row[year]) {
                        categoryData[category.key][year] = parseFloat(row[year]) || 0;
                    } else {
                        categoryData[category.key][year] = 0;
                    }
                });
            }
        });
    });
    
    // Check if we have data
    const hasData = Object.keys(categoryData).length > 0 && 
                    Object.values(categoryData).some(data => 
                        Object.values(data).some(val => val > 0)
                    );
    
    if (!hasData) {
        console.warn('[Business Size Chart] No revenue category data found');
        return '';
    }
    
    // Calculate totals for each year
    const yearlyTotals = {};
    years.forEach(year => {
        yearlyTotals[year] = 0;
        revenueCategories.forEach(category => {
            yearlyTotals[year] += categoryData[category.key] ? (categoryData[category.key][year] || 0) : 0;
        });
    });
    
    // Create datasets for stacked area chart
    const colors = {
        'rev_under_1m': '#2fade3',  // Blue for under $1M
        'rev_over_1m': '#ffc23a'    // Orange for over $1M
    };
    
    const datasets = revenueCategories.map(category => {
        const data = years.map(year => categoryData[category.key] ? (categoryData[category.key][year] || 0) : 0);
        return {
            label: category.label,
            data: data,
            borderColor: '#000000',
            borderWidth: 2,
            backgroundColor: colors[category.key] + 'E6',  // Add transparency
            tension: 0.4,
            fill: true,
            stack: 'stack0'
        };
    });
    
    const chartId = 'business-size-chart';
    
    // Store chart data for initialization
    if (!window.chartData) {
        window.chartData = {};
    }
    
    window.chartData[chartId] = {
        type: 'line', // Stacked area chart
        data: {
            labels: years,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Year',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Loan Amount ($)',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            },
            plugins: {
                legend: { 
                    display: true, 
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: { 
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y || 0;
                            const year = years[context.dataIndex];
                            const totalForYear = yearlyTotals[year] || 0;
                            const marketShare = totalForYear > 0 ? ((value / totalForYear) * 100).toFixed(1) : '0.0';
                            
                            // Format as currency (loan amount)
                            const formattedValue = formatCurrency(value);
                            
                            return [
                                label + ': ' + formattedValue,
                                'Market Share: ' + marketShare + '%'
                            ];
                        },
                        footer: function(tooltipItems) {
                            const year = years[tooltipItems[0].dataIndex];
                            const totalForYear = yearlyTotals[year] || 0;
                            const formattedTotal = formatCurrency(totalForYear);
                            return 'Total Market: ' + formattedTotal;
                        }
                    }
                },
                title: { display: false }
            }
        }
    };
    
    let html = '<div class="analysis-table-card">';
    html += '<div class="table-header">';
    html += '<h4><i class="fas fa-chart-area"></i> Small Business Loans by Business Size</h4>';
    html += '<div class="export-buttons">';
    html += '<button class="btn-export-chart" data-chart="business_size" data-format="png" title="Export as Image"><i class="fas fa-image"></i> PNG</button>';
    html += '<button class="btn-share-chart" data-chart="business_size" title="Share to Social Media"><i class="fas fa-share-alt"></i> Share</button>';
    html += '</div>';
    html += '</div>';
    
    html += '<div class="chart-container" style="padding: 20px; position: relative; height: 400px;">';
    html += `<canvas id="${chartId}" aria-label="Chart showing loan amounts by business revenue size from ${years[0]} to ${years[years.length - 1]}"></canvas>`;
    html += '</div>';
    html += '</div>';
    
    return html;
}

function initializeCharts() {
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded yet, retrying in 500ms...');
        setTimeout(initializeCharts, 500);
        return;
    }
    
    // Check if chart data exists
    if (!window.chartData || Object.keys(window.chartData).length === 0) {
        // No charts to initialize - this is fine, not all analyses have charts
        return;
    }
    
    // Register Chart.js annotation plugin if available
    // In Chart.js v4, the annotation plugin should auto-register when loaded via CDN
    // But we can manually register it if needed
    if (typeof Chart !== 'undefined' && Chart.register) {
        try {
            // Try different possible global variable names for the annotation plugin
            if (typeof chartjsPluginAnnotation !== 'undefined') {
                Chart.register(chartjsPluginAnnotation);
            } else if (typeof window.chartjsPluginAnnotation !== 'undefined') {
                Chart.register(window.chartjsPluginAnnotation);
            }
            // Note: When loaded via CDN, the plugin may auto-register, so this is just a fallback
        } catch (e) {
            console.warn('Chart.js annotation plugin registration:', e);
            // Plugin may have already auto-registered, which is fine
        }
    }
    
    Object.keys(window.chartData).forEach(chartId => {
        const canvas = document.getElementById(chartId);
        if (canvas && !canvas.chart) {
            try {
                const ctx = canvas.getContext('2d');
                const config = window.chartData[chartId];
                if (config && config.data) {
                    canvas.chart = new Chart(ctx, config);
                    // Store chart instance for tab switching
                    if (!window.chartInstances) {
                        window.chartInstances = {};
                    }
                    window.chartInstances[chartId] = canvas.chart;
                }
            } catch (error) {
                console.error('Error initializing chart ' + chartId + ':', error);
            }
        } else if (!canvas) {
            console.warn('Canvas element not found for chart: ' + chartId);
        }
    });
    
    // Don't clean up chart data - we need it for tab switching
    // Only clean up if charts are being reinitialized (which happens on new analysis)
}


// Removed: Mortgage and Small Business Analysis tabs have been deleted
