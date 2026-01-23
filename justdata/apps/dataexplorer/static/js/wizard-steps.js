// DataExplorer Wizard Steps Implementation
// Complete step rendering and interaction logic

// Card Definitions
// ============================================================================
// DATAEXPLORER WIZARD STEPS - LOCKED CODE
// ============================================================================
// This file contains all step definitions and handlers for the DataExplorer wizard.
//
// AREA ANALYSIS STEPS (LOCKED):
// - step1: Choose Analysis Type
// - step2A: Select Metro Area (with keyboard navigation)
// - step3A: Select Counties (chip format with select all/deselect all)
// - step4A: Data Filters (grouped by variable with chip format)
// - step5A: Disclaimer
//
// LENDER ANALYSIS STEPS (LOCKED):
// - step1: Choose Analysis Type
// - step2B: Select Lender (with dropdown search, displays LEI/RSSD/SB_RESID with links)
// - step3B: Define Geography (all_cbsas, branch_cbsas, loan_cbsas)
// - step4B: Comparison Group (all, banks, mortgage)
// - step5B: Data Filters (same format as step4A)
// - step6B: Disclaimer
//
// DO NOT MODIFY WITHOUT USER APPROVAL
// ============================================================================

// Institution Type Helper - Classify lenders by branch availability in FDIC SOD data
// Note: Credit unions have branches but they're in NCUA data, not FDIC - will add in v2
function getInstitutionCategory(typeName) {
    if (!typeName) {
        return { category: 'unknown', badge: '', hasBranches: null };
    }

    const lower = typeName.toLowerCase();

    // Credit unions - have branches but in NCUA data (not yet integrated)
    if (lower.includes('credit union')) {
        return {
            category: 'credit_union',
            hasBranches: false,  // Not in FDIC SOD - will add NCUA in v2
            badge: '<span style="font-size: 0.7rem; padding: 2px 6px; background: #e3f2fd; color: #1565c0; border-radius: 4px; white-space: nowrap;" title="Credit Union - branch data coming in v2"><i class="fas fa-users" style="margin-right: 3px;"></i>Credit Union</span>'
        };
    }

    // Banks/Thrifts - have branches in FDIC SOD data
    const bankKeywords = ['bank', 'savings', 'thrift', 'affiliate'];
    const isBank = bankKeywords.some(k => lower.includes(k));

    // Non-depository institutions - no physical branches
    const nonDepositoryKeywords = ['mortgage', 'finance company', 'non-bank', 'independent'];
    const isNonDepository = nonDepositoryKeywords.some(k => lower.includes(k));

    if (isBank && !isNonDepository) {
        return {
            category: 'bank',
            hasBranches: true,
            badge: '<span style="font-size: 0.7rem; padding: 2px 6px; background: #e8f5e9; color: #2e7d32; border-radius: 4px; white-space: nowrap;" title="Bank - has physical branch locations in FDIC data"><i class="fas fa-building" style="margin-right: 3px;"></i>Bank</span>'
        };
    } else if (isNonDepository || lower.includes('mortgage')) {
        return {
            category: 'non-depository',
            hasBranches: false,
            badge: '<span style="font-size: 0.7rem; padding: 2px 6px; background: #fff3e0; color: #e65100; border-radius: 4px; white-space: nowrap;" title="Non-bank lender - no physical branch locations"><i class="fas fa-briefcase" style="margin-right: 3px;"></i>Non-Bank</span>'
        };
    } else {
        return {
            category: 'unknown',
            hasBranches: null,
            badge: ''
        };
    }
}

const cards = {
    step1: {
        number: 1,
        title: 'Choose Analysis Type',
        render: () => `
            <div class="card-body">
                <p>Select the type of analysis you want to perform:</p>
                <div class="analysis-type-buttons">
                    <div class="analysis-btn" onclick="selectAnalysisType('area')" role="button" tabindex="0" aria-label="Select Area Analysis">
                        <span class="analysis-btn-text">Area Analysis</span>
                        <div class="analysis-btn-description">
                            <div>Explore lending patterns and trends for specific</div>
                            <div>metro areas with detailed filtering and export options</div>
                        </div>
                        <div class="tooltip-popup">
                            <div class="tooltip-content">
                                <strong>Area Analysis</strong>
                                <p>Detailed lending data dashboard for geographic areas with advanced filtering, exports, and flexibility for experienced users. Analyze mortgage lending patterns, small business lending, and branch locations for specific counties or CBSAs.</p>
                            </div>
                        </div>
                    </div>
                    <div class="analysis-btn" onclick="selectAnalysisType('lender')" role="button" tabindex="0" aria-label="Select Lender Analysis">
                        <span class="analysis-btn-text">Lender Analysis</span>
                        <div class="analysis-btn-description">
                            <div>Compare a specific lender's performance against</div>
                            <div>peers and market segments in their operating areas</div>
                        </div>
                        <div class="tooltip-popup">
                            <div class="tooltip-content">
                                <strong>Lender Analysis</strong>
                                <p>Performance analysis comparing a specific lender against peers or market segments. Evaluate lending patterns, geographic distribution, and performance metrics to understand how a lender compares to competitors in the same markets.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },
    // LOCKED: Part of Area Analysis Structure
    step2A: {
        number: 2,
        title: 'Select Metro Area',
        render: () => `
            <div class="card-body" style="display: flex; flex-direction: column; padding: 16px;">
                <div style="flex: 1; overflow-y: auto;">
                    <div class="form-group" style="margin-bottom: 0;">
                        <div class="metro-select-container">
                            <div class="metro-select-button" id="metroSelectButton" role="button" tabindex="0" aria-haspopup="listbox" aria-expanded="false">
                                <span class="metro-select-text" id="metroSelectText">Select a metro area...</span>
                            </div>
                            <select id="metroSelect" style="display: none;" aria-required="true">
                                <option value="">Select a metro area...</option>
                            </select>
                            <div class="metro-dropdown-wrapper" style="display: none;">
                                <div class="metro-search-box">
                                    <input type="text" 
                                           id="metroSearch" 
                                           placeholder="Search metros..."
                                           autocomplete="off"
                                           aria-label="Search metro areas">
                                    <i class="fas fa-search"></i>
                                </div>
                                <div id="metroDropdown" class="metro-dropdown" role="listbox"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },
    // LOCKED: Part of Area Analysis Structure
    step3A: {
        number: 3,
        title: 'Select Counties',
        render: () => `
            <div class="card-body" style="display: flex; flex-direction: column; padding: 16px;">
                <div style="flex: 1; overflow-y: auto;">
                    <div class="form-group" style="margin-bottom: 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <label style="margin: 0; font-size: 0.9rem;">Counties (select multiple)</label>
                            <div style="display: flex; gap: 8px;">
                                <button type="button" class="btn btn-link" onclick="selectAllCounties()" style="padding: 2px 6px; font-size: 0.75rem; text-decoration: underline;">
                                    Select All
                                </button>
                                <button type="button" class="btn btn-link" onclick="deselectAllCounties()" style="padding: 2px 6px; font-size: 0.75rem; text-decoration: underline;">
                                    Deselect All
                                </button>
                            </div>
                        </div>
                        <div id="countyCheckboxes" class="county-tiles-container" role="group" aria-label="County selection">
                            <p style="color: #999; font-size: 0.85rem; margin: 8px 0;">Loading counties...</p>
                        </div>
                    </div>
                </div>
            </div>
        `
    },
    step2B: {
        number: 2,
        title: 'Select Lender',
        render: () => `
            <div class="card-body" style="display: flex; flex-direction: column; padding: 16px;">
                <div style="flex: 1; overflow-y: auto; display: flex; gap: 20px;">
                    <!-- Lender Information Block (Left) -->
                    <div id="lenderInfoBlock" class="lender-info-block" style="flex: 0 0 300px; display: none;">
                        <h4 style="margin: 0 0 12px 0; font-size: 1rem; color: var(--ncrc-primary-blue);">Lender Information</h4>
                        <div id="lenderInfoContent" style="display: flex; flex-direction: column; gap: 8px;">
                            <!-- Info will be populated here -->
                        </div>
                    </div>
                    
                    <!-- Lender Selector (Right) -->
                    <div style="flex: 1; min-width: 0;">
                        <div class="form-group" style="margin-bottom: 0;">
                            <div class="lender-select-container">
                                <div class="lender-select-button" id="lenderSelectButton" role="button" tabindex="0" aria-haspopup="listbox" aria-expanded="false">
                                    <span class="lender-select-text" id="lenderSelectText">Select a lender...</span>
                                </div>
                                <select id="lenderSelect" style="display: none;" aria-required="true">
                                    <option value="">Select a lender...</option>
                                </select>
                                <div class="lender-dropdown-wrapper" style="display: none;">
                                    <div class="lender-search-box">
                                        <input type="text" 
                                               id="lenderSearch" 
                                               placeholder="Search lenders..."
                                               autocomplete="off"
                                               aria-label="Search lenders">
                                        <i class="fas fa-search"></i>
                                    </div>
                                    <div id="lenderDropdown" class="lender-dropdown" role="listbox"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },
    // LOCKED: Part of Area Analysis Structure
    step4A: {
        number: 4,
        title: 'Data Filters',
        render: () => `
            <div class="card-body" style="display: flex; flex-direction: column; padding: 16px;">
                <div style="flex: 1; overflow-y: auto;">
                    <div id="filterChipsDisplay" class="filter-groups-container">
                        <!-- Filter groups will be rendered here -->
                    </div>
                </div>
            </div>
        `
    },
    step3B: {
        number: 3,
        title: 'Define Geography',
        render: () => `
            <div class="card-body">
                <p>How should we define the geographic scope?</p>
                <div class="checkbox-group" style="margin-top: 20px;" role="radiogroup" aria-label="Geographic scope options">
                    <label class="checkbox-item">
                        <input type="radio" name="geoScope" value="loan_cbsas" aria-required="true"> 
                        <span>CBSAs with >1% of loan applications</span>
                    </label>
                    <label class="checkbox-item">
                        <input type="radio" name="geoScope" value="branch_cbsas"> 
                        <span>CBSAs with >1% of branches</span>
                    </label>
                    <label class="checkbox-item">
                        <input type="radio" name="geoScope" value="custom"> 
                        <span>Custom CBSA</span>
                    </label>
                    <label class="checkbox-item">
                        <input type="radio" name="geoScope" value="all_cbsas"> 
                        <span>All CBSAs</span>
                    </label>
                </div>
            </div>
        `
    },
    step3B5: {
        number: 3.5,
        title: 'Select Metro Area',
        render: () => `
            <div class="card-body" style="display: flex; flex-direction: column; padding: 16px;">
                <div style="flex: 1; overflow-y: auto;">
                    <div class="form-group" style="margin-bottom: 0;">
                        <div class="metro-select-container">
                            <div class="metro-select-button" id="customMetroSelectButton" role="button" tabindex="0" aria-haspopup="listbox" aria-expanded="false">
                                <span class="metro-select-text" id="customMetroSelectText">Select a metro area...</span>
                            </div>
                            <select id="customMetroSelect" style="display: none;" aria-required="true">
                                <option value="">Select a metro area...</option>
                            </select>
                            <div class="metro-dropdown-wrapper" style="display: none;">
                                <div class="metro-search-box">
                                    <input type="text" 
                                           id="customMetroSearch" 
                                           placeholder="Search metros..."
                                           autocomplete="off"
                                           aria-label="Search metro areas">
                                    <i class="fas fa-search"></i>
                                </div>
                                <div id="customMetroDropdown" class="metro-dropdown" role="listbox"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },
    step3B6: {
        number: 3.6,
        title: 'Select Counties',
        render: () => `
            <div class="card-body" style="display: flex; flex-direction: column; padding: 16px;">
                <div style="flex: 1; overflow-y: auto;">
                    <div class="form-group" style="margin-bottom: 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <label style="margin: 0; font-size: 0.9rem;">Counties (all pre-selected, uncheck to exclude)</label>
                            <div style="display: flex; gap: 8px;">
                                <button type="button" class="btn btn-link" onclick="selectAllCustomCounties()" style="padding: 2px 6px; font-size: 0.75rem; text-decoration: underline;">
                                    Select All
                                </button>
                                <button type="button" class="btn btn-link" onclick="deselectAllCustomCounties()" style="padding: 2px 6px; font-size: 0.75rem; text-decoration: underline;">
                                    Deselect All
                                </button>
                            </div>
                        </div>
                        <div id="customCountyCheckboxes" class="county-tiles-container" role="group" aria-label="County selection">
                            <p style="color: #999; font-size: 0.85rem; margin: 8px 0;">Loading counties...</p>
                        </div>
                    </div>
                </div>
            </div>
        `
    },
    // LOCKED: Part of Area Analysis Structure
    step5A: {
        number: 5,
        title: 'Disclaimer',
        render: () => `
            <div class="card-body">
                <div class="disclaimer-box">
                    <h4><i class="fas fa-exclamation-triangle"></i> Important Notice</h4>
                    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
                    <div class="disclaimer-checkbox">
                        <input type="checkbox" id="disclaimerAccept" aria-required="true">
                        <label for="disclaimerAccept">I understand and accept these terms</label>
                    </div>
                </div>
            </div>
        `
    },
    step4B: {
        number: 4,
        title: 'Comparison Group',
        render: () => `
            <div class="card-body">
                <p>Compare subject lender to:</p>
                <div class="checkbox-group" style="margin-top: 20px;" role="radiogroup" aria-label="Comparison group options">
                    <label class="checkbox-item">
                        <input type="radio" name="compGroup" value="peers" aria-required="true" checked>
                        <span>
                            Peer Lenders
                            <span class="tooltip-icon">
                                <i class="fas fa-info-circle"></i>
                                <span class="tooltip-content">
                                    DOJ methodology: Peers are lenders with 50-200% of subject lender's application volume. 
                                    <a href="/methodology/peer-selection" target="_blank" style="color: #2fade3;">Learn more</a>
                                </span>
                            </span>
                        </span>
                    </label>
                    <label class="checkbox-item">
                        <input type="radio" name="compGroup" value="all"> 
                        <span>All Lenders</span>
                    </label>
                    <label class="checkbox-item">
                        <input type="radio" name="compGroup" value="banks"> 
                        <span>Banks</span>
                    </label>
                    <label class="checkbox-item">
                        <input type="radio" name="compGroup" value="mortgage"> 
                        <span>Mortgage Companies</span>
                    </label>
                    <label class="checkbox-item">
                        <input type="radio" name="compGroup" value="credit_unions"> 
                        <span>Credit Unions</span>
                    </label>
                </div>
            </div>
        `
    },
    step5B: {
        number: 5,
        title: 'Data Filters',
        render: () => `
            <div class="card-body" style="display: flex; flex-direction: column; padding: 16px;">
                <div style="flex: 1; overflow-y: auto;">
                    <div id="filterChipsDisplayB" class="filter-groups-container">
                        <!-- Filter groups will be rendered here -->
                    </div>
                </div>
            </div>
        `
    },
    step6B: {
        number: 6,
        title: 'Disclaimer',
        render: () => `
            <div class="card-body">
                <div class="disclaimer-box">
                    <h4><i class="fas fa-exclamation-triangle"></i> Important Notice</h4>
                    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
                    <div class="disclaimer-checkbox">
                        <input type="checkbox" id="disclaimerAcceptB" aria-required="true">
                        <label for="disclaimerAcceptB">I understand and accept these terms</label>
                    </div>
                </div>
            </div>
        `
    }
};

// Initialize wizard
function initWizard() {
    renderStep('step1');
}

// Navigate to a step by clicking a progress dot
function navigateToStepByDot(stepNum) {
    console.log('navigateToStepByDot called with stepNum:', stepNum);
    const currentPath = wizardState.analysisType ? stepPaths[wizardState.analysisType] : ['step1'];
    console.log('Current path:', currentPath);
    
    if (stepNum > 0 && stepNum <= currentPath.length) {
        const targetStep = currentPath[stepNum - 1];
        const currentStepKey = document.querySelector('.step-card.active')?.dataset.step;
        const currentIndex = currentPath.indexOf(currentStepKey);
        
        console.log('Target step:', targetStep, 'Current index:', currentIndex);
        
        // Only allow navigation to completed steps (steps before or equal to current)
        if (stepNum <= currentIndex + 1 && stepNum > 0) {
            console.log('Navigating to step:', targetStep);
            transitionToStep(targetStep, 'backward');
        } else {
            console.log('Cannot navigate to step', stepNum, '- not completed yet');
        }
    } else {
        console.log('Invalid step number:', stepNum);
    }
}


// Generate progress dots based on current step and path
function generateProgressDots(stepKey) {
    // Determine the path based on analysis type
    let currentPath;
    let totalDots;
    
    if (stepKey === 'step1' && !wizardState.analysisType) {
        // On step1 before path selection, show all 5 dots (max path length)
        // Step1 will be current (blue), rest will be upcoming (grey)
        totalDots = 5;
        currentPath = null; // No path selected yet
    } else {
        currentPath = wizardState.analysisType ? stepPaths[wizardState.analysisType] : ['step1'];
        totalDots = currentPath.length;
    }
    
    const currentStepIndex = currentPath ? currentPath.indexOf(stepKey) : 0;
    
    let dotsHTML = '<div class="progress-dots" role="progressbar" aria-valuenow="' + (currentStepIndex + 1) + '" aria-valuemin="1" aria-valuemax="' + totalDots + '">';
    
    // Generate dots for all steps in the current path
    for (let stepNum = 1; stepNum <= totalDots; stepNum++) {
        let dotClass = 'progress-dot';
        let isClickable = false;
        let onClickHandler = '';
        let ariaLabel = `Step ${stepNum}`;
        
        if (currentPath) {
            // Path is determined - show status based on actual progress
            if (stepNum < currentStepIndex + 1) {
                // Completed step - green and clickable
                dotClass += ' completed clickable';
                isClickable = true;
                ariaLabel += ' - completed, click to return';
            } else if (stepNum === currentStepIndex + 1) {
                // Current step - blue, not clickable
                dotClass += ' current';
                ariaLabel += ' - current step';
            } else {
                // Upcoming step - grey, not clickable
                dotClass += ' upcoming';
                ariaLabel += ' - upcoming';
            }
        } else {
            // No path selected yet (step1) - show step1 as current, rest as upcoming
            if (stepNum === 1) {
                dotClass += ' current';
                ariaLabel += ' - current step';
            } else {
                dotClass += ' upcoming';
                ariaLabel += ' - upcoming';
            }
        }
        
        // Add step number inside the dot
        dotsHTML += `<div class="${dotClass}" data-step-num="${stepNum}" role="${isClickable ? 'button' : 'presentation'}" tabindex="${isClickable ? '0' : '-1'}" aria-label="${ariaLabel}">${stepNum}${isClickable ? '<span class="sr-only"> - click to return</span>' : ''}</div>`;
    }
    
    dotsHTML += '</div>';
    return dotsHTML;
}

