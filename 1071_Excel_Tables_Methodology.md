# 1071 Analysis Excel Tables - Detailed Methodology

## Overview

This document provides a comprehensive summary of the methods, calculations, and data sources used to create the 6 Excel tables for 1071 small business lending analysis.

**Output File:** `1071_Analysis_Tables_YYYYMMDD_HHMMSS.xlsx`  
**Date Created:** November 25, 2025  
**Data Years:** 2018-2024  
**Source Table:** `hdma1-242116.misc.1071_1k_lenders`

---

## Data Source: 1071_1k_lenders Table

### Table Creation

The source table `1071_1k_lenders` was created using a comprehensive SQL query that:

1. **Includes all lenders** from the disclosure table (not just qualified lenders)
2. **Marks credit card lenders** based on average loan amount thresholds
3. **Identifies qualified lenders** (those with ≥1,000 loans in consecutive years)
4. **Includes 2017 data** for qualification checks (to determine 2018 status)
5. **Outputs only 2018-2024** in the final table

### Key Fields in Source Table

- **All original disclosure table fields** (`d.*`)
- **`lender_name`**: Lender name from `sb.lenders` table
- **`county_name`**, **`state_name`**: Geographic information from `geo.cbsa_to_county`
- **`is_credit_card_lender`**: Boolean flag (1 = credit card lender, 0 = not)
- **`lender_type`**: Text field ('Credit Card Lender' or 'Not Credit Card Lender')
- **`qualification_status`**: 'Qualifies', 'Does Not Qualify', or 'N/A (Credit Card)'

### Credit Card Lender Identification

**Rule:** A lender is classified as a credit card lender if their **average loan amount per year** is less than $10,000.

**Calculation:**
```sql
avg_loan_amount_thousands = 
  SUM(amt_under_100k + amt_100k_250k + amt_250k_1m) / 
  SUM(num_under_100k + num_100k_250k + num_250k_1m)
```

**Note:** Amounts in the disclosure table are stored in thousands (000s), so $10,000 = 10 in the data.

**Logic:**
- If `avg_loan_amount_thousands < 10` OR `avg_loan_amount_thousands IS NULL` → Credit Card Lender
- Otherwise → Not Credit Card Lender

### Qualified Lender Identification

**Rule:** A lender qualifies if they made **≥1,000 loans in a given year AND the previous year**.

**Calculation:**
1. Calculate total loans per lender per year: `num_under_100k + num_100k_250k + num_250k_1m`
2. For each year, check if lender had ≥1,000 loans in that year AND the previous year
3. Mark as 'Qualifies' if both conditions are met (and lender is not a credit card lender)

**Note:** 2017 data is included in calculations to determine 2018 qualification status, but 2017 is not included in the output.

---

## Table 1: Bank Size Analysis (All Lending)

### Purpose
Count banks by loan volume threshold for all lending (card and non-card).

### Columns

1. **Year**: Reporting year (2018-2024)
2. **# Large Banks <1 K loans**: Count of banks that made fewer than 1,000 loans in that year
3. **# All large banks**: Total count of all unique banks/lenders in that year
4. **# loans of banks < 1k**: Total number of loans from banks that made fewer than 1,000 loans
5. **# all large bank loans**: Total number of loans made by all banks in that year

### Calculations

**Step 1: Calculate total loans per lender per year**
```sql
total_loans = SUM(num_under_100k + num_100k_250k + num_250k_1m)
GROUP BY year, respondent_id
```

**Step 2: Aggregate by year**
- **All large banks**: `COUNT(DISTINCT respondent_id)` - All unique lenders
- **Banks <1K loans**: `COUNT(DISTINCT CASE WHEN total_loans < 1000 THEN respondent_id END)`
- **Loans from banks <1K**: `SUM(CASE WHEN total_loans < 1000 THEN total_loans ELSE 0 END)`
- **All large bank loans**: `SUM(total_loans)`

### Data Source
- **Table**: `1071_1k_lenders`
- **Filter**: None (includes all lending, card and non-card)
- **Grouping**: By year and respondent_id

---

## Table 2: Business Revenue Analysis (All Lending)

### Purpose
Count loans by business revenue size for all lending (card and non-card).

### Columns

1. **Year**: Reporting year (2018-2024)
2. **# loans to biz <$1 mill rev**: Number of loans to businesses with less than $1 million in revenue
3. **# loans to biz >$1 mil.**: Number of loans to businesses with more than $1 million in revenue

### Calculations

**Direct field usage:**
- **Loans to businesses <$1M**: `SUM(numsbrev_under_1m)`
  - This field directly counts loans to businesses with revenue under $1 million

**Calculated field:**
- **Loans to businesses >$1M**: 
  ```sql
  SUM(num_under_100k + num_100k_250k + num_250k_1m - numsbrev_under_1m)
  ```
  - Total loans minus loans to businesses <$1M

