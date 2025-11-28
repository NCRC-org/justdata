# DataExplorer Dashboard Proposal
## Three Data Type Dashboards: HMDA, Small Business, and Branch Data

Based on review of BranchSeeker and BizSight applications, here are comprehensive dashboard proposals for each data type in DataExplorer.

---

## Overview

DataExplorer will have **three distinct dashboards**, each activated when the user selects:
1. **Mortgage Data (HMDA)** - Already partially implemented
2. **Small Business Data** - New dashboard based on BizSight features
3. **Branch Data** - New dashboard based on BranchSeeker features

Each dashboard will have its own set of visualizations, tables, and analysis tools tailored to the specific data type.

---

## 1. HMDA (Mortgage) Dashboard

### Current Implementation Status
- ✅ Area Analysis tab with feature cards
- ✅ Summary tables, demographics, income/neighborhood indicators
- ✅ Top lenders table
- ✅ HHI calculations
- ✅ Trends analysis

### Recommended Enhancements

#### Additional Visualizations:
1. **Loan Purpose Breakdown Chart**
   - Pie/bar chart showing distribution of home purchase, refinance, home improvement loans
   - Year-over-year comparison

2. **Action Taken Flow Chart**
   - Sankey diagram showing loan application flow (Applications → Originated/Denied/Withdrawn)
   - Percentage breakdowns

3. **Geographic Heat Map**
   - Choropleth map showing loan volume by county/metro
   - Color intensity based on loan amounts or counts

4. **Lender Market Share Chart**
   - Horizontal bar chart of top 10 lenders with market share percentages
   - Interactive tooltips showing loan counts and amounts

5. **Demographic Disparity Analysis**
   - Side-by-side comparison of lending rates vs. population percentages
   - Highlight disparities (e.g., if Hispanic population is 20% but receives 10% of loans)

#### Additional Tables:
1. **Denial Rate Analysis**
   - Denial rates by demographic group
   - Comparison to national/state averages

2. **Loan Amount Distribution**
   - Percentiles (25th, 50th, 75th, 90th) by demographic group
   - Average loan amounts

3. **Time Series Trends**
   - Monthly/quarterly breakdowns (if available)
   - Seasonal patterns

---

## 2. Small Business Dashboard (New)

### Based on BizSight Features

#### Core Visualizations:

1. **Loan Volume Overview**
   - **Summary Cards**: Total loans, total amount, average loan size, number of lenders
   - **Year-over-Year Line Chart**: Trends in loan counts and amounts
   - **Quick Stats**: Percentage change from previous year

2. **Loan Size Distribution**
   - **Stacked Bar Chart**: Loans by size category (Under $100K, $100K-$250K, $250K-$1M) over years
   - **Pie Chart**: Current year distribution
   - **Comparison**: County vs. State vs. National averages

3. **Income Group Analysis**
   - **Grouped Bar Chart**: Loans by income group (Low, Moderate, Middle, Upper) by year
   - **Percentage Stacked Chart**: Income group distribution over time
   - **LMI Focus**: Highlight Low-to-Moderate Income (LMI) lending patterns

4. **LMI Tract Analysis**
   - **Dual Metric Chart**: Loans to LMI tracts vs. non-LMI tracts
   - **Percentage Trend**: LMI tract lending as % of total over time
   - **Geographic Map**: Census tract-level visualization (if tract data available)

5. **Top Lenders Visualization**
   - **Horizontal Bar Chart**: Top 10 lenders by loan volume
   - **Market Share Pie Chart**: Concentration visualization
   - **Lender Comparison Table**: Side-by-side metrics

6. **Market Concentration (HHI)**
   - **Line Chart**: HHI trends over years
   - **Concentration Level Indicator**: Visual gauge showing Unconcentrated/Moderately Concentrated/Highly Concentrated
   - **HHI Components**: Breakdown showing contribution of top 5 lenders

#### Core Tables:

1. **County Summary Table** (Similar to BizSight Section 2)
   - **By Number of Loans**:
     - Total loans by year
     - Loans by size category (Under $100K, $100K-$250K, $250K-$1M)
     - Loans by income group
     - Loans to LMI tracts
     - Year-over-year changes
   
   - **By Amount of Loans**:
     - Total loan amounts by year
     - Amounts by size category
     - Amounts by income group
     - Amounts to LMI tracts
     - Year-over-year changes

2. **Comparison Table** (Similar to BizSight Section 3)
   - **County vs. State vs. National**:
     - Loan counts per 1,000 businesses (if business count data available)
     - Average loan amounts
     - LMI tract lending percentages
     - Loan size distribution percentages
   - **Benchmark Indicators**: Above/Below/At benchmark indicators

