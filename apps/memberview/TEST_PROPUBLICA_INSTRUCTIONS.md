# Testing ProPublica API Matching

## Quick Test

To test matching 10 HubSpot companies with IRS Form 990 data:

### Option 1: Run the batch file
```bash
run_test.bat
```

### Option 2: Run Python directly
```bash
cd "#Cursor Agent Backups\MemberView_Standalone"
python test_propublica_simple.py
```

## What the Test Does

1. Loads 10 companies from HubSpot companies CSV
2. For each company, searches ProPublica API using:
   - Company name
   - City (if available)
   - State (if available)
3. Shows match results with:
   - EIN (if found)
   - Matched organization name
   - Location
   - Financial data (revenue, expenses)

## Expected Output

```
================================================================================
PROPUBLICA API MATCHING TEST - 10 COMPANIES
================================================================================

[1] Company Name
     City: City Name
     State: ST
     MATCH: Matched Organization Name
     EIN: 12-3456789
     Location: City, ST
     Revenue: $1,234,567
     Expenses: $1,000,000

[2] Another Company
     NO MATCH

...

SUMMARY
================================================================================
Matched: 7/10 (70.0%)
```

## Notes

- The API has rate limiting (0.6 seconds between requests)
- Some companies may not be nonprofits (won't have Form 990)
- Name matching uses fuzzy logic with city/state filtering
- Results are shown in real-time

