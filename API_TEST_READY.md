# ProPublica API Test - Ready to Run

## Issue Resolved

The PowerShell wrapper issue with apostrophes in the path has been addressed using the `C:\dream` symbolic link workaround.

## How to Run the Test

### Option 1: Batch File (Easiest)
Double-click or run:
```
RUN_API_TEST_FINAL.bat
```

This batch file:
- Uses the `C:\dream` symbolic link path (no apostrophe issues)
- Changes to the correct directory
- Runs the API test script
- Shows output in real-time

### Option 2: Manual Python Execution
Open Command Prompt (cmd.exe) and run:
```cmd
cd C:\dream\#JustData_Repo
python execute_inline.py
```

### Option 3: Using the Utility Script
```cmd
cd C:\dream
python utils\run_python_script.py #JustData_Repo\execute_inline.py
```

## What the Test Does

The test script (`execute_inline.py`) will:

1. **Test 3 sample EINs** from your data:
   - `46-5333729` - Center for Housing Economics
   - `82-3374968` - The Resiliency Collaborative Inc
   - `82-1125482` - City Fields

2. **Query ProPublica API** for each EIN

3. **Display results** showing:
   - Available fields from the API
   - Field categories (Basic Info, Address, Classification, Links, Other)
   - Summary of all unique fields available

4. **Save results** to `api_test_results.json`

## Expected Output

You should see output like:
```
================================================================================
PROPUBLICA API TEST - Executing Now
================================================================================

================================================================================
Testing EIN: 46-5333729
Organization: Center for Housing Economics
================================================================================

Requesting: https://projects.propublica.org/nonprofits/api/v2/search.json?q=46-5333729
✓ Success! Status: 200
Total Results: 1

✓ Found: Center For Housing Economics

Available Fields (XX total):
--------------------------------------------------------------------------------

Basic Info:
  • ein                : 465333729
  • name               : Center For Housing Economics
  • strein             : 46-5333729
  • updated            : 2013-04-11T15:41:23Z

Address:
  • address            : 55 BROADWAY
  • city               : SEATTLE
  • state              : WA
  • zipcode            : 10006-3008

Classification:
  • ntee_code          : S99
  • subseccd           : 4
  ...

Links:
  • guidestar_url      : https://www.guidestar.org/organizations/46-5333729/.aspx
  • nccs_url           : http://nccsweb.urban.org/communityplatform/nccs/organization/profile/id/465333729/
  ...
```

## Files Created

- `execute_inline.py` - Main test script
- `RUN_API_TEST_FINAL.bat` - Batch file launcher
- `api_test_results.json` - Results file (created after running)

## Next Steps

After running the test successfully:

1. Review the output to see what additional fields are available
2. Let me know which fields you'd like to add to your enriched data
3. I'll create a full enrichment script that processes all ~85,000 records

## Notes

- The API is free and doesn't require authentication
- Be respectful with API calls (the script includes delays)
- Results are saved to JSON for later analysis