// Generate header buttons for a step
function generateHeaderButtons(stepKey) {
    const stepConfig = {
        'step1': { back: false, next: false },
        'step2A': { back: true, next: 'confirmMetro()', nextText: 'Next' },
        'step3A': { back: true, next: 'confirmGeography()', nextText: 'Next' },
        'step4A': { back: true, next: 'confirmFilters()', nextText: 'Next' },
        'step5A': { back: true, next: 'generateReport()', nextText: 'Generate Report', nextId: 'finalSubmitBtn', nextIcon: 'fa-rocket', nextDisabled: true },
        'step2B': { back: true, next: 'confirmLender()', nextText: 'Confirm', nextIcon: 'fa-check' },
        'step3B': { back: true, next: 'confirmGeoScope()', nextText: 'Next' },
        'step3B5': { back: true, next: 'confirmCustomCbsa()', nextText: 'Next' },
        'step3B6': { back: true, next: 'confirmCustomCounties()', nextText: 'Next' },
        'step4B': { back: true, next: 'confirmComparisonGroup()', nextText: 'Next' },
        'step5B': { back: true, next: 'confirmFiltersB()', nextText: 'Next' },
        'step6B': { back: true, next: 'generateReport()', nextText: 'Generate Report', nextId: 'finalSubmitBtnB', nextIcon: 'fa-rocket', nextDisabled: true }
    };
    
    const config = stepConfig[stepKey] || { back: true, next: false };
    let buttonsHTML = '<div class="card-header-buttons">';
    
    if (config.back) {
        buttonsHTML += `<button class="btn btn-secondary" onclick="goBack()" aria-label="Go back to previous step">
            <i class="fas fa-arrow-left"></i> Back
        </button>`;
    }
    
    if (config.next) {
        const nextId = config.nextId ? ` id="${config.nextId}"` : '';
        const nextDisabled = config.nextDisabled ? ' disabled' : '';
        const nextIcon = config.nextIcon ? ` <i class="fas ${config.nextIcon}"></i>` : ' <i class="fas fa-arrow-right"></i>';
        const nextText = config.nextText || 'Next';
        buttonsHTML += `<button class="btn btn-primary" onclick="${config.next}"${nextId}${nextDisabled} aria-label="Continue to next step">
            ${nextText}${nextIcon}
        </button>`;
    }
    
    buttonsHTML += '</div>';
    return buttonsHTML;
}

// Render a step
function renderStep(stepKey) {
    const container = document.getElementById('wizardContainer');
    const card = cards[stepKey];

    if (!card) return;

    const progressDots = generateProgressDots(stepKey);
    const headerButtons = generateHeaderButtons(stepKey);

    container.innerHTML = `
        <div class="step-card active" data-step="${stepKey}" role="region" aria-label="${card.title}">
            <div class="card-header">
                ${progressDots}
                <h3>${card.title}</h3>
                ${headerButtons}
            </div>
            ${card.render()}
        </div>
    `;

    // Attach event listeners specific to this step
    attachStepListeners(stepKey);
    
    // Setup metros UI when step2A is rendered (metros should already be loading/loaded)
    if (stepKey === 'step2A') {
        // Use requestAnimationFrame to ensure DOM is fully rendered first
        requestAnimationFrame(() => {
            // If metros are already loaded, set up UI immediately
            if (wizardState.cache.metros && wizardState.cache.metros.length > 0) {
                setupMetroDropdown();
            } else {
                // Metros not loaded yet, wait for them and then set up UI
                // loadMetros() will call setupMetroDropdown() when done
                loadMetros();
            }
        });
    }
    
    // Load counties when step3A is rendered (if metro is already selected)
    if (stepKey === 'step3A' && wizardState.data.geography.cbsa) {
        loadCountiesByMetro();
    }
    
    // Update branch_cbsas option state based on lender type (step3B)
    if (stepKey === 'step3B') {
        requestAnimationFrame(() => {
            updateBranchOptionState();
        });
    }
    
    // Setup custom metro dropdown when step3B5 is rendered
    if (stepKey === 'step3B5') {
        console.log('step3B5 rendered, setting up custom metro dropdown...');
        requestAnimationFrame(() => {
            if (wizardState.cache.metros && wizardState.cache.metros.length > 0) {
                console.log('Metros already loaded, calling setupCustomMetroDropdown');
                setupCustomMetroDropdown();
            } else {
                console.log('Loading metros first, then will call setupCustomMetroDropdown');
                loadMetros().then(() => {
                    console.log('Metros loaded, calling setupCustomMetroDropdown');
                    setupCustomMetroDropdown();
                });
            }
        });
    }
    
    // Load counties when step3B6 is rendered (if CBSA is already selected)
    if (stepKey === 'step3B6' && wizardState.data.lenderAnalysis.customCbsa) {
        loadCustomCountiesByMetro();
    }
    
    // Initialize filters when step4A or step5B is rendered
    if (stepKey === 'step4A' || stepKey === 'step5B') {
        // Initialize default filters if not set
        if (!wizardState.data.filters) {
            wizardState.data.filters = {
                actionTaken: 'origination',
                occupancy: ['owner-occupied'],
                totalUnits: '1-4',
                construction: ['site-built', 'manufactured'],
                loanPurpose: ['home-purchase', 'refinance', 'home-equity'],
                loanType: ['conventional', 'fha', 'va', 'rhs'],
                reverseMortgage: true
            };
        }
        // Render filter chips (use different container for step5B)
        if (stepKey === 'step4A') {
            renderFilterChips();
        } else if (stepKey === 'step5B') {
            renderFilterChipsB();
        }
    }
    
    // Attach click handlers to progress dots (for completed steps)
    // Use requestAnimationFrame to ensure DOM is ready
    requestAnimationFrame(() => {
        attachProgressDotListeners();
    });
}

// Attach click handlers to progress dots
function attachProgressDotListeners() {
    const completedDots = document.querySelectorAll('.progress-dot.completed.clickable');
    console.log('Found', completedDots.length, 'clickable progress dots');
    
    completedDots.forEach((dot) => {
        const stepNum = parseInt(dot.getAttribute('data-step-num'));
        if (!stepNum) {
            console.warn('Progress dot missing data-step-num attribute');
            return;
        }
        
        // Remove any existing listeners by cloning
        const newDot = dot.cloneNode(true);
        dot.parentNode.replaceChild(newDot, dot);
        
        // Add click handler with explicit binding
        newDot.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Clicked progress dot for step', stepNum);
            navigateToStepByDot(stepNum);
            return false;
        }, true); // Use capture phase
        
        // Add keyboard support (Enter/Space)
        newDot.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                e.stopPropagation();
                console.log('Keyboard activated progress dot for step', stepNum);
                navigateToStepByDot(stepNum);
                return false;
            }
        }, true);
        
        // Also add mousedown for better mobile support
        newDot.addEventListener('mousedown', function(e) {
            e.preventDefault();
        });
    });
}

function attachStepListeners(stepKey) {
    // Disclaimer checkbox handlers
    if (stepKey === 'step5A') {
        const checkbox = document.getElementById('disclaimerAccept');
        if (checkbox) {
            checkbox.addEventListener('change', function(e) {
                document.getElementById('finalSubmitBtn').disabled = !e.target.checked;
                wizardState.data.disclaimerAccepted = e.target.checked;
            });
        }
    }
    
    if (stepKey === 'step6B') {
        const checkbox = document.getElementById('disclaimerAcceptB');
        if (checkbox) {
            checkbox.addEventListener('change', function(e) {
                document.getElementById('finalSubmitBtnB').disabled = !e.target.checked;
                wizardState.data.disclaimerAccepted = e.target.checked;
            });
        }
    }
    
    // Filter editor toggle
    if (stepKey === 'step3A') {
        const toggleBtn = document.querySelector('[onclick="toggleFilterEdit()"]');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleFilterEdit);
        }
    }
    
    // Lender search autocomplete
    if (stepKey === 'step2B') {
        // Setup lender dropdown similar to metro selector
        setupLenderDropdown();
    }
}

// Debounce variable for autocomplete
let autocompleteDebounceTimer = null;

// Perform autocomplete search
async function performAutocompleteSearch(query) {
    const dropdown = document.getElementById('lenderAutocomplete');
    const searchInput = document.getElementById('lenderSearch');
    
    if (!dropdown || !searchInput) return;
    
    try {
        // Show loading state
        dropdown.innerHTML = '<div class="autocomplete-item loading">Searching...</div>';
        dropdown.style.display = 'block';
        searchInput.setAttribute('aria-expanded', 'true');
        
        const results = await apiClient.searchLender(query);
        
        if (results.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-item no-results">No lenders found</div>';
            return;
        }
        
        // Display results with verification information
        dropdown.innerHTML = results.map((lender, index) => {
            const name = lender.name || lender.lender_name || 'Unknown';
            const location = lender.city && lender.state ? `${lender.city}, ${lender.state}` : '';
            const verification = lender.verification || {};
            const verificationSummary = lender.verification_summary || {};
            
            // Get verification confidence indicator
            let confidenceBadge = '';
            let confidenceClass = '';
            if (verificationSummary.confidence) {
                const confidence = verificationSummary.confidence;
                if (confidence === 'high') {
                    confidenceBadge = '<span class="verification-badge high" title="High confidence - verified with GLEIF and CFPB">✓ Verified</span>';
                    confidenceClass = 'verified-high';
                } else if (confidence === 'medium') {
                    confidenceBadge = '<span class="verification-badge medium" title="Medium confidence - some verification data available">⚠ Partial</span>';
                    confidenceClass = 'verified-medium';
                } else {
                    confidenceBadge = '<span class="verification-badge low" title="Low confidence - limited verification data">? Unverified</span>';
                    confidenceClass = 'verified-low';
                }
            }
            
            // Get distinguishing information
            let distinguishingInfo = [];
            
            // GLEIF headquarters
            if (verification.gleif && verification.gleif.headquarters) {
                const hq = verification.gleif.headquarters;
                if (hq.city || hq.state) {
                    const hqLocation = [hq.city, hq.state].filter(Boolean).join(', ');
                    if (hqLocation && hqLocation !== location) {
                        distinguishingInfo.push(`HQ: ${hqLocation}`);
                    }
                }
            }
            
            // CFPB assets
            if (verification.cfpb && verification.cfpb.assets) {
                const assets = verification.cfpb.assets;
                let assetsDisplay = '';
                if (typeof assets === 'number') {
                    if (assets >= 1000000000) {
                        assetsDisplay = `$${(assets / 1000000000).toFixed(1)}B`;
                    } else if (assets >= 1000000) {
                        assetsDisplay = `$${(assets / 1000000).toFixed(0)}M`;
                    } else {
                        assetsDisplay = `$${assets.toLocaleString()}`;
                    }
                } else {
                    assetsDisplay = String(assets);
                }
                distinguishingInfo.push(`Assets: ${assetsDisplay}`);
            }
            
            // LEI (always show for identification)
            if (lender.lei) {
                distinguishingInfo.push(`LEI: ${lender.lei.substring(0, 8)}...`);
            }
            
            // Warnings
            let warningsHtml = '';
            if (verificationSummary.has_warnings && verification.warnings && verification.warnings.length > 0) {
                warningsHtml = `<div class="verification-warnings" title="${verification.warnings.join('; ')}">
                    <i class="fas fa-exclamation-triangle"></i> ${verification.warnings.length} warning${verification.warnings.length > 1 ? 's' : ''}
                </div>`;
            }
            
            return `
                <div class="autocomplete-item ${confidenceClass}" 
                     data-lender-index="${index}"
                     role="option"
                     onclick="selectAutocompleteLender(${index})"
                     onmouseenter="highlightAutocompleteItem(this)">
                    <div class="autocomplete-item-header">
                        <div class="autocomplete-item-name">${name}</div>
                        ${confidenceBadge}
                    </div>
                    ${location ? `<div class="autocomplete-item-location">${location}</div>` : ''}
                    ${distinguishingInfo.length > 0 ? `<div class="autocomplete-item-distinguishing">${distinguishingInfo.join(' • ')}</div>` : ''}
                    ${warningsHtml}
                </div>
            `;
        }).join('');
        
        // Store results for selection
        window.currentAutocompleteResults = results;
        
    } catch (error) {
        console.error('Autocomplete error:', error);
        dropdown.innerHTML = '<div class="autocomplete-item error">Error searching lenders</div>';
    }
}

// Select a lender from autocomplete
function selectAutocompleteLender(index) {
    const results = window.currentAutocompleteResults;
    if (!results || !results[index]) return;
    
    const lender = results[index];
    selectLender(lender);
    hideAutocomplete();
    
    // Set the search input to the selected lender name
    const searchInput = document.getElementById('lenderSearch');
    if (searchInput) {
        searchInput.value = lender.name || lender.lender_name || '';
    }
    
    // Show the confirmation card
    const confirmation = document.getElementById('lenderConfirmation');
    if (confirmation) {
        confirmation.style.display = 'block';
    }
}

// Navigate autocomplete with keyboard
function navigateAutocomplete(direction) {
    const dropdown = document.getElementById('lenderAutocomplete');
    if (!dropdown || dropdown.style.display === 'none') return;
    
    const items = dropdown.querySelectorAll('.autocomplete-item:not(.loading):not(.no-results):not(.error)');
    if (items.length === 0) return;
    
    const current = dropdown.querySelector('.autocomplete-item.selected');
    let currentIndex = current ? Array.from(items).indexOf(current) : -1;
    
    currentIndex += direction;
    
    if (currentIndex < 0) currentIndex = items.length - 1;
    if (currentIndex >= items.length) currentIndex = 0;
    
    // Remove previous selection
    items.forEach(item => item.classList.remove('selected'));
    
    // Add selection to new item
    items[currentIndex].classList.add('selected');
    items[currentIndex].scrollIntoView({ block: 'nearest' });
}

// Highlight autocomplete item on hover
function highlightAutocompleteItem(element) {
    const dropdown = document.getElementById('lenderAutocomplete');
    if (!dropdown) return;
    
    const items = dropdown.querySelectorAll('.autocomplete-item');
    items.forEach(item => item.classList.remove('selected'));
    element.classList.add('selected');
}

// Hide autocomplete dropdown
function hideAutocomplete() {
    const dropdown = document.getElementById('lenderAutocomplete');
    const searchInput = document.getElementById('lenderSearch');
    
    if (dropdown) {
        dropdown.style.display = 'none';
    }
    if (searchInput) {
        searchInput.setAttribute('aria-expanded', 'false');
    }
}

// Make functions globally available
window.selectAutocompleteLender = selectAutocompleteLender;
window.highlightAutocompleteItem = highlightAutocompleteItem;

// Analysis type selection
function selectAnalysisType(type) {
    wizardState.analysisType = type;
    wizardState.data.analysisType = type;
    
    showLoading('Loading analysis options...');
    
    // Start loading metros immediately if going to area analysis
    // Load from static JSON file for instant loading
    if (type === 'area') {
        // Pre-load metros from static file before transitioning to step2A
        loadMetros();
    }
    
    setTimeout(() => {
        hideLoading();
        if (type === 'area') {
            transitionToStep('step2A');
        } else {
            transitionToStep('step2B');
        }
    }, 500);
}

// Navigation
function goBack() {
    const currentPath = wizardState.analysisType ? stepPaths[wizardState.analysisType] : ['step1'];
    const currentIndex = currentPath.findIndex(step => {
        const card = document.querySelector(`.step-card[data-step="${step}"]`);
        return card && card.classList.contains('active');
    });
    
    if (currentIndex > 0) {
        const prevStep = currentPath[currentIndex - 1];
        transitionToStep(prevStep, 'backward');
    }
}

function goToStep(stepNum) {
    const currentPath = wizardState.analysisType ? stepPaths[wizardState.analysisType] : ['step1'];
    if (stepNum > 0 && stepNum <= currentPath.length) {
        const targetStep = currentPath[stepNum - 1];
        transitionToStep(targetStep, 'backward');
    }
}

// Geography functions
async function loadStates() {
    try {
        const states = await apiClient.getStates();
        wizardState.cache.states = states;
        saveToCache('states', states);
        
        const select = document.getElementById('stateSelect');
        if (select) {
            select.innerHTML = '<option value="">Select a state...</option>';
            states.forEach(state => {
                const option = document.createElement('option');
                option.value = state.code;
                option.textContent = state.name;
                // Smart default: pre-select last used state
                if (wizardState.cache.lastState === state.code) {
                    option.selected = true;
                }
                select.appendChild(option);
            });
            
            // If last state was cached, load its counties
            if (wizardState.cache.lastState) {
                await loadCounties();
            }
        }
    } catch (error) {
        showError('Unable to load states. Please refresh the page.');
    }
}

