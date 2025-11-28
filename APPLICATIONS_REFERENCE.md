# JustData Applications - Reference Guide

**For:** Claude AI Agent  
**Purpose:** Quick reference for all JustData applications, features, and access levels

---

## Application Overview

### AI-Driven Reports (3 apps)
Generate comprehensive written reports with AI-powered insights:
- **LendSight** - Mortgage lending analysis
- **BranchSeeker** - Bank branch location analysis  
- **BizSight** - Small business lending analysis

### Interactive Tools (3 apps)
Interactive dashboards and data exploration:
- **BranchMapper** - Interactive branch map visualization
- **CommentMaker** - Federal rulemaking comment tool
- **DataExplorer** - Comprehensive data dashboard (HMDA, Small Business, Branch)

---

## Application Details

### 1. LendSight
**Type:** AI-Driven Report | **Port:** 8082 | **Status:** Fully Functional

**Features:**
- HMDA mortgage data (2018-2024)
- Census demographic data (2010, 2020, 2024 ACS)
- Up to 3 counties analysis
- AI-generated executive summary, key findings, narratives
- Loan purpose filtering (home purchase, refinance, home equity)

**Exports:** Excel, PDF, PowerPoint, Social Share

**Access:**
- Public/Just Economy Club: Own county only, view-only
- Member+: Multiple counties, full exports
- Staff/Admin: Unlimited, all formats

---

### 2. BranchSeeker
**Type:** AI-Driven Report | **Port:** 8080 | **Status:** Fully Functional

**Features:**
- FDIC Summary of Deposits (2017-2025)
- County/state/metro analysis
- HHI market concentration calculations
- LMI/MMCT tract analysis
- Year-over-year trends
- AI-generated insights

**Exports:** Excel, CSV, JSON, ZIP, PowerPoint, Social Share

**Access:**
- Public/Just Economy Club: Locked (requires membership)
- Member+: Full access, multiple geographies
- Staff/Admin: Unlimited, all formats

---

### 3. BizSight
**Type:** AI-Driven Report | **Port:** 8081 | **Status:** Fully Functional

**Features:**
- HMDA Section 1071 small business data (2019-2023)
- Tract-level and lender-level analysis
- Income/neighborhood indicators
- Loan size categories, revenue analysis
- HHI calculations
- AI-generated insights

**Exports:** Excel, PDF, PowerPoint, Social Share

**Access:**
- Public/Just Economy Club: Locked (requires membership)
- Member+: Full access, multiple geographies
- Staff/Admin: Unlimited, all formats

---

### 4. BranchMapper
**Type:** Interactive Tool | **Port:** 8084 | **Status:** Fully Functional

**Features:**
- Interactive Leaflet.js map
- Branch markers (color-coded by bank)
- Census tract boundaries with income/minority shading
- Filter by bank, year, service type
- Real-time tract boundary fetching

**Exports:** Map screenshot, data CSV/Excel, Social Share

**Access:**
- Public/Just Economy Club: Locked (requires membership)
- Member+: Full access, multiple geographies
- Staff/Admin: Unlimited, all formats

**Note:** No AI narratives, user-driven exploration only

---

### 5. CommentMaker
**Type:** Interactive Tool | **Port:** TBD | **Status:** In Development

**Features:**
- Template-based comment creation
- Integration with JustData analysis results
- Federal submission formatting
- Multi-agency support (CFPB, FDIC, OCC, Fed)
- Submission tracking

**Exports:** PDF, Word, Excel, Social Share

**Access:**
- Public/Just Economy Club: Own county only, view-only
- Member+: Full access, full exports
- Staff/Admin: Unlimited, all formats

---

### 6. DataExplorer
**Type:** Interactive Tool | **Port:** 8085 | **Status:** Fully Functional

**Features:**
- **Two modes:**
  - Area Analyses: Geography/year/data type filtering
  - Lender Targeting: Specific lender + peer comparison
- **Three data types:**
  - HMDA mortgage (2018-2024)
  - Small Business Section 1071 (2019-2023)
  - Branch FDIC SOD (2017-2025)
- Interactive filtering, real-time visualization
- Summary cards, trend charts, top lenders tables
- HHI calculations, MMCT analysis

**Exports:** Excel, PDF, PowerPoint, Social Share

**Access Levels:**
- **Member (Standard):**
  - Basic filtering
  - Standard exports
  - Area analyses + lender targeting
  - All three data types
