-- Copy shared reference tables from hdma1-242116 to justdata.shared
-- Run this in BigQuery Console connected to justdata project

-- =============================================================================
-- 1. Copy cbsa_to_county reference table
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.shared.cbsa_to_county` AS
SELECT *
FROM `hdma1-242116.geo.cbsa_to_county`;

-- =============================================================================
-- 2. Copy census reference table
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.shared.census` AS
SELECT *
FROM `hdma1-242116.geo.census`;

-- =============================================================================
-- Verification
-- =============================================================================
SELECT 'cbsa_to_county' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.shared.cbsa_to_county`
UNION ALL
SELECT 'census' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.shared.census`;
