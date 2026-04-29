// DataExplorer Wizard Steps Implementation
// Complete step rendering and interaction logic
//
// Orchestrator: imports state/util from wizard.js and apiClient from api-client.js,
// owns the DOMContentLoaded init block, and (at the bottom) exposes the minimal set
// of functions referenced from inline onclick= attributes via a window shim.

import {
    wizardState,
    stepPaths,
    validationRules,
    saveToCache,
    transitionToStep,
    showError,
    showLoading,
    hideLoading,
    showStepSuccess,
    getSelectedCounties,
    generateStepIndicators,
    generateSummaryDetails,
    initializeSmartDefaults,
    initSwipeGestures,
    initAccessibility,
} from './wizard.js';
import { apiClient } from './api-client.js';
import { cards, getInstitutionCategory } from './wizard/dataexplorer_wizard_cards.js';
import {
    loadLenders,
    setupLenderDropdown,
    showLenderDropdown,
    hideLenderDropdown,
    renderLenderDropdown,
    navigateLenderDropdown,
    selectHighlightedLender,
    selectLender,
    updateBranchOptionState,
    displayLenderInfo,
    createInfoItem,
    createInfoItemWithLink,
    validateLenderSearch,
    confirmLender,
} from './wizard/dataexplorer_wizard_step_lender.js';
import {
    loadStates,
    loadMetros,
    setupMetroDropdown,
    showMetroDropdown,
    hideMetroDropdown,
    renderMetroDropdown,
    navigateMetroDropdown,
    selectHighlightedMetro,
    selectMetro,
    loadCountiesByMetro,
    removeCounty,
    selectAllCounties,
    deselectAllCounties,
    loadCounties,
    validateCountySelection,
    confirmMetro,
    confirmGeography,
} from './wizard/dataexplorer_wizard_step_geography.js';
import {
    setupCustomMetroDropdown,
    showCustomMetroDropdown,
    hideCustomMetroDropdown,
    renderCustomMetroDropdown,
    selectCustomMetro,
    navigateCustomMetroDropdown,
    selectHighlightedCustomMetro,
    loadCustomCountiesByMetro,
    getSelectedCustomCounties,
    validateCustomCountySelection,
    removeCustomCounty,
    selectAllCustomCounties,
    deselectAllCustomCounties,
} from './wizard/dataexplorer_wizard_step_geography_custom.js';
// Re-export validateLenderSearch for wizard.js (it imports from the orchestrator).
export { validateLenderSearch } from './wizard/dataexplorer_wizard_step_lender.js';


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
export function renderStep(stepKey) {
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
export function goBack() {
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
export function validateFilters() {
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

        // Check for no_data response (lender has no HMDA data in selected geography)
        if (result.no_data === true) {
            // Redirect to no-data info page instead of progress page
            const params = new URLSearchParams({
                lender_name: result.lender_name || wizardState.data.lender?.name || 'the selected lender',
                county_count: result.county_count || '0',
                year_range: result.year_range || ''
            });
            window.location.href = `/dataexplorer/no-data?${params.toString()}`;
            return;
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


// ----------------------------------------------------------------------------
// Wizard initialization (moved from inline <script> in _wizard_scripts.html so it
// runs inside the module graph; modules are deferred, so DOMContentLoaded fires
// after the module loads).
// ----------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
    initializeSmartDefaults();
    // createSummaryBar(); // Removed - summary bar not needed
    initSwipeGestures();
    initAccessibility();
    initWizard();

    // Hide swipe indicator on desktop
    if (window.innerWidth > 768) {
        const swipeIndicator = document.getElementById('swipeIndicator');
        if (swipeIndicator) {
            swipeIndicator.style.display = 'none';
        }
    }
});

// ----------------------------------------------------------------------------
// Window exports for inline onclick handlers — remove when onclick= is replaced
// with event listeners. Only includes symbols referenced from inline HTML event
// attributes (in templates and in HTML strings rendered by JS), nothing else.
// ----------------------------------------------------------------------------
window.selectAnalysisType = selectAnalysisType;
window.selectAllCounties = selectAllCounties;
window.deselectAllCounties = deselectAllCounties;
window.selectAllCustomCounties = selectAllCustomCounties;
window.deselectAllCustomCounties = deselectAllCustomCounties;
window.goBack = goBack;
window.goToStep = goToStep;
window.toggleFilterEdit = toggleFilterEdit;
window.selectAutocompleteLender = selectAutocompleteLender;
window.highlightAutocompleteItem = highlightAutocompleteItem;
window.validateCountySelection = validateCountySelection;
window.confirmMetro = confirmMetro;
window.confirmGeography = confirmGeography;
window.confirmFilters = confirmFilters;
window.generateReport = generateReport;
window.confirmLender = confirmLender;
window.confirmGeoScope = confirmGeoScope;
window.confirmCustomCbsa = confirmCustomCbsa;
window.confirmCustomCounties = confirmCustomCounties;
window.confirmComparisonGroup = confirmComparisonGroup;
window.confirmFiltersB = confirmFiltersB;
