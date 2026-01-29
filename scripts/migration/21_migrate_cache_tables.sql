-- Migration Script 21: Migrate cache tables with history to justdata-ncrc
-- Source: hdma1-242116.justdata.* (cache tables)
-- Destination: justdata-ncrc.cache.*
-- Type: Full copy with history

-- Migrate usage_log with history
CREATE OR REPLACE TABLE `justdata-ncrc.cache.usage_log` AS
SELECT *
FROM `hdma1-242116.justdata.usage_log`;

-- Migrate analysis_cache with history
CREATE OR REPLACE TABLE `justdata-ncrc.cache.analysis_cache` AS
SELECT *
FROM `hdma1-242116.justdata.analysis_cache`;

-- Migrate analysis_results with history
CREATE OR REPLACE TABLE `justdata-ncrc.cache.analysis_results` AS
SELECT *
FROM `hdma1-242116.justdata.analysis_results`;

-- Migrate analysis_result_sections if exists (wrapped in try-catch style)
-- Note: This may fail if table doesn't exist - run separately if needed
CREATE OR REPLACE TABLE `justdata-ncrc.cache.analysis_result_sections` AS
SELECT *
FROM `hdma1-242116.justdata.analysis_result_sections`;

-- Verify row counts
SELECT 'usage_log' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.cache.usage_log`
UNION ALL
SELECT 'analysis_cache' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.cache.analysis_cache`
UNION ALL
SELECT 'analysis_results' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.cache.analysis_results`;
