# Automatic Updates for justdata.de_hmda Table

## Overview

The `justdata.de_hmda` table can be automatically updated when new HMDA data is added using BigQuery **Scheduled Queries**. This ensures the optimized table stays in sync with the source HMDA data.

---

## Option 1: Scheduled Query (Recommended)

### Setup Steps

1. **Create a scheduled query in BigQuery Console**
   - Go to BigQuery Console → Scheduled Queries
   - Create new scheduled query
   - Use the incremental update SQL (see below)
   - Set schedule: **Monthly** (HMDA data is typically released annually, but monthly checks catch updates)
   - Set destination: `justdata.de_hmda` (MERGE mode)

2. **Incremental Update SQL**

```sql
-- ============================================================================
-- Incremental Update for justdata.de_hmda
-- ============================================================================
-- This query only processes NEW years that don't exist in de_hmda yet
-- Run monthly to catch new HMDA data releases
-- ============================================================================

MERGE `hdma1-242116.justdata.de_hmda` AS target
USING (
  -- Select only new years that don't exist in de_hmda yet
  SELECT
    -- Identifiers
    h.lei,
    h.activity_year,
    h.county_code,
    c.county_state,
    -- geoid5: Normalize Connecticut data to planning region codes
    COALESCE(
      CASE 
        WHEN CAST(h.county_code AS STRING) LIKE '09%' 
             AND CAST(h.county_code AS STRING) NOT LIKE '091%'
             AND h.census_tract IS NOT NULL
             AND ct_tract.geoid IS NOT NULL THEN
          SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
        ELSE NULL
      END,
      CAST(h.county_code AS STRING)
    ) as geoid5,
    h.census_tract,
    h.census_tract as tract_code,
    
    -- Lender information
    l.respondent_name as lender_name,
    l.type_name as lender_type,
    
    -- Loan characteristics
    h.loan_purpose,
    h.loan_type,
    h.action_taken,
    h.occupancy_type,
    h.total_units,
    h.construction_method,
    h.reverse_mortgage,
    
    -- Loan amounts and values
    h.loan_amount,
    h.property_value,
    h.interest_rate,
    h.total_loan_costs,
    h.origination_charges,
    h.income,
    
    -- Tract characteristics
    h.tract_minority_population_percent,
    h.tract_to_msa_income_percentage,
    h.ffiec_msa_md_median_family_income,
    
    -- Pre-computed race/ethnicity flags (same logic as create_de_hmda_table.sql)
    (
      h.applicant_ethnicity_1 IN ('1','11','12','13','14')
      OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
      OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
      OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
      OR h.applicant_ethnicity_5 IN ('1','11','12','13','14')
    ) as is_hispanic,
    
    -- ... (include all other race/ethnicity flags from create_de_hmda_table.sql)
    -- ... (include all income category flags)
    -- ... (include all tract category flags)
    -- (Full logic same as in create_de_hmda_table.sql)
    
  FROM `hdma1-242116.hmda.hmda` h
  LEFT JOIN `hdma1-242116.geo.census` ct_tract
    ON CAST(h.county_code AS STRING) LIKE '09%'
    AND CAST(h.county_code AS STRING) NOT LIKE '091%'
    AND h.census_tract IS NOT NULL
    AND SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 6, 6) = SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 6, 6)
  LEFT JOIN `hdma1-242116.geo.cbsa_to_county` c
    ON COALESCE(
      CASE 
        WHEN CAST(h.county_code AS STRING) LIKE '09%' 
             AND CAST(h.county_code AS STRING) NOT LIKE '091%'
             AND ct_tract.geoid IS NOT NULL THEN
          SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
        ELSE NULL
      END,
      CAST(h.county_code AS STRING)
    ) = CAST(c.geoid5 AS STRING)
  LEFT JOIN `hdma1-242116.hmda.lenders18` l
    ON h.lei = l.lei
  WHERE h.activity_year > (
    -- Only process years that don't exist in de_hmda yet
    SELECT COALESCE(MAX(activity_year), 2017)
    FROM `hdma1-242116.justdata.de_hmda`
  )
) AS source
ON FALSE  -- Always insert (no matching needed for new years)
WHEN NOT MATCHED BY TARGET THEN
  INSERT ROW;

-- Note: This uses MERGE with ON FALSE to only insert new rows
-- For full logic, copy all the race/ethnicity calculations from create_de_hmda_table.sql
```