3. **Top Lenders Table** (Similar to BizSight Section 4)
   - **By Number of Loans**:
     - Lender name, total loans, loans by size category, loans by income group
     - LMI tract lending percentage
     - Market share
   
   - **By Amount of Loans**:
     - Lender name, total amount, amounts by size category
     - Average loan size
     - Market share

4. **HHI by Year Table**
   - Year, HHI value, concentration level
   - Top 5 lenders and their market shares
   - Year-over-year HHI change

5. **Income Group Detail Table**
   - Detailed breakdown by income group
   - Loan counts and amounts
   - Percentage of total
   - Comparison to population/business demographics (if available)

#### Interactive Features:

1. **Drill-Down Capability**
   - Click on a lender to see detailed breakdown
   - Click on a year to see quarterly/monthly data (if available)
   - Click on a geographic area to see tract-level detail

2. **Filtering Options**
   - Filter by loan size category
   - Filter by income group
   - Filter by LMI tract status
   - Filter by lender (multi-select)

3. **Export Options**
   - Export all tables to Excel (separate sheets)
   - Export charts as images (PNG/SVG)
   - Export full dashboard as PDF report

---

## 3. Branch Data Dashboard (New)

### Based on BranchSeeker Features

#### Core Visualizations:

1. **Branch Network Overview**
   - **Summary Cards**: Total branches, total deposits, average deposits per branch, number of banks
   - **Branch Count Trend**: Line chart showing branch count over years
   - **Deposit Trend**: Line chart showing total deposits over years
   - **Net Change Indicator**: Visual indicator showing branch growth/decline

2. **Branch Distribution by Geography**
   - **County Breakdown**: Bar chart showing branches per county
   - **State/Metro Comparison**: Comparison across selected geographies
   - **Geographic Map**: Branch locations on interactive map (if coordinates available)

3. **LMI/MMCT Branch Analysis**
   - **Stacked Bar Chart**: Branches by category (LMI only, MMCT only, Both LMICT/MMCT, Neither)
   - **Percentage Trend**: LMI/MMCT branch percentage over time
   - **Accessibility Metric**: Branches per capita in LMI/MMCT areas

4. **Bank Market Share**
   - **Top Banks Chart**: Horizontal bar chart of top 10 banks by branch count
   - **Deposit Market Share**: Pie chart showing deposit concentration
   - **Branch vs. Deposit Comparison**: Scatter plot showing branch count vs. deposit volume

5. **Market Concentration (HHI)**
   - **HHI Trend Line**: Market concentration over years
   - **Concentration Level Gauge**: Visual indicator
   - **HHI by Geography**: Comparison across counties/metros

6. **Branch Service Types**
   - **Service Type Distribution**: Pie/bar chart of branch service types
   - **Service Type Trends**: Changes in service type distribution over time
   - **Full-Service vs. Limited-Service**: Comparison

7. **Year-over-Year Changes**
   - **Branch Openings/Closings**: Net change visualization
   - **Bank Entry/Exit**: Banks entering/leaving the market
   - **Deposit Shifts**: Changes in deposit distribution

#### Core Tables:

1. **Yearly Breakdown Table** (Similar to BranchSeeker Table 1)
   - **Columns**:
     - Year
     - Total Branches
     - LMI Only Branches (distinct from MMCT)
     - MMCT Only Branches (distinct from LMI)
     - Both LMICT/MMCT Branches
     - Neither LMI nor MMCT Branches
     - Total Deposits
     - Average Deposits per Branch
     - Net Change (from first to last year)
   - **Deduplication**: Each branch appears in only one category

2. **Analysis by Bank Table** (Similar to BranchSeeker Table 2)
   - **Columns**:
     - Bank Name
     - RSSD ID
     - Total Branches (latest year)
     - LMI Only Branches (count and %)
     - MMCT Only Branches (count and %)
     - Both LMICT/MMCT Branches (count and %)
     - Total Deposits
     - Average Deposits per Branch
     - Net Change in Branches (over study period)
     - Market Share (% of total branches)
   - **Sorting**: By total branches (descending)

3. **Analysis by County Table**
   - **Columns**:
     - County Name
     - State
     - Total Branches
     - Branches per 10,000 population
     - Total Deposits
     - Average Deposits per Branch
     - LMI Branch Count
     - MMCT Branch Count
     - Both LMICT/MMCT Branch Count
     - Number of Banks Operating
     - HHI (market concentration)

