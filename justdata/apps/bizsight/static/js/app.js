// DOM Elements - will be initialized when DOM is ready
let analysisForm, submitBtn, progressSection, resultsSection, errorSection, progressText, downloadBtn, errorMessage;

// Real-time progress tracking
let currentProgress = 0;

// Initialize DOM elements
function initDOMElements() {
    analysisForm = document.getElementById('analysisForm');
    submitBtn = document.getElementById('submitBtn');
    progressSection = document.getElementById('progressSection');
    resultsSection = document.getElementById('resultsSection');
    errorSection = document.getElementById('errorSection');
    progressText = document.getElementById('progressText');
    downloadBtn = document.getElementById('downloadBtn');
    errorMessage = document.getElementById('errorMessage');
}

// Form submission handler
function setupFormHandler() {
    if (!analysisForm) {
        // Form doesn't exist on this page (e.g., report page) - silently return
        return;
    }
    
    analysisForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(analysisForm);
    const startYear = formData.get('startYear');
    const endYear = formData.get('endYear');
    
    // Enhanced validation with helpful messages
    let hasErrors = false;
    
    // Year validation removed - years are now automatically set based on selection type
    // (County = 2020-2023, Planning Region = 2024 only, Other states = 2020-2024)
    
    // State selection is optional
    const selectedState = $('#state-filter-select').val();
    
    // Validate county selection (up to 3 counties)
    const selectedCounties = $('#county-select').val();
    if (!selectedCounties || selectedCounties.length === 0) {
        showValidationMessage(document.getElementById('county-select'), 'Please select at least one county to analyze.', 'error');
        hasErrors = true;
    } else if (selectedCounties.length > 3) {
        showValidationMessage(document.getElementById('county-select'), `Please select no more than 3 counties to analyze. You selected ${selectedCounties.length} counties.`, 'error');
        hasErrors = true;
    }
    
    if (hasErrors) {
        // Scroll to first error
        const firstError = document.querySelector('.validation-message.error');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
    }
    
    const start = parseInt(startYear);
    const end = parseInt(endYear);
    
    // Get loan purpose from checkboxes
    const loanPurpose = [];
    if (document.getElementById('loan_purpose_purchase') && document.getElementById('loan_purpose_purchase').checked) {
        loanPurpose.push('purchase');
    }
    if (document.getElementById('loan_purpose_refinance') && document.getElementById('loan_purpose_refinance').checked) {
        loanPurpose.push('refinance');
    }
    if (document.getElementById('loan_purpose_equity') && document.getElementById('loan_purpose_equity').checked) {
        loanPurpose.push('equity');
    }
    // Default to purchase if nothing selected
    if (loanPurpose.length === 0) {
        loanPurpose.push('purchase');
    }
    
    // Build request data (always use county selection)
    // Extract county data (with FIPS codes) if available, otherwise use county names
    const countiesData = selectedCounties.map(countyName => {
        // Try to get the full county object from the option's data attribute
        const option = $('#county-select option').filter(function() {
            return $(this).val() === countyName;
        }).first();
        
        const countyData = option.data('county-data');
        if (countyData && countyData.geoid5) {
            // Return the full county object with FIPS codes
            return countyData;
        } else {
            // Fallback: return just the county name (old format)
            return countyName;
        }
    });
    
    let requestData = {
        selection_type: 'county',
        state_code: selectedState,
        years: (() => {
            const years = [];
            for (let year = start; year <= end; year++) {
                years.push(year);
            }
            return years.join(',');
        })(),
        counties: selectedCounties.join(';'), // Keep for backward compatibility
        counties_data: countiesData, // New: send full county objects with FIPS codes
        loan_purpose: loanPurpose
    };
    
    // Debug logging
    console.log('Form submission - selectedState:', selectedState);
    console.log('Form submission - requestData:', requestData);
    
    // Show progress and disable form
    try {
        showProgress();
        disableForm();
        console.log('[DEBUG] Progress shown and form disabled');
    } catch (error) {
        console.error('[ERROR] Error showing progress/disabling form:', error);
    }
    
    let timeoutId = null;
    try {
        console.log('[DEBUG] Sending analyze request:', requestData);
        const controller = new AbortController();
        timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
        
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        console.log('[DEBUG] Received response, status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[ERROR] Response not OK:', response.status, errorText);
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }
        
        const result = await response.json();
        console.log('[DEBUG] Response JSON:', result);
        
        if (!result.success) {
            throw new Error(result.error || 'Analysis failed');
        }
        const jobId = result.job_id;
        console.log('[DEBUG] Got job_id:', jobId);
        listenForProgress(jobId);
    } catch (error) {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        console.error('[ERROR] Fetch error:', error);
        console.error('[ERROR] Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        if (error.name === 'AbortError') {
            showError('Request timed out. The server may be processing your request. Please check the progress indicator or try again.');
        } else {
            showError(error.message || 'Network error. Please check your connection and try again.');
        }
        hideProgress();
        enableForm();
    }
    });
}

