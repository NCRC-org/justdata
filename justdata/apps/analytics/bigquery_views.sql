-- BigQuery Views for JustData Analytics
-- These views aggregate Firebase Analytics data exported to BigQuery.
--
-- Rewritten 2026-08-31 to match the infrastructure that is actually live.
-- The file previously described a `justdata-f7da7` / `justdata_analytics`
-- setup that was never realized in production -- the events_* wildcard
-- table it depended on doesn't exist there, so none of the CREATE OR
-- REPLACE VIEW statements below it could ever have run successfully.
-- The real infrastructure lives entirely in `justdata-ncrc`, confirmed by
-- pulling the live `all_events` view definition directly from BigQuery
-- (INFORMATION_SCHEMA.VIEWS) rather than guessing.
--
-- Project: justdata-ncrc
-- Firebase Export Datasets (sequential, non-overlapping date ranges):
--   - firebase_analytics.events_*     (through 2026-01-26)
--   - analytics_521852976.events_*    (2026-01-27 onward -- export moved
--     to a new GA4 stream; same schema, different dataset)
-- Analytics Views Dataset: firebase_analytics

-- ============================================================================
-- PREREQUISITES:
-- 1. Firebase Analytics -> BigQuery export is already enabled and linked to
--    justdata-ncrc (both datasets above receive daily export tables).
-- 2. The Cloud Run service account needs BigQuery Data Viewer on
--    justdata-ncrc.firebase_analytics.backfilled_events for the historical
--    backfill portion of all_events.
-- ============================================================================

-- ============================================================================
-- UNIFIED ALL_EVENTS VIEW (CRITICAL - Required by Analytics Dashboard)
-- Combines historical backfilled data with both live Firebase export streams.
-- This is the exact live definition as of 2026-08-31 (pulled from
-- INFORMATION_SCHEMA.VIEWS, not reconstructed from memory).
-- ============================================================================

CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.all_events` AS

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
    GENERATE_UUID() AS event_id,
    event_name,
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
    COALESCE(user_id, user_pseudo_id) AS user_id,
    CAST(NULL AS STRING) AS user_email,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'user_type') AS user_type,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'county_fips') AS county_fips,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'county_name') AS county_name,
    COALESCE(
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'state'),
        geo.region
    ) AS state,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lender_name') AS lender_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lender_id') AS lender_id,
    CAST(NULL AS STRING) AS year_range,
    'ga4' AS source,
    CAST(NULL AS STRING) AS hubspot_contact_id,
    CAST(NULL AS STRING) AS hubspot_company_id,
    CAST(NULL AS STRING) AS organization_name
FROM `justdata-ncrc.firebase_analytics.events_*`
WHERE event_name LIKE '%report%' OR event_name LIKE '%_generated'

UNION ALL

-- GA4 export from analytics_521852976 (newer data, export stream migrated 2026-01-27)
SELECT
    GENERATE_UUID() AS event_id,
    event_name,
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
    COALESCE(user_id, user_pseudo_id) AS user_id,
    CAST(NULL AS STRING) AS user_email,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'user_type') AS user_type,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'county_fips') AS county_fips,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'county_name') AS county_name,
    COALESCE(
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'state'),
        geo.region
    ) AS state,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lender_name') AS lender_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lender_id') AS lender_id,
    CAST(NULL AS STRING) AS year_range,
    'ga4' AS source,
    CAST(NULL AS STRING) AS hubspot_contact_id,
    CAST(NULL AS STRING) AS hubspot_company_id,
    CAST(NULL AS STRING) AS organization_name
FROM `justdata-ncrc.analytics_521852976.events_*`
WHERE event_name LIKE '%report%' OR event_name LIKE '%_generated';


-- ============================================================================
-- ADDITIONAL VIEWS FOR SPECIFIC ANALYTICS FEATURES
--
-- NOT CURRENTLY LIVE: none of the views below this point exist in
-- BigQuery today (confirmed via INFORMATION_SCHEMA.TABLES against both
-- justdata-ncrc.firebase_analytics and the abandoned justdata-f7da7
-- project -- neither has them). They read raw geo/device fields that
-- all_events doesn't carry (it only exposes the flattened columns
-- above), so they can't be rebuilt on top of all_events -- they still
-- need to read the raw events_* wildcard tables directly, same as
-- all_events's own live and ga4 branches do.
--
-- Updated below to point at the real justdata-ncrc project and union
-- both live export streams (firebase_analytics + analytics_521852976),
-- matching all_events's pattern. Still unverified against actual data
-- since they've never been created -- review before first use.
-- ============================================================================

-- View: User Locations
-- Aggregates user locations from Firebase Analytics events
CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.user_locations` AS
SELECT
    user_pseudo_id,
    geo.city AS city,
    geo.region AS state,
    geo.country AS country,
    device.category AS device_category,
    device.operating_system AS os,
    MAX(event_timestamp) AS last_activity,
    COUNT(*) AS event_count
