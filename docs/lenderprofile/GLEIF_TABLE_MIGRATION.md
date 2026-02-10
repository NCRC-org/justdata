# GLEIF Names Table Migration to JustData

## Summary

All GLEIF names data has been migrated from `hmda.lender_names_gleif` to `justdata.gleif_names`.

## Updated Files

### Analysis Scripts (Updated to use `justdata.gleif_names`)

1. **`apps/dataexplorer/data_utils.py`**
   - `get_all_lenders_with_lar_count()` - Updated JOIN to use `justdata.gleif_names`
   - `get_gleif_data_by_lei()` - Updated query to use `justdata.gleif_names`

2. **`apps/lenderprofile/test_all_apis.py`**
   - `get_gleif_from_bigquery()` - Updated query to use `justdata.gleif_names`

3. **`apps/dataexplorer/scripts/update_gleif_names_bulk.py`**
   - Updated to write directly to `justdata.gleif_names` (primary location)

### Files That Use GLEIF Data (Indirectly)

These files use the functions above, so they automatically benefit from the migration:

- `apps/dataexplorer/lender_analysis_core.py` - Uses `get_gleif_data_by_lei()`
- `apps/dataexplorer/area_analysis_processor.py` - Uses lender queries that JOIN with GLEIF

## Table Location

**New Location:** `hdma1-242116.justdata.gleif_names`

**Old Location (still exists):** `hdma1-242116.hmda.lender_names_gleif`

The old table is kept for backward compatibility but all new queries use the `justdata` location.

## Verification

Test that GLEIF lookups work:
```python
from apps.dataexplorer.data_utils import get_gleif_data_by_lei
result = get_gleif_data_by_lei('549300XY701IELCE5Q08')
# Should return GLEIF data from justdata.gleif_names
```

## Benefits

1. **Consolidated Data**: All analysis data in one dataset (`justdata`)
2. **Consistency**: Same dataset as credit union and optimized SOD data
3. **Performance**: Clustered with other analysis tables
4. **Maintainability**: Single source of truth for analysis data

