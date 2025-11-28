# NCRC Applications - Complete List for Landing Page

## All Available Applications

### 1. **BranchSeeker** - Bank Branch Location Analysis
**Port:** 8080  
**URL:** http://127.0.0.1:8080  
**Status:** ✅ Fully Functional

**Description:**
Analyzes FDIC Summary of Deposits (SOD) data to track bank branch locations, market concentration, and branch network changes over time.

**Key Features:**
- County, state, and metro area analysis
- Market concentration analysis (HHI calculations)
- Year-over-year trend analysis
- LMI (Low-to-Moderate Income) and MMCT (Majority-Minority Census Tract) analysis
- AI-powered insights and narrative summaries
- Excel, CSV, JSON, and ZIP export options
- Interactive web reports with collapsible tables

**Data Sources:**
- FDIC Summary of Deposits (SOD) - 2017-2025
- Branch locations, deposits, service types

---

### 2. **LendSight** - Mortgage Lending Analysis
**Port:** 8082  
**URL:** http://127.0.0.1:8082  
**Status:** ✅ Fully Functional (Version 0.9.0)

**Description:**
Analyzes Home Mortgage Disclosure Act (HMDA) mortgage lending data to assess lending patterns, disparities, and fair lending compliance.

**Key Features:**
- Multi-county analysis (up to 3 counties)
- HMDA data analysis (2018-2024)
- Census demographic integration (2010, 2020, 2024)
- Loan purpose filtering (home purchase, refinance, home equity)
- AI-generated narrative reports
- Analysis by demographic group (race/ethnicity, income, neighborhood)
- Analysis by individual bank/lender
- Excel and PDF export options

**Data Sources:**
- HMDA mortgage lending data (BigQuery)
- U.S. Census Bureau demographic data
- Weighted average aggregation for multi-county analysis

---

### 3. **BranchMapper** - Interactive Branch Map
**Port:** 8084  
**URL:** http://127.0.0.1:8084  
**Status:** ✅ Fully Functional

**Description:**
Interactive map visualization of bank branch locations with geographic filtering and branch details.

**Key Features:**
- Interactive map with Leaflet.js
- State and county selection
- Branch location markers
- Branch details popups
- Export map and data
- Real-time filtering

**Data Sources:**
- FDIC Summary of Deposits (SOD) data
- Branch coordinates and addresses

---

### 4. **MergerMeter** - Two-Bank Merger Impact Analysis
**Port:** 8083  
**URL:** http://127.0.0.1:8083  
**Status:** ✅ Fully Functional

**Description:**
Analyzes two-bank mergers for CRA compliance and fair lending. Generates comprehensive reports with assessment area mapping and goal-setting analysis.

**Key Features:**
- Two-bank merger analysis
- Assessment area generation (CBSA-level logic)
- CRA compliance assessment
- Fair lending analysis
- Market concentration analysis (HHI)
- Excel report generation
- Real-time progress tracking
- Interactive web interface

**Data Sources:**
- FDIC Summary of Deposits (SOD)
- HMDA lending data
- Census demographic data
- BigQuery financial data

**Recent Updates:**
- Updated to CBSA-level deposit threshold logic
- Enhanced Excel filenames with bank names

---

### 5. **BizSight** - Small Business Lending Analysis
**Port:** 8081  
**URL:** http://127.0.0.1:8081  
**Status:** ✅ Fully Functional

**Description:**
Analyzes small business lending data from HMDA Section 1071 to assess lending patterns and economic indicators.

**Key Features:**
- Tract-level and lender-level analysis
- Small business lending patterns
- AI-powered insights
- Interactive web reports
- Excel export
- Benchmark comparisons
- Income group analysis

**Data Sources:**
- HMDA Section 1071 small business lending data
- Census tract demographics
- National benchmarks

---

### 6. **MemberView** - Member Management Application
**Port:** 8082 (Standalone)  
**URL:** http://127.0.0.1:8082 (when running standalone)  
**Status:** 🏗️ In Development

**Description:**
Self-contained application for managing and analyzing NCRC member data from HubSpot. Provides comprehensive member tracking and analytics.

**Key Features:**
- Member dashboard with status, financials, and engagement
- Member details view with contacts and payment history
- Financial tracking (dues, donations)
- Contact management
- Engagement analytics
- Retention analysis
- Search and filter capabilities
- Excel/CSV export
- Interactive member map (planned)

**Data Sources:**
- HubSpot contacts, deals, and companies data
- Processed parquet/CSV files

**Note:** Can run standalone or integrated with main platform

---

## Application Summary Table

| Application | Port | Status | Primary Purpose |
|------------|------|--------|----------------|
| **BranchSeeker** | 8080 | ✅ Ready | Bank branch location analysis |
| **LendSight** | 8082 | ✅ Ready | Mortgage lending analysis |
| **BranchMapper** | 8084 | ✅ Ready | Interactive branch map |
| **MergerMeter** | 8083 | ✅ Ready | Two-bank merger analysis |
| **BizSight** | 8081 | ✅ Ready | Small business lending analysis |
| **MemberView** | 8082* | 🏗️ Dev | Member management |

*MemberView uses port 8082 when running standalone, but can be configured differently

---

## Quick Start Commands

```bash
# Start all applications
python start_all_apps.bat
# or
.\start_all_apps.ps1

# Start individually
python run_branchseeker.py    # Port 8080
python run_lendsight.py        # Port 8082
python run_branchmapper.py    # Port 8084
python run_mergermeter.py     # Port 8083
python run_bizsight.py        # Port 8081
python run_memberview.py      # Port 8082 (standalone)
```

---

## Landing Page Recommendations

### Suggested Layout:
1. **Header** - NCRC JustData Platform
2. **Main Section** - Grid of 6 application cards
3. **Each Card Should Include:**
   - Application name and icon
   - Brief description (1-2 sentences)
   - Key features (3-4 bullet points)
   - Status badge (Ready/In Development)
   - "Launch" button linking to the app

### Color Coding Suggestions:
- **BranchSeeker** - Blue (banking/financial)
- **LendSight** - Green (lending/mortgage)
- **BranchMapper** - Orange (mapping/visualization)
- **MergerMeter** - Purple (merger/analysis)
- **BizSight** - Teal (business/small business)
- **MemberView** - Red (membership/CRM)

---

## Application Categories

### Financial Analysis
- BranchSeeker
- LendSight
- BizSight
- MergerMeter

### Visualization
- BranchMapper

### Management
- MemberView

---

**Last Updated:** Current session  
**Total Applications:** 6  
**Fully Functional:** 5  
**In Development:** 1


