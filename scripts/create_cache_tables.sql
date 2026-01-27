-- BigQuery Table Creation Scripts for Analysis Cache System
-- Project: hdma1-242116
-- Dataset: justdata (existing)

-- 1. Analysis Cache Table
-- Stores cache metadata and access statistics
CREATE TABLE IF NOT EXISTS `hdma1-242116.justdata.analysis_cache` (
  cache_key STRING NOT NULL,              -- Primary key: hash of normalized parameters
  app_name STRING NOT NULL,               -- 'branchsight', 'bizsight', 'lendsight', 'mergermeter', 'branchmapper'
  job_id STRING NOT NULL,                 -- Original job_id from first analysis
  parameters_hash STRING,                -- SHA256 of normalized parameters (for verification)
  parameters_json JSON,                   -- Full normalized parameters (for debugging/analytics)
  created_at TIMESTAMP NOT NULL,          -- When cache entry was created
  created_by_user_type STRING,            -- User type who created this cache entry
  last_accessed TIMESTAMP,                -- Last time this cache was used
  access_count INT64 DEFAULT 0,           -- How many times this cache was hit
  result_size_bytes INT64,                -- Size of result JSON in bytes
  cost_saved_usd FLOAT64 DEFAULT 0.0,     -- Estimated cost savings from caching
  expires_at TIMESTAMP                    -- Optional expiration (NULL = never expires)
)
PARTITION BY DATE(created_at)
CLUSTER BY app_name, cache_key;

-- 2. Usage Log Table
-- Tracks every request for analytics and auditing
CREATE TABLE IF NOT EXISTS `hdma1-242116.justdata.usage_log` (
  request_id STRING NOT NULL,             -- Primary key: unique request ID
  timestamp TIMESTAMP NOT NULL,           -- When request was made
  user_type STRING NOT NULL,              -- 'public', 'economy', 'member', 'partner', 'staff', 'developer'
  user_id STRING,                         -- Optional: user identifier (if you add auth later)
  app_name STRING NOT NULL,               -- Which app was requested
  parameters_json JSON NOT NULL,          -- Full request parameters
  cache_key STRING,                       -- Cache key for this request
  cache_hit BOOLEAN NOT NULL,             -- Was this a cache hit?
  job_id STRING NOT NULL,                 -- Job ID (new or cached)
  response_time_ms INT64,                 -- How long request took (milliseconds)
  bigquery_cost_usd FLOAT64 DEFAULT 0.0,  -- Estimated BigQuery cost
  ai_cost_usd FLOAT64 DEFAULT 0.0,        -- Estimated AI API cost
  total_cost_usd FLOAT64 DEFAULT 0.0,     -- Total estimated cost
  ip_address STRING,                      -- Optional: for security/analytics
  user_agent STRING,                      -- Optional: browser/client info
  error_message STRING                    -- If request failed, error message
)
PARTITION BY DATE(timestamp)
CLUSTER BY app_name, user_type, timestamp;

-- 3. Analysis Results Table
-- Stores summary and metadata for each analysis
CREATE TABLE IF NOT EXISTS `hdma1-242116.justdata.analysis_results` (
  job_id STRING NOT NULL,                 -- Primary key
  app_name STRING NOT NULL,               -- Which app
  cache_key STRING NOT NULL,              -- Link to cache entry
  result_summary JSON NOT NULL,           -- Summary/metadata (counties, years, etc.)
  sections_summary JSON,                  -- List of all section names/types for quick reference
  created_at TIMESTAMP NOT NULL,          -- When analysis was completed
  created_by_user_type STRING,            -- User type who created this
  analysis_duration_seconds FLOAT64,      -- How long analysis took
  bigquery_queries_count INT64 DEFAULT 0, -- Number of BQ queries run
  ai_calls_count INT64 DEFAULT 0,         -- Number of AI API calls
  status STRING NOT NULL,                 -- 'completed', 'failed', 'in_progress'
  error_message STRING                    -- If failed, error details
)
PARTITION BY DATE(created_at)
CLUSTER BY app_name, job_id;

-- 4. Analysis Result Sections Table
-- Stores each section of the analysis result separately
CREATE TABLE IF NOT EXISTS `hdma1-242116.justdata.analysis_result_sections` (
  section_id STRING NOT NULL,             -- Primary key: unique section ID
  job_id STRING NOT NULL,                 -- Links to analysis_results table
  app_name STRING NOT NULL,               -- Which app
  section_type STRING NOT NULL,           -- 'data_table', 'ai_summary', 'ai_narrative', 'metadata', 'raw_data'
  section_name STRING NOT NULL,           -- e.g., 'county_summary_table', 'executive_summary', 'by_bank'
  section_category STRING,                -- Optional grouping: 'tables', 'ai_insights', 'metadata'
  section_data JSON NOT NULL,             -- The actual section data (table rows, AI text, etc.)
  section_metadata JSON,                  -- Section-specific metadata (headers, columns, word_count, etc.)
  display_order INT64,                    -- Order for display (1, 2, 3...)
  created_at TIMESTAMP NOT NULL,          -- When section was created
  updated_at TIMESTAMP                    -- If section was regenerated/updated
)
PARTITION BY DATE(created_at)
CLUSTER BY app_name, job_id, section_type;

-- Create indexes for common queries (BigQuery uses clustering, but we can add these for reference)
-- Note: BigQuery doesn't support traditional indexes, clustering is handled above

-- Example queries for verification:
-- SELECT COUNT(*) FROM `hdma1-242116.justdata.analysis_cache`;
-- SELECT COUNT(*) FROM `hdma1-242116.justdata.usage_log`;
-- SELECT COUNT(*) FROM `hdma1-242116.justdata.analysis_results`;
-- SELECT COUNT(*) FROM `hdma1-242116.justdata.analysis_result_sections`;

