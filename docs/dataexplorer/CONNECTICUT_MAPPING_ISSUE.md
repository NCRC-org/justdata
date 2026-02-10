# Connecticut Planning Region to County Mapping Issue

## Problem

Connecticut planning regions (2024) do NOT align 1:1 with legacy counties. Some planning regions span multiple counties:

### Actual Relationships (from `connecticut_county_mapper.py`):

1. **Capitol (09110)** → `['09003']` ✅ Single county: Hartford
2. **Greater Bridgeport (09120)** → `['09001']` ✅ Single county: Fairfield  
3. **Lower CT River Valley (09130)** → `['09007', '09011']` ❌ **SPANS TWO**: Middlesex + New London
4. **Naugatuck Valley (09140)** → `['09009', '09005']` ❌ **SPANS TWO**: New Haven + Litchfield
5. **Northeastern CT (09150)** → `['09013', '09015']` ❌ **SPANS TWO**: Tolland + Windham
6. **Northwest Hills (09160)** → `['09005']` ✅ Single county: Litchfield
7. **South Central (09170)** → `['09009', '09007']` ❌ **SPANS TWO**: New Haven + Middlesex
8. **Southeastern CT (09180)** → `['09011']` ✅ Single county: New London (assumed)
9. **Western CT (09190)** → `['09001', '09005']` ❌ **SPANS TWO**: Fairfield + Litchfield

### Current (Incorrect) Mapping:

The current implementation maps each planning region to a single "primary" county:

- 09130 → 09007 (Middlesex) - **LOSES New London data**
- 09140 → 09009 (New Haven) - **LOSES Litchfield data**
- 09150 → 09013 (Tolland) - **LOSES Windham data**
- 09170 → 09009 (New Haven) - **LOSES Middlesex data**
- 09190 → 09001 (Fairfield) - **LOSES Litchfield data**

## Impact

When 2024 HMDA data uses planning region codes that span multiple counties, mapping to a single county:
- **Loses data** from the secondary county
- **Creates incorrect aggregations** (loans from multiple counties counted as one)
- **Breaks time-series consistency** (2024 totals won't match 2022-2023 if you sum by county)

## Solution Options

### Option 1: Use Tract-Level Mapping (Most Accurate)
- Map planning region codes to all constituent counties
- For multi-county regions, we'd need to either:
  - Duplicate records (one per county) - but this would double-count
  - Use a UNION query to split by county - complex
  - Keep planning region as-is and map counties to regions for comparison

### Option 2: Keep Planning Regions Separate (Recommended)
- Don't normalize multi-county planning regions
- Keep them as separate entities
- Only normalize single-county planning regions
- This preserves data integrity but requires handling both systems

### Option 3: Use Census Tract Data
- Use tract-level HMDA data to determine which county each loan belongs to
- More accurate but requires tract-level queries (slower, more complex)

### Option 4: Proportional Allocation (Not Recommended)
- Split loans proportionally across counties
- Requires population/loan volume data
- Complex and potentially inaccurate

## Recommended Approach

**Option 2 Modified**: 
- For single-county planning regions (09110, 09120, 09160, 09180): Map to county ✅
- For multi-county planning regions (09130, 09140, 09150, 09170, 09190): 
  - **Option A**: Keep as planning region codes (don't normalize)
  - **Option B**: Map to the county with the largest share (requires data analysis)
  - **Option C**: Create a "virtual county" that represents the planning region

The challenge is that HMDA data in 2024 reports at the planning region level, so we can't determine which specific county each loan belongs to without tract-level data.

