# Methods for Housing Tables in Area Analysis

**Date:** 2025-01-27  
**Purpose:** Document the definitions, methods, and calculations used in Section 1 Tables 4-6 of the Area Analysis report.

---

## Overview

Section 1 of the Area Analysis report includes three new housing tables that provide detailed information about housing costs, owner occupancy, and housing unit characteristics. These tables use data from the U.S. Census Bureau's American Community Survey (ACS) 5-year estimates.

**Time Periods:**
- 2006-2010 ACS (5-year estimate ending in 2010)
- 2016-2020 ACS (5-year estimate ending in 2020)
- Most Recent ACS (typically 2019-2023, but will use the most recent available year)

**Data Source:**
- U.S. Census Bureau Census Data API
- Dataset: ACS 5-year estimates (`acs5`)
- Geography: County-level data aggregated across selected counties

---

## Table 4: Housing Costs and Burden

**Purpose:** Shows median housing costs, income, and the percentage of households experiencing housing cost burden.

### Metrics

1. **Median Household Income**
   - **Definition:** The median annual income of all households in the selected counties
   - **Census Variable:** `B19013_001E`
   - **Calculation:** Weighted median of county medians, weighted by number of households (total occupied units)
   - **Unit:** Dollars (annual)

2. **Median Home Value**
   - **Definition:** The median value of owner-occupied housing units
   - **Census Variable:** `B25077_001E`
   - **Calculation:** Weighted median of county medians, weighted by number of owner-occupied units
   - **Unit:** Dollars

3. **Median Owner Costs (Monthly)**
   - **Definition:** The median selected monthly owner costs (mortgage, taxes, insurance, utilities, etc.) for owner-occupied housing units
   - **Census Variable:** `B25088_001E`
   - **Calculation:** Weighted median of county medians, weighted by number of owner-occupied units
   - **Unit:** Dollars (monthly)

4. **Owner Cost Burden (%)**
   - **Definition:** The percentage of owner-occupied households spending 30% or more of their income on housing costs
   - **Census Variables:**
     - `B25091_001E`: Total owner-occupied households
     - `B25091_007E`: 30.0 to 34.9 percent of income
     - `B25091_008E`: 35.0 to 39.9 percent of income
     - `B25091_009E`: 40.0 to 49.9 percent of income
     - `B25091_010E`: 50.0 percent or more of income
   - **Calculation:**
     ```
     Owner Cost Burden (%) = (
         (B25091_007E + B25091_008E + B25091_009E + B25091_010E) / B25091_001E
     ) * 100
     ```
   - **Aggregation:** Weighted median of burden percentages across all selected counties, weighted by number of owner-occupied households
   - **Unit:** Percentage (0-100%)

5. **Median Rent (Monthly)**
   - **Definition:** The median gross rent (rent + utilities) for renter-occupied housing units
   - **Census Variable:** `B25064_001E`
   - **Calculation:** Weighted median of county medians, weighted by number of renter-occupied units
   - **Unit:** Dollars (monthly)

6. **Rental Burden (%)**
   - **Definition:** The percentage of renter-occupied households spending 30% or more of their income on rent
   - **Census Variables:**
     - `B25070_001E`: Total renter-occupied households
     - `B25070_007E`: 30.0 to 34.9 percent of income
     - `B25070_008E`: 35.0 to 39.9 percent of income
     - `B25070_009E`: 40.0 to 49.9 percent of income
     - `B25070_010E`: 50.0 percent or more of income
   - **Calculation:**
     ```
     Rental Burden (%) = (
         (B25070_007E + B25070_008E + B25070_009E + B25070_010E) / B25070_001E
     ) * 100
     ```
   - **Aggregation:** Weighted median of burden percentages across all selected counties, weighted by number of renter-occupied households
   - **Unit:** Percentage (0-100%)

### Change % Calculation

The "Change %" column shows the percentage change from the earliest time period (2006-2010 ACS) to the most recent time period:

```
Change % = ((Most Recent Value - Earliest Value) / Earliest Value) * 100
```

**Color Coding:**
- Green: Positive change for income/home value (favorable)
- Red: Positive change for costs/burdens (unfavorable)
- Black: No change or neutral

---

## Table 5: Owner Occupancy by Race and Ethnicity

**Purpose:** Shows the percentage of occupied housing units that are owner-occupied, overall and by race/ethnicity.

### Metrics

1. **Overall Owner Occupancy (%)**
   - **Definition:** The percentage of all occupied housing units that are owner-occupied
   - **Census Variables:**
     - `B25003_001E`: Total occupied housing units
     - `B25003_002E`: Owner-occupied housing units
   - **Calculation:**
     ```
     Overall Owner Occupancy (%) = (B25003_002E / B25003_001E) * 100
     ```
   - **Aggregation:** Sum of owner-occupied units / Sum of total occupied units across all selected counties
   - **Unit:** Percentage (0-100%)

