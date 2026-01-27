-- Copy raw de_hmda table to dataexplorer dataset for edge cases
-- This is a fallback for queries that need loan-level detail
-- Run this in BigQuery Console connected to justdata project

-- =============================================================================
-- Copy de_hmda (loan-level HMDA data)
-- WARNING: This is a large table (~50M rows). Only copy if needed.
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.dataexplorer.de_hmda`
PARTITION BY RANGE_BUCKET(activity_year, GENERATE_ARRAY(2018, 2030, 1))
CLUSTER BY geoid5, lei, loan_purpose
OPTIONS(
    description="Loan-level HMDA data for DataExplorer edge cases. Use summary tables when possible to reduce costs."
)
AS
SELECT *
FROM `hdma1-242116.justdata.de_hmda`;

-- =============================================================================
-- Verification
-- =============================================================================

-- Row counts by year
SELECT 
    activity_year as year,
    COUNT(*) as row_count
FROM `justdata-ncrc.dataexplorer.de_hmda`
GROUP BY year
ORDER BY year;

-- Compare totals
SELECT 
    'dataexplorer.de_hmda' as source,
    COUNT(*) as total_rows
FROM `justdata-ncrc.dataexplorer.de_hmda`
UNION ALL
SELECT 
    'source.de_hmda' as source,
    COUNT(*) as total_rows
FROM `hdma1-242116.justdata.de_hmda`;

-- Table size
SELECT 
    table_id,
    ROUND(size_bytes / (1024*1024*1024), 2) as size_gb,
    row_count
FROM `justdata-ncrc.dataexplorer.__TABLES__`
WHERE table_id = 'de_hmda';
