// DataExplorer Wizard - step1: Analysis-type selection (Area vs Lender) and the
// related lender-autocomplete dropdown. Moved verbatim from wizard-steps.js.
// Function bodies untouched.

import {
    wizardState,
    showLoading,
    hideLoading,
    transitionToStep,
} from '../wizard.js';
import { apiClient } from '../api-client.js';
import { selectLender } from './dataexplorer_wizard_step_lender.js';
import { loadMetros } from './dataexplorer_wizard_step_geography.js';

// Debounce variable for autocomplete
let autocompleteDebounceTimer = null;

// Perform autocomplete search
export async function performAutocompleteSearch(query) {
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
export function selectAutocompleteLender(index) {
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
export function navigateAutocomplete(direction) {
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
export function highlightAutocompleteItem(element) {
    const dropdown = document.getElementById('lenderAutocomplete');
    if (!dropdown) return;

    const items = dropdown.querySelectorAll('.autocomplete-item');
    items.forEach(item => item.classList.remove('selected'));
    element.classList.add('selected');
}

// Hide autocomplete dropdown
export function hideAutocomplete() {
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
export function selectAnalysisType(type) {
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
