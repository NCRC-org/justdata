// DataExplorer Wizard - step5A/step6B: Final report generation and summary-bar
// refresh. Moved verbatim from wizard-steps.js. Function bodies untouched.

import {
    wizardState,
    showError,
    showLoading,
    hideLoading,
    generateStepIndicators,
    generateSummaryDetails,
} from '../wizard.js';
import { apiClient } from '../api-client.js';

// Report generation
export async function generateReport() {
    if (!wizardState.data.disclaimerAccepted) {
        showError('Please accept the disclaimer to continue');
        return;
    }

    showLoading('Generating your report...');

    try {
        let result;
        if (wizardState.data.analysisType === 'area') {
            result = await apiClient.generateAreaReport(wizardState.data);
        } else {
            result = await apiClient.generateLenderReport(wizardState.data);
        }

        // Check for no_data response (lender has no HMDA data in selected geography)
        if (result.no_data === true) {
            // Redirect to no-data info page instead of progress page
            const params = new URLSearchParams({
                lender_name: result.lender_name || wizardState.data.lender?.name || 'the selected lender',
                county_count: result.county_count || '0',
                year_range: result.year_range || ''
            });
            window.location.href = `/dataexplorer/no-data?${params.toString()}`;
            return;
        }

        // Log analytics event
        if (window.JustDataAnalytics) {
            if (wizardState.data.analysisType === 'area') {
                window.JustDataAnalytics.logDataExplorerAreaReport({
                    countyFips: wizardState.data.county?.geoid5 || '',
                    countyName: wizardState.data.county?.name || '',
                    state: wizardState.data.state || '',
                    year: wizardState.data.years?.join('-') || '',
                    dataTypes: wizardState.data.dataTypes?.join(',') || '',
                    reportType: 'area_exploration'
                });
            } else {
                window.JustDataAnalytics.logDataExplorerLenderReport({
                    lenderName: wizardState.data.lender?.name || '',
                    lei: wizardState.data.lender?.lei || '',
                    year: wizardState.data.years?.join('-') || '',
                    dataTypes: wizardState.data.dataTypes?.join(',') || '',
                    reportType: 'lender_exploration'
                });
            }
        }

        // Redirect to report view (which will show progress page if not ready)
        if (result.report_id) {
            window.location.href = `/dataexplorer/report/${result.report_id}`;
        } else {
            hideLoading();
            showError('Report generated but no redirect URL provided');
        }
    } catch (error) {
        hideLoading();
        showError('Unable to generate report. Please try again.');
    }
}

// Update summary bar
export function updateSummaryBar() {
    const summaryBar = document.getElementById('wizardSummaryBar');
    if (summaryBar) {
        const steps = summaryBar.querySelector('.summary-steps');
        const details = summaryBar.querySelector('.summary-details');

        if (steps) {
            steps.innerHTML = generateStepIndicators();
        }
        if (details) {
            details.innerHTML = generateSummaryDetails();
        }
    }
}
