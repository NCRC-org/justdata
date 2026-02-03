# SQL Template Update Summary

## Changes Made to `mortgage_report.sql`

### ✅ 1. Updated FROM Clause
**Before:**
```sql
FROM hmda.hmda h
LEFT JOIN `shared.census` ct_tract ...
LEFT JOIN shared.cbsa_to_county c ...
LEFT JOIN hmda.lenders18 l ...
```

**After:**
```sql
FROM `hdma1-242116.justdata.de_hmda` h
-- No joins needed! Everything is already in de_hmda
```

### ✅ 2. Simplified SELECT Columns
**Before:**
- Complex COALESCE for geoid5 normalization
- MAX(l.respondent_name) from join
- MAX(l.type_name) from join

**After:**
- `h.geoid5` (already normalized)
- `h.county_state` (already joined)
- `MAX(h.lender_name)` (already joined)
- `MAX(h.lender_type)` (already joined)

### ✅ 3. Replaced Race/Ethnicity Calculations
**Before:** ~400 lines of complex CASE statements with nested subqueries

**After:** Simple COUNTIF() statements
```sql
COUNTIF(h.is_hispanic) as hispanic_originations
COUNTIF(h.is_black) as black_originations
COUNTIF(h.is_asian) as asian_originations
COUNTIF(h.is_white) as white_originations
COUNTIF(h.is_native_american) as native_american_originations
COUNTIF(h.is_hopi) as hopi_originations
COUNTIF(h.is_multi_racial) as multi_racial_originations
```

### ✅ 4. Replaced Income Category Calculations
**Before:** Complex calculations with income/median comparisons

**After:** Simple COUNTIF() statements
```sql
COUNTIF(h.is_lmib) as lmib_originations
COUNTIF(h.is_low_income_borrower) as low_income_borrower_originations
COUNTIF(h.is_moderate_income_borrower) as moderate_income_borrower_originations
COUNTIF(h.is_middle_income_borrower) as middle_income_borrower_originations
COUNTIF(h.is_upper_income_borrower) as upper_income_borrower_originations
```

### ✅ 5. Replaced Tract Category Calculations
**Before:** Complex CASE statements with tract income comparisons

**After:** Simple COUNTIF() statements
```sql
COUNTIF(h.is_lmict) as lmict_originations
COUNTIF(h.is_low_income_tract) as low_income_tract_originations
COUNTIF(h.is_moderate_income_tract) as moderate_income_tract_originations
COUNTIF(h.is_middle_income_tract) as middle_income_tract_originations
COUNTIF(h.is_upper_income_tract) as upper_income_tract_originations
COUNTIF(h.is_mmct) as mmct_originations
```

### ✅ 6. Replaced Demographic Data Check
**Before:** Complex CASE with ethnicity and race checks

**After:**
```sql
COUNTIF(h.has_demographic_data) as loans_with_demographic_data
```

### ✅ 7. Updated WHERE Clause
**Before:**
```sql
WHERE c.county_state = @county
    AND h.activity_year = @year
```

**After:**
```sql
WHERE h.county_state = @county
    AND CAST(h.activity_year AS INT64) = @year
```

## Results

- **File size:** Reduced from ~650 lines to ~110 lines (83% reduction!)
- **Query performance:** Expected 5-10x faster
- **Query cost:** Expected 5-10x lower
- **Maintainability:** Much easier to read and maintain

## Next Steps

1. ✅ Run verification queries (see `verify_de_hmda.sql`)
2. ⏳ Test the updated SQL template with a real query
3. ⏳ Compare results with previous version to ensure accuracy
4. ⏳ Monitor query performance improvements

