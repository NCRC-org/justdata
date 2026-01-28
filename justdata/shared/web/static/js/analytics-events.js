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
    console.log('[DEBUG] initAnalytics called, alreadyInit:', !!firebaseAnalytics, 'firebaseDefined:', typeof firebase !== 'undefined');
    if (firebaseAnalytics) return;

    try {
        // Firebase should already be initialized by auth.js
        if (typeof firebase !== 'undefined' && firebase.app) {
            firebaseAnalytics = firebase.analytics();
            console.log('[DEBUG] Firebase Analytics initialized successfully');
        } else {
            console.log('[DEBUG] Firebase not defined or no app - cannot init analytics');
        }
    } catch (error) {
        console.warn('[DEBUG] Firebase Analytics initialization error:', error);
    }
}

/**
 * Log a custom event to Firebase Analytics
 * @param {string} eventName - The name of the event (e.g., 'lendsight_report')
 * @param {Object} params - Event parameters
 */
function logAnalyticsEvent(eventName, params = {}) {
    console.log('[DEBUG] logAnalyticsEvent called:', eventName, 'hasAnalytics:', !!firebaseAnalytics);
    if (!firebaseAnalytics) {
        initAnalytics();
    }

    if (!firebaseAnalytics) {
        console.warn('[DEBUG] Firebase Analytics not available, event not logged:', eventName);
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
        
        // Add Firebase Auth user info if signed in
        try {
            const currentUser = firebase.auth && firebase.auth().currentUser;
            if (currentUser) {
                enrichedParams.firebase_uid = currentUser.uid;
                // Add email for user identification (hashed for privacy in analytics)
                if (currentUser.email) {
                    enrichedParams.user_email = currentUser.email;
                }
                if (currentUser.displayName) {
                    enrichedParams.user_display_name = currentUser.displayName;
                }
            }
        } catch (e) {
            // Ignore - user might not be signed in
        }

        firebaseAnalytics.logEvent(eventName, enrichedParams);
        console.log('[DEBUG] Analytics event logged successfully:', eventName, enrichedParams);
    } catch (error) {
        console.error('[DEBUG] Error logging analytics event:', eventName, error);
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
