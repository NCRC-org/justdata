# NCRC Data Analysis Tools - Summary

This document provides an overview of four web-based data analysis tools developed for the National Community Reinvestment Coalition (NCRC). All tools are Flask web applications that query BigQuery for financial and demographic data, generate reports, and provide interactive web interfaces.

---

## 1. LendSight

**Purpose:** Mortgage lending analysis and fair lending assessment tool

**Port:** 8082 (default)

**Description:**
LendSight analyzes Home Mortgage Disclosure Act (HMDA) mortgage lending data to assess lending patterns, disparities, and fair lending compliance across selected geographic areas. The tool generates comprehensive written reports with demographic context, lending trends, and AI-generated narrative summaries.

**Key Features:**
- **Geographic Selection:** Users can select up to 3 counties (state selection is optional)
- **Loan Purpose Filtering:** Defaults to home purchase loans only, with options for refinance and home equity lending
- **Data Sources:**
  - HMDA mortgage lending data from BigQuery (2018-2024)
  - U.S. Census Bureau demographic data (2010 Decennial Census, 2020 Decennial Census, 2024 ACS 5-year estimates)
- **Report Generation:**
  - Written narrative report with multiple sections
  - Executive summary (JavaScript-generated, not AI)
  - Population demographics table showing change over time (2010 Census, 2020 Census, 2024 ACS)
  - Key findings section
  - Analysis by demographic group (race/ethnicity, income, neighborhood characteristics)
  - Analysis by bank
  - AI-generated two-paragraph narrative summaries following each table (adhering to NCRC style guidelines)
