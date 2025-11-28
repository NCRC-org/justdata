# How to View Queries in BigQuery

## Method 1: View Query History in BigQuery Console

1. Go to [BigQuery Console](https://console.cloud.google.com/bigquery)
2. In the left sidebar, click on **"Query history"** (or go to "Job history")
3. You'll see all recent queries executed, including:
   - Queries from your Flask app
   - Queries from Tableau
   - Any manual queries you've run

4. Click on any query to see:
   - The full SQL query text
   - Execution time
   - Bytes processed
   - Results (if still cached)

## Method 2: View Tableau Queries

1. In BigQuery Console, go to **"Query history"**
2. Filter by:
   - **User**: Look for queries from your Tableau service account
   - **Time range**: Select the time when you ran the Tableau query
3. Tableau queries will typically have:
   - A comment or identifier in the query
   - Multiple CTEs (Common Table Expressions)
   - Complex aggregations

## Method 3: Check the Query Log File

The Flask app now saves the full query to a file:
- **Location**: `dataexplorer_query_log.sql` in the repo root
- This file is overwritten each time you run an analysis
- You can copy this query and run it directly in BigQuery Console

**OR** view it via API:
- After running an analysis, visit: `http://localhost:5000/api/debug/query`
- This will show you the exact query that was generated

## Method 4: Run a Simple Test Query

To verify the data directly, run this query in BigQuery Console (replace placeholders):

```sql
-- Test query for Abilene, TX (GEOID: 48001) - 2024
-- Owner-occupied, site-built, 1-4 units, originations only

SELECT 
  loan_purpose,
  COUNT(*) as loan_count,
  COUNT(DISTINCT CONCAT(
    CAST(activity_year AS STRING), '-',
    COALESCE(lei, ''), '-',
    LPAD(CAST(county_code AS STRING), 5, '0'), '-',
    COALESCE(census_tract, ''), '-',
    COALESCE(loan_purpose, ''), '-',
    COALESCE(CAST(loan_amount AS STRING), ''), '-',
    COALESCE(CAST(action_taken AS STRING), '')
  )) as unique_loans
FROM `hdma1-242116.hmda.hmda` h
WHERE CAST(h.activity_year AS STRING) = '2024'
  AND h.state_code IS NOT NULL
  AND h.county_code IS NOT NULL
  AND LPAD(CAST(h.county_code AS STRING), 5, '0') = '48001'
  AND h.loan_purpose IN ('1', '2', '4', '31', '32')
  AND h.action_taken = '1'
  AND h.occupancy_type = '1'
  AND h.total_units IN ('1', '2', '3', '4')
  AND h.construction_method = '1'
  -- Note: NOT excluding reverse mortgages (reverse_mortgage can be NULL or any value)
GROUP BY loan_purpose
ORDER BY loan_purpose
```

## Method 5: Compare with Tableau Query

1. In Tableau, go to **Help > Settings and Performance > Start Performance Recording**
2. Run your analysis
3. Go to **Help > Settings and Performance > Stop Performance Recording**
4. In the performance recording, look for the **"Queries"** section
5. You'll see the exact BigQuery SQL that Tableau generated
6. Copy that query and compare it with the Flask app query

## Key Differences to Check

When comparing queries, look for:

1. **Reverse Mortgage Filter**:
   - Flask app: Should NOT have `(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')` if `exclude_reverse_mortgages = False`
   - Tableau: Check if it's filtering reverse mortgages

2. **Loan Purpose Codes**:
   - Flask app: Should include '1', '2', '4', '31', '32'
   - Tableau: Check which codes it's using

3. **Deduplication Logic**:
   - Flask app: Uses `loan_key` with `ROW_NUMBER()` for deduplication
   - Tableau: May use different deduplication logic

4. **Action Taken**:
   - Flask app: Should be `action_taken = '1'` (originations only)
   - Tableau: Check what action_taken values it's using

## Quick Verification Query

Run this to see total loans by purpose for a specific county:

```sql
SELECT 
  loan_purpose,
  COUNT(*) as total_rows,
  COUNT(DISTINCT CONCAT(
    CAST(activity_year AS STRING), '-',
    COALESCE(lei, ''), '-',
    LPAD(CAST(county_code AS STRING), 5, '0'), '-',
    COALESCE(census_tract, ''), '-',
    COALESCE(loan_purpose, ''), '-',
    COALESCE(CAST(loan_amount AS STRING), ''), '-',
    COALESCE(CAST(action_taken AS STRING), '')
  )) as unique_loans
FROM `hdma1-242116.hmda.hmda`
WHERE activity_year = 2024
  AND LPAD(CAST(county_code AS STRING), 5, '0') = '48001'  -- Abilene, TX
  AND loan_purpose IN ('1', '2', '4', '31', '32')
  AND action_taken = '1'
  AND occupancy_type = '1'
  AND total_units IN ('1', '2', '3', '4')
  AND construction_method = '1'
GROUP BY loan_purpose
ORDER BY loan_purpose
```

Expected results for Abilene, TX (2024, owner-occupied, site-built, 1-4 units, originations):
- Loan Purpose 1 (Home Purchase): ~1,805 loans
- Loan Purpose 31+32 (Refinance): ~532 loans  
- Loan Purpose 2+4 (Home Equity): ~244 loans

