// ============================================================================
// DATAEXPLORER WIZARD - LOCKED CODE
// ============================================================================
// This wizard collects user choices for both Area Analysis and Lender Analysis.
// All data is stored in wizardState.data and passed to the respective analysis apps.
//
// AREA ANALYSIS PATH: step1 -> step2A -> step3A -> step4A -> step5A
// LENDER ANALYSIS PATH: step1 -> step2B -> step3B -> step4B -> step5B -> step6B
//
// DATA STRUCTURE:
// - geography: Selected counties, CBSA, state (for area analysis)
// - lender: LEI, RSSD, SB_RESID, name, city, state (for lender analysis)
// - filters: Loan filters (actionTaken, occupancy, totalUnits, construction, loanPurpose, loanType, reverseMortgage)
// - lenderAnalysis: Geography scope and comparison group (for lender analysis)
// - disclaimerAccepted: User acceptance of terms
//
// DO NOT MODIFY WITHOUT USER APPROVAL
// ============================================================================

// DataExplorer Wizard - Complete Implementation
// Features: Progressive disclosure, smart defaults, real-time validation, enhanced UX, mobile-first, accessibility

// Wizard State Management
// LOCKED: Core data structure - all user choices are stored here
let wizardState = {
    currentStep: 1,
    analysisType: null, // 'area' or 'lender'
    stepHistory: [],
    data: {
        analysisType: null,  // 'area' or 'lender'
        // AREA ANALYSIS: Geography selection
        geography: {
            counties: [],      // Array of county GEOIDs (5-digit FIPS codes) - selected in step3A
            cbsa: null,        // CBSA code (metro area) - selected in step2A
            cbsa_name: null,   // CBSA name - selected in step2A
            state: null        // State code (if applicable)
        },
        // LENDER ANALYSIS: Lender identification
        lender: {
            name: null,        // Lender name (ALL CAPS) - selected in step2B
            lei: null,         // Legal Entity Identifier - for HMDA data queries - selected in step2B
            rssd: null,        // RSSD ID (10-digit padded) - for branch/CBSA queries - selected in step2B
            sb_resid: null,   // Small Business Respondent ID - for small business loan data - selected in step2B
            type: null,        // Lender type
            city: null,        // Lender city
            state: null,       // Lender state
            sb_rssd: null      // Legacy field (backward compatibility)
        },
        // LOAN FILTERS: Applied to both area and lender analysis
        filters: {
            actionTaken: 'origination',              // 'origination' or 'application' - selected in step4A/step5B
            occupancy: ['owner-occupied'],           // Array: 'owner-occupied', 'second-home', 'investor' - selected in step4A/step5B
            totalUnits: '1-4',                       // '1-4' or '5+' - selected in step4A/step5B
            construction: ['site-built', 'manufactured'],            // Array: 'site-built', 'manufactured' - selected in step4A/step5B
            loanPurpose: ['home-purchase', 'refinance', 'home-equity'],  // Array - selected in step4A/step5B
            loanType: ['conventional', 'fha', 'va', 'rhs'],  // Array - selected in step4A/step5B
            reverseMortgage: true                    // true = not reverse, false = reverse - selected in step4A/step5B
        },
        // LENDER ANALYSIS: Additional selections
        lenderAnalysis: {
            geographyScope: null,    // 'loan_cbsas', 'branch_cbsas', 'custom', 'all_cbsas' - selected in step3B
            comparisonGroup: null,   // 'peers', 'all', 'banks', 'mortgage', 'credit_unions' - selected in step4B
            customCbsa: null,        // CBSA code when geographyScope === 'custom'
            customCbsaName: null,    // CBSA name when geographyScope === 'custom'
            customCounties: []       // Array of county GEOIDs when geographyScope === 'custom'
        },
        disclaimerAccepted: false  // User acceptance - selected in step5A/step6B
    },
    // Smart defaults cache
    cache: {
        states: null,
        metros: null,
        counties: {},
        countiesByMetro: {},
        lenderSearches: [],
        lastState: null,
        lastMetro: null,
        lastLender: null,
        selectedLenderIndex: -1,
        currentLenders: [],
        lenderClickHandlerSet: false,
        lenders: null,  // Cache for all lenders
        filteredLenders: null,  // Filtered lenders for search
        lastCounties: []
    }
};

