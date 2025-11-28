# HubSpot Company Data Points Available

## Summary

Based on analysis of HubSpot data structure, here are the available company data points:

## Companies Table Data Points

**File**: `hubspot-crm-exports-all-companies-2025-11-14.csv`  
**Total Companies**: 10,545  
**Total Columns**: 13

### Confirmed Fields (from codebase analysis):

1. **Record ID** - HubSpot internal ID (primary key for joins)
2. **Company name** - Company/organization name
3. **Membership Status** - Current membership status (CURRENT, LAPSED, GRACE, etc.)
4. **Create Date** - When company record was created in HubSpot
5. **Last Activity Date** - Last engagement/activity date
6. **Phone Number** - Company phone number (1% populated)

### Additional Fields (likely present):
- Address fields (city, state, country) - may be present
- Website - may be present
- Industry - may be present
- Other custom properties

**Note**: Only 13 columns total, so the dataset is relatively simple.

## Deals Table Data Points

**File**: `20251114_123117_all-deals_processed.parquet`  
**Total Deals**: 6,628  
**Total Columns**: 617 (very wide dataset with many custom fields)

### Company-Related Fields in Deals:

1. **Associated Company IDs (Primary)** - Join key to companies table
2. **Company name** - Company name (may be in deal)
3. **Company name 2** - Alternative company name field
4. **Associated Company** - Company association

### Financial Fields in Deals:

1. **amount** - Deal amount (financial data)
2. **membership_status_when_renewing** - Status at renewal time
3. **membership_expiration_date** - Membership expiration date
4. **Deal Stage** - Status (e.g., "Closed won", "Closed Won & Paid")
5. **Close Date** - When deal was closed
6. **Deal Name** - Contains membership/renewal information

### Tax ID / EIN Status:

**Result**: ❌ **No tax ID/EIN found in deals table**

- Searched 617 columns for tax/EIN related keywords
- No columns found with tax ID, EIN, or employer identification number
- No 9-digit EIN patterns found in any columns

## Contacts Table Data Points

**File**: `20251114_123115_all-contacts_processed.parquet`  
**Total Contacts**: 108,403  
**Total Columns**: 12

### Company Association:

1. **associated_company** - Join key to companies table
2. **email** - Contact email
3. **first_name / last_name** - Contact name
4. **phone** - Contact phone
5. Address fields (city, state, country)
6. Date fields (created, updated, last activity)

## Complete Company Data Profile

For each company/member, you can get:

### From Companies Table:
- ✅ Company name
- ✅ Membership status
- ✅ Record ID (for joins)
- ✅ Create date
- ✅ Last activity date
- ⚠️ Phone number (1% populated)
- ❌ Tax ID/EIN (NOT AVAILABLE)
- ❌ Address (may be available, needs verification)
- ❌ Website (may be available, needs verification)
- ❌ Industry (may be available, needs verification)

### From Deals Table (joined):
- ✅ All financial transactions (dues, donations)
- ✅ Payment dates
- ✅ Deal amounts
- ✅ Membership expiration dates
- ✅ Deal stages (paid/unpaid status)
- ❌ Tax ID/EIN (NOT AVAILABLE)

### From Contacts Table (joined):
- ✅ All contacts associated with company
- ✅ Contact emails, names, phones
- ✅ Contact engagement data
- ❌ Tax ID/EIN (NOT AVAILABLE)

## Implications for ProPublica Integration

Since **no tax ID/EIN is available** in HubSpot data:

### Recommended Approach:
1. **Use Company Name** for ProPublica API searches
2. **Use State** (if available) for better matching
3. **Fuzzy matching** to handle name variations
4. **Manual review** option for ambiguous matches

### ProPublica Client Implementation:
- ✅ `find_organization_by_name()` - Search by company name
- ✅ `enrich_member_with_form_990()` - Enrich with Form 990 data
- ✅ Handles name-based matching with state filtering
- ✅ Returns match confidence

## Data Quality Notes

### High Quality Fields:
- Company name: ✅ Available
- Membership status: ✅ Available
- Financial data: ✅ Available in deals
- Contact associations: ✅ Available

### Missing/Incomplete Fields:
- Tax ID/EIN: ❌ Not available
- Phone number: ⚠️ Only 1% populated
- Address: ⚠️ Needs verification
- Website: ⚠️ Needs verification

## Recommendations

1. **For ProPublica Integration**: Use name-based search (already implemented)
2. **For Future Enhancement**: Consider adding EIN as custom property in HubSpot
3. **For Data Quality**: Verify address/website fields if needed for other features
4. **For Matching**: Use company name + state (if available) for best ProPublica matches

