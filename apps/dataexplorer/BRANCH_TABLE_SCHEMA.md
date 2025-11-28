# Branch Table Schema Reference

## ✅ VERIFIED SCHEMAS (Checked via BigQuery INFORMATION_SCHEMA)

## Table: `branches.sod_legacy` (Years < 2025)

### Verified Column Names (25 total):
- `year` - Year (STRING)
- `geoid5` - 5-digit FIPS county code (STRING)
- `rssd` - RSSD ID (STRING)
- `bank_name` - Bank name (STRING)
- `branch_name` - Branch name (STRING)
- `deposits_000s` - Deposits in thousands (INT64)
- `br_lmi` - Low-to-moderate income tract flag (INT64) ✅
- `br_minority` - Majority-minority tract flag (INT64) ✅
- `geoid` - Census tract identifier (STRING) ✅
- `uninumbr` - Unique branch number (STRING)
- Plus: address, city, county, state, zip, latitude, longitude, etc.

### Key Facts:
- ✅ **HAS `br_minority`** - Use this (NOT `cr_minority`)
- ✅ **HAS `geoid`** - Use this (NOT `census_tract`)
- ❌ **NO `cr_minority` column**
- ❌ **NO `census_tract` column**

## Table: `branches.sod25` (Year >= 2025)

### Verified Column Names (25 total):
- `year` - Year (STRING)
- `geoid5` - 5-digit FIPS county code (STRING)
- `rssd` - RSSD ID (STRING)
- `bank_name` - Bank name (STRING)
- `branch_name` - Branch name (STRING)
- `deposits_000s` - Deposits in thousands (INT64)
- `br_lmi` - Low-to-moderate income tract flag (INT64) ✅
- `br_minority` - Majority-minority tract flag (INT64) ✅
- `geoid` - Census tract identifier (STRING) ✅
- `uninumbr` - Unique branch number (STRING)
- Plus: address, city, county, state, zip, latitude, longitude, etc.

### Key Facts:
- ✅ **HAS `br_minority`** - Use this (NOT `cr_minority`) - **SAME as sod_legacy**
- ✅ **HAS `geoid`** - Use this (NOT `census_tract`) - **SAME as sod_legacy**
- ❌ **NO `cr_minority` column**
- ❌ **NO `census_tract` column**

## Table: `geo.census` (Census Tract Data)

### Verified Column Names (30 total):
- `geoid` - Full 11-digit census tract identifier (STRING) ✅
- `income_level` - Income level (1=low, 2=moderate, 3=middle, 4=upper) (INT64) ✅
- `total_persons` - Total population (INT64) ✅
- `total_white` - White population (INT64) ✅
- `census_tract_number` - Tract number (STRING) - but use `geoid` instead
- Plus: year, msamd, state_code, county_code, etc.

### Key Facts:
- ✅ **HAS `geoid`** - 11-digit identifier (use for joining)
- ✅ **HAS `income_level`** - For income tract categorization
- ✅ **HAS `total_persons` and `total_white`** - For minority percentage calculation
- ❌ **NO `census_tract` column** (has `census_tract_number` but use `geoid` instead)

## Query Pattern

When querying both tables, use:

```sql
WITH branch_data AS (
    -- sod_legacy: Use br_minority and geoid
    SELECT 
        year, geoid5, rssd, bank_name, branch_name, deposits_000s, 
        br_lmi, br_minority as cr_minority, geoid as census_tract
    FROM `project.branches.sod_legacy`
    WHERE ...
    UNION ALL
    -- sod25: Use br_minority and geoid (SAME as sod_legacy)
    SELECT 
        year, geoid5, rssd, bank_name, branch_name, deposits_000s, 
        br_lmi, br_minority as cr_minority, geoid as census_tract
    FROM `project.branches.sod25`
    WHERE ...
)
```

**IMPORTANT**: Both tables use the SAME column names (verified via BigQuery):
- Both use `br_minority` (NOT `cr_minority`) ✅ VERIFIED
- Both use `geoid` (NOT `census_tract`) ✅ VERIFIED

**Census Table:**
- Uses `geoid` (11-digit identifier) for joining
- Extract tract portion: `SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 6, 6)` gives last 6 digits

## Join Logic with Census Table

The census table's `geoid` is an 11-digit identifier:
- First 2 digits: State code
- Next 3 digits: County code (positions 3-5)
- Last 6 digits: Tract code (positions 6-11)

Join pattern:
```sql
LEFT JOIN `geo.census` c
    ON LPAD(CAST(b.geoid5 AS STRING), 5, '0') = SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 1, 5)  -- County match
    AND LPAD(CAST(b.geoid AS STRING), 6, '0') = SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 6, 6)  -- Tract match
```

Note: `b.geoid` from branch tables should be the tract portion (6 digits). If it's already 11 digits, adjust the join accordingly.

## Files Updated

1. ✅ `apps/dataexplorer/app.py` - All 3 query sections fixed
2. ✅ `apps/dataexplorer/query_builders.py` - Fixed sod25 section
3. ✅ `apps/dataexplorer/test_branch_query.py` - Updated test query
4. ✅ `apps/dataexplorer/BRANCH_TABLE_SCHEMA.md` - This file (verified schemas)

## Verification

Run `python apps/dataexplorer/test_branch_query.py` to verify queries work.