FROM (
    SELECT user_pseudo_id, geo, device, event_timestamp, _TABLE_SUFFIX
    FROM `justdata-ncrc.firebase_analytics.events_*`
    UNION ALL
    SELECT user_pseudo_id, geo, device, event_timestamp, _TABLE_SUFFIX
    FROM `justdata-ncrc.analytics_521852976.events_*`
)
WHERE
    _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY
    user_pseudo_id,
    geo.city,
    geo.region,
    geo.country,
    device.category,
    device.operating_system;


-- View: Research Activity by County
-- Tracks which counties are being researched through LendSight, BizSight, BranchSight
CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.research_activity` AS
SELECT
    user_pseudo_id,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'county_fips') AS county_fips,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'state') AS state,
    event_name AS app_name,
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
    geo.city AS researcher_city,
    geo.region AS researcher_state
FROM (
    SELECT user_pseudo_id, event_params, event_name, event_timestamp, geo, _TABLE_SUFFIX
    FROM `justdata-ncrc.firebase_analytics.events_*`
    UNION ALL
    SELECT user_pseudo_id, event_params, event_name, event_timestamp, geo, _TABLE_SUFFIX
    FROM `justdata-ncrc.analytics_521852976.events_*`
)
WHERE
    event_name IN ('lendsight_report', 'bizsight_report', 'branchsight_report', 'dataexplorer_area_report')
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE());


-- View: Lender Interest
-- Tracks which lenders are being researched
CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.lender_interest` AS
SELECT
    user_pseudo_id,
    COALESCE(
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lender_name'),
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'institution_name'),
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'acquirer_name')
    ) AS lender_name,
    COALESCE(
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lei'),
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'cert')
    ) AS lender_id,
    event_name AS source_app,
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
    geo.city AS researcher_city,
    geo.region AS researcher_state
FROM (
    SELECT user_pseudo_id, event_params, event_name, event_timestamp, geo, _TABLE_SUFFIX
    FROM `justdata-ncrc.firebase_analytics.events_*`
    UNION ALL
    SELECT user_pseudo_id, event_params, event_name, event_timestamp, geo, _TABLE_SUFFIX
    FROM `justdata-ncrc.analytics_521852976.events_*`
)
WHERE
    event_name IN ('lendsight_report', 'dataexplorer_lender_report', 'mergermeter_report')
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE());


-- View: Coalition Opportunities (Counties)
-- Identifies counties being researched by multiple users/organizations
CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.coalition_opportunities_county` AS
SELECT
    county_fips,
    state,
    COUNT(DISTINCT user_pseudo_id) AS unique_users,
    COUNT(*) AS total_events,
    ARRAY_AGG(DISTINCT researcher_state IGNORE NULLS) AS researcher_states,
    MAX(event_timestamp) AS last_activity
FROM `justdata-ncrc.firebase_analytics.research_activity`
WHERE county_fips IS NOT NULL
GROUP BY county_fips, state
HAVING COUNT(DISTINCT user_pseudo_id) >= 2
ORDER BY unique_users DESC;


-- View: Coalition Opportunities (Lenders)
-- Identifies lenders being researched by multiple users/organizations
CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.coalition_opportunities_lender` AS
SELECT
    lender_name,
    lender_id,
    COUNT(DISTINCT user_pseudo_id) AS unique_users,
    COUNT(*) AS total_events,
    ARRAY_AGG(DISTINCT researcher_state IGNORE NULLS) AS researcher_states,
    ARRAY_AGG(DISTINCT source_app IGNORE NULLS) AS source_apps,
    MAX(event_timestamp) AS last_activity
FROM `justdata-ncrc.firebase_analytics.lender_interest`
WHERE lender_name IS NOT NULL
GROUP BY lender_name, lender_id
HAVING COUNT(DISTINCT user_pseudo_id) >= 2
ORDER BY unique_users DESC;


