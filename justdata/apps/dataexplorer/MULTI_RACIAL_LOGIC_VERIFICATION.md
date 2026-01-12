# Multi-Racial Logic Verification

## Current Implementation Analysis

After reviewing the code, the multi-racial logic appears **CORRECT** and matches the NCRC methodology. Here's the verification:

### Multi-Racial Definition (from SQL template comments)
- **ONLY Non-Hispanic** + **2 or more DISTINCT main race categories**
- **CRITICAL**: You **CANNOT** be multi-racial and Hispanic. Only non-Hispanic people can be multi-racial.
- **CRITICAL**: Multiple subcategories of the same race do **NOT** count as multi-racial. They all map to the same main category, so COUNT(DISTINCT) = 1, meaning they are just that race, NOT multi-racial.
  - **Asian**: Multiple Asian subcategories (e.g., Chinese '21', Japanese '22', Filipino '23') all map to main category '2' (Asian)
  - **HoPI**: Multiple HoPI subcategories (e.g., Native Hawaiian '41', Guamanian '42', Samoan '43') all map to main category '4' (HoPI)
- **NOTE**: Hispanic borrowers are counted in Hispanic category, **NOT** in Multi-Racial
- **Main race categories**: 
  - 1 = Native American
  - 2 = Asian (includes 2, 21-27) - **All Asian subcategories map to '2'**
  - 3 = Black
  - 4 = HoPI (includes 4, 41-44) - **All HoPI subcategories map to '4'**
  - 5 = White

### Logic Verification

#### ✅ Multi-Racial Flag (`is_multi_racial`)
```sql
-- 1. Check NOT Hispanic (all 5 ethnicity fields) - REQUIRED FIRST
--    If ANY ethnicity field indicates Hispanic, is_multi_racial = FALSE
(h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)

-- 2. Count DISTINCT main race categories from all 5 race fields
AND (
  SELECT COUNT(DISTINCT main_cat)
  FROM UNNEST([
    -- Maps each race code to main category ('1', '2', '3', '4', '5')
    -- Then counts distinct categories
  ]) AS main_cat
  WHERE main_cat IS NOT NULL
) >= 2
```

**This is CORRECT** ✓
- The first condition ensures that if ANY ethnicity field indicates Hispanic, `is_multi_racial` will be FALSE
- This enforces: **You cannot be multi-racial and Hispanic. Only non-Hispanic people can be multi-racial.**

#### ✅ Individual Race Flags (e.g., `is_black`)
```sql
-- 1. Check NOT Hispanic
-- 2. First valid race code matches category (using COALESCE)
COALESCE(race_1, race_2, race_3, race_4, race_5) = '3'  -- For Black

-- 3. Exclude multi-racial (count distinct main categories < 2)
AND (
  SELECT COUNT(DISTINCT main_cat)
  FROM UNNEST([...]) AS main_cat
  WHERE main_cat IS NOT NULL
) < 2
```

**This is CORRECT** ✓ - Multi-racial borrowers are excluded from individual race categories

### Test Cases

| Scenario | Race Codes | Main Categories | Expected Result |
|----------|-----------|-----------------|-----------------|
| Black + White | race_1='3', race_2='5' | ['3', '5'] | is_multi_racial=TRUE, is_black=FALSE, is_white=FALSE ✓ |
| **Multiple Asian subcategories** | race_1='21' (Chinese), race_2='22' (Japanese) | ['2', '2'] → ['2'] | **is_multi_racial=FALSE, is_asian=TRUE ✓** (Multiple Asian subcategories map to same main category '2', so NOT multi-racial) |
| Hispanic + Black | ethnicity_1='1', race_1='3' | ['3'] | is_hispanic=TRUE, is_black=FALSE, is_multi_racial=FALSE ✓ (Hispanic takes precedence, cannot be multi-racial) |
| Black + White + Asian | race_1='3', race_2='5', race_3='2' | ['3', '5', '2'] | is_multi_racial=TRUE ✓ |
| **Multiple Asian subcategories (3)** | race_1='21', race_2='22', race_3='23' | ['2', '2', '2'] → ['2'] | **is_multi_racial=FALSE, is_asian=TRUE ✓** (All map to category '2', so NOT multi-racial) |
| **Multiple HoPI subcategories** | race_1='41' (Native Hawaiian), race_2='42' (Guamanian) | ['4', '4'] → ['4'] | **is_multi_racial=FALSE, is_hopi=TRUE ✓** (All map to category '4', so NOT multi-racial) |

