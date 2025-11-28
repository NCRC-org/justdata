# Comprehensive Analysis of Four NCRC Data Analysis Applications

## Executive Summary

This document provides a comprehensive analysis of four web-based financial data analysis applications developed for the National Community Reinvestment Coalition (NCRC). All applications are Flask-based web services that query Google Cloud BigQuery for financial and demographic data, generate reports, and provide interactive web interfaces.

---

## 1. LendSight - Mortgage Lending Analysis Tool

### Overview
**Port:** 8082  
**Purpose:** Mortgage lending analysis and fair lending assessment  
**Status:** Fully Functional (Version 0.9.0 - Development)

### Core Functionality
LendSight analyzes Home Mortgage Disclosure Act (HMDA) mortgage lending data to assess lending patterns, disparities, and fair lending compliance across selected geographic areas. The tool generates comprehensive written reports with demographic context, lending trends, and AI-generated narrative summaries.

### Key Features

#### Geographic Selection
- Users can select up to 3 counties (state selection is optional)
- Supports county-level analysis with FIPS code integration
- State selection available but optional
- Uses FIPS codes end-to-end for Census API calls (no BigQuery dependency for FIPS lookup)

#### Data Sources
- **HMDA Data:** Mortgage lending data from BigQuery (2018-2024)
- **Census Data:** U.S. Census Bureau demographic data
  - 2010 Decennial Census
  - 2020 Decennial Census
  - 2024 ACS 5-year estimates
- **Weighted Average Aggregation:** For multi-county demographic data

#### Loan Purpose Filtering
- Defaults to home purchase loans only
- Options for refinance and home equity lending
- Configurable loan purpose filters

#### Report Generation
- **Written Narrative Report:** Multiple sections with comprehensive analysis
- **Executive Summary:** JavaScript-generated (not AI)
- **Population Demographics Table:** Shows change over time (2010, 2020, 2024)
- **Key Findings Section:** AI-generated insights
- **Analysis by Demographic Group:** Race/ethnicity, income, neighborhood characteristics
- **Analysis by Bank:** Individual lender performance
- **AI-Generated Narratives:** Two-paragraph summaries following each table (adhering to NCRC style guidelines)

#### Export Options
- **Excel Export (.xlsx):** Multiple sheets with proper number formatting
  - Integers: `#,##0`
  - Percentages: `#,##0.00`
- **PDF Export:** Page numbers, proper page breaks, table integrity
- **Filenames:** `NCRC_LendSight_[County]_[State]_[YYYYMMDD_HHMMSS].[ext]`

#### Technical Architecture
- **Progress Tracking:** Server-Sent Events (SSE) with detailed substeps
- **Census API Integration:** Detailed progress tracking for API calls
- **Background Processing:** Non-blocking analysis in background threads
- **Error Handling:** Graceful failure recovery
- **Version:** 0.9.0 (Development)

### Data Processing Pipeline
1. Queries BigQuery for HMDA loan-level data filtered by county, year, and loan purpose
2. Fetches Census demographic data (population, race/ethnicity percentages) for selected counties
3. Aggregates lending data by demographic characteristics, income levels, and neighborhood types
4. Calculates lending rates, denial rates, and disparities compared to population shares
5. Generates AI-powered narrative summaries using Claude API

### API Endpoints
- `GET /` - Main page with analysis form
- `POST /analyze` - Start new analysis
- `GET /progress/<job_id>` - Real-time progress updates (SSE)
- `GET /report` - View interactive web report
- `GET /report-data` - Get report data (JSON)
- `GET /download?format=excel` - Download Excel file
- `GET /download?format=pdf` - Download PDF file
- `GET /states` - Get available states
- `GET /counties` - Get available counties
- `GET /counties-by-state/<state_identifier>` - Get counties for a state

### Configuration
- **BigQuery Project:** `hdma1-242116`
- **Dataset:** `hmda`
- **Table:** `hmda`
- **AI Provider:** Claude (default) with GPT-4 fallback
- **Claude Model:** `claude-sonnet-4-20250514`

---

## 2. BranchSeeker - Bank Branch Location Analysis