-- View: App Usage Summary
-- Daily summary of app usage by application
CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.app_usage_summary` AS
SELECT
    DATE(TIMESTAMP_MICROS(event_timestamp)) AS event_date,
    event_name AS app_name,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS unique_users
FROM (
    SELECT user_pseudo_id, event_name, event_timestamp, _TABLE_SUFFIX
    FROM `justdata-ncrc.firebase_analytics.events_*`
    UNION ALL
    SELECT user_pseudo_id, event_name, event_timestamp, _TABLE_SUFFIX
    FROM `justdata-ncrc.analytics_521852976.events_*`
)
WHERE
    event_name IN (
        'lendsight_report',
        'bizsight_report',
        'branchsight_report',
        'branchmapper_report',
        'mergermeter_report',
        'dataexplorer_area_report',
        'dataexplorer_lender_report'
    )
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY event_date, event_name
ORDER BY event_date DESC, event_count DESC;


-- View: User Activity Timeline
-- Daily activity counts for trend analysis
CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.user_activity_timeline` AS
SELECT
    DATE(TIMESTAMP_MICROS(event_timestamp)) AS activity_date,
    COUNT(DISTINCT user_pseudo_id) AS active_users,
    COUNT(*) AS total_events,
    COUNTIF(event_name = 'lendsight_report') AS lendsight_events,
    COUNTIF(event_name = 'bizsight_report') AS bizsight_events,
    COUNTIF(event_name = 'branchsight_report') AS branchsight_events,
    COUNTIF(event_name = 'branchmapper_report') AS branchmapper_events,
    COUNTIF(event_name = 'mergermeter_report') AS mergermeter_events,
    COUNTIF(event_name = 'dataexplorer_area_report') AS dataexplorer_area_events,
    COUNTIF(event_name = 'dataexplorer_lender_report') AS dataexplorer_lender_events
FROM (
    SELECT user_pseudo_id, event_name, event_timestamp, _TABLE_SUFFIX
    FROM `justdata-ncrc.firebase_analytics.events_*`
    UNION ALL
    SELECT user_pseudo_id, event_name, event_timestamp, _TABLE_SUFFIX
    FROM `justdata-ncrc.analytics_521852976.events_*`
)
WHERE
    event_name IN (
        'lendsight_report',
        'bizsight_report',
        'branchsight_report',
        'branchmapper_report',
        'mergermeter_report',
        'dataexplorer_area_report',
        'dataexplorer_lender_report'
    )
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY activity_date
ORDER BY activity_date DESC;


-- View: Top Counties by Research Interest
-- Identifies the most researched counties
CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.top_counties` AS
SELECT
    county_fips,
    state,
    COUNT(DISTINCT user_pseudo_id) AS unique_researchers,
    COUNT(*) AS total_reports,
    ARRAY_AGG(DISTINCT app_name IGNORE NULLS) AS apps_used,
    MAX(event_timestamp) AS last_activity
FROM `justdata-ncrc.firebase_analytics.research_activity`
WHERE county_fips IS NOT NULL
GROUP BY county_fips, state
ORDER BY unique_researchers DESC, total_reports DESC
LIMIT 100;


-- View: Top Lenders by Research Interest
-- Identifies the most researched lenders
CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.top_lenders` AS
SELECT
    lender_name,
    lender_id,
    COUNT(DISTINCT user_pseudo_id) AS unique_researchers,
    COUNT(*) AS total_views,
    ARRAY_AGG(DISTINCT source_app IGNORE NULLS) AS apps_used,
    ARRAY_AGG(DISTINCT researcher_state IGNORE NULLS) AS researcher_states,
    MAX(event_timestamp) AS last_activity
FROM `justdata-ncrc.firebase_analytics.lender_interest`
WHERE lender_name IS NOT NULL
GROUP BY lender_name, lender_id
ORDER BY unique_researchers DESC, total_views DESC
LIMIT 100;


-- ============================================================================
-- NOTES:
--
-- - all_events (above) is live and correct as of 2026-08-31 -- verified
--   directly against INFORMATION_SCHEMA.VIEWS, not assumed.
-- - Everything after it (user_locations through top_lenders) is a
--   best-effort reconstruction pointed at the real project/datasets and
--   has NOT been created or tested against live data. Before running
--   these against production, verify the event_params keys referenced
--   (county_fips, state, lender_name, lei, etc.) actually appear in
--   current export rows -- the source events changed shape at least once
--   already (the Firebase SDK -> GA4 export migration on 2026-01-27).
-- - To apply: run this file's statements against justdata-ncrc via
--   `bq query --use_legacy_sql=false --project_id=justdata-ncrc` or the
--   BigQuery Console. No script in this repo runs it automatically.
-- ============================================================================
