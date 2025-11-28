# Cost Estimate: Enriching 700 Current Members

## Overview

This document estimates the API costs for enriching all 700 current NCRC members with:
- Website discovery
- Staff/leadership information extraction
- Contact information extraction
- Organization information (funders, partners, areas of work)
- Form 990 financial data

## API Usage Per Member

### 1. Website Discovery
- **DuckDuckGo Search**: FREE (no API key required)
- **Google Custom Search API**: Only used as fallback (~20-30% of members)
  - Estimated: 140-210 calls for 700 members
  - Free tier: 100 queries/day
  - Paid tier: $5 per 1,000 queries
  - **Cost**: $0.70 - $1.05 (if using paid tier)

### 2. ProPublica API (Form 990 Data)
- **Cost**: FREE
- **Usage**: 2-5 search attempts per member (abbreviation expansion)
  - Stops when match found, so average ~2-3 searches per member
  - Total: ~1,400-2,100 API calls
  - **Cost**: $0

### 3. Claude API (Anthropic) - Main Cost Driver

**Per Member (if website found):**
- Staff extraction: 1 API call
- Contact extraction: 1 API call
- Organization info extraction: 1 API call
- **Total: 3 Claude API calls per member with website**

**Token Usage Per Call:**
- **Input tokens**: ~15,000 tokens per call
  - HTML content: ~50,000 characters ≈ 12,500 tokens
  - Prompt text: ~2,500 tokens
  - Total: ~15,000 input tokens
- **Output tokens**: ~1,500 tokens per call (average)
  - Staff extraction: max_tokens=4000, actual ~1,500
  - Contact extraction: max_tokens=2000, actual ~800
  - Org info extraction: max_tokens=4000, actual ~1,500
  - Average: ~1,500 output tokens

**Assumptions:**
- Website found rate: ~80% (560 members with websites)
- Members without websites: No Claude API calls needed
- Cache hit rate: 0% (first-time processing)

## Cost Calculation

### Claude API Pricing (Claude Sonnet 4)
- **Input tokens**: $3.00 per million tokens
- **Output tokens**: $15.00 per million tokens

### Per Member with Website:
- Input: 15,000 tokens × 3 calls = **45,000 input tokens**
- Output: 1,500 tokens × 3 calls = **4,500 output tokens**

### For 560 Members with Websites:
- Total input tokens: 45,000 × 560 = **25,200,000 tokens**
- Total output tokens: 4,500 × 560 = **2,520,000 tokens**

### Cost Breakdown:
- **Input cost**: (25,200,000 / 1,000,000) × $3.00 = **$75.60**
- **Output cost**: (2,520,000 / 1,000,000) × $15.00 = **$37.80**
- **Claude API subtotal**: **$113.40**

### Google Custom Search API:
- Estimated 140-210 calls (20-30% fallback usage)
- If using paid tier: (210 / 1,000) × $5.00 = **$1.05**
- If staying within free tier (100/day): **$0** (would need to spread over 2-3 days)

### ProPublica API:
- **$0** (free)

## Total Estimated Cost

### Scenario 1: All Paid APIs
- Claude API: **$113.40**
- Google Custom Search: **$1.05**
- ProPublica: **$0.00**
- **TOTAL: ~$114.45**

### Scenario 2: Using Free Tier Where Possible
- Claude API: **$113.40** (required - no free tier)
- Google Custom Search: **$0.00** (free tier, spread over 2-3 days)
- ProPublica: **$0.00**
- **TOTAL: ~$113.40**

## Cost Optimization Strategies

### 1. Caching
- **Impact**: Massive cost savings on re-runs
- All results are cached, so subsequent runs cost $0 for cached data
- **First run**: ~$113-114
- **Subsequent runs**: Only new/updated members cost money

### 2. Batch Processing (Anthropic)
- **Potential savings**: Up to 50% discount
- **Cost with batch**: ~$56.70 (input) + $18.90 (output) = **$75.60**
- **Total savings**: ~$37.80

### 3. Selective Processing
- Only process members without existing website data
- Skip members already enriched
- **Potential savings**: 20-30% if many members already have data

### 4. Model Selection
- Claude Haiku (cheaper): $0.25/$1.25 per million tokens
  - Input: $6.30
  - Output: $3.15
  - **Total: $9.45** (but lower quality)
- Claude Opus (more expensive): $15/$75 per million tokens
  - Input: $378.00
  - Output: $189.00
  - **Total: $567.00** (higher quality)

## Processing Time Estimate

With current rate limiting:
- 2 seconds delay between members
- ~1 second per Claude API call
- ~1 second per ProPublica search
- **Per member**: ~5-10 seconds
- **Total time**: 700 × 7 seconds = ~4,900 seconds = **~82 minutes = ~1.4 hours**

## Recommendations

1. **Use Claude Sonnet 4** (current): Best balance of cost and quality
2. **Enable caching**: Critical for cost savings on re-runs
3. **Process in batches**: Consider Anthropic's batch API for 50% discount
4. **Monitor usage**: Track actual token usage to refine estimates
5. **Start small**: Test on 20-50 members first to validate costs

## Actual vs Estimated

**Note**: These are estimates. Actual costs may vary based on:
- Actual website discovery rate
- HTML page sizes (some may be larger/smaller than 50K chars)
- Response lengths (may vary)
- Cache hit rates on subsequent runs
- Rate limit retries (adds small overhead)

## Monthly/Annual Costs

If running enrichment monthly:
- **Monthly**: ~$113-114
- **Annual**: ~$1,356-1,368

With caching, subsequent runs only process new/updated members, significantly reducing costs.