async function loadMetros() {
    // Prevent multiple simultaneous loads
    if (wizardState.cache.loadingMetros) {
        return;
    }
    
    // Check if already loaded
    if (wizardState.cache.metros && wizardState.cache.metros.length > 0) {
        if (document.getElementById('metroSelect')) {
            setupMetroDropdown();
        }
        return;
    }
    
    try {
        wizardState.cache.loadingMetros = true;
        
        // Load from static JSON file first (fastest)
        try {
            const response = await fetch('/dataexplorer/static/data/metros.json');
            if (response.ok) {
                const data = await response.json();
                if (data.metros && data.metros.length > 0) {
                    // Metros are already sorted alphabetically from the file
                    wizardState.cache.metros = data.metros;
                    saveToCache('metros', data.metros);
                    wizardState.cache.loadingMetros = false;
                    
                    // Setup UI once metros are loaded (if DOM is ready)
                    if (document.getElementById('metroSelect')) {
                        setupMetroDropdown();
                    }
                    return;
                }
            }
        } catch (fileError) {
            console.warn('Could not load metros from static file, falling back to API:', fileError);
        }
        
        // Fallback to API if static file doesn't exist
        const metros = await apiClient.getMetros();
        // Sort metros alphabetically by name
        const sortedMetros = metros.sort((a, b) => a.name.localeCompare(b.name));
        wizardState.cache.metros = sortedMetros;
        saveToCache('metros', sortedMetros);
        wizardState.cache.loadingMetros = false;
        
        // Setup UI once metros are loaded (if DOM is ready)
        if (document.getElementById('metroSelect')) {
            setupMetroDropdown();
        }
    } catch (error) {
        wizardState.cache.loadingMetros = false;
        console.error('Error loading metros:', error);
        showError('Unable to load metros. Please refresh the page.');
    }
}

// LOCKED: Part of Area Analysis Structure
function setupMetroDropdown() {
    const select = document.getElementById('metroSelect');
    const selectButton = document.getElementById('metroSelectButton');
    const selectText = document.getElementById('metroSelectText');
    const searchInput = document.getElementById('metroSearch');
    const dropdown = document.getElementById('metroDropdown');
    const dropdownWrapper = document.querySelector('.metro-dropdown-wrapper');
    const sortedMetros = wizardState.cache.metros || [];
    
    if (!select || !selectButton || !selectText || !dropdown || !dropdownWrapper || sortedMetros.length === 0) {
        return;
    }
    
    // Clear existing options to avoid duplicates
    select.innerHTML = '<option value="">Select a metro area...</option>';
    
    // Populate select dropdown (alphabetically sorted) - hidden select for form submission
    sortedMetros.forEach(metro => {
        const option = document.createElement('option');
        option.value = metro.code;
        option.textContent = metro.name;
        if (wizardState.cache.lastMetro === metro.code) {
            option.selected = true;
            selectText.textContent = metro.name;
        }
        select.appendChild(option);
    });
    
    // Store metros for filtering (alphabetically sorted)
    wizardState.cache.filteredMetros = sortedMetros;
    
    // Remove existing event listeners by cloning (to avoid duplicates)
    const newButton = selectButton.cloneNode(true);
    selectButton.parentNode.replaceChild(newButton, selectButton);
    const newSelectButton = document.getElementById('metroSelectButton');
    
    // Show custom dropdown when button is clicked
    newSelectButton.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        showMetroDropdown();
    });
    
    newSelectButton.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            showMetroDropdown();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            showMetroDropdown();
            // Focus first item after dropdown opens
            setTimeout(() => {
                const searchInput = document.getElementById('metroSearch');
                if (searchInput) {
                    searchInput.focus();
                }
            }, 50);
        }
    });
    
    // Setup search functionality
    let searchTimeout;
    if (searchInput) {
        // Remove existing listeners
        const newSearchInput = searchInput.cloneNode(true);
        searchInput.parentNode.replaceChild(newSearchInput, searchInput);
        const newInput = document.getElementById('metroSearch');
        
        newInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            const query = e.target.value.toLowerCase().trim();
            
            searchTimeout = setTimeout(() => {
                const filtered = query.length === 0 
                    ? sortedMetros 
                    : sortedMetros.filter(metro => 
                        metro.name.toLowerCase().includes(query)
                    );
                renderMetroDropdown(filtered);
                // Reset selection after filtering
                wizardState.cache.selectedMetroIndex = -1;
            }, 100);
        });
        
        // Add keyboard navigation for search input
        newInput.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateMetroDropdown(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateMetroDropdown(-1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                selectHighlightedMetro();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideMetroDropdown();
                if (selectButton) {
                    selectButton.focus();
                }
            }
        });
        
        // Prevent dropdown from closing when clicking search box
        newInput.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
    
    // Hide dropdown when clicking outside (only set up once)
    if (!wizardState.cache.metroClickHandlerSet) {
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.metro-select-container')) {
                hideMetroDropdown();
            }
        });
        wizardState.cache.metroClickHandlerSet = true;
    }
    
    // Pre-render dropdown list so it's ready immediately when clicked
    renderMetroDropdown(sortedMetros);
}

function showMetroDropdown() {
    const dropdownWrapper = document.querySelector('.metro-dropdown-wrapper');
    const searchInput = document.getElementById('metroSearch');
    const searchBox = document.querySelector('.metro-search-box');
    const selectButton = document.getElementById('metroSelectButton');
    const selectContainer = document.querySelector('.metro-select-container');
    
    if (dropdownWrapper && selectContainer && selectButton) {
        // Get position of the select button
        const buttonRect = selectButton.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const spaceBelow = viewportHeight - buttonRect.bottom;
        const spaceAbove = buttonRect.top;
        
        // Calculate optimal height to show at least 10 items
        // Each item is approximately 30px (6px padding top + 6px padding bottom + ~18px text)
        const itemHeight = 30;
        const searchBoxHeight = 50; // Approximate height of search box
        const minHeight = (itemHeight * 10) + searchBoxHeight; // 10 items + search box
        const maxHeight = Math.min(spaceBelow - 20, spaceAbove - 20, 500); // Leave 20px margin
        
        // Position dropdown below the button using fixed positioning
        let topPosition = buttonRect.bottom + 4;
        let dropdownHeight = Math.max(minHeight, Math.min(maxHeight, 500));
        
        // If not enough space below, position above
        if (spaceBelow < minHeight && spaceAbove > spaceBelow) {
            topPosition = buttonRect.top - dropdownHeight - 4;
        }
        
        dropdownWrapper.style.top = topPosition + 'px';
        dropdownWrapper.style.left = buttonRect.left + 'px';
        dropdownWrapper.style.width = buttonRect.width + 'px';
        dropdownWrapper.style.height = dropdownHeight + 'px';
        
        // Make sure dropdown wrapper only shows search box and metro list
        dropdownWrapper.style.display = 'flex';
        dropdownWrapper.style.flexDirection = 'column';
        
        // Ensure search box is always visible and at the top
        if (searchBox) {
            searchBox.style.display = 'block';
            searchBox.style.visibility = 'visible';
            searchBox.style.opacity = '1';
            searchBox.style.position = 'relative';
        }
        
        // Hide any buttons that might have accidentally been included
        const buttonsInDropdown = dropdownWrapper.querySelectorAll('.btn-group, .btn');
        buttonsInDropdown.forEach(btn => {
            if (btn.closest('.metro-dropdown-wrapper')) {
                btn.style.display = 'none';
            }
        });
        
        if (selectButton) {
            selectButton.setAttribute('aria-expanded', 'true');
        }
        
        // Use cached metros if available (already loaded and pre-rendered)
        const allMetros = wizardState.cache.metros || [];
        if (allMetros.length > 0) {
            // Metros are already loaded and rendered, just show the dropdown
            // The list is already in the DOM from loadMetros()
        } else {
            // Fallback: if metros aren't loaded yet, load them now
            loadMetros();
        }
        
        // Auto-focus search input after a brief delay to ensure dropdown is rendered
        setTimeout(() => {
            if (searchInput) {
                searchInput.value = '';
                searchInput.focus();
                // Reset selection when opening dropdown
                wizardState.cache.selectedMetroIndex = -1;
            }
        }, 10);
    }
}

function hideMetroDropdown() {
    const dropdownWrapper = document.querySelector('.metro-dropdown-wrapper');
    const selectButton = document.getElementById('metroSelectButton');
    if (dropdownWrapper) {
        dropdownWrapper.style.display = 'none';
    }
    if (selectButton) {
        selectButton.setAttribute('aria-expanded', 'false');
    }
}

function renderMetroDropdown(metros) {
    const dropdown = document.getElementById('metroDropdown');
    if (!dropdown) return;
    
    dropdown.innerHTML = '';
    
    if (metros.length === 0) {
        dropdown.innerHTML = '<div class="metro-dropdown-item no-results">No metros found</div>';
        return;
    }
    
    // Store current metros for keyboard navigation
    wizardState.cache.currentMetros = metros;
    
    metros.forEach((metro, index) => {
        const item = document.createElement('div');
        item.className = 'metro-dropdown-item';
        item.textContent = metro.name;
        item.setAttribute('role', 'option');
        item.setAttribute('data-code', metro.code);
        item.setAttribute('data-name', metro.name);
        item.setAttribute('data-index', index);
        item.setAttribute('tabindex', '-1');
        
        item.addEventListener('click', function() {
            selectMetro(metro.code, metro.name);
        });
        
        // Add keyboard support for individual items
        item.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                selectMetro(metro.code, metro.name);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateMetroDropdown(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateMetroDropdown(-1);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideMetroDropdown();
                const selectButton = document.getElementById('metroSelectButton');
                if (selectButton) {
                    selectButton.focus();
                }
            }
        });
        
        dropdown.appendChild(item);
    });
    
    // Reset selection index when rendering
    wizardState.cache.selectedMetroIndex = -1;
}

// Navigate metro dropdown with keyboard
function navigateMetroDropdown(direction) {
    const dropdown = document.getElementById('metroDropdown');
    const dropdownWrapper = document.querySelector('.metro-dropdown-wrapper');
    if (!dropdown || !dropdownWrapper || dropdownWrapper.style.display === 'none') return;
    
    const items = dropdown.querySelectorAll('.metro-dropdown-item:not(.no-results)');
    if (items.length === 0) return;
    
    // Get current selected index or start at -1
    let currentIndex = wizardState.cache.selectedMetroIndex !== undefined 
        ? wizardState.cache.selectedMetroIndex 
        : -1;
    
    // Update index based on direction
    currentIndex += direction;
    
    // Wrap around
    if (currentIndex < 0) currentIndex = items.length - 1;
    if (currentIndex >= items.length) currentIndex = 0;
    
    // Remove previous selection
    items.forEach(item => item.classList.remove('selected'));
    
    // Add selection to new item
    if (items[currentIndex]) {
        items[currentIndex].classList.add('selected');
        items[currentIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        items[currentIndex].focus();
        wizardState.cache.selectedMetroIndex = currentIndex;
    }
}

// Select the currently highlighted metro
function selectHighlightedMetro() {
    const dropdown = document.getElementById('metroDropdown');
    if (!dropdown) return;
    
    const selectedItem = dropdown.querySelector('.metro-dropdown-item.selected');
    if (selectedItem) {
        const code = selectedItem.getAttribute('data-code');
        const name = selectedItem.getAttribute('data-name');
        selectMetro(code, name);
    } else {
        // If nothing is selected, select the first item
        const firstItem = dropdown.querySelector('.metro-dropdown-item:not(.no-results)');
        if (firstItem) {
            const code = firstItem.getAttribute('data-code');
            const name = firstItem.getAttribute('data-name');
            selectMetro(code, name);
        }
    }
}

// Select a metro (shared function for click and keyboard selection)
function selectMetro(code, name) {
    const select = document.getElementById('metroSelect');
    const selectButton = document.getElementById('metroSelectButton');
    const selectText = document.getElementById('metroSelectText');
    
    if (select && selectText) {
        select.value = code;
        selectText.textContent = name;
        if (selectButton) {
            selectButton.setAttribute('aria-expanded', 'false');
        }
        // Store selected metro
        wizardState.data.geography.cbsa = code;
        saveToCache('lastMetro', code);
    }
    hideMetroDropdown();
    
    // Reset selection index
    wizardState.cache.selectedMetroIndex = -1;
}

// LOCKED: Part of Area Analysis Structure
async function loadCountiesByMetro() {
    // Get CBSA code from either metroSelect dropdown or wizardState
    let cbsaCode;
    const select = document.getElementById('metroSelect');
    if (select && select.value) {
        cbsaCode = select.value;
    } else if (wizardState.data.geography.cbsa) {
        cbsaCode = wizardState.data.geography.cbsa;
    } else {
        return;
    }
    
    wizardState.data.geography.cbsa = cbsaCode;
    saveToCache('lastMetro', cbsaCode);
    
    showLoading('Loading counties...');
    
    try {
        const counties = await apiClient.getCountiesByMetro(cbsaCode);
        wizardState.cache.countiesByMetro = wizardState.cache.countiesByMetro || {};
        wizardState.cache.countiesByMetro[cbsaCode] = counties;
        
        const container = document.getElementById('countyCheckboxes');
        if (container) {
            container.innerHTML = '';
            
            if (counties.length === 0) {
                container.innerHTML = '<p style="color: #999;">No counties found for this metro area.</p>';
                hideLoading();
                return;
            }
            
            counties.forEach(county => {
                const fullFips = `${county.state_fips || ''}${county.fips || ''}`;
                const countyName = county.name || '';
                const stateName = county.state_name || '';
                const cbsa = county.cbsa || '';
                const cbsaName = county.cbsa_name || '';
                
                // Skip if essential data is missing
                if (!fullFips || !countyName || !stateName) {
                    console.warn('Skipping county with missing data:', county);
                    return;
                }
                
                // Remove "County" from county name if present
                let displayCountyName = countyName.replace(/\s+County\s*$/i, '').trim();
                
                // Get state abbreviation - comprehensive mapping for all US states
                const stateAbbrMap = {
                    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
                    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
                    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
                    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
                    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
                    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
                    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
                    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
                    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
                    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
                    'District of Columbia': 'DC'
                };
                const stateAbbr = stateAbbrMap[stateName] || stateName.substring(0, 2).toUpperCase();
                
                // Create chip element
                const chip = document.createElement('span');
                chip.className = 'county-chip';
                chip.setAttribute('data-fips', fullFips);
                chip.setAttribute('data-name', countyName);
                chip.setAttribute('data-state', stateName);
                chip.setAttribute('data-cbsa', cbsa);
                chip.setAttribute('data-cbsa-name', cbsaName);
                
                // Create hidden checkbox for form submission
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.value = fullFips;
                checkbox.checked = true;
                checkbox.style.display = 'none';
                checkbox.setAttribute('data-geoid', fullFips);
                checkbox.setAttribute('data-fips', county.fips || '');
                checkbox.setAttribute('data-name', countyName);
                checkbox.setAttribute('data-state', stateName);
                checkbox.setAttribute('data-cbsa', cbsa);
                checkbox.setAttribute('data-cbsa-name', cbsaName);
                checkbox.addEventListener('change', validateCountySelection);
                
                // Create text span
                const textSpan = document.createElement('span');
                textSpan.className = 'county-chip-text';
                textSpan.textContent = `${displayCountyName}, ${stateAbbr}`;
                
                // Create remove button
                const removeBtn = document.createElement('button');
                removeBtn.className = 'remove-chip';
                removeBtn.type = 'button';
                removeBtn.setAttribute('aria-label', `Remove ${countyName}, ${stateName}`);
                removeBtn.textContent = '×';
                removeBtn.onclick = function(e) {
                    e.stopPropagation();
                    removeCounty(fullFips);
                };
                
                // Append all elements
                chip.appendChild(checkbox);
                chip.appendChild(textSpan);
                chip.appendChild(removeBtn);
                container.appendChild(chip);
            });
            
            // Validate initial selection (all counties selected by default)
            validateCountySelection();
        }
        
        hideLoading();
    } catch (error) {
        hideLoading();
        showError('Unable to load counties. Please try again.');
    }
}

// LOCKED: Part of Area Analysis Structure
function removeCounty(fips) {
    const chip = document.querySelector(`#countyCheckboxes .county-chip[data-fips="${fips}"]`);
    const checkbox = chip ? chip.querySelector('input[type="checkbox"]') : null;
    
    if (chip && checkbox) {
        checkbox.checked = false;
        chip.remove();
        validateCountySelection();
    }
}

function selectAllCounties() {
    const checkboxes = document.querySelectorAll('#countyCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.checked = true;
    });
    // Re-render all counties as chips if they were removed
    const cbsaCode = wizardState.data.geography.cbsa;
    if (cbsaCode) {
        loadCountiesByMetro();
    }
    validateCountySelection();
}

function deselectAllCounties() {
    const checkboxes = document.querySelectorAll('#countyCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.checked = false;
    });
    // Remove all chips
    const container = document.getElementById('countyCheckboxes');
    if (container) {
        container.innerHTML = '';
    }
    validateCountySelection();
}

async function loadCounties() {
    const stateSelect = document.getElementById('stateSelect');
    if (!stateSelect || !stateSelect.value) return;
    
    const stateCode = stateSelect.value;
    wizardState.data.geography.state = stateCode;
    saveToCache('lastState', stateCode);
    
    showLoading('Loading counties...');
    
    try {
        const counties = await apiClient.getCounties(stateCode);
        wizardState.cache.counties[stateCode] = counties;
        
        const container = document.getElementById('countyCheckboxes');
        if (container) {
            container.innerHTML = '';
            
            if (counties.length === 0) {
                container.innerHTML = '<p style="color: #999;">No counties found for this state.</p>';
                return;
            }
            
            counties.forEach(county => {
                const label = document.createElement('label');
                label.className = 'checkbox-item';
                label.innerHTML = `
                    <input type="checkbox"
                           value="${county.geoid}"
                           data-name="${county.name}"
                           data-geoid="${county.geoid}"
                           data-fips="${county.fips}"
                           data-cbsa="${county.cbsa}"
                           data-cbsa-name="${county.cbsa_name}"
                           onchange="validateCountySelection()">
                    <span>${county.name} (${county.cbsa_name})</span>
                `;
                container.appendChild(label);
            });
            
            // Real-time validation listener
            container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.addEventListener('change', validateCountySelection);
            });
        }
        
        hideLoading();
    } catch (error) {
        hideLoading();
        showError('Unable to load counties. Please try again.');
    }
}

