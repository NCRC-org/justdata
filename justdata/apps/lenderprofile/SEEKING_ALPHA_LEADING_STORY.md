# Seeking Alpha Leading Story Endpoint

## ✅ Working!

The `/leading-story` endpoint is now working and returns leading news stories and articles.

## Endpoint Details

**URL:** `https://seeking-alpha-api.p.rapidapi.com/leading-story`  
**Host:** `seeking-alpha-api.p.rapidapi.com`  
**Method:** GET  
**Parameters:** 
- `symbol` (optional): Ticker symbol (e.g., 'FITB')

## Response Structure

```json
{
  "leading_news_story": [
    {
      "id": 0,
      "type": "leadingNewsStory",
      "attributes": {
        "type": "MarketCurrent",
        "headline": "Catalyst Watch: FOMC minutes, opening 2026 trades",
        "url": "https://seekingalpha.com/news/4534879-catalyst-watch-defense-stocks-in-play-fomc-minutes-and-opening-2026-trades"
      }
    },
    {
      "id": 1,
      "type": "leadingNewsStory",
      "attributes": {
        "type": "Article",
        "headline": "3 Major Hurdles For The AI Revolution",
        "url": "https://seekingalpha.com/article/4855683-the-ai-revolution-3-major-hurdles-that-need-to-be-overcome-in-2026"
      }
    }
  ]
}
```

## Usage

```python
from apps.lenderprofile.services.seeking_alpha_client import SeekingAlphaClient

client = SeekingAlphaClient()

# Get leading stories (general market news)
stories = client.get_leading_story()
# Returns: List of leading news stories

# Get leading stories for specific ticker
stories = client.get_leading_story(symbol='FITB')
# Returns: Leading stories related to FITB
```

## Integration

The `leading_story` data is now automatically included when calling `search_by_ticker()`:

```python
result = client.search_by_ticker('FITB')
# result includes:
# - profile
# - financials
# - ratings
# - earnings
# - leading_story  # NEW!
```

## Data Collector Integration

The `DataCollector` now includes leading stories in Seeking Alpha data:

```python
seeking_alpha_data = collector._get_seeking_alpha_data('Fifth Third Bank')
# Includes: ticker, profile, financials, ratings, earnings, leading_story
```

## Notes

- Works with or without `symbol` parameter
- Returns general market news if no symbol provided
- Returns ticker-specific news if symbol provided
- Automatically uses alternative API (no need to set `use_alternative_api=True`)
- Each story includes headline, URL, and type (Article, MarketCurrent, etc.)

