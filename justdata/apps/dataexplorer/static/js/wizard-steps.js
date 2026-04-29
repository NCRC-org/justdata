// DataExplorer Wizard Steps Orchestrator
//
// Thin orchestrator. Wires up the DOMContentLoaded init hook and exposes the
// minimal set of functions referenced from inline onclick= attributes via a
// concentrated window shim. Step logic lives in ./wizard/*.js modules.
//
// wizard.js consumes validateLenderSearch / validateFilters / renderStep /
// goBack from this file, so the orchestrator re-exports them to keep wizard.js
// import paths stable.

import {
    initializeSmartDefaults,
    initSwipeGestures,
    initAccessibility,
} from './wizard.js';
import {
    initWizard,
    goBack,
    goToStep,
} from './wizard/dataexplorer_wizard_navigation.js';
import {
    selectAnalysisType,
    selectAutocompleteLender,
    highlightAutocompleteItem,
} from './wizard/dataexplorer_wizard_step_analysis_type.js';
import {
    selectAllCounties,
    deselectAllCounties,
    validateCountySelection,
    confirmMetro,
    confirmGeography,
} from './wizard/dataexplorer_wizard_step_geography.js';
import {
    selectAllCustomCounties,
    deselectAllCustomCounties,
} from './wizard/dataexplorer_wizard_step_geography_custom.js';
import {
    confirmLender,
} from './wizard/dataexplorer_wizard_step_lender.js';
import {
    toggleFilterEdit,
    confirmFilters,
} from './wizard/dataexplorer_wizard_step_filters.js';
import {
    confirmGeoScope,
    confirmCustomCbsa,
    confirmCustomCounties,
    confirmComparisonGroup,
    confirmFiltersB,
} from './wizard/dataexplorer_wizard_step_geo_scope.js';
import { generateReport } from './wizard/dataexplorer_wizard_step_report.js';

// Re-exports for wizard.js (which imports validators + renderStep + goBack
// from this orchestrator). The validators are overridden versions that live
// in their step modules; under classic scripts the wizard-steps.js definitions
// shadowed wizard.js's stubs at load order, and the re-export preserves that.
export { validateLenderSearch } from './wizard/dataexplorer_wizard_step_lender.js';
export { validateFilters } from './wizard/dataexplorer_wizard_step_filters.js';
export { renderStep, goBack } from './wizard/dataexplorer_wizard_navigation.js';

// ----------------------------------------------------------------------------
// Wizard initialization (moved from inline <script> in _wizard_scripts.html so
// it runs inside the module graph; modules are deferred, so DOMContentLoaded
// fires after the module loads).
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
