// ============================================================================
// DATAEXPLORER API CLIENT - LOCKED CODE
// ============================================================================
// This file handles all API communication between the wizard and backend.
// Key functions:
// - generateAreaReport(): Sends area analysis data to /api/generate-area-report
// - generateLenderReport(): Sends lender analysis data to /api/generate-lender-report
//
// Both functions include complete data structures with all user choices.
// See DATAEXPLORER_WIZARD_DATA_STRUCTURE.md for full documentation.
//
// DO NOT MODIFY WITHOUT USER APPROVAL
// ============================================================================

// DataExplorer API Client
// Handles all API communication with Flask backend

const API_BASE = '/dataexplorer/api';

class APIClient {
    constructor() {
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    }

    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const cacheKey = `${url}_${JSON.stringify(options.body || {})}`;
        
        // Check cache
        if (options.method === 'GET' && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
        }
        
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: 'Unknown error' }));
                throw new Error(error.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // Cache GET requests
            if (options.method === 'GET') {
                this.cache.set(cacheKey, {
                    data,
                    timestamp: Date.now()
                });
            }
            
            return data;
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    // Get all states
    async getStates() {
        try {
            const data = await this.request('/states', { method: 'GET' });
            return data.states || [];
        } catch (error) {
            console.error('Error fetching states:', error);
            throw new Error('Unable to load states. Please try again.');
        }
    }

    // Get all metros (CBSAs) - API endpoint (fallback if static file unavailable)
    async getMetros() {
        try {
            const data = await this.request('/metros', { method: 'GET' });
            return data.metros || [];
        } catch (error) {
            console.error('Error fetching metros:', error);
            throw new Error('Unable to load metros. Please try again.');
        }
    }

    // Get counties for a metro (CBSA)
    async getCountiesByMetro(cbsaCode) {
        try {
            const data = await this.request(`/metros/${encodeURIComponent(cbsaCode)}/counties`, { method: 'GET' });
            return data.counties || [];
        } catch (error) {
            console.error('Error fetching counties by metro:', error);
            throw new Error('Unable to load counties. Please try again.');
        }
    }

    // Get counties for a state
    async getCounties(stateCode) {
        try {
            const data = await this.request('/get-counties', {
                method: 'POST',
                body: JSON.stringify({ state: stateCode })
            });
            return data.counties || [];
        } catch (error) {
            console.error('Error fetching counties:', error);
            throw new Error('Unable to load counties. Please try again.');
        }
    }

    // Get all lenders
    async getAllLenders() {
        try {
            const data = await this.request('/lenders', { method: 'GET' });
            return data.lenders || [];
        } catch (error) {
            console.error('Error loading lenders:', error);
            throw new Error('Unable to load lenders. Please try again.');
        }
    }

    // Search for lenders (filter from loaded list)
    async searchLender(query) {
        try {
            console.log('API Client: Searching for lenders with query:', query);
            const data = await this.request('/search-lender', {
                method: 'POST',
                body: JSON.stringify({ query: query.trim() })
            });
            console.log('API Client: Received response:', data);
            return data.results || [];
        } catch (error) {
            console.error('API Client: Error searching lenders:', error);
            console.error('API Client: Error details:', error.message);
            throw new Error('Unable to search lenders. Please try again.');
        }
    }

    // Get lender geography
    async getLenderGeography(lei, scopeType) {
        try {
            const data = await this.request('/get-lender-geography', {
                method: 'POST',
                body: JSON.stringify({
                    lei: lei,
                    scope_type: scopeType
                })
            });
            return data;
        } catch (error) {
            console.error('Error fetching lender geography:', error);
            throw new Error('Unable to load geography data. Please try again.');
        }
    }

    // Generate area report
    // LOCKED: Data structure for area analysis - includes all user choices
    async generateAreaReport(wizardData) {
        try {
            const data = await this.request('/generate-area-report', {
                method: 'POST',
                body: JSON.stringify({
                    analysis_type: 'area',
                    // Geography selection
                    geography: {
                        counties: wizardData.geography.counties,  // Array of county GEOIDs (5-digit FIPS codes)
                        cbsa: wizardData.geography.cbsa,          // CBSA code (metro area)
                        cbsa_name: wizardData.geography.cbsa_name, // CBSA name
                        state: wizardData.geography.state          // State code (if applicable)
                    },
                    // Loan filters
                    filters: wizardData.filters || {
                        actionTaken: 'origination',              // 'origination' or 'application'
                        occupancy: ['owner-occupied'],           // Array: 'owner-occupied', 'second-home', 'investor'
                        totalUnits: '1-4',                       // '1-4' or '5+'
                        construction: ['site-built', 'manufactured'],            // Array: 'site-built', 'manufactured'
                        loanPurpose: ['home-purchase', 'refinance', 'home-equity'],  // Array
                        loanType: ['conventional', 'fha', 'va', 'rhs'],  // Array
                        reverseMortgage: true                    // true = not reverse, false = reverse
                    },
                    disclaimer_accepted: wizardData.disclaimerAccepted,
                    timestamp: new Date().toISOString()
                })
            });
            return data;
        } catch (error) {
            console.error('Error generating area report:', error);
            throw new Error('Unable to generate report. Please try again.');
        }
    }

    // Generate lender report
    // LOCKED: Data structure for lender analysis - includes all user choices
    async generateLenderReport(wizardData) {
        try {
            const data = await this.request('/generate-lender-report', {
                method: 'POST',
                body: JSON.stringify({
                    analysis_type: 'lender',
                    // Lender identification (all three identifiers for different data sources)
                    lender: {
                        name: wizardData.lender.name,           // Lender name
                        lei: wizardData.lender.lei,              // For HMDA data queries
                        rssd: wizardData.lender.rssd,            // For branch/CBSA queries (10-digit padded)
                        sb_resid: wizardData.lender.sb_resid,    // For small business loan data queries
                        type: wizardData.lender.type,
                        city: wizardData.lender.city,
                        state: wizardData.lender.state
                    },
                    // Geography scope selection
                    geography_scope: wizardData.lenderAnalysis.geographyScope,  // 'loan_cbsas', 'branch_cbsas', 'custom', 'all_cbsas'
                    // Custom geography (if geography_scope === 'custom')
                    custom_cbsa: wizardData.lenderAnalysis.customCbsa,
                    custom_cbsa_name: wizardData.lenderAnalysis.customCbsaName,
                    custom_counties: wizardData.lenderAnalysis.customCounties || [],
                    // Comparison group selection
                    comparison_group: wizardData.lenderAnalysis.comparisonGroup,  // 'peers', 'all', 'banks', 'mortgage', 'credit_unions'
                    // Loan filters (same as area analysis)
                    filters: wizardData.filters || {
                        actionTaken: 'origination',              // 'origination' or 'application'
                        occupancy: ['owner-occupied'],           // Array: 'owner-occupied', 'second-home', 'investor'
                        totalUnits: '1-4',                       // '1-4' or '5+'
                        construction: ['site-built', 'manufactured'],            // Array: 'site-built', 'manufactured'
                        loanPurpose: ['home-purchase', 'refinance', 'home-equity'],  // Array
                        loanType: ['conventional', 'fha', 'va', 'rhs'],  // Array
                        reverseMortgage: true                    // true = not reverse, false = reverse
                    },
                    disclaimer_accepted: wizardData.disclaimerAccepted,
                    timestamp: new Date().toISOString()
                })
            });
            return data;
        } catch (error) {
            console.error('Error generating lender report:', error);
            throw new Error('Unable to generate report. Please try again.');
        }
    }

    // Get lender details by LEI (RSSD, SB_RESID)
    async getLenderDetailsByLei(lei) {
        try {
            const data = await this.request('/lender/lookup-by-lei', {
                method: 'POST',
                body: JSON.stringify({ lei: lei })
            });
            return data.details;
        } catch (error) {
            console.error('API Client: Error fetching lender details by LEI:', error);
            throw new Error('Unable to fetch lender details. Please try again.');
        }
    }

    // Get GLEIF data by LEI (legal/hq addresses, parent/child relationships)
    async getGLEIFDataByLei(lei) {
        try {
            const data = await this.request('/lender/gleif-data', {
                method: 'POST',
                body: JSON.stringify({ lei: lei })
            });
            return data.data;
        } catch (error) {
            console.error('API Client: Error fetching GLEIF data by LEI:', error);
            throw new Error('Unable to fetch GLEIF data. Please try again.');
        }
    }

    // Verify LEI with GLEIF API
    async verifyGLEIF(lei, name) {
        try {
            const data = await this.request('/lender/verify-gleif', {
                method: 'POST',
                body: JSON.stringify({ lei: lei, name: name })
            });
            return data;
        } catch (error) {
            console.error('API Client: Error verifying with GLEIF:', error);
            throw new Error('Unable to verify LEI with GLEIF. Please try again.');
        }
    }

    // Get lender assets from CFPB HMDA API
    async getLenderAssets(lei) {
        try {
            const data = await this.request('/lender/assets', {
                method: 'POST',
                body: JSON.stringify({ lei: lei })
            });
            return data.assets;
        } catch (error) {
            console.error('API Client: Error fetching lender assets:', error);
            return null;
        }
    }
}

// Create singleton instance
const apiClient = new APIClient();

// Export for use in other files
window.apiClient = apiClient;
