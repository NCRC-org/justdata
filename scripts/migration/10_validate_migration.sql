-- Validate Migration: Compare old vs new data
-- Run these queries to verify data integrity before switching production
-- Run this in BigQuery Console

-- =============================================================================
-- 1. HMDA County Summary Validation
-- =============================================================================

-- Total originations by year should match
WITH old_data AS (
    SELECT 
        activity_year as year,
        COUNT(*) as total_originations
    FROM `hdma1-242116.justdata.de_hmda`
    WHERE action_taken = '1' 
      AND occupancy_type = '1'
      AND total_units IN ('1','2','3','4') 
      AND construction_method = '1'
      AND (reverse_mortgage IS NULL OR reverse_mortgage != '1')
    GROUP BY year
),
new_data AS (
    SELECT 
        year,
        SUM(total_originations) as total_originations
    FROM `justdata-ncrc.lendsight.de_hmda_county_summary`
    GROUP BY year
)
SELECT 
    COALESCE(o.year, n.year) as year,
    o.total_originations as old_total,
    n.total_originations as new_total,
    CASE 
        WHEN o.total_originations = n.total_originations THEN 'MATCH'
        ELSE 'MISMATCH'
    END as status
FROM old_data o
FULL OUTER JOIN new_data n ON o.year = n.year
ORDER BY year;

-- =============================================================================
-- 2. HMDA Tract Summary Validation
-- =============================================================================

WITH old_data AS (
    SELECT 
        activity_year as year,
        COUNT(*) as total_originations
    FROM `hdma1-242116.justdata.de_hmda`
    WHERE action_taken = '1' 
      AND occupancy_type = '1'
      AND total_units IN ('1','2','3','4') 
      AND construction_method = '1'
      AND (reverse_mortgage IS NULL OR reverse_mortgage != '1')
    GROUP BY year
),
new_data AS (
    SELECT 
        year,
        SUM(total_originations) as total_originations
    FROM `justdata-ncrc.lendsight.de_hmda_tract_summary`
    GROUP BY year
)
SELECT 
    COALESCE(o.year, n.year) as year,
    o.total_originations as old_total,
    n.total_originations as new_total,
    CASE 
        WHEN o.total_originations = n.total_originations THEN 'MATCH'
        ELSE 'MISMATCH'
    END as status
FROM old_data o
FULL OUTER JOIN new_data n ON o.year = n.year
ORDER BY year;

-- =============================================================================
-- 3. SB County Summary Validation
-- =============================================================================

WITH old_data AS (
    SELECT 
        year,
        SUM(COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0)) as total_loans
    FROM `hdma1-242116.sb.disclosure`
    GROUP BY year
),
new_data AS (
    SELECT 
        year,
        SUM(total_loans) as total_loans
    FROM `justdata-ncrc.bizsight.sb_county_summary`
    GROUP BY year
)
SELECT 
    COALESCE(o.year, n.year) as year,
    o.total_loans as old_total,
    n.total_loans as new_total,
    CASE 
        WHEN o.total_loans = n.total_loans THEN 'MATCH'
        ELSE 'MISMATCH'
    END as status
FROM old_data o
FULL OUTER JOIN new_data n ON o.year = n.year
ORDER BY year;

-- =============================================================================
-- 4. SOD Tables Validation
-- =============================================================================

SELECT 
    'sod' as table_name,
    (SELECT COUNT(*) FROM `hdma1-242116.fdic_data.sod`) as old_count,
    (SELECT COUNT(*) FROM `justdata-ncrc.branchsight.sod`) as new_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM `hdma1-242116.fdic_data.sod`) = 
             (SELECT COUNT(*) FROM `justdata-ncrc.branchsight.sod`)
        THEN 'MATCH' ELSE 'MISMATCH' 
    END as status
UNION ALL
SELECT 
    'sod_legacy' as table_name,
    (SELECT COUNT(*) FROM `hdma1-242116.fdic_data.sod_legacy`) as old_count,
    (SELECT COUNT(*) FROM `justdata-ncrc.branchsight.sod_legacy`) as new_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM `hdma1-242116.fdic_data.sod_legacy`) = 
             (SELECT COUNT(*) FROM `justdata-ncrc.branchsight.sod_legacy`)
        THEN 'MATCH' ELSE 'MISMATCH' 
    END as status;

-- =============================================================================
-- 5. Connecticut Crosswalk Validation
-- =============================================================================

-- Should have all 9 planning regions
SELECT 
    ce_name_2022,
    ce_fips_2022,
    COUNT(*) as tract_count
FROM `justdata-ncrc.shared.ct_tract_crosswalk`
GROUP BY 1, 2
ORDER BY 2;

-- Should have all 8 old counties
SELECT 
    county_name,
    county_fips_2020,
    COUNT(*) as tract_count
FROM `justdata-ncrc.shared.ct_tract_crosswalk`
GROUP BY 1, 2
ORDER BY 2;

-- =============================================================================
-- 6. Cost Comparison Query (estimate bytes processed)
-- =============================================================================

-- Old way: Query loan-level data
-- SELECT ... FROM `hdma1-242116.justdata.de_hmda` WHERE county_state = 'MD' AND activity_year = 2023
-- Estimated bytes: ~2GB per query

-- New way: Query county summary
-- SELECT ... FROM `justdata-ncrc.lendsight.de_hmda_county_summary` WHERE county_state = 'MD' AND year = 2023
-- Estimated bytes: ~2MB per query

-- Savings: ~99.9%
