// LoanTrends App JavaScript
// Handles form submission, progress tracking, and report rendering

console.log('LoanTrends app.js loaded');

// DOM Elements
let analysisForm, submitBtn, progressSection, resultsSection, errorSection, progressText, progressFill;
let currentProgress = 0;
let eventSource = null;

// Initialize when DOM is ready
$(document).ready(function() {
    initDOMElements();
    setupFormHandler();
    setupTimePeriodHandler();
});

function initDOMElements() {
    analysisForm = document.getElementById('analysisForm');
    submitBtn = document.getElementById('submitBtn');
    progressSection = document.getElementById('progressSection');
    resultsSection = document.getElementById('resultsSection');
    errorSection = document.getElementById('errorSection');
    progressText = document.getElementById('progressText');
    progressFill = document.getElementById('progressFill');
}

function setupTimePeriodHandler() {
    const timePeriodSelect = document.getElementById('time_period');
    const customTimePeriod = document.getElementById('customTimePeriod');
    
    if (timePeriodSelect) {
        timePeriodSelect.addEventListener('change', function() {
            if (this.value === 'custom') {
                customTimePeriod.style.display = 'block';
            } else {
                customTimePeriod.style.display = 'none';
            }
        });
    }
}

function setupFormHandler() {
    if (!analysisForm) return;
    
    analysisForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get selected endpoints
        const selectedEndpoints = [];
        const checkboxes = analysisForm.querySelectorAll('input[name="selected_endpoints"]:checked');
        checkboxes.forEach(cb => selectedEndpoints.push(cb.value));
        
        if (selectedEndpoints.length === 0) {
            alert('Please select at least one metric to analyze.');
            return;
        }
        
        // Get time period
        const timePeriod = document.getElementById('time_period').value;
        let startQuarter = null;
        let endQuarter = null;
        
        if (timePeriod === 'custom') {
            startQuarter = document.getElementById('start_quarter').value.trim();
            endQuarter = document.getElementById('end_quarter').value.trim();
            
            if (!startQuarter || !endQuarter) {
                alert('Please specify both start and end quarters for custom time period.');
                return;
            }
            
            // Validate quarter format (YYYY-QN)
            const quarterPattern = /^\d{4}-Q[1-4]$/;
            if (!quarterPattern.test(startQuarter) || !quarterPattern.test(endQuarter)) {
                alert('Quarter format must be YYYY-QN (e.g., 2020-Q1)');
                return;
            }
        }
        
        // Prepare request data
        const requestData = {
            selected_endpoints: selectedEndpoints,
            time_period: timePeriod
        };
        
        if (timePeriod === 'custom') {
            requestData.start_quarter = startQuarter;
            requestData.end_quarter = endQuarter;
        }
        
        // Show progress, hide results/error
        showProgress();
        hideResults();
        hideError();
        
        // Disable submit button
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Analyzing...</span>';
        }
        
        try {
            // Submit analysis request
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Analysis request failed');
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Analysis failed');
            }
            
            const jobId = result.job_id;
            
            // Start progress tracking
            trackProgress(jobId);
            
        } catch (error) {
            console.error('Error starting analysis:', error);
            showError(error.message || 'Network error. Please check your connection and try again.');
            hideProgress();
            
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-magic"></i> <span>Generate Analysis</span>';
            }
        }
    });
}

function trackProgress(jobId) {
    // Close existing connection if any
    if (eventSource) {
        eventSource.close();
    }
    
    // Create new EventSource for SSE
    eventSource = new EventSource(`/progress/${jobId}`);
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            
            const percent = data.percent || 0;
            const step = data.step || 'Processing...';
            const done = data.done || false;
            const error = data.error;
            
            // Update progress
            updateProgress(percent, step);
            
            if (done) {
                eventSource.close();
                eventSource = null;
                
                if (error) {
                    showError(error);
                    hideProgress();
                } else {
                    // Analysis complete, fetch results
                    fetchResults(jobId);
                }
                
                // Re-enable submit button
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-magic"></i> <span>Generate Analysis</span>';
                }
            }
        } catch (e) {
            console.error('Error parsing progress data:', e);
        }
    };
    
    eventSource.onerror = function(event) {
        console.error('EventSource error:', event);
        // Try to fetch results anyway (might be complete)
        setTimeout(() => {
            fetchResults(jobId);
        }, 2000);
    };
}

function updateProgress(percent, step) {
    currentProgress = percent;
    
    if (progressFill) {
        progressFill.style.width = percent + '%';
    }
    
    if (progressText) {
        progressText.textContent = step;
    }
}

function fetchResults(jobId) {
    fetch(`/results/${jobId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Redirect to report page
                window.location.href = `/report/${jobId}`;
            } else {
                showError(data.error || 'Failed to retrieve results');
                hideProgress();
            }
        })
        .catch(error => {
            console.error('Error fetching results:', error);
            showError('Failed to retrieve results. Please try again.');
            hideProgress();
        });
}

function showProgress() {
    if (progressSection) {
        progressSection.style.display = 'block';
    }
    if (progressFill) {
        progressFill.style.width = '0%';
    }
    if (progressText) {
        progressText.textContent = 'Initializing analysis...';
    }
}

function hideProgress() {
    if (progressSection) {
        progressSection.style.display = 'none';
    }
}

function showResults(jobId) {
    if (resultsSection) {
        resultsSection.style.display = 'block';
        const viewReportBtn = document.getElementById('viewReportBtn');
        if (viewReportBtn) {
            viewReportBtn.href = `/report/${jobId}`;
        }
    }
}

function hideResults() {
    if (resultsSection) {
        resultsSection.style.display = 'none';
    }
}

function showError(message) {
    if (errorSection) {
        errorSection.style.display = 'block';
        const errorMsg = document.getElementById('errorMessage');
        if (errorMsg) {
            errorMsg.textContent = message;
        }
    }
}

function hideError() {
    if (errorSection) {
        errorSection.style.display = 'none';
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (eventSource) {
        eventSource.close();
    }
});




