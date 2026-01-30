-- Migration: Set up analytics events tables and views
-- This creates the backfilled_events table and all_events view in firebase_analytics dataset
-- 
-- Run this migration to enable the analytics maps (Report Locations, Lender Interest)
-- 
-- Usage: Run each statement separately in BigQuery console or via:
--   bq query --use_legacy_sql=false < scripts/migration/27_setup_analytics_events.sql

-- ============================================================================
-- 1. Create firebase_analytics dataset if it doesn't exist
-- ============================================================================
-- Run manually in BigQuery console:
-- CREATE SCHEMA IF NOT EXISTS `justdata-ncrc.firebase_analytics` OPTIONS(location="US");

-- ============================================================================
-- 2. Create backfilled_events table
-- ============================================================================
CREATE TABLE IF NOT EXISTS `justdata-ncrc.firebase_analytics.backfilled_events` (
    event_id STRING NOT NULL,
    event_name STRING NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    user_id STRING,
    user_email STRING,
    user_type STRING,
    
    -- Event parameters (flattened for easier querying)
    county_fips STRING,
    county_name STRING,
    state STRING,
    lender_name STRING,
    lender_id STRING,  -- LEI or RSSD
    year_range STRING,
    
    -- Source metadata
    source STRING DEFAULT 'sync',  -- 'backfill', 'sync', or 'live'
    source_job_id STRING,
    source_cache_key STRING,
    
    -- For HubSpot integration
    hubspot_contact_id STRING,
    hubspot_company_id STRING,
    organization_name STRING,
    
    backfill_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- 3. Create or replace the all_events unified view
-- ============================================================================
-- This view combines:
-- 1. Backfilled/synced events from usage_log
-- 2. Firebase Analytics events from firebase_analytics.events_* tables
-- 3. GA4 export from analytics_521852976 (newer data)

CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.all_events` AS

-- Backfilled/synced events from usage_log
SELECT
    event_id,
    event_name,
    event_timestamp,
    user_id,
    user_email,
    user_type,
    county_fips,
    county_name,
    state,
    lender_name,
    lender_id,
    year_range,
    source,
    hubspot_contact_id,
    hubspot_company_id,
    organization_name
FROM `justdata-ncrc.firebase_analytics.backfilled_events`

UNION ALL

-- Firebase Analytics events from firebase_analytics.events_* tables
SELECT
    GENERATE_UUID() as event_id,
    event_name,
    TIMESTAMP_MICROS(event_timestamp) as event_timestamp,
    COALESCE(user_id, user_pseudo_id) as user_id,  -- Use pseudo_id if no real user_id
    CAST(NULL AS STRING) as user_email,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "user_type") as user_type,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "county_fips") as county_fips,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "county_name") as county_name,
    COALESCE(
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "state"),
        geo.region
    ) as state,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "lender_name") as lender_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "lender_id") as lender_id,
    CAST(NULL AS STRING) as year_range,
    "ga4" as source,
    CAST(NULL AS STRING) as hubspot_contact_id,
    CAST(NULL AS STRING) as hubspot_company_id,
    CAST(NULL AS STRING) as organization_name
FROM `justdata-ncrc.firebase_analytics.events_*`
WHERE event_name LIKE "%report%" OR event_name LIKE "%_generated"

UNION ALL

-- GA4 export from analytics_521852976 (newer data from Jan 27+)
SELECT
    GENERATE_UUID() as event_id,
    event_name,
    TIMESTAMP_MICROS(event_timestamp) as event_timestamp,
    COALESCE(user_id, user_pseudo_id) as user_id,
    CAST(NULL AS STRING) as user_email,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "user_type") as user_type,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "county_fips") as county_fips,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "county_name") as county_name,
    COALESCE(
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "state"),
        geo.region
    ) as state,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "lender_name") as lender_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "lender_id") as lender_id,
    CAST(NULL AS STRING) as year_range,
    "ga4" as source,
    CAST(NULL AS STRING) as hubspot_contact_id,
    CAST(NULL AS STRING) as hubspot_company_id,
    CAST(NULL AS STRING) as organization_name
FROM `justdata-ncrc.analytics_521852976.events_*`
WHERE event_name LIKE "%report%" OR event_name LIKE "%_generated";

-- ============================================================================
-- 4. Verify the setup
-- ============================================================================
-- Check table exists and has expected columns
SELECT column_name, data_type 
FROM `justdata-ncrc.firebase_analytics.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'backfilled_events'
ORDER BY ordinal_position;

-- Check view exists
SELECT table_name, table_type
FROM `justdata-ncrc.firebase_analytics.INFORMATION_SCHEMA.TABLES`
WHERE table_name IN ('backfilled_events', 'all_events');
