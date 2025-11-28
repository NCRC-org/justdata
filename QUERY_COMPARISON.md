# Query Comparison: Tableau vs Flask App

## Key Differences Found:

### 1. **ACTION_TAKEN Filter** ⚠️ CRITICAL DIFFERENCE
- **Tableau**: `action_taken = 1` (originations only)
- **Flask App**: `action_taken IN ('1', '2', '3', '4', '5')` (ALL applications)
- **Impact**: Flask app is counting ALL applications, not just originations. This will make numbers MUCH higher.

### 2. **REVERSE MORTGAGE Filter**
- **Tableau**: `CASE WHEN (hmda.reverse_mortgage IN ('1', '1111')) THEN FALSE ELSE TRUE END`
  - Excludes both '1' AND '1111'
- **Flask App**: `(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')`
  - Only excludes '1', includes '1111'
- **Impact**: Flask app includes more reverse mortgages (those with value '1111')

### 3. **LOAN_PURPOSE Filter**
- **Tableau**: NO filter - counts ALL loan purposes
- **Flask App**: `loan_purpose IN ('1', '2', '4', '31', '32')`
  - Only counts specific purposes
- **Impact**: Flask app excludes some loan purposes that Tableau includes

### 4. **GEOGRAPHY Filtering**
- **Tableau**: Uses CBSA join: `INNER JOIN cbsa_to_county ON (hmda.county_code = cbsa_to_county.geoid5) WHERE cbsa_to_county.cbsa = 'Abilene, TX'`
- **Flask App**: Direct county codes: `LPAD(CAST(h.county_code AS STRING), 5, '0') IN ('48059', '48253', '48441')`
- **Impact**: Should be similar if the county codes match the CBSA, but join method differs

### 5. **DEDUPLICATION**
- **Tableau**: NO deduplication - just counts rows with `SUM(CAST(1 AS INT64))`
- **Flask App**: Uses `loan_key` deduplication with `ROW_NUMBER() OVER (PARTITION BY loan_key)`
- **Impact**: Flask app may have fewer counts if there are duplicate loans

### 6. **YEAR FILTER**
- **Tableau**: Excludes 2018, 2019: `CASE WHEN (hmda.activity_year IN ('2018', '2019')) THEN FALSE ELSE TRUE END`
- **Flask App**: `CAST(h.activity_year AS STRING) IN ('2020', '2021', '2022', '2023', '2024')`
- **Impact**: Should be the same (both exclude 2018-2019)

## Summary of Issues:

1. **MAJOR**: Flask app uses `action_taken IN ('1', '2', '3', '4', '5')` instead of `action_taken = '1'`
   - This is the PRIMARY reason numbers are too high
   - We already fixed this in config, but need to verify it's being used

2. **MEDIUM**: Reverse mortgage filter doesn't exclude '1111'
   - Tableau excludes both '1' and '1111'
   - Flask only excludes '1'

3. **MEDIUM**: Loan purpose filter differences
   - Tableau counts ALL purposes
   - Flask only counts specific purposes
   - This could make Flask numbers LOWER, not higher

4. **MINOR**: Deduplication differences
   - Tableau has no deduplication
   - Flask has deduplication
   - This could make Flask numbers LOWER, not higher

## Recommended Fixes:

1. ✅ Already fixed: Change `action_taken` to `['1']` only (originations)
2. ⚠️ Need to fix: Update reverse mortgage filter to exclude both '1' and '1111'
3. ⚠️ Need to decide: Should we remove loan_purpose filter to match Tableau?

