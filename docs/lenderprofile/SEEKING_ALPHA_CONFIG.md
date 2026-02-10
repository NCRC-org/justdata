# Seeking Alpha API Configuration

## API Key
The Seeking Alpha API is accessed via RapidAPI with the following key:
- **API Key**: `YOUR_RAPIDAPI_KEY_HERE`
- **Host**: `seeking-alpha.p.rapidapi.com`
- **Base URL**: `https://seeking-alpha.p.rapidapi.com`

## Environment Variable
The API key is stored in the `.env` file as:
```
SEEKING_ALPHA_API_KEY=YOUR_RAPIDAPI_KEY_HERE
```

## MCP Configuration (Alternative Access Method)
If using Model Context Protocol (MCP), the configuration is:
```json
{
  "mcpServers": {
    "RapidAPI Hub - Seeking Alpha": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://mcp.rapidapi.com",
        "--header",
        "x-api-host: seeking-alpha.p.rapidapi.com",
        "--header",
        "x-api-key: YOUR_RAPIDAPI_KEY_HERE"
      ]
    }
  }
}
```

## Current Implementation
The LenderProfile application uses direct HTTP calls to RapidAPI (not MCP). The client is located at:
- `apps/lenderprofile/services/seeking_alpha_client.py`

## Two API Providers Available

### 1. Primary API: `seeking-alpha.p.rapidapi.com` (Default)
**Working Endpoints:**
1. **Get Financials**: `/symbols/get-financials?symbol={ticker}`
   - Returns detailed financial data (revenue, income, etc.)
   - Example: `symbol=PNC` returns 7 financial sections

2. **Get Earnings**: `/symbols/get-earnings?ticker_ids={id}&period_type=quarterly`
   - Requires numeric ticker_id (not ticker symbol)
   - Returns earnings estimates and revisions

3. **Get Ratings**: `/symbols/get-ratings?symbol={ticker}`
   - Returns analyst ratings, quant ratings, and grade metrics

4. **Get Profile**: `/symbols/get-profile?symbol={ticker}`
   - Returns 204 (no content) for some tickers like PNC

### 2. Alternative API: `seeking-alpha-api.p.rapidapi.com` (Requires Subscription)
**Available Endpoints (requires subscription):**
- `/leading-story` - Get leading story/article
- `/articles` - Articles endpoint
- `/news` - News endpoint

**Note:** This alternative API provider has article/news endpoints but requires a separate subscription. To use it, set `use_alternative_api=True` when initializing `SeekingAlphaClient`.

## Usage
```python
from apps.lenderprofile.services.seeking_alpha_client import SeekingAlphaClient

client = SeekingAlphaClient()
financials = client.get_financials('PNC')
```

## Notes
- API uses ticker symbols (e.g., 'PNC'), not company names
- Need to resolve company name → ticker symbol first (use SEC client or web search)
- Financials endpoint works with `symbol=PNC` parameter
- Earnings endpoint requires `ticker_ids` (numeric IDs), not ticker symbols



