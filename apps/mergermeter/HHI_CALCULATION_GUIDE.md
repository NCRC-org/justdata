# HHI (Herfindahl-Hirschman Index) Calculation Guide

## Overview

The HHI calculator measures deposit market concentration before and after a bank merger. HHI is calculated for each county where both the acquirer and target banks have branch locations.

## HHI Formula

```
HHI = Σ(market_share_i)² × 10,000
```

Where:
- `market_share_i` = Each bank's share of total deposits in the county
- HHI ranges from 0 to 10,000

## Concentration Levels

- **HHI < 1,500**: Low Concentration (Competitive Market)
- **HHI 1,500-2,500**: Moderate Concentration
- **HHI > 2,500**: High Concentration

## Usage

### In the Merger Analysis

When implementing the `analyze()` function in `app.py`, include HHI calculation:

```python
from .hhi_calculator import calculate_hhi_by_county

# Get assessment area counties (GEOID5 codes)
assessment_area_geoids = [...]  # List of 5-digit GEOID5 strings

# Get bank RSSD IDs
acquirer_rssd = request.form.get('acquirer_rssd')
target_rssd = request.form.get('target_rssd')

# Calculate HHI for each county
hhi_df = calculate_hhi_by_county(
    county_geoids=assessment_area_geoids,
    acquirer_rssd=acquirer_rssd,
    target_rssd=target_rssd,
    year=2025
)

# Add to Excel export
# When saving Excel file, add hhi_df as a new sheet named "HHI Analysis"
```

### Excel Sheet Structure

The HHI Analysis sheet will contain:

| Column | Description |
|--------|-------------|
| County, State | County name and state |
| GEOID5 | 5-digit county FIPS code |
| Pre-Merger HHI | HHI before merger (banks separate) |
| Post-Merger HHI | HHI after merger (banks combined) |
| HHI Change | Difference (Post - Pre) |
| Pre-Merger Concentration | Concentration level before merger |
| Post-Merger Concentration | Concentration level after merger |
| Total Deposits (Pre-Merger) | Total deposits in county before merger |
| Total Deposits (Post-Merger) | Total deposits in county after merger |

### Notes

1. **Only counties with both banks**: HHI is only calculated for counties where both the acquirer and target banks have branch locations.

2. **Deposit data source**: Uses `branches.sod25` table with `deposits_000s` field (converted to actual deposits by multiplying by 1,000).

3. **Pre-merger calculation**: All banks are treated as separate entities, including the acquirer and target.

4. **Post-merger calculation**: Acquirer and target deposits are combined into a single merged entity, then HHI is recalculated.

5. **All banks included**: The calculation includes ALL banks with deposits in the county, not just the two merging banks.

## Example Output

```
County, State          | GEOID5 | Pre-Merger HHI | Post-Merger HHI | HHI Change
Hillsborough, Florida  | 12057  | 1,234.56       | 1,456.78        | +222.22
Pinellas, Florida      | 12103  | 2,345.67       | 2,567.89        | +222.22
```

## Integration Points

1. **Branch Analysis**: HHI calculation requires deposit data from branch analysis
2. **Excel Export**: Add HHI sheet when generating Excel report
3. **Web Report**: HHI sheet will automatically appear in web report viewer (via `/report-data` endpoint)