function validateCountySelection() {
    const selectedCounties = getSelectedCounties();
    const validation = validationRules.counties.validate(selectedCounties);
    
    const container = document.getElementById('countyCheckboxes');
    if (container) {
        validationRules.counties.showFeedback(container, validation);
    }
    
    return validation.valid;
}

// LOCKED: Part of Area Analysis Structure
async function confirmMetro() {
    const select = document.getElementById('metroSelect');
    const selectText = document.getElementById('metroSelectText');
    
    if (!select || !select.value) {
        if (!selectText || selectText.textContent === 'Select a metro area...') {
            showError('Please select a metro area');
            return;
        }
    }
    
    const cbsaCode = select.value;
    if (!cbsaCode) {
        showError('Please select a metro area');
        return;
    }
    
    wizardState.data.geography.cbsa = cbsaCode;
    
    // Load counties for the selected metro
    await loadCountiesByMetro();
    
    // Transition to step 3A (county selection)
    showStepSuccess(document.querySelector('.step-card.active'));
    setTimeout(() => {
        transitionToStep('step3A');
    }, 500);
}

// LOCKED: Part of Area Analysis Structure
function confirmGeography() {
    if (!validateCountySelection()) {
        return;
    }
    
    const selectedCounties = getSelectedCounties();
    if (selectedCounties.length === 0) {
        showError('Please select at least one county');
        return;
    }
    
    wizardState.data.geography.counties = selectedCounties.map(c => c.geoid);
    wizardState.data.geography.cbsa = selectedCounties[0].cbsa;
    wizardState.data.geography.cbsa_name = selectedCounties[0].cbsa_name;
    
    saveToCache('lastCounties', selectedCounties);
    
    showStepSuccess(document.querySelector('.step-card.active'));
    setTimeout(() => {
        transitionToStep('step4A');
    }, 500);
}

// Lender functions - Dropdown with search (similar to metro selector)
async function loadLenders() {
    // Check if lenders are already cached
    if (wizardState.cache.lenders && wizardState.cache.lenders.length > 0) {
        return wizardState.cache.lenders;
    }
    
    showLoading('Loading lenders...');
    
    try {
        const lenders = await apiClient.getAllLenders();
        
        // Lenders are already sorted by LAR count (descending) from the API
        // No need to sort again - use them as-is
        
        // Cache lenders
        wizardState.cache.lenders = lenders;
        wizardState.cache.filteredLenders = lenders;
        
        hideLoading();
        return lenders;
    } catch (error) {
        hideLoading();
        showError('Unable to load lenders. Please refresh the page.');
        return [];
    }
}

function setupLenderDropdown() {
    const select = document.getElementById('lenderSelect');
    const selectButton = document.getElementById('lenderSelectButton');
    const selectText = document.getElementById('lenderSelectText');
    const searchInput = document.getElementById('lenderSearch');
    const dropdown = document.getElementById('lenderDropdown');
    const dropdownWrapper = document.querySelector('.lender-dropdown-wrapper');
    
    if (!select || !selectButton || !selectText || !dropdown || !dropdownWrapper) {
        return;
    }
    
    // Load lenders if not already loaded
    loadLenders().then(lenders => {
        if (lenders.length > 0) {
            // Populate select dropdown
            select.innerHTML = '<option value="">Select a lender...</option>';
            lenders.forEach(lender => {
                const option = document.createElement('option');
                option.value = lender.lei || lender.lender_id || '';
                const lenderName = (lender.name || lender.lender_name || 'Unknown').toUpperCase();
                const city = lender.city || lender.respondent_city || '';
                const state = lender.state || lender.respondent_state || '';
                let displayText = lenderName;
                if (city && state) {
                    displayText = `${lenderName} (${city}, ${state})`;
                }
                option.textContent = displayText;
                select.appendChild(option);
            });
            
            // Pre-render dropdown list
            renderLenderDropdown(lenders);
        }
    });
    
    // Remove existing event listeners by cloning
    const newButton = selectButton.cloneNode(true);
    selectButton.parentNode.replaceChild(newButton, selectButton);
    const newSelectButton = document.getElementById('lenderSelectButton');
    
    // Show dropdown when button is clicked
    newSelectButton.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        showLenderDropdown();
    });
    
    newSelectButton.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            showLenderDropdown();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            showLenderDropdown();
            setTimeout(() => {
                const searchInput = document.getElementById('lenderSearch');
                if (searchInput) {
                    searchInput.focus();
                }
            }, 50);
        }
    });
    
    // Setup search functionality (filter from loaded list)
    if (searchInput) {
        const newSearchInput = searchInput.cloneNode(true);
        searchInput.parentNode.replaceChild(newSearchInput, searchInput);
        const newInput = document.getElementById('lenderSearch');
        
        let searchTimeout;
        newInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            const query = e.target.value.toLowerCase().trim();
            
            searchTimeout = setTimeout(() => {
                const allLenders = wizardState.cache.lenders || [];
                
                if (query.length === 0) {
                    wizardState.cache.filteredLenders = allLenders;
                } else {
                    // Filter lenders by name, city, or state
                    wizardState.cache.filteredLenders = allLenders.filter(lender => {
                        const name = (lender.name || lender.lender_name || '').toLowerCase();
                        const city = (lender.city || lender.respondent_city || '').toLowerCase();
                        const state = (lender.state || lender.respondent_state || '').toLowerCase();
                        const lei = (lender.lei || lender.lender_id || '').toLowerCase();
                        
                        return name.includes(query) || 
                               city.includes(query) || 
                               state.includes(query) ||
                               lei.includes(query);
                    });
                }
                
                renderLenderDropdown(wizardState.cache.filteredLenders);
                wizardState.cache.selectedLenderIndex = -1;
            }, 100);
        });
        
        newInput.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateLenderDropdown(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateLenderDropdown(-1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                selectHighlightedLender();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideLenderDropdown();
                if (newSelectButton) {
                    newSelectButton.focus();
                }
            }
        });
        
        newInput.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
    
    // Hide dropdown when clicking outside
    if (!wizardState.cache.lenderClickHandlerSet) {
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.lender-select-container')) {
                hideLenderDropdown();
            }
        });
        wizardState.cache.lenderClickHandlerSet = true;
    }
}

// This function is no longer needed - filtering is done client-side
// Keeping for backward compatibility but it's not used
async function performLenderSearch(query) {
    // Filtering is now done in setupLenderDropdown input handler
    // This function is kept for compatibility but not actively used
}

function showLenderDropdown() {
    const dropdownWrapper = document.querySelector('.lender-dropdown-wrapper');
    const selectButton = document.getElementById('lenderSelectButton');
    const selectContainer = document.querySelector('.lender-select-container');
    
    if (!dropdownWrapper || !selectContainer || !selectButton) {
        console.error('Lender dropdown elements not found');
        return;
    }
    
    // Get position of the select button (viewport coordinates)
    const buttonRect = selectButton.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const spaceBelow = viewportHeight - buttonRect.bottom;
    const spaceAbove = buttonRect.top;
    
    // Calculate optimal height
    const itemHeight = 30;
    const searchBoxHeight = 50;
    const minHeight = (itemHeight * 10) + searchBoxHeight;
    const maxHeight = Math.min(spaceBelow - 20, spaceAbove - 20, 500);
    
    // Position dropdown below the button using fixed positioning
    let topPosition = buttonRect.bottom + 4;
    let dropdownHeight = Math.max(minHeight, Math.min(maxHeight, 500));
    
    // If not enough space below, position above
    if (spaceBelow < minHeight && spaceAbove > spaceBelow) {
        topPosition = buttonRect.top - dropdownHeight - 4;
    }
    
    dropdownWrapper.style.position = 'fixed';
    dropdownWrapper.style.top = topPosition + 'px';
    dropdownWrapper.style.left = buttonRect.left + 'px';
    dropdownWrapper.style.width = buttonRect.width + 'px';
    dropdownWrapper.style.maxHeight = dropdownHeight + 'px';
    dropdownWrapper.style.flexDirection = 'column';
    dropdownWrapper.style.zIndex = '99999';
    dropdownWrapper.classList.add('show');
    
    if (selectButton) {
        selectButton.setAttribute('aria-expanded', 'true');
    }
    
    // Show all lenders or filtered list
    const lendersToShow = wizardState.cache.filteredLenders || wizardState.cache.lenders || [];
    renderLenderDropdown(lendersToShow);
    
    // Auto-focus search input after dropdown is shown
    setTimeout(() => {
        const searchInput = document.getElementById('lenderSearch');
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
            wizardState.cache.selectedLenderIndex = -1;
        }
    }, 50);
}

function hideLenderDropdown() {
    const dropdownWrapper = document.querySelector('.lender-dropdown-wrapper');
    const selectButton = document.getElementById('lenderSelectButton');
    
    if (dropdownWrapper) {
        dropdownWrapper.classList.remove('show');
    }
    
    if (selectButton) {
        selectButton.setAttribute('aria-expanded', 'false');
    }
}

