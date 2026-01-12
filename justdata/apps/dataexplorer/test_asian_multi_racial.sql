-- ============================================================================
-- Test: Multiple Race Subcategories Should NOT Be Multi-Racial
-- ============================================================================
-- This test verifies that people who select multiple subcategories of the same race
-- (e.g., Chinese '21' and Japanese '22' for Asian, or Native Hawaiian '41' and 
-- Guamanian '42' for HoPI) are counted as that race, NOT multi-racial
-- ============================================================================

WITH test_cases AS (
  SELECT 
    'Test 1: Chinese + Japanese (both Asian)' as test_name,
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
    'Test 2: Asian + Black (different categories)' as test_name,
    '21' as race_1,  -- Chinese (Asian)
    '3' as race_2,   -- Black
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
    'Test 3: Multiple Asian subcategories (3)' as test_name,
    '21' as race_1,  -- Chinese
    '22' as race_2,  -- Japanese
    '23' as race_3,  -- Filipino
    NULL as race_4,
    NULL as race_5,
    NULL as ethnicity_1,
    NULL as ethnicity_2,
    NULL as ethnicity_3,
    NULL as ethnicity_4,
    NULL as ethnicity_5
  UNION ALL
  SELECT 
    'Test 4: Multiple HoPI subcategories' as test_name,
    '41' as race_1,  -- Native Hawaiian
    '42' as race_2,  -- Guamanian or Chamorro
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
    'Test 5: HoPI + Black (different categories)' as test_name,
    '41' as race_1,  -- Native Hawaiian (HoPI)
    '3' as race_2,   -- Black
    NULL as race_3,
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
  -- Show what main categories are detected
  (
    SELECT ARRAY_AGG(DISTINCT main_cat ORDER BY main_cat)
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
  ) as distinct_main_category_count,
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
  ) as is_multi_racial,
  -- Check if Asian (first valid race code is Asian subcategory)
  (
    (ethnicity_1 NOT IN ('1','11','12','13','14') OR ethnicity_1 IS NULL)
    AND (ethnicity_2 NOT IN ('1','11','12','13','14') OR ethnicity_2 IS NULL)
    AND (ethnicity_3 NOT IN ('1','11','12','13','14') OR ethnicity_3 IS NULL)
    AND (ethnicity_4 NOT IN ('1','11','12','13','14') OR ethnicity_4 IS NULL)
    AND (ethnicity_5 NOT IN ('1','11','12','13','14') OR ethnicity_5 IS NULL)
    AND COALESCE(
      CASE WHEN race_1 IS NOT NULL AND race_1 != '' AND race_1 NOT IN ('6','7','8') 
           THEN race_1 ELSE NULL END,
      CASE WHEN race_2 IS NOT NULL AND race_2 != '' AND race_2 NOT IN ('6','7','8') 
           THEN race_2 ELSE NULL END,
      CASE WHEN race_3 IS NOT NULL AND race_3 != '' AND race_3 NOT IN ('6','7','8') 
           THEN race_3 ELSE NULL END,
      CASE WHEN race_4 IS NOT NULL AND race_4 != '' AND race_4 NOT IN ('6','7','8') 
           THEN race_4 ELSE NULL END,
      CASE WHEN race_5 IS NOT NULL AND race_5 != '' AND race_5 NOT IN ('6','7','8') 
           THEN race_5 ELSE NULL END
    ) IN ('2','21','22','23','24','25','26','27')
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
    ) < 2
  ) as is_asian,
  -- Check if HoPI (first valid race code is HoPI subcategory)
  (
    (ethnicity_1 NOT IN ('1','11','12','13','14') OR ethnicity_1 IS NULL)
    AND (ethnicity_2 NOT IN ('1','11','12','13','14') OR ethnicity_2 IS NULL)
    AND (ethnicity_3 NOT IN ('1','11','12','13','14') OR ethnicity_3 IS NULL)
    AND (ethnicity_4 NOT IN ('1','11','12','13','14') OR ethnicity_4 IS NULL)
    AND (ethnicity_5 NOT IN ('1','11','12','13','14') OR ethnicity_5 IS NULL)
    AND COALESCE(
      CASE WHEN race_1 IS NOT NULL AND race_1 != '' AND race_1 NOT IN ('6','7','8') 
           THEN race_1 ELSE NULL END,
      CASE WHEN race_2 IS NOT NULL AND race_2 != '' AND race_2 NOT IN ('6','7','8') 
           THEN race_2 ELSE NULL END,
      CASE WHEN race_3 IS NOT NULL AND race_3 != '' AND race_3 NOT IN ('6','7','8') 
           THEN race_3 ELSE NULL END,
      CASE WHEN race_4 IS NOT NULL AND race_4 != '' AND race_4 NOT IN ('6','7','8') 
           THEN race_4 ELSE NULL END,
      CASE WHEN race_5 IS NOT NULL AND race_5 != '' AND race_5 NOT IN ('6','7','8') 
           THEN race_5 ELSE NULL END
    ) IN ('4','41','42','43','44')
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
    ) < 2
  ) as is_hopi
FROM test_cases
ORDER BY test_name;

-- ============================================================================
-- Expected Results:
-- ============================================================================
-- Test 1: Chinese + Japanese (both Asian)
--   - distinct_main_categories: ['2'] (both map to category '2' = Asian)
--   - distinct_main_category_count: 1
--   - is_multi_racial: FALSE ✓ (correct - multiple Asian subcategories don't count)
--   - is_asian: TRUE ✓ (correct - they are Asian)
--
-- Test 2: Asian + Black (different categories)
--   - distinct_main_categories: ['2', '3'] (Asian and Black)
--   - distinct_main_category_count: 2
--   - is_multi_racial: TRUE ✓ (correct - 2 distinct main categories)
--   - is_asian: FALSE ✓ (correct - multi-racial, not just Asian)
--
-- Test 3: Multiple Asian subcategories (3)
--   - distinct_main_categories: ['2'] (all map to category '2' = Asian)
--   - distinct_main_category_count: 1
--   - is_multi_racial: FALSE ✓ (correct - multiple Asian subcategories don't count)
--   - is_asian: TRUE ✓ (correct - they are Asian)
--
-- Test 4: Multiple HoPI subcategories
--   - distinct_main_categories: ['4'] (both map to category '4' = HoPI)
--   - distinct_main_category_count: 1
--   - is_multi_racial: FALSE ✓ (correct - multiple HoPI subcategories don't count)
--   - is_hopi: TRUE ✓ (correct - they are HoPI)
--
-- Test 5: HoPI + Black (different categories)
--   - distinct_main_categories: ['4', '3'] (HoPI and Black)
--   - distinct_main_category_count: 2
--   - is_multi_racial: TRUE ✓ (correct - 2 distinct main categories)
--   - is_hopi: FALSE ✓ (correct - multi-racial, not just HoPI)
-- ============================================================================