- **Member Plus (Enhanced):**
  - All standard features, PLUS:
  - Advanced filtering options
  - Bulk export capabilities
  - Custom report builder
  - Historical data access
  - Priority support
- **Institutional:**
  - Same as Member (standard features)
  - Additional: CSV exports, unlimited geography
- **Staff/Admin:**
  - All Member Plus features
  - API access
  - JSON exports
  - Unlimited everything

**Note:** No AI narratives, user-driven analysis only

---

## User Types & Access with Pricing

### 1. Public (Free)
- **Price:** **Free**
- **Geographic:** Own county only
- **Exports:** None (view-only)
- **Apps:** LendSight (limited), CommentMaker (limited), others locked
- **DataExplorer:** Locked
- **Upsell:** Member for multi-county + exports

### 2. Just Economy Club (Free)
- **Price:** **Free** (with Just Economy Club membership)
- **Geographic:** Own county only
- **Exports:** None (view-only)
- **Apps:** LendSight (limited), CommentMaker (limited), others locked
- **DataExplorer:** Locked
- **Upsell:** Member for multi-county + exports

### 3. Member (Included with NCRC Membership)
- **Price:** **Included with $900/year NCRC membership** (no additional cost)
- **Geographic:** Up to 3 counties/metro areas
- **Exports:** Excel, PDF, PowerPoint
- **Apps:** 
  - ✅ LendSight: Full access
  - ✅ BranchSeeker: Full access
  - ✅ BizSight: Full access
  - ✅ BranchMapper: Full access
  - ✅ CommentMaker: Full access
  - 🔒 **DataExplorer: LOCKED** (premium feature)
- **Upsell:** Member Plus ($500-750/year) for DataExplorer access

### 4. Member Plus (Premium Add-On)
- **Price:** **$500-750/year** (add-on to Member tier)
- **Geographic:** 5+ counties or unlimited
- **Exports:** Excel, PDF, PowerPoint
- **Apps:** 
  - ✅ All Member features, PLUS:
  - ✅ **DataExplorer: Full access** (enhanced features)
- **Enhanced DataExplorer Features:**
  - Advanced filtering options
  - Bulk export capabilities
  - Custom report builder
  - Historical data access
  - Priority support
- **Value Proposition:** For power users and researchers who need advanced data analysis capabilities

### 5. Institutional (Banks/For-Profits)
- **Price:** **$5,000-15,000/year**
  - **Base Tier:** $5,000/year (standard DataExplorer features)
  - **Premium Tier:** $10,000-15,000/year (enhanced DataExplorer features)
- **Geographic:** Unlimited
- **Exports:** Excel, PDF, PowerPoint, CSV
- **Apps:** 
  - ✅ All apps including DataExplorer
  - ✅ Base tier: Standard DataExplorer features
  - ✅ Premium tier: Enhanced DataExplorer features (advanced filtering, bulk exports, custom reports, historical data)
- **Target:** Banks, for-profit businesses, consulting firms

### 6. Staff
- **Price:** **Included with NCRC employment** (no cost)
- **Geographic:** Unlimited
- **Exports:** All formats (Excel, PDF, PowerPoint, CSV, JSON)
- **Apps:** Full access to everything including DataExplorer
- **Additional:** Analytics dashboard

### 7. Admin
- **Price:** **N/A** (internal only, no cost)
- **Geographic:** Unlimited
- **Exports:** All formats
- **Apps:** Full access to everything
- **Additional:** Analytics + Administration dashboards

---

## Access Matrix

| App | Public | Just Economy | Member | Member Plus | Institutional | Staff | Admin |
|-----|--------|--------------|--------|-------------|---------------|-------|-------|
| **AI Reports** |
| LendSight | Limited | Limited | Full (up to 3 counties) | Full (5+ counties) | Full (unlimited) | Full | Full |
| BranchSeeker | Locked | Locked | Full (up to 3 counties) | Full (5+ counties) | Full (unlimited) | Full | Full |
| BizSight | Locked | Locked | Full (up to 3 counties) | Full (5+ counties) | Full (unlimited) | Full | Full |
| **Interactive** |
| BranchMapper | Locked | Locked | Full (up to 3 counties) | Full (5+ counties) | Full (unlimited) | Full | Full |
| CommentMaker | Limited | Limited | Full | Full | Full | Full | Full |
| DataExplorer | Locked | Locked | 🔒 **Locked** | ✅ **Full** | ✅ Standard | Full | Full |
| **Admin** |
| Analytics | Hidden | Hidden | Hidden | Hidden | Hidden | Full | Full |
| Administration | Hidden | Hidden | Hidden | Hidden | Hidden | Hidden | Full |