function renderLenderDropdown(lenders) {
    const dropdown = document.getElementById('lenderDropdown');
    if (!dropdown) return;
    
    dropdown.innerHTML = '';
    
    if (lenders.length === 0) {
        dropdown.innerHTML = '<div class="lender-dropdown-item no-results">No lenders found. Try a different search term.</div>';
        return;
    }
    
    // Store current lenders for keyboard navigation
    wizardState.cache.currentLenders = lenders;
    
    lenders.forEach((lender, index) => {
        const item = document.createElement('div');
        item.className = 'lender-dropdown-item';

        // Format: LENDER NAME (City, State if available)
        const lenderName = (lender.name || lender.lender_name || 'Unknown').toUpperCase();
        const city = lender.city || lender.respondent_city || '';
        const state = lender.state || lender.respondent_state || '';
        const lenderType = lender.type || lender.type_name || '';

        // Determine institution category (depository = has branches, non-depository = no branches)
        const institutionInfo = getInstitutionCategory(lenderType);

        // Display just the name if city/state not available (they'll be looked up after selection)
        let locationText = '';
        if (city && state) {
            locationText = `(${city}, ${state})`;
        } else if (city) {
            locationText = `(${city})`;
        } else if (state) {
            locationText = `(${state})`;
        }

        // Build HTML with institution type badge
        item.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; width: 100%;">
                <span style="flex: 1; font-weight: 500;">${lenderName}</span>
                ${institutionInfo.badge}
            </div>
            ${locationText ? `<div style="font-size: 0.8rem; color: #666; margin-top: 2px;">${locationText}</div>` : ''}
        `;
        item.setAttribute('role', 'option');
        item.setAttribute('data-index', index);
        item.setAttribute('tabindex', '-1');
        
        item.addEventListener('click', function() {
            selectLender(lender);
        });
        
        // Add keyboard support
        item.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                selectLender(lender);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateLenderDropdown(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateLenderDropdown(-1);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideLenderDropdown();
                const selectButton = document.getElementById('lenderSelectButton');
                if (selectButton) {
                    selectButton.focus();
                }
            }
        });
        
        dropdown.appendChild(item);
    });
    
    // Reset selection index
    wizardState.cache.selectedLenderIndex = -1;
}

function navigateLenderDropdown(direction) {
    const dropdown = document.getElementById('lenderDropdown');
    const dropdownWrapper = document.querySelector('.lender-dropdown-wrapper');
    if (!dropdown || !dropdownWrapper || dropdownWrapper.style.display === 'none') return;
    
    const items = dropdown.querySelectorAll('.lender-dropdown-item:not(.no-results)');
    if (items.length === 0) return;
    
    let currentIndex = wizardState.cache.selectedLenderIndex !== undefined 
        ? wizardState.cache.selectedLenderIndex 
        : -1;
    
    currentIndex += direction;
    
    if (currentIndex < 0) currentIndex = items.length - 1;
    if (currentIndex >= items.length) currentIndex = 0;
    
    items.forEach(item => item.classList.remove('selected'));
    
    if (items[currentIndex]) {
        items[currentIndex].classList.add('selected');
        items[currentIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        items[currentIndex].focus();
        wizardState.cache.selectedLenderIndex = currentIndex;
    }
}

function selectHighlightedLender() {
    const dropdown = document.getElementById('lenderDropdown');
    if (!dropdown) return;
    
    const selectedItem = dropdown.querySelector('.lender-dropdown-item.selected');
    if (selectedItem) {
        const index = parseInt(selectedItem.getAttribute('data-index'));
        const lenders = wizardState.cache.currentLenders || [];
        if (lenders[index]) {
            selectLender(lenders[index]);
        }
    }
}

async function selectLender(lender) {
    const select = document.getElementById('lenderSelect');
    const selectButton = document.getElementById('lenderSelectButton');
    const selectText = document.getElementById('lenderSelectText');
    
    // Format: LENDER NAME (City, State) - all caps
    const lenderName = (lender.name || lender.lender_name || 'Unknown').toUpperCase();
    const city = lender.city || lender.respondent_city || '';
    const state = lender.state || lender.respondent_state || '';
    const lenderLEI = lender.lei || lender.lender_id || '';
    
    let displayText = lenderName;
    if (city && state) {
        displayText = `${lenderName} (${city}, ${state})`;
    } else if (city) {
        displayText = `${lenderName} (${city})`;
    } else if (state) {
        displayText = `${lenderName} (${state})`;
    }
    
    if (select && selectText) {
        // Create a temporary option for the selected lender
        select.innerHTML = '';
        const option = document.createElement('option');
        option.value = lenderLEI || lenderName;
        option.textContent = displayText;
        option.selected = true;
        select.appendChild(option);
        
        selectText.textContent = displayText;
        if (selectButton) {
            selectButton.setAttribute('aria-expanded', 'false');
        }
        
        // Helper function to pad RSSD to 10 digits
        function padRSSD(rssd) {
            if (!rssd) return null;
            const rssdStr = String(rssd).trim();
            if (rssdStr === '') return null;
            // Pad to 10 digits with leading zeros
            return rssdStr.padStart(10, '0');
        }
        
        // Store selected lender with all identifiers
        // LEI is for HMDA data, RSSD is for branch/CBSA data, SB_RESID is for small business loan data
        const rawRSSD = lender.rssd || lender.rssd_id || lender.respondent_rssd;
        wizardState.data.lender = {
            name: lenderName,
            lei: lenderLEI,  // For HMDA data queries
            rssd: padRSSD(rawRSSD),  // For branch/CBSA queries (padded to 10 digits)
            sb_resid: lender.sb_resid || lender.sb_rssd,  // For small business loan data queries
            type: lender.type || lender.type_name,  // Use type_name if type is not available
            type_name: lender.type_name || lender.type,  // Also store type_name
            city: city,
            state: state,
            sb_rssd: lender.sb_rssd  // Keep for backward compatibility if needed
        };
        
        // Use LEI to look up RSSD and SB_RESID if not already present
        // This ensures we have all three identifiers for different data sources
        if (lenderLEI && (!wizardState.data.lender.rssd || !wizardState.data.lender.sb_resid)) {
            try {
                console.log('Fetching lender details for LEI:', lenderLEI);
                const details = await apiClient.getLenderDetailsByLei(lenderLEI);
                console.log('Received lender details (full object):', JSON.stringify(details, null, 2));
                console.log('Details keys:', details ? Object.keys(details) : 'null');
                if (details) {
                    // RSSD is used to select CBSAs with branches (must be 10-digit padded)
                    if (details.rssd && !wizardState.data.lender.rssd) {
                        wizardState.data.lender.rssd = padRSSD(details.rssd);
                        console.log('Set RSSD to:', wizardState.data.lender.rssd);
                    }
                    // SB_RESID is used to select small business loan data
                    // Check multiple possible property names
                    const sbResid = details.sb_resid || details.sbResid || details.SB_RESID || details.respondent_id;
                    if (sbResid && !wizardState.data.lender.sb_resid) {
                        wizardState.data.lender.sb_resid = sbResid;
                        console.log('Set SB_RESID to:', wizardState.data.lender.sb_resid);
                    } else {
                        console.warn('SB_RESID not found in details. Available keys:', Object.keys(details));
                        console.warn('Details object:', details);
                    }
                    // Update lender type from API if available
                    if (details.type_name || details.type) {
                        wizardState.data.lender.type = details.type_name || details.type;
                        console.log('Set lender type to:', wizardState.data.lender.type);
                    }
                } else {
                    console.warn('No details returned from API');
                }
            } catch (error) {
                console.error('Could not look up additional lender info:', error);
            }
        }
        
        // Log the stored identifiers for debugging
        console.log('Lender identifiers stored:', {
            lei: wizardState.data.lender.lei,  // For HMDA
            rssd: wizardState.data.lender.rssd,  // For branches/CBSAs (10-digit padded)
            sb_resid: wizardState.data.lender.sb_resid,  // For small business loans
            type: wizardState.data.lender.type  // Lender type
        });
        
        // Update branch option state immediately based on lender type
        updateBranchOptionState();
        
        // Fetch GLEIF data and display lender information (but don't wait for it)
        // User will trigger GLEIF confirmation when they click "Confirm"
        displayLenderInfo(lenderLEI, lenderName, wizardState.data.lender);
        
        // Also fetch and store GLEIF addresses for confirmation display
        if (lenderLEI) {
            try {
                const gleifData = await apiClient.getGLEIFDataByLei(lenderLEI);
                if (gleifData) {
                    // Store in wizard state for later use
                    wizardState.data.lender.gleif_data = gleifData;
                    
                    // Update lender data with addresses for confirmation
                    if (gleifData.legal_address) {
                        wizardState.data.lender.legal_address = gleifData.legal_address;
                    }
                    if (gleifData.headquarters_address) {
                        wizardState.data.lender.headquarters_address = gleifData.headquarters_address;
                    }
                }
            } catch (error) {
                console.warn('Could not fetch GLEIF data for confirmation:', error);
            }
        }
        
        // Reset GLEIF confirmed state when a new lender is selected
        gleifConfirmed = false;
        
        saveToCache('lastLender', lenderLEI || lenderName);
    }
    
    hideLenderDropdown();
    wizardState.cache.selectedLenderIndex = -1;
}

// Update branch option state based on lender type and RSSD availability
function updateBranchOptionState() {
    const lenderType = wizardState.data.lender?.type || wizardState.data.lender?.type_name || '';
    const lenderTypeLower = lenderType.toLowerCase();
    const lenderRssd = wizardState.data.lender?.rssd;

    // Check if lender is a bank (contains "bank" or "affiliate" in type name)
    // OR has an RSSD number (which indicates they have branch data)
    const isBankByType = lenderTypeLower.includes('bank') || lenderTypeLower.includes('affiliate');
    const hasRssd = lenderRssd && lenderRssd.trim() !== '' && lenderRssd !== '0000000000';
    const canUseBranchOption = isBankByType || hasRssd;

    console.log('[updateBranchOptionState] lenderType:', lenderType, 'rssd:', lenderRssd, 'isBankByType:', isBankByType, 'hasRssd:', hasRssd, 'canUseBranchOption:', canUseBranchOption);

    const branchOption = document.querySelector('input[name="geoScope"][value="branch_cbsas"]');
    const branchLabel = branchOption?.closest('label');

    if (branchOption) {
        if (!canUseBranchOption) {
            // Cannot use branch option - disable it
            branchOption.disabled = true;
            branchOption.setAttribute('aria-disabled', 'true');

            // If branch_cbsas is currently selected, clear it and select all_cbsas instead
            if (branchOption.checked) {
                branchOption.checked = false;
                const allCbsasOption = document.querySelector('input[name="geoScope"][value="all_cbsas"]');
                if (allCbsasOption) {
                    allCbsasOption.checked = true;
                }
            }
        } else {
            // Can use branch option - enable it
            branchOption.disabled = false;
            branchOption.removeAttribute('aria-disabled');
        }
    }

    if (branchLabel) {
        if (!canUseBranchOption) {
            branchLabel.style.opacity = '0.5';
            branchLabel.style.cursor = 'not-allowed';
            branchLabel.title = 'Branch data is only available for banks with RSSD';
        } else {
            branchLabel.style.opacity = '1';
            branchLabel.style.cursor = 'pointer';
            branchLabel.title = '';
        }
    }
}

// Track GLEIF loading state
let gleifLoadingPromise = null;

async function displayLenderInfo(lei, name, lenderData) {
    const infoBlock = document.getElementById('lenderInfoBlock');
    const infoContent = document.getElementById('lenderInfoContent');
    
    if (!infoBlock || !infoContent) return;
    
    // Show loading state
    infoContent.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;"><i class="fas fa-spinner fa-spin"></i> Loading lender information...</div>';
    infoBlock.style.display = 'block';
    
    try {
        // Fetch GLEIF data from our BigQuery table (addresses and relationships)
        let gleifTableData = null;
        let gleifData = null;
        let gleifStatus = 'unknown';
        let legalCity = '';
        let legalState = '';
        let hqCity = '';
        let hqState = '';
        
        if (lei) {
            try {
                // Fetch from our lender_names_gleif table (faster, includes addresses and relationships)
                gleifTableData = await apiClient.getGLEIFDataByLei(lei);
                
                if (gleifTableData) {
                    legalCity = (gleifTableData.legal_address?.city || '').trim();
                    legalState = (gleifTableData.legal_address?.state || '').trim();
                    hqCity = (gleifTableData.headquarters_address?.city || '').trim();
                    hqState = (gleifTableData.headquarters_address?.state || '').trim();
                    
                    // Clean up state codes (remove "US-" prefix if present)
                    if (legalState && legalState.startsWith('US-')) {
                        legalState = legalState.substring(3);
                    }
                    if (hqState && hqState.startsWith('US-')) {
                        hqState = hqState.substring(3);
                    }
                }
                
                // Also fetch from GLEIF API for status verification (legacy, but still useful)
                try {
                    gleifLoadingPromise = apiClient.verifyGLEIF(lei, name);
                    const gleifResult = await gleifLoadingPromise;
                    if (gleifResult.success && gleifResult.data) {
                        gleifData = gleifResult.data;
                        gleifStatus = gleifData.is_active ? 'active' : 'inactive';
                    }
                } catch (gleifApiError) {
                    console.warn('Could not fetch GLEIF API data (using table data only):', gleifApiError);
                    // If we have table data, assume active
                    if (gleifTableData) {
                        gleifStatus = 'active';
                    }
                } finally {
                    gleifLoadingPromise = null;
                }
            } catch (error) {
                console.warn('Could not fetch GLEIF table data:', error);
            }
        }
        
        // Fetch assets from CFPB API if lender is a bank or credit union
        let lenderAssets = null;
        const lenderType = lenderData.type || lenderData.type_name || '';
        const lenderTypeLower = lenderType.toLowerCase();
        const isBank = lenderTypeLower.includes('bank') || lenderTypeLower.includes('affiliate');
        const isCreditUnion = lenderTypeLower.includes('credit union') || lenderTypeLower.includes('cu ');
        const isBankOrCreditUnion = isBank || isCreditUnion;
        
        if (lei && isBankOrCreditUnion) {
            try {
                lenderAssets = await apiClient.getLenderAssets(lei);
                if (lenderAssets !== null && lenderAssets !== undefined) {
                    console.log('Lender assets fetched:', lenderAssets);
                    // CFPB API returns -1 for non-banks/credit unions, treat as not available
                    if (lenderAssets === -1 || lenderAssets < 0) {
                        lenderAssets = null;
                        console.log('Assets value is -1 (not applicable for this institution type)');
                    }
                }
            } catch (error) {
                console.warn('Could not fetch lender assets:', error);
            }
        }
        
        // Build info display
        infoContent.innerHTML = '';

        // Institution Type (Bank vs Non-Bank) - with branch availability indicator
        const institutionInfo = getInstitutionCategory(lenderType);
        if (institutionInfo.category !== 'unknown') {
            const typeItem = document.createElement('div');
            typeItem.className = 'lender-info-item';
            typeItem.innerHTML = `
                <div class="lender-info-label">Institution Type</div>
                <div class="lender-info-value" style="display: flex; align-items: center; gap: 8px;">
                    ${institutionInfo.badge}
                    <span style="font-size: 0.8rem; color: #666;">
                        ${institutionInfo.hasBranches ? '(Has physical branches)' : '(No branch network)'}
                    </span>
                </div>
            `;
            infoContent.appendChild(typeItem);
        }

        // LEI (used for HMDA data queries) - with GLEIF lookup link
        if (lei) {
            // Direct link to the lender's LEI record on GLEIF
            const gleifUrl = `https://www.gleif.org/en/lei/search/#/record/${lei}`;
            const leiItem = createInfoItemWithLink('LEI (HMDA)', lei, gleifUrl, 'View on GLEIF');
            infoContent.appendChild(leiItem);
        }
        
        // Assets (only for banks and credit unions, and only if value is valid)
        if (isBankOrCreditUnion) {
            let assetsDisplay = 'Not available';
            let showAssets = false;
            
            if (lenderAssets !== null && lenderAssets !== undefined && lenderAssets >= 0) {
                showAssets = true;
                if (typeof lenderAssets === 'number') {
                    if (lenderAssets >= 1000000000) {
                        assetsDisplay = `$${(lenderAssets / 1000000000).toFixed(2)}B`;
                    } else if (lenderAssets >= 1000000) {
                        assetsDisplay = `$${(lenderAssets / 1000000).toFixed(2)}M`;
                    } else if (lenderAssets >= 1000) {
                        assetsDisplay = `$${(lenderAssets / 1000).toFixed(2)}K`;
                    } else {
                        assetsDisplay = `$${lenderAssets.toLocaleString()}`;
                    }
                } else {
                    assetsDisplay = String(lenderAssets);
                }
            } else if (lenderAssets === -1) {
                // Assets returned -1, meaning not applicable for this institution type
                assetsDisplay = 'Not applicable';
            }
            
            const assetsItem = createInfoItem('Assets (HMDA)', assetsDisplay);
            if (!showAssets) {
                assetsItem.querySelector('.lender-info-value').style.color = '#999';
                assetsItem.querySelector('.lender-info-value').style.fontStyle = 'italic';
            }
            infoContent.appendChild(assetsItem);
        }
        
        // RSSD (used to select CBSAs with branches) - with FFIEC lookup link
        if (lenderData.rssd) {
            const rssdItem = createInfoItemWithLink('RSSD (Branches)', lenderData.rssd, 'https://www.ffiec.gov/NPW', 'Lookup RSSD');
            infoContent.appendChild(rssdItem);
        }
        
        // Respondent ID / SB_RESID (used to select small business loan data) - with FFIEC lookup link
        if (lenderData.sb_resid) {
            const residItem = createInfoItemWithLink('Respondent ID (Small Business)', lenderData.sb_resid, 'https://www.ffiec.gov/craadweb/DisRptMain.aspx', 'View Report');
            infoContent.appendChild(residItem);
        } else {
            // Show message if SB_RESID is not available
            const residItem = createInfoItem('Respondent ID (Small Business)', 'Not found');
            residItem.querySelector('.lender-info-value').style.color = '#999';
            residItem.querySelector('.lender-info-value').style.fontStyle = 'italic';
            infoContent.appendChild(residItem);
        }
        
        // GLEIF Status
        if (lei) {
            const statusItem = document.createElement('div');
            statusItem.className = 'lender-info-item';
            
            const statusLabel = document.createElement('div');
            statusLabel.className = 'lender-info-label';
            statusLabel.textContent = 'GLEIF Status';
            statusItem.appendChild(statusLabel);
            
            const statusValue = document.createElement('div');
            statusValue.className = 'lender-info-status';
            statusValue.classList.add(gleifStatus);
            
            let statusText = '';
            let statusIcon = '';
            if (gleifStatus === 'active') {
                statusText = 'Active';
                statusIcon = '<i class="fas fa-check-circle"></i>';
            } else if (gleifStatus === 'inactive') {
                statusText = 'Inactive';
                statusIcon = '<i class="fas fa-times-circle"></i>';
            } else {
                statusText = 'Unknown';
                statusIcon = '<i class="fas fa-question-circle"></i>';
            }
            
            statusValue.innerHTML = `${statusIcon} ${statusText}`;
            statusItem.appendChild(statusValue);
            infoContent.appendChild(statusItem);
        }
        
        // GLEIF Legal Address
        if (gleifTableData) {
            const legalLocation = [legalCity, legalState].filter(Boolean).join(', ');
            const legalItem = createInfoItem('Legal Address', legalLocation || 'Not available');
            if (!legalCity && !legalState) {
                legalItem.querySelector('.lender-info-value').style.color = '#999';
                legalItem.querySelector('.lender-info-value').style.fontStyle = 'italic';
            }
            infoContent.appendChild(legalItem);
        } else if (lei) {
            const legalItem = createInfoItem('Legal Address', 'Not available');
            legalItem.querySelector('.lender-info-value').style.color = '#999';
            legalItem.querySelector('.lender-info-value').style.fontStyle = 'italic';
            infoContent.appendChild(legalItem);
        }
        
        // GLEIF Headquarters Address
        if (gleifTableData) {
            const hqLocation = [hqCity, hqState].filter(Boolean).join(', ');
            const hqItem = createInfoItem('Headquarters Address', hqLocation || 'Not available');
            if (!hqCity && !hqState) {
                hqItem.querySelector('.lender-info-value').style.color = '#999';
                hqItem.querySelector('.lender-info-value').style.fontStyle = 'italic';
            }
            infoContent.appendChild(hqItem);
        } else if (lei) {
            const hqItem = createInfoItem('Headquarters Address', 'Not available');
            hqItem.querySelector('.lender-info-value').style.color = '#999';
            hqItem.querySelector('.lender-info-value').style.fontStyle = 'italic';
            infoContent.appendChild(hqItem);
        }
        
        // Parent/Child Relationships
        if (gleifTableData) {
            const hasParent = gleifTableData.direct_parent || gleifTableData.ultimate_parent;
            const hasChildren = (gleifTableData.direct_children && gleifTableData.direct_children.length > 0) ||
                               (gleifTableData.ultimate_children && gleifTableData.ultimate_children.length > 0);
            
            if (hasParent || hasChildren) {
                const relationshipsDiv = document.createElement('div');
                relationshipsDiv.className = 'lender-info-item';
                relationshipsDiv.style.borderTop = '2px solid #e0e0e0';
                relationshipsDiv.style.paddingTop = '12px';
                relationshipsDiv.style.marginTop = '12px';
                
                const relationshipsLabel = document.createElement('div');
                relationshipsLabel.className = 'lender-info-label';
                relationshipsLabel.textContent = 'Corporate Structure';
                relationshipsDiv.appendChild(relationshipsLabel);
                
                const relationshipsContent = document.createElement('div');
                relationshipsContent.className = 'lender-info-value';
                relationshipsContent.style.fontSize = '0.9rem';
                
                // Direct Parent
                if (gleifTableData.direct_parent) {
                    const parentDiv = document.createElement('div');
                    parentDiv.style.marginBottom = '8px';
                    parentDiv.innerHTML = `<strong>Direct Parent:</strong> ${gleifTableData.direct_parent.name || 'N/A'}`;
                    if (gleifTableData.direct_parent.lei) {
                        const leiLink = document.createElement('a');
                        leiLink.href = `https://www.gleif.org/en/lei/search/#/record/${gleifTableData.direct_parent.lei}`;
                        leiLink.target = '_blank';
                        leiLink.textContent = ` (LEI: ${gleifTableData.direct_parent.lei})`;
                        leiLink.style.color = '#0066cc';
                        leiLink.style.textDecoration = 'none';
                        leiLink.style.marginLeft = '4px';
                        parentDiv.appendChild(leiLink);
                    }
                    relationshipsContent.appendChild(parentDiv);
                }
                
                // Ultimate Parent
                if (gleifTableData.ultimate_parent && 
                    (!gleifTableData.direct_parent || 
                     gleifTableData.ultimate_parent.lei !== gleifTableData.direct_parent.lei)) {
                    const ultimateParentDiv = document.createElement('div');
                    ultimateParentDiv.style.marginBottom = '8px';
                    ultimateParentDiv.innerHTML = `<strong>Ultimate Parent:</strong> ${gleifTableData.ultimate_parent.name || 'N/A'}`;
                    if (gleifTableData.ultimate_parent.lei) {
                        const leiLink = document.createElement('a');
                        leiLink.href = `https://www.gleif.org/en/lei/search/#/record/${gleifTableData.ultimate_parent.lei}`;
                        leiLink.target = '_blank';
                        leiLink.textContent = ` (LEI: ${gleifTableData.ultimate_parent.lei})`;
                        leiLink.style.color = '#0066cc';
                        leiLink.style.textDecoration = 'none';
                        leiLink.style.marginLeft = '4px';
                        ultimateParentDiv.appendChild(leiLink);
                    }
                    relationshipsContent.appendChild(ultimateParentDiv);
                }
                
                // Direct Children
                if (gleifTableData.direct_children && gleifTableData.direct_children.length > 0) {
                    const childrenDiv = document.createElement('div');
                    childrenDiv.style.marginTop = '8px';
                    childrenDiv.innerHTML = `<strong>Direct Children (${gleifTableData.direct_children.length}):</strong>`;
                    const childrenList = document.createElement('ul');
                    childrenList.style.margin = '4px 0 0 20px';
                    childrenList.style.paddingLeft = '16px';
                    gleifTableData.direct_children.slice(0, 5).forEach(child => {
                        const li = document.createElement('li');
                        li.textContent = child.name || child.lei || 'Unknown';
                        childrenList.appendChild(li);
                    });
                    if (gleifTableData.direct_children.length > 5) {
                        const li = document.createElement('li');
                        li.style.fontStyle = 'italic';
                        li.textContent = `... and ${gleifTableData.direct_children.length - 5} more`;
                        childrenList.appendChild(li);
                    }
                    childrenDiv.appendChild(childrenList);
                    relationshipsContent.appendChild(childrenDiv);
                }
                
                relationshipsDiv.appendChild(relationshipsContent);
                infoContent.appendChild(relationshipsDiv);
            }
        }
        
        // Show verification warnings if available
        if (lenderData.verification && lenderData.verification.warnings && lenderData.verification.warnings.length > 0) {
            const warningsDiv = document.createElement('div');
            warningsDiv.className = 'lender-info-item';
            warningsDiv.style.borderTop = '2px solid #ffc107';
            warningsDiv.style.paddingTop = '12px';
            warningsDiv.style.marginTop = '12px';
            
            const warningsLabel = document.createElement('div');
            warningsLabel.className = 'lender-info-label';
            warningsLabel.innerHTML = '<i class="fas fa-exclamation-triangle" style="color: #856404;"></i> Verification Warnings';
            warningsDiv.appendChild(warningsLabel);
            
            const warningsList = document.createElement('ul');
            warningsList.style.margin = '8px 0 0 0';
            warningsList.style.paddingLeft = '20px';
            warningsList.style.color = '#856404';
            warningsList.style.fontSize = '0.9rem';
            
            lenderData.verification.warnings.forEach(warning => {
                const li = document.createElement('li');
                li.textContent = warning;
                warningsList.appendChild(li);
            });
            
            warningsDiv.appendChild(warningsList);
            infoContent.appendChild(warningsDiv);
        }
        
    } catch (error) {
        console.error('Error displaying lender info:', error);
        infoContent.innerHTML = '<div style="color: #dc3545; padding: 10px;">Error loading lender information</div>';
    }
}

function createInfoItem(label, value) {
    const item = document.createElement('div');
    item.className = 'lender-info-item';
    
    const labelEl = document.createElement('div');
    labelEl.className = 'lender-info-label';
    labelEl.textContent = label;
    
    const valueEl = document.createElement('div');
    valueEl.className = 'lender-info-value';
    valueEl.textContent = value || 'N/A';
    
    item.appendChild(labelEl);
    item.appendChild(valueEl);
    
    return item;
}

