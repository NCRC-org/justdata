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
        console.warn('Analysis form not found');
        return;
    }
    
    analysisForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(analysisForm);
    const startYear = formData.get('startYear');
    const endYear = formData.get('endYear');
    
    // Enhanced validation with helpful messages
    let hasErrors = false;
    
    // Year range is now automatic (last 5 years) - no validation needed
    // Years will be automatically determined by the backend
    
    // State selection is optional
    const selectedState = $('#state-filter-select').val();
    
    // Validate county selection (single or multiple based on select type)
    const countySelectEl = document.getElementById('county-select');
    const isMultiple = countySelectEl && countySelectEl.hasAttribute('multiple');
    
    if (isMultiple) {
        // Multi-select validation (for MergerMeter)
        const selectedCounties = $('#county-select').val();
        if (!selectedCounties || selectedCounties.length === 0) {
            showValidationMessage(countySelectEl, 'Please select at least one county to analyze.', 'error');
            hasErrors = true;
        } else if (selectedCounties.length > 3) {
            showValidationMessage(countySelectEl, `Please select no more than 3 counties to analyze. You selected ${selectedCounties.length} counties.`, 'error');
            hasErrors = true;
        }
    } else {
        // Single-select validation (for LendSight, BizSight, BranchSeeker)
        const selectedCounty = countySelectEl ? countySelectEl.value : '';
        if (!selectedCounty || selectedCounty === '') {
            showValidationMessage(countySelectEl, 'Please select a county to analyze.', 'error');
            hasErrors = true;
        }
    }
    
    if (hasErrors) {
        // Scroll to first error
        const firstError = document.querySelector('.validation-message.error');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
    }
    
    // Years are now automatically determined (last 5 years) - no need to parse
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
    
    // Build request data (handle both single and multi-select)
    // Reuse countySelectEl and isMultiple from above (lines 67-68) - don't redeclare
    
    let selectedCountiesList = [];
    if (isMultiple) {
        // Multi-select: get array from jQuery
        selectedCountiesList = $('#county-select').val() || [];
    } else {
        // Single-select: get single value from DOM
        const selectedCounty = countySelectEl ? countySelectEl.value : '';
        if (selectedCounty) {
            selectedCountiesList = [selectedCounty];
        }
    }
    
    // Extract county data (with FIPS codes) if available, otherwise use county names
    const countiesData = selectedCountiesList.map(countyName => {
        // Try to get the full county object from the option's data attribute
        let countyData = null;
        if (isMultiple) {
            const option = $('#county-select option').filter(function() {
                return $(this).val() === countyName;
            }).first();
            countyData = option.data('county-data');
        } else {
            // Single-select: get from dataset attribute
            const option = countySelectEl.options[countySelectEl.selectedIndex];
            if (option && option.dataset.county) {
                try {
                    countyData = JSON.parse(option.dataset.county);
                } catch (e) {
                    // Ignore parse errors
                }
            }
        }
        
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
        // years: omitted - will be automatically determined by backend (last 5 years)
        counties: selectedCountiesList.join(';'), // Keep for backward compatibility
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
        
        const baseUrl = window.APP_BASE_URL || '';
        const analyzeUrl = `${baseUrl}/analyze`;
        console.log(`[DEBUG] Fetching from: ${analyzeUrl}`);
        
        const response = await fetch(analyzeUrl, {
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
            const baseUrl = window.APP_BASE_URL || '';
            window.location.href = `${baseUrl}/report`;
        });
    }
}

// Download button handler
function setupDownloadHandler() {
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            const baseUrl = window.APP_BASE_URL || '';
            window.location.href = `${baseUrl}/download`;
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
        const baseUrl = window.APP_BASE_URL || '';
        console.log('[DEBUG] showResults - APP_BASE_URL:', window.APP_BASE_URL);
        console.log('[DEBUG] showResults - baseUrl:', baseUrl);
        console.log('[DEBUG] showResults - jobId:', jobId);
        const url = jobId ? `${baseUrl}/report?job_id=${jobId}` : `${baseUrl}/report`;
        console.log('[DEBUG] showResults - redirecting to:', url);
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
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-magic"></i><span>Generate Analysis</span>';
    
    // Enable inputs and selects
    const inputs = analysisForm.querySelectorAll('input, select');
    inputs.forEach(input => input.disabled = false);
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
        const countySelectEl = document.getElementById('county-select');
        const isMultiple = countySelectEl && countySelectEl.hasAttribute('multiple');
        
        if (isMultiple) {
            // Multi-select validation (for MergerMeter)
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
        } else {
            // Single-select validation (for LendSight, BizSight, BranchSeeker)
            const selectedCounty = countySelectEl ? countySelectEl.value : '';
            if (!selectedCounty || selectedCounty === '') {
                isValid = false;
                message = 'Please select a county to analyze.';
                input.setCustomValidity('Please select a county.');
            } else {
                isValid = true;
                message = 'County selected successfully.';
                messageType = 'success';
                input.setCustomValidity('');
            }
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
                    } else if (yearRange < 3) {
                        isValid = false;
                        message = `You've selected ${yearRange} ${yearRange === 1 ? 'year' : 'years'}. Please select at least 3 years for meaningful analysis.`;
                        input.setCustomValidity('Please select a range of at least 3 years.');
                    } else {
                        isValid = true;
                        message = `Good! You've selected ${yearRange} years (${start}-${end}).`;
                        messageType = 'success';
                        input.setCustomValidity('');
                    }
                } else {
                    isValid = true;
                    input.setCustomValidity('');
                }
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

