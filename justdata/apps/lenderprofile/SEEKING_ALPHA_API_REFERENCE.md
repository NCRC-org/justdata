# Seeking Alpha API Reference

## Overview

The Seeking Alpha API is accessed via RapidAPI and provides financial data, ratings, and analysis for publicly traded companies.

**Base URL:** `https://seeking-alpha.p.rapidapi.com`  
**Authentication:** RapidAPI key in `x-rapidapi-key` header  
**Host Header:** `x-rapidapi-host: seeking-alpha.p.rapidapi.com`

## Available Endpoints

### ✅ Working Endpoints

#### 1. `/symbols/get-financials`
**Purpose:** Get detailed financial data (revenue, income, balance sheet items)

**Parameters:**
- `symbol` (required): Ticker symbol (e.g., 'FITB', 'PNC')

**Response:**
- Returns list of financial sections with historical data
- Each section contains rows with time-series data

**Example:**
```python
client.get_financials('FITB')
# Returns: List of financial sections
```

#### 2. `/symbols/get-earnings`
**Purpose:** Get earnings estimates and revisions

**Parameters:**
- `ticker_ids` (required): Comma-separated list of numeric ticker IDs
- `period_type`: 'quarterly' or 'annual' (default: 'quarterly')
- `relative_periods`: List of relative periods (e.g., [-3, -2, -1, 0, 1, 2, 3])
- `estimates_data_items`: List of data items to retrieve
- `revisions_data_items`: List of revision data items

**Note:** Requires numeric `ticker_id`, not ticker symbol. You may need to look up ticker_id from ticker symbol first.

**Example:**
```python
client.get_earnings(ticker_ids=[1620], period_type='quarterly')
# Returns: Earnings data dictionary
```

#### 3. `/symbols/get-ratings` ⭐ NEW
**Purpose:** Get stock ratings, analyst recommendations, and quant ratings

**Parameters:**
- `symbol` (required): Ticker symbol (e.g., 'FITB', 'PNC')

**Response Structure:**
```json
{
  "data": [
    {
      "id": "[1620, Sat, 27 Dec 2025]",
      "type": "rating",
      "attributes": {
        "asDate": "2025-12-27",
        "tickerId": 1620,
        "ratings": {
          "authorsRating": 3.0,
          "sellSideRating": 4.18182,
          "quantRating": 3.082581540596808,
          "authorsCount": 3.0,
          "authorsRatingBuyCount": 1.0,
          "authorsRatingHoldCount": 1.0,
          "authorsRatingSellCount": 1.0,
          "epsRevisionsGrade": 10,
          "growthGrade": 8,
          "momentumGrade": 5,
          "profitabilityGrade": 7,
          "valueGrade": 6,
          "divGrowthCategoryGrade": 9,
          "divSafetyCategoryGrade": 4,
          ...
        }
      }
    }
  ],
  "meta": {...}
}
```

**Key Ratings Fields:**
- `authorsRating`: Average rating from Seeking Alpha authors (1-5 scale)
- `sellSideRating`: Average rating from sell-side analysts (1-5 scale)
- `quantRating`: Quantitative rating score
- `authorsCount`: Number of authors providing ratings
- `authorsRatingBuyCount`: Number of "Buy" ratings
- `authorsRatingHoldCount`: Number of "Hold" ratings
- `authorsRatingSellCount`: Number of "Sell" ratings
- Various grade fields (EPS revisions, growth, momentum, profitability, value, dividend growth/safety)

**Example:**
```python
client.get_ratings('FITB')
# Returns: Ratings data with analyst recommendations
```

#### 4. `/symbols/get-profile`
**Purpose:** Get company profile information

**Parameters:**
- `symbol` (required): Ticker symbol

**Status:** Returns 204 (No Content) for many tickers - may not be fully implemented

**Example:**
```python
client.get_profile('FITB')
# Returns: None or profile data if available
```

### ❌ Not Available

The following endpoints were tested but return 404:
- `/symbols/get-news` - News articles not available via API
- `/symbols/get-articles` - Articles not available via API
- `/articles` - Articles endpoint doesn't exist
- `/news` - News endpoint doesn't exist
- `/symbols/get-analysis` - Analysis endpoint doesn't exist
- `/symbols/get-insights` - Insights endpoint doesn't exist

**Note:** Seeking Alpha articles and news are not available through the RapidAPI. You would need to use web scraping (with proper compliance to terms of service) or other methods to access article content.

## Usage in LenderProfile

The `SeekingAlphaClient` provides methods for all available endpoints:

```python
from apps.lenderprofile.services.seeking_alpha_client import SeekingAlphaClient

client = SeekingAlphaClient()

# Get comprehensive data (includes all available endpoints)
result = client.search_by_ticker('FITB')
# Returns: {
#   'ticker': 'FITB',
#   'profile': {...},
#   'financials': [...],
#   'ratings': {...},
#   'earnings': {...}
# }

# Or get individual data types
financials = client.get_financials('FITB')
ratings = client.get_ratings('FITB')
earnings = client.get_earnings(ticker_ids=[1620])
```

## Data Flow

1. **Get Ticker from SEC** (most reliable)
   - Search SEC for company name → Get CIK
   - Get SEC submissions → Extract ticker symbol

2. **Query Seeking Alpha with Ticker**
   - Use ticker to get financials, ratings, earnings
   - Combine all available data

## Limitations

1. **No Articles/News:** The API does not provide access to Seeking Alpha articles or news content
2. **Ticker ID Required for Earnings:** Earnings endpoint requires numeric ticker_id, not ticker symbol
3. **Profile Endpoint:** Returns 204 (No Content) for many companies
4. **Rate Limits:** Subject to RapidAPI rate limits (check your plan)

## Recommendations

1. **Use Ratings Data:** The ratings endpoint provides valuable analyst recommendations and quant ratings
2. **Combine with Other Sources:** For articles/news, consider:
   - NewsAPI (already implemented in LenderProfile)
   - Web scraping (with proper compliance)
   - Other financial news APIs
3. **Cache Results:** Ratings and financials don't change frequently - consider caching

