# Race/Ethnicity Pre-Computation Implementation Guide

## Overview

Since we cannot modify the existing HMDA tables in BigQuery, we'll create **separate pre-computed tables** that store race/ethnicity classifications. This allows us to get the performance benefits without modifying the source data.

## Option 1: Race/Ethnicity Lookup Table (Recommended)

### Table Structure

Create a new table: `hmda.race_ethnicity_lookup`

```sql
CREATE TABLE `hdma1-242116.hmda.race_ethnicity_lookup` (
  lei STRING,
  activity_year INT64,
  county_code STRING,
  census_tract STRING,
  race_ethnicity_category STRING,  -- 'Hispanic', 'Black', 'Asian', 'White', 'Native_American', 'HoPI', 'Multi_Racial', 'No_Data'
  is_multi_racial BOOL,
  -- Include other fields needed for joins (loan_purpose, etc. if needed)
  PRIMARY KEY (lei, activity_year, county_code, census_tract) NOT ENFORCED
)
PARTITION BY activity_year
CLUSTER BY county_code, lei;
```

### Population Query

One-time ETL job or scheduled query to populate:

```sql
INSERT INTO `hdma1-242116.hmda.race_ethnicity_lookup`
SELECT 
  h.lei,
  h.activity_year,
  h.county_code,
  h.census_tract,
  -- Race/ethnicity classification logic (same as current SQL template)
  CASE 
    -- Hispanic check first
    WHEN h.applicant_ethnicity_1 IN ('1','11','12','13','14')
        OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
        OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
        OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
        OR h.applicant_ethnicity_5 IN ('1','11','12','13','14')
    THEN 'Hispanic'
    -- Then check race (using COALESCE for first valid race code)
    WHEN COALESCE(
        CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
             THEN h.applicant_race_1 ELSE NULL END,
        CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
             THEN h.applicant_race_2 ELSE NULL END,
        CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
             THEN h.applicant_race_3 ELSE NULL END,
        CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
             THEN h.applicant_race_4 ELSE NULL END,
        CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
             THEN h.applicant_race_5 ELSE NULL END
    ) = '3' THEN 'Black'
    WHEN COALESCE(...) IN ('2','21','22','23','24','25','26','27') THEN 'Asian'
    WHEN COALESCE(...) = '5' THEN 'White'
    WHEN COALESCE(...) = '1' THEN 'Native_American'
    WHEN COALESCE(...) IN ('4','41','42','43','44') THEN 'HoPI'
    -- Multi-racial check (2+ distinct main race categories)
    WHEN (
        SELECT COUNT(DISTINCT main_cat)
        FROM UNNEST([...]) AS main_cat
        WHERE main_cat IS NOT NULL
    ) >= 2 THEN 'Multi_Racial'
    ELSE 'No_Data'
  END as race_ethnicity_category,
  -- Multi-racial flag
  (
    SELECT COUNT(DISTINCT main_cat)
    FROM UNNEST([...]) AS main_cat
    WHERE main_cat IS NOT NULL
  ) >= 2 as is_multi_racial
FROM `hdma1-242116.hmda.hmda` h
WHERE h.activity_year >= 2020  -- Adjust year range as needed
```

### Updated SQL Template

Modify `apps/lendsight/sql_templates/mortgage_report.sql` to JOIN to lookup table:

```sql
SELECT
    h.lei,
    h.activity_year as year,
    h.county_code,
    c.county_state,
    -- ... other fields ...
    -- Replace complex CASE statements with simple COUNT from lookup table
    COUNTIF(r.race_ethnicity_category = 'Hispanic') as hispanic_originations,
    COUNTIF(r.race_ethnicity_category = 'Black') as black_originations,
    COUNTIF(r.race_ethnicity_category = 'Asian') as asian_originations,
    COUNTIF(r.race_ethnicity_category = 'White') as white_originations,
    COUNTIF(r.race_ethnicity_category = 'Native_American') as native_american_originations,
    COUNTIF(r.race_ethnicity_category = 'HoPI') as hopi_originations,
    COUNTIF(r.race_ethnicity_category = 'Multi_Racial') as multi_racial_originations,
    COUNT(*) as total_originations
FROM `hdma1-242116.hmda.hmda` h
LEFT JOIN `hdma1-242116.hmda.race_ethnicity_lookup` r
    ON h.lei = r.lei
    AND h.activity_year = r.activity_year
    AND h.county_code = r.county_code
    AND h.census_tract = r.census_tract
-- ... rest of query ...
GROUP BY h.lei, h.activity_year, h.county_code, c.county_state, ...
```

