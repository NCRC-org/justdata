-- Diagnostic query to determine the actual structure of county_code in HMDA table
-- Run this in BigQuery to see what county_code actually contains

SELECT 
    CAST(h.activity_year AS STRING) as activity_year,
    h.state_code,
    h.county_code,
    LENGTH(CAST(h.county_code AS STRING)) as county_code_length,
    CONCAT(LPAD(CAST(h.state_code AS STRING), 2, '0'), LPAD(CAST(h.county_code AS STRING), 3, '0')) as derived_geoid5,
    LPAD(CAST(h.county_code AS STRING), 5, '0') as padded_county_code,
    COUNT(*) as row_count
FROM `hdma1-242116.hmda.hmda` h
WHERE CAST(h.activity_year AS STRING) IN ('2023', '2024')
  AND h.state_code IS NOT NULL
  AND h.county_code IS NOT NULL
GROUP BY activity_year, state_code, county_code, county_code_length, derived_geoid5, padded_county_code
ORDER BY row_count DESC
LIMIT 20;

