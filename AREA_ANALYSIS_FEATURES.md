# Area Analysis Dashboard - Features from LendSight

## Overview
This document lists features from LendSight that can be added to the Area Analysis dashboard. The Area Analysis should be a data-focused dashboard (no AI narratives or introductions) that presents all data in interactive tables with user-editable capabilities.

---

## 1. Summary/Metrics Tables

### 1.1 Mortgage Summary Table (Yearly Breakdown)
**What it shows:**
- Total originations by year
- Total loan amounts by year
- Average loan amount by year
- Year-over-year change percentages

**Implementation Recommendation:**
- **Table Type:** Aggregated summary table
- **Layout:** Horizontal table with years as columns
- **Editable:** Allow users to edit calculated values (e.g., change totals, adjust percentages)
- **Visual Design:** 
  - Use card-based layout similar to filter cards
  - Highlight key metrics (latest year, largest change)
  - Add sparkline charts for trend visualization
- **Best Practice:** Include a "Reset to Calculated" button to restore original values

### 1.2 County Summary Table (Multi-County Analysis)
**What it shows:**
- When multiple counties selected, show breakdown by county
- Total loans, loan amounts per county
- Percentage of total for each county

**Implementation Recommendation:**
- **Table Type:** Expandable/collapsible sections
- **Layout:** Vertical table with counties as rows
- **Conditional Display:** Only show when 2+ counties selected
- **Best Practice:** Add county comparison toggle (side-by-side vs. stacked)

---

## 2. Demographic Analysis Tables

### 2.1 Demographic Overview Table (Race/Ethnicity)
**What it shows:**
- Loans by race/ethnicity group (Hispanic, Black, White, Asian, Native American, etc.)
- Number and percentage for each group by year
- Change over time (first year vs. last year)
- Population share comparison (if Census data available)

**Implementation Recommendation:**
- **Table Structure:**
  - Left column: Demographic group
  - Middle columns: One per year showing "Number (Percent%)"
  - Right column: Change column (absolute and percentage change)
  - Optional: Population Share % column (if Census data integrated)
- **Filtering:** 
  - Only show groups with ≥1% of loans (configurable threshold)
  - Add "Show All Groups" toggle
- **Editable:** 
  - Allow editing of numbers (percentages auto-recalculate)
  - Allow editing of percentages (numbers auto-recalculate)
- **Visual Design:**
  - Color-code demographic groups for quick identification
  - Add bar charts next to each row showing distribution
  - Highlight groups with significant changes (>10% increase/decrease)

### 2.2 Income & Neighborhood Indicators Table
**What it shows:**
- LMI Borrower (Low-to-Moderate Income Borrower) loans
- LMICT (Low-to-Moderate Income Census Tract) loans
- MMCT (Majority-Minority Census Tract) loans
- Number and percentage for each category by year
- Change over time

**Implementation Recommendation:**
- **Table Structure:**
  - Left column: Indicator type (LMI Borrower, LMICT, MMCT)
  - Middle columns: One per year showing "Number (Percent%)"
  - Right column: Change column
- **Grouping:** 
  - Group related indicators together
  - Add expandable details showing methodology
- **Editable:** Same as demographic table
- **Visual Design:**
  - Use icons to represent each indicator type
  - Add tooltips explaining each metric
  - Color-code based on percentage thresholds (e.g., <30% = red, 30-50% = yellow, >50% = green)

---

## 3. Lender Analysis Tables

### 3.1 Top Lenders Detailed Table
**What it shows:**
- Top 10 lenders (or all if <10) by total loans in most recent year
- Lender name, type, total loans, total loan amount
- Breakdown by demographic groups for each lender
- "No Data" category for loans without demographic information

**Implementation Recommendation:**
- **Table Structure:**
  - Left columns: Lender info (Name, Type, Total Loans, Total Amount)
  - Middle columns: Demographic breakdown (Hispanic, Black, White, Asian, Native American, No Data)
  - Each demographic cell shows: Number (Percent%)
- **Sorting:** 
  - Default: Sort by total loans (descending)
  - Allow sorting by any column
  - Add "Sort by [Demographic Group]" quick filters
- **Filtering:**
  - Filter by lender type
  - Search by lender name
  - Show/hide lenders below threshold