### Overview
**Port:** 8080  
**Purpose:** Bank branch location analysis and market concentration assessment  
**Status:** Fully Functional

### Core Functionality
BranchSeeker analyzes FDIC Summary of Deposits (SOD) data to track bank branch locations, market concentration, and branch network changes over time. The tool generates written reports with Excel exports showing branch distribution, market share, and Herfindahl-Hirschman Index (HHI) calculations.

### Key Features

#### Geographic Selection
- **Counties:** County-level analysis
- **States:** State-wide analysis
- **Metro Areas:** Metropolitan statistical area (MSA/CBSA) analysis
- Flexible selection types with automatic expansion

#### Data Source
- **FDIC Summary of Deposits (SOD):** Branch locations and deposits data from BigQuery (2017-2025)
- Branch-level data including:
  - Branch locations (addresses, coordinates)
  - Deposits
  - Service types
  - Bank identifiers

#### Report Generation
- **Written Narrative Report:** No map visualization (text-based)
- **Executive Summary:** AI-generated overview
- **Analysis by County:** County-level branch distribution
- **Analysis by Bank:** Branch counts and deposits per bank
- **Market Concentration Analysis:** HHI calculations
- **AI-Generated Narrative Summaries:** Following each analysis section

#### Export Options
- **Excel Export (.xlsx):** Multiple sheets with all tables
- **CSV Export:** Summary data
- **JSON Export:** Full data structure
- **ZIP Export:** Multiple formats bundled

#### Technical Architecture
- **Progress Tracking:** Server-Sent Events (SSE)
- **Background Processing:** Non-blocking analysis
- **Version Tracking:** Version management system
- **Error Handling:** Comprehensive error recovery

### Data Processing Pipeline
1. Queries BigQuery for FDIC SOD data filtered by geographic area and year
2. Aggregates branch data by county, bank, and year
3. Calculates market share and HHI for each geographic area
4. Tracks changes in branch networks over time
5. Generates AI-powered insights using Claude API

### API Endpoints
- `GET /` - Main page with analysis form
- `POST /analyze` - Start new analysis
- `GET /progress/<job_id>` - Real-time progress updates (SSE)
- `GET /report` - View interactive web report
- `GET /report-data` - Get report data (JSON)
- `GET /download?format=excel` - Download Excel file
- `GET /download?format=csv` - Download CSV file
- `GET /download?format=json` - Download JSON file
- `GET /download?format=zip` - Download ZIP file
- `GET /counties` - Get available counties
- `GET /states` - Get available states
- `GET /metro-areas` - Get available metro areas
- `GET /counties-by-state/<state_code>` - Get counties for a state

### Configuration
- **BigQuery Project:** `hdma1-242116`
- **Dataset:** `branches`
- **Table:** `sod`
- **Default Years:** 2017-2024
- **AI Provider:** Claude (default) with GPT-4 fallback

---

## 3. BranchMapper - Interactive Branch Map Visualization

### Overview
**Port:** 8084  
**Purpose:** Interactive map visualization of bank branch locations  
**Status:** Fully Functional

### Core Functionality
BranchMapper provides an interactive web-based map showing bank branch locations with demographic and income context. Users can visualize branch distribution across census tracts, filter by bank, year, and service type, and see demographic characteristics of areas with and without branches.

### Key Features

#### Interactive Map
- **Leaflet.js:** Leaflet-based map rendering
- **Branch Markers:** Color-coded by bank
- **Census Tract Boundaries:** Tract-level geographic boundaries
- **Income Shading:** Tract-level income categorization
- **Minority Percentage Shading:** Demographic visualization

#### Geographic Selection
- **Counties:** County-level selection
- **States:** State-wide selection
- **Metro Areas:** MSA/CBSA selection

#### Data Sources
- **FDIC Summary of Deposits (SOD):** Branch locations with coordinates from BigQuery
- **U.S. Census Bureau:** Tract-level demographic and income data
- **Census API:** Real-time tract boundary fetching

