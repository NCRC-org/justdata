# DataExplorer Wizard - Data Structure Documentation

## LOCKED CODE - DO NOT MODIFY WITHOUT USER APPROVAL

This document describes the complete data structure that the DataExplorer wizard collects and passes to the analysis apps.

---

## API Endpoints

### Area Analysis
**Endpoint:** `POST /api/generate-area-report`

**Request Body:**
```json
{
  "analysis_type": "area",
  "geography": {
    "counties": ["01001", "01003", ...],  // Array of 5-digit county GEOIDs (FIPS codes)
    "cbsa": "12060",                      // CBSA code (metro area)
    "cbsa_name": "Atlanta-Sandy Springs-Roswell, GA",  // CBSA name
    "state": null                         // State code (if applicable)
  },
  "filters": {
    "actionTaken": "origination",         // "origination" or "application"
    "occupancy": ["owner-occupied"],      // Array: "owner-occupied", "second-home", "investor"
    "totalUnits": "1-4",                  // "1-4" or "5+"
    "construction": ["site-built"],       // Array: "site-built", "manufactured"
    "loanPurpose": ["home-purchase", "refinance", "home-equity"],  // Array
    "loanType": ["conventional", "fha", "va", "rhs"],  // Array
    "reverseMortgage": true               // true = not reverse, false = reverse
  },
  "disclaimer_accepted": true,
  "timestamp": "2025-01-17T12:00:00.000Z"
}
```

### Lender Analysis
**Endpoint:** `POST /api/generate-lender-report`

**Request Body:**
```json
{
  "analysis_type": "lender",
  "lender": {
    "name": "WELLS FARGO BANK",            // Lender name (ALL CAPS)
    "lei": "KB1H1DSPRFMYMCUFXT09",        // Legal Entity Identifier - for HMDA data queries
    "rssd": "0000451965",                 // RSSD ID (10-digit padded) - for branch/CBSA queries
    "sb_resid": "0000012072",             // Small Business Respondent ID - for small business loan data queries
    "type": "Bank",                       // Lender type
    "city": "Sioux Falls",                // Lender city
    "state": "SD"                         // Lender state
  },
  "geography_scope": "loan_cbsas",         // "loan_cbsas", "branch_cbsas", "custom", or "all_cbsas"
  "comparison_group": "peers",             // "peers", "all", "banks", "mortgage", or "credit_unions"
  "filters": {
    "actionTaken": "origination",         // "origination" or "application"
    "occupancy": ["owner-occupied"],      // Array: "owner-occupied", "second-home", "investor"
    "totalUnits": "1-4",                  // "1-4" or "5+"
    "construction": ["site-built"],       // Array: "site-built", "manufactured"
    "loanPurpose": ["home-purchase", "refinance", "home-equity"],  // Array
    "loanType": ["conventional", "fha", "va", "rhs"],  // Array
    "reverseMortgage": true              // true = not reverse, false = reverse
  },
  "disclaimer_accepted": true,
  "timestamp": "2025-01-17T12:00:00.000Z"
}
```

---

## Data Collection Flow

### Area Analysis Path
1. **Step 1**: User selects "Area Analysis" → `wizardState.data.analysisType = 'area'`
2. **Step 2A**: User selects metro area → `wizardState.data.geography.cbsa` and `cbsa_name` set
3. **Step 3A**: User selects counties → `wizardState.data.geography.counties` array populated
4. **Step 4A**: User configures filters → `wizardState.data.filters` object updated
5. **Step 5A**: User accepts disclaimer → `wizardState.data.disclaimerAccepted = true`
6. **Generate Report**: All data from `wizardState.data` is sent to `/api/generate-area-report`

### Lender Analysis Path
1. **Step 1**: User selects "Lender Analysis" → `wizardState.data.analysisType = 'lender'`
2. **Step 2B**: User selects lender → `wizardState.data.lender` object populated with:
   - `name`, `lei`, `rssd` (10-digit padded), `sb_resid`, `city`, `state`
3. **Step 3B**: User selects geography scope → `wizardState.data.lenderAnalysis.geographyScope` set
4. **Step 4B**: User selects comparison group → `wizardState.data.lenderAnalysis.comparisonGroup` set
5. **Step 5B**: User configures filters → `wizardState.data.filters` object updated
6. **Step 6B**: User accepts disclaimer → `wizardState.data.disclaimerAccepted = true`
7. **Generate Report**: All data from `wizardState.data` is sent to `/api/generate-lender-report`

---

## Key Identifiers

### LEI (Legal Entity Identifier)
- **Purpose**: Used for HMDA data queries
- **Format**: 20-character alphanumeric string (e.g., "KB1H1DSPRFMYMCUFXT09")
- **Lookup**: https://www.gleif.org/en
- **Source**: Selected from `hmda.lenders18` table

### RSSD (Federal Reserve System ID)
- **Purpose**: Used for branch/CBSA queries
- **Format**: 10-digit zero-padded number (e.g., "0000451965")
- **Lookup**: https://www.ffiec.gov/NPW
- **Source**: Retrieved from `hmda.lenders18` table, then used to query `bizsight.sb_lenders` for SB_RESID

### SB_RESID (Small Business Respondent ID)
- **Purpose**: Used for small business loan data queries
- **Format**: Variable length string (e.g., "0000012072")
- **Lookup**: https://www.ffiec.gov/craadweb/DisRptMain.aspx
- **Source**: Retrieved from `bizsight.sb_lenders` table using RSSD as crosswalk

---

## Filter Defaults

All filters default to the following values (can be modified by user):

```javascript
{
  actionTaken: 'origination',
  occupancy: ['owner-occupied'],
  totalUnits: '1-4',
  construction: ['site-built'],
  loanPurpose: ['home-purchase', 'refinance', 'home-equity'],
  loanType: ['conventional', 'fha', 'va', 'rhs'],
  reverseMortgage: true  // true = not reverse mortgage
}
```

---

## Files Modified

### Core Wizard Files (LOCKED)
- `apps/dataexplorer/static/js/wizard.js` - Core wizard state and navigation
- `apps/dataexplorer/static/js/wizard-steps.js` - Step definitions and handlers
- `apps/dataexplorer/static/js/api-client.js` - API communication
- `apps/dataexplorer/templates/wizard.html` - HTML template and CSS
- `apps/dataexplorer/app.py` - Flask routes and API endpoints
- `apps/dataexplorer/data_utils.py` - BigQuery data utilities

### Key Functions
- `generateAreaReport(wizardData)` - Sends area analysis data to backend
- `generateLenderReport(wizardData)` - Sends lender analysis data to backend
- `selectLender(lender)` - Captures lender data with all three identifiers
- `displayLenderInfo()` - Shows lender information with lookup links

---

## Next Steps for Analysis Apps

When building the area analysis and lender analysis apps, use the data structure above to:

1. **Area Analysis App**: Receive data from `/api/generate-area-report` and use:
   - `geography.counties` - Array of county GEOIDs for filtering
   - `geography.cbsa` - CBSA code for metro-level analysis
   - `filters` - All loan filters for querying HMDA/SB/Branch data

2. **Lender Analysis App**: Receive data from `/api/generate-lender-report` and use:
   - `lender.lei` - For HMDA data queries
   - `lender.rssd` - For branch/CBSA queries (10-digit padded)
   - `lender.sb_resid` - For small business loan data queries
   - `geography_scope` - To determine which CBSAs to include
   - `comparison_group` - To determine peer comparison group
   - `filters` - All loan filters for querying data

---

## Status: LOCKED AND READY FOR ANALYSIS APP DEVELOPMENT