// Step definitions with paths
// ============================================================================
// LOCKED: AREA ANALYSIS STEP PATHS - DO NOT MODIFY WITHOUT USER APPROVAL
// This defines the area analysis flow structure which is locked and working.
// ============================================================================
const stepPaths = {
    area: ['step1', 'step2A', 'step3A', 'step4A', 'step5A'],
    lender: ['step1', 'step2B', 'step3B', 'step4B', 'step5B', 'step6B']
};

// Progressive Disclosure: Mini Summary Bar
function createSummaryBar() {
    const summaryHTML = `
        <div class="wizard-summary-bar" id="wizardSummaryBar" role="region" aria-label="Wizard progress summary">
            <div class="summary-steps">
                ${generateStepIndicators()}
            </div>
            <div class="summary-details" id="summaryDetails">
                ${generateSummaryDetails()}
            </div>
            <button class="summary-toggle" id="summaryToggle" aria-expanded="false" aria-label="Toggle summary details">
                <i class="fas fa-chevron-down"></i>
            </button>
        </div>
    `;
    
    const wrapper = document.querySelector('.wizard-wrapper');
    if (wrapper && !document.getElementById('wizardSummaryBar')) {
        wrapper.insertAdjacentHTML('afterbegin', summaryHTML);
        attachSummaryListeners();
    }
}

function generateStepIndicators() {
    const currentPath = wizardState.analysisType ? stepPaths[wizardState.analysisType] : ['step1'];
    let html = '';
    
    currentPath.forEach((step, index) => {
        const stepNum = index + 1;
        const isActive = stepNum === wizardState.currentStep;
        const isCompleted = stepNum < wizardState.currentStep;
        const stepName = getStepName(step);
        
        html += `
            <div class="summary-step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}" 
                 data-step="${stepNum}" 
                 onclick="${isCompleted ? `goToStep(${stepNum})` : ''}"
                 role="button"
                 tabindex="${isCompleted ? '0' : '-1'}"
                 aria-label="${stepName} ${isCompleted ? 'completed' : isActive ? 'current' : 'upcoming'}">
                <div class="summary-step-number">${stepNum}</div>
                <div class="summary-step-label">${stepName}</div>
            </div>
        `;
    });
    
    return html;
}

function generateSummaryDetails() {
    let details = [];
    
    if (wizardState.data.analysisType) {
        details.push(`<strong>Type:</strong> ${wizardState.data.analysisType === 'area' ? 'Area Analysis' : 'Lender Analysis'}`);
    }
    
    if (wizardState.data.geography.state) {
        details.push(`<strong>State:</strong> ${wizardState.data.geography.state}`);
    }
    
    if (wizardState.data.geography.counties.length > 0) {
        details.push(`<strong>Counties:</strong> ${wizardState.data.geography.counties.length}`);
    }
    
    if (wizardState.data.lender.name) {
        details.push(`<strong>Lender:</strong> ${wizardState.data.lender.name}`);
    }
    
    if (wizardState.data.lenderAnalysis.geographyScope) {
        details.push(`<strong>Scope:</strong> ${formatGeographyScope(wizardState.data.lenderAnalysis.geographyScope)}`);
    }
    
    if (wizardState.data.lenderAnalysis.comparisonGroup) {
        details.push(`<strong>Compare:</strong> ${formatComparisonGroup(wizardState.data.lenderAnalysis.comparisonGroup)}`);
    }
    
    return details.length > 0 ? details.join(' • ') : 'No selections made yet';
}

function attachSummaryListeners() {
    const toggle = document.getElementById('summaryToggle');
    if (toggle) {
        toggle.addEventListener('click', () => {
            const details = document.getElementById('summaryDetails');
            const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
            details.style.display = isExpanded ? 'none' : 'block';
            toggle.setAttribute('aria-expanded', !isExpanded);
            toggle.querySelector('i').classList.toggle('fa-chevron-down');
            toggle.querySelector('i').classList.toggle('fa-chevron-up');
        });
    }
}

// Smart Defaults: Auto-detect location, suggest common combinations
function initializeSmartDefaults() {
    // Try to detect user's location
    if (navigator.geolocation && !wizardState.cache.lastState) {
        // Note: We'll use IP-based geolocation via backend instead
        // This is just a placeholder for the concept
        loadLastUsedSelections();
    }
    
    // Load cached data
    loadCachedData();
}

function loadLastUsedSelections() {
    const lastState = localStorage.getItem('dataexplorer_lastState');
    const lastCounties = localStorage.getItem('dataexplorer_lastCounties');
    
    if (lastState) {
        wizardState.cache.lastState = lastState;
    }
    
    if (lastCounties) {
        try {
            wizardState.cache.lastCounties = JSON.parse(lastCounties);
        } catch (e) {
            console.error('Error parsing cached counties:', e);
        }
    }
}

