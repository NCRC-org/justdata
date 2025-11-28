# Report Template Sections Reference

This document identifies all narrative analysis sections and tables in the report template for working on prompts and charts.

## 📊 NARRATIVE ANALYSIS SECTIONS (AI-Generated Content)

These sections are populated by AI-generated content via prompts in `justdata/apps/branchseeker/analysis.py`.

### 1. Executive Summary
- **HTML Location**: Lines 483-491
- **Section ID**: `aiExecutiveSummarySection`
- **Content ID**: `executiveSummaryContent`
- **Prompt Method**: `generate_executive_summary()` (analysis.py:14-53)
- **Display**: Hidden by default (`display: none`), shown when AI insights available

### 2. Key Findings
- **HTML Location**: Lines 519-527
- **Section ID**: `aiKeyFindingsSection`
- **Content ID**: `keyFindingsContent`
- **Prompt Method**: `generate_key_findings()` (analysis.py:55-88)
- **Display**: Hidden by default, shown when AI insights available

### 3. Bank Strategies Analysis
- **HTML Location**: Lines 560-568
- **Section ID**: `aiBankStrategiesSection`
- **Content ID**: `bankStrategiesContent`
- **Prompt Method**: `generate_bank_strategies_analysis()` (analysis.py:126-160)
- **Display**: Hidden by default, shown when AI insights available

### 4. Community Impact Analysis
- **HTML Location**: Lines 596-604
- **Section ID**: `aiCommunityImpactSection`
- **Content ID**: `communityImpactContent`
- **Prompt Method**: `generate_community_impact_analysis()` (analysis.py:162-195)
- **Display**: Hidden by default, shown when AI insights available

### 5. Trends Analysis
- **HTML Location**: Lines 639-647
- **Section ID**: `aiTrendsAnalysisSection`
- **Content ID**: `trendsAnalysisContent`
- **Prompt Method**: `generate_trends_analysis()` (analysis.py:90-124)
- **Display**: Hidden by default, shown when AI insights available

---

## 📋 TABLES IN THE REPORT

### Table 1: Yearly Breakdown
- **HTML Location**: Lines 493-517
- **Table ID**: `summaryTable`
- **JavaScript Populate Function**: `populateTable('summaryTable', data.summary)` (line 693)
- **Columns**:
  - County
  - Year
  - Total Branches
  - LMI Branches
  - Minority Branches
  - Number of Banks
  - LMI %
  - Minority %
- **Data Source**: `data.summary` (from report_builder.py: `create_summary_table()`)
- **Features**: Always visible, no collapse button

### Table 2: Analysis by Bank
- **HTML Location**: Lines 529-558
- **Table ID**: `bankTable`
- **JavaScript Populate Function**: `populateTable('bankTable', data.by_bank)` (line 694)
- **Columns**:
  - Bank Name
  - County
  - Year
  - Total Branches
  - LMI Branches
  - Minority Branches
  - LMI %
  - Minority %
- **Data Source**: `data.by_bank` (from report_builder.py: `create_bank_summary()`)
- **Features**: 
  - Collapsible (Show/Hide button)
  - Auto-collapses if > 10 rows (line 966)
  - Shows first 3 rows when collapsed

### Table 3: Analysis by County
- **HTML Location**: Lines 570-594
- **Table ID**: `countyTable`
- **JavaScript Populate Function**: `populateTable('countyTable', data.by_county)` (line 695)
- **Columns**:
  - County
  - Year
  - Total Branches
  - LMI Branches
  - Minority Branches
  - Number of Banks
  - LMI %
  - Minority %
- **Data Source**: `data.by_county` (from report_builder.py: `create_county_summary()`)
- **Features**: Always visible, no collapse button

### Table 4: Year-over-Year Trends
- **HTML Location**: Lines 606-637
- **Table ID**: `trendsTable`
- **JavaScript Populate Function**: `populateTable('trendsTable', data.trends)` (line 700)
- **Columns**:
  - Year
  - Total Branches
  - LMI Branches
  - Minority Branches
  - Number of Banks
  - Total Branches YoY %
  - LMI Branches YoY %
  - Minority Branches YoY %
  - LMI %
  - Minority %
- **Data Source**: `data.trends` (from report_builder.py: `create_trend_analysis()`)
- **Features**: 
  - Hidden by default (`display: none`)
  - Shown only if `data.trends` has data (line 698)
  - Collapsible (Show/Hide button)

---

## 📈 CHARTS/VISUALIZATIONS

**Current Status**: No charts are currently implemented in the report template.

**Potential Chart Locations** (suggestions):
- After "Latest Statistics" section (after line 481)
- After each table section
- In a dedicated "Visualizations" section

**Chart Libraries Available**:
- Consider Chart.js, D3.js, or Plotly.js for interactive charts
- For print-friendly charts, consider static image generation or SVG

---

## 🔧 JAVASCRIPT FUNCTIONS

### Key Functions for Content Population:
- `populateAIInsights(aiInsights)` (lines 704-752): Populates all AI narrative sections
- `formatMarkdownContent(content)` (lines 754-824): Formats AI-generated markdown content
- `populateTable(tableId, data)` (lines 918-981): Populates table data with formatting
- `populateSummaryCards(rawData)` (lines 826-886): Creates summary statistics cards

### Data Flow:
1. `loadReportData()` fetches from `/report-data` endpoint
2. `displayReport(data, metadata)` orchestrates population
3. AI insights come from `metadata.ai_insights`
4. Table data comes from `data.summary`, `data.by_bank`, `data.by_county`, `data.trends`

---

## 📝 PROMPT FILES

All AI prompts are defined in:
- **File**: `justdata/apps/branchseeker/analysis.py`
- **Class**: `BranchSeekerAnalyzer`
- **Methods**: Each narrative section has a corresponding `generate_*()` method

### Prompt Structure:
Each prompt includes:
- Context data (counties, years, statistics)
- Important definitions (LMICT, MMCT)
- Focus areas
- Writing requirements (objective, third-person, no speculation)

---

## 🎯 SUMMARY STATISTICS CARDS

- **HTML Location**: Lines 476-481
- **Container ID**: `summaryCards`
- **JavaScript Function**: `populateSummaryCards(rawData)` (lines 826-886)
- **Cards Display**:
  - Total Branches (latest year)
  - LMI Branches (latest year)
  - Minority Branches (latest year)
  - LMI % (latest year)
  - Minority % (latest year)