#### Visualization Features
- **Branch Markers:** Color-coded by bank with popup details
- **Census Tract Boundaries:** Income and minority percentage shading
- **Branch Details Popup:** Bank name, address, deposits, service type
- **Filtering:** By bank, year, and service type
- **Legend:** Income levels and minority percentages

#### Income Categorization
- **LMI (Low-to-Moderate Income):** Tracts below county median
- **Moderate Income:** Tracts near county median
- **Middle Income:** Tracts above county median
- **Upper Income:** Tracts significantly above county median

#### Minority Categorization
- **Majority-Minority Census Tracts (MMCT):** Tracts with >50% minority population
- **Minority Percentage:** Compared to county baseline

#### Technical Architecture
- **Real-time Filtering:** Dynamic marker updates
- **Census API Integration:** Tract boundary and demographic data fetching
- **No Report Generation:** Map-only tool (no Excel/PDF export)
- **Client-side Rendering:** JavaScript-based map interaction

### Data Processing Pipeline
1. Queries BigQuery for branch locations with coordinates
2. Fetches Census tract boundaries via Census API
3. Fetches tract-level income and demographic data
4. Categorizes tracts by income level and minority percentage
5. Renders branches and tract boundaries on interactive map

### API Endpoints
- `GET /` - Main page with interactive map
- `GET /counties` - Get available counties
- `GET /states` - Get available states
- `GET /metro-areas` - Get available metro areas
- `GET /counties-by-state/<state_code>` - Get counties for a state
- `GET /api/census-tracts/<county>` - Get census tract boundaries with income/minority data
- `GET /api/branches` - Get branch data with coordinates for map display

### Configuration
- **BigQuery Project:** `hdma1-242116`
- **Dataset:** `branches`
- **Table:** `sod`
- **Census API Key:** Required for income and minority data layers

---

## 4. MergerMeter - Two-Bank Merger Impact Analysis

### Overview
**Port:** 8083  
**Purpose:** Two-bank merger impact analysis and CRA goal-setting assessment  
**Status:** Fully Functional

### Core Functionality
MergerMeter analyzes the potential impact of bank mergers on Community Reinvestment Act (CRA) compliance and fair lending. The tool compares lending patterns, branch networks, and assessment area coverage for an acquiring bank and a target bank, generating goal-setting analysis reports in Excel format matching the original merger report template.

### Key Features

#### Bank Identification
- **LEI (Legal Entity Identifier):** 20-character identifier
- **RSSD ID:** Federal Reserve System identifier
- **Small Business ID (ResID):** Small business lending respondent ID
- **Bank Name Lookup:** Automatic name resolution from identifiers
- **Bulk Import:** CSV template for multiple banks

#### Assessment Areas
- **Upload Options:** JSON or CSV file upload
- **Manual Definition:** JSON format input
- **Auto-Generation:** Generate from branch locations
- **MSA Support:** MSA code and name expansion to counties
- **Template Download:** CSV template for assessment area definition

#### Data Sources
- **HMDA Mortgage Lending Data:** 2020-2024
- **Small Business Lending Data:** 2019-2023
- **FDIC Summary of Deposits:** Branch data (2025)
- **HHI Calculation:** Market concentration analysis

#### Report Generation
- **Excel Report:** Matches original merger report template format
- **Goal-Setting Analysis Sheets:** Structured goal-setting recommendations
- **Mortgage Lending Analysis:** By assessment area for both banks
- **Small Business Lending Analysis:** Subject and peer comparisons
- **Branch Network Analysis:** Branch locations and deposits
- **Assessment Area Comparison:** Side-by-side comparison
- **HHI Analysis:** Market concentration metrics
- **Notes and Methodology Section:** Documentation

#### Export Options
- **Excel Export (.xlsx):** Template-based formatting
- **ZIP Export:** Multiple files bundled
- **Filenames:** `NCRC_MergerMeter_[BankA]_[BankB]_[YYYYMMDD_HHMMSS].xlsx`

#### Technical Architecture
- **Template Matching:** Uses original merger report Excel template for exact format matching
- **Progress Tracking:** Server-Sent Events (SSE) with detailed steps
- **Background Processing:** Long-running analysis in background threads
- **File Upload:** JSON and CSV file parsing
- **Assessment Area Parsing:** Complex parsing from PDF text, JSON, CSV formats

