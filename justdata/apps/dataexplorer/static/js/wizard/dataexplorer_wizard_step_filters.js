// DataExplorer Wizard - step4A/step5B: Loan filter chips (occupancy, total
// units, construction type, loan purpose, loan type, action taken,
// reverse-mortgage toggle). Two render entry points (step4A and step5B
// share the same filter UI but render into different containers). Moved
// verbatim from wizard-steps.js. Function bodies untouched.

import {
    wizardState,
    showError,
    showStepSuccess,
    transitionToStep,
} from '../wizard.js';

// Filter functions
export function toggleFilterEdit() {
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

export function applyFilters() {
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
export function createToggleSwitch(id, currentValue, leftLabel, rightLabel, onChange) {
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
export function renderFilterChips() {
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
export function renderFilterChipsB() {
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

export function createFilterGroup(label) {
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
export function createFilterChipBox(category, label, value, isSelected, isSingleSelect) {
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
export function toggleFilter(category, value, isSingleSelect) {
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
export function updateFilterChipState(chip, isSelected) {
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

export function updateFilterEditor() {
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
export function confirmFilters() {
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
