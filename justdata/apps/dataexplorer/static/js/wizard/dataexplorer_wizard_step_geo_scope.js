// DataExplorer Wizard - lender-analysis confirms: step3B (geographic scope),
// step3B5 (custom CBSA), step3B6 (custom counties), step4B (comparison group),
// step5B (filters confirm). Moved verbatim from wizard-steps.js. Function
// bodies untouched.

import {
    wizardState,
    showError,
    showStepSuccess,
    transitionToStep,
} from '../wizard.js';
import {
    loadCustomCountiesByMetro,
    getSelectedCustomCounties,
    validateCustomCountySelection,
} from './dataexplorer_wizard_step_geography_custom.js';
import { validateFilters } from './dataexplorer_wizard_step_filters.js';

// Geography scope
export function confirmGeoScope() {
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
export async function confirmCustomCbsa() {
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
export function confirmCustomCounties() {
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
export function confirmComparisonGroup() {
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

export function confirmFiltersB() {
    if (!validateFilters()) {
        return;
    }

    showStepSuccess(document.querySelector('.step-card.active'));
    setTimeout(() => {
        transitionToStep('step6B');
    }, 500);
}