- **Export Options:**
  - Excel export (.xlsx) with multiple sheets, proper number formatting (integers: #,##0; percentages: #,##0.00)
  - PDF export with page numbers, proper page breaks, and table integrity
  - Filenames: `NCRC_LendSight_[County]_[State]_[YYYYMMDD_HHMMSS].[ext]`
- **Technical Details:**
  - Uses FIPS codes end-to-end for Census API calls (no BigQuery dependency for FIPS lookup)
  - Weighted average aggregation for multi-county demographic data
  - Progress tracking via Server-Sent Events (SSE)
  - Census API integration with detailed progress tracking
  - Version: 0.9.0 (Development)

**Data Processing:**
- Queries BigQuery for HMDA loan-level data filtered by county, year, and loan purpose
- Fetches Census demographic data (population, race/ethnicity percentages) for selected counties
- Aggregates lending data by demographic characteristics, income levels, and neighborhood types
- Calculates lending rates, denial rates, and disparities compared to population shares

---

## 2. BranchSeeker

**Purpose:** Bank branch location analysis and market concentration assessment

**Port:** 8080 (default)

**Description:**
BranchSeeker analyzes FDIC Summary of Deposits (SOD) data to track bank branch locations, market concentration, and branch network changes over time. The tool generates written reports with Excel exports showing branch distribution, market share, and Herfindahl-Hirschman Index (HHI) calculations.

**Key Features:**
- **Geographic Selection:** Counties, states, or metropolitan areas
- **Data Source:** FDIC Summary of Deposits (SOD) data from BigQuery (2017-2025)
- **Report Generation:**
  - Written narrative report (no map visualization)
  - Executive summary
  - Analysis by county
  - Analysis by bank (with branch counts and deposits)
  - Market concentration analysis (HHI calculations)
  - AI-generated narrative summaries
- **Export Options:**
  - Excel export (.xlsx) with multiple sheets
  - All tables included in Excel format
- **Technical Details:**
  - Queries BigQuery for branch-level data (branch locations, deposits, service types)
  - Calculates market concentration metrics (HHI)
  - Tracks branch openings and closures over time
  - Identifies top banks by branch count and deposits

**Data Processing:**
- Queries BigQuery for FDIC SOD data filtered by geographic area and year
- Aggregates branch data by county, bank, and year
- Calculates market share and HHI for each geographic area
- Tracks changes in branch networks over time

---

## 3. BranchMapper

**Purpose:** Interactive map visualization of bank branch locations

**Port:** 8084 (default)

**Description:**
BranchMapper provides an interactive web-based map showing bank branch locations with demographic and income context. Users can visualize branch distribution across census tracts, filter by bank, year, and service type, and see demographic characteristics of areas with and without branches.

**Key Features:**
- **Interactive Map:** Leaflet-based map with branch markers
- **Geographic Selection:** Counties, states, or metropolitan areas
- **Data Sources:**
  - FDIC Summary of Deposits (SOD) data from BigQuery
  - U.S. Census Bureau tract-level demographic and income data
- **Visualization Features:**
  - Branch markers color-coded by bank
  - Census tract boundaries with income and minority percentage shading
  - Branch details popup (bank name, address, deposits, service type)
  - Filtering by bank, year, and service type
  - Legend showing income levels and minority percentages
- **Technical Details:**
  - Uses Leaflet.js for map rendering
  - Fetches Census tract boundaries via Census API
  - Real-time filtering and marker updates
  - No report generation (map-only tool)

**Data Processing:**
- Queries BigQuery for branch locations with coordinates
- Fetches Census tract boundaries and demographic data
- Categorizes tracts by income level (LMI, moderate, middle, upper) and minority percentage
- Renders branches and tract boundaries on interactive map

---

## 4. MergerMeter

**Purpose:** Two-bank merger impact analysis and CRA goal-setting assessment

**Port:** 8083 (default)

**Description:**
MergerMeter analyzes the potential impact of bank mergers on Community Reinvestment Act (CRA) compliance and fair lending. The tool compares lending patterns, branch networks, and assessment area coverage for an acquiring bank and a target bank, generating goal-setting analysis reports in Excel format matching the original merger report template.

**Key Features:**
- **Bank Identification:** Users provide LEI, RSSD ID, or Small Business ID for both acquirer and target banks
- **Assessment Areas:** Users can upload or manually define assessment areas for both banks (JSON format)
- **Data Sources:**
  - HMDA mortgage lending data (2020-2024)
  - Small Business Lending data (2019-2023)
  - FDIC Summary of Deposits branch data
- **Report Generation:**
  - Excel report matching original merger report template format
  - Goal-setting analysis sheets
  - Mortgage lending analysis by assessment area
  - Small business lending analysis
  - Branch network analysis
  - Assessment area comparison
  - Notes and methodology section
- **Export Options:**
  - Excel export (.xlsx) with template-based formatting
  - ZIP export containing multiple files
- **Technical Details:**
  - Uses original merger report Excel template (if available) for exact format matching
  - Queries BigQuery for HMDA, small business lending, and branch data
  - Compares lending patterns, branch locations, and assessment area coverage
  - Calculates lending gaps and opportunities for goal-setting

**Data Processing:**
- Queries BigQuery for HMDA loan-level data for both banks
- Queries BigQuery for small business lending data for both banks
- Queries BigQuery for branch locations and deposits
- Aggregates data by assessment area, loan purpose, and demographic characteristics
- Compares pre-merger and post-merger scenarios
- Generates goal-setting recommendations

---

## Common Technical Architecture

**Shared Components:**
- **Flask Web Framework:** All tools use Flask with a shared app factory pattern
- **BigQuery Integration:** All tools query Google Cloud BigQuery for financial data
- **Progress Tracking:** Server-Sent Events (SSE) for real-time progress updates
- **Shared Static Assets:** Common CSS, JavaScript, and UI components
- **Excel Generation:** Uses `openpyxl` for Excel report generation
- **PDF Generation:** LendSight uses `playwright` for HTML-to-PDF conversion

**Data Sources:**
- **BigQuery Project:** `hdma1-242116`
- **HMDA Data:** Mortgage lending data (2018-2024)
- **FDIC SOD Data:** Branch locations and deposits (2017-2025)
- **Small Business Lending Data:** CRA small business lending (2019-2023)
- **Census API:** Demographic and geographic data (2010 Decennial, 2020 Decennial, ACS estimates)

**Environment Requirements:**
- Python 3.x
- Google Cloud credentials for BigQuery access
- Census API key (for LendSight and BranchMapper)
- Claude API key (for AI-generated narrative summaries)
- Playwright browsers (for LendSight PDF generation)

**Deployment:**
- Each tool runs as a separate Flask application on its own port
- Tools can run simultaneously on different ports
- Development mode with hot-reloading enabled
- Production deployment would use a WSGI server (e.g., Gunicorn) behind a reverse proxy (e.g., Nginx)

---

## Access URLs (Local Development)

- **LendSight:** http://127.0.0.1:8082
- **BranchSeeker:** http://127.0.0.1:8080
- **BranchMapper:** http://127.0.0.1:8084
- **MergerMeter:** http://127.0.0.1:8083

---

## Notes

- All tools are currently in development (LendSight is version 0.9.0)
- Tools share common UI components and styling (NCRC Blue: `#034ea0`)
- AI-generated content uses Claude API and adheres to NCRC style guidelines
- Excel exports use proper number formatting and multi-sheet organization
- PDF exports (LendSight) ensure table integrity and proper page breaks
- All tools support real-time progress tracking for long-running analyses