function loadCachedData() {
    // Load states if cached
    const cachedStates = localStorage.getItem('dataexplorer_states');
    if (cachedStates) {
        try {
            wizardState.cache.states = JSON.parse(cachedStates);
        } catch (e) {
            console.error('Error parsing cached states:', e);
        }
    }
    
    // Load lender search history
    const searchHistory = localStorage.getItem('dataexplorer_lenderSearches');
    if (searchHistory) {
        try {
            wizardState.cache.lenderSearches = JSON.parse(searchHistory);
        } catch (e) {
            console.error('Error parsing search history:', e);
        }
    }
}

function saveToCache(key, data) {
    try {
        localStorage.setItem(`dataexplorer_${key}`, JSON.stringify(data));
    } catch (e) {
        console.error(`Error saving to cache (${key}):`, e);
    }
}

// Real-time Validation
const validationRules = {
    counties: {
        validate: (counties) => {
            if (!counties || counties.length === 0) {
                return { valid: false, message: 'Please select at least one county' };
            }
            
            // Check CBSA consistency
            const cbsas = [...new Set(counties.map(c => c.cbsa))];
            if (cbsas.length > 1) {
                return { 
                    valid: false, 
                    message: `Selected counties span ${cbsas.length} different CBSAs. All counties must be in the same CBSA.`,
                    details: cbsas.map(cbsa => {
                        const county = counties.find(c => c.cbsa === cbsa);
                        return county?.cbsa_name || cbsa;
                    })
                };
            }
            
            return { valid: true };
        },
        showFeedback: (element, result) => {
            const feedback = element.parentElement.querySelector('.validation-feedback');
            if (feedback) feedback.remove();
            
            // Only show feedback for errors (not for valid states)
            if (result.valid) {
                return;
            }
            
            // Ensure message exists
            const message = result.message || 'Validation error';
            
            const feedbackEl = document.createElement('div');
            feedbackEl.className = `validation-feedback invalid`;
            feedbackEl.setAttribute('role', 'alert');
            feedbackEl.innerHTML = `
                <i class="fas fa-exclamation-circle"></i>
                <span>${message}</span>
            `;
            
            element.parentElement.appendChild(feedbackEl);
            
            // Announce to screen readers
            announceToScreenReader(message);
        }
    },
    lender: {
        validate: (query) => {
            if (!query || query.length < 3) {
                return { valid: false, message: 'Please enter at least 3 characters' };
            }
            return { valid: true };
        }
    }
};

function validateStep(stepKey) {
    switch(stepKey) {
        case 'step2A':
            // Validate metro selection
            const select = document.getElementById('metroSelect');
            const selectText = document.getElementById('metroSelectText');
            if (!select || !select.value) {
                if (!selectText || selectText.textContent === 'Select a metro area...') {
                    return { valid: false, message: 'Please select a metro area' };
                }
            }
            return { valid: true };
        case 'step2B':
            return validateLenderSearch();
        case 'step3A':
            return validateCounties();
        case 'step4A':
            // validateFilters() returns boolean, but we need { valid, message }
            const filtersValid = validateFilters();
            if (!filtersValid) {
                // Error message already shown by validateFilters()
                return { valid: false, message: 'Please complete all filter selections' };
            }
            return { valid: true };
        case 'step3B':
            return validateGeographyScope();
        case 'step4B':
            return validateComparisonGroup();
        default:
            return { valid: true };
    }
}

function validateCounties() {
    const selectedCounties = getSelectedCounties();
    return validationRules.counties.validate(selectedCounties);
}

// Updated to work with lender dropdown selector
function validateLenderSearch() {
    const select = document.getElementById('lenderSelect');
    const selectText = document.getElementById('lenderSelectText');
    
    if (!select || !select.value) {
        if (!selectText || selectText.textContent === 'Select a lender...') {
            return { valid: false, message: 'Please select a lender' };
        }
    }
    
    if (!wizardState.data.lender || !wizardState.data.lender.lei) {
        return { valid: false, message: 'Please select a lender' };
    }
    
    return { valid: true };
}

function validateFilters() {
    // Filters always have defaults, so always valid
    return { valid: true };
}

function validateGeographyScope() {
    const selected = document.querySelector('input[name="geoScope"]:checked');
    if (!selected) {
        return { valid: false, message: 'Please select a geographic scope' };
    }
    return { valid: true };
}

