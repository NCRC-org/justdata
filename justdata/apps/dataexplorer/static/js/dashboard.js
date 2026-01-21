// DataExplorer 2.0 Dashboard JavaScript
// FIXED: Wrapped in DOMContentLoaded to ensure DOM is ready before attaching event listeners

let selectedLenderId = null;
let selectedLenderName = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    // Mode switching
    const modeButtons = document.querySelectorAll('.mode-btn');
    if (modeButtons.length === 0) {
        console.warn('No mode buttons found - dashboard may not be fully loaded');
        return;
    }

    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            if (mode) {
                switchMode(mode);
            }
        });
    });

    // Initialize run analysis button
    const runAreaBtn = document.getElementById('run-area-analysis');
    if (runAreaBtn) {
        runAreaBtn.addEventListener('click', runAreaAnalysis);
    }

    // Initialize lender search
    const searchLenderBtn = document.getElementById('search-lender');
    if (searchLenderBtn) {
        searchLenderBtn.addEventListener('click', searchLender);
    }

    // Initialize lender analysis
    const runLenderBtn = document.getElementById('run-lender-analysis');
    if (runLenderBtn) {
        runLenderBtn.addEventListener('click', runLenderAnalysis);
    }

    // Allow pressing Enter in search fields
    const lenderSearchInput = document.getElementById('lender-search');
    if (lenderSearchInput) {
        lenderSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchLender();
            }
        });
    }

    console.log('Dashboard initialized successfully');
}

