# BigQuery-Based Analysis Cache Implementation

## Overview

This document describes the BigQuery-based caching system implemented for the JustData platform. The system provides cost-saving, user-agnostic caching that stores analysis results in BigQuery with section-based storage for better querying and analytics.

## Features

- **User-Agnostic Caching**: Cache keys are generated from normalized parameters only, not user-specific information
- **Cost Savings**: Identical requests reuse cached results, avoiding redundant BigQuery queries and AI API calls
- **Section-Based Storage**: Results are stored by section (data tables, AI summaries, etc.) for better organization
- **Complete Audit Trail**: Every request is logged in `usage_log` for analytics and auditing
- **Persistent Storage**: All results stored as JSON in BigQuery, surviving server restarts

## Architecture

### BigQuery Tables

All tables are in the `justdata` dataset:

1. **`analysis_cache`**: Cache metadata and access statistics
2. **`usage_log`**: Complete request log for analytics
3. **`analysis_results`**: Summary and metadata for each analysis
4. **`analysis_result_sections`**: Individual sections of results (data tables, AI summaries, etc.)

### Cache Flow

```
User Request
    ↓
Check Cache (by normalized parameters)
    ↓
Cache Hit? → Yes → Return cached job_id + Reconstruct result from sections
    ↓ No
Run Analysis → Store result in sections → Log usage
```

## Setup

### 1. Create BigQuery Tables

Run the setup script:

```bash
python scripts/setup_cache_tables.py
```

Or manually run the SQL:

```bash
bq query --use_legacy_sql=false < scripts/create_cache_tables.sql
```

### 2. Verify Tables

```sql
SELECT COUNT(*) FROM `hdma1-242116.justdata.analysis_cache`;
SELECT COUNT(*) FROM `hdma1-242116.justdata.usage_log`;
SELECT COUNT(*) FROM `hdma1-242116.justdata.analysis_results`;
SELECT COUNT(*) FROM `hdma1-242116.justdata.analysis_result_sections`;
```

## Usage

The caching system is automatically integrated into all blueprint `analyze()` functions:

- **BranchSight**: `/branchsight/analyze`
- **BizSight**: `/bizsight/analyze`
- **MergerMeter**: `/mergermeter/analyze`
- **LendSight**: `/lendsight/analyze` (if applicable)
- **BranchMapper**: `/branchmapper/analyze` (if applicable)

### How It Works

1. **Cache Check**: Before running analysis, the system checks for a cached result using normalized parameters
2. **Cache Hit**: If found, returns cached `job_id` and reconstructs result from sections
3. **Cache Miss**: Runs new analysis, stores result in sections, logs usage
4. **Usage Logging**: Every request (hit or miss) is logged with metadata

## Section Types

Results are stored by section type:

- **`data_table`**: Data tables (by_county, by_bank, county_summary_table, etc.)
- **`ai_summary`**: AI-generated summaries (executive_summary, key_findings)
- **`ai_narrative`**: AI-generated narratives (trends_analysis, discussions)
- **`raw_data`**: Raw data (if applicable)
- **`metadata`**: Analysis metadata

## Example Queries

### Cache Effectiveness

```sql
SELECT 
    app_name,
    COUNT(*) as total_requests,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
    ROUND(100.0 * SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) / COUNT(*), 2) as hit_rate_pct,
    SUM(CASE WHEN cache_hit THEN 0 ELSE total_cost_usd END) as total_cost,
    SUM(CASE WHEN cache_hit THEN total_cost_usd ELSE 0 END) as cost_saved
FROM `justdata.usage_log`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY app_name;
```

### Most Requested Analyses

```sql
SELECT 
    app_name,
    parameters_json,
    COUNT(*) as request_count,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
FROM `justdata.usage_log`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY app_name, parameters_json
ORDER BY request_count DESC
LIMIT 20;
```

### Get All Sections for a Job

```sql
SELECT 
    section_name,
    section_type,
    section_category,
    section_data,
    section_metadata
FROM `justdata.analysis_result_sections`
WHERE job_id = 'your-job-id'
ORDER BY display_order;
```

## Cost Tracking

The system tracks estimated costs:

- **BigQuery costs**: Estimated based on query complexity
- **AI costs**: Estimated based on API calls
- **Total costs**: Sum of BigQuery + AI costs
- **Cost saved**: Calculated from cache hits

## Notes

- Cache keys are **user-agnostic**: Same parameters = same cache key, regardless of user
- All results stored as **JSON** in BigQuery, regardless of size
- Cache entries **never expire** by default (can be configured)
- Section-based storage allows **selective retrieval** and **better analytics**

## Troubleshooting

### Cache Not Working

1. Check BigQuery tables exist: `SELECT COUNT(*) FROM justdata.analysis_cache`
2. Check credentials: Ensure `GOOGLE_APPLICATION_CREDENTIALS` is set
3. Check logs: Look for cache-related errors in application logs

### Performance Issues

- BigQuery queries are partitioned and clustered for performance
- Cache lookups are fast (indexed by `cache_key`)
- Section retrieval is optimized with clustering

## Future Enhancements

- Cache expiration policies
- Cost calculation improvements
- Cache warming strategies
- Section-level cache invalidation

