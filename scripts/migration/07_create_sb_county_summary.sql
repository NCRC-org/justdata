-- Create County-Level Small Business Summary Table
-- Aggregates SB disclosure data to county level for ~99% cost reduction
-- Run this in BigQuery Console connected to justdata project

-- =============================================================================
-- Create the SB county summary table
-- Expected: ~5,000 rows per year
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.bizsight.sb_county_summary`
PARTITION BY RANGE_BUCKET(year, GENERATE_ARRAY(2018, 2030, 1))
CLUSTER BY geoid5
OPTIONS(
    description="County-level Small Business lending summary for BizSight and MergerMeter. Aggregated from sb.disclosure for ~99% cost reduction."
)
AS
SELECT
    LPAD(CAST(geoid5 AS STRING), 5, '0') as geoid5,
    CAST(year AS INT64) as year,
    lender_name,
    
    -- Loan counts by size (4 cols)
    SUM(COALESCE(num_under_100k, 0)) as num_under_100k,
    SUM(COALESCE(num_100k_250k, 0)) as num_100k_250k,
    SUM(COALESCE(num_250k_1m, 0)) as num_250k_1m,
    SUM(COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0)) as total_loans,
    
    -- Loan amounts (3 cols)
    SUM(COALESCE(amt_under_100k, 0)) as amt_under_100k,
    SUM(COALESCE(amt_100k_250k, 0)) as amt_100k_250k,
    SUM(COALESCE(amt_250k_1m, 0)) as amt_250k_1m,
    
    -- Pre-aggregated income category metrics (4 cols)
    SUM(CASE WHEN income_group_total IN ('101','102','001','002','003','004','005','006','007','008') 
        THEN COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0) 
        ELSE 0 END) as lmi_tract_loans,
    SUM(CASE WHEN income_group_total = '101' 
        THEN COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0) 
        ELSE 0 END) as low_income_loans,
    SUM(CASE WHEN income_group_total = '102' 
        THEN COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0) 
        ELSE 0 END) as moderate_income_loans,
    SUM(CASE WHEN income_group_total IN ('103','104') 
        THEN COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0) 
        ELSE 0 END) as midu_income_loans

FROM `hdma1-242116.sb.disclosure`
GROUP BY geoid5, year, lender_name;

-- =============================================================================
-- Verification
-- =============================================================================

-- Row counts by year
SELECT 
    year,
    COUNT(*) as row_count,
    SUM(total_loans) as total_loans,
    COUNT(DISTINCT geoid5) as counties,
    COUNT(DISTINCT lender_name) as lenders
FROM `justdata-ncrc.bizsight.sb_county_summary`
GROUP BY year
ORDER BY year;

-- Compare totals to source
SELECT 
    'sb_county_summary' as source,
    SUM(total_loans) as total_loans
FROM `justdata-ncrc.bizsight.sb_county_summary`
UNION ALL
SELECT 
    'source_disclosure' as source,
    SUM(COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0)) as total_loans
FROM `hdma1-242116.sb.disclosure`;

-- Table size
SELECT 
    table_id,
    ROUND(size_bytes / (1024*1024), 2) as size_mb,
    row_count
FROM `justdata-ncrc.bizsight.__TABLES__`
WHERE table_id = 'sb_county_summary';
