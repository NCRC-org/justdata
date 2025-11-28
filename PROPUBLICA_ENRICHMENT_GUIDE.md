# ProPublica API Enrichment Guide

## Overview

This script enriches your member data with additional fields from the ProPublica Nonprofit Explorer API. It processes all records in your `enriched_members_cleaned_final.json` file and adds new data fields that aren't currently in your dataset.

## What Gets Added

The enrichment script adds the following new fields from ProPublica API:

### External Links (NEW)
- `guidestar_url` - Link to GuideStar profile
- `nccs_url` - Link to National Center for Charitable Statistics profile

### Additional Metadata (NEW)
- `updated` - Last update timestamp from ProPublica
- Additional address fields (`address`, `zipcode`) if missing

### Additional EO-BMF Fields (NEW)
- `classification` - Additional classification codes
- `ruling_date` - IRS ruling date
- `deductibility` - Deductibility code
- `foundation` - Foundation code
- `activity` - Activity code
- `asset_cd`, `income_cd`, `revenue_amt` - Asset/income codes
- `filing_req_cd`, `pf_filing_req_cd` - Filing requirement codes
- `subsection`, `affiliation`, `ruling` - Additional classification
- `exempt_cd`, `foundation_cd`, `status_cd` - Status codes
- `ntee1`, `ntee2`, `ntee3` - Additional NTEE codes
- And more...

## Data Structure

The enriched data is added under a new `propublica_enrichment` section in each record:

```json
{
  "member_id": "...",
  "company_name": "...",
  "form_990": {
    "organization": {
      "ein": 465333729,
      "strein": "46-5333729",
      ...
    }
  },
  "propublica_enrichment": {
    "enriched_at": "2025-01-27T...",
    "api_source": "ProPublica Nonprofit Explorer API v2",
    "guidestar_url": "https://www.guidestar.org/...",
    "nccs_url": "http://nccsweb.urban.org/...",
    "updated": "2013-04-11T15:41:23Z",
    ...
  }
}
```

## How to Run

### Option 1: Using the Launcher (Recommended)
```bash
python run_enrichment.py
```

### Option 2: Direct Execution
```bash
cd C:\dream\#JustData_Repo
python enrich_with_propublica.py
```

### Option 3: Using the Utility Script
```bash
cd C:\dream
python utils\run_python_script.py #JustData_Repo\enrich_with_propublica.py
```

## Features

### Checkpoint System
- Automatically saves progress every 100 records
- Can resume from where it left off if interrupted
- Checkpoint file: `propublica_enrichment_checkpoint.json`

### Rate Limiting
- Respectful 1-second delay between API calls
- Automatic retry on rate limit errors (429)
- Prevents overwhelming the API

### Error Handling
- Gracefully handles missing EINs
- Continues processing even if individual records fail
- Tracks failed EINs for review

### Progress Tracking
- Shows progress every 100 records
- Displays statistics (enriched, skipped, errors)
- Real-time status updates

## Configuration

Edit `enrich_with_propublica.py` to customize:

- `RATE_LIMIT_DELAY` - Delay between API calls (default: 1.0 seconds)
- `INPUT_FILE` - Path to input JSON file
- `OUTPUT_FILE` - Path for enriched output
- `FIELDS_TO_ADD` - List of fields to extract from API

## Output

The script creates:
1. **Enriched JSON file**: `enriched_members_propublica_enhanced.json`
   - Contains all original data plus new ProPublica fields
   
2. **Checkpoint file**: `propublica_enrichment_checkpoint.json`
   - Allows resuming if process is interrupted

## Performance

- **Processing time**: ~1 second per record (due to rate limiting)
- **Total time estimate**: ~85,000 records × 1 second = ~24 hours
- **Can be interrupted and resumed** using checkpoint system

## Notes

- The API is free and doesn't require authentication
- Be respectful with API calls (script includes rate limiting)
- The script only adds fields that don't already exist
- Original data is preserved - new data is added, not replaced

## Troubleshooting

### Script stops/fails
- Check the checkpoint file to see where it stopped
- The script will resume from the last checkpoint on next run
- Review failed EINs in checkpoint file

### Rate limiting errors
- Script automatically handles 429 errors
- Increases delay and retries
- If persistent, increase `RATE_LIMIT_DELAY`

### Missing data
- Some organizations may not be in ProPublica database
- This is normal - script tracks skipped records
- Check `skipped_count` in final summary

## Next Steps

After enrichment completes:
1. Review the enriched data file
2. Check which fields were successfully added
3. Use the new `guidestar_url` and `nccs_url` fields for additional research
4. Analyze the additional EO-BMF fields for insights
















