# ProPublica API Test - Instructions

## Quick Test

I've created several test scripts for you. Due to terminal execution issues, please run one of these manually:

### Option 1: Simple Test (Recommended)
```bash
python direct_api_test.py
```

This will:
- Test 3 sample EINs from your data
- Show all available fields from ProPublica API
- Save results to `api_test_results.json`

### Option 2: Single EIN Test
```bash
python simple_api_test.py
```

### Option 3: Full Enrichment Test
```bash
python test_propublica_enrichment.py
```

## Expected Results

Based on the ProPublica API documentation, when you query by EIN, you'll get an Organization object with these fields:

### Basic Information
- `ein` - Employer Identification Number (integer)
- `strein` - EIN in "XX-XXXXXXX" format
- `name` - Organization name
- `sub_name` - Secondary name/alias
- `updated` - Last update timestamp

### Address Information  
- `address` - Street address
- `city` - City
- `state` - State (2-letter code)
- `zipcode` - ZIP code

### Classification
- `ntee_code` - NTEE category code
- `subseccd` - Tax subsection code (501(c)(X))
- `classification` - Additional classification
- `ruling_date` - IRS ruling date
- `deductibility` - Deductibility code

### External Links (NEW - Not in your current data!)
- `guidestar_url` - Link to GuideStar profile
- `nccs_url` - Link to NCCS profile

### Additional EO-BMF Fields
The API also returns 20+ additional fields from the IRS Exempt Organizations Business Master File, including:
- Foundation codes
- Activity codes
- Status codes
- And more...

## Sample API Response Structure

```json
{
  "total_results": 1,
  "organizations": [
    {
      "ein": 465333729,
      "strein": "46-5333729",
      "name": "Center For Housing Economics",
      "sub_name": "",
      "address": "55 BROADWAY",
      "city": "SEATTLE",
      "state": "WA",
      "zipcode": "10006-3008",
      "ntee_code": "S99",
      "subseccd": 4,
      "guidestar_url": "https://www.guidestar.org/organizations/46-5333729/.aspx",
      "nccs_url": "http://nccsweb.urban.org/communityplatform/nccs/organization/profile/id/465333729/",
      "updated": "2013-04-11T15:41:23Z",
      ... (20+ more fields)
    }
  ]
}
```

## What This Means for Your Data

Your current data already has:
- ✓ EIN numbers
- ✓ Basic organization info
- ✓ Some financial data
- ✓ NTEE codes

**Additional data you can get:**
- ✨ External links (GuideStar, NCCS) - **NEW**
- ✨ More detailed EO-BMF fields - **NEW**
- ✨ Updated timestamps - **NEW**
- ✨ Additional classification details

## Next Steps After Testing

Once you've run the test and seen the results:

1. Review which fields are most valuable for your use case
2. I can create a full enrichment script that:
   - Processes all records in your file
   - Queries ProPublica API for each EIN
   - Merges additional fields into your existing data
   - Handles rate limiting and errors
   - Saves enriched data to a new file

Let me know what you'd like to do next!

