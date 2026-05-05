// DataExplorer Wizard - step2A/step3A: Area-analysis geography selection.
// states + metros + counties dropdowns and confirms. Moved verbatim from
// wizard-steps.js. Function bodies untouched.

import {
    wizardState,
    validationRules,
    saveToCache,
    transitionToStep,
    showError,
    showLoading,
    hideLoading,
    showStepSuccess,
    getSelectedCounties,
} from '../wizard.js';
import { apiClient } from '../api-client.js';

// Geography functions
export async function loadStates() {
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

export async function loadMetros() {
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
export function setupMetroDropdown() {
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

export function showMetroDropdown() {
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

export function hideMetroDropdown() {
    const dropdownWrapper = document.querySelector('.metro-dropdown-wrapper');
    const selectButton = document.getElementById('metroSelectButton');
    if (dropdownWrapper) {
        dropdownWrapper.style.display = 'none';
    }
    if (selectButton) {
        selectButton.setAttribute('aria-expanded', 'false');
    }
}

export function renderMetroDropdown(metros) {
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
export function navigateMetroDropdown(direction) {
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
export function selectHighlightedMetro() {
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
export function selectMetro(code, name) {
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
export async function loadCountiesByMetro() {
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
export function removeCounty(fips) {
    const chip = document.querySelector(`#countyCheckboxes .county-chip[data-fips="${fips}"]`);
    const checkbox = chip ? chip.querySelector('input[type="checkbox"]') : null;
    
    if (chip && checkbox) {
        checkbox.checked = false;
        chip.remove();
        validateCountySelection();
    }
}

export function selectAllCounties() {
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

export function deselectAllCounties() {
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

export async function loadCounties() {
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

export function validateCountySelection() {
    const selectedCounties = getSelectedCounties();
    const validation = validationRules.counties.validate(selectedCounties);
    
    const container = document.getElementById('countyCheckboxes');
    if (container) {
        validationRules.counties.showFeedback(container, validation);
    }
    
    return validation.valid;
}

// LOCKED: Part of Area Analysis Structure
export async function confirmMetro() {
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
export function confirmGeography() {
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

