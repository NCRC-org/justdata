// DataExplorer Wizard - card definitions and lender-type classification helper.
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
// DO NOT MODIFY WITHOUT USER APPROVAL.

// Institution Type Helper - Classify lenders by branch availability in FDIC SOD data.
// Note: Credit unions have branches but they're in NCUA data, not FDIC - will add in v2.
export function getInstitutionCategory(typeName) {
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

export const cards = {
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