// View report button handler
function setupViewReportHandler() {
    const viewReportBtn = document.getElementById('viewReportBtn');
    if (viewReportBtn) {
        viewReportBtn.addEventListener('click', function() {
            window.location.href = '/report';
        });
    }
}

// Download button handler
function setupDownloadHandler() {
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            window.location.href = '/download';
        });
    }
}

// Show progress section
function showProgress() {
    if (!progressSection || !resultsSection || !errorSection) return;
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    
    // Initialize progress steps
    initializeProgressSteps();
    updateProgressStep('initializing', 'active');
    
    // Initialize progress bar
    const progressFill = document.getElementById('progressFill');
    if (progressFill) progressFill.style.width = '0%';
    if (progressText) progressText.textContent = 'Initializing analysis...';
}

// Hide progress section
function hideProgress() {
    if (progressSection) progressSection.style.display = 'none';
}

// Show results section
function showResults(jobId) {
    // Add a small delay to ensure the analysis result is stored before redirecting
    // Also pass job_id as URL parameter as fallback if session doesn't persist
    setTimeout(function() {
        const url = jobId ? `/report?job_id=${jobId}` : '/report';
        window.location.href = url;
    }, 1000); // 1 second delay to ensure result is stored
}

// Show error section
function showError(message) {
    if (!errorMessage || !errorSection) return;
    errorMessage.textContent = message;
    errorSection.style.display = 'block';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    
    // Scroll to error
    errorSection.scrollIntoView({ behavior: 'smooth' });
}

// Disable form
function disableForm() {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Processing...</span>';
    
    // Disable inputs and selects
    const inputs = analysisForm.querySelectorAll('input, select');
    inputs.forEach(input => input.disabled = true);
}

// Enable form
function enableForm() {
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-magic"></i><span>Generate Analysis</span>';
    }
    
    // Enable inputs and selects
    if (analysisForm) {
        const inputs = analysisForm.querySelectorAll('input, select');
        inputs.forEach(input => input.disabled = false);
    }
}

// Reset form (for retry button)
function resetForm() {
    analysisForm.reset();
    errorSection.style.display = 'none';
    resultsSection.style.display = 'none';
    progressSection.style.display = 'none';
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Show validation message
function showValidationMessage(element, message, type = 'error') {
    // Check if element exists
    if (!element || !element.parentElement) {
        // Silently return - element might not exist in all app contexts
        // Only log in debug mode
        if (window.DEBUG_MODE) {
            console.warn('Cannot show validation message: element or parentElement is null');
        }
        return;
    }
    // Remove existing validation message
    const existing = element.parentElement.querySelector('.validation-message');
    if (existing) {
        existing.remove();
    }
    
    // Create new validation message
    const messageEl = document.createElement('div');
    messageEl.className = `validation-message ${type}`;
    messageEl.textContent = message;
    element.parentElement.appendChild(messageEl);
    
    // Update form group class
    const formGroup = element.closest('.form-group');
    if (formGroup) {
        formGroup.classList.remove('has-error', 'has-success');
        if (type === 'error') {
            formGroup.classList.add('has-error');
        } else if (type === 'success') {
            formGroup.classList.add('has-success');
        }
    }
}

// Hide validation message
function hideValidationMessage(element) {
    const message = element.parentElement.querySelector('.validation-message');
    if (message) {
        message.remove();
    }
    const formGroup = element.closest('.form-group');
    if (formGroup) {
        formGroup.classList.remove('has-error', 'has-success');
    }
}

// Input validation with helpful messages
function validateInput(input, type) {
    const value = input.value.trim();
    let isValid = true;
    let message = '';
    let messageType = 'error';
    
    if (type === 'county-select') {
        const selected = $('#county-select').val();
        if (!selected || selected.length === 0) {
            isValid = false;
            message = 'Please select at least one county to analyze.';
            input.setCustomValidity('Please select at least one county.');
        } else if (selected.length > 3) {
            isValid = true;
            message = `You've selected ${selected.length} counties. Analysis may take longer with more counties.`;
            messageType = 'info';
            input.setCustomValidity('');
        } else {
            isValid = true;
            message = `Great! You've selected ${selected.length} ${selected.length === 1 ? 'county' : 'counties'}.`;
            messageType = 'success';
            input.setCustomValidity('');
        }
    } else if (type === 'startYear' || type === 'endYear') {
        if (!value) {
            isValid = false;
            message = 'Please select a year.';
            input.setCustomValidity('Please select a year.');
        } else {
            const year = parseInt(value);
            if (isNaN(year) || year < 2017 || year > 2025) {
                isValid = false;
                message = 'Please select a valid year between 2017-2025.';
                input.setCustomValidity('Please select a valid year between 2017-2025.');
            } else {
                    // Year validation removed - years are automatically set
                    // (County = 2020-2023, Planning Region = 2024 only)
                    /*
                    // Check if the range is at least 3 years
                const startYearEl = document.getElementById('startYear');
                const endYearEl = document.getElementById('endYear');
                const startYear = startYearEl ? startYearEl.value : null;
                const endYear = endYearEl ? endYearEl.value : null;
                
                if (startYear && endYear) {
                    const start = parseInt(startYear);
                    const end = parseInt(endYear);
                    const yearRange = end - start + 1;
                    
                    if (start > end) {
                        isValid = false;
                        message = 'Start year must be before or equal to end year.';
                        input.setCustomValidity('Start year must be before or equal to end year.');
                    } else {
                        // Year validation removed - years are automatically set
                        // Allow any valid year range (planning regions = 1 year, counties = 4 years)
                        isValid = true;
                        message = `Years automatically set: ${start}-${end}`;
                        messageType = 'success';
                        input.setCustomValidity('');
                    }
                } else {
                    isValid = true;
                    input.setCustomValidity('');
                }
            */
            }
        }
    }

    // Show/hide validation message
    if (message) {
        showValidationMessage(input, message, messageType);
    } else {
        hideValidationMessage(input);
    }
    
    return isValid;
}




    }, 200);
}