### Potential Issue Found

However, I notice one potential edge case that should be verified:

**What if someone has:**
- race_1 = '3' (Black)
- race_2 = '3' (Black again - duplicate)
- race_3 = '5' (White)

**Current logic:**
- Main categories from UNNEST: ['3', '3', '5'] → DISTINCT: ['3', '5'] → COUNT = 2
- Result: is_multi_racial = TRUE ✓ (correct - Black + White)

**This is correct!** The DISTINCT ensures duplicates don't matter.

### Verification Query

Run this query to verify the logic works correctly:

```sql
-- Test the multi-racial logic with real data
SELECT 
  COUNTIF(is_multi_racial) as multi_racial_count,
  COUNTIF(is_black) as black_count,
  COUNTIF(is_asian) as asian_count,
  COUNTIF(is_white) as white_count,
  COUNTIF(is_hispanic) as hispanic_count,
  COUNT(*) as total_loans,
  -- Verify no overlap: multi-racial should NOT be in individual categories
  COUNTIF(is_multi_racial AND is_black) as multi_racial_and_black,  -- Should be 0
  COUNTIF(is_multi_racial AND is_white) as multi_racial_and_white,  -- Should be 0
  COUNTIF(is_multi_racial AND is_hispanic) as multi_racial_and_hispanic  -- Should be 0
FROM `hdma1-242116.justdata.de_hmda`
WHERE activity_year = 2024
  AND action_taken = '1'
LIMIT 1000;  -- Test on sample first
```

**Expected Results:**
- `multi_racial_and_black` = 0 (multi-racial should not be counted as Black)
- `multi_racial_and_white` = 0 (multi-racial should not be counted as White)
- `multi_racial_and_hispanic` = 0 (multi-racial should not be counted as Hispanic) **CRITICAL: This MUST be 0 - you cannot be multi-racial and Hispanic**

### Conclusion

The multi-racial logic appears **CORRECT** based on:
1. ✅ Matches the SQL template methodology exactly
2. ✅ Uses COUNT(DISTINCT main_cat) to count distinct main race categories
3. ✅ **CRITICAL**: Excludes Hispanic borrowers from multi-racial (checks ALL 5 ethnicity fields are NOT Hispanic FIRST)
4. ✅ Excludes multi-racial from individual race categories
5. ✅ **CRITICAL**: Handles multiple subcategories of same race correctly - **Multiple subcategories of the same race all map to the same main category, so COUNT(DISTINCT) = 1, meaning they are NOT multi-racial, just that race**
   - **Asian**: Multiple Asian subcategories (e.g., Chinese '21', Japanese '22', Filipino '23') all map to main category '2' (Asian)
   - **HoPI**: Multiple HoPI subcategories (e.g., Native Hawaiian '41', Guamanian '42', Samoan '43') all map to main category '4' (HoPI)
6. ✅ **Enforces**: You cannot be multi-racial and Hispanic. Only non-Hispanic people can be multi-racial.
7. ✅ **Enforces**: People who select multiple subcategories of the same race (e.g., multiple Asian categories or multiple HoPI categories) are NOT multi-racial, just that race.

**However**, I recommend:
1. **Run the verification query** above on a sample of real data
2. **Compare results** with current SQL template output
3. **Test edge cases** (duplicate race codes, etc.)

If you find any discrepancies, we can adjust the logic.

