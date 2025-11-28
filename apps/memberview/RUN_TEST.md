# How to Run ProPublica Matching Test

## Quick Run

Double-click: `run_test_simple.bat`

Or from command line:
```bash
cd "#Cursor Agent Backups\MemberView_Standalone"
python analyze_and_test_propublica.py
```

## What It Does

1. **Schema Analysis**: Shows which fields are populated for most members
2. **Field Selection**: Identifies company name, city, and state fields
3. **ProPublica Test**: Tests 10 companies against IRS Form 990 data
4. **Results Summary**: Shows match rate and details

## Expected Output

The script will show:
- Schema analysis with field population percentages
- Which fields are used for matching (name, city, state)
- For each of 10 companies:
  - Company name, city, state
  - Match result (found/not found)
  - EIN and financial data if match found
- Summary with match rate

## Important Notes

**Many companies are FOR-PROFIT**:
- For-profit businesses don't file Form 990
- They won't appear in ProPublica database
- **Low match rate (20-40%) is EXPECTED and NORMAL**

Only nonprofits will have Form 990 records in ProPublica.