### Alternative: Simpler Incremental Insert

If MERGE is too complex, use a simpler INSERT-only approach:

```sql
-- ============================================================================
-- Incremental Insert for justdata.de_hmda (New Years Only)
-- ============================================================================

INSERT INTO `hdma1-242116.justdata.de_hmda`
SELECT
  -- ... (same SELECT as create_de_hmda_table.sql)
  -- Copy full SELECT statement from create_de_hmda_table.sql
FROM `hdma1-242116.hmda.hmda` h
-- ... (same joins as create_de_hmda_table.sql)
WHERE h.activity_year > (
  -- Only process years that don't exist in de_hmda yet
  SELECT COALESCE(MAX(activity_year), 2017)
  FROM `hdma1-242116.justdata.de_hmda`
)
```

---

## Option 2: Full Refresh (If Data Can Be Updated Retroactively)

If HMDA data for existing years can be updated (corrected), use this approach:

```sql
-- ============================================================================
-- Full Refresh for Specific Year
-- ============================================================================
-- Use this if HMDA data for a year is updated/corrected
-- ============================================================================

-- Step 1: Delete existing data for the year
DELETE FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2024;  -- Replace with year to refresh

-- Step 2: Re-insert data for that year
INSERT INTO `hdma1-242116.justdata.de_hmda`
SELECT
  -- ... (same SELECT as create_de_hmda_table.sql)
FROM `hdma1-242116.hmda.hmda` h
-- ... (same joins)
WHERE h.activity_year = 2024;  -- Replace with year to refresh
```

---

## Option 3: Scheduled Query with Python Script

For more control, create a Python script that can be run via Cloud Scheduler or GitHub Actions:

```python
#!/usr/bin/env python3
"""
Automatically update justdata.de_hmda table when new HMDA data is available.
Run via Cloud Scheduler, GitHub Actions, or cron.
"""

from google.cloud import bigquery
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = "hdma1-242116"
DE_HMDA_TABLE = f"{PROJECT_ID}.justdata.de_hmda"
HMDA_TABLE = f"{PROJECT_ID}.hmda.hmda"

def get_max_year_in_de_hmda(client):
    """Get the maximum year currently in de_hmda table."""
    query = f"""
    SELECT COALESCE(MAX(activity_year), 2017) as max_year
    FROM `{DE_HMDA_TABLE}`
    """
    result = client.query(query).result()
    row = next(result, None)
    return row.max_year if row else 2017

def get_available_years_in_hmda(client):
    """Get all available years in source HMDA table."""
    query = f"""
    SELECT DISTINCT activity_year
    FROM `{HMDA_TABLE}`
    WHERE activity_year >= 2018
    ORDER BY activity_year
    """
    result = client.query(query).result()
    return [row.activity_year for row in result]

def update_de_hmda_for_year(client, year):
    """Update de_hmda table for a specific year."""
    # Read the full INSERT query from create_de_hmda_table.sql
    # and modify WHERE clause to filter by year
    query = f"""
    INSERT INTO `{DE_HMDA_TABLE}`
    SELECT
      -- ... (full SELECT from create_de_hmda_table.sql)
    FROM `{HMDA_TABLE}` h
    -- ... (joins)
    WHERE h.activity_year = {year}
    """
    
    logger.info(f"Updating de_hmda for year {year}...")
    job = client.query(query)
    job.result()  # Wait for completion
    logger.info(f"Successfully updated de_hmda for year {year}")

def main():
    """Main function to check and update de_hmda table."""
    client = bigquery.Client(project=PROJECT_ID)
    
    # Get current state
    max_year_in_de = get_max_year_in_de_hmda(client)
    available_years = get_available_years_in_hmda(client)
    
    logger.info(f"Current max year in de_hmda: {max_year_in_de}")
    logger.info(f"Available years in HMDA: {available_years}")
    
    # Find years that need to be added
    years_to_add = [y for y in available_years if y > max_year_in_de]
    
    if not years_to_add:
        logger.info("No new years to process. de_hmda is up to date.")
        return
    
    logger.info(f"Processing new years: {years_to_add}")
    
    # Process each new year
    for year in years_to_add:
        try:
            update_de_hmda_for_year(client, year)
        except Exception as e:
            logger.error(f"Error updating year {year}: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    main()
```