### Data Source
- **Table**: `1071_1k_lenders`
- **Fields Used**: 
  - `numsbrev_under_1m` (direct count of loans to businesses <$1M revenue)
  - `num_under_100k`, `num_100k_250k`, `num_250k_1m` (for total loan calculation)
- **Filter**: None (includes all lending, card and non-card)

---

## Table 3: Combined Bank Size + Business Revenue (All Lending)

### Purpose
Count loans from large banks (>1K loans) by business revenue category for all lending.

### Columns

1. **Year**: Reporting year (2018-2024)
2. **#loans banks > 1 K to biz <1 mil**: Loans from banks with >1,000 loans to businesses <$1M revenue
3. **# loans banks > 1 K to biz >1 mil**: Loans from banks with >1,000 loans to businesses >$1M revenue

### Calculations

**Step 1: Identify banks with >1,000 loans**
```sql
WITH lender_loans_by_year AS (
  SELECT year, respondent_id,
    SUM(num_under_100k + num_100k_250k + num_250k_1m) AS total_loans
  FROM 1071_1k_lenders
  GROUP BY year, respondent_id
)
SELECT DISTINCT year, respondent_id
FROM lender_loans_by_year
WHERE total_loans >= 1000
```

**Step 2: Filter to only banks >1K loans and aggregate by business revenue**
- **Loans to businesses <$1M**: `SUM(numsbrev_under_1m)` for banks with >1K loans
- **Loans to businesses >$1M**: `SUM(num_under_100k + num_100k_250k + num_250k_1m - numsbrev_under_1m)` for banks with >1K loans

### Data Source
- **Table**: `1071_1k_lenders`
- **Filter**: Only lenders with ≥1,000 total loans in that year
- **Grouping**: By year

---

## Table 4: Bank Size Analysis (Non-Credit Card Lending Only)

### Purpose
Same as Table 1, but filtered to non-credit card lending only.

### Columns
Same as Table 1:
1. **Year**
2. **# Large Banks <1 K loans**
3. **# All large banks**
4. **# loans of banks < 1k**
5. **# all large bank loans**

### Calculations
Same as Table 1, with additional filter:

**Filter Applied:**
```sql
WHERE is_credit_card_lender = 0
```

This excludes all lenders classified as credit card lenders (those with average loan amount < $10,000 per year).

### Data Source
- **Table**: `1071_1k_lenders`
- **Filter**: `is_credit_card_lender = 0` (non-credit card lenders only)

---

## Table 5: Business Revenue Analysis (Non-Credit Card Lending Only)

### Purpose
Same as Table 2, but filtered to non-credit card lending only.

### Columns
Same as Table 2:
1. **Year**
2. **# loans to biz <$1 mill rev**
3. **# loans to biz >$1 mil.**

### Calculations
Same as Table 2, with additional filter:

**Filter Applied:**
```sql
WHERE is_credit_card_lender = 0
```

### Data Source
- **Table**: `1071_1k_lenders`
- **Filter**: `is_credit_card_lender = 0` (non-credit card lenders only)

---

## Table 6: Combined Bank Size + Business Revenue (Non-Credit Card Lending Only)

### Purpose
Same as Table 3, but filtered to non-credit card lending only.

### Columns
Same as Table 3:
1. **Year**
2. **#loans banks > 1 K to biz <1 mil**
3. **# loans banks > 1 K to biz >1 mil**

### Calculations
Same as Table 3, with additional filter:

**Filter Applied:**
```sql
WHERE is_credit_card_lender = 0
```

This ensures:
1. Only non-credit card lenders are included
2. Only banks with >1,000 loans are counted
3. Loans are categorized by business revenue

### Data Source
- **Table**: `1071_1k_lenders`
- **Filter**: `is_credit_card_lender = 0` AND lender has ≥1,000 loans in that year

---

## Key Business Rules

### 1. "Large Banks" Definition
**Rule:** All banks in the disclosure table are considered "large banks" for this analysis.

**Implementation:** No additional filtering by bank size or assets - all `respondent_id` values are included.

### 2. Loan Counting
**Rule:** Total loans = sum of loans across all size categories.

**Calculation:**
```sql
total_loans = num_under_100k + num_100k_250k + num_250k_1m
```

**Note:** This counts the number of loans, not the number of records. Each record in the disclosure table represents a lender-county-year combination, and the `num_*` fields contain the loan counts for that combination.

### 3. Business Revenue Classification
**Rule:** Loans are classified by the revenue of the business receiving the loan.

**Data Source:**
- **Loans to businesses <$1M**: Directly from `numsbrev_under_1m` field
- **Loans to businesses >$1M**: Calculated as total loans minus loans <$1M

