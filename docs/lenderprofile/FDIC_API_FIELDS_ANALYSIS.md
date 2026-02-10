# FDIC API Fields Analysis

Based on review of FDIC API definition files:
- `demographics_properties.yaml` - Demographics and geographic data
- `risview_properties.yaml` - Financial and institution data (RISVIEW)

## Key Findings

### Demographics Properties (demographics_properties.yaml)

**Geographic Data:**
- `CBSANAME` - Core Based Statistical Area name
- `CNTYNUM` - FIPS county code
- `METRO` - Flag for Metropolitan Statistical Area (0/1)
- `MICRO` - Flag for Micropolitan Statistical Area (0/1)
- `SIMS_LAT` / `SIMS_LONG` - Geographic coordinates of main office
- `CSA` - Combined Statistical Area

**Branch/Office Data:**
- `OFFSOD` - Number of offices based on Summary of Deposits definition
- `OFFTOT` - Total number of offices operated
- `OFFDMULT` - Number of multiple service domestic offices
- `OFFNDOM` - Number of non-domestic offices
- `OFFSTATE` - Number of states with offices
- `BRANCH` - Flag indicating if institution has branches (0=unit bank, 1=has branches)

**Institution Characteristics:**
- `CERT` - FDIC Certificate number
- `MNRTYCDE` - Minority ownership code
- `HCTNONE` - Flag for independent bank (not in holding company)
- `WEBADDR` - Primary internet web address
- `TE01N528` through `TE10N528` - Additional web site URLs
- `TE01N529` through `TE06N529` - Trade names

**Compliance/Regulatory:**
- `FDICAREA` - FDIC compliance area number
- `FDICTERR` - FDIC compliance territory abbreviation
- `FLDOFDCA` - Name of compliance field office
- `RISKTERR` - FDIC risk territory abbreviation

**Dates:**
- `REPDTE` - Report date (last day of financial reporting period)
- `CALLYM` - Calendar date in YYYYMM format
- `CALLYMD` - Calendar date in YYYYMMDD format
- `QTRNO` - Calendar quarter (1=March, 2=June, 3=September, 4=December)

### RISVIEW Properties (risview_properties.yaml)

This file contains **21,666 lines** and appears to be the comprehensive financial data schema. It likely includes:
- All Call Report financial fields (assets, deposits, income, etc.)
- Balance sheet items
- Income statement items
- Regulatory capital ratios
- Loan portfolio details
- And much more

## Recommendations for LenderProfile

### What We Should Use from FDIC API:

1. **Financial API (Call Reports)** ✅ **KEEP THIS**
   - Use `/financials` endpoint for quarterly financial data
   - Fields: ASSET, DEP, EQUITY, NETINC, ROA, ROE, REPDTE
   - This is the only FDIC API we should actively use

2. **Demographics API** ⚠️ **CONSIDER FOR ENRICHMENT**
   - Could use for geographic context (CBSA, metro flags)
   - Office counts (OFFSOD, OFFTOT) - but we have this from BigQuery SOD
   - Minority ownership codes (MNRTYCDE)
   - Compliance territory info
   - **Note:** Most of this is available from other sources (BigQuery, CFPB, GLEIF)

### What We Should NOT Use:

1. **Location/Branch API** ❌ **REMOVED**
   - We use BigQuery SOD tables instead
   - More accurate and historical
   - Already implemented

2. **Institution API** ❌ **REMOVED**
   - We use CFPB HMDA API and GLEIF for institution data
   - More complete and reliable

## Current Implementation Status

✅ **Correctly Using:**
- FDIC Financial API (`/financials`) for Call Report data only

❌ **Removed (as requested):**
- FDIC Institution API - replaced with CFPB/GLEIF
- FDIC Branch/Location API - replaced with BigQuery SOD

## Potential Enhancements

If we want to enrich reports with additional FDIC data:

1. **Demographics API** - Could add:
   - Minority ownership status
   - Compliance territory assignments
   - Geographic flags (metro/micro)
   - Office count breakdowns

2. **RISVIEW Financial Data** - Could expand financial fields:
   - More detailed balance sheet items
   - Loan portfolio composition
   - Regulatory capital details
   - Income statement breakdowns

**Recommendation:** Keep current minimal approach (Financial API only) unless specific use cases require additional FDIC data.