// Initialize onboarding tour
function initializeTour() {
    // Check if user has seen the tour before
    const hasSeenTour = localStorage.getItem('branchseeker_tour_completed');
    const startTourBtn = document.getElementById('startTourBtn');
    
    if (!startTourBtn) return;
    
    // Start tour button click handler
    startTourBtn.addEventListener('click', function() {
        startTour();
    });
    
    // Auto-start tour for first-time visitors - DISABLED
    // if (!hasSeenTour) {
    //     // Wait a bit for page to load, then show tour
    //     setTimeout(() => {
    //         const shouldStart = confirm('Welcome to BranchSeeker! Would you like to take a quick tour to learn how to use the tool?');
    //         if (shouldStart) {
    //             startTour();
    //         } else {
    //             localStorage.setItem('branchseeker_tour_completed', 'true');
    //         }
    //     }, 1000);
    // }
}

// Start the onboarding tour
function startTour() {
    if (typeof introJs === 'undefined') {
        console.error('Intro.js not loaded');
        return;
    }
    
    introJs().setOptions({
        nextLabel: 'Next →',
        prevLabel: '← Back',
        skipLabel: 'Skip Tour',
        doneLabel: 'Got it!',
        showProgress: true,
        showBullets: true,
        exitOnOverlayClick: false,
        exitOnEsc: true,
        tooltipClass: 'customTooltip',
        highlightClass: 'customHighlight',
        buttonClass: 'introjs-button',
        scrollToElement: true,
        scrollPadding: 100,
        disableInteraction: false
    }).onchange(function(targetElement) {
        // Simple, one-time move of skip button after each step change
        setTimeout(function() {
            var skipButton = document.querySelector('.introjs-skipbutton');
            var buttonContainer = document.querySelector('.introjs-tooltipbuttons');
            var nextButton = document.querySelector('.introjs-nextbutton');
            if (skipButton && buttonContainer && nextButton && skipButton.parentNode !== buttonContainer) {
                buttonContainer.insertBefore(skipButton, nextButton);
            }
        }, 100);
    }).oncomplete(function() {
        localStorage.setItem('branchseeker_tour_completed', 'true');
    }).onexit(function() {
        // Don't mark as completed if they exit early
    }).start();
    
    // Also try once after tour starts
    setTimeout(function() {
        var skipButton = document.querySelector('.introjs-skipbutton');
        var buttonContainer = document.querySelector('.introjs-tooltipbuttons');
        var nextButton = document.querySelector('.introjs-nextbutton');
        if (skipButton && buttonContainer && nextButton && skipButton.parentNode !== buttonContainer) {
            buttonContainer.insertBefore(skipButton, nextButton);
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
    
    // Initialize tour
    initializeTour();
    
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
    const stateSelect = $('#state-select');
    if (stateSelect.length) {
        stateSelect.on('change', function() {
            if (!this.value) {
                showValidationMessage(this, 'Please select a state to analyze.', 'error');
            } else {
                hideValidationMessage(this);
            }
        });
    }
    
    // Initialize onboarding tour
    initializeTour();
    
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
    
    // Function to detect if county select is single-select or multi-select
    function isCountySelectMultiple() {
        const countySelect = document.getElementById('county-select');
        if (!countySelect) return false;
        // Check if element has multiple attribute
        return countySelect.hasAttribute('multiple');
    }
    
    // Function to load and populate counties
    function loadCounties(stateCode = null) {
        const $countySelect = $('#county-select');
        const countySelectEl = document.getElementById('county-select');
        
        if (!$countySelect.length || !countySelectEl) {
            console.error('County select element not found!');
            return;
        }
        
        // Detect if this is a single-select or multi-select
        const isMultiple = isCountySelectMultiple();
        const selectedCounties = isMultiple ? ($countySelect.val() || []) : ($countySelect.val() ? [$countySelect.val()] : []);
        
        const baseUrl = window.APP_BASE_URL || '';
        let url = `${baseUrl}/counties`;
        if (stateCode) {
            url = `${baseUrl}/counties-by-state/${stateCode}`;
        }
        
        console.log(`Fetching counties from: ${url} (${isMultiple ? 'multi-select' : 'single-select'})`);
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
                
                // If Select2 is initialized, destroy it first
                if (countySelect2Initialized && $countySelect.hasClass('select2-hidden-accessible')) {
                    console.log('Destroying existing Select2 instance');
                    $countySelect.select2('destroy');
                    countySelect2Initialized = false;
                }
                
                // Clear and populate options using plain DOM (no Select2 for single-select)
                if (isMultiple) {
                    // Multi-select: Use Select2
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
                    const availableCounties = counties.map(c => typeof c === 'string' ? c : (c && c.name ? c.name : c));
                    const validSelections = selectedCounties.filter(c => availableCounties.includes(c));
                    if (validSelections.length > 0) {
                        $countySelect.val(validSelections);
                    }
                    
                    // Initialize Select2 for multi-select
                    console.log('Initializing Select2 for counties (multi-select)');
                    $countySelect.select2({
                        placeholder: "Select up to 3 counties...",
                        allowClear: true,
                        width: '100%',
                        dropdownAutoWidth: false,
                        minimumResultsForSearch: 0, // Always show search box
                        maximumSelectionLength: 3, // Limit to 3 counties
                        language: {
                            noResults: function() {
                                return "No counties found";
                            },
                            searching: function() {
                                return "Searching...";
                            },
                            maximumSelected: function(e) {
                                return "You can only select " + e.maximum + " counties";
                            }
                        },
                        matcher: function(params, data) {
                            // If no search term, show all results
                            if ($.trim(params.term) === '') {
                                return data;
                            }
                            // Case-insensitive search
                            if (data.text && params.term) {
                                const searchTerm = params.term.toUpperCase();
                                const dataText = data.text.toUpperCase();
                                // Match if county name contains search term
                                if (dataText.indexOf(searchTerm) >= 0) {
                                    return data;
                                }
                            }
                            return null;
                        }
                    });
                    countySelect2Initialized = true;
                    console.log('Select2 initialized for counties');
                    
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
                } else {
                    // Single-select: Use Select2 for better search functionality
                    countySelectEl.innerHTML = '<option value="">Select a county</option>';
                    counties.forEach(county => {
                        const option = document.createElement('option');
                        if (typeof county === 'string') {
                            option.value = county;
                            option.textContent = county;
                        } else if (county && county.name) {
                            option.value = county.name;
                            option.textContent = county.name;
                            option.dataset.county = JSON.stringify(county);
                        }
                        countySelectEl.appendChild(option);
                    });
                    console.log(`Successfully added ${counties.length} county options (single-select)`);
                    
                    // Re-select previously selected county if it's still in the list
                    if (selectedCounties.length > 0) {
                        const selectedCounty = selectedCounties[0];
                        const availableCounties = counties.map(c => typeof c === 'string' ? c : (c && c.name ? c.name : c));
                        if (availableCounties.includes(selectedCounty)) {
                            countySelectEl.value = selectedCounty;
                        }
                    }
                    
                    // Initialize Select2 for single-select with search
                    if ($countySelect.hasClass('select2-hidden-accessible')) {
                        $countySelect.select2('destroy');
                    }
                    $countySelect.select2({
                        placeholder: "Select a county",
                        allowClear: true,
                        width: '100%',
                        minimumResultsForSearch: 0, // Always show search box
                        language: {
                            noResults: function() {
                                return "No counties found";
                            },
                            searching: function() {
                                return "Searching...";
                            }
                        },
                        matcher: function(params, data) {
                            // If no search term, show all results
                            if ($.trim(params.term) === '') {
                                return data;
                            }
                            // Case-insensitive search
                            if (data.text && params.term) {
                                const searchTerm = params.term.toUpperCase();
                                const dataText = data.text.toUpperCase();
                                // Match if county name contains search term
                                if (dataText.indexOf(searchTerm) >= 0) {
                                    return data;
                                }
                            }
                            return null;
                        }
                    });
                    countySelect2Initialized = true;
                    console.log('Select2 initialized for counties (single-select)');
                    
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
                }
                
                // Verify options are in the DOM
                const optionCount = countySelectEl.options.length;
                console.log(`County dropdown now has ${optionCount} options`);
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
    // Skip this for LendSight - it has its own state management
    if ($('#county-select').length && !window.LENDSIGHT_MODE) {
        // First, populate state filter dropdown
        const baseUrl = window.APP_BASE_URL || '';
        // BizSight uses /api/states, others use /states
        const statesEndpoint = baseUrl.includes('bizsight') ? `${baseUrl}/api/states` : `${baseUrl}/states`;
        
        // Show loading spinner
        const stateLoadingSpinner = $('#state-loading-spinner');
        const $stateFilter = $('#state-filter-select');
        if (stateLoadingSpinner.length) {
            stateLoadingSpinner.show();
        }
        
        fetch(statesEndpoint)
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
                
                if ($stateFilter.length === 0) {
                    console.error('State filter dropdown not found!');
                    return;
                }
                
                // Hide loading spinner
                if (stateLoadingSpinner.length) {
                    stateLoadingSpinner.hide();
                }
                
                // Clear existing options and enable dropdown
                $stateFilter.empty();
                $stateFilter.prop('disabled', false);
                $stateFilter.append(new Option('Select a state', ''));
                
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
                    placeholder: "Select a state",
                    allowClear: true,
                    width: '100%',
                    minimumResultsForSearch: 0, // Always show search box
                    language: {
                        noResults: function() {
                            return "No states found";
                        },
                        searching: function() {
                            return "Searching...";
                        }
                    },
                    matcher: function(params, data) {
                        // If no search term, show all results
                        if ($.trim(params.term) === '') {
                            return data;
                        }
                        // Case-insensitive search
                        if (data.text && params.term) {
                            const searchTerm = params.term.toUpperCase();
                            const dataText = data.text.toUpperCase();
                            // Match if state name contains search term
                            if (dataText.indexOf(searchTerm) >= 0) {
                                return data;
                            }
                            // Also check state code if available
                            if (data.id && data.id.toUpperCase().indexOf(searchTerm) >= 0) {
                                return data;
                            }
                        }
                        return null;
                    }
                });
                
                // When state filter changes, show/hide county dropdown and reload counties
                $stateFilter.on('change', function() {
                    const stateCode = $(this).val();
                    console.log('State filter changed to:', stateCode);
                    const countyWrapper = $('#county-selection-wrapper');
                    
                    if (stateCode) {
                        // Show county dropdown and load counties for selected state
                        countyWrapper.slideDown(200);
                        loadCounties(stateCode);
                    } else {
                        // Hide county dropdown and clear selection
                        countyWrapper.slideUp(200);
                        const $countySelect = $('#county-select');
                        if ($countySelect.hasClass('select2-hidden-accessible')) {
                            $countySelect.val(null).trigger('change');
                            $countySelect.select2('destroy');
                        } else {
                            $countySelect.val('');
                        }
                    }
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
                // Hide loading spinner
                const stateLoadingSpinner = $('#state-loading-spinner');
                if (stateLoadingSpinner.length) {
                    stateLoadingSpinner.hide();
                }
                // Show error in dropdown
                const $stateFilter = $('#state-filter-select');
                if ($stateFilter.length) {
                    $stateFilter.empty();
                    $stateFilter.prop('disabled', false);
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
        
        // Don't load counties initially - wait for state selection
        // Skip this for LendSight - it has its own state/county management
        if (!window.LENDSIGHT_MODE) {
            console.log('Waiting for state selection before loading counties...');
            // Hide county wrapper initially
            $('#county-selection-wrapper').hide();
        } else {
            console.log('Skipping automatic county load for LendSight');
        }
    } else {
        // County select is optional - some apps (like MergerMeter) don't use it
        // Only log if we're in debug mode
        if (window.DEBUG_MODE) {
            console.warn('County select element not found in DOM (this is OK if not using county selection)');
        }
    }
    
    // Populate state dropdown
    if ($('#state-select').length) {
        const baseUrl = window.APP_BASE_URL || '';
        // BizSight uses /api/states, others use /states
        const statesEndpoint = baseUrl.includes('bizsight') ? `${baseUrl}/api/states` : `${baseUrl}/states`;
        
        const $stateSelect = $('#state-select');
        // Show loading state
        $stateSelect.prop('disabled', true);
        $stateSelect.empty();
        $stateSelect.append(new Option('Loading states...', ''));
        
        fetch(statesEndpoint)
            .then(response => response.json())
            .then(states => {
                $stateSelect.empty();
                $stateSelect.prop('disabled', false);
                $stateSelect.append(new Option('Select a state', ''));
                states.forEach(state => {
                    $stateSelect.append(new Option(state.name, state.code));
                });
                $stateSelect.select2({
                    placeholder: "Select a state",
                    allowClear: true,
                    width: '100%',
                    minimumResultsForSearch: 0, // Always show search box
                    language: {
                        noResults: function() {
                            return "No states found";
                        },
                        searching: function() {
                            return "Searching...";
                        }
                    },
                    matcher: function(params, data) {
                        // If no search term, show all results
                        if ($.trim(params.term) === '') {
                            return data;
                        }
                        // Case-insensitive search
                        if (data.text && params.term) {
                            const searchTerm = params.term.toUpperCase();
                            const dataText = data.text.toUpperCase();
                            // Match if state name contains search term
                            if (dataText.indexOf(searchTerm) >= 0) {
                                return data;
                            }
                            // Also check state code if available
                            if (data.id && data.id.toUpperCase().indexOf(searchTerm) >= 0) {
                                return data;
                            }
                        }
                        return null;
                    }
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
                // Show error in dropdown
                const $stateSelect = $('#state-select');
                if ($stateSelect.length) {
                    $stateSelect.empty();
                    $stateSelect.prop('disabled', false);
                    $stateSelect.append(new Option('Error loading states. Please refresh.', '', true, true));
                }
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
    
    // If completing a step, mark previous steps as completed
    if (status === 'completed' || status === 'active') {
        const currentIndex = PROGRESS_STEPS.findIndex(s => s.id === stepId);
        for (let i = 0; i < currentIndex; i++) {
            const prevStep = document.getElementById(`step-${PROGRESS_STEPS[i].id}`);
            if (prevStep && !prevStep.classList.contains('completed')) {
                prevStep.classList.remove('pending', 'active');
                prevStep.classList.add('completed');
            }
        }
    }
}

// Map progress step names to step IDs
function mapStepToId(stepName) {
    const stepMap = {
        'initializing': 'initializing',
        'parsing_params': 'parsing_params',
        'preparing_data': 'preparing_data',
        'connecting_db': 'connecting_db',
        'fetching_data': 'fetching_data',
        'processing_data': 'processing_data',
        'generating_ai': 'generating_ai',
        'completed': 'completed'
    };
    
    // Try exact match first
    if (stepMap[stepName]) return stepMap[stepName];
    
    // Try partial matches
    if (stepName.includes('initializ')) return 'initializing';
    if (stepName.includes('parsing') || stepName.includes('param')) return 'parsing_params';
    if (stepName.includes('preparing') || stepName.includes('matching')) return 'preparing_data';
    if (stepName.includes('connect') || stepName.includes('database')) return 'connecting_db';
    if (stepName.includes('fetch') || stepName.includes('query')) return 'fetching_data';
    if (stepName.includes('process') || stepName.includes('build')) return 'processing_data';
    if (stepName.includes('ai') || stepName.includes('generating') || stepName.includes('insight')) return 'generating_ai';
    if (stepName.includes('complete') || stepName.includes('done')) return 'completed';
    
    return null;
}

// Real-time progress bar using SSE
function listenForProgress(jobId) {
    console.log(`[DEBUG] Starting progress listener for job: ${jobId}`);
    const baseUrl = window.APP_BASE_URL || '';
    const progressUrl = baseUrl ? `${baseUrl}/progress/${jobId}` : `/progress/${jobId}`;
    const evtSource = new EventSource(progressUrl);
    let currentStepId = null;
    
    evtSource.onopen = function(event) {
        console.log('[DEBUG] SSE connection opened');
    };
    
    evtSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('[DEBUG] Progress update received:', data);
        
        document.getElementById('progressFill').style.width = data.percent + '%';
        document.getElementById('progressText').textContent = data.step;
        
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
            evtSource.close();
            if (currentStepId) {
                updateProgressStep(currentStepId, 'completed');
            }
            if (data.error) {
                showError(data.error);
            } else {
                updateProgressStep('completed', 'completed');
                showResults(jobId);
            }
            hideProgress();
            enableForm();
        }
    };
    
    evtSource.onerror = function(event) {
        console.error('[ERROR] SSE error:', event);
        console.error('[ERROR] SSE readyState:', evtSource.readyState);
        evtSource.close();
        showError('Connection lost. Please refresh and try again.');
        hideProgress();
        enableForm();
    };
}

// Navigation Menu Functionality - DISABLED: Now handled by base_app.html
// The hamburger menu functionality is now standardized in base_app.html template
// to avoid duplicate event handlers and style conflicts. 