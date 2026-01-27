-- Copy FDIC SOD (Summary of Deposits) tables to branchsight dataset
-- These need lat/lng for mapping, so we keep them at full detail
-- Run this in BigQuery Console connected to justdata project

-- =============================================================================
-- 1. Copy main SOD table (current year data)
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.branchsight.sod` AS
SELECT *
FROM `hdma1-242116.fdic_data.sod`;

-- =============================================================================
-- 2. Copy SOD legacy table (historical data)
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.branchsight.sod_legacy` AS
SELECT *
FROM `hdma1-242116.fdic_data.sod_legacy`;

-- =============================================================================
-- 3. Copy SOD 2025 table (if exists)
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.branchsight.sod25` AS
SELECT *
FROM `hdma1-242116.fdic_data.sod25`;

-- =============================================================================
-- Verification
-- =============================================================================

-- Row counts for all SOD tables
SELECT 'sod' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.branchsight.sod`
UNION ALL
SELECT 'sod_legacy' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.branchsight.sod_legacy`
UNION ALL
SELECT 'sod25' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.branchsight.sod25`;

-- Compare to source
SELECT 'source_sod' as table_name, COUNT(*) as row_count FROM `hdma1-242116.fdic_data.sod`
UNION ALL
SELECT 'source_sod_legacy' as table_name, COUNT(*) as row_count FROM `hdma1-242116.fdic_data.sod_legacy`
UNION ALL
SELECT 'source_sod25' as table_name, COUNT(*) as row_count FROM `hdma1-242116.fdic_data.sod25`;

-- Table sizes
SELECT 
    table_id,
    ROUND(size_bytes / (1024*1024), 2) as size_mb,
    row_count
FROM `justdata-ncrc.branchsight.__TABLES__`;
