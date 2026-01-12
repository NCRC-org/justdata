# Seeking Alpha Data Flow

## Flow Diagram

```
Company Name (e.g., "Fifth Third Bank")
    ↓
┌─────────────────────────────────────┐
│  STEP 1: SEC (Get Ticker Symbol)   │
└─────────────────────────────────────┘
    ↓
1. Search SEC by company name
   → Get CIK (e.g., "0000001750")
    ↓
2. Get SEC submissions for CIK
   → Extract ticker from JSON (e.g., "FITB")
    ↓
┌─────────────────────────────────────┐
│  STEP 2: Seeking Alpha (Get Data)  │
└─────────────────────────────────────┘
    ↓
3. Use ticker to query Seeking Alpha API
   → Get financial data, profile, etc.
```

## Implementation Details

### Step 1: SEC Lookup (Get Ticker)

**Method:** `sec_client.get_ticker_from_company_name(company_name)`

**Process:**
1. Search SEC for company: `search_companies(company_name)`
   - Returns list of companies with CIK
2. For each company, get CIK and call: `get_company_submissions(cik)`
   - Returns JSON with `tickers` array
3. Extract first ticker: `submissions['tickers'][0]`

**Example:**
```python
# Input: "Fifth Third Bank"
# Step 1: Search SEC
companies = sec_client.search_companies("Fifth Third Bank")
# Returns: [{'name': 'FIFTH THIRD BANCORP', 'cik': '0000001750'}]

# Step 2: Get submissions
submissions = sec_client.get_company_submissions("0000001750")
# Returns: {'tickers': ['FITB'], 'name': 'FIFTH THIRD BANCORP', ...}

# Step 3: Extract ticker
ticker = submissions['tickers'][0]  # "FITB"
```

### Step 2: Seeking Alpha Lookup (Get Financial Data)

**Method:** `seeking_alpha_client.search_by_ticker(ticker)`

**Process:**
1. Use ticker from SEC to query Seeking Alpha API
2. Get financial data, profile, earnings, etc.

**Example:**
```python
# Input: "FITB" (from SEC)
result = seeking_alpha_client.search_by_ticker("FITB")
# Returns: {
#   'profile': {...},
#   'financials': [...],
#   ...
# }
```

## Code Flow in DataCollector

```python
def _get_seeking_alpha_data(self, name: str):
    # Fast lookup: Check hardcoded mapping first
    ticker = ticker_map.get(name.upper())
    
    # If not found, go to SEC
    if not ticker:
        ticker = self.sec_client.get_ticker_from_company_name(name)
        # This internally:
        #   1. Searches SEC for company → gets CIK
        #   2. Gets SEC submissions → extracts ticker
    
    # Then go to Seeking Alpha
    if ticker:
        result = self.seeking_alpha_client.search_by_ticker(ticker)
        return {'ticker': ticker, ...result}
```

## Benefits of This Approach

1. **Reliability**: SEC is authoritative source for ticker symbols
2. **Accuracy**: No guessing or pattern matching
3. **Always Up-to-Date**: SEC data is current
4. **Handles Edge Cases**: Works for companies with multiple tickers, name changes, etc.

## Fallback Strategy

If SEC lookup fails:
1. Try hardcoded mapping (fast lookup for known banks)
2. Try web search (DuckDuckGo API)
3. Try name extraction (last resort)

But primary flow is always: **SEC → Seeking Alpha**

