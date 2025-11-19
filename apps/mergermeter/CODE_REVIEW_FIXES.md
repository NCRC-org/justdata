# Code Review and Fixes Applied

## Issues Found and Fixed

### 1. **Variable Scope Issues**
- **Fixed**: `USE_ORIGINAL_FUNCTIONS` variable initialization
  - **Location**: `excel_generator.py` line 19
  - **Issue**: Variable could be undefined if exception occurred during import
  - **Fix**: Initialize to `False` before conditional block

### 2. **Request Context Issues**
- **Fixed**: Accessing `request.form` in background thread
  - **Location**: `app.py` lines 335-337
  - **Issue**: Flask request context not available in background threads
  - **Fix**: Use `form_data` dictionary instead of `request.form`

### 3. **None Value Handling**
- **Fixed**: String operations on potentially None values
  - **Location**: `app.py` lines 132-141, 335-346
  - **Issue**: `.strip()` called on None values
  - **Fix**: Use `or ''` pattern: `(form_data.get('key') or '').strip()`

### 4. **Dictionary Deduplication**
- **Fixed**: Unhashable type error when deduplicating counties
  - **Location**: `app.py` lines 289-290
  - **Issue**: Dictionaries can't be added to sets
  - **Fix**: Created `deduplicate_counties()` function that handles both strings and dicts

### 5. **BigQuery Column References**
- **Fixed**: Missing `county_state` column in queries
  - **Location**: `query_builders.py`, `hhi_calculator.py`, `branch_assessment_area_generator.py`
  - **Issue**: Queries referenced `county_state` but didn't create it
  - **Fix**: Added `CONCAT(County, ', ', State) as county_state` to all relevant queries

### 6. **MSA Expansion with Dictionaries**
- **Fixed**: `.strip()` called on dictionary objects
  - **Location**: `county_mapper.py` line 309
  - **Issue**: `detect_and_expand_msa_names` tried to process dictionaries as strings
  - **Fix**: Skip dictionaries (they're already in correct format) and only process strings

### 7. **DataFrame Operations**
- **Fixed**: Potential errors with empty DataFrames and missing columns
  - **Location**: `hhi_calculator.py`, `branch_assessment_area_generator.py`, `excel_generator.py`
  - **Issue**: Accessing columns/rows without checking if they exist
  - **Fix**: Added checks for `.empty`, column existence, and `pd.notna()` checks

### 8. **JSON Parsing**
- **Fixed**: Better error handling for JSON parsing
  - **Location**: `app.py` lines 147-153
  - **Issue**: Generic `except:` clause and no type checking
  - **Fix**: Specific exception types and type checking before parsing

### 9. **Excel Column Width Calculation**
- **Fixed**: Potential errors when calculating column widths
  - **Location**: `excel_generator.py` lines 251-255
  - **Issue**: DataFrame operations could fail on empty or invalid data
  - **Fix**: Added try/except for ValueError and AttributeError

## Remaining Optional Import Warning

- **Location**: `excel_generator.py` line 24
- **Status**: Expected warning - optional import that may not exist
- **Action**: No action needed - this is handled gracefully with try/except

## Summary

All critical issues have been addressed:
- ✅ Variable scope issues fixed
- ✅ Request context issues fixed
- ✅ None value handling improved
- ✅ Dictionary deduplication working
- ✅ BigQuery queries fixed
- ✅ DataFrame operations protected
- ✅ Error handling improved

The codebase should now be more robust and handle edge cases better.



