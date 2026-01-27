/**
 * JustData Analytics Event Logging
 * Tracks user interactions for coalition building and usage analytics
 */

// Firebase Analytics instance
let firebaseAnalytics = null;

/**
 * Initialize Firebase Analytics
 */
function initAnalytics() {
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/49846568-3a47-434f-af1f-d48b592f8068',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'analytics-events.js:initAnalytics',message:'initAnalytics called',data:{alreadyInit:!!firebaseAnalytics,firebaseDefined:typeof firebase!=='undefined'},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'A,B'})}).catch(()=>{});
    // #endregion
    if (firebaseAnalytics) return;

    try {
        // Firebase should already be initialized by auth.js
        if (typeof firebase !== 'undefined' && firebase.app) {
            firebaseAnalytics = firebase.analytics();
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/49846568-3a47-434f-af1f-d48b592f8068',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'analytics-events.js:initAnalytics:success',message:'Firebase Analytics initialized OK',data:{hasAnalytics:!!firebaseAnalytics},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
            console.log('Firebase Analytics initialized');
        } else {
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/49846568-3a47-434f-af1f-d48b592f8068',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'analytics-events.js:initAnalytics:noFirebase',message:'Firebase not defined or no app',data:{firebaseDefined:typeof firebase!=='undefined',hasApp:typeof firebase!=='undefined'&&!!firebase.app},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
        }
    } catch (error) {
        // #region agent log
        fetch('http://127.0.0.1:7243/ingest/49846568-3a47-434f-af1f-d48b592f8068',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'analytics-events.js:initAnalytics:error',message:'Analytics init error',data:{error:error.message},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'B'})}).catch(()=>{});
        // #endregion
        console.warn('Firebase Analytics initialization error:', error);
    }
}

/**
 * Log a custom event to Firebase Analytics
 * @param {string} eventName - The name of the event (e.g., 'lendsight_report')
 * @param {Object} params - Event parameters
 */
function logAnalyticsEvent(eventName, params = {}) {
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/49846568-3a47-434f-af1f-d48b592f8068',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'analytics-events.js:logAnalyticsEvent',message:'logAnalyticsEvent called',data:{eventName:eventName,hasAnalytics:!!firebaseAnalytics,params:JSON.stringify(params).substring(0,200)},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
    if (!firebaseAnalytics) {
        initAnalytics();
    }

    if (!firebaseAnalytics) {
        // #region agent log
        fetch('http://127.0.0.1:7243/ingest/49846568-3a47-434f-af1f-d48b592f8068',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'analytics-events.js:logAnalyticsEvent:noAnalytics',message:'Analytics not available after init attempt',data:{eventName:eventName},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'C'})}).catch(()=>{});
        // #endregion
        console.warn('Firebase Analytics not available, event not logged:', eventName);
        return;
    }

    try {
        // Add common parameters
        const enrichedParams = {
            ...params,
            timestamp: new Date().toISOString(),
            page_url: window.location.href,
            page_path: window.location.pathname
        };

        // Add user info if available
        if (window.justDataUserType) {
            enrichedParams.user_type = window.justDataUserType;
        }

        firebaseAnalytics.logEvent(eventName, enrichedParams);
        // #region agent log
        fetch('http://127.0.0.1:7243/ingest/49846568-3a47-434f-af1f-d48b592f8068',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'analytics-events.js:logAnalyticsEvent:success',message:'Event logged to Firebase',data:{eventName:eventName},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'C'})}).catch(()=>{});
        // #endregion
        console.log('Analytics event logged:', eventName, enrichedParams);
    } catch (error) {
        // #region agent log
        fetch('http://127.0.0.1:7243/ingest/49846568-3a47-434f-af1f-d48b592f8068',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'analytics-events.js:logAnalyticsEvent:error',message:'Error logging event',data:{eventName:eventName,error:error.message},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'C'})}).catch(()=>{});
        // #endregion
        console.error('Error logging analytics event:', error);
    }
}

/**
 * Log LendSight report generation
 * @param {Object} params - Report parameters
 */
function logLendSightReport(params) {
    logAnalyticsEvent('lendsight_report', {
        lender_name: params.lenderName || '',
        lei: params.lei || '',
        county_fips: params.countyFips || '',
        state: params.state || '',
        year: params.year || '',
        report_type: params.reportType || 'hmda_analysis'
    });
}

/**
 * Log BizSight report generation
 * @param {Object} params - Report parameters
 */
