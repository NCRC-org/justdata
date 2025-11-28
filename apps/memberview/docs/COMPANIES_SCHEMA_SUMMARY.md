# HubSpot Companies Schema Summary

## Overview

Based on analysis of the HubSpot companies export file, here's what data is available for most members.

## File Information

- **File**: `hubspot-crm-exports-all-companies-2025-11-14.csv`
- **Total Companies**: ~10,545
- **Total Columns**: 13
- **Companies with Membership Status**: Varies (subset of total)

## Well-Populated Fields (for members)

Fields that are populated for most member companies:

### Always Present (100%)
- **Record ID** - HubSpot internal ID (join key)
- **Company name** - Organization name
- **Membership Status** - Current status (CURRENT, LAPSED, GRACE, etc.)

### Usually Present (>50%)
- **Create Date** - When company record created
- **Last Activity Date** - Last engagement date

### Sometimes Present (<50%)
- **Phone Number** - Only ~1% populated
- **City** - May be present (needs verification)
- **State** - May be present (needs verification)
- **Address fields** - May be present (needs verification)

## Key Fields for ProPublica Matching

### Company Name
- **Field**: `Company name`
- **Population**: ~100% (always present)
- **Use**: Primary search term for ProPublica API

### City
- **Field**: TBD (needs verification)
- **Population**: TBD
- **Use**: Filter ProPublica results by city

### State
- **Field**: TBD (needs verification)  
- **Population**: TBD
- **Use**: Filter ProPublica results by state

## Data Quality Notes

1. **Company Name**: Always available - good for matching
2. **Location Data**: May be incomplete - check actual population
3. **Phone**: Very low population (~1%) - not useful
4. **Tax ID/EIN**: NOT AVAILABLE in any table

## For ProPublica Matching

**Best Available Fields**:
1. Company name (always available)
2. State (if available - improves matching)
3. City (if available - further improves matching)

**Matching Strategy**:
- Use company name as primary search
- Filter by state if available
- Filter by city if available
- Accept that many companies are for-profit (no Form 990)

## Expected Match Rate

**Important**: Many NCRC members are for-profit businesses, which means:
- They don't file Form 990 with IRS
- They won't appear in ProPublica database
- Low match rate is EXPECTED and NORMAL

**Typical Match Rate**: 20-40% (depending on how many members are nonprofits)