**Legend:**
- **Full** = Complete access with all features
- **Standard** = Basic features (DataExplorer: basic filtering, standard exports)
- **Enhanced** = Advanced features (DataExplorer: advanced filtering, bulk exports, custom reports)
- **Limited** = Own county only, view-only
- **Locked** = Visible but requires membership
- **Hidden** = Not visible to user type

---

## Export Formats by User Type

| Format | Public | Just Economy | Member | Member Plus | Institutional | Staff | Admin |
|--------|--------|--------------|--------|-------------|---------------|-------|-------|
| Excel | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PDF | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PowerPoint | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CSV | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| JSON | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Social Share | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## DataExplorer Feature Comparison

| Feature | Public | Just Economy Club | Member | Member Plus | Institutional | Staff/Admin |
|---------|--------|-------------------|--------|-------------|---------------|-------------|
| Access to DataExplorer | 🔒 Locked | 🔒 Locked | 🔒 **Locked** | ✅ **Full** | ✅ Standard | ✅ Full |
| Basic filtering | N/A | N/A | N/A | ✅ | ✅ | ✅ |
| Standard exports | N/A | N/A | N/A | ✅ | ✅ | ✅ |
| Advanced filtering | N/A | N/A | N/A | ✅ | ❌ (Premium only) | ✅ |
| Bulk exports | N/A | N/A | N/A | ✅ | ❌ (Premium only) | ✅ |
| Custom report builder | N/A | N/A | N/A | ✅ | ❌ (Premium only) | ✅ |
| API access | N/A | N/A | N/A | ❌ | ❌ | ✅ |
| Historical data access | N/A | N/A | N/A | ✅ | ❌ (Premium only) | ✅ |

**Note:** DataExplorer is a premium feature. Members must upgrade to Member Plus ($500-750/year) to access it. Institutional base tier gets standard features; premium tier ($10,000-15,000/year) gets enhanced features.

---

## Partial Access Upsell Options

### Geographic Expansion
- **Single County:** Unlock one additional county
- **Multi-County Package:** Up to 5 counties
- **State-Wide:** All counties in one state
- **Regional:** Multiple states/regions

### Export Features
- **Basic Export:** Excel only, limited monthly
- **Standard Export:** Excel/PDF/PowerPoint, higher limit
- **Professional Export:** All formats, unlimited

### Application-Specific Premiums
- **Priority AI Processing:** Faster report generation
- **Extended Historical Data:** Pre-2018 data access
- **Custom Market Definitions:** Save market areas
- **Custom Benchmark Comparisons:** Custom peer groups
- **Custom Map Styling:** Branded map exports
- **Priority Comment Review:** Expert feedback

---

## Key Technical Details

### Data Sources
- **HMDA:** `hdma1-242116.hmda.hmda` (2018-2024)
- **Small Business:** `hdma1-242116.sb.disclosure`, `hdma1-242116.sb.lenders` (2019-2023)
- **Branches:** `hdma1-242116.branches.sod` (2017-2025)
- **Census:** U.S. Census Bureau API (2010, 2020 Decennial; 2024 ACS)

### AI Integration
- **Provider:** Claude (primary), GPT-4 (fallback)
- **Model:** Claude Sonnet 4
- **Style:** NCRC guidelines, objective third-person, factual patterns only

### Common Features
- Real-time progress tracking (SSE)
- Background processing
- Error handling
- Responsive design
- Social media sharing

---

## Deprecated Applications

- **MergerMeter** - Replaced by DataExplorer
  - Two-bank merger analysis now available in DataExplorer's lender targeting mode

---

---

## Pricing Summary

| User Type | Price | Key Features |
|-----------|-------|--------------|
| Public | Free | Own county, view-only |
| Just Economy Club | Free | Own county, view-only |
| Member | Included with $900/year NCRC membership | Up to 3 counties, full exports, all apps except DataExplorer |
| Member Plus | $500-750/year (add-on) | 5+ counties, DataExplorer full access |
| Institutional Base | $5,000/year | Unlimited geography, standard DataExplorer |
| Institutional Premium | $10,000-15,000/year | Unlimited geography, enhanced DataExplorer |
| Staff | Included with employment | Full access |
| Admin | N/A (internal) | Full access |

**See `PRICING_SUMMARY.md` for detailed pricing information and revenue projections.**

---

**Last Updated:** 2025-01-27