function logBizSightReport(params) {
    logAnalyticsEvent('bizsight_report', {
        lender_name: params.lenderName || '',
        lei: params.lei || '',
        county_fips: params.countyFips || '',
        state: params.state || '',
        year: params.year || '',
        report_type: params.reportType || 'small_business_analysis'
    });
}

/**
 * Log BranchSight report generation
 * @param {Object} params - Report parameters
 */
function logBranchSightReport(params) {
    logAnalyticsEvent('branchsight_report', {
        institution_name: params.institutionName || '',
        cert: params.cert || '',
        county_fips: params.countyFips || '',
        state: params.state || '',
        year: params.year || '',
        report_type: params.reportType || 'branch_analysis'
    });
}

/**
 * Log BranchMapper report generation
 * @param {Object} params - Report parameters
 */
function logBranchMapperReport(params) {
    logAnalyticsEvent('branchmapper_report', {
        institution_name: params.institutionName || '',
        cert: params.cert || '',
        state: params.state || '',
        year: params.year || '',
        branch_count: params.branchCount || 0,
        report_type: params.reportType || 'branch_mapping'
    });
}

/**
 * Log MergerMeter report generation
 * @param {Object} params - Report parameters
 */
function logMergerMeterReport(params) {
    logAnalyticsEvent('mergermeter_report', {
        acquirer_name: params.acquirerName || '',
        target_name: params.targetName || '',
        acquirer_cert: params.acquirerCert || '',
        target_cert: params.targetCert || '',
        merger_type: params.mergerType || '',
        report_type: params.reportType || 'merger_analysis'
    });
}

/**
 * Log DataExplorer area report generation
 * @param {Object} params - Report parameters
 */
function logDataExplorerAreaReport(params) {
    logAnalyticsEvent('dataexplorer_area_report', {
        county_fips: params.countyFips || '',
        county_name: params.countyName || '',
        state: params.state || '',
        year: params.year || '',
        data_types: params.dataTypes || '',
        report_type: params.reportType || 'area_exploration'
    });
}

/**
 * Log DataExplorer lender report generation
 * @param {Object} params - Report parameters
 */
function logDataExplorerLenderReport(params) {
    logAnalyticsEvent('dataexplorer_lender_report', {
        lender_name: params.lenderName || '',
        lei: params.lei || '',
        year: params.year || '',
        data_types: params.dataTypes || '',
        report_type: params.reportType || 'lender_exploration'
    });
}

/**
 * Log LenderProfile view
 * @param {Object} params - View parameters
 */
function logLenderProfileView(params) {
    logAnalyticsEvent('lenderprofile_view', {
        lender_name: params.lenderName || '',
        lei: params.lei || '',
        rssd_id: params.rssdId || '',
        view_type: params.viewType || 'profile'
    });
}

/**
 * Log page view
 * @param {string} pageName - Name of the page
 * @param {Object} params - Additional parameters
 */
function logPageView(pageName, params = {}) {
    logAnalyticsEvent('page_view', {
        page_name: pageName,
        ...params
    });
}

/**
 * Log search action
 * @param {string} searchType - Type of search
 * @param {string} searchTerm - Search term used
 * @param {number} resultCount - Number of results
 */
function logSearch(searchType, searchTerm, resultCount = 0) {
    logAnalyticsEvent('search', {
        search_type: searchType,
        search_term: searchTerm,
        result_count: resultCount
    });
}

/**
 * Log download action
 * @param {string} downloadType - Type of download (excel, pdf, csv, etc.)
 * @param {string} reportName - Name of the report being downloaded
 */
function logDownload(downloadType, reportName) {
    logAnalyticsEvent('download', {
        download_type: downloadType,
        report_name: reportName
    });
}

// Initialize analytics when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure Firebase is initialized first
    setTimeout(initAnalytics, 500);
});

// Export functions for global access
window.JustDataAnalytics = {
    logEvent: logAnalyticsEvent,
    logLendSightReport: logLendSightReport,
    logBizSightReport: logBizSightReport,
    logBranchSightReport: logBranchSightReport,
    logBranchMapperReport: logBranchMapperReport,
    logMergerMeterReport: logMergerMeterReport,
    logDataExplorerAreaReport: logDataExplorerAreaReport,
    logDataExplorerLenderReport: logDataExplorerLenderReport,
    logLenderProfileView: logLenderProfileView,
    logPageView: logPageView,
    logSearch: logSearch,
    logDownload: logDownload
};