### Data Processing Pipeline
1. Parses bank identifiers (LEI, RSSD, SB ID) and assessment areas
2. Maps counties to GEOIDs for BigQuery queries
3. Queries HMDA loan-level data for both banks (subject and peer)
4. Queries small business lending data for both banks
5. Queries branch locations and deposits
6. Calculates HHI (Herfindahl-Hirschman Index) for market concentration
7. Aggregates data by assessment area, loan purpose, and demographic characteristics
8. Compares pre-merger and post-merger scenarios
9. Generates goal-setting recommendations
10. Creates Excel report matching template format

### API Endpoints
- `GET /` - Main page with analysis form
- `POST /analyze` - Start new analysis (form data)
- `GET /progress/<job_id>` - Real-time progress updates (SSE)
- `GET /report` - View interactive web report
- `GET /report-data` - Get report data (JSON)
- `GET /download?job_id=<job_id>` - Download Excel file
- `POST /api/load-bank-names` - Load bank names from identifiers
- `POST /api/generate-assessment-areas-from-branches` - Generate AAs from branch locations
- `POST /api/upload-assessment-areas` - Upload assessment area JSON/CSV
- `GET /api/download-assessment-area-template` - Download CSV template
- `GET /api/download-bank-identifiers-template` - Download CSV template

### Configuration
- **BigQuery Project:** `hdma1-242116`
- **Excel Template:** Path to original merger report template
- **Output Directory:** Application-specific output folder
- **File Upload Limit:** 10MB maximum

---

## Common Technical Architecture

### Shared Components

#### Web Framework
- **Flask:** All applications use Flask with shared app factory pattern
- **Template System:** Jinja2 templates with shared base templates
- **Static Assets:** Common CSS, JavaScript, and UI components
- **NCRC Branding:** Consistent color scheme (NCRC Blue: `#034ea0`)

#### Data Infrastructure
- **BigQuery Integration:** All tools query Google Cloud BigQuery
- **BigQuery Client:** Shared utility for connection management
- **Project ID:** `hdma1-242116` (consistent across all apps)

#### Progress Tracking
- **Server-Sent Events (SSE):** Real-time progress updates
- **Progress Tracker:** Shared utility for job tracking
- **Background Threading:** Non-blocking analysis execution

#### Report Generation
- **Excel Generation:** Uses `openpyxl` for Excel report generation
- **PDF Generation:** LendSight uses `playwright` for HTML-to-PDF conversion
- **Number Formatting:** Proper formatting for integers and percentages

#### AI Integration
- **Claude API:** Primary AI engine (Anthropic Claude 4 Sonnet)
- **OpenAI GPT-4:** Secondary AI engine (fallback)
- **NCRC Style Guidelines:** AI-generated content adheres to NCRC standards
- **Narrative Summaries:** Two-paragraph summaries following data tables

### Data Sources

#### BigQuery Tables
- **HMDA Data:** `hmda.hmda` (2018-2024)
- **FDIC SOD Data:** `branches.sod` (2017-2025)
- **Small Business Lending:** CRA small business lending (2019-2023)
- **Geographic Data:** `geo.cbsa_to_county` (MSA to county mapping)

#### External APIs
- **Census API:** Demographic and geographic data
  - 2010 Decennial Census
  - 2020 Decennial Census
  - ACS 5-year estimates
- **Census Tract Boundaries:** GeoJSON via Census API

### Environment Requirements

#### Python Dependencies
- **Python 3.11+:** Core runtime
- **Flask 2.3.0+:** Web framework
- **pandas 1.5.0+:** Data manipulation
- **google-cloud-bigquery 3.0.0+:** BigQuery client
- **openpyxl 3.0.0+:** Excel generation
- **playwright 1.40.0+:** PDF generation (LendSight)
- **anthropic 0.7.0+:** Claude API client
- **openai 1.0.0+:** OpenAI API client
- **numpy 1.21.0+:** Numerical operations

