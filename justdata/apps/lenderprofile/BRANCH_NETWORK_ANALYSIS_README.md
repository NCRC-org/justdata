# Branch Network Analysis System

## Overview

The Branch Network Analysis system tracks branch network changes over time for banks and credit unions, analyzing growth, shrinkage, and geographic reallocation patterns.

## Features

### Bank Branch Analysis (via BigQuery SOD)

- **Year-over-year comparison**: Tracks branch network size changes from 2021-2025
- **Closure/Opening detection**: Identifies which branches closed and opened each year
- **Geographic analysis**: Analyzes patterns by:
  - State
  - MSA/CBSA
  - City
- **Narrative generation**: Creates human-readable summaries like:
  > "The bank has been closing branches at a pace of approximately 100 per year, reducing from 5,200 branches in 2021 to 4,800 branches in 2025. Branch closures have been concentrated in: CA (45), NY (32), TX (28)."

### Credit Union Branch Analysis (via Call Reports)

- Processes credit union call report ZIP files (2021-2025)
- Loads branch data into BigQuery `credit_unions.cu_branches` table
- Supports same analysis capabilities as banks

## Usage

### Analyze Bank Branch Network

```bash
python apps/lenderprofile/branch_network_analyzer.py "Bank Name"
```

Example:
```bash
python apps/lenderprofile/branch_network_analyzer.py "Fifth Third Bank"
```

### Load Credit Union Call Reports

```bash
python apps/lenderprofile/scripts/load_cu_call_reports_to_bq.py
```

This processes all ZIP files in:
`C:\Users\jrichardson\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\call-report-data-*.zip`

## Architecture

### Components

1. **`branch_network_analyzer.py`**: Main analysis script
   - Resolves lender identifiers (RSSD, FDIC cert)
   - Fetches branch data for multiple years
   - Analyzes changes and generates reports

2. **`services/bq_branch_client.py`**: BigQuery client for SOD data
   - Queries `branches.sod`, `branches.sod_legacy`, `branches.sod25`
   - Handles RSSD type conversion (STRING in BigQuery)
   - Returns standardized branch data

3. **`scripts/load_cu_call_reports_to_bq.py`**: Credit union data loader
   - Extracts ZIP files
   - Parses CSV data
   - Loads into BigQuery tables

### Data Sources

**Banks:**
- BigQuery SOD tables: `branches.sod`, `branches.sod_legacy`, `branches.sod25`
- Identified by RSSD (Federal Reserve identifier)

**Credit Unions:**
- Call report ZIP files (NCUA)
- Loaded into: `credit_unions.cu_branches`, `credit_unions.cu_call_reports`
- Identified by CU_NUMBER and RSSD

## Example Output

```
Network Size by Year:
   2021: 1,110 branches
   2022: 1,090 branches
   2023: 1,082 branches
   2024: 1,078 branches
   2025: 1,097 branches

Network Size Changes (from total counts):
   2021 to 2022: -19 branches (-1.7%)
   2022 to 2023: -6 branches (-0.6%)
   2023 to 2024: -4 branches (-0.4%)
   2024 to 2025: +19 branches (+1.8%)

Geographic Patterns:
   Top 10 States for Closures:
    1. OH: 340 closures
    2. MI: 216 closures
    3. IL: 204 closures
    ...

NARRATIVE SUMMARY:
The bank's branch network has remained relatively stable, with 1,107 branches in 2021 
and 1,097 branches in 2025. Branch closures have been concentrated in: OH (340), MI (216), 
IL (204), FL (189), IN (137). New branch openings have been focused in: OH (300), FL (230), 
IL (202), MI (197), IN (126).
```

## Technical Notes

### RSSD Handling

- RSSD is stored as STRING in BigQuery SOD tables
- Query handles both padded (10 digits) and unpadded formats
- Example: RSSD `723112` matches both `723112` and `0000723112`

### Branch Matching

- Uses coordinates (latitude/longitude) as primary key when available
- Falls back to address + city + state + ZIP
- Rounds coordinates to 4 decimal places (~11 meters precision)

### Performance

- BigQuery queries are optimized with proper indexing
- Credit union data loaded in batches of 1,000 rows
- Timeout set to 120 seconds for large queries

## Future Enhancements

1. **Credit Union Analysis**: Extend branch network analyzer to support credit unions
2. **Visualization**: Add maps showing branch footprint changes
3. **Trend Prediction**: Use historical data to predict future trends
4. **Multi-institution Comparison**: Compare branch strategies across institutions

