# ProPublica API Enrichment Analysis

## Current Data Structure

Your current data file (`enriched_members_cleaned_final.json`) already contains:
- Basic organization info (EIN, name, address)
- NTEE codes
- Some financial data from Form 990 filings
- Tax subsection codes

## Additional Data Available from ProPublica API

Based on the ProPublica API documentation, here are additional fields we can retrieve:

### Organization Object Fields (from `/search.json`)

#### Currently Missing or Could Be Enhanced:

1. **External Links** (NEW):
   - `guidestar_url` - Link to GuideStar profile
   - `nccs_url` - Link to National Center for Charitable Statistics profile

2. **Additional Organization Metadata** (NEW):
   - `updated` - Date organization profile was last updated in ProPublica
   - Additional EO-BMF (Exempt Organizations Business Master File) fields (20+ fields)

3. **Enhanced Classification Data**:
   - More detailed NTEE classification information
   - Additional IRS status codes

### Filing Data (from organization detail endpoints)

The API also provides access to:
- Multiple years of Form 990 filings (not just the latest)
- Detailed financial breakdowns
- PDF links to full Form 990 documents
- XML data for electronically filed forms

## Sample EINs from Your Data

From your file, sample EINs include:
- `465333729` (46-5333729) - Center for Housing Economics
- `823374968` (82-3374968) - The Resiliency Collaborative Inc  
- `821125482` (82-1125482) - City Fields

## API Endpoints to Use

1. **Search by EIN**: `GET /search.json?q={strein}`
   - Returns organization details
   - No authentication required
   - Rate limit: Not specified, but be respectful

2. **Organization Details**: (if available)
   - Can get multiple filings for an organization
   - Historical financial data

## Fields That Could Fill Gaps in Your Data

Looking at your current data structure, many fields are `null`:
- `mission` - Could potentially be extracted from filings
- `activities` - Could potentially be extracted from filings  
- `have_filings`, `have_extracts`, `have_pdfs` - Can be determined from API
- Additional financial breakdowns
- Multiple years of historical data

## Next Steps

1. Test the API with sample EINs to see exact response structure
2. Create enrichment script to:
   - Query ProPublica API for each EIN
   - Merge additional fields into existing records
   - Fill in null values where possible
   - Add external links (GuideStar, NCCS)
3. Handle rate limiting and error cases
4. Save enriched data back to file

