# HubSpot Tax ID / EIN Analysis

## Summary

**Result**: ❌ **No tax ID/EIN fields found in HubSpot data (checked both companies AND deals tables)**

## Analysis Results

### Companies Data Check
- **File**: `hubspot-crm-exports-all-companies-2025-11-14.csv`
- **Total Companies**: 10,545
- **Total Columns**: 13
- **Result**: No tax ID/EIN fields found

### Deals Data Check
- **File**: `20251114_123117_all-deals_processed.parquet`
- **Total Deals**: 6,628
- **Total Columns**: 617 (very wide dataset)
- **Result**: No tax ID/EIN fields found (searched all 617 columns)

### Search Results

1. **No explicit tax ID/EIN columns found**
   - Searched for: tax, ein, employer, identification, taxid, tax_id, tax_number, federal, irs, ssn, tin, taxpayer, id_number
   - Result: No matching columns

2. **No EIN-like patterns found**
   - Searched for 9-digit numbers (EIN format: XX-XXXXXXX)
   - Result: No columns contain EIN-like patterns

3. **Available ID fields**
   - `Record ID` - HubSpot internal ID (not EIN)
   - `Phone Number` - Contains phone numbers (not EIN)

## Implications

Since HubSpot does not contain EIN/tax ID data, we have two options for integrating ProPublica Form 990 data:

### Option 1: Search by Company Name (Recommended)
- Use ProPublica API's search functionality
- Search by company name from HubSpot
- Filter by state if available for better matching
- **Pros**: Works immediately, no data changes needed
- **Cons**: May have false matches, requires fuzzy matching

### Option 2: Add EIN to HubSpot
- Add EIN as a custom property in HubSpot
- Manually populate or import EIN data
- Then use EIN for direct ProPublica lookups
- **Pros**: Most accurate, fastest lookups
- **Cons**: Requires manual data entry/import

## Implementation Recommendation

**Use Option 1 (Name-based search)** for initial implementation:

1. **ProPublica API Client** (`utils/propublica_client.py`)
   - `find_organization_by_name()` - Search by company name
   - `enrich_member_with_form_990()` - Enrich member with Form 990 data
   - Handles both EIN (if available) and name-based searches

2. **Matching Strategy**
   - Try exact name match first
   - Filter by state if available in HubSpot
   - Return best match with confidence level
   - Allow manual review/selection if multiple matches

3. **Future Enhancement**
   - Add EIN field to HubSpot as custom property
   - Import EIN data from ProPublica or other sources
   - Switch to EIN-based lookups for better accuracy

## Next Steps

1. ✅ Create ProPublica API client (done)
2. ⏳ Integrate into MemberView data loading
3. ⏳ Add Form 990 data to member detail view
4. ⏳ Implement caching to reduce API calls
5. ⏳ Consider adding EIN field to HubSpot for future use