#### Environment Variables
- **GCP_PROJECT_ID:** Google Cloud Project ID (`hdma1-242116`)
- **GOOGLE_APPLICATION_CREDENTIALS:** Path to GCP credentials JSON
- **CLAUDE_API_KEY:** Anthropic Claude API key
- **OPENAI_API_KEY:** OpenAI API key (optional)
- **CENSUS_API_KEY:** U.S. Census Bureau API key (for LendSight and BranchMapper)
- **SECRET_KEY:** Flask session secret key
- **DEBUG:** Development mode flag

### Deployment Architecture

#### Development Mode
- Each application runs as a separate Flask application on its own port
- Applications can run simultaneously on different ports
- Hot-reloading enabled for development
- Debug mode with detailed error messages

#### Production Deployment
- **WSGI Server:** Gunicorn or similar
- **Reverse Proxy:** Nginx for load balancing and SSL termination
- **Process Management:** Systemd or supervisor for process management
- **Containerization:** Docker support available (Dockerfile and docker-compose.yml)

### Access URLs (Local Development)

- **LendSight:** http://127.0.0.1:8082
- **BranchSeeker:** http://127.0.0.1:8080
- **BranchMapper:** http://127.0.0.1:8084
- **MergerMeter:** http://127.0.0.1:8083

---

## Application Comparison Matrix

| Feature | LendSight | BranchSeeker | BranchMapper | MergerMeter |
|---------|-----------|--------------|--------------|-------------|
| **Port** | 8082 | 8080 | 8084 | 8083 |
| **Primary Data Source** | HMDA | FDIC SOD | FDIC SOD | HMDA + SB + SOD |
| **Geographic Scope** | Counties (max 3) | Counties/States/Metro | Counties/States/Metro | Assessment Areas |
| **Report Type** | Narrative + Tables | Narrative + Tables | Map Only | Excel Template |
| **Export Formats** | Excel, PDF | Excel, CSV, JSON, ZIP | None | Excel, ZIP |
| **AI Integration** | Yes | Yes | No | No |
| **Progress Tracking** | SSE | SSE | N/A | SSE |
| **Census Integration** | Yes | No | Yes | No |
| **Map Visualization** | No | No | Yes | No |
| **Multi-Bank Analysis** | No | No | No | Yes (2 banks) |
| **Assessment Areas** | No | No | No | Yes |
| **HHI Calculation** | No | Yes | No | Yes |

---

## Notes and Considerations

### Development Status
- **LendSight:** Version 0.9.0 (Development) - Fully functional
- **BranchSeeker:** Fully functional with version tracking
- **BranchMapper:** Fully functional
- **MergerMeter:** Fully functional

### Shared UI Components
- All tools share common UI components and styling
- NCRC Blue color scheme (`#034ea0`) used consistently
- Responsive design for mobile-friendly interfaces
- Print-friendly report layouts

### AI-Generated Content
- Uses Claude API with adherence to NCRC style guidelines
- Objective, third-person analysis only
- No speculation about strategic implications
- Factual pattern reporting without cause attribution
- Professional, analytical tone enforcement

### Excel Export Features
- Proper number formatting (integers: `#,##0`; percentages: `#,##0.00`)
- Multi-sheet organization
- Template-based formatting (MergerMeter)
- Preserves Excel formulas and formatting

### PDF Export Features (LendSight)
- Page numbers and proper page breaks
- Table integrity preservation
- Print-optimized layouts

### Real-time Progress Tracking
- All tools support real-time progress tracking for long-running analyses
- Detailed substeps for AI generation
- Error reporting and recovery

---

## Conclusion

All four applications provide comprehensive financial data analysis capabilities for the National Community Reinvestment Coalition. Each application serves a specific purpose:

1. **LendSight** focuses on mortgage lending analysis with AI-powered insights
2. **BranchSeeker** provides branch network analysis and market concentration metrics
3. **BranchMapper** offers interactive map visualization of branch locations
4. **MergerMeter** enables two-bank merger impact analysis with goal-setting recommendations

The applications share a common technical foundation while providing specialized functionality for different use cases. All applications are production-ready and can run simultaneously on different ports for concurrent use.

