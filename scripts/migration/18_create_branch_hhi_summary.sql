-- Migration Script 18: Create branch_hhi_summary for MergerMeter HHI calculations
-- Source: justdata-ncrc.branchsight.sod (existing)
-- Destination: justdata-ncrc.branchsight.branch_hhi_summary
-- Type: New aggregated table (~100K rows)

-- Create aggregated summary table for HHI calculations
-- This eliminates the need to query the full sod table for HHI analysis
CREATE OR REPLACE TABLE `justdata-ncrc.branchsight.branch_hhi_summary`
CLUSTER BY year, geoid5 AS
SELECT
    CAST(year AS INT64) as year,
    geoid5,
    rssd,
    bank_name,
    COUNT(*) as branch_count,
    SUM(CAST(deposits_000s AS FLOAT64) * 1000) as total_deposits,
    COUNTIF(br_lmi = 1) as lmict_branches,
    COUNTIF(br_minority = 1) as mmct_branches,
    -- Additional useful aggregations for MergerMeter
    MIN(CAST(deposits_000s AS FLOAT64) * 1000) as min_branch_deposits,
    MAX(CAST(deposits_000s AS FLOAT64) * 1000) as max_branch_deposits,
    AVG(CAST(deposits_000s AS FLOAT64) * 1000) as avg_branch_deposits
FROM `justdata-ncrc.branchsight.sod`
WHERE geoid5 IS NOT NULL
GROUP BY year, geoid5, rssd, bank_name;

-- Note: Clustering is applied in the initial CREATE statement below

-- Verify row count
SELECT 
    'branch_hhi_summary' as table_name, 
    COUNT(*) as row_count,
    COUNT(DISTINCT geoid5) as unique_counties,
    COUNT(DISTINCT rssd) as unique_banks
FROM `justdata-ncrc.branchsight.branch_hhi_summary`;
