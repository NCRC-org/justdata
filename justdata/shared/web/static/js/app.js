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
    const selectionType = formData.get('selection_type') || 'county';
    const startYear = formData.get('startYear');
    const endYear = formData.get('endYear');
    
    // Enhanced validation with helpful messages
    let hasErrors = false;
    
    // Validate year range
    if (!startYear || !endYear) {
        showValidationMessage(document.getElementById('startYear'), 'Please select both start and end years.', 'error');
        if (endYear) showValidationMessage(document.getElementById('endYear'), 'Please select both start and end years.', 'error');
        hasErrors = true;
    } else {
        const start = parseInt(startYear);
        const end = parseInt(endYear);
        const yearRange = end - start + 1;
        
        if (start > end) {
            showValidationMessage(document.getElementById('startYear'), 'Start year must be before or equal to end year.', 'error');
            showValidationMessage(document.getElementById('endYear'), 'End year must be after or equal to start year.', 'error');
            hasErrors = true;
        } else if (yearRange < 3) {
            showValidationMessage(document.getElementById('startYear'), `You've selected ${yearRange} ${yearRange === 1 ? 'year' : 'years'}. Please select at least 3 years for meaningful analysis.`, 'error');
            showValidationMessage(document.getElementById('endYear'), `You've selected ${yearRange} ${yearRange === 1 ? 'year' : 'years'}. Please select at least 3 years for meaningful analysis.`, 'error');
            hasErrors = true;
        }
    }
    
    // Validate selection based on type
    if (selectionType === 'county') {
        const selectedCounties = $('#county-select').val();
        if (!selectedCounties || selectedCounties.length === 0) {
            showValidationMessage(document.getElementById('county-select'), 'Please select at least one county to analyze.', 'error');
            hasErrors = true;
        }
    } else if (selectionType === 'state') {
        const stateCode = formData.get('state_code');
        if (!stateCode) {
            showValidationMessage(document.getElementById('state-select'), 'Please select a state to analyze.', 'error');
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
    
    const start = parseInt(startYear);
    const end = parseInt(endYear);
    
    // Build request data
    let requestData = {
        selection_type: selectionType,
        years: (() => {
            const years = [];
            for (let year = start; year <= end; year++) {
                years.push(year);
            }
            return years.join(',');
        })()
    };
    
    if (selectionType === 'county') {
        const selectedCounties = $('#county-select').val();
        requestData.counties = selectedCounties.join(';');
    } else if (selectionType === 'state') {
        const stateCode = formData.get('state_code');
        requestData.state_code = stateCode;
    }
    
    // Show progress and disable form
    showProgress();
    disableForm();
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        if (!result.success) {
            throw new Error(result.error || 'Analysis failed');
        }
        const jobId = result.job_id;
        listenForProgress(jobId);
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Network error. Please check your connection and try again.');
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
            if (isNaN(year) || year < 2017 || year > 2024) {
                isValid = false;
                message = 'Please select a valid year between 2017-2024.';
                input.setCustomValidity('Please select a valid year between 2017-2024.');
            } else {
                // Check if the range is at least 3 years
                const startYear = document.getElementById('startYear').value;
                const endYear = document.getElementById('endYear').value;
                
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
    
    // Auto-start tour for first-time visitors
    if (!hasSeenTour) {
        // Wait a bit for page to load, then show tour
        setTimeout(() => {
            const shouldStart = confirm('Welcome to BranchSeeker! Would you like to take a quick tour to learn how to use the tool?');
            if (shouldStart) {
                startTour();
            } else {
                localStorage.setItem('branchseeker_tour_completed', 'true');
            }
        }, 1000);
    }
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
    
    // County selection validation
    $('#county-select').on('change', function() {
        validateInput(this, 'county-select');
    });
    
    // Year validation
    document.getElementById('startYear').addEventListener('change', function() {
        validateInput(this, 'startYear');
        // Also validate end year when start year changes
        const endYearInput = document.getElementById('endYear');
        if (endYearInput.value) {
            validateInput(endYearInput, 'endYear');
        }
    });
    
    document.getElementById('endYear').addEventListener('change', function() {
        validateInput(this, 'endYear');
        // Also validate start year when end year changes
        const startYearInput = document.getElementById('startYear');
        if (startYearInput.value) {
            validateInput(startYearInput, 'startYear');
        }
    });
    
    // State selection validation
    $('#state-select').on('change', function() {
        if (!this.value) {
            showValidationMessage(this, 'Please select a state to analyze.', 'error');
        } else {
            hideValidationMessage(this);
        }
    });
    
    // Initialize onboarding tour
    initializeTour();
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

    // Handle selection type radio buttons
    const selectionTypeRadios = document.querySelectorAll('input[name="selection_type"]');
    const countyGroup = document.getElementById('county-selection-group');
    const stateGroup = document.getElementById('state-selection-group');
    
    selectionTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const selectionType = this.value;
            
            // Hide all groups
            countyGroup.style.display = 'none';
            stateGroup.style.display = 'none';
            
            // Show appropriate group
            if (selectionType === 'county') {
                countyGroup.style.display = 'block';
            } else if (selectionType === 'state') {
                stateGroup.style.display = 'block';
            }
        });
    });
    
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
        
        fetch(url)
            .then(response => response.json())
            .then(counties => {
                if (!stateCode) {
                    allCounties = counties; // Store all counties when loading without filter
                }
                
                $countySelect.empty();
                counties.forEach(county => {
                    $countySelect.append(new Option(county, county));
                });
                
                // Re-select previously selected counties if they're still in the filtered list
                const availableCounties = counties.map(c => c);
                const validSelections = selectedCounties.filter(c => availableCounties.includes(c));
                if (validSelections.length > 0) {
                    $countySelect.val(validSelections).trigger('change');
                }
                
                // Initialize Select2 only once
                if (!countySelect2Initialized) {
                    $countySelect.select2({
                        placeholder: "Select counties...",
                        allowClear: true,
                        matcher: function(params, data) {
                            // If there is no search term, return all data
                            if ($.trim(params.term) === '') {
                                return data;
                            }
                            // Use the default matcher to get matches
                            var matches = $.fn.select2.defaults.defaults.matcher(params, data);
                            // If matches is an array, limit to 10
                            if (matches && matches.children && matches.children.length > 10) {
                                matches.children = matches.children.slice(0, 10);
                            }
                            return matches;
                        }
                    });
                    countySelect2Initialized = true;
                    
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
                    // If Select2 is already initialized, just trigger change to refresh
                    $countySelect.trigger('change');
                }
            })
            .catch(error => {
                console.error('Error loading counties:', error);
            });
    }
    
    // Populate state filter dropdown and county dropdown
    if ($('#county-select').length) {
        // First, populate state filter dropdown
        fetch('/states')
            .then(response => response.json())
            .then(states => {
                const $stateFilter = $('#state-filter-select');
                $stateFilter.empty();
                $stateFilter.append(new Option('All States', ''));
                states.forEach(state => {
                    $stateFilter.append(new Option(state.name, state.code));
                });
                $stateFilter.select2({
                    placeholder: "Select a state to filter counties...",
                    allowClear: true
                });
                
                // When state filter changes, reload counties
                $stateFilter.on('change', function() {
                    const stateCode = $(this).val();
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
            });
        
        // Load all counties initially
        loadCounties();
    }
    
    // Populate state dropdown
    if ($('#state-select').length) {
        fetch('/states')
            .then(response => response.json())
            .then(states => {
                const $stateSelect = $('#state-select');
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
const PROGRESS_STEPS = [
    { id: 'initializing', label: 'Initializing analysis', icon: 'fa-cog' },
    { id: 'parsing_params', label: 'Parsing parameters', icon: 'fa-check-circle' },
    { id: 'preparing_data', label: 'Preparing data', icon: 'fa-database' },
    { id: 'connecting_db', label: 'Connecting to database', icon: 'fa-plug' },
    { id: 'fetching_data', label: 'Fetching branch data', icon: 'fa-download' },
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
    const evtSource = new EventSource(`/progress/${jobId}`);
    let currentStepId = null;
    
    evtSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        document.getElementById('progressFill').style.width = data.percent + '%';
        document.getElementById('progressText').textContent = data.step;
        
        // Update progress steps
        const stepId = mapStepToId(data.step.toLowerCase());
        if (stepId && stepId !== currentStepId) {
            if (currentStepId) {
                updateProgressStep(currentStepId, 'completed');
            }
            updateProgressStep(stepId, 'active');
            currentStepId = stepId;
        }
        
        if (data.done || data.error) {
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
        console.error('SSE error:', event);
        evtSource.close();
        showError('Connection lost. Please refresh and try again.');
        hideProgress();
        enableForm();
    };
} 