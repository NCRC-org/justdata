-- ============================================================================
-- Test Multi-Racial Logic
-- ============================================================================
-- This query tests various scenarios to verify multi-racial counting is correct
-- ============================================================================

-- Test Case 1: Person with race_1='3' (Black) and race_2='5' (White)
-- Expected: is_multi_racial = TRUE, is_black = FALSE, is_white = FALSE
-- Main categories: ['3', '5'] -> COUNT(DISTINCT) = 2 -> Multi-racial ✓

-- Test Case 2: Person with race_1='21' (Asian - Chinese) and race_2='22' (Asian - Japanese)
-- Expected: is_multi_racial = FALSE, is_asian = TRUE
-- Main categories: ['2', '2'] -> COUNT(DISTINCT) = 1 -> NOT multi-racial ✓
-- (Multiple Asian subcategories don't count as multi-racial)

-- Test Case 3: Person with race_1='3' (Black) and ethnicity_1='1' (Hispanic)
-- Expected: is_hispanic = TRUE, is_black = FALSE, is_multi_racial = FALSE
-- (Hispanic takes precedence, not counted in race categories)

-- Test Case 4: Person with race_1='3' (Black), race_2='5' (White), race_3='2' (Asian)
-- Expected: is_multi_racial = TRUE (3 distinct categories: Black, White, Asian)
-- Main categories: ['3', '5', '2'] -> COUNT(DISTINCT) = 3 -> Multi-racial ✓

WITH test_cases AS (
  SELECT 
    'Test 1: Black + White' as test_name,
    '3' as race_1,
    '5' as race_2,
    NULL as race_3,
    NULL as race_4,
    NULL as race_5,
    NULL as ethnicity_1,
    NULL as ethnicity_2,
    NULL as ethnicity_3,
    NULL as ethnicity_4,
    NULL as ethnicity_5
  UNION ALL
  SELECT 
    'Test 2: Multiple Asian subcategories' as test_name,
    '21' as race_1,  -- Chinese
    '22' as race_2,  -- Japanese
    NULL as race_3,
    NULL as race_4,
    NULL as race_5,
    NULL as ethnicity_1,
    NULL as ethnicity_2,
    NULL as ethnicity_3,
    NULL as ethnicity_4,
    NULL as ethnicity_5
  UNION ALL
  SELECT 
    'Test 3: Hispanic + Black' as test_name,
    '3' as race_1,
    NULL as race_2,
    NULL as race_3,
    NULL as race_4,
    NULL as race_5,
    '1' as ethnicity_1,  -- Hispanic
    NULL as ethnicity_2,
    NULL as ethnicity_3,
    NULL as ethnicity_4,
    NULL as ethnicity_5
  UNION ALL
  SELECT 
    'Test 4: Black + White + Asian' as test_name,
    '3' as race_1,  -- Black
    '5' as race_2,  -- White
    '2' as race_3,  -- Asian
    NULL as race_4,
    NULL as race_5,
    NULL as ethnicity_1,
    NULL as ethnicity_2,
    NULL as ethnicity_3,
    NULL as ethnicity_4,
    NULL as ethnicity_5
)
SELECT 
  test_name,
  -- Calculate main categories for each race field
  (
    SELECT COUNT(DISTINCT main_cat)
    FROM UNNEST([
      CASE WHEN race_1 IS NOT NULL AND race_1 != '' AND race_1 NOT IN ('6','7','8') 
           THEN CASE WHEN race_1 = '1' THEN '1'
                     WHEN race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                     WHEN race_1 = '3' THEN '3'
                     WHEN race_1 IN ('4','41','42','43','44') THEN '4'
                     WHEN race_1 = '5' THEN '5'
                     ELSE NULL END
           ELSE NULL END,
      CASE WHEN race_2 IS NOT NULL AND race_2 != '' AND race_2 NOT IN ('6','7','8') 
           THEN CASE WHEN race_2 = '1' THEN '1'
                     WHEN race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                     WHEN race_2 = '3' THEN '3'
                     WHEN race_2 IN ('4','41','42','43','44') THEN '4'
                     WHEN race_2 = '5' THEN '5'
                     ELSE NULL END
           ELSE NULL END,
      CASE WHEN race_3 IS NOT NULL AND race_3 != '' AND race_3 NOT IN ('6','7','8') 
           THEN CASE WHEN race_3 = '1' THEN '1'
                     WHEN race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                     WHEN race_3 = '3' THEN '3'
                     WHEN race_3 IN ('4','41','42','43','44') THEN '4'
                     WHEN race_3 = '5' THEN '5'
                     ELSE NULL END
           ELSE NULL END,
      CASE WHEN race_4 IS NOT NULL AND race_4 != '' AND race_4 NOT IN ('6','7','8') 
           THEN CASE WHEN race_4 = '1' THEN '1'
                     WHEN race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                     WHEN race_4 = '3' THEN '3'
                     WHEN race_4 IN ('4','41','42','43','44') THEN '4'
                     WHEN race_4 = '5' THEN '5'
                     ELSE NULL END
           ELSE NULL END,
      CASE WHEN race_5 IS NOT NULL AND race_5 != '' AND race_5 NOT IN ('6','7','8') 
           THEN CASE WHEN race_5 = '1' THEN '1'
                     WHEN race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                     WHEN race_5 = '3' THEN '3'
                     WHEN race_5 IN ('4','41','42','43','44') THEN '4'
                     WHEN race_5 = '5' THEN '5'
                     ELSE NULL END
           ELSE NULL END
    ]) AS main_cat
    WHERE main_cat IS NOT NULL
  ) as distinct_main_categories,
  -- Check if Hispanic
  (
    ethnicity_1 IN ('1','11','12','13','14')
    OR ethnicity_2 IN ('1','11','12','13','14')
    OR ethnicity_3 IN ('1','11','12','13','14')
    OR ethnicity_4 IN ('1','11','12','13','14')
    OR ethnicity_5 IN ('1','11','12','13','14')
  ) as is_hispanic,
  -- Check if multi-racial (using same logic as create_de_hmda_table.sql)
  (
    (ethnicity_1 NOT IN ('1','11','12','13','14') OR ethnicity_1 IS NULL)
    AND (ethnicity_2 NOT IN ('1','11','12','13','14') OR ethnicity_2 IS NULL)
    AND (ethnicity_3 NOT IN ('1','11','12','13','14') OR ethnicity_3 IS NULL)
    AND (ethnicity_4 NOT IN ('1','11','12','13','14') OR ethnicity_4 IS NULL)
    AND (ethnicity_5 NOT IN ('1','11','12','13','14') OR ethnicity_5 IS NULL)
    AND (
      SELECT COUNT(DISTINCT main_cat)
      FROM UNNEST([
        CASE WHEN race_1 IS NOT NULL AND race_1 != '' AND race_1 NOT IN ('6','7','8') 
             THEN CASE WHEN race_1 = '1' THEN '1'
                       WHEN race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN race_1 = '3' THEN '3'
                       WHEN race_1 IN ('4','41','42','43','44') THEN '4'
                       WHEN race_1 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN race_2 IS NOT NULL AND race_2 != '' AND race_2 NOT IN ('6','7','8') 
             THEN CASE WHEN race_2 = '1' THEN '1'
                       WHEN race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN race_2 = '3' THEN '3'
                       WHEN race_2 IN ('4','41','42','43','44') THEN '4'
                       WHEN race_2 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN race_3 IS NOT NULL AND race_3 != '' AND race_3 NOT IN ('6','7','8') 
             THEN CASE WHEN race_3 = '1' THEN '1'
                       WHEN race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN race_3 = '3' THEN '3'
                       WHEN race_3 IN ('4','41','42','43','44') THEN '4'
                       WHEN race_3 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN race_4 IS NOT NULL AND race_4 != '' AND race_4 NOT IN ('6','7','8') 
             THEN CASE WHEN race_4 = '1' THEN '1'
                       WHEN race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN race_4 = '3' THEN '3'
                       WHEN race_4 IN ('4','41','42','43','44') THEN '4'
                       WHEN race_4 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN race_5 IS NOT NULL AND race_5 != '' AND race_5 NOT IN ('6','7','8') 
             THEN CASE WHEN race_5 = '1' THEN '1'
                       WHEN race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN race_5 = '3' THEN '3'
                       WHEN race_5 IN ('4','41','42','43','44') THEN '4'
                       WHEN race_5 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END
      ]) AS main_cat
      WHERE main_cat IS NOT NULL
    ) >= 2
  ) as is_multi_racial
FROM test_cases
ORDER BY test_name;

-- ============================================================================
-- Expected Results:
-- ============================================================================
-- Test 1: Black + White
--   - distinct_main_categories: 2
--   - is_hispanic: FALSE
--   - is_multi_racial: TRUE ✓
--
-- Test 2: Multiple Asian subcategories
--   - distinct_main_categories: 1 (both map to category '2')
--   - is_hispanic: FALSE
--   - is_multi_racial: FALSE ✓ (correct - multiple subcategories of same race don't count)
--
-- Test 3: Hispanic + Black
--   - distinct_main_categories: 1
--   - is_hispanic: TRUE
--   - is_multi_racial: FALSE ✓ (correct - Hispanic takes precedence)
--
-- Test 4: Black + White + Asian
--   - distinct_main_categories: 3
--   - is_hispanic: FALSE
--   - is_multi_racial: TRUE ✓
-- ============================================================================