- **Editable:**
  - Allow editing of loan counts
  - Percentages auto-recalculate
  - Allow adding/removing lenders (with validation)
- **Visual Design:**
  - Use expandable rows for detailed breakdown
  - Add pie charts showing demographic distribution per lender
  - Highlight lenders with significant disparities

### 3.2 Lender Summary Table (All Lenders)
**What it shows:**
- All lenders (not just top 10)
- Aggregated metrics: total loans, loan amounts
- Lender type breakdown

**Implementation Recommendation:**
- **Table Type:** Full data table with pagination
- **Features:**
  - Pagination (50-100 rows per page)
  - Search/filter functionality
  - Export to CSV/Excel
  - Column visibility toggle
- **Editable:** Same as top lenders table

---

## 4. Market Concentration Analysis

### 4.1 HHI (Herfindahl-Hirschman Index) Display
**What it shows:**
- HHI value for loan amounts in latest year
- Concentration level (Unconcentrated, Moderately Concentrated, Highly Concentrated)
- Top lenders by market share

**Implementation Recommendation:**
- **Display Format:** 
  - Card-based metric display (not a table)
  - Large HHI number with color-coded concentration level
  - List of top 5 lenders with market share percentages
- **Visual Design:**
  - Progress bar showing concentration level
  - Pie chart of top lenders' market share
  - Historical HHI trend (if multiple years selected)
- **Editable:** Allow manual adjustment of HHI calculation parameters

---

## 5. Trend Analysis Tables

### 5.1 Year-over-Year Trends Table
**What it shows:**
- Changes between consecutive years
- Percentage changes for key metrics
- Highlight significant trends

**Implementation Recommendation:**
- **Table Structure:**
  - Left column: Metric name
  - Middle columns: Year-over-year change (e.g., "2023→2024: +5.2%")
  - Right column: Overall trend (up/down arrow with color)
- **Features:**
  - Highlight largest increases/decreases
  - Add trend indicators (↑, ↓, →)
  - Filter by metric type
- **Editable:** Allow editing of trend calculations

---

## 6. Census Data Integration (Optional Enhancement)

### 6.1 Population Demographics Table
**What it shows:**
- Total population by year (2010 Census, 2020 Census, 2024 ACS)
- Racial/ethnic composition over time
- Population share percentages

**Implementation Recommendation:**
- **Table Structure:**
  - Left column: Demographic group
  - Middle columns: Population counts by year
  - Right columns: Population share % by year
- **Integration:**
  - Fetch from Census API (similar to LendSight)
  - Cache results to avoid repeated API calls
  - Show loading state while fetching
- **Editable:** Allow manual entry of population data
- **Best Practice:** Add note explaining data sources and years

---

## 7. Implementation Best Practices

### 7.1 Table Design Principles
1. **Consistent Structure:**
   - All tables should follow similar layout patterns
   - Use consistent column headers and formatting
   - Maintain consistent color scheme (NCRC brand colors)

2. **User Experience:**
   - **Loading States:** Show skeleton loaders while data loads
   - **Empty States:** Clear messages when no data available
   - **Error Handling:** User-friendly error messages with retry options
   - **Responsive Design:** Tables should work on mobile (horizontal scroll or card view)

3. **Editability:**
   - **Visual Indicators:** 
     - Highlight edited cells (e.g., yellow background)
     - Add "edited" badge to modified tables
   - **Validation:**
     - Prevent invalid edits (negative numbers, percentages >100%)
     - Show validation errors inline
   - **Undo/Redo:**
     - Add undo/redo buttons per table
     - Track edit history
   - **Save State:**
     - Auto-save edits to browser localStorage
     - "Reset All" button to restore original data

4. **Data Presentation:**
   - **Number Formatting:**
     - Integers: `#,##0` (e.g., 1,234)
     - Percentages: `#,##0.00%` (e.g., 12.34%)
     - Currency: `$#,##0` (e.g., $1,234,567)
   - **Sorting:**
     - All numeric columns should be sortable
     - Maintain sort state across table updates
   - **Filtering:**
     - Add filter rows below headers
     - Clear filters button
     - Show active filter count

