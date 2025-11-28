# ProPublica API Matching Test Results

## Test Setup

- **Date**: 2025-01-27
- **Companies Tested**: 10
- **Matching Method**: Company name + city + state
- **API**: ProPublica Nonprofit Explorer API v2

## How to Run the Test

```bash
cd "#Cursor Agent Backups\MemberView_Standalone"
python test_propublica_simple.py
```

Or use the batch file:
```bash
run_test.bat
```

## Test Process

1. Loads 10 sample companies from HubSpot companies CSV
2. Extracts company name, city, and state
3. Searches ProPublica API for each company
4. Returns match results with EIN and financial data

## Expected Results

The test will show:
- ✅ **Matches Found**: Companies with IRS Form 990 records
- ❌ **No Match**: Companies not found (may not be nonprofits, or name mismatch)
- ⚠️ **Errors**: API errors or rate limiting issues

## Matching Logic

1. **Search by Name**: Uses company name as primary search term
2. **Filter by State**: If state available, filters results to that state
3. **Filter by City**: If city available, further filters by city
4. **Scoring**: Ranks matches by name similarity
5. **Best Match**: Returns highest scoring match

## Notes

- Not all HubSpot companies are nonprofits (may not have Form 990)
- Name variations may cause misses
- City/state filtering improves accuracy
- Rate limiting: 0.6 seconds between API calls

## Next Steps After Testing

1. Review match rate
2. Identify common issues (name variations, etc.)
3. Improve matching algorithm if needed
4. Integrate into MemberView data loading
5. Cache results to reduce API calls

