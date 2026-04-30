// DataExplorer Wizard - cross-step navigation, rendering, and listener wiring.
// Owns initWizard, the progress-dot UI, the per-step header buttons (Back/Next),
// renderStep, and attachStepListeners. Moved verbatim from wizard-steps.js.
// Function bodies untouched.

import {
    wizardState,
    stepPaths,
    transitionToStep,
} from '../wizard.js';
import { cards } from './dataexplorer_wizard_cards.js';
import {
    setupMetroDropdown,
    loadMetros,
    loadCountiesByMetro,
} from './dataexplorer_wizard_step_geography.js';
import {
    setupCustomMetroDropdown,
    loadCustomCountiesByMetro,
} from './dataexplorer_wizard_step_geography_custom.js';
import {
    updateBranchOptionState,
    setupLenderDropdown,
} from './dataexplorer_wizard_step_lender.js';
import {
    renderFilterChips,
    renderFilterChipsB,
    toggleFilterEdit,
} from './dataexplorer_wizard_step_filters.js';

// Initialize wizard
export function initWizard() {
    renderStep('step1');
}

// Navigate to a step by clicking a progress dot
export function navigateToStepByDot(stepNum) {
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
export function generateProgressDots(stepKey) {
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
export function generateHeaderButtons(stepKey) {
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
export function attachProgressDotListeners() {
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

export function attachStepListeners(stepKey) {
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

export function goToStep(stepNum) {
    const currentPath = wizardState.analysisType ? stepPaths[wizardState.analysisType] : ['step1'];
    if (stepNum > 0 && stepNum <= currentPath.length) {
        const targetStep = currentPath[stepNum - 1];
        transitionToStep(targetStep, 'backward');
    }
}