**Benefits:**
- Eliminates hundreds of lines of complex CASE statements
- Much faster queries (5-10x speedup)
- Can be updated incrementally (only new years need processing)
- Partitioned by year for efficient queries

**Storage Cost:**
- ~10-20% of HMDA table size (one row per loan)
- Clustered by county_code and lei for fast joins

---

## Option 2: Aggregated Pre-Computed Tables (Alternative)

### Table Structure

Create aggregated tables that pre-compute common aggregations:

```sql
CREATE TABLE `hdma1-242116.hmda.aggregated_by_county_year` (
  county_code STRING,
  activity_year INT64,
  lei STRING,
  lender_name STRING,
  loan_purpose STRING,
  total_originations INT64,
  hispanic_originations INT64,
  black_originations INT64,
  asian_originations INT64,
  white_originations INT64,
  native_american_originations INT64,
  hopi_originations INT64,
  multi_racial_originations INT64,
  -- Other aggregated fields (income, tract, etc.)
  PRIMARY KEY (county_code, activity_year, lei, loan_purpose) NOT ENFORCED
)
PARTITION BY activity_year
CLUSTER BY county_code, lei;
```

### Population Query

Aggregate once, query many times:

```sql
INSERT INTO `hdma1-242116.hmda.aggregated_by_county_year`
SELECT 
  h.county_code,
  h.activity_year,
  h.lei,
  MAX(l.respondent_name) as lender_name,
  h.loan_purpose,
  COUNT(*) as total_originations,
  COUNTIF(r.race_ethnicity_category = 'Hispanic') as hispanic_originations,
  COUNTIF(r.race_ethnicity_category = 'Black') as black_originations,
  -- ... other race categories ...
FROM `hdma1-242116.hmda.hmda` h
LEFT JOIN `hdma1-242116.hmda.race_ethnicity_lookup` r
    ON h.lei = r.lei
    AND h.activity_year = r.activity_year
    AND h.county_code = r.county_code
    AND h.census_tract = r.census_tract
LEFT JOIN `hdma1-242116.hmda.lenders18` l
    ON h.lei = l.lei
WHERE h.action_taken = '1'
  AND h.occupancy_type = '1'
  -- ... other filters ...
GROUP BY h.county_code, h.activity_year, h.lei, h.loan_purpose
```

**Benefits:**
- Even faster queries (data already aggregated)
- Much smaller storage (already aggregated)
- Can create multiple aggregation levels (by county, by lender, by tract, etc.)

**Storage Cost:**
- Much smaller than raw HMDA (already aggregated)
- Multiple tables for different aggregation levels

---

## Implementation Steps

### Step 1: Create Lookup Table
1. Run the CREATE TABLE statement for `race_ethnicity_lookup`
2. Set up partitioning and clustering

### Step 2: Populate Lookup Table
1. Create the population query (one-time for historical data)
2. Run the query (may take several hours for full HMDA dataset)
3. Set up scheduled query to update for new years

### Step 3: Update SQL Template
1. Modify `apps/lendsight/sql_templates/mortgage_report.sql`
2. Replace complex CASE statements with JOIN to lookup table
3. Test with sample queries

### Step 4: Verify Performance
1. Run test queries and compare execution times
2. Verify results match previous calculations
3. Monitor BigQuery slot usage

### Step 5: Deploy
1. Update production SQL template
2. Monitor for any issues
3. Consider creating aggregated tables for further optimization

---

## Maintenance

### Scheduled Updates
- Set up a scheduled query to run monthly/quarterly for new HMDA data
- Or trigger on new data availability

### Incremental Updates
- Only process new years (use WHERE activity_year > last_processed_year)
- Use MERGE statement to update existing records if needed

---

## Cost Considerations

### Storage Costs
- Lookup table: ~10-20% of HMDA table size
- Aggregated tables: Much smaller (already aggregated)

### Query Costs
- Initial population: One-time cost (can run during off-peak hours)
- Scheduled updates: Minimal (only new data)
- Query performance: **Significantly reduced** (5-10x faster = 5-10x cheaper per query)

### Net Savings
- Faster queries = lower BigQuery costs per query
- Reduced slot usage = better performance for all users
- Storage cost is one-time, query savings are ongoing

---

## Rollback Plan

If issues arise:
1. Keep old SQL template as backup
2. Can switch back by removing JOIN to lookup table
3. Lookup table can be dropped without affecting source data

