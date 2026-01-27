-- Create Connecticut Tract Crosswalk table
-- Maps 2020 tract FIPS codes to 2022 Planning Region codes
-- Source: https://github.com/CT-Data-Collaborative/2022-tract-crosswalk
-- Run this in BigQuery Console connected to justdata project

-- =============================================================================
-- Create the table structure
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.shared.ct_tract_crosswalk` (
    tract_fips_2020 STRING NOT NULL,      -- Old tract code (e.g., 09013528100)
    tract_fips_2022 STRING NOT NULL,      -- New tract code (e.g., 09110528100)
    tract_name STRING,                     -- Tract number
    town_name STRING,                      -- Town name (e.g., "Andover")
    town_fips_2020 STRING,                -- Old town FIPS
    town_fips_2022 STRING,                -- New town FIPS
    county_name STRING,                    -- Old county name (e.g., "Tolland")
    county_fips_2020 STRING,              -- Old county code (09013)
    ce_name_2022 STRING,                  -- Planning region name
    ce_fips_2022 STRING                   -- New planning region code (09110)
)
OPTIONS(
    description="Connecticut tract crosswalk from 2020 counties to 2022 Planning Regions. Source: Census Bureau via CT Data Collaborative."
);

-- =============================================================================
-- Load data from CSV (upload to GCS first, or use inline INSERT)
-- Option 1: Load from GCS
-- bq load --source_format=CSV --skip_leading_rows=1 justdata-ncrc.shared.ct_tract_crosswalk gs://your-bucket/2022tractcrosswalk.csv
-- 
-- Option 2: Use BigQuery Console to upload CSV directly
-- 
-- Option 3: Insert data inline (subset shown below, full data in separate file)
-- =============================================================================

-- Sample insert for validation (full data should be loaded from CSV)
INSERT INTO `justdata-ncrc.shared.ct_tract_crosswalk` 
(tract_fips_2020, tract_fips_2022, tract_name, town_name, town_fips_2020, town_fips_2022, county_name, county_fips_2020, ce_name_2022, ce_fips_2022)
VALUES
-- Capitol Planning Region (09110)
('09013528100', '09110528100', '5281', 'Andover', '0901301080', '0911001080', 'Tolland', '09013', 'Capitol Planning Region', '09110'),
('09003462202', '09110462202', '4622.02', 'Avon', '0900302060', '0911002060', 'Hartford', '09003', 'Capitol Planning Region', '09110'),
('09003462201', '09110462201', '4622.01', 'Avon', '0900302060', '0911002060', 'Hartford', '09003', 'Capitol Planning Region', '09110'),
-- Greater Bridgeport Planning Region (09120)
('09001071000', '09120071000', '710', 'Bridgeport', '0900108070', '0912008070', 'Fairfield', '09001', 'Greater Bridgeport Planning Region', '09120'),
('09001071100', '09120071100', '711', 'Bridgeport', '0900108070', '0912008070', 'Fairfield', '09001', 'Greater Bridgeport Planning Region', '09120'),
-- Lower Connecticut River Valley Planning Region (09130)
('09007600100', '09130600100', '6001', 'Chester', '0900714300', '0913014300', 'Middlesex', '09007', 'Lower Connecticut River Valley Planning Region', '09130'),
-- Naugatuck Valley Planning Region (09140)
('09009125200', '09140125200', '1252', 'Ansonia', '0900901220', '0914001220', 'New Haven', '09009', 'Naugatuck Valley Planning Region', '09140'),
-- Northeastern Connecticut Planning Region (09150)
('09015830100', '09150830100', '8301', 'Ashford', '0901501430', '0915001430', 'Windham', '09015', 'Northeastern Connecticut Planning Region', '09150'),
-- Northwest Hills Planning Region (09160)
('09005290100', '09160290100', '2901', 'Barkhamsted', '0900502760', '0916002760', 'Litchfield', '09005', 'Northwest Hills Planning Region', '09160'),
-- South Central Connecticut Planning Region (09170)
('09009184300', '09170184300', '1843', 'Branford', '0900907310', '0917007310', 'New Haven', '09009', 'South Central Connecticut Planning Region', '09170'),
-- Southeastern Connecticut Planning Region (09180)
('09011713100', '09180713100', '7131', 'Bozrah', '0901106820', '0918006820', 'New London', '09011', 'Southeastern Connecticut Planning Region', '09180'),
-- Western Connecticut Planning Region (09190)
('09001200302', '09190200302', '2003.02', 'Bethel', '0900104720', '0919004720', 'Fairfield', '09001', 'Western Connecticut Planning Region', '09190');

-- NOTE: The above is a SAMPLE. Load the full CSV from:
-- https://raw.githubusercontent.com/CT-Data-Collaborative/2022-tract-crosswalk/main/2022tractcrosswalk.csv

-- =============================================================================
-- Verification queries
-- =============================================================================

-- Count by planning region
SELECT 
    ce_name_2022,
    ce_fips_2022,
    COUNT(*) as tract_count
FROM `justdata-ncrc.shared.ct_tract_crosswalk`
GROUP BY 1, 2
ORDER BY 2;

-- Count by old county
SELECT 
    county_name,
    county_fips_2020,
    COUNT(*) as tract_count
FROM `justdata-ncrc.shared.ct_tract_crosswalk`
GROUP BY 1, 2
ORDER BY 2;