---

## Recommended Setup: BigQuery Scheduled Query

### Step-by-Step Instructions

1. **Go to BigQuery Console**
   - Navigate to: https://console.cloud.google.com/bigquery
   - Select project: `hdma1-242116`

2. **Create Scheduled Query**
   - Click "Scheduled Queries" in left sidebar
   - Click "Create Scheduled Query"
   - Name: `update_de_hmda_incremental`
   - Description: "Automatically update justdata.de_hmda when new HMDA data is available"

3. **Set Schedule**
   - Frequency: **Monthly** (or **Weekly** if you want more frequent checks)
   - Start date: Today
   - Time: Choose off-peak hours (e.g., 2 AM)

4. **Set Query**
   - Use the incremental INSERT query (Option 1, Alternative)
   - Destination: `justdata.de_hmda`
   - Write preference: **WRITE_APPEND** (only add new rows)

5. **Set Notifications** (Optional)
   - Email on failure: Your email
   - Email on success: (optional)

6. **Save and Enable**

---

## Monitoring

### Check Last Update

```sql
-- Check when de_hmda was last updated
SELECT 
  activity_year,
  COUNT(*) as row_count,
  MAX(_PARTITIONTIME) as last_updated  -- If using partition time
FROM `hdma1-242116.justdata.de_hmda`
GROUP BY activity_year
ORDER BY activity_year DESC;
```

### Compare with Source HMDA

```sql
-- Compare years available in source vs de_hmda
SELECT 
  'Source HMDA' as source,
  COUNT(DISTINCT activity_year) as year_count,
  MIN(activity_year) as min_year,
  MAX(activity_year) as max_year
FROM `hdma1-242116.hmda.hmda`
WHERE activity_year >= 2018

UNION ALL

SELECT 
  'de_hmda' as source,
  COUNT(DISTINCT activity_year) as year_count,
  MIN(activity_year) as min_year,
  MAX(activity_year) as max_year
FROM `hdma1-242116.justdata.de_hmda`;
```

### Check Scheduled Query Status

- Go to BigQuery Console → Scheduled Queries
- View execution history
- Check for any failures

---

## Handling Edge Cases

### 1. Data Corrections for Existing Years

If HMDA data for an existing year is corrected:

```sql
-- Delete and re-insert for that year
DELETE FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2023;  -- Year to refresh

-- Then run the INSERT for that year
-- (Use the incremental query but filter to specific year)
```

### 2. Partial Year Updates

If HMDA data is updated mid-year (unlikely but possible):

- The scheduled query will detect new rows based on `activity_year > MAX(existing)`
- If data is updated for existing year, use full refresh approach above

### 3. Schema Changes

If HMDA table schema changes:
- Update `create_de_hmda_table.sql` to match new schema
- Recreate table or alter existing table
- Re-run full population

---

## Cost Considerations

- **Scheduled Query Execution**: Minimal cost (only processes new data)
- **Storage**: Same as source HMDA (one row per loan)
- **Query Savings**: 5-10x faster queries = 5-10x cheaper per query
- **Net Benefit**: Ongoing query cost savings far exceed one-time storage cost

---

## Summary

✅ **Yes, the table can update automatically!**

**Recommended Approach:**
1. Use **BigQuery Scheduled Query** (Option 1)
2. Run **monthly** to catch new HMDA data releases
3. Use **incremental INSERT** (only process new years)
4. Monitor via BigQuery Console scheduled query history

This ensures `justdata.de_hmda` stays up-to-date automatically without manual intervention.