function validateComparisonGroup() {
    const selected = document.querySelector('input[name="compGroup"]:checked');
    if (!selected) {
        return { valid: false, message: 'Please select a comparison group' };
    }
    return { valid: true };
}

// Enhanced UX: Smooth transitions, loading states, success animations
function transitionToStep(stepKey, direction = 'forward') {
    const currentCard = document.querySelector('.step-card.active');
    if (!currentCard) return;
    
    // Validate current step before proceeding
    if (direction === 'forward') {
        const validation = validateStep(currentCard.dataset.step);
        if (!validation.valid) {
            showError(validation.message);
            return false;
        }
    }
    
    // Show loading
    showLoading('Preparing next step...');
    
    // Animate out current card
    currentCard.classList.add('exiting');
    currentCard.classList.remove('active');
    
    setTimeout(() => {
        // Update state
        updateWizardState(stepKey);
        
        // Render new step
        renderStep(stepKey);
        
        // Update summary bar (removed - summary bar not displayed)
        // updateSummaryBar();
        
        // Hide loading
        hideLoading();
        
        // Animate in new card
        const newCard = document.querySelector('.step-card.active');
        if (newCard) {
            newCard.classList.add('entering');
            setTimeout(() => {
                newCard.classList.remove('entering');
            }, 300);
        }
        
        // Focus management for accessibility
        focusFirstInput(newCard);
        
        // Announce step change to screen readers
        announceStepChange(stepKey);
        
    }, 300);
    
    return true;
}

function updateWizardState(stepKey) {
    // Determine step number from step key
    const path = wizardState.analysisType ? stepPaths[wizardState.analysisType] : [];
    const stepIndex = path.indexOf(stepKey);
    if (stepIndex !== -1) {
        wizardState.currentStep = stepIndex + 1;
    }
    
    // Add to history
    if (!wizardState.stepHistory.includes(stepKey)) {
        wizardState.stepHistory.push(stepKey);
    }
}

function announceStepChange(stepKey) {
    const stepName = getStepName(stepKey);
    announceToScreenReader(`Now on step ${wizardState.currentStep}: ${stepName}`);
}

function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    document.body.appendChild(announcement);
    
    setTimeout(() => {
        document.body.removeChild(announcement);
    }, 1000);
}

function focusFirstInput(container) {
    const firstInput = container.querySelector('input, select, textarea, button');
    if (firstInput) {
        firstInput.focus();
    }
}

// Success animation when step completes
function showStepSuccess(stepElement) {
    const checkmark = document.createElement('div');
    checkmark.className = 'step-success-checkmark';
    checkmark.innerHTML = '<i class="fas fa-check-circle"></i>';
    stepElement.appendChild(checkmark);
    
    setTimeout(() => {
        checkmark.classList.add('animate');
    }, 100);
    
    setTimeout(() => {
        checkmark.remove();
    }, 2000);
}

// Mobile-first enhancements: Swipe gestures, bottom sheets
let touchStartX = 0;
let touchEndX = 0;

function initSwipeGestures() {
    const container = document.getElementById('wizardContainer');
    if (!container) return;
    
    container.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    container.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
}

function handleSwipe() {
    const swipeThreshold = 50;
    const diff = touchStartX - touchEndX;
    
    if (Math.abs(diff) > swipeThreshold) {
        if (diff > 0) {
            // Swipe left - go forward
            const currentPath = wizardState.analysisType ? stepPaths[wizardState.analysisType] : [];
            const currentIndex = currentPath.findIndex(step => {
                const card = document.querySelector(`.step-card[data-step="${step}"]`);
                return card && card.classList.contains('active');
            });
            
            if (currentIndex < currentPath.length - 1) {
                const nextStep = currentPath[currentIndex + 1];
                transitionToStep(nextStep, 'forward');
            }
        } else {
            // Swipe right - go back
            goBack();
        }
    }
}

// Accessibility: Keyboard navigation, screen reader support, reduced motion
function initAccessibility() {
    // Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
        document.documentElement.classList.add('reduced-motion');
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardNavigation);
    
    // Focus trap in modals
    initFocusTraps();
    
    // High contrast mode toggle (if needed)
    initHighContrastToggle();
}

function handleKeyboardNavigation(e) {
    // Escape key - go back
    if (e.key === 'Escape' && wizardState.currentStep > 1) {
        e.preventDefault();
        goBack();
        return;
    }
    
    // Enter key - proceed (if on button or last input)
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
        const activeCard = document.querySelector('.step-card.active');
        if (activeCard) {
            const nextButton = activeCard.querySelector('.btn-primary');
            if (nextButton && !nextButton.disabled) {
                e.preventDefault();
                nextButton.click();
            }
        }
    }
    
    // Arrow keys for step navigation (if implemented)
    if (e.key === 'ArrowLeft' && wizardState.currentStep > 1) {
        e.preventDefault();
        goBack();
    }
}