2. **Owner Occupancy by Race/Ethnicity (%)**
   - **Definition:** The percentage of occupied housing units for each race/ethnicity group that are owner-occupied
   - **Census Variables (for each race/ethnicity):**
     - `B25003B_001E` through `B25003I_001E`: Total occupied units by race/ethnicity
     - `B25003B_002E` through `B25003I_002E`: Owner-occupied units by race/ethnicity
   - **Race/Ethnicity Groups:**
     - White (Non-Hispanic): `B25003H_001E` / `B25003H_002E`
     - Hispanic or Latino: `B25003I_001E` / `B25003I_002E`
     - Black or African American: `B25003B_001E` / `B25003B_002E`
     - Asian: `B25003D_001E` / `B25003D_002E`
     - Native American: `B25003C_001E` / `B25003C_002E`
     - Pacific Islander: `B25003E_001E` / `B25003E_002E`
     - Multi-Racial: `B25003G_001E` / `B25003G_002E`
   - **Calculation:**
     ```
     Owner Occupancy by Race (%) = (Owner-Occupied Units / Total Occupied Units) * 100
     ```
   - **Aggregation:** Sum of owner-occupied units by race / Sum of total occupied units by race across all selected counties
   - **Unit:** Percentage (0-100%)

### Filtering

Only race/ethnicity groups that represent **1% or more** of the total population in the selected counties are included in the table. This is determined using the most recent ACS demographic data.

### Change % Calculation

The "Change %" column shows the percentage point change (not percentage change) from the earliest time period to the most recent:

```
Change % = Most Recent Value - Earliest Value
```

**Color Coding:**
- Green: Positive change (increase in owner occupancy)
- Red: Negative change (decrease in owner occupancy)
- Black: No change

---

## Table 6: Housing Units by Structure Type

**Purpose:** Shows the distribution of housing units by structure type and occupancy status.

### Metrics

1. **Total Housing Units**
   - **Definition:** The total number of housing units (occupied and vacant) in the selected counties
   - **Census Variable:** `B25001_001E`
   - **Calculation:** Sum of total housing units across all selected counties
   - **Unit:** Count

2. **% 1-4 Units**
   - **Definition:** The percentage of total housing units that are 1-4 unit structures
   - **Census Variables:**
     - `B25024_002E`: 1-unit, detached
     - `B25024_003E`: 1-unit, attached
     - `B25024_004E`: 2 units
     - `B25024_005E`: 3-4 units
   - **Calculation:**
     ```
     1-4 Units = B25024_002E + B25024_003E + B25024_004E + B25024_005E
     % 1-4 Units = (1-4 Units / Total Housing Units) * 100
     ```
   - **Aggregation:** Sum of 1-4 units / Sum of total units across all selected counties
   - **Unit:** Percentage (0-100%)

3. **% Manufactured/Mobile**
   - **Definition:** The percentage of total housing units that are manufactured/mobile homes
   - **Census Variable:** `B25024_010E`
   - **Calculation:**
     ```
     % Manufactured/Mobile = (B25024_010E / Total Housing Units) * 100
     ```
   - **Aggregation:** Sum of mobile units / Sum of total units across all selected counties
   - **Unit:** Percentage (0-100%)
   - **Note:** This is a sub-category of 1-4 units (indented in the table)

4. **% 5+ Units**
   - **Definition:** The percentage of total housing units that are structures with 5 or more units
   - **Calculation:**
     ```
     5+ Units = Total Housing Units - 1-4 Units - Manufactured/Mobile Units
     % 5+ Units = (5+ Units / Total Housing Units) * 100
     ```
   - **Aggregation:** Calculated from aggregated totals across all selected counties
   - **Unit:** Percentage (0-100%)

5. **% of 1-4 Units Owner-Occupied**
   - **Definition:** The percentage of occupied 1-4 unit structures that are owner-occupied
   - **Census Variables (from B25032 - Occupied Units by Structure Type):**
     - `B25032_002E`: Owner-occupied 1-unit, detached
     - `B25032_003E`: Owner-occupied 1-unit, attached
     - `B25032_004E`: Owner-occupied 2 units
     - `B25032_005E`: Owner-occupied 3-4 units
     - `B25032_006E`: Occupied 1-unit, detached (total)
     - `B25032_007E`: Occupied 1-unit, attached (total)
     - `B25032_008E`: Occupied 2 units (total)
     - `B25032_009E`: Occupied 3-4 units (total)
   - **Calculation:**
     ```
     Owner-Occupied 1-4 Units = B25032_002E + B25032_003E + B25032_004E + B25032_005E
     Occupied 1-4 Units = B25032_006E + B25032_007E + B25032_008E + B25032_009E
     % of 1-4 Units Owner-Occupied = (Owner-Occupied 1-4 Units / Occupied 1-4 Units) * 100
     ```
   - **Aggregation:** Sum of owner-occupied 1-4 units / Sum of occupied 1-4 units across all selected counties
   - **Unit:** Percentage (0-100%)
   - **Note:** Uses occupied units (B25032) as denominator, not total units (B25024), to calculate the percentage of occupied units that are owner-occupied

