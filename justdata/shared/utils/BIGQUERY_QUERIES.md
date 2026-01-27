# BigQuery Queries Documentation

This document contains the exact BigQuery queries used across all applications to ensure consistency.

## Data Source
**Table**: `geo.cbsa_to_county`

**Key Columns**:
- `state` - State abbreviation (e.g., "CA", "NY", "TX")
- `county_state` - Full county name with state (e.g., "Los Angeles County, California")
- `cbsa_code` - Core-Based Statistical Area code
- `cbsa_name` - Metro area name

---

## 1. Get All Counties

**Purpose**: Fetch all unique counties for dropdown population

```sql
SELECT DISTINCT county_state 
FROM geo.cbsa_to_county 
WHERE county_state IS NOT NULL
ORDER BY county_state
```

**Returns**: 3,247 counties
**Used in**: 
- `branchsight/data_utils.py` - `get_available_counties()`
- Fallback data in `shared/utils/geo_data.py` - `get_fallback_counties()`

---

## 2. Get All States

**Purpose**: Fetch all unique states for dropdown population

```sql
SELECT DISTINCT state
FROM geo.cbsa_to_county 
WHERE state IS NOT NULL
ORDER BY state
```

**Returns**: 52 states/territories (50 states + DC + PR)
**Used in**: 
- `branchsight/data_utils.py` - `get_available_states()`

**States**: Alabama, Alaska, Arizona, Arkansas, California, Colorado, Connecticut, Delaware, District of Columbia, Florida, Georgia, Hawaii, Idaho, Illinois, Indiana, Iowa, Kansas, Kentucky, Louisiana, Maine, Maryland, Massachusetts, Michigan, Minnesota, Mississippi, Missouri, Montana, Nebraska, Nevada, New Hampshire, New Jersey, New Mexico, New York, North Carolina, North Dakota, Ohio, Oklahoma, Oregon, Pennsylvania, Puerto Rico, Rhode Island, South Carolina, South Dakota, Tennessee, Texas, Utah, Vermont, Virginia, Washington, West Virginia, Wisconsin, Wyoming

---

## 3. Get Counties by State

**Purpose**: Filter counties when a user selects a specific state

```sql
SELECT DISTINCT county_state
FROM geo.cbsa_to_county 
WHERE state = '{STATE_CODE}'
ORDER BY county_state
```

**Parameters**:
- `{STATE_CODE}` - Two-letter state abbreviation (e.g., "CA", "NY")

**Example**:
```sql
SELECT DISTINCT county_state
FROM geo.cbsa_to_county 
WHERE state = 'CA'
ORDER BY county_state
```

**Used in**: 
- `branchsight/data_utils.py` - `expand_state_to_counties(state_code)`
- All apps - `/counties-by-state/<state_code>` endpoint

---

## 4. Get All Metro Areas (CBSAs)

**Purpose**: Fetch all Core-Based Statistical Areas for metro area selection

```sql
SELECT DISTINCT 
    cbsa_code as code,
    cbsa_name as name
FROM geo.cbsa_to_county 
WHERE cbsa_code IS NOT NULL AND cbsa_name IS NOT NULL
ORDER BY cbsa_name
```

**Used in**: 
- `branchsight/data_utils.py` - `get_available_metro_areas()`

---

## Fallback Data

When BigQuery is unavailable (e.g., local development, API limits), the applications use fallback data from `shared/utils/geo_data.py`:

- **52 states** with full names and codes
- **3,247 counties** - complete list matching BigQuery

This ensures the applications work reliably even without BigQuery access.

---

## Query Performance Notes

1. All queries use `DISTINCT` to avoid duplicates
2. `ORDER BY` ensures consistent, alphabetical sorting
3. `WHERE ... IS NOT NULL` filters out any null/invalid entries
4. Queries are fast because `geo.cbsa_to_county` is a reference table (~3,247 rows)

---

## Data Freshness

The fallback county list was last updated: **November 19, 2025**

To update the fallback list, run:
```bash
cd /Users/jadedlebi/justdata
python3 scripts/update_geo_fallback.py
```

This will query BigQuery and regenerate `shared/utils/geo_data.py` with the latest data.

