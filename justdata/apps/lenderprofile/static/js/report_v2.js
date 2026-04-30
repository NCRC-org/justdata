/**
 * LenderProfile Intelligence Report V2 - Orchestrator
 *
 * Thin orchestrator. Wires up the DOMContentLoaded handler that calls each
 * section initializer with window.reportData, and exposes copyEntityInfo on
 * window for the inline onclick= in JS-rendered HTML. All other logic lives
 * in ./report/*.js modules.
 */

import { exportToPDF } from './report/lenderprofile_report_utils.js';
import { copyEntityInfo, initializeCorporateStructure } from './report/lenderprofile_report_corporate_structure.js';
import {
    initializeAISummary,
    initializeSECFilingsAnalysis,
} from './report/lenderprofile_report_summary.js';
import {
    initializeHeader,
    initializeBusinessStrategy,
    initializeRiskFactors,
    initializeFinancialPerformance,
    initializeMergerActivity,
    initializeRegulatoryRisk,
    initializeCommunityInvestment,
    initializeBranchNetwork,
    initializeLendingFootprint,
    initializeLeadership,
    initializeCongressionalTrading,
    initializeNews,
    initializeSeekingAlpha,
} from './report/lenderprofile_report_sections.js';
// Charts module owns its own DOMContentLoaded handler that kicks off all
// visualizations after a short setTimeout — importing it here is sufficient
// to register that handler.
import './report/lenderprofile_report_charts.js';

document.addEventListener('DOMContentLoaded', function() {
    const reportData = window.reportData;
    console.log('Report data:', reportData);
    if (!reportData) {
        console.warn('No report data available');
        return;
    }

    // Initialize all sections
    console.log('Initializing header with:', reportData.header);
    initializeHeader(reportData);
    initializeBusinessStrategy(reportData);
    initializeRiskFactors(reportData);
    initializeFinancialPerformance(reportData);
    initializeMergerActivity(reportData);
    initializeRegulatoryRisk(reportData);
    initializeCommunityInvestment(reportData);
    initializeBranchNetwork(reportData);
    initializeLendingFootprint(reportData);
    initializeLeadership(reportData);
    initializeCongressionalTrading(reportData);
    initializeCorporateStructure(reportData);
    initializeNews(reportData);
    initializeSeekingAlpha(reportData);
    initializeAISummary(reportData);
    initializeSECFilingsAnalysis(reportData);

    // Export button
    document.getElementById('export-pdf-btn')?.addEventListener('click', exportToPDF);
});

// ----------------------------------------------------------------------------
// Window exports for inline onclick handlers — remove when onclick= is replaced
// with event listeners. Only includes symbols referenced from inline HTML event
// attributes (in templates and in HTML strings rendered by JS), nothing else.
// ----------------------------------------------------------------------------
window.copyEntityInfo = copyEntityInfo;