function switchMode(mode) {
    // Update buttons
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-mode="${mode}"]`).classList.add('active');
    
    // Update panels
    document.querySelectorAll('.mode-panel').forEach(p => p.classList.remove('active'));
    document.getElementById(`${mode}-mode`).classList.add('active');
    
    // Clear results
    clearResults();
}

function clearResults() {
    const areaResults = document.getElementById('area-results');
    const lenderResults = document.getElementById('lender-results-panel');
    if (areaResults) areaResults.style.display = 'none';
    if (lenderResults) lenderResults.style.display = 'none';
}

// Area Analysis
async function runAreaAnalysis() {
    const dataTypeEl = document.getElementById('data-type');
    const yearsEl = document.getElementById('years');
    const geoidsEl = document.getElementById('geoids');

    if (!dataTypeEl || !yearsEl || !geoidsEl) {
        showError('Form elements not found');
        return;
    }

    const dataType = dataTypeEl.value;
    const yearsInput = yearsEl.value.trim();
    const geoidsInput = geoidsEl.value.trim();

    // Validate inputs
    if (!yearsInput || !geoidsInput) {
        showError('Please provide both years and GEOIDs');
        return;
    }

    const years = yearsInput.split(',').map(y => parseInt(y.trim())).filter(y => !isNaN(y));
    const geoids = geoidsInput.split(',').map(g => g.trim()).filter(g => g);

    if (years.length === 0) {
        showError('Please provide valid years');
        return;
    }

    if (geoids.length === 0) {
        showError('Please provide valid GEOIDs');
        return;
    }

    // Show loading
    const resultsPanel = document.getElementById('area-results');
    if (resultsPanel) {
        resultsPanel.style.display = 'block';
    }
    const resultsContent = document.getElementById('area-results-content');
    if (resultsContent) {
        resultsContent.innerHTML = '<div class="loading">Running analysis...</div>';
    }

    try {
        const endpoint = `/api/area/${dataType}/analysis`;
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                geoids: geoids,
                years: years,
                filters: {}
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Analysis failed');
        }

        displayAreaResults(result.data);

    } catch (error) {
        showError(`Error: ${error.message}`);
    }
}

function displayAreaResults(data) {
    const content = document.getElementById('area-results-content');
    
    let html = '<div class="success-message">Analysis completed successfully!</div>';
    
    // Summary
    if (data.summary) {
        html += '<h4>Summary</h4><ul>';
        for (const [key, value] of Object.entries(data.summary)) {
            html += `<li><strong>${key}:</strong> ${formatNumber(value)}</li>`;
        }
        html += '</ul>';
    }
    
    // By Year
    if (data.by_year && data.by_year.length > 0) {
        html += '<h4>By Year</h4>';
        html += '<table><thead><tr>';
        Object.keys(data.by_year[0]).forEach(key => {
            html += `<th>${key}</th>`;
        });
        html += '</tr></thead><tbody>';
        data.by_year.forEach(row => {
            html += '<tr>';
            Object.values(row).forEach(val => {
                html += `<td>${formatNumber(val)}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
    }
    
    // By Lender
    if (data.by_lender && data.by_lender.length > 0) {
        html += '<h4>Top Lenders</h4>';
        html += '<table><thead><tr>';
        Object.keys(data.by_lender[0]).forEach(key => {
            html += `<th>${key}</th>`;
        });
        html += '</tr></thead><tbody>';
        data.by_lender.forEach(row => {
            html += '<tr>';
            Object.values(row).forEach(val => {
                html += `<td>${formatNumber(val)}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
    }
    
    content.innerHTML = html;
}

// Lender Search
async function searchLender() {
    const lenderSearchEl = document.getElementById('lender-search');
    if (!lenderSearchEl) {
        showError('Search field not found');
        return;
    }

    const lenderName = lenderSearchEl.value.trim();

    if (!lenderName || lenderName.length < 2) {
        showError('Please enter at least 2 characters');
        return;
    }

    const lenderResults = document.getElementById('lender-results');
    const lenderOptions = document.getElementById('lender-options');

    if (lenderResults) {
        lenderResults.style.display = 'block';
    }
    if (lenderOptions) {
        lenderOptions.innerHTML = '<div class="loading">Searching...</div>';
    }

    try {
        const response = await fetch('/api/lender/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                lender_name: lenderName,
                exact_match: false
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Search failed');
        }

        displayLenderOptions(result.data);

    } catch (error) {
        showError(`Error: ${error.message}`);
    }
}

function displayLenderOptions(lenders) {
    const optionsDiv = document.getElementById('lender-options');
    
    if (!lenders || lenders.length === 0) {
        optionsDiv.innerHTML = '<p>No lenders found</p>';
        return;
    }
    
    let html = '';
    lenders.forEach(lender => {
        html += `<div class="lender-option" data-lender-id="${lender.lender_id}" data-lender-name="${lender.lender_name}">
            <strong>${lender.lender_name}</strong> (ID: ${lender.lender_id})
        </div>`;
    });
    
    optionsDiv.innerHTML = html;
    
    // Add click handlers
    document.querySelectorAll('.lender-option').forEach(option => {
        option.addEventListener('click', () => {
            selectedLenderId = option.dataset.lenderId;
            selectedLenderName = option.dataset.lenderName;
            
            // Update UI
            document.getElementById('selected-lender-info').style.display = 'block';
            document.getElementById('lender-details').innerHTML = `
                <strong>${selectedLenderName}</strong> (ID: ${selectedLenderId})
            `;
            
            document.getElementById('run-lender-analysis').disabled = false;
            
            // Highlight selected
            document.querySelectorAll('.lender-option').forEach(o => o.style.background = 'white');
            option.style.background = '#e7f3ff';
        });
    });
}

// Lender Analysis
async function runLenderAnalysis() {
    if (!selectedLenderId) {
        showError('Please select a lender first');
        return;
    }

    const lenderYearsEl = document.getElementById('lender-years');
    const enablePeerComparisonEl = document.getElementById('enable-peer-comparison');

    const yearsInput = lenderYearsEl ? lenderYearsEl.value.trim() : '';
    const enablePeerComparison = enablePeerComparisonEl ? enablePeerComparisonEl.checked : true;

    const years = yearsInput ? yearsInput.split(',').map(y => parseInt(y.trim())).filter(y => !isNaN(y)) : [];

    const resultsPanel = document.getElementById('lender-results-panel');
    const resultsContent = document.getElementById('lender-results-content');

    if (resultsPanel) {
        resultsPanel.style.display = 'block';
    }
    if (resultsContent) {
        resultsContent.innerHTML = '<div class="loading">Running analysis... This may take up to 60 seconds.</div>';
    }

    try {
        // Use AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout

        const response = await fetch('/api/lender/analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                lender_id: selectedLenderId,
                data_types: ['hmda', 'sb', 'branches'],
                years: years,
                geoids: [],
                enable_peer_comparison: enablePeerComparison
            }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Analysis failed');
        }

        displayLenderResults(result.data);

    } catch (error) {
        if (error.name === 'AbortError') {
            showError('Analysis timed out. Please try again with fewer years or disable peer comparison.');
        } else {
            showError(`Error: ${error.message}`);
        }
    }
}

function displayLenderResults(data) {
    const content = document.getElementById('lender-results-content');
    
    let html = '<div class="success-message">Analysis completed successfully!</div>';
    
    // HMDA Results
    if (data.hmda) {
        html += '<h4>HMDA Mortgage Lending</h4>';
        html += '<h5>Subject Lender</h5>';
        html += '<ul>';
        for (const [key, value] of Object.entries(data.hmda.subject)) {
            html += `<li><strong>${key}:</strong> ${formatNumber(value)}</li>`;
        }
        html += '</ul>';
        
        if (data.hmda.comparison && data.hmda.comparison.peer_average) {
            html += '<h5>Peer Comparison</h5>';
            html += '<ul>';
            for (const [key, value] of Object.entries(data.hmda.comparison.peer_average)) {
                html += `<li><strong>Peer Average ${key}:</strong> ${formatNumber(value)}</li>`;
            }
            html += '</ul>';
        }
    }
    
    // SB Results
    if (data.sb) {
        html += '<h4>Small Business Lending</h4>';
        html += '<ul>';
        for (const [key, value] of Object.entries(data.sb.subject)) {
            html += `<li><strong>${key}:</strong> ${formatNumber(value)}</li>`;
        }
        html += '</ul>';
    }
    
    // Branch Results
    if (data.branches) {
        html += '<h4>Bank Branches</h4>';
        html += '<ul>';
        for (const [key, value] of Object.entries(data.branches)) {
            if (key !== 'by_county') {
                html += `<li><strong>${key}:</strong> ${formatNumber(value)}</li>`;
            }
        }
        html += '</ul>';
    }
    
    content.innerHTML = html;
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    
    // Insert at top of current mode panel
    const activePanel = document.querySelector('.mode-panel.active');
    activePanel.insertBefore(errorDiv, activePanel.firstChild);
    
    // Remove after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

function formatNumber(num) {
    if (typeof num === 'number') {
        if (num >= 1000000) {
            return '$' + (num / 1000000).toFixed(2) + 'M';
        } else if (num >= 1000) {
            return '$' + (num / 1000).toFixed(2) + 'K';
        } else {
            return num.toLocaleString();
        }
    }
    return num;
}
