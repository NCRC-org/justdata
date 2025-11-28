# Rate Limiting Strategy

## Overview

This document outlines the rate limiting strategy implemented to avoid API rate limit errors when enriching member data.

## Rate Limiting Implementation

### 1. ProPublica API

**Current Settings:**
- Base delay: **1.0 second** (increased from 0.5s)
- Adaptive delay: Increases exponentially with consecutive errors (up to 10 seconds max)
- Retry logic: Handles 429 (rate limit) errors with exponential backoff

**Features:**
- Tracks consecutive errors and increases delay automatically
- Respects `Retry-After` header if provided
- Retries once after waiting on 429 errors
- Resets error counter on successful requests

**Multiple Search Terms:**
- When searching with abbreviation expansions, adds 0.5 second delay between each search term attempt
- Stops as soon as a match is found (doesn't try all variations)

### 2. Google Custom Search API

**Current Settings:**
- No explicit rate limiting (relies on Google's built-in limits)
- Error handling: Detects 403 errors and logs warnings

**Recommendations:**
- Google Custom Search API has generous rate limits (100 queries/day free tier)
- If hitting limits, consider upgrading to paid tier or reducing usage

### 3. Claude API (Anthropic)

**Current Settings:**
- Base delay: **1.0 second** between API calls
- Exponential backoff on rate limit errors (up to 60 seconds)
- Automatic retry on rate limit errors

**Features:**
- Tracks consecutive errors
- Waits and retries once on rate limit errors
- Resets error counter on success

### 4. Website Scraping

**Current Settings:**
- 1 second delay after scraping operations
- Uses respectful User-Agent headers
- Caches results to avoid re-scraping

### 5. Batch Processing

**Member-Level Delays:**
- **2 seconds** delay between processing each member
- This ensures we don't overwhelm APIs when processing multiple members

## Error Handling

### Rate Limit Detection

The system detects rate limit errors by:
1. HTTP status code 429 (Too Many Requests)
2. Error messages containing "rate limit"
3. API-specific error responses

### Exponential Backoff

When rate limit errors are detected:
1. Wait time = base_delay × (2 ^ consecutive_errors)
2. Maximum wait time capped (varies by API)
3. Random jitter added to avoid synchronized retries

### Retry Logic

- Automatic retry once after waiting
- Logs warnings for visibility
- Continues processing other members if one fails

## Best Practices

1. **Use Caching**: All results are cached to avoid redundant API calls
2. **Batch Processing**: Process members with delays between each
3. **Monitor Logs**: Watch for rate limit warnings
4. **Adjust Delays**: If hitting limits frequently, increase base delays
5. **Check API Quotas**: Monitor API usage in provider dashboards

## Configuration

Rate limit delays can be adjusted in:

- `ProPublicaClient.__init__(rate_limit_delay=1.0)`
- `ClaudeHTMLParser.__init__()` - `claude_rate_limit_delay = 1.0`
- `test_enrichment_new_selection.py` - member processing delay (2.0 seconds)

## Monitoring

Watch for these log messages:
- `"Rate limit (429) for..."` - ProPublica rate limit
- `"Claude API rate limit detected..."` - Claude rate limit
- `"Rate limiting: waiting X seconds..."` - Adaptive delays

## Future Improvements

1. **Dynamic Rate Limiting**: Adjust delays based on API response times
2. **Queue System**: Queue requests and process with proper spacing
3. **Distributed Processing**: Spread requests across time if processing large batches
4. **API Key Rotation**: Use multiple API keys if available



