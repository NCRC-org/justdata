// DataExplorer Wizard - step3B5/step3B6: Custom CBSA selection (mirror of the
// area-analysis geography step, with custom* IDs to avoid clashing). Moved
// verbatim from wizard-steps.js. Function bodies untouched.

import {
    wizardState,
    validationRules,
    showError,
    showLoading,
    hideLoading,
} from '../wizard.js';
import { apiClient } from '../api-client.js';

export function setupCustomMetroDropdown() {
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

export function showCustomMetroDropdown() {
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

export function hideCustomMetroDropdown() {
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

export function renderCustomMetroDropdown(metros) {
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

export function selectCustomMetro(code, name) {
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

export function navigateCustomMetroDropdown(direction) {
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

export function selectHighlightedCustomMetro() {
    const metros = wizardState.cache.currentCustomMetros || [];
    const currentIndex = wizardState.cache.selectedCustomMetroIndex;
    
    if (currentIndex >= 0 && currentIndex < metros.length) {
        const metro = metros[currentIndex];
        selectCustomMetro(metro.code, metro.name);
    }
}

// Load counties for custom selection (reuses area analysis logic)
export async function loadCustomCountiesByMetro() {
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
export function getSelectedCustomCounties() {
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
export function validateCustomCountySelection() {
    const selectedCounties = getSelectedCustomCounties();
    const validation = validationRules.counties.validate(selectedCounties);
    
    const container = document.getElementById('customCountyCheckboxes');
    if (container) {
        validationRules.counties.showFeedback(container, validation);
    }
    
    return validation.valid;
}

// Remove custom county
export function removeCustomCounty(fips) {
    const chip = document.querySelector(`#customCountyCheckboxes .county-chip[data-fips="${fips}"]`);
    const checkbox = chip ? chip.querySelector('input[type="checkbox"]') : null;
    
    if (chip && checkbox) {
        checkbox.checked = false;
        chip.remove();
        validateCustomCountySelection();
    }
}

// Select all custom counties
export function selectAllCustomCounties() {
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
export function deselectAllCustomCounties() {
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
