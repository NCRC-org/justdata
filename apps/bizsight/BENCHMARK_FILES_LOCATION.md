# Benchmark Files Location and Verification

## Generated Files

The benchmark generation script successfully created:
- **52 state benchmark files** (01.json through 72.json, excluding missing FIPS codes)
- **1 national benchmark file** (national.json)
- **1 consolidated file** (benchmarks.json)

## File Locations

### Primary Location (Where Files Were Generated)
```
#JustData_Repo/apps/data/
├── 01.json
├── 02.json
├── ...
├── 72.json
├── national.json
└── benchmarks.json
```

### Verified Data

**National Benchmark:**
- Total Loans: 8,694,061
- Total Amount: $257,462,673

**State Benchmarks (Sample):**
- Alabama (01): 87,349 loans, $4,036,910
- Illinois (17): 305,794 loans, $10,365,869
- California (06): 1,371,070 loans, $32,195,696
- Texas (48): 800,731 loans, $26,179,917
- All 52 states/territories generated successfully

## Application Search Order

The application (`core.py`) searches for benchmark files in this order:
1. `apps/data/` (primary location - where files were generated)
2. `apps/bizsight/data/`
3. `#JustData_Repo/data/`
4. `#JustData_Repo/data/benchmarks/`
5. Falls back to BigQuery if files not found

## Backup Scripts

To backup files to multiple locations, run:
```powershell
python backup_benchmarks.py
```

Or from the repo root:
```powershell
python #JustData_Repo/backup_benchmarks.py
```

## Regenerating Benchmarks

If files are lost, regenerate with:
```powershell
python apps/bizsight/generate_benchmarks.py
```

This will query BigQuery and recreate all 52 state files plus the national file.

## File Format

Each state file contains:
```json
{
  "state_fips": "17",
  "year": 2024,
  "total_loans": 305794,
  "total_amount": 10365869.0,
  "pct_loans_under_100k": 93.86,
  "pct_loans_100k_250k": 3.28,
  "pct_loans_250k_1m": 2.85,
  "pct_loans_sb_under_1m": 57.07,
  "pct_loans_lmi_tract": 21.62,
  "pct_amount_under_100k": 37.72,
  "pct_amount_250k_1m": 45.96,
  "pct_amount_sb_under_1m": 32.61,
  "pct_amount_lmi_tract": 21.62,
  ...
}
```

## Last Generated

Files were generated on: 2025-01-27
All 52 state files + national file verified and valid.

