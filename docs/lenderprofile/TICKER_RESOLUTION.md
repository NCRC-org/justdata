# Ticker Symbol Resolution Strategy

## Overview

This document describes the reliable methods for resolving company names to stock ticker symbols.

## Primary Method: SEC Submissions API (Most Reliable)

The **most reliable** method is to use the SEC Submissions API, which returns ticker symbols in the JSON response.

### Process:
1. Search SEC for company by name → Get CIK
2. Call SEC Submissions API with CIK → Get `tickers` array
3. Use first ticker (primary ticker)

### Example:
```python
from apps.lenderprofile.services.sec_client import SECClient

client = SECClient()

# Step 1: Search for company
companies = client.search_companies("Fifth Third Bank")
cik = companies[0]['cik']  # e.g., "0000001750"

# Step 2: Get submissions (contains tickers)
submissions = client.get_company_submissions(cik)
ticker = submissions['tickers'][0]  # e.g., "FITB"
```

### Why This is Most Reliable:
- ✅ Official SEC data source
- ✅ Always up-to-date
- ✅ Returns multiple tickers if company has multiple classes
- ✅ No web scraping or guessing required

## Implementation

### New Methods in `SECClient`:

1. **`get_ticker_from_cik(cik)`** - Get ticker directly from CIK
   - Uses SEC submissions API
   - Returns primary ticker symbol

2. **`get_ticker_from_company_name(company_name)`** - Comprehensive lookup
   - Tries SEC search → CIK → submissions API (most reliable)
   - Falls back to web search if needed
   - Falls back to name extraction as last resort

3. **`get_ticker_from_search(company_name)`** - DEPRECATED
   - Kept for backward compatibility
   - Now calls `get_ticker_from_company_name()`

### Fallback Methods:

1. **Hardcoded Mapping** (Fast lookup for known banks)
   ```python
   ticker_map = {
       'FIFTH THIRD BANK': 'FITB',
       'FIFTH THIRD': 'FITB',
       'FIFTH THIRD BANCORP': 'FITB',
   }
   ```

2. **Web Search** (DuckDuckGo API)
   - Used if SEC lookup fails
   - Less reliable, may return incorrect results

3. **Name Extraction** (Last resort)
   - Tries to extract ticker from company name
   - Only works for simple cases (e.g., "PNC Bank" → "PNC")

## Usage in Data Collector

The `DataCollector._get_seeking_alpha_data()` method now uses:

1. Hardcoded mapping (fastest)
2. `sec_client.get_ticker_from_company_name()` (most reliable)
3. Returns empty dict if no ticker found

## SEC Submissions API Response Structure

```json
{
  "cik": "0000001750",
  "name": "FIFTH THIRD BANCORP",
  "tickers": ["FITB"],  // <-- Ticker symbols here
  "exchanges": ["Nasdaq"],
  "sic": "6029",
  "sicDescription": "State Commercial Banks",
  "filings": {
    "recent": {
      "form": ["10-K", "10-Q", ...],
      "filingDate": ["2024-12-31", ...],
      ...
    }
  }
}
```

## Benefits

1. **Reliability**: Uses official SEC data, not web scraping
2. **Accuracy**: Always returns correct ticker for public companies
3. **Completeness**: Can return multiple tickers if company has multiple classes
4. **Performance**: Single API call after getting CIK (which we already do)
5. **Maintainability**: No need to maintain large ticker mapping tables

## Limitations

1. **Only for Public Companies**: Only works for companies that file with SEC
2. **Requires CIK**: Must first resolve company name to CIK
3. **Rate Limiting**: SEC API has 10 requests/second limit (already handled)

## Testing

Test the ticker resolution:

```python
from apps.lenderprofile.services.sec_client import SECClient

client = SECClient()

# Test various company names
test_names = [
    "Fifth Third Bank",
    "PNC Financial Services",
    "Bank of America",
    "JPMorgan Chase"
]

for name in test_names:
    ticker = client.get_ticker_from_company_name(name)
    print(f"{name}: {ticker}")
```

## Future Enhancements

1. **Cache Ticker Lookups**: Store company name → ticker mappings in Redis
2. **Expand Hardcoded Mapping**: Add more common banks for faster lookup
3. **Multiple Ticker Support**: Return all tickers, not just primary
4. **Exchange Information**: Include exchange data from submissions API