### Change % Calculation

The "Change %" column shows the percentage change from the earliest time period to the most recent:

```
Change % = ((Most Recent Value - Earliest Value) / Earliest Value) * 100
```

**Color Coding:**
- Green: Positive change for owner-occupied percentage (favorable)
- Red: Negative change for owner-occupied percentage (unfavorable)
- Black: No change or neutral

---

## Data Aggregation Methods

### Multi-County Aggregation

When multiple counties are selected, data is aggregated as follows:

1. **Medians (Table 4):**
   - For median values (home value, owner costs, rent, household income), weighted medians are calculated
   - Each county's median is weighted by the number of relevant households/units:
     - Median Household Income: weighted by total occupied units (households)
     - Median Home Value: weighted by owner-occupied units
     - Median Owner Costs: weighted by owner-occupied units
     - Median Rent: weighted by renter-occupied units
     - Burden percentages: weighted by number of owners/renters
   - Example: If County A has 1M households with median income $50,000 and County B has 100K households with median income $100,000, the weighted median will be closer to $50,000 (reflecting County A's larger population)

2. **Percentages (Tables 4, 5, 6):**
   - For percentages (burden, owner occupancy, unit distribution), values are calculated from aggregated totals
   - Example: Owner occupancy = (Sum of owner-occupied units across all counties) / (Sum of total occupied units across all counties) * 100

3. **Counts (Table 6):**
   - For counts (total units), values are summed across all counties

### Missing Data Handling

- If a Census variable is missing or returns 0 for a county, that county is excluded from the calculation for that specific metric
- If all counties are missing data for a metric, the value is set to 0 or N/A
- The burden calculations require all component variables to be present; if any are missing, the burden percentage is not calculated for that county

---

## API Implementation Details

### Data Fetching

- **Function:** `fetch_acs_housing_data()` in `apps/dataexplorer/area_report_builder.py`
- **API Endpoint:** `https://api.census.gov/data/{year}/acs/acs5`
- **Authentication:** Requires `CENSUS_API_KEY` environment variable
- **Rate Limiting:** API calls are made sequentially with timeout handling

### Variable Groups

To avoid API failures, variables are fetched in separate API calls:

1. **Main Housing Variables:** Basic housing characteristics (value, costs, rent, income, units, owner occupancy)
2. **Rent Burden Variables:** B25070 table (rent burden categories)
3. **Owner Burden Variables:** B25091 table (owner cost burden categories)
4. **Occupied Units by Structure:** B25032 table (for owner-occupied 1-4 units calculation)

### Error Handling

- If a specific ACS year is unavailable, the system attempts to fetch the next most recent year
- If B25032 variables are unavailable (e.g., for older ACS years), the system falls back to using B25024 totals as an approximation
- API errors are logged but do not prevent the report from generating (missing data is shown as 0 or N/A)

---

## Code Locations

### Data Fetching
- **Function:** `fetch_acs_housing_data()` in `apps/dataexplorer/area_report_builder.py` (lines ~370-709)

### Table Creation
- **Table 4:** `create_housing_costs_table()` in `apps/dataexplorer/area_report_builder.py` (lines ~712-798)
- **Table 5:** `create_owner_occupancy_table()` in `apps/dataexplorer/area_report_builder.py` (lines ~801-919)
- **Table 6:** `create_housing_units_table()` in `apps/dataexplorer/area_report_builder.py` (lines ~922-1024)

### Report Integration
- **Function:** `build_area_report()` in `apps/dataexplorer/area_report_builder.py` (lines ~1027+)
- **Template:** `apps/dataexplorer/templates/area_report_template.html`
  - `renderHousingCostsTable()` - Table 4 rendering
  - `renderOwnerOccupancyTable()` - Table 5 rendering
  - `renderHousingUnitsTable()` - Table 6 rendering

---

## Notes

1. **Burden Threshold:** The standard definition of housing cost burden is spending 30% or more of income on housing costs. This is consistent with HUD and Census Bureau definitions.

2. **Race/Ethnicity Categories:** The Census Bureau uses mutually exclusive categories (e.g., "White alone, not Hispanic" and "Hispanic or Latino" are separate). The "Hispanic or Latino" category can include people of any race.

3. **Structure Type Definitions:**
   - 1-unit, detached: Single-family homes not attached to other structures
   - 1-unit, attached: Single-family homes attached to other structures (townhouses, row houses)
   - 2 units: Duplexes
   - 3-4 units: Small multi-family structures
   - 5+ units: Large apartment buildings
   - Manufactured/Mobile: Factory-built homes, including mobile homes and manufactured homes

4. **Occupied vs. Total Units:** Table 6 uses both B25024 (total units) and B25032 (occupied units) to correctly calculate owner-occupancy rates. The percentage of 1-4 units that are owner-occupied uses occupied units as the denominator, not total units.

5. **Time Period Labels:** The table headers dynamically show the actual ACS years (e.g., "2019-2023 ACS") based on the data that was successfully fetched.