5. **Performance:**
   - **Virtual Scrolling:** For large tables (>100 rows)
   - **Lazy Loading:** Load data as user scrolls
   - **Debouncing:** Debounce edit inputs to reduce recalculation
   - **Memoization:** Cache calculated values

### 7.2 Technical Architecture Recommendations

1. **Frontend State Management:**
   ```javascript
   // Recommended structure
   const AreaAnalysisState = {
     originalData: {},      // Original data from API
     editedData: {},        // User-edited data
     editHistory: [],       // Undo/redo history
     activeFilters: {},     // Current filter state
     tableConfig: {}        // Table display preferences
   };
   ```

2. **Table Component Structure:**
   - Create reusable `EditableTable` component
   - Props: `data`, `columns`, `editable`, `onEdit`, `onReset`
   - Support for sorting, filtering, pagination

3. **Data Flow:**
   ```
   API Call → Store Original Data → Render Tables → User Edits → 
   Update Edited Data → Recalculate Dependencies → Re-render
   ```

4. **API Endpoints Needed:**
   - `/api/area/hmda/summary` - Summary metrics
   - `/api/area/hmda/demographics` - Demographic breakdown
   - `/api/area/hmda/income-neighborhood` - LMI/MMCT data
   - `/api/area/hmda/lenders` - Lender analysis
   - `/api/area/hmda/hhi` - Market concentration
   - `/api/area/hmda/trends` - Trend analysis

### 7.3 UI/UX Recommendations

1. **Table Layout:**
   - Use sticky headers for long tables
   - Add row hover effects
   - Highlight selected rows
   - Add row numbers for reference

2. **Editing Interface:**
   - Click to edit (inline editing)
   - Show edit icon on hover
   - Save on blur or Enter key
   - Cancel on Escape key

3. **Visual Enhancements:**
   - Add mini charts (sparklines) for trends
   - Color-code cells based on values (heatmap)
   - Add icons for quick actions (edit, delete, duplicate)

4. **Accessibility:**
   - Keyboard navigation (Tab, Arrow keys)
   - Screen reader support
   - ARIA labels for all interactive elements
   - High contrast mode support

---

## 8. Priority Implementation Order

### Phase 1 (Core Tables - Essential):
1. **Summary Table** - Basic yearly metrics
2. **Demographic Overview Table** - Race/ethnicity breakdown
3. **Top Lenders Table** - Top 10 lenders with demographics

### Phase 2 (Enhanced Analysis):
4. **Income & Neighborhood Indicators** - LMI/MMCT analysis
5. **HHI Display** - Market concentration
6. **Trend Analysis Table** - Year-over-year changes

### Phase 3 (Advanced Features):
7. **County Summary** - Multi-county breakdown
8. **Lender Summary (All)** - Complete lender list
9. **Population Demographics** - Census integration

### Phase 4 (Polish & Optimization):
10. **Edit History & Undo/Redo**
11. **Advanced Filtering & Search**
12. **Export Functionality** (Excel, PowerPoint)

---

## 9. Key Differences from LendSight

1. **No AI Narratives:** Pure data presentation, no text summaries
2. **No Introduction:** Start directly with data tables
3. **User Editable:** All tables allow manual data editing
4. **Interactive:** More interactive features (sorting, filtering, editing)
5. **Real-time Updates:** Changes reflect immediately across dependent tables
6. **Export Focus:** Emphasis on export capabilities for further analysis

---

## 10. Example Table Structure

### Demographic Overview Table Example:
```
| Demographic Group | 2018        | 2019        | 2020        | ... | Change (2018→2024) |
|-------------------|-------------|-------------|-------------|-----|---------------------|
| Hispanic          | 1,234 (12%) | 1,456 (14%) | 1,678 (16%) | ... | +444 (+4%)          |
| Black             | 2,345 (23%) | 2,234 (22%) | 2,123 (21%) | ... | -222 (-2%)          |
| White             | 5,678 (56%) | 5,789 (57%) | 5,890 (58%) | ... | +212 (+2%)          |
| ...               | ...         | ...         | ...         | ... | ...                 |
```

Each cell is editable, and percentages auto-recalculate when numbers change.

---

This document provides a comprehensive roadmap for implementing LendSight-like features in the Area Analysis dashboard while maintaining a data-focused, user-editable approach.