// Add input validation listeners
$(document).ready(function() {
    // Initialize DOM elements first
    initDOMElements();
    
    // Setup form and button handlers
    setupFormHandler();
    setupViewReportHandler();
    setupDownloadHandler();
    
    // County selection validation - check if element exists
    const countySelect = $('#county-select');
    if (countySelect.length) {
        countySelect.on('change', function() {
            validateInput(this, 'county-select');
        });
    }
    
    // Year validation - check if element exists first
    const startYearInput = document.getElementById('startYear');
    if (startYearInput) {
        startYearInput.addEventListener('change', function() {
            validateInput(this, 'startYear');
            // Also validate end year when start year changes
            const endYearInput = document.getElementById('endYear');
            if (endYearInput && endYearInput.value) {
                validateInput(endYearInput, 'endYear');
            }
        });
    }
    
    const endYearInput = document.getElementById('endYear');
    if (endYearInput) {
        endYearInput.addEventListener('change', function() {
            validateInput(this, 'endYear');
            // Also validate start year when end year changes
            const startYearInput = document.getElementById('startYear');
            if (startYearInput && startYearInput.value) {
                validateInput(startYearInput, 'startYear');
            }
        });
    }
    
    // State selection validation - check if element exists
    const stateSelect = $('#state-filter-select');
    if (stateSelect.length) {
        stateSelect.on('change', function() {
            if (!this.value) {
                showValidationMessage(this, 'Please select a state to analyze.', 'error');
            } else {
                hideValidationMessage(this);
            }
        });
    }
    
    // Initialize sidebar tooltips
    initializeSidebarTooltips();
});

// Global function to ensure Select2 search inputs have proper attributes
function ensureSelect2SearchAttributes() {
    $('.select2-search__field').each(function() {
        const $input = $(this);
        if (!$input.attr('id') && !$input.attr('name')) {
            // Try to determine which Select2 this belongs to
            const $select2Container = $input.closest('.select2-container');
            if ($select2Container.length) {
                const $originalSelect = $select2Container.siblings('select');
                if ($originalSelect.length) {
                    const selectId = $originalSelect.attr('id');
                    if (selectId) {
                        $input.attr('id', selectId + '-search');
                        $input.attr('name', selectId + '-search');
                    }
                }
            }
        }
    });
}

