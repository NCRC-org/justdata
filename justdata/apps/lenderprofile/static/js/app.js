/**
 * LenderProfile Main Application JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const institutionInput = document.getElementById('institution-name');
    const lenderSummary = document.getElementById('lender-summary');
    const lenderSummaryContent = document.getElementById('lender-summary-content');
    const reportFocusInput = document.getElementById('report-focus');
    const charCount = document.getElementById('char-count');
    const generateReportBtn = document.getElementById('generate-report-btn');
    const searchResults = document.getElementById('search-results');
    const errorMessage = document.getElementById('error-message');
    
    let currentLenderData = null;
    
    // Track rejected lenders to exclude from future searches
    function getRejectedLenders() {
        try {
            const rejected = sessionStorage.getItem('rejected_lenders');
            return rejected ? JSON.parse(rejected) : [];
        } catch (e) {
            return [];
        }
    }
    
    function addRejectedLender(lenderData) {
        try {
            const rejected = getRejectedLenders();
            // Store identifiers to exclude (LEI, RSSD, FDIC cert)
            const identifiers = {
                lei: lenderData.identifiers?.lei || lenderData.lei,
                rssd_id: lenderData.identifiers?.rssd_id || lenderData.rssd_id,
                fdic_cert: lenderData.identifiers?.fdic_cert || lenderData.fdic_cert,
                name: lenderData.identifiers?.name || lenderData.name
            };
            // Only add if it has at least one identifier
            if (identifiers.lei || identifiers.rssd_id || identifiers.fdic_cert) {
                rejected.push(identifiers);
                sessionStorage.setItem('rejected_lenders', JSON.stringify(rejected));
            }
        } catch (e) {
            console.error('Error storing rejected lender:', e);
        }
    }
    
    // Character counter for report focus
    if (reportFocusInput && charCount) {
        reportFocusInput.addEventListener('input', function() {
            const length = this.value.length;
            charCount.textContent = length;
            
            if (length > 250) {
                this.value = this.value.substring(0, 250);
                charCount.textContent = '250';
            }
        });
    }
    
    // Generate report button
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', async function() {
            if (!currentLenderData) {
                showError('Please search for a lender first');
                return;
            }
            
            const reportFocus = reportFocusInput ? reportFocusInput.value.trim() : '';
            
            // Validate focus length
            if (reportFocus && reportFocus.length > 250) {
                showError('Report focus must be 250 characters or less');
                return;
            }
            
            // Disable button
            const originalText = generateReportBtn.innerHTML;
            generateReportBtn.disabled = true;
            generateReportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating Report...';
            
            // Show progress message
            const progressMsg = document.createElement('div');
            progressMsg.className = 'progress-message';
            progressMsg.innerHTML = `
                <div style="padding: 20px; background: var(--ncrc-light-blue); border-radius: 8px; margin-top: 20px;">
                    <p><i class="fas fa-spinner fa-spin"></i> Generating comprehensive intelligence report...</p>
                    <p style="font-size: 0.9rem; color: var(--ncrc-gray); margin-top: 10px;">
                        This may take 60-90 seconds as we gather data from multiple sources.
                    </p>
                </div>
            `;
            lenderSummary.appendChild(progressMsg);
            
            try {
                const response = await fetch('/api/generate-report', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: currentLenderData.name,
                        id: currentLenderData.fdic_cert || currentLenderData.rssd_id || currentLenderData.lei,
                        identifiers: currentLenderData.identifiers,
                        report_focus: reportFocus
                    })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Report generation failed');
                }
                
                // Store report data
                sessionStorage.setItem('lenderprofile_report', JSON.stringify(data.report));
                sessionStorage.setItem('lenderprofile_report_id', data.report_id);
                
                // Redirect to report view
                window.location.href = `/report/${data.report_id}`;
                
            } catch (error) {
                showError(error.message || 'An error occurred while generating the report');
                progressMsg.remove();
            } finally {
                generateReportBtn.disabled = false;
                generateReportBtn.innerHTML = originalText;
            }
        });
    }
    
    if (searchForm) {
        searchForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const institutionName = institutionInput.value.trim();
            
            if (!institutionName) {
                showError('Please enter an institution name');
                return;
            }
            
            // Hide previous results/errors
            lenderSummary.style.display = 'none';
            searchResults.style.display = 'none';
            errorMessage.style.display = 'none';
            
            // Disable form
            const submitBtn = searchForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Searching...';
            
            try {
                // Get rejected lenders to exclude
                const excludedLenders = getRejectedLenders();
                
                const response = await fetch('/api/search-lender', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: institutionName,
                        exclude: excludedLenders  // Send excluded lenders to backend
                    })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    if (response.status === 404) {
                        showError(data.message || `No institution found matching "${institutionName}"`);
                    } else {
                        showError(data.error || 'An error occurred while searching');
                    }
                    return;
                }
                
                if (data.success) {
                    // Check if multiple candidates returned
                    if (data.multiple && data.candidates && data.candidates.length > 1) {
                        displayCandidateSelector(data.candidates, institutionName);
                    } else {
                        // Single result - display directly
                        currentLenderData = data;
                        displayLenderSummary(data);
                    }
                } else {
                    showError(data.error || 'Search failed');
                }
                
            } catch (error) {
                showError(error.message || 'An error occurred while searching');
            } finally {
                // Re-enable form
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    }
    
    function formatAddress(addressObj) {
        if (!addressObj) return 'N/A';
        
        const parts = [];
        if (addressObj.address_lines && addressObj.address_lines.length > 0) {
            parts.push(addressObj.address_lines.join(', '));
        }
        if (addressObj.city) parts.push(addressObj.city);
        if (addressObj.region) parts.push(addressObj.region);
        if (addressObj.postal_code) parts.push(addressObj.postal_code);
        if (addressObj.country && addressObj.country !== 'US') parts.push(addressObj.country);
        
        return parts.length > 0 ? parts.join(', ') : 'N/A';
    }
    
    function displayLenderSummary(data) {
        const identifiers = data.identifiers || {};
        const details = data.details || {};
        const fdicData = details.fdic_data || {};
        const gleifData = details.gleif_data || {};
        
        // Format assets - check both fdic_data and details for asset info
        let assetsDisplay = 'N/A';
        let assetsValue = null;
        
        // Try to get ASSET from fdic_data first (from financials endpoint)
        if (fdicData && fdicData.ASSET) {
            assetsValue = parseFloat(fdicData.ASSET);
        }
        // Fallback: check if assets are in details (from CFPB or other sources)
        else if (details && details.assets) {
            assetsValue = parseFloat(details.assets);
        }
        
        if (assetsValue && !isNaN(assetsValue) && assetsValue > 0) {
            if (assetsValue >= 1000000000) {
                assetsDisplay = `$${(assetsValue / 1000000000).toFixed(2)}B`;
            } else if (assetsValue >= 1000000) {
                assetsDisplay = `$${(assetsValue / 1000000).toFixed(2)}M`;
            } else {
                assetsDisplay = `$${assetsValue.toLocaleString()}`;
            }
        }
        
        // Format report date if available
        const reportDate = fdicData.REPDTE || '';
        const reportDateDisplay = reportDate ? new Date(reportDate).toLocaleDateString() : 'N/A';
        
        // Format location from FDIC
        const city = fdicData.CITY || '';
        const state = fdicData.STALP || fdicData.STATE || '';
        const fdicLocation = city && state ? `${city}, ${state}` : (city || state || 'N/A');
        
        // Get addresses from GLEIF (preferred) or FDIC
        const legalAddress = formatAddress(details.legal_address);
        const headquartersAddress = formatAddress(details.headquarters_address);
        const displayLocation = legalAddress !== 'N/A' ? legalAddress : (headquartersAddress !== 'N/A' ? headquartersAddress : fdicLocation);
        
        // Format RSSD (remove leading zeros)
        let rssdDisplay = identifiers.rssd_id || fdicData.RSSDID || 'N/A';
        if (rssdDisplay !== 'N/A' && typeof rssdDisplay === 'string') {
            rssdDisplay = rssdDisplay.replace(/^0+/, '') || '0';
        }
        
        // Format lender type - prioritize BigQuery type_name, then FDIC INSTTYPE
        let lenderType = identifiers.type || details.type || fdicData.INSTTYPE || fdicData.TYPE || 'N/A';
        if (lenderType !== 'N/A' && !identifiers.type && !details.type) {
            // Only map FDIC INSTTYPE codes if we don't have BigQuery type
            const typeMap = {
                '1': 'Commercial Bank',
                '2': 'Savings Institution',
                '3': 'National Bank',
                '4': 'State Bank',
                '11': 'Federal Savings Bank',
                '12': 'State Savings Bank'
            };
            lenderType = typeMap[lenderType] || lenderType;
        }
        
        // Format tax ID
        const taxId = details.tax_id || identifiers.tax_id || 'N/A';
        
        lenderSummaryContent.innerHTML = `
            <div class="lender-summary-item">
                <span class="lender-summary-label">Lender Name</span>
                <span class="lender-summary-value">${identifiers.name || 'N/A'}</span>
            </div>
            <div class="lender-summary-item">
                <span class="lender-summary-label">Type</span>
                <span class="lender-summary-value">${lenderType}</span>
            </div>
            <div class="lender-summary-item">
                <span class="lender-summary-label">Legal Address</span>
                <span class="lender-summary-value">${legalAddress}</span>
            </div>
            <div class="lender-summary-item">
                <span class="lender-summary-label">Headquarters Address</span>
                <span class="lender-summary-value">${headquartersAddress}</span>
            </div>
            <div class="lender-summary-item">
                <span class="lender-summary-label">Tax ID (EIN)</span>
                <span class="lender-summary-value">${taxId}</span>
            </div>
            <div class="lender-summary-item">
                <span class="lender-summary-label">FDIC Cert</span>
                <span class="lender-summary-value">${identifiers.fdic_cert || 'N/A'}</span>
            </div>
            <div class="lender-summary-item">
                <span class="lender-summary-label">RSSD ID</span>
                <span class="lender-summary-value">${rssdDisplay}</span>
            </div>
            <div class="lender-summary-item">
                <span class="lender-summary-label">LEI</span>
                <span class="lender-summary-value">${identifiers.lei || 'N/A'}</span>
            </div>
            <div class="lender-summary-item">
                <span class="lender-summary-label">Assets</span>
                <span class="lender-summary-value">${assetsDisplay}${reportDateDisplay !== 'N/A' ? ` (as of ${reportDateDisplay})` : ''}</span>
            </div>
            ${fdicData.ROA ? `
            <div class="lender-summary-item">
                <span class="lender-summary-label">ROA (Return on Assets)</span>
                <span class="lender-summary-value">${(parseFloat(fdicData.ROA) * 100).toFixed(2)}%</span>
            </div>
            ` : ''}
            ${fdicData.ROE ? `
            <div class="lender-summary-item">
                <span class="lender-summary-label">ROE (Return on Equity)</span>
                <span class="lender-summary-value">${(parseFloat(fdicData.ROE) * 100).toFixed(2)}%</span>
            </div>
            ` : ''}
            <div class="lender-summary-item">
                <span class="lender-summary-label">Confidence</span>
                <span class="lender-summary-value">${(identifiers.confidence * 100).toFixed(0)}%</span>
            </div>
            <div class="lender-summary-actions" style="grid-column: 1 / -1; margin-top: 20px; padding-top: 20px; border-top: 2px solid var(--ncrc-light-blue);">
                <button type="button" id="reject-lender-btn" class="btn btn-secondary" style="background: var(--ncrc-accent-red); color: white;">
                    <i class="fas fa-times-circle"></i> This is not the right lender
                </button>
            </div>
        `;
        
        lenderSummary.style.display = 'block';
        
        // Add event listener for reject button
        const rejectBtn = document.getElementById('reject-lender-btn');
        if (rejectBtn) {
            rejectBtn.addEventListener('click', function() {
                // Add to rejected lenders list
                if (currentLenderData) {
                    addRejectedLender(currentLenderData);
                    console.log('Rejected lender added to exclusion list:', currentLenderData.identifiers?.name || currentLenderData.name);
                }
                
                // Clear the lender summary
                lenderSummary.style.display = 'none';
                lenderSummaryContent.innerHTML = '';
                currentLenderData = null;
                
                // Clear and focus the search input
                if (institutionInput) {
                    institutionInput.value = '';
                    institutionInput.focus();
                }
                
                // Clear report focus
                if (reportFocusInput) {
                    reportFocusInput.value = '';
                    charCount.textContent = '0';
                }
                
                // Hide any error messages
                if (errorMessage) {
                    errorMessage.style.display = 'none';
                }
            });
        }
        
        // Reset report focus
        if (reportFocusInput) {
            reportFocusInput.value = '';
            charCount.textContent = '0';
        }
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        lenderSummary.style.display = 'none';
        searchResults.style.display = 'none';
    }
    
    function displayCandidateSelector(candidates, query) {
        // Hide other elements
        lenderSummary.style.display = 'none';
        errorMessage.style.display = 'none';
        
        // Create dropdown selector
        const selectorHtml = `
            <div class="candidate-selector">
                <h3><i class="fas fa-list"></i> Multiple Institutions Found</h3>
                <p class="selector-description">
                    We found ${candidates.length} institutions matching "${escapeHtml(query)}". Please select the correct one:
                </p>
                <div class="candidate-list">
                    ${candidates.map((candidate, index) => `
                        <div class="candidate-item" data-index="${index}">
                            <div class="candidate-name">${escapeHtml(candidate.name)}</div>
                            <div class="candidate-location">
                                <i class="fas fa-map-marker-alt"></i> ${escapeHtml(candidate.location || 'Location unknown')}
                            </div>
                            ${candidate.type ? `<div class="candidate-type">${escapeHtml(candidate.type)}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        searchResults.innerHTML = selectorHtml;
        searchResults.style.display = 'block';
        
        // Add click handlers
        const candidateItems = searchResults.querySelectorAll('.candidate-item');
        candidateItems.forEach((item, index) => {
            item.addEventListener('click', async function() {
                const candidate = candidates[index];
                
                // Show loading state
                item.classList.add('loading');
                const originalHtml = item.innerHTML;
                item.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
                
                // Fetch full details for selected candidate
                try {
                    const response = await fetch('/api/search-lender', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            query: candidate.name,
                            exclude: getRejectedLenders(),
                            selected_candidate: {
                                lei: candidate.lei,
                                rssd_id: candidate.rssd_id,
                                fdic_cert: candidate.fdic_cert,
                                name: candidate.name
                            }
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        currentLenderData = data;
                        searchResults.style.display = 'none';
                        displayLenderSummary(data);
                    } else {
                        showError(data.error || 'Error loading lender details');
                        item.classList.remove('loading');
                        item.innerHTML = originalHtml;
                    }
                } catch (error) {
                    showError('Error loading lender details: ' + error.message);
                    item.classList.remove('loading');
                    item.innerHTML = originalHtml;
                }
            });
        });
    }
    
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});