4. **Market Concentration (HHI) Table**
   - **Columns**:
     - Year
     - HHI Value
     - Concentration Level (Unconcentrated/Moderately Concentrated/Highly Concentrated)
     - Top 5 Banks and Market Shares
     - Year-over-Year HHI Change

5. **Service Type Analysis Table**
   - **Columns**:
     - Service Type
     - Branch Count
     - Percentage of Total
     - Total Deposits
     - Average Deposits
     - Year-over-Year Change

6. **Branch Openings/Closings Table**
   - **Columns**:
     - Year
     - New Branches Opened
     - Branches Closed
     - Net Change
     - Banks Entering Market
     - Banks Exiting Market

#### Interactive Features:

1. **Branch Location Map**
   - Interactive map showing branch locations
   - Color coding by bank
   - Filter by bank, service type, LMI/MMCT status
   - Click on branch for details (address, deposits, service type)

2. **Drill-Down Capability**
   - Click on bank to see all branches
   - Click on county to see county-level detail
   - Click on year to see year-specific analysis

3. **Comparison Tools**
   - Compare multiple banks side-by-side
   - Compare multiple counties
   - Compare multiple years

4. **Filtering Options**
   - Filter by bank (multi-select)
   - Filter by service type
   - Filter by LMI/MMCT status
   - Filter by deposit size range
   - Filter by year range

5. **Export Options**
   - Export all tables to Excel (separate sheets)
   - Export branch locations to CSV/KML
   - Export maps as images
   - Export full dashboard as PDF report

---

## Implementation Recommendations

### 1. Data Type Selection
- **Location**: Top of dashboard (already implemented)
- **Options**: Radio buttons or tabs for HMDA, Small Business, Branch Data
- **Behavior**: Switching data types reloads the entire dashboard with appropriate visualizations

### 2. Shared Components
- **Geography Selector**: Counties, Metro Areas, States (already implemented)
- **Year Selector**: Multi-select checkboxes with quick-select buttons (already implemented)
- **Export Buttons**: Excel, PowerPoint, PDF (to be implemented)

### 3. Dashboard Layout
- **Top Section**: Summary cards with key metrics
- **Middle Section**: Main visualizations (charts, maps)
- **Bottom Section**: Detailed tables
- **Sidebar**: Filters and controls (optional, or keep current top filter cards)

### 4. Technology Stack
- **Charts**: Chart.js (already in use) or consider D3.js for more complex visualizations
- **Maps**: Leaflet.js (for branch locations) or Mapbox/Google Maps API
- **Tables**: DataTables.js for sortable, searchable tables
- **Export**: 
  - Excel: openpyxl or xlsxwriter
  - PowerPoint: python-pptx
  - PDF: ReportLab or WeasyPrint

### 5. Performance Considerations
- **Lazy Loading**: Load visualizations on demand
- **Data Caching**: Cache frequently accessed queries
- **Pagination**: For large tables (show 25/50/100 rows per page)
- **Progressive Loading**: Show summary first, then load detailed data

### 6. User Experience
- **Loading States**: Show spinners/progress bars during data fetching
- **Error Handling**: Clear error messages with suggestions
- **Tooltips**: Helpful tooltips explaining metrics and calculations
- **Responsive Design**: Ensure dashboards work on tablets and larger screens
- **Accessibility**: ARIA labels, keyboard navigation, screen reader support

---

## Priority Implementation Order

### Phase 1: Small Business Dashboard (High Priority)
1. Summary cards and overview charts
2. County summary tables (by count and amount)
3. Top lenders table
4. HHI visualization and table
5. Basic filtering

### Phase 2: Branch Data Dashboard (High Priority)
1. Summary cards and branch count trends
2. Yearly breakdown table
3. Analysis by bank table
4. HHI visualization
5. Basic filtering

### Phase 3: Enhanced HMDA Dashboard (Medium Priority)
1. Additional visualizations (loan purpose, action taken flow)
2. Denial rate analysis
3. Geographic heat maps
4. Enhanced demographic analysis

### Phase 4: Advanced Features (Lower Priority)
1. Interactive maps for all data types
2. Drill-down capabilities
3. Advanced comparison tools
4. Export functionality (Excel, PowerPoint, PDF)

---

## Notes

- All dashboards should maintain consistent styling with NCRC brand colors
- Tables should be editable (as currently implemented) for user adjustments
- All calculations should be clearly documented in a "Methods" section
- Consider adding "Help" tooltips explaining each metric and visualization
- Ensure all data is properly sourced and cited