// Add some nice animations and interactions
$(document).ready(function() {
    // Use MutationObserver to catch dynamically created Select2 search inputs
    const mutationObserver = new MutationObserver(function(mutations) {
        ensureSelect2SearchAttributes();
    });
    
    // Observe the document body for new elements
    mutationObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Also run immediately and periodically to catch any missed elements
    ensureSelect2SearchAttributes();
    setInterval(ensureSelect2SearchAttributes, 500);
    
    // Animate feature cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe feature cards (exclude sidebar and all its children to prevent flickering)
    const featureCards = document.querySelectorAll('.feature-card');
    const sidebar = document.querySelector('.sidebar');
    featureCards.forEach(card => {
        // Only animate if not inside sidebar
        if (!card.closest('.sidebar') && sidebar && !sidebar.contains(card)) {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        }
    });
    
    // Explicitly exclude sidebar and all its children from any observers
    if (sidebar) {
        const sidebarElements = sidebar.querySelectorAll('*');
        sidebarElements.forEach(el => {
            // Don't hide sidebar elements, just prevent transforms
            el.style.willChange = 'auto';
            // Only prevent translate transforms, not display
            if (el.style.transform && el.style.transform.includes('translateY')) {
                el.style.transform = 'none';
            }
            // Ensure visibility
            el.style.display = '';
            el.style.visibility = '';
            el.style.opacity = '';
        });
    }
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add loading state for download button
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Preparing download...</span>';
            this.disabled = true;
            
            // Reset after a delay (download should start)
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
            }, 3000);
        });
    }

    // Store all counties for filtering
    let allCounties = [];
    let countySelect2Initialized = false;
    
    // Function to load and populate counties
    function loadCounties(stateCode = null) {
        const $countySelect = $('#county-select');
        const selectedCounties = $countySelect.val() || [];
        
        let url = '/counties';
        if (stateCode) {
            url = `/counties-by-state/${stateCode}`;
        }
        
        console.log(`Fetching counties from: ${url}`);
        fetch(url)
            .then(response => {
                console.log(`Response status: ${response.status}, ok: ${response.ok}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(counties => {
                console.log('Raw response data type:', typeof counties, Array.isArray(counties));
                console.log('Raw response data sample:', counties ? counties.slice(0, 3) : 'null');
                console.log(`loadCounties: Received ${counties.length} counties from ${url}`);
                
                // Handle error response from backend
                if (counties.error) {
                    console.error('Backend error:', counties.error);
                    throw new Error(counties.error);
                }
                
                // Ensure counties is an array
                if (!Array.isArray(counties)) {
                    console.error('Invalid response format:', counties);
                    throw new Error('Invalid response format from server');
                }
                
                if (!stateCode) {
                    allCounties = counties; // Store all counties when loading without filter
                    console.log(`Stored ${allCounties.length} counties in allCounties`);
                }
                
                // Check if element exists
                if ($countySelect.length === 0) {
                    console.error('County select element not found!');
                    return;
                }
                
                // If Select2 is initialized, destroy it first
                if (countySelect2Initialized && $countySelect.hasClass('select2-hidden-accessible')) {
                    console.log('Destroying existing Select2 instance');
                    $countySelect.select2('destroy');
                    countySelect2Initialized = false;
                }
                
                // Clear and populate options
                $countySelect.empty();
                if (counties.length === 0) {
                    console.warn('No counties returned from server');
                    $countySelect.append(new Option('No counties available', '', true, true));
                } else {
                    console.log(`Adding ${counties.length} counties to dropdown`);
                    counties.forEach((county, index) => {
                        if (county) {
                            // Handle both old format (strings) and new format (objects with FIPS codes)
                            if (typeof county === 'string') {
                                // Old format: just county name string
                                $countySelect.append(new Option(county, county));
                            } else if (county && county.name) {
                                // New format: county object with name, geoid5, state_fips, county_fips
                                const option = new Option(county.name, county.name);
                                $(option).data('county-data', county); // Store full county object
                                $countySelect.append(option);
                            }
                        }
                    });
                    console.log(`Successfully added ${counties.length} county options`);
                }
                
                // Re-select previously selected counties if they're still in the filtered list
                // Extract county names for comparison
                const availableCounties = counties.map(c => typeof c === 'string' ? c : (c && c.name ? c.name : c));
                const validSelections = selectedCounties.filter(c => availableCounties.includes(c));
                if (validSelections.length > 0) {
                    $countySelect.val(validSelections);
                }
                
                // Initialize or reinitialize Select2
                console.log('Initializing Select2 for counties');
                $countySelect.select2({
                    placeholder: "Select up to 3 counties...",
                    allowClear: true,
                    width: '100%',
                    dropdownAutoWidth: false,
                    minimumResultsForSearch: 0, // Always show search box
                    maximumSelectionLength: 3, // Limit to 3 counties
                    matcher: function(params, data) {
                        // If there is no search term, return all data
                        if ($.trim(params.term) === '') {
                            return data;
                        }
                        // Use the default matcher to get matches
                        if (typeof $.fn.select2.defaults.defaults.matcher === 'function') {
                            return $.fn.select2.defaults.defaults.matcher(params, data);
                        }
                        // Fallback matcher
                        if (data.text && params.term) {
                            return data.text.toUpperCase().indexOf(params.term.toUpperCase()) >= 0 ? data : null;
                        }
                        return data;
                    }
                });
                countySelect2Initialized = true;
                console.log('Select2 initialized for counties');
                
                // Verify options are in the DOM
                const optionCount = $countySelect.find('option').length;
                console.log(`County dropdown now has ${optionCount} options`);
                
                // Trigger change if we have valid selections
                if (validSelections.length > 0) {
                    $countySelect.val(validSelections).trigger('change');
                }
                
                // Ensure Select2 search input has proper attributes
                $countySelect.on('select2:open', function() {
                    setTimeout(function() {
                        const searchInput = $('.select2-container--open .select2-search__field');
                        if (searchInput.length) {
                            if (!searchInput.attr('id')) {
                                searchInput.attr('id', 'county-select-search');
                            }
                            if (!searchInput.attr('name')) {
                                searchInput.attr('name', 'county-select-search');
                            }
                        }
                    }, 50);
                });
            })
            .catch(error => {
                console.error('Error loading counties:', error);
                console.error('Error details:', error.message, error.stack);
                
                // Try to load fallback or retry
                const $countySelect = $('#county-select');
                if ($countySelect.length) {
                    // Try one more time after a delay
                    setTimeout(function() {
                        console.log('Retrying county load...');
                        loadCounties(stateCode);
                    }, 1000);
                }
            });
    }
    
    // Populate state filter dropdown and county dropdown
    if ($('#county-select').length) {
        // First, populate state filter dropdown
        fetch('/states')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(states => {
                console.log(`Loading ${states.length} states into dropdown`);
                
                // Validate response format
                if (!Array.isArray(states)) {
                    console.error('Invalid states response format:', states);
                    throw new Error('Invalid response format from server');
                }
                
                const $stateFilter = $('#state-filter-select');
                if ($stateFilter.length === 0) {
                    console.error('State filter dropdown not found!');
                    return;
                }
                
                // Clear existing options
                $stateFilter.empty();
                $stateFilter.append(new Option('All States', ''));
                
                // Add all states
                states.forEach(state => {
                    if (state && state.name && state.code) {
                        $stateFilter.append(new Option(state.name, state.code));
                    } else {
                        console.warn('Invalid state object:', state);
                    }
                });
                
                console.log(`Added ${states.length} states to dropdown`);
                
                // Initialize or reinitialize Select2
                if ($stateFilter.hasClass('select2-hidden-accessible')) {
                    $stateFilter.select2('destroy');
                }
                
                $stateFilter.select2({
                    placeholder: "Select a state to filter counties...",
                    allowClear: true
                });
                
                // When state filter changes, reload counties
                $stateFilter.on('change', function() {
                    const stateCode = $(this).val();
                    console.log('State filter changed to:', stateCode);
                    loadCounties(stateCode || null);
                });
                
                // Ensure Select2 search input has proper attributes for state filter
                $stateFilter.on('select2:open', function() {
                    setTimeout(function() {
                        const searchInput = $('.select2-container--open .select2-search__field');
                        if (searchInput.length) {
                            if (!searchInput.attr('id')) {
                                searchInput.attr('id', 'state-filter-select-search');
                            }
                            if (!searchInput.attr('name')) {
                                searchInput.attr('name', 'state-filter-select-search');
                            }
                        }
                    }, 50);
                });
            })
            .catch(error => {
                console.error('Error loading states for filter:', error);
                // Show error in dropdown
                const $stateFilter = $('#state-filter-select');
                if ($stateFilter.length) {
                    $stateFilter.empty();
                    $stateFilter.append(new Option('Error loading states. Please refresh.', '', true, true));
                    if ($stateFilter.hasClass('select2-hidden-accessible')) {
                        $stateFilter.select2('destroy');
                    }
                    $stateFilter.select2({
                        placeholder: "Error loading states...",
                        allowClear: true
                    });
                }
            });
        
        // Load all counties initially - use a small delay to ensure DOM is ready
        setTimeout(function() {
            console.log('Loading counties on page load...');
            loadCounties();
        }, 100);
    } else {
        // County select is optional - some apps (like MergerMeter) don't use it
        // Only log if we're in debug mode
        if (window.DEBUG_MODE) {
            console.warn('County select element not found in DOM (this is OK if not using county selection)');
        }
    }
    
    // Populate state dropdown
    if ($('#state-filter-select').length) {
        fetch('/states')
            .then(response => response.json())
            .then(states => {
                const $stateSelect = $('#state-filter-select');
                $stateSelect.empty();
                $stateSelect.append(new Option('Select a state...', ''));
                states.forEach(state => {
                    $stateSelect.append(new Option(state.name, state.code));
                });
                $stateSelect.select2({
                    placeholder: "Select a state...",
                    allowClear: true
                });
                // Ensure Select2 search input has proper attributes
                $stateSelect.on('select2:open', function() {
                    setTimeout(function() {
                        const searchInput = $('.select2-container--open .select2-search__field');
                        if (searchInput.length) {
                            if (!searchInput.attr('id')) {
                                searchInput.attr('id', 'state-select-search');
                            }
                            if (!searchInput.attr('name')) {
                                searchInput.attr('name', 'state-select-search');
                            }
                        }
                    }, 50);
                });
            })
            .catch(error => {
                console.error('Error loading states:', error);
            });
    }
    
});

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter to submit form
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (!submitBtn.disabled) {
            analysisForm.dispatchEvent(new Event('submit'));
        }
    }
    
    // Escape to reset form
    if (e.key === 'Escape') {
        resetForm();
    }
});

// Add tooltips for help text
document.querySelectorAll('.help-text').forEach(helpText => {
    helpText.style.cursor = 'help';
    helpText.title = helpText.textContent;
});

// Initialize tooltips for sidebar feature cards with white backgrounds
function initializeSidebarTooltips() {
    const featureCards = document.querySelectorAll('.sidebar .feature-card[data-tooltip]');
    
    featureCards.forEach((card, index) => {
        const tooltipText = card.getAttribute('data-tooltip');
        if (!tooltipText) return;
        
        // Create tooltip element
        let tooltip = card.querySelector('.custom-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.className = 'custom-tooltip';
            tooltip.innerHTML = tooltipText;
            // Append to body to avoid overflow issues
            document.body.appendChild(tooltip);
        }
        
        // Show tooltip on hover
        card.addEventListener('mouseenter', function() {
            const cardRect = card.getBoundingClientRect();
            
            // Show tooltip first to measure it
            tooltip.style.cssText = 'display: block !important; visibility: hidden !important; opacity: 0 !important; position: fixed !important;';
            
            // Calculate position after tooltip is rendered
            requestAnimationFrame(() => {
                const tooltipRect = tooltip.getBoundingClientRect();
                const tooltipWidth = tooltipRect.width || 300;
                const tooltipHeight = tooltipRect.height || 100;
                
                // Position to the left of the sidebar card
                // Always position to the left, never to the right
                let left = cardRect.left - tooltipWidth - 15;
                let top = cardRect.top + (cardRect.height / 2) - (tooltipHeight / 2);
                
                // If tooltip would go off screen to the left, adjust position
                if (left < 10) {
                    // Position it at the left edge of the screen with some padding
                    left = 10;
                }
                if (top < 10) {
                    top = 10;
                }
                if (top + tooltipHeight > window.innerHeight - 10) {
                    top = window.innerHeight - tooltipHeight - 10;
                }
                
                // Apply all styles with white background
                tooltip.style.cssText = `
                    display: block !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                    position: fixed !important;
                    left: ${left}px !important;
                    top: ${top}px !important;
                    z-index: 99999 !important;
                    background: white !important;
                    color: #333 !important;
                    padding: 12px 16px !important;
                    border-radius: 8px !important;
                    font-size: 0.9rem !important;
                    line-height: 1.5 !important;
                    white-space: normal !important;
                    max-width: 350px !important;
                    min-width: 250px !important;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
                    pointer-events: auto !important;
                    text-align: left !important;
                    word-wrap: break-word !important;
                    margin: 0 !important;
                    border: 1px solid #ddd !important;
                    overflow: visible !important;
                `;
            });
        });
        
        // Hide tooltip on mouse leave
        card.addEventListener('mouseleave', function() {
            tooltip.style.cssText = 'display: none !important; visibility: hidden !important; opacity: 0 !important;';
        });
        
        // Keep tooltip visible when hovering over it
        tooltip.addEventListener('mouseenter', function() {
            tooltip.style.opacity = '1';
            tooltip.style.visibility = 'visible';
        });
        
        tooltip.addEventListener('mouseleave', function() {
            tooltip.style.cssText = 'display: none !important; visibility: hidden !important; opacity: 0 !important;';
        });
    });
}

// Add success animation for form submission
function addSuccessAnimation() {
    const form = document.querySelector('.analysis-form');
    form.style.transform = 'scale(0.98)';
    form.style.transition = 'transform 0.2s ease';
    
    setTimeout(() => {
        form.style.transform = 'scale(1)';
    }, 200);
}

// Add error shake animation
function addErrorShake() {
    const form = document.querySelector('.analysis-form');
    form.style.animation = 'shake 0.5s ease-in-out';
    
    setTimeout(() => {
        form.style.animation = '';
    }, 500);
}

// Add CSS for shake animation
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
`;
document.head.appendChild(style);

// Progress steps configuration
// Can be overridden by app-specific templates
const PROGRESS_STEPS = window.PROGRESS_STEPS || [
    { id: 'initializing', label: 'Initializing analysis', icon: 'fa-cog' },
    { id: 'parsing_params', label: 'Parsing parameters', icon: 'fa-check-circle' },
    { id: 'preparing_data', label: 'Preparing data', icon: 'fa-database' },
    { id: 'connecting_db', label: 'Connecting to database', icon: 'fa-plug' },
    { id: 'fetching_data', label: 'Fetching data', icon: 'fa-download' },
    { id: 'processing_data', label: 'Processing data', icon: 'fa-cogs' },
    { id: 'generating_ai', label: 'Generating AI insights', icon: 'fa-brain' },
    { id: 'completed', label: 'Analysis complete', icon: 'fa-check' }
];

// Initialize progress steps display
function initializeProgressSteps() {
    const stepsContainer = document.getElementById('progressSteps');
    if (!stepsContainer) return;
    
    stepsContainer.innerHTML = PROGRESS_STEPS.map((step, index) => `
        <div class="progress-step pending" id="step-${step.id}">
            <i class="fas ${step.icon}"></i>
            <span>${index + 1}. ${step.label}</span>
        </div>
    `).join('');
}

// Update progress step
function updateProgressStep(stepId, status = 'active') {
    const stepElement = document.getElementById(`step-${stepId}`);
    if (!stepElement) return;
    
    // Remove all status classes
    stepElement.classList.remove('pending', 'active', 'completed');
    
    // Add new status
    stepElement.classList.add(status);
    
    // Update icon based on status
    const iconElement = stepElement.querySelector('i');
    if (iconElement) {
        if (status === 'completed') {
            iconElement.className = 'fas fa-check-circle'; // Green checkmark
        } else if (status === 'active') {
            // Keep original icon from PROGRESS_STEPS
            const stepConfig = PROGRESS_STEPS.find(s => s.id === stepId);
            if (stepConfig) {
                iconElement.className = `fas ${stepConfig.icon}`;
            }
        }
    }
    
    // If completing a step, mark previous steps as completed
    if (status === 'completed' || status === 'active') {
        const currentIndex = PROGRESS_STEPS.findIndex(s => s.id === stepId);
        for (let i = 0; i < currentIndex; i++) {
            const prevStep = document.getElementById(`step-${PROGRESS_STEPS[i].id}`);
            if (prevStep && !prevStep.classList.contains('completed')) {
                prevStep.classList.remove('pending', 'active');
                prevStep.classList.add('completed');
                // Update icon for previous steps too
                const prevIcon = prevStep.querySelector('i');
                if (prevIcon) {
                    prevIcon.className = 'fas fa-check-circle';
                }
            }
        }
    }
}

// Map progress step names to step IDs
function mapStepToId(stepName) {
    const stepMap = {
        'initializing': 'initializing',
        'preparing_data': 'preparing_data',
        'connecting_db': 'connecting_db',
        'fetching_data': 'fetching_data',
        'building_report': 'building_report',
        'section_1': 'section_1',
        'section_2': 'section_2',
        'section_3': 'section_3',
        'section_4': 'section_4',
        'generating_ai': 'generating_ai',
        'completed': 'completed'
    };
    
    // Try exact match first
    if (stepMap[stepName]) return stepMap[stepName];
    
    // Try partial matches
    if (stepName.includes('initializ')) return 'initializing';
    if (stepName.includes('preparing') || stepName.includes('matching') || stepName.includes('parsing')) return 'preparing_data';
    if (stepName.includes('connect') || stepName.includes('database')) return 'connecting_db';
    if (stepName.includes('fetch') || stepName.includes('query') || stepName.includes('benchmark')) return 'fetching_data';
    if (stepName.includes('build') && (stepName.includes('report') || stepName.includes('section'))) return 'building_report';
    // BizSight specific sections
    if (stepName.includes('section 1') || stepName.includes('geographic') || stepName.includes('map')) return 'section_1';
    if (stepName.includes('section 2') || stepName.includes('county summary')) return 'section_2';
    if (stepName.includes('section 3') || stepName.includes('comparison')) return 'section_3';
    if (stepName.includes('section 4') || stepName.includes('top lenders')) return 'section_4';
    // BranchSight specific sections
    if (stepName.includes('yearly breakdown') || stepName.includes('yearly') && stepName.includes('breakdown')) return 'yearly_breakdown';
    if (stepName.includes('bank networks') || (stepName.includes('bank') && stepName.includes('network'))) return 'bank_networks';
    if (stepName.includes('county analysis') || (stepName.includes('county') && stepName.includes('analysis'))) return 'county_analysis';
    if (stepName.includes('ai') || stepName.includes('generating') || stepName.includes('insight')) return 'generating_ai';
    if (stepName.includes('complete') || stepName.includes('done') || stepName.includes('finaliz')) return 'completed';
    
    return null;
}

// Real-time progress bar using SSE
function listenForProgress(jobId) {
    console.log(`[DEBUG] Starting progress listener for job: ${jobId}`);
    const evtSource = new EventSource(`/progress/${jobId}`);
    let currentStepId = null;
    let isCompleted = false; // Track if we've received a completion message
    
    // Random fun messages to intersperse with progress updates
    const funMessages = [
        "Doing something cool.",
        "Russell hates this.",
        "Data drives the movement for economic justice.",
        "Support the CFPB.",
        "Fight. Fight. Fight.",
        "Data geeks to the front.",
        "This is awesome, isn't it?"
    ];
    
    // Randomly select 1-2 messages for this report run
    const numMessages = Math.random() < 0.5 ? 1 : 2; // 50% chance of 1, 50% chance of 2
    const selectedMessages = [];
    const availableMessages = [...funMessages]; // Copy array to avoid modifying original
    
    for (let i = 0; i < numMessages && availableMessages.length > 0; i++) {
        const randomIndex = Math.floor(Math.random() * availableMessages.length);
        selectedMessages.push(availableMessages.splice(randomIndex, 1)[0]);
    }
    
    let messageIndex = 0; // Track which fun message to show next
    let updateCount = 0; // Track number of progress updates received
    
    evtSource.onopen = function(event) {
        console.log('[DEBUG] SSE connection opened');
    };
    
    evtSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('[DEBUG] Progress update received:', data);
        
        document.getElementById('progressFill').style.width = data.percent + '%';
        // Update progress text - show the current step/section being processed
        const progressTextEl = document.getElementById('progressText');
        if (progressTextEl) {
            updateCount++;
            
            // Randomly show fun messages 10-15% of the time (but not on first update or last update)
            const shouldShowFunMessage = selectedMessages.length > 0 && 
                                        updateCount > 2 && 
                                        !data.done && 
                                        !data.error &&
                                        Math.random() < 0.12; // 12% chance
            
            if (shouldShowFunMessage) {
                // Show a fun message instead of the actual progress
                progressTextEl.textContent = selectedMessages[messageIndex % selectedMessages.length];
                messageIndex++;
                
                // After showing fun message, restore actual progress after a short delay
                setTimeout(() => {
                    if (progressTextEl && !data.done && !data.error) {
                        // Restore the actual progress message
                        progressTextEl.textContent = data.step;
                    }
                }, 2000); // Show fun message for 2 seconds
            } else {
                // Show normal progress message
                progressTextEl.textContent = data.step;
            }
        }
        
        // Update progress steps
        const stepId = mapStepToId(data.step.toLowerCase());
        if (stepId && stepId !== currentStepId) {
            console.log(`[DEBUG] Progress step changed: ${currentStepId} -> ${stepId}`);
            if (currentStepId) {
                updateProgressStep(currentStepId, 'completed');
            }
            updateProgressStep(stepId, 'active');
            currentStepId = stepId;
        }
        
        if (data.done || data.error) {
            console.log(`[DEBUG] Progress complete. done: ${data.done}, error: ${data.error}`);
            isCompleted = true; // Mark as completed before closing
            evtSource.close();
            if (currentStepId) {
                updateProgressStep(currentStepId, 'completed');
            }
            if (data.error) {
                showError(data.error);
            } else {
                updateProgressStep('completed', 'completed');
                if (progressTextEl) {
                    progressTextEl.textContent = 'Analysis complete!';
                }
                showResults(jobId);
            }
            hideProgress();
            enableForm();
        }
    };
    
    evtSource.onerror = function(event) {
        // Ignore errors if we've already completed successfully
        // The connection may close normally after completion, triggering onerror
        if (isCompleted) {
            console.log('[DEBUG] SSE connection closed after completion (normal)');
            return;
        }
        
        // Only show error if we haven't completed yet
        console.error('[ERROR] SSE error:', event);
        console.error('[ERROR] SSE readyState:', evtSource.readyState);
        evtSource.close();
        showError('Connection lost. Please refresh and try again.');
        hideProgress();
        enableForm();
    };
}