function createInfoItemWithLink(label, value, linkUrl, linkText) {
    const item = document.createElement('div');
    item.className = 'lender-info-item';
    
    const labelEl = document.createElement('div');
    labelEl.className = 'lender-info-label';
    labelEl.textContent = label;
    
    const valueContainer = document.createElement('div');
    valueContainer.style.display = 'flex';
    valueContainer.style.alignItems = 'center';
    valueContainer.style.gap = '8px';
    
    const valueEl = document.createElement('div');
    valueEl.className = 'lender-info-value';
    valueEl.textContent = value || 'N/A';
    valueEl.style.flex = '1';
    
    const linkEl = document.createElement('a');
    linkEl.href = linkUrl;
    linkEl.target = '_blank';
    linkEl.rel = 'noopener noreferrer';
    linkEl.textContent = linkText || 'View';
    linkEl.className = 'lender-info-link';
    linkEl.style.cssText = 'font-size: 0.75rem; color: var(--ncrc-primary-blue); text-decoration: none; padding: 2px 6px; border: 1px solid var(--ncrc-primary-blue); border-radius: 4px; white-space: nowrap; transition: all 0.2s;';
    linkEl.addEventListener('mouseenter', function() {
        linkEl.style.backgroundColor = 'var(--ncrc-primary-blue)';
        linkEl.style.color = 'white';
    });
    linkEl.addEventListener('mouseleave', function() {
        linkEl.style.backgroundColor = 'transparent';
        linkEl.style.color = 'var(--ncrc-primary-blue)';
    });
    
    valueContainer.appendChild(valueEl);
    valueContainer.appendChild(linkEl);
    
    item.appendChild(labelEl);
    item.appendChild(valueContainer);
    
    return item;
}

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

// Track if GLEIF has been confirmed and user can proceed
let gleifConfirmed = false;

async function confirmLender() {
    const validation = validateLenderSearch();
    if (!validation.valid) {
        showError(validation.message);
        return;
    }
    
    // If GLEIF is already confirmed, proceed to next step
    if (gleifConfirmed) {
        showStepSuccess(document.querySelector('.step-card.active'));
        setTimeout(() => {
            transitionToStep('step3B');
        }, 500);
        return;
    }
    
    // First click: Load and display GLEIF info, then enable Continue button
    const nextButton = document.querySelector('.card-header-buttons .btn-primary');
    if (nextButton) {
        nextButton.disabled = true;
        nextButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading GLEIF verification...';
    }
    
    // Ensure lender info block is visible
    const infoBlock = document.getElementById('lenderInfoBlock');
    if (infoBlock) {
        infoBlock.style.display = 'block';
    }
    
    // Wait for GLEIF data to finish loading if it's still in progress
    if (gleifLoadingPromise) {
        try {
            await gleifLoadingPromise;
            // Give a moment for the UI to update with GLEIF data
            await new Promise(resolve => setTimeout(resolve, 300));
        } catch (error) {
            console.warn('GLEIF loading completed with error:', error);
        }
    } else {
        // If GLEIF wasn't loading, trigger it now
        const lei = wizardState.data.lender?.lei;
        const name = wizardState.data.lender?.name;
        if (lei && name) {
            await displayLenderInfo(lei, name, wizardState.data.lender);
            await new Promise(resolve => setTimeout(resolve, 300));
        }
    }
    
    // Mark GLEIF as confirmed and update button to Continue
    gleifConfirmed = true;
    
    // Show confirmation message with addresses if available
    const gleifData = wizardState.data.lender?.gleif_data;
    if (gleifData) {
        const legalAddr = gleifData.legal_address || {};
        const hqAddr = gleifData.headquarters_address || {};
        const legalLocation = [legalAddr.city, legalAddr.state].filter(Boolean).join(', ') || 'Not available';
        const hqLocation = [hqAddr.city, hqAddr.state].filter(Boolean).join(', ') || 'Not available';
        
        // Clean state codes
        const cleanLegalState = legalAddr.state?.startsWith('US-') ? legalAddr.state.substring(3) : legalAddr.state;
        const cleanHqState = hqAddr.state?.startsWith('US-') ? hqAddr.state.substring(3) : hqAddr.state;
        const cleanLegalLocation = [legalAddr.city, cleanLegalState].filter(Boolean).join(', ') || 'Not available';
        const cleanHqLocation = [hqAddr.city, cleanHqState].filter(Boolean).join(', ') || 'Not available';
        
        // Update lender data with cleaned addresses
        wizardState.data.lender.legal_address = {
            city: legalAddr.city || '',
            state: cleanLegalState || ''
        };
        wizardState.data.lender.headquarters_address = {
            city: hqAddr.city || '',
            state: cleanHqState || ''
        };
        
        console.log('Lender addresses confirmed:', {
            legal: cleanLegalLocation,
            headquarters: cleanHqLocation
        });
    }
    if (nextButton) {
        nextButton.disabled = false;
        nextButton.innerHTML = 'Continue <i class="fas fa-arrow-right"></i>';
        nextButton.onclick = confirmLender; // Will now proceed to next step on next click
    }
    
    // Show a message that GLEIF info is ready
    const infoContent = document.getElementById('lenderInfoContent');
    if (infoContent) {
        // Add a small notification that they can continue
        const notification = document.createElement('div');
        notification.style.cssText = 'margin-top: 12px; padding: 8px; background: #e7f3ff; border-left: 3px solid #2fade3; border-radius: 4px; font-size: 0.9rem; color: #004085;';
        notification.innerHTML = '<i class="fas fa-info-circle"></i> GLEIF verification complete. Click "Continue" to proceed.';
        notification.id = 'gleifContinueNotification';
        // Remove any existing notification
        const existing = document.getElementById('gleifContinueNotification');
        if (existing) existing.remove();
        infoContent.appendChild(notification);
    }
}

// Filter functions
function toggleFilterEdit() {
    const editor = document.getElementById('filterEditor');
    const button = document.querySelector('[onclick="toggleFilterEdit()"]');
    
    if (editor && button) {
        const isExpanded = editor.style.display !== 'none';
        editor.style.display = isExpanded ? 'none' : 'block';
        button.setAttribute('aria-expanded', !isExpanded);
        if (button.querySelector('i')) {
            button.querySelector('i').classList.toggle('fa-plus');
            button.querySelector('i').classList.toggle('fa-times');
        }
    }
}

function applyFilters() {
    // Get all filter values
    const actionTaken = document.getElementById('actionTaken')?.value || 'originations';
    const occupancy = document.getElementById('occupancy')?.value || 'owner-occupied';
    const units = Array.from(document.querySelectorAll('#filterEditor input[type="checkbox"][value="1"]:checked, #filterEditor input[type="checkbox"][value="2"]:checked, #filterEditor input[type="checkbox"][value="3"]:checked, #filterEditor input[type="checkbox"][value="4"]:checked'))
        .map(cb => cb.value);
    const construction = Array.from(document.querySelectorAll('#filterEditor input[type="checkbox"][value="site-built"]:checked, #filterEditor input[type="checkbox"][value="manufactured"]:checked'))
        .map(cb => cb.value);
    const reverseMortgage = Array.from(document.querySelectorAll('#filterEditor input[type="checkbox"][value="not-reverse"]:checked'))
        .map(cb => cb.value);
    const loanPurpose = Array.from(document.querySelectorAll('#filterEditor input[type="checkbox"][value="purchase"]:checked, #filterEditor input[type="checkbox"][value="refinance"]:checked, #filterEditor input[type="checkbox"][value="equity"]:checked'))
        .map(cb => cb.value);
    
    // Store filters
    wizardState.data.filters = {
        actionTaken,
        occupancy,
        units: units.length > 0 ? units : ['1', '2', '3', '4'],
        construction: construction.length > 0 ? construction : ['site-built', 'manufactured'],
        reverseMortgage: reverseMortgage.length > 0 ? reverseMortgage : ['not-reverse'],
        loanPurpose: loanPurpose.length > 0 ? loanPurpose : ['purchase', 'refinance']
    };
    
    // Update filter chips display
    renderFilterChips();
    
    // Close editor
    toggleFilterEdit();
}

// LOCKED: Part of Area Analysis Structure - Filter Toggle Switch
function createToggleSwitch(id, currentValue, leftLabel, rightLabel, onChange) {
    const toggleContainer = document.createElement('div');
    toggleContainer.className = 'filter-toggle-container';
    toggleContainer.style.marginTop = '4px';
    
    const toggleWrapper = document.createElement('div');
    toggleWrapper.className = 'filter-toggle-wrapper';
    
    const leftOption = document.createElement('button');
    leftOption.type = 'button';
    leftOption.className = 'filter-toggle-option';
    leftOption.textContent = leftLabel;
    
    const rightOption = document.createElement('button');
    rightOption.type = 'button';
    rightOption.className = 'filter-toggle-option';
    rightOption.textContent = rightLabel;
    
    // Determine which option is selected
    let isLeftSelected;
    if (id === 'actionTaken') {
        isLeftSelected = currentValue === 'origination';
    } else if (id === 'reverseMortgage') {
        isLeftSelected = currentValue === 'not-reverse';
    } else {
        isLeftSelected = false;
    }
    
    if (isLeftSelected) {
        leftOption.classList.add('active');
    } else {
        rightOption.classList.add('active');
    }
    
    leftOption.onclick = function() {
        leftOption.classList.add('active');
        rightOption.classList.remove('active');
        if (id === 'actionTaken') {
            onChange('origination');
        } else if (id === 'reverseMortgage') {
            onChange('not-reverse');
        }
    };
    
    rightOption.onclick = function() {
        rightOption.classList.add('active');
        leftOption.classList.remove('active');
        if (id === 'actionTaken') {
            onChange('application');
        } else if (id === 'reverseMortgage') {
            onChange('reverse');
        }
    };
    
    toggleWrapper.appendChild(leftOption);
    toggleWrapper.appendChild(rightOption);
    toggleContainer.appendChild(toggleWrapper);
    
    return toggleContainer;
}

// LOCKED: Part of Area Analysis Structure - Filter Rendering
function renderFilterChips() {
    const container = document.getElementById('filterChipsDisplay');
    if (!container) return;
    
    // Initialize filters with defaults if not set
    if (!wizardState.data.filters) {
        wizardState.data.filters = {
            actionTaken: 'origination',
            occupancy: ['owner-occupied'],
            totalUnits: '1-4',
            construction: ['site-built', 'manufactured'],
            loanPurpose: ['home-purchase', 'refinance', 'home-equity'],
            loanType: ['conventional', 'fha', 'va', 'rhs'],
            reverseMortgage: true
        };
    }
    
    const filters = wizardState.data.filters;
    
    // Ensure arrays exist for multi-select categories
    if (!Array.isArray(filters.occupancy)) filters.occupancy = filters.occupancy ? [filters.occupancy] : ['owner-occupied'];
    if (!Array.isArray(filters.construction)) filters.construction = filters.construction ? [filters.construction] : ['site-built'];
    if (!Array.isArray(filters.loanPurpose)) filters.loanPurpose = filters.loanPurpose ? [filters.loanPurpose] : ['home-purchase', 'refinance', 'home-equity'];
    if (!Array.isArray(filters.loanType)) filters.loanType = filters.loanType ? [filters.loanType] : ['conventional', 'fha', 'va', 'rhs'];
    
    container.innerHTML = '';
    
    // Action Taken - Toggle (no container box)
    const actionTakenGroup = document.createElement('div');
    actionTakenGroup.className = 'filter-group';
    
    const actionTakenLabel = document.createElement('div');
    actionTakenLabel.className = 'filter-group-label';
    actionTakenLabel.textContent = 'Action Taken';
    actionTakenGroup.appendChild(actionTakenLabel);
    
    const actionTakenToggle = createToggleSwitch(
        'actionTaken',
        filters.actionTaken || 'origination',
        'Origination',
        'Application',
        function(value) {
            wizardState.data.filters.actionTaken = value;
        }
    );
    actionTakenGroup.appendChild(actionTakenToggle);
    container.appendChild(actionTakenGroup);
    
    // Occupancy - Multi-select
    const occupancyGroup = createFilterGroup('Occupancy');
    const occupancyOptions = [
        { value: 'owner-occupied', label: 'Owner Occupied' },
        { value: 'second-home', label: 'Second Home' },
        { value: 'investor', label: 'Investor Loan' }
    ];
    occupancyOptions.forEach(option => {
        const isSelected = filters.occupancy.includes(option.value);
        occupancyGroup._chipsContainer.appendChild(createFilterChipBox('occupancy', option.label, option.value, isSelected, false));
    });
    container.appendChild(occupancyGroup);
    
    // Total Units - Single-select
    const totalUnitsGroup = createFilterGroup('Total Units');
    const totalUnitsOptions = [
        { value: '1-4', label: '1-4' },
        { value: '5+', label: '5+' }
    ];
    totalUnitsOptions.forEach(option => {
        const isSelected = filters.totalUnits === option.value;
        totalUnitsGroup._chipsContainer.appendChild(createFilterChipBox('totalUnits', option.label, option.value, isSelected, true));
    });
    container.appendChild(totalUnitsGroup);
    
    // Construction Type - Multi-select
    const constructionGroup = createFilterGroup('Construction Type');
    const constructionOptions = [
        { value: 'site-built', label: 'Site Built' },
        { value: 'manufactured', label: 'Manufactured' }
    ];
    constructionOptions.forEach(option => {
        const isSelected = filters.construction.includes(option.value);
        constructionGroup._chipsContainer.appendChild(createFilterChipBox('construction', option.label, option.value, isSelected, false));
    });
    container.appendChild(constructionGroup);
    
    // Loan Purpose - Multi-select
    const loanPurposeGroup = createFilterGroup('Loan Purpose');
    const loanPurposeOptions = [
        { value: 'home-purchase', label: 'Home Purchase' },
        { value: 'refinance', label: 'Refinance' },
        { value: 'home-equity', label: 'Home Equity' }
    ];
    loanPurposeOptions.forEach(option => {
        const isSelected = filters.loanPurpose.includes(option.value);
        loanPurposeGroup._chipsContainer.appendChild(createFilterChipBox('loanPurpose', option.label, option.value, isSelected, false));
    });
    container.appendChild(loanPurposeGroup);
    
    // Loan Type - Multi-select
    const loanTypeGroup = createFilterGroup('Loan Type');
    const loanTypeOptions = [
        { value: 'conventional', label: 'Conventional' },
        { value: 'fha', label: 'FHA' },
        { value: 'va', label: 'VA' },
        { value: 'rhs', label: 'RHS' }
    ];
    loanTypeOptions.forEach(option => {
        const isSelected = filters.loanType.includes(option.value);
        loanTypeGroup._chipsContainer.appendChild(createFilterChipBox('loanType', option.label, option.value, isSelected, false));
    });
    container.appendChild(loanTypeGroup);
    
    // Reverse Mortgage - Toggle (no container box)
    const reverseGroup = document.createElement('div');
    reverseGroup.className = 'filter-group';
    
    const reverseLabel = document.createElement('div');
    reverseLabel.className = 'filter-group-label';
    reverseLabel.textContent = 'Reverse Mortgage';
    reverseGroup.appendChild(reverseLabel);
    
    // reverseMortgage: true = not reverse, false = reverse (HMDA reverse mortgage = 1 means reverse)
    const reverseValue = filters.reverseMortgage === false ? 'reverse' : 'not-reverse';
    const reverseToggle = createToggleSwitch(
        'reverseMortgage',
        reverseValue,
        'Not Reverse',
        'Reverse',
        function(value) {
            // If value is 'reverse', set to false (HMDA reverse mortgage = 1)
            // If value is 'not-reverse', set to true (any other entry)
            wizardState.data.filters.reverseMortgage = value === 'reverse' ? false : true;
        }
    );
    reverseGroup.appendChild(reverseToggle);
    container.appendChild(reverseGroup);
}

