-- Migration Script 22: Copy centroid tables to justdata-ncrc shared dataset
-- Source: hdma1-242116.justdata_analytics.* (~3K rows total)
-- Destination: justdata-ncrc.shared.*
-- Type: Full copy

-- Copy county centroids to shared dataset
CREATE OR REPLACE TABLE `justdata-ncrc.shared.county_centroids` AS
SELECT *
FROM `hdma1-242116.justdata_analytics.county_centroids`;

-- Copy CBSA centroids to shared dataset
CREATE OR REPLACE TABLE `justdata-ncrc.shared.cbsa_centroids` AS
SELECT *
FROM `hdma1-242116.justdata_analytics.cbsa_centroids`;

-- Verify row counts
SELECT 'county_centroids' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.shared.county_centroids`
UNION ALL
SELECT 'cbsa_centroids' as table_name, COUNT(*) as row_count FROM `justdata-ncrc.shared.cbsa_centroids`;
