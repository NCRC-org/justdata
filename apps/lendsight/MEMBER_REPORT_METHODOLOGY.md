# Member Report Methodology - Applied to LendSight

## Overview
LendSight should pull much of the same data and use similar analysis methods as the Member Report system. The Member Report is used for custom requests, but the functions and queries are very similar.

## Race and Ethnicity Classification Methodology

### Key Principle: COALESCE Function
The COALESCE function is used to find the **FIRST valid race code** from `applicant_race_1` through `applicant_race_5`, checking in order.

### Step-by-Step Process

1. **First: Check for Hispanic Ethnicity**
   - Check if ANY ethnicity field (`applicant_ethnicity_1` through `applicant_ethnicity_5`) indicates Hispanic
   - Hispanic codes: `'1'`, `'11'`, `'12'`, `'13'`, `'14'`
   - If ANY ethnicity field has these codes, classify as Hispanic

2. **If NOT Hispanic: Use COALESCE for Race**
   - Only classify by race if the applicant is NOT Hispanic
   - Use COALESCE to find the first valid race code from race_1 through race_5
   - Valid race codes: Must be NOT NULL, not empty string, and NOT IN ('6','7','8')
     - Code '6' = "Not provided"
     - Code '7' = "Not applicable"  
     - Code '8' = "No co-applicant"
   - COALESCE checks in order: race_1, then race_2, then race_3, then race_4, then race_5
   - Returns the first non-NULL, non-empty, valid race code found

3. **Race Classifications**
   - **Black**: First valid race code = `'3'`
   - **Asian**: First valid race code IN (`'2'`, `'21'`, `'22'`, `'23'`, `'24'`, `'25'`, `'26'`, `'27'`)
   - **White**: First valid race code = `'5'`
   - **Native American**: First valid race code = `'1'`
   - **HoPI (Hawaiian/Pacific Islander)**: First valid race code IN (`'4'`, `'41'`, `'42'`, `'43'`, `'44'`)

### SQL Pattern Example

```sql
-- Hispanic check
CASE 
    WHEN h.applicant_ethnicity_1 IN ('1','11','12','13','14')
        OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
        OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
        OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
        OR h.applicant_ethnicity_5 IN ('1','11','12','13','14')
    THEN 1 ELSE 0 
END as is_hispanic,

-- Black (only if NOT Hispanic)
CASE 
    WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
        AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
        AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
        AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
        AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
        AND COALESCE(
            CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
                 THEN h.applicant_race_1 ELSE NULL END,
            CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
                 THEN h.applicant_race_2 ELSE NULL END,
            CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
                 THEN h.applicant_race_3 ELSE NULL END,
            CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
                 THEN h.applicant_race_4 ELSE NULL END,
            CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
                 THEN h.applicant_race_5 ELSE NULL END
        ) = '3'
    THEN 1 ELSE 0 
END as is_black,
```

## Income Metrics

### LMIB (Low-to-Moderate Income Borrowers)
- Based on applicant income relative to MSA/MD median family income
- Formula: `(income * 1000) / ffiec_msa_md_median_family_income * 100 <= 80.0`
- Income is stored in thousands, so multiply by 1000
- Must have both income and median income data

### LMICT (Low-to-Moderate Income Census Tracts)
- Based on tract income as percentage of MSA/MD median
- Formula: `tract_to_msa_income_percentage <= 80`
- Uses the `tract_to_msa_income_percentage` field directly

## Redlining Metrics

### MMCT (Majority-Minority Census Tracts)
- Tracts where minority population is > 50%
- Formula: `tract_minority_population_percent > 50`
- Uses the `tract_minority_population_percent` field directly

## Demographic Data Availability

### has_demographic_data Flag
- Check if loan has usable demographic data
- Must have either:
  - Hispanic ethnicity (codes 1, 11-14) in ANY ethnicity field, OR
  - Explicit race selection (codes 1-5, 21-27, 41-44) in ANY race field
- Excludes codes 6, 7, 8 (not provided, not applicable, no co-applicant)

## Standard HMDA Filters

All queries use these standard filters:
- `action_taken = '1'` - Originations only
- `loan_purpose = '1'` - Home purchase
- `occupancy_type = '1'` - Owner-occupied
- `reverse_mortgage != '1'` - Exclude reverse mortgages
- `construction_method = '1'` - Site-built
- `total_units IN ('1', '2', '3', '4')` - 1-4 units

## Geographic Identifiers

- `county_code` in HMDA is already a 5-digit FIPS code (e.g., '24031')
- This is the same as `geoid5` in the geo tables
- Join using: `CAST(h.county_code AS STRING) = CAST(c.geoid5 AS STRING)`

## Lender Information

- Lender names come from `hmda.lenders18` table
- Join using LEI: `h.lei = l.lei`
- Select: `MAX(l.respondent_name) as lender_name`

## References

- Member Report queries: `C:\DREAM\3_Member_Report\queries\`
- Example queries:
  - `tampa_market_query.py` - Market overview with COALESCE methodology
  - `montgomery_market_query.py` - County-level analysis
  - `member_report_queries.py` - General query builder

