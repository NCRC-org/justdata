-- ============================================================================
-- Verification Queries for justdata.de_hmda Table
-- ============================================================================
-- Run these queries to verify the table was created correctly
-- ============================================================================

-- 1. Check row counts by year
SELECT 
  activity_year,
  COUNT(*) as row_count
FROM `hdma1-242116.justdata.de_hmda`
GROUP BY activity_year
ORDER BY activity_year DESC;

-- 2. Compare with source HMDA table (should be similar counts)
SELECT 
  'Source HMDA' as source,
  CAST(activity_year AS INT64) as activity_year,
  COUNT(*) as row_count
FROM `hdma1-242116.hmda.hmda`
WHERE CAST(activity_year AS INT64) >= 2018
GROUP BY activity_year
ORDER BY activity_year DESC;

-- 3. Verify race/ethnicity flags are populated correctly
SELECT 
  activity_year,
  COUNT(*) as total_rows,
  COUNTIF(is_hispanic) as hispanic_count,
  COUNTIF(is_black) as black_count,
  COUNTIF(is_asian) as asian_count,
  COUNTIF(is_white) as white_count,
  COUNTIF(is_native_american) as native_american_count,
  COUNTIF(is_hopi) as hopi_count,
  COUNTIF(is_multi_racial) as multi_racial_count,
  COUNTIF(has_demographic_data) as has_demographic_data_count
FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2024  -- Test with most recent year
GROUP BY activity_year;

-- 4. CRITICAL: Verify no overlaps (these should all be 0)
SELECT 
  activity_year,
  COUNTIF(is_hispanic AND is_multi_racial) as hispanic_and_multi_racial,  -- Should be 0
  COUNTIF(is_multi_racial AND is_black) as multi_racial_and_black,  -- Should be 0
  COUNTIF(is_multi_racial AND is_white) as multi_racial_and_white,  -- Should be 0
  COUNTIF(is_multi_racial AND is_asian) as multi_racial_and_asian,  -- Should be 0
  COUNTIF(is_multi_racial AND is_hopi) as multi_racial_and_hopi,  -- Should be 0
  COUNTIF(is_multi_racial AND is_native_american) as multi_racial_and_native_american  -- Should be 0
FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2024
GROUP BY activity_year;

-- 5. Verify income category flags are populated
SELECT 
  activity_year,
  COUNTIF(is_lmib) as lmib_count,
  COUNTIF(is_low_income_borrower) as low_income_borrower_count,
  COUNTIF(is_moderate_income_borrower) as moderate_income_borrower_count,
  COUNTIF(is_middle_income_borrower) as middle_income_borrower_count,
  COUNTIF(is_upper_income_borrower) as upper_income_borrower_count
FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2024
GROUP BY activity_year;

-- 6. Verify tract category flags are populated
SELECT 
  activity_year,
  COUNTIF(is_lmict) as lmict_count,
  COUNTIF(is_low_income_tract) as low_income_tract_count,
  COUNTIF(is_moderate_income_tract) as moderate_income_tract_count,
  COUNTIF(is_middle_income_tract) as middle_income_tract_count,
  COUNTIF(is_upper_income_tract) as upper_income_tract_count,
  COUNTIF(is_mmct) as mmct_count
FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2024
GROUP BY activity_year;

-- 7. Check that lender information is populated
SELECT 
  activity_year,
  COUNT(*) as total_rows,
  COUNTIF(lender_name IS NOT NULL) as has_lender_name,
  COUNTIF(lender_type IS NOT NULL) as has_lender_type
FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2024
GROUP BY activity_year;

-- 8. Check geoid5 normalization (Connecticut planning regions)
SELECT 
  activity_year,
  COUNT(*) as total_rows,
  COUNTIF(geoid5 LIKE '09%') as connecticut_rows,
  COUNTIF(geoid5 LIKE '091%') as planning_region_rows  -- Should be all CT rows for 2024
FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2024
  AND geoid5 LIKE '09%'
GROUP BY activity_year;

-- 9. Sample a few rows to verify data looks correct
SELECT 
  activity_year,
  lei,
  geoid5,
  lender_name,
  is_hispanic,
  is_black,
  is_asian,
  is_white,
  is_multi_racial,
  is_lmib,
  is_lmict
FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2024
LIMIT 10;