**Note:** The disclosure table includes `numsbrev_under_1m` which directly counts loans to businesses with revenue under $1 million. Loans to businesses over $1 million are calculated by subtracting this from the total.

### 4. Credit Card Lender Exclusion
**Rule:** Credit card lenders are identified by average loan amount < $10,000 per year.

**Threshold:** $10,000 (stored as 10 in thousands)

**Application:** 
- Tables 1-3: Include all lenders (card and non-card)
- Tables 4-6: Exclude credit card lenders (`is_credit_card_lender = 0`)

### 5. Bank Size Threshold
**Rule:** Banks with ≥1,000 loans in a year are considered "large volume" banks.

**Application:** Used in Tables 3 and 6 to filter to only banks with >1,000 loans before categorizing by business revenue.

---

## Data Quality Notes

### Year Coverage
- **Output Years:** 2018-2024 (7 years)
- **Calculation Years:** 2017-2024 (2017 used for qualification checks only)

### Loan Count Aggregation
- Loan counts are aggregated at the lender-year level
- Each row in the source table represents a lender-county-year combination
- Loan counts (`num_*` fields) are summed across all counties for each lender-year

### Missing Data Handling
- **NULL values**: Treated as 0 using `COALESCE()` function
- **Missing lender names**: Left as NULL (LEFT JOIN with lenders table)
- **Missing geographic data**: Left as NULL (LEFT JOIN with geo table)

---

## Technical Implementation

### SQL Query Structure

Each table uses a similar structure:

1. **CTE (Common Table Expression)** for intermediate calculations
2. **Aggregation** by year (and lender_id where needed)
3. **Filtering** based on table requirements
4. **Final SELECT** with proper column naming

### Excel Export

**Method:**
- Python script using `pandas` and `openpyxl`
- Each table exported as a separate worksheet
- Column names preserved from SQL queries (renamed after query execution to handle special characters)

**File Format:**
- Excel (.xlsx) format
- Multiple worksheets (one per table)
- Column headers match requirements exactly

---

## Summary Statistics

### Source Table
- **Total Records:** 37,691,700 rows
- **Unique Lenders:** 915
- **Credit Card Lenders:** 9
- **Non-Credit Card Lenders:** 912
- **Qualified Lenders:** 415 (non-card, 1000+ loans in consecutive years)

### Output Tables
- **Number of Tables:** 6
- **Years Covered:** 2018-2024 (7 years per table)
- **Total Worksheets:** 6
- **File Size:** ~9 KB

---

## Validation

### Data Consistency Checks

1. **Year Coverage:** All tables have exactly 7 rows (2018-2024)
2. **Loan Counts:** Table 1 "all large bank loans" should match sum of Table 2 columns
3. **Filtering:** Tables 4-6 should have lower counts than Tables 1-3 (credit card exclusion)
4. **Bank Threshold:** Tables 3 and 6 should have lower loan counts than Tables 1-2 and 4-5 (only banks >1K loans)

### Expected Relationships

- **Table 1 "all large bank loans"** = **Table 2 "loans <$1M" + "loans >$1M"**
- **Table 4 "all large bank loans"** = **Table 5 "loans <$1M" + "loans >$1M"**
- **Table 3 loan counts** ≤ **Table 1 "all large bank loans"** (subset: only banks >1K)
- **Table 6 loan counts** ≤ **Table 4 "all large bank loans"** (subset: only banks >1K)

---

## Files and Scripts

### Source Files
1. **`1071_table_sql.txt`**: SQL query to create the source table
2. **`generate_1071_excel_tables.py`**: Python script to generate Excel file
3. **`apps/bizsight/utils/bigquery_client.py`**: BigQuery client wrapper

### Output Files
1. **`1071_Analysis_Tables_YYYYMMDD_HHMMSS.xlsx`**: Final Excel file with 6 tables
2. **`1071_Excel_Tables_Methodology.md`**: This documentation file

---

## References

### BigQuery Tables Used
- **`hdma1-242116.sb.disclosure`**: Main small business lending disclosure data
- **`hdma1-242116.sb.lenders`**: Lender name lookup table
- **`hdma1-242116.geo.cbsa_to_county`**: Geographic information (county, state)
- **`hdma1-242116.misc.1071_1k_lenders`**: Created source table with credit card flags

### Key Fields from Disclosure Table
- **`respondent_id`**: Unique lender identifier
- **`year`**: Reporting year
- **`num_under_100k`**, **`num_100k_250k`**, **`num_250k_1m`**: Loan counts by size category
- **`amt_under_100k`**, **`amt_100k_250k`**, **`amt_250k_1m`**: Loan amounts by size category
- **`numsbrev_under_1m`**: Number of loans to businesses with revenue < $1M

---

**Document Version:** 1.0  
**Last Updated:** November 25, 2025  
**Author:** Cursor AI Agent