// Render filter chips for lender analysis (step5B)
function renderFilterChipsB() {
    const container = document.getElementById('filterChipsDisplayB');
    if (!container) return;
    
    // Initialize filters with defaults if not set
    if (!wizardState.data.filters) {
        wizardState.data.filters = {
            actionTaken: 'origination',
            occupancy: ['owner-occupied'],
            totalUnits: '1-4',
            construction: ['site-built', 'manufactured'],
            loanPurpose: ['home-purchase', 'refinance', 'home-equity'],
            loanType: ['conventional', 'fha', 'va', 'rhs'],
            reverseMortgage: true
        };
    }
    
    const filters = wizardState.data.filters;
    
    // Ensure arrays exist for multi-select categories
    if (!Array.isArray(filters.occupancy)) filters.occupancy = filters.occupancy ? [filters.occupancy] : ['owner-occupied'];
    if (!Array.isArray(filters.construction)) filters.construction = filters.construction ? [filters.construction] : ['site-built'];
    if (!Array.isArray(filters.loanPurpose)) filters.loanPurpose = filters.loanPurpose ? [filters.loanPurpose] : ['home-purchase', 'refinance', 'home-equity'];
    if (!Array.isArray(filters.loanType)) filters.loanType = filters.loanType ? [filters.loanType] : ['conventional', 'fha', 'va', 'rhs'];
    
    container.innerHTML = '';
    
    // Action Taken - Toggle (no container box)
    const actionTakenGroup = document.createElement('div');
    actionTakenGroup.className = 'filter-group';
    
    const actionTakenLabel = document.createElement('div');
    actionTakenLabel.className = 'filter-group-label';
    actionTakenLabel.textContent = 'Action Taken';
    actionTakenGroup.appendChild(actionTakenLabel);
    
    const actionTakenToggle = createToggleSwitch(
        'actionTaken',
        filters.actionTaken || 'origination',
        'Origination',
        'Application',
        function(value) {
            wizardState.data.filters.actionTaken = value;
        }
    );
    actionTakenGroup.appendChild(actionTakenToggle);
    container.appendChild(actionTakenGroup);
    
    // Occupancy - Multi-select
    const occupancyGroup = createFilterGroup('Occupancy');
    const occupancyOptions = [
        { value: 'owner-occupied', label: 'Owner Occupied' },
        { value: 'second-home', label: 'Second Home' },
        { value: 'investor', label: 'Investor Loan' }
    ];
    occupancyOptions.forEach(option => {
        const isSelected = filters.occupancy.includes(option.value);
        occupancyGroup._chipsContainer.appendChild(createFilterChipBox('occupancy', option.label, option.value, isSelected, false));
    });
    container.appendChild(occupancyGroup);
    
    // Total Units - Single-select
    const totalUnitsGroup = createFilterGroup('Total Units');
    const totalUnitsOptions = [
        { value: '1-4', label: '1-4' },
        { value: '5+', label: '5+' }
    ];
    totalUnitsOptions.forEach(option => {
        const isSelected = filters.totalUnits === option.value;
        totalUnitsGroup._chipsContainer.appendChild(createFilterChipBox('totalUnits', option.label, option.value, isSelected, true));
    });
    container.appendChild(totalUnitsGroup);
    
    // Construction Type - Multi-select
    const constructionGroup = createFilterGroup('Construction Type');
    const constructionOptions = [
        { value: 'site-built', label: 'Site Built' },
        { value: 'manufactured', label: 'Manufactured' }
    ];
    constructionOptions.forEach(option => {
        const isSelected = filters.construction.includes(option.value);
        constructionGroup._chipsContainer.appendChild(createFilterChipBox('construction', option.label, option.value, isSelected, false));
    });
    container.appendChild(constructionGroup);
    
    // Loan Purpose - Multi-select
    const loanPurposeGroup = createFilterGroup('Loan Purpose');
    const loanPurposeOptions = [
        { value: 'home-purchase', label: 'Home Purchase' },
        { value: 'refinance', label: 'Refinance' },
        { value: 'home-equity', label: 'Home Equity' }
    ];
    loanPurposeOptions.forEach(option => {
        const isSelected = filters.loanPurpose.includes(option.value);
        loanPurposeGroup._chipsContainer.appendChild(createFilterChipBox('loanPurpose', option.label, option.value, isSelected, false));
    });
    container.appendChild(loanPurposeGroup);
    
    // Loan Type - Multi-select
    const loanTypeGroup = createFilterGroup('Loan Type');
    const loanTypeOptions = [
        { value: 'conventional', label: 'Conventional' },
        { value: 'fha', label: 'FHA' },
        { value: 'va', label: 'VA' },
        { value: 'rhs', label: 'RHS' }
    ];
    loanTypeOptions.forEach(option => {
        const isSelected = filters.loanType.includes(option.value);
        loanTypeGroup._chipsContainer.appendChild(createFilterChipBox('loanType', option.label, option.value, isSelected, false));
    });
    container.appendChild(loanTypeGroup);
    
    // Reverse Mortgage - Toggle (no container box)
    const reverseGroup = document.createElement('div');
    reverseGroup.className = 'filter-group';
    
    const reverseLabel = document.createElement('div');
    reverseLabel.className = 'filter-group-label';
    reverseLabel.textContent = 'Reverse Mortgage';
    reverseGroup.appendChild(reverseLabel);
    
    // reverseMortgage: true = not reverse, false = reverse (HMDA reverse mortgage = 1 means reverse)
    const reverseValue = filters.reverseMortgage === false ? 'reverse' : 'not-reverse';
    const reverseToggle = createToggleSwitch(
        'reverseMortgage',
        reverseValue,
        'Not Reverse',
        'Reverse',
        function(value) {
            // If value is 'reverse', set to false (HMDA reverse mortgage = 1)
            // If value is 'not-reverse', set to true (any other entry)
            wizardState.data.filters.reverseMortgage = value === 'reverse' ? false : true;
        }
    );
    reverseGroup.appendChild(reverseToggle);
    container.appendChild(reverseGroup);
}

function createFilterGroup(label) {
    const group = document.createElement('div');
    group.className = 'filter-group';
    
    const labelEl = document.createElement('div');
    labelEl.className = 'filter-group-label';
    labelEl.textContent = label;
    
    const chipsContainer = document.createElement('div');
    chipsContainer.className = 'county-tiles-container';
    chipsContainer.style.marginTop = '4px';
    
    group.appendChild(labelEl);
    group.appendChild(chipsContainer);
    
    // Store reference to chips container for appending chips
    group._chipsContainer = chipsContainer;
    
    return group;
}

// LOCKED: Part of Area Analysis Structure - Filter Chip Creation
function createFilterChipBox(category, label, value, isSelected, isSingleSelect) {
    const chip = document.createElement('span');
    chip.className = 'county-chip';
    chip.setAttribute('data-category', category);
    chip.setAttribute('data-value', value);
    
    if (isSelected) {
        chip.classList.add('selected');
    }
    
    // Create checkbox/radio (hidden)
    const checkbox = document.createElement('input');
    checkbox.type = isSingleSelect ? 'radio' : 'checkbox';
    checkbox.name = isSingleSelect ? category : `${category}[]`;
    checkbox.value = value;
    checkbox.checked = isSelected;
    checkbox.style.display = 'none';
    checkbox.setAttribute('data-category', category);
    checkbox.addEventListener('change', function() {
        toggleFilter(category, value, isSingleSelect);
    });
    
    // Create text span
    const textSpan = document.createElement('span');
    textSpan.className = 'county-chip-text';
    textSpan.textContent = label;
    
    // Create remove button (only show if selected and multi-select)
    const removeBtn = document.createElement('button');
    removeBtn.className = 'remove-chip';
    removeBtn.type = 'button';
    removeBtn.setAttribute('aria-label', `Remove ${label}`);
    removeBtn.textContent = '×';
    // Hide remove button for single-select (can't remove, only switch)
    removeBtn.style.display = (isSelected && !isSingleSelect) ? 'inline-flex' : 'none';
    removeBtn.onclick = function(e) {
        e.stopPropagation();
        toggleFilter(category, value, isSingleSelect);
    };
    
    // Make chip clickable to toggle
    chip.style.cursor = 'pointer';
    chip.onclick = function(e) {
        if (e.target !== removeBtn && !removeBtn.contains(e.target)) {
            if (isSingleSelect) {
                // For single-select, always select this option (will deselect others)
                checkbox.checked = true;
            } else {
                // For multi-select, toggle
                checkbox.checked = !checkbox.checked;
            }
            toggleFilter(category, value, isSingleSelect);
        }
    };
    
    // Store reference to remove button for updating visibility
    chip._removeBtn = removeBtn;
    
    // Append all elements
    chip.appendChild(checkbox);
    chip.appendChild(textSpan);
    chip.appendChild(removeBtn);
    
    return chip;
}

// LOCKED: Part of Area Analysis Structure - Filter Toggle Logic
function toggleFilter(category, value, isSingleSelect) {
    if (!wizardState.data.filters) {
        wizardState.data.filters = {};
    }
    
    if (isSingleSelect) {
        // For single-select categories (actionTaken, totalUnits), just set the value
        wizardState.data.filters[category] = value;
    } else {
        // For multi-select categories
        if (!Array.isArray(wizardState.data.filters[category])) {
            wizardState.data.filters[category] = [];
        }
        
        const index = wizardState.data.filters[category].indexOf(value);
        if (index > -1) {
            // Remove if already selected
            wizardState.data.filters[category].splice(index, 1);
            
            // If all removed, add back at least one default
            if (wizardState.data.filters[category].length === 0) {
                if (category === 'occupancy') {
                    wizardState.data.filters[category] = ['owner-occupied'];
                } else if (category === 'construction') {
                    wizardState.data.filters[category] = ['site-built'];
                } else if (category === 'loanPurpose') {
                    wizardState.data.filters[category] = ['home-purchase', 'refinance', 'home-equity'];
                } else if (category === 'loanType') {
                    wizardState.data.filters[category] = ['conventional', 'fha', 'va', 'rhs'];
                }
            }
        } else {
            // Add if not selected
            wizardState.data.filters[category].push(value);
        }
    }
    
    // Re-render chips to update visual state (both containers if they exist)
    renderFilterChips();
    renderFilterChipsB();
}

// Update chip visual state without full re-render (for better performance)
function updateFilterChipState(chip, isSelected) {
    if (isSelected) {
        chip.classList.add('selected');
        if (chip._removeBtn) {
            chip._removeBtn.style.display = 'inline-flex';
        }
    } else {
        chip.classList.remove('selected');
        if (chip._removeBtn) {
            chip._removeBtn.style.display = 'none';
        }
    }
}

function updateFilterEditor() {
    const filters = wizardState.data.filters || {};
    
    // Update checkboxes to match current filter state
    if (filters.units) {
        document.querySelectorAll('#filterEditor input[type="checkbox"][value="1"], #filterEditor input[type="checkbox"][value="2"], #filterEditor input[type="checkbox"][value="3"], #filterEditor input[type="checkbox"][value="4"]').forEach(cb => {
            cb.checked = filters.units.includes(cb.value);
        });
    }
    
    if (filters.construction) {
        document.querySelectorAll('#filterEditor input[type="checkbox"][value="site-built"], #filterEditor input[type="checkbox"][value="manufactured"]').forEach(cb => {
            cb.checked = filters.construction.includes(cb.value);
        });
    }
    
    // Reverse Mortgage is a boolean, not an array
    if (filters.reverseMortgage !== undefined) {
        const reverseCheckbox = document.querySelector('#filterEditor input[type="checkbox"][value="not-reverse"]');
        if (reverseCheckbox) {
            reverseCheckbox.checked = filters.reverseMortgage === true;
        }
    }
    
    if (filters.loanPurpose) {
        document.querySelectorAll('#filterEditor input[type="checkbox"][value="purchase"], #filterEditor input[type="checkbox"][value="refinance"], #filterEditor input[type="checkbox"][value="equity"]').forEach(cb => {
            cb.checked = filters.loanPurpose.includes(cb.value);
        });
    }
    
    if (filters.actionTaken) {
        const actionTakenSelect = document.getElementById('actionTaken');
        if (actionTakenSelect) actionTakenSelect.value = filters.actionTaken;
    }
    
    if (filters.occupancy) {
        const occupancySelect = document.getElementById('occupancy');
        if (occupancySelect) occupancySelect.value = filters.occupancy;
    }
}

// LOCKED: Part of Area Analysis Structure - Filter Validation
function validateFilters() {
    const filters = wizardState.data.filters || {};
    
    // Validate Action Taken (single-select, must have value)
    if (!filters.actionTaken) {
        showError('Please select an Action Taken option');
        return false;
    }
    
    // Validate Occupancy (multi-select, must have at least one)
    if (!Array.isArray(filters.occupancy) || filters.occupancy.length === 0) {
        showError('Please select at least one Occupancy option');
        return false;
    }
    
    // Validate Total Units (single-select, must have value)
    if (!filters.totalUnits) {
        showError('Please select a Total Units option');
        return false;
    }
    
    // Validate Construction (multi-select, must have at least one)
    if (!Array.isArray(filters.construction) || filters.construction.length === 0) {
        showError('Please select at least one Construction Type option');
        return false;
    }
    
    // Validate Loan Purpose (multi-select, must have at least one)
    if (!Array.isArray(filters.loanPurpose) || filters.loanPurpose.length === 0) {
        showError('Please select at least one Loan Purpose option');
        return false;
    }
    
    // Validate Loan Type (multi-select, must have at least one)
    if (!Array.isArray(filters.loanType) || filters.loanType.length === 0) {
        showError('Please select at least one Loan Type option');
        return false;
    }
    
    // Reverse Mortgage is optional (boolean), no validation needed
    
    return true;
}

// LOCKED: Part of Area Analysis Structure
function confirmFilters() {
    // Ensure filters are applied
    if (!wizardState.data.filters) {
        // Initialize with defaults if not set
        wizardState.data.filters = {
            actionTaken: 'origination',
            occupancy: ['owner-occupied'],
            totalUnits: '1-4',
            construction: ['site-built', 'manufactured'],
            loanPurpose: ['home-purchase', 'refinance', 'home-equity'],
            loanType: ['conventional', 'fha', 'va', 'rhs'],
            reverseMortgage: true
        };
    }
    
    // Validate all filters
    if (!validateFilters()) {
        return;
    }
    
    showStepSuccess(document.querySelector('.step-card.active'));
    setTimeout(() => {
        transitionToStep('step5A');
    }, 500);
}

// Geography scope
function confirmGeoScope() {
    const selected = document.querySelector('input[name="geoScope"]:checked');
    if (!selected) {
        showError('Please select a geographic scope');
        return;
    }
    
    // Validate: Only banks/lenders with RSSD can use branch_cbsas
    if (selected.value === 'branch_cbsas') {
        const lenderType = wizardState.data.lender?.type || wizardState.data.lender?.type_name || '';
        const lenderTypeLower = lenderType.toLowerCase();
        const lenderRssd = wizardState.data.lender?.rssd;
        const isBankByType = lenderTypeLower.includes('bank') || lenderTypeLower.includes('affiliate');
        const hasRssd = lenderRssd && lenderRssd.trim() !== '' && lenderRssd !== '0000000000';
        const canUseBranchOption = isBankByType || hasRssd;

        if (!canUseBranchOption) {
            showError('Branch data is only available for banks with RSSD. Please select a different geographic scope.');
            // Auto-select loan_cbsas as fallback (first option)
            const loanCbsasOption = document.querySelector('input[name="geoScope"][value="loan_cbsas"]');
            if (loanCbsasOption) {
                loanCbsasOption.checked = true;
            }
            return;
        }
    }
    
    wizardState.data.lenderAnalysis.geographyScope = selected.value;
    
    // If custom is selected, transition to CBSA selection step
    if (selected.value === 'custom') {
        console.log('Custom CBSA selected, transitioning to step3B5...');
        showStepSuccess(document.querySelector('.step-card.active'));
        setTimeout(() => {
            console.log('Calling transitionToStep(step3B5)');
            transitionToStep('step3B5');
        }, 500);
        return;
    }
    
    showStepSuccess(document.querySelector('.step-card.active'));
    setTimeout(() => {
        transitionToStep('step4B');
    }, 500);
}

// Custom CBSA selection
async function confirmCustomCbsa() {
    const select = document.getElementById('customMetroSelect');
    const selectText = document.getElementById('customMetroSelectText');
    
    if (!select || !select.value) {
        if (!selectText || selectText.textContent === 'Select a metro area...') {
            showError('Please select a metro area');
            return;
        }
    }
    
    const cbsaCode = select.value;
    if (!cbsaCode) {
        showError('Please select a metro area');
        return;
    }
    
    // Find metro name (metros use 'code' property, not 'cbsa')
    const metro = wizardState.cache.metros?.find(m => m.code === cbsaCode);
    const metroName = metro?.name || selectText.textContent;
    
    wizardState.data.lenderAnalysis.customCbsa = cbsaCode;
    wizardState.data.lenderAnalysis.customCbsaName = metroName;
    
    // Load counties for the selected metro
    await loadCustomCountiesByMetro();
    
    // Transition to step 3B6 (county selection)
    showStepSuccess(document.querySelector('.step-card.active'));
    setTimeout(() => {
        transitionToStep('step3B6');
    }, 500);
}

// Custom county selection
function confirmCustomCounties() {
    if (!validateCustomCountySelection()) {
        return;
    }
    
    const selectedCounties = getSelectedCustomCounties();
    if (selectedCounties.length === 0) {
        showError('Please select at least one county');
        return;
    }
    
    wizardState.data.lenderAnalysis.customCounties = selectedCounties.map(c => c.geoid);
    
    showStepSuccess(document.querySelector('.step-card.active'));
    setTimeout(() => {
        transitionToStep('step4B');
    }, 500);
}

// Comparison group
function confirmComparisonGroup() {
    const selected = document.querySelector('input[name="compGroup"]:checked');
    if (!selected) {
        showError('Please select a comparison group');
        return;
    }
    
    wizardState.data.lenderAnalysis.comparisonGroup = selected.value;
    
    showStepSuccess(document.querySelector('.step-card.active'));
    setTimeout(() => {
        transitionToStep('step5B');
    }, 500);
}

function confirmFiltersB() {
    if (!validateFilters()) {
        return;
    }
    
    showStepSuccess(document.querySelector('.step-card.active'));
    setTimeout(() => {
        transitionToStep('step6B');
    }, 500);
}

// Report generation
async function generateReport() {
    if (!wizardState.data.disclaimerAccepted) {
        showError('Please accept the disclaimer to continue');
        return;
    }
    
    showLoading('Generating your report...');
    
    try {
        let result;
        if (wizardState.data.analysisType === 'area') {
            result = await apiClient.generateAreaReport(wizardState.data);
        } else {
            result = await apiClient.generateLenderReport(wizardState.data);
        }
        
        // Log analytics event
        if (window.JustDataAnalytics) {
            if (wizardState.data.analysisType === 'area') {
                window.JustDataAnalytics.logDataExplorerAreaReport({
                    countyFips: wizardState.data.county?.geoid5 || '',
                    countyName: wizardState.data.county?.name || '',
                    state: wizardState.data.state || '',
                    year: wizardState.data.years?.join('-') || '',
                    dataTypes: wizardState.data.dataTypes?.join(',') || '',
                    reportType: 'area_exploration'
                });
            } else {
                window.JustDataAnalytics.logDataExplorerLenderReport({
                    lenderName: wizardState.data.lender?.name || '',
                    lei: wizardState.data.lender?.lei || '',
                    year: wizardState.data.years?.join('-') || '',
                    dataTypes: wizardState.data.dataTypes?.join(',') || '',
                    reportType: 'lender_exploration'
                });
            }
        }

        // Redirect to report view (which will show progress page if not ready)
        if (result.report_id) {
            window.location.href = `/dataexplorer/report/${result.report_id}`;
        } else {
            hideLoading();
            showError('Report generated but no redirect URL provided');
        }
    } catch (error) {
        hideLoading();
        showError('Unable to generate report. Please try again.');
    }
}

// Update summary bar
function updateSummaryBar() {
    const summaryBar = document.getElementById('wizardSummaryBar');
    if (summaryBar) {
        const steps = summaryBar.querySelector('.summary-steps');
        const details = summaryBar.querySelector('.summary-details');
        
        if (steps) {
            steps.innerHTML = generateStepIndicators();
        }
        if (details) {
            details.innerHTML = generateSummaryDetails();
        }
    }
}

