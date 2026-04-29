// DataExplorer Wizard - step2B: Lender selection (search dropdown, GLEIF lookup,
// confirmation, branch-option gating). Moved verbatim from wizard-steps.js.

import {
    wizardState,
    showError,
    showLoading,
    hideLoading,
    showStepSuccess,
    transitionToStep,
    saveToCache,
} from '../wizard.js';
import { apiClient } from '../api-client.js';
import { getInstitutionCategory } from './dataexplorer_wizard_cards.js';

// Lender functions - Dropdown with search (similar to metro selector)
export async function loadLenders() {
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

export function setupLenderDropdown() {
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
export async function performLenderSearch(query) {
    // Filtering is now done in setupLenderDropdown input handler
    // This function is kept for compatibility but not actively used
}

export function showLenderDropdown() {
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

export function hideLenderDropdown() {
    const dropdownWrapper = document.querySelector('.lender-dropdown-wrapper');
    const selectButton = document.getElementById('lenderSelectButton');

    if (dropdownWrapper) {
        dropdownWrapper.classList.remove('show');
    }

    if (selectButton) {
        selectButton.setAttribute('aria-expanded', 'false');
    }
}

export function renderLenderDropdown(lenders) {
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

export function navigateLenderDropdown(direction) {
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

export function selectHighlightedLender() {
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

export async function selectLender(lender) {
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
        console.log('[selectLender] Raw lender object from search:', JSON.stringify(lender, null, 2));
        console.log('[selectLender] type_name from search:', lender.type_name, '| type:', lender.type);
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
                    // Update lender type from API if available (overwrite search value which may be empty)
                    if (details.type_name || details.type) {
                        const apiType = details.type_name || details.type;
                        wizardState.data.lender.type = apiType;
                        wizardState.data.lender.type_name = apiType;
                        console.log('[selectLender] Set lender type from API to:', apiType);
                    } else {
                        console.log('[selectLender] API did not return type_name, current type:', wizardState.data.lender.type);
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
export function updateBranchOptionState() {
    const lenderType = wizardState.data.lender?.type || wizardState.data.lender?.type_name || '';
    const lenderTypeLower = lenderType.toLowerCase();
    const lenderRssd = wizardState.data.lender?.rssd;

    // Check if lender type explicitly indicates NON-BANK (these don't have branch networks)
    // Non-banks include: mortgage companies, non-depository institutions, credit unions (handled separately)
    const isNonBankByType = lenderTypeLower.includes('mortgage') ||
                            lenderTypeLower.includes('non-depository') ||
                            lenderTypeLower.includes('nondepository') ||
                            lenderTypeLower.includes('credit union') ||
                            lenderTypeLower.includes('finance company');

    // Check if lender is a bank (contains "bank" or "affiliate" in type name)
    const isBankByType = lenderTypeLower.includes('bank') || lenderTypeLower.includes('affiliate');
    const hasRssd = lenderRssd && lenderRssd.trim() !== '' && lenderRssd !== '0000000000';

    // Non-banks explicitly disabled, even if they have RSSD (which may be from parent/affiliate)
    // Banks enabled by type, or by having RSSD (for edge cases where type is unknown)
    const canUseBranchOption = !isNonBankByType && (isBankByType || hasRssd);

    console.log('[updateBranchOptionState] lenderType:', lenderType, 'rssd:', lenderRssd, 'isNonBankByType:', isNonBankByType, 'isBankByType:', isBankByType, 'hasRssd:', hasRssd, 'canUseBranchOption:', canUseBranchOption);

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
            branchLabel.title = 'Branch data is only available for banks (not mortgage companies or credit unions)';
        } else {
            branchLabel.style.opacity = '1';
            branchLabel.style.cursor = 'pointer';
            branchLabel.title = '';
        }
    }
}

// Track GLEIF loading state
let gleifLoadingPromise = null;

export async function displayLenderInfo(lei, name, lenderData) {
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

export function createInfoItem(label, value) {
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

export function createInfoItemWithLink(label, value, linkUrl, linkText) {
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

export function validateLenderSearch() {
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

export async function confirmLender() {
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