function initFocusTraps() {
    // Focus trap for modals/overlays
    const modals = document.querySelectorAll('.modal, .loading-overlay');
    modals.forEach(modal => {
        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                const focusableElements = modal.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];
                
                if (e.shiftKey && document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                } else if (!e.shiftKey && document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        });
    });
}

function initHighContrastToggle() {
    // Add high contrast toggle button (optional feature)
    const toggle = document.createElement('button');
    toggle.className = 'accessibility-toggle';
    toggle.setAttribute('aria-label', 'Toggle high contrast mode');
    toggle.innerHTML = '<i class="fas fa-adjust"></i>';
    toggle.onclick = () => {
        document.body.classList.toggle('high-contrast');
        const isActive = document.body.classList.contains('high-contrast');
        toggle.setAttribute('aria-pressed', isActive);
        localStorage.setItem('dataexplorer_highContrast', isActive);
    };
    
    // Check saved preference
    if (localStorage.getItem('dataexplorer_highContrast') === 'true') {
        document.body.classList.add('high-contrast');
        toggle.setAttribute('aria-pressed', 'true');
    }
    
    // Add to page (you might want to position this differently)
    const header = document.querySelector('.wizard-wrapper');
    if (header) {
        header.insertAdjacentElement('afterbegin', toggle);
    }
}

// Utility functions
function getStepName(stepKey) {
    const names = {
        'step1': 'Choose Analysis Type',
        'step2A': 'Select Geography',
        'step2B': 'Enter Lender',
        'step2A': 'Select Metro Area',
        'step3A': 'Select Counties',
        'step4A': 'Data Filters',
        'step3B': 'Define Geography',
        'step5A': 'Disclaimer',
        'step4B': 'Comparison Group',
        'step5B': 'Disclaimer'
    };
    return names[stepKey] || stepKey;
}

function formatGeographyScope(scope) {
    const formats = {
        'all_cbsas': 'All CBSAs',
        'branch_cbsas': 'Branch CBSAs (>1%)',
        'loan_cbsas': 'Loan Volume CBSAs (>1%)'
    };
    return formats[scope] || scope;
}

function formatComparisonGroup(group) {
    const formats = {
        'all': 'All Lenders',
        'banks': 'Banks Only',
        'mortgage': 'Mortgage Companies',
        'credit_unions': 'Credit Unions',
        'peers': 'Peer Lenders (DOJ)'
    };
    return formats[group] || group;
}

function getSelectedCounties() {
    const checkboxes = document.querySelectorAll('#countyCheckboxes input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => {
        return {
            geoid: cb.value,
            fips: cb.dataset.fips,
            name: cb.dataset.name,
            cbsa: cb.dataset.cbsa,
            cbsa_name: cb.dataset.cbsaName
        };
    });
}

function showError(message) {
    // Remove existing errors
    const existingErrors = document.querySelectorAll('.error-message');
    existingErrors.forEach(err => err.remove());
    
    // Don't show error if message is undefined or empty, but log it for debugging
    if (!message || message === 'undefined') {
        console.warn('showError called with undefined or empty message');
        return;
    }
    
    const error = document.createElement('div');
    error.className = 'error-message';
    error.setAttribute('role', 'alert');
    error.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <span>${message}</span>
    `;
    
    const activeCard = document.querySelector('.step-card.active .card-body');
    if (activeCard) {
        activeCard.insertAdjacentElement('afterbegin', error);
        
        // Focus error for screen readers
        error.focus();
        
        // Announce to screen readers
        announceToScreenReader(`Error: ${message}`);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            error.remove();
        }, 5000);
    }
}

function showLoading(text = 'Loading...') {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    
    if (overlay) {
        if (loadingText) loadingText.textContent = text;
        overlay.classList.add('active');
        overlay.setAttribute('aria-busy', 'true');
        announceToScreenReader(text);
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('active');
        overlay.setAttribute('aria-busy', 'false');
    }
}

// Export for use in main HTML file
window.wizardState = wizardState;
window.transitionToStep = transitionToStep;
window.createSummaryBar = createSummaryBar;
window.initializeSmartDefaults = initializeSmartDefaults;
window.initSwipeGestures = initSwipeGestures;
window.initAccessibility = initAccessibility;