// Export functions for use in HTML
// Custom metro dropdown setup (reuses area analysis metro dropdown logic with custom IDs)
function setupCustomMetroDropdown() {
    console.log('setupCustomMetroDropdown called');
    // Scope to step3B5 to avoid conflicts with area analysis dropdown
    // The step card uses data-step attribute, not id, so find it by attribute
    let step3B5 = document.querySelector('[data-step="step3B5"]');
    if (!step3B5) {
        console.error('setupCustomMetroDropdown: step3B5 not found (tried [data-step="step3B5"])');
        // Try alternative selector
        step3B5 = document.querySelector('.step-card.active[data-step="step3B5"]');
        if (!step3B5) {
            console.error('setupCustomMetroDropdown: step3B5 not found with alternative selector either');
            return;
        }
    }
    
    console.log('step3B5 found, looking for elements...');
    const select = step3B5.querySelector('#customMetroSelect');
    const selectButton = step3B5.querySelector('#customMetroSelectButton');
    const selectText = step3B5.querySelector('#customMetroSelectText');
    const searchInput = step3B5.querySelector('#customMetroSearch');
    const dropdown = step3B5.querySelector('#customMetroDropdown');
    const selectContainer = step3B5.querySelector('.metro-select-container');
    const dropdownWrapper = selectContainer ? selectContainer.querySelector('.metro-dropdown-wrapper') : null;
    const sortedMetros = wizardState.cache.metros || [];
    
    console.log('Elements found:', {
        select: !!select,
        selectButton: !!selectButton,
        selectText: !!selectText,
        searchInput: !!searchInput,
        dropdown: !!dropdown,
        selectContainer: !!selectContainer,
        dropdownWrapper: !!dropdownWrapper,
        metrosCount: sortedMetros.length
    });
    
    if (!select || !selectButton || !selectText || !dropdown || !dropdownWrapper) {
        console.error('setupCustomMetroDropdown: Missing required elements', {
            select: !!select,
            selectButton: !!selectButton,
            selectText: !!selectText,
            dropdown: !!dropdown,
            dropdownWrapper: !!dropdownWrapper,
            metrosCount: sortedMetros.length
        });
        return;
    }
    
    if (sortedMetros.length === 0) {
        console.error('setupCustomMetroDropdown: No metros available');
        return;
    }
    
    console.log('All elements found, setting up dropdown...');
    
    // Clear existing options
    select.innerHTML = '<option value="">Select a metro area...</option>';
    
    // Populate select dropdown (alphabetically sorted) - hidden select for form submission
    sortedMetros.forEach(metro => {
        const option = document.createElement('option');
        option.value = metro.code;
        option.textContent = metro.name;
        select.appendChild(option);
    });
    
    // Store metros for filtering
    wizardState.cache.filteredCustomMetros = sortedMetros;
    
    // Remove existing event listeners by cloning
    const newButton = selectButton.cloneNode(true);
    selectButton.parentNode.replaceChild(newButton, selectButton);
    const newSelectButton = step3B5.querySelector('#customMetroSelectButton');
    
    if (!newSelectButton) {
        console.warn('setupCustomMetroDropdown: Could not find newSelectButton after cloning');
        return;
    }
    
    // Show custom dropdown when button is clicked
    newSelectButton.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Custom metro button clicked');
        showCustomMetroDropdown();
    });
    
    newSelectButton.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            showCustomMetroDropdown();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            showCustomMetroDropdown();
            setTimeout(() => {
                const searchInput = document.getElementById('customMetroSearch');
                if (searchInput) {
                    searchInput.focus();
                }
            }, 50);
        }
    });
    
    // Setup search functionality
    let searchTimeout;
    if (searchInput) {
        const newSearchInput = searchInput.cloneNode(true);
        searchInput.parentNode.replaceChild(newSearchInput, searchInput);
        const newInput = document.getElementById('customMetroSearch');
        
        newInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            const query = e.target.value.toLowerCase().trim();
            
            searchTimeout = setTimeout(() => {
                const filtered = query.length === 0 
                    ? sortedMetros 
                    : sortedMetros.filter(metro => 
                        metro.name.toLowerCase().includes(query)
                    );
                renderCustomMetroDropdown(filtered);
                wizardState.cache.selectedCustomMetroIndex = -1;
            }, 100);
        });
        
        // Add keyboard navigation for search input
        newInput.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateCustomMetroDropdown(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateCustomMetroDropdown(-1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                selectHighlightedCustomMetro();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideCustomMetroDropdown();
                if (selectButton) {
                    selectButton.focus();
                }
            }
        });
        
        newInput.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
    
    // Hide dropdown when clicking outside (only for custom metro)
    // Use a one-time listener to avoid conflicts with area analysis dropdown
    const clickHandler = function(e) {
        // Use the selectContainer from the outer scope (scoped to step3B5)
        if (selectContainer && !e.target.closest('.metro-select-container')) {
            // Check if we're in step3B5 (custom metro step)
            const currentStep = document.querySelector('.step-card.active');
            if (currentStep && currentStep.getAttribute('data-step') === 'step3B5') {
                hideCustomMetroDropdown();
            }
        }
    };
    // Remove any existing listener and add new one
    document.removeEventListener('click', clickHandler);
    document.addEventListener('click', clickHandler);
    
    // Pre-render dropdown list (but keep it hidden until button is clicked)
    renderCustomMetroDropdown(sortedMetros);
    
    // Ensure dropdown is hidden initially (dropdownWrapper was already declared at top of function)
    if (dropdownWrapper) {
        dropdownWrapper.style.display = 'none';
    }
}

function showCustomMetroDropdown() {
    // Find the dropdown wrapper specifically for custom metro (within step3B5)
    // MUST scope to step3B5 to avoid conflicts with area analysis dropdown
    const step3B5 = document.querySelector('[data-step="step3B5"]');
    if (!step3B5) {
        console.warn('showCustomMetroDropdown: step3B5 not found (tried [data-step="step3B5"])');
        return;
    }
    
    const selectContainer = step3B5.querySelector('.metro-select-container');
    const dropdownWrapper = selectContainer ? selectContainer.querySelector('.metro-dropdown-wrapper') : null;
    const searchInput = step3B5.querySelector('#customMetroSearch');
    const selectButton = step3B5.querySelector('#customMetroSelectButton');
    
    console.log('showCustomMetroDropdown called', {
        step3B5: !!step3B5,
        selectContainer: !!selectContainer,
        dropdownWrapper: !!dropdownWrapper,
        searchInput: !!searchInput,
        selectButton: !!selectButton
    });
    
    if (dropdownWrapper && selectContainer && selectButton) {
        const buttonRect = selectButton.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const spaceBelow = viewportHeight - buttonRect.bottom;
        const spaceAbove = buttonRect.top;
        
        const itemHeight = 30;
        const searchBoxHeight = 50;
        const minHeight = (itemHeight * 10) + searchBoxHeight;
        const maxHeight = Math.min(spaceBelow - 20, spaceAbove - 20, 500);
        
        let topPosition = buttonRect.bottom + 4;
        let dropdownHeight = Math.max(minHeight, Math.min(maxHeight, 500));
        
        if (spaceBelow < minHeight && spaceAbove > spaceBelow) {
            topPosition = buttonRect.top - dropdownHeight - 4;
        }
        
        dropdownWrapper.style.position = 'fixed';
        dropdownWrapper.style.top = `${topPosition}px`;
        dropdownWrapper.style.left = `${buttonRect.left}px`;
        dropdownWrapper.style.width = `${buttonRect.width}px`;
        dropdownWrapper.style.maxHeight = `${dropdownHeight}px`;
        dropdownWrapper.style.display = 'block';
        dropdownWrapper.style.zIndex = '1000';
        
        selectButton.setAttribute('aria-expanded', 'true');
        
        if (searchInput) {
            setTimeout(() => searchInput.focus(), 50);
        }
    }
}

function hideCustomMetroDropdown() {
    // MUST scope to step3B5 to avoid conflicts with area analysis dropdown
    const step3B5 = document.querySelector('[data-step="step3B5"]');
    if (!step3B5) {
        return; // Step not active, nothing to hide
    }
    const selectContainer = step3B5.querySelector('.metro-select-container');
    const dropdownWrapper = selectContainer ? selectContainer.querySelector('.metro-dropdown-wrapper') : null;
    const selectButton = step3B5.querySelector('#customMetroSelectButton');
    
    if (dropdownWrapper) {
        dropdownWrapper.style.display = 'none';
    }
    if (selectButton) {
        selectButton.setAttribute('aria-expanded', 'false');
    }
}

function renderCustomMetroDropdown(metros) {
    const dropdown = document.getElementById('customMetroDropdown');
    if (!dropdown) return;
    
    dropdown.innerHTML = '';
    
    if (metros.length === 0) {
        dropdown.innerHTML = '<div class="metro-dropdown-item no-results">No metros found</div>';
        return;
    }
    
    wizardState.cache.currentCustomMetros = metros;
    
    metros.forEach((metro, index) => {
        const item = document.createElement('div');
        item.className = 'metro-dropdown-item';
        item.textContent = metro.name;
        item.setAttribute('role', 'option');
        item.setAttribute('data-code', metro.code);
        item.setAttribute('data-name', metro.name);
        item.setAttribute('data-index', index);
        item.setAttribute('tabindex', '-1');
        item.style.cursor = 'pointer';
        
        item.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            selectCustomMetro(metro.code, metro.name);
        });
        
        item.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                selectCustomMetro(metro.code, metro.name);
            }
        });
        
        dropdown.appendChild(item);
    });
}

function selectCustomMetro(code, name) {
    const step3B5 = document.querySelector('[data-step="step3B5"]');
    if (!step3B5) {
        return;
    }
    const select = step3B5.querySelector('#customMetroSelect');
    const selectText = step3B5.querySelector('#customMetroSelectText');
    const selectButton = step3B5.querySelector('#customMetroSelectButton');
    
    if (select) {
        select.value = code;
    }
    if (selectText) {
        selectText.textContent = name;
    }
    if (selectButton) {
        selectButton.setAttribute('aria-expanded', 'false');
    }
    
    hideCustomMetroDropdown();
    
    // Clear search input
    const searchInput = step3B5.querySelector('#customMetroSearch');
    if (searchInput) {
        searchInput.value = '';
        // Re-render with all metros when cleared
        const sortedMetros = wizardState.cache.metros || [];
        renderCustomMetroDropdown(sortedMetros);
    }
}

function navigateCustomMetroDropdown(direction) {
    const metros = wizardState.cache.currentCustomMetros || [];
    if (metros.length === 0) return;
    
    let currentIndex = wizardState.cache.selectedCustomMetroIndex || -1;
    currentIndex += direction;
    
    if (currentIndex < 0) {
        currentIndex = 0;
    } else if (currentIndex >= metros.length) {
        currentIndex = metros.length - 1;
    }
    
    wizardState.cache.selectedCustomMetroIndex = currentIndex;
    
    const items = document.querySelectorAll('#customMetroDropdown .metro-dropdown-item');
    items.forEach((item, index) => {
        item.classList.remove('highlighted');
        if (index === currentIndex) {
            item.classList.add('highlighted');
            item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    });
}

function selectHighlightedCustomMetro() {
    const metros = wizardState.cache.currentCustomMetros || [];
    const currentIndex = wizardState.cache.selectedCustomMetroIndex;
    
    if (currentIndex >= 0 && currentIndex < metros.length) {
        const metro = metros[currentIndex];
        selectCustomMetro(metro.code, metro.name);
    }
}

// Load counties for custom selection (reuses area analysis logic)
async function loadCustomCountiesByMetro() {
    const cbsaCode = wizardState.data.lenderAnalysis.customCbsa;
    if (!cbsaCode) return;
    
    showLoading('Loading counties...');
    
    try {
        const counties = await apiClient.getCountiesByMetro(cbsaCode);
        wizardState.cache.countiesByMetro = wizardState.cache.countiesByMetro || {};
        wizardState.cache.countiesByMetro[cbsaCode] = counties;
        
        const container = document.getElementById('customCountyCheckboxes');
        if (container) {
            container.innerHTML = '';
            
            if (counties.length === 0) {
                container.innerHTML = '<p style="color: #999;">No counties found for this metro area.</p>';
                hideLoading();
                return;
            }
            
            counties.forEach(county => {
                const fullFips = `${county.state_fips || ''}${county.fips || ''}`;
                const countyName = county.name || '';
                const stateName = county.state_name || '';
                const cbsa = county.cbsa || '';
                const cbsaName = county.cbsa_name || '';
                
                if (!fullFips || !countyName || !stateName) {
                    console.warn('Skipping county with missing data:', county);
                    return;
                }
                
                let displayCountyName = countyName.replace(/\s+County\s*$/i, '').trim();
                
                const stateAbbrMap = {
                    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
                    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
                    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
                    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
                    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
                    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
                    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
                    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
                    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
                    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
                    'District of Columbia': 'DC'
                };
                const stateAbbr = stateAbbrMap[stateName] || stateName.substring(0, 2).toUpperCase();
                
                const chip = document.createElement('span');
                chip.className = 'county-chip';
                chip.setAttribute('data-fips', fullFips);
                chip.setAttribute('data-name', countyName);
                chip.setAttribute('data-state', stateName);
                chip.setAttribute('data-cbsa', cbsa);
                chip.setAttribute('data-cbsa-name', cbsaName);
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.value = fullFips;
                checkbox.checked = true; // Pre-check all counties
                checkbox.style.display = 'none';
                checkbox.setAttribute('data-geoid', fullFips);
                checkbox.setAttribute('data-fips', county.fips || '');
                checkbox.setAttribute('data-name', countyName);
                checkbox.setAttribute('data-state', stateName);
                checkbox.setAttribute('data-cbsa', cbsa);
                checkbox.setAttribute('data-cbsa-name', cbsaName);
                checkbox.addEventListener('change', validateCustomCountySelection);
                
                const textSpan = document.createElement('span');
                textSpan.className = 'county-chip-text';
                textSpan.textContent = `${displayCountyName}, ${stateAbbr}`;
                
                const removeBtn = document.createElement('button');
                removeBtn.className = 'remove-chip';
                removeBtn.type = 'button';
                removeBtn.setAttribute('aria-label', `Remove ${countyName}, ${stateName}`);
                removeBtn.textContent = '×';
                removeBtn.onclick = function(e) {
                    e.stopPropagation();
                    removeCustomCounty(fullFips);
                };
                
                chip.appendChild(checkbox);
                chip.appendChild(textSpan);
                chip.appendChild(removeBtn);
                container.appendChild(chip);
            });
            
            validateCustomCountySelection();
        }
        
        hideLoading();
    } catch (error) {
        hideLoading();
        showError('Unable to load counties. Please try again.');
    }
}

// Get selected custom counties
function getSelectedCustomCounties() {
    const checkboxes = document.querySelectorAll('#customCountyCheckboxes input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => ({
        geoid: cb.value,
        fips: cb.value,
        name: cb.getAttribute('data-name'),
        state: cb.getAttribute('data-state'),
        cbsa: cb.getAttribute('data-cbsa'),
        cbsa_name: cb.getAttribute('data-cbsa-name')
    }));
}

// Validate custom county selection
function validateCustomCountySelection() {
    const selectedCounties = getSelectedCustomCounties();
    const validation = validationRules.counties.validate(selectedCounties);
    
    const container = document.getElementById('customCountyCheckboxes');
    if (container) {
        validationRules.counties.showFeedback(container, validation);
    }
    
    return validation.valid;
}

// Remove custom county
function removeCustomCounty(fips) {
    const chip = document.querySelector(`#customCountyCheckboxes .county-chip[data-fips="${fips}"]`);
    const checkbox = chip ? chip.querySelector('input[type="checkbox"]') : null;
    
    if (chip && checkbox) {
        checkbox.checked = false;
        chip.remove();
        validateCustomCountySelection();
    }
}

// Select all custom counties
function selectAllCustomCounties() {
    const checkboxes = document.querySelectorAll('#customCountyCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.checked = true;
    });
    const cbsaCode = wizardState.data.lenderAnalysis.customCbsa;
    if (cbsaCode) {
        loadCustomCountiesByMetro();
    }
    validateCustomCountySelection();
}

// Deselect all custom counties
function deselectAllCustomCounties() {
    const checkboxes = document.querySelectorAll('#customCountyCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.checked = false;
    });
    const container = document.getElementById('customCountyCheckboxes');
    if (container) {
        container.innerHTML = '';
    }
    validateCustomCountySelection();
}

window.selectAnalysisType = selectAnalysisType;
window.goBack = goBack;
window.goToStep = goToStep;
window.loadMetros = loadMetros;
window.setupMetroDropdown = setupMetroDropdown;
window.renderMetroDropdown = renderMetroDropdown;
window.loadCountiesByMetro = loadCountiesByMetro;
window.selectAllCounties = selectAllCounties;
window.deselectAllCounties = deselectAllCounties;
window.removeCounty = removeCounty;
window.loadCounties = loadCounties;
window.validateCountySelection = validateCountySelection;
window.confirmMetro = confirmMetro;
window.confirmGeography = confirmGeography;
window.confirmLender = confirmLender;
window.toggleFilterEdit = toggleFilterEdit;
window.confirmFilters = confirmFilters;
window.applyFilters = applyFilters;
window.renderFilterChips = renderFilterChips;
window.removeFilter = toggleFilter; // Alias for backward compatibility
window.createToggleSwitch = createToggleSwitch;
window.updateFilterEditor = updateFilterEditor;
window.confirmGeoScope = confirmGeoScope;
window.confirmCustomCbsa = confirmCustomCbsa;
window.confirmCustomCounties = confirmCustomCounties;
window.selectAllCustomCounties = selectAllCustomCounties;
window.deselectAllCustomCounties = deselectAllCustomCounties;
window.confirmComparisonGroup = confirmComparisonGroup;
window.confirmFiltersB = confirmFiltersB;
window.generateReport = generateReport;
window.renderStep = renderStep;
window.initWizard = initWizard;
window.updateSummaryBar = updateSummaryBar;
