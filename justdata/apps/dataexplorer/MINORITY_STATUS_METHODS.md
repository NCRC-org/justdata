# Methods for Determining Minority Status in DataExplorer

**Date:** 2025-01-27  
**Purpose:** Document the methods used to calculate and categorize minority population percentages for census tracts in area analysis and lender analysis.

---

## Base Calculation Method

**Both area analysis and lender analysis use the same base calculation:**

### Minority Population Percentage Formula

```sql
tract_minority_population_percent = (
    (total_persons - total_white) / total_persons
) * 100
```

**Where:**
- `total_persons` = Total population in the census tract
- `total_white` = Non-Hispanic White population in the census tract
- `minority_population` = `total_persons - total_white` (all persons who are not non-Hispanic White)

**Data Source:**
- U.S. Census Bureau data (ACS 5-year estimates or Decennial Census)
- Stored in BigQuery `geo.census` table
- Fields: `total_persons`, `total_white` (non-Hispanic White)

**SQL Implementation:**
```sql
SAFE_DIVIDE(
    COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
    NULLIF(COALESCE(c.total_persons, 0), 0)
) * 100 as tract_minority_population_percent
```

---

## Categorization Methods

### Area Analysis: Dynamic Quartiles

**Method:** Quartiles calculated from the distribution of minority percentages across all census tracts in the analysis area (single CBSA).

**Why Dynamic:**
- Area analysis is limited to a single CBSA
- Quartiles provide meaningful relative comparison within that geography
- Categories adapt to the actual distribution of minority populations in that area

**Process:**
1. Get all unique census tracts in the analysis area
2. Calculate quartile thresholds (25th, 50th, 75th percentiles) from the distribution
3. Classify each tract into a quartile:
   - **Low Minority**: 0-25th percentile
   - **Moderate Minority**: 25th-50th percentile
   - **Middle Minority**: 50th-75th percentile
   - **High Minority**: 75th-100th percentile

**Implementation:**
- Function: `calculate_minority_quartiles(df)` in `apps/lendsight/mortgage_report_builder.py`
- Function: `classify_tract_minority_quartile(minority_pct, quartiles)` in `apps/lendsight/mortgage_report_builder.py`
- Used in: `apps/dataexplorer/area_report_builder.py`

**Example:**
If a CBSA has tracts with minority percentages ranging from 5% to 95%, the quartiles might be:
- Q25 = 15% (Low Minority: <15%)
- Q50 = 35% (Moderate Minority: 15-35%)
- Q75 = 60% (Middle Minority: 35-60%, High Minority: ≥60%)

---

### Lender Analysis: Fixed Percentage Thresholds

**Method:** Fixed percentage thresholds applied consistently across all geographies.

**Why Fixed:**
- Lender analysis may span dozens of CBSAs
- Fixed thresholds ensure consistent categorization across different geographic contexts
- Allows meaningful comparison of lender performance across different markets

**Fixed Thresholds:**
- **High Minority**: ≥80%
- **Middle Minority**: 50%-<80%
- **Moderate Minority**: 20%-<50%
- **Low Minority**: <20%

**Implementation:**
- Used in: `apps/dataexplorer/lender_report_builder.py`
- Function: `create_lender_neighborhood_demographics_comparison_table()`
- Direct filtering by percentage ranges (no quartile calculation)

**Example:**
A tract with 85% minority population is always "High Minority" regardless of the analysis area, while a tract with 15% is always "Low Minority".

---

## Majority Minority Census Tracts (MMCT)

**Both methods use the same definition for MMCT:**

- **MMCT**: Census tracts where `tract_minority_population_percent ≥ 50%`
- This is a fixed threshold (not quartile-based) in both analyses
- Used as an aggregate category separate from the quartile/fixed breakdowns

---

## Summary Table

| Aspect | Area Analysis | Lender Analysis |
|--------|---------------|-----------------|
| **Base Calculation** | Same: `(total_persons - total_white) / total_persons * 100` | Same: `(total_persons - total_white) / total_persons * 100` |
| **Categorization Method** | Dynamic Quartiles | Fixed Thresholds |
| **High Minority** | 75th-100th percentile (varies by area) | ≥80% (fixed) |
| **Middle Minority** | 50th-75th percentile (varies by area) | 50%-<80% (fixed) |
| **Moderate Minority** | 25th-50th percentile (varies by area) | 20%-<50% (fixed) |
| **Low Minority** | 0-25th percentile (varies by area) | <20% (fixed) |
| **MMCT** | ≥50% (fixed) | ≥50% (fixed) |
| **Rationale** | Single CBSA - quartiles provide relative comparison | Multiple CBSAs - fixed thresholds ensure consistency |

---

## Code Locations

### Base Calculation
- **SQL Generation**: `shared/data_processing/census_tract_utils.py` → `get_minority_percentage()`
- **BigQuery Table**: `geo.census` table with `total_persons` and `total_white` fields

### Area Analysis (Quartiles)
- **Quartile Calculation**: `apps/lendsight/mortgage_report_builder.py` → `calculate_minority_quartiles()`
- **Quartile Classification**: `apps/lendsight/mortgage_report_builder.py` → `classify_tract_minority_quartile()`
- **Usage**: `apps/dataexplorer/area_report_builder.py` → `build_area_report()`

### Lender Analysis (Fixed Thresholds)
- **Implementation**: `apps/dataexplorer/lender_report_builder.py` → `create_lender_neighborhood_demographics_comparison_table()`
- **Direct filtering**: Uses fixed percentage ranges (≥80%, 50-80%, 20-50%, <20%)

---

## Notes

1. **MMCT is always fixed at ≥50%** in both analyses
2. **Area analysis quartiles** are calculated from the actual distribution in the analysis area
3. **Lender analysis fixed thresholds** ensure consistent categorization when comparing lenders across multiple CBSAs
4. **Minority population** is defined as all persons who are not non-Hispanic White (includes Hispanic, Black, Asian, Native American, Pacific Islander, Multi-racial, etc.)

