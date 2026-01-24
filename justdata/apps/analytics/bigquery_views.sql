-- BigQuery Views for JustData Analytics
-- These views aggregate Firebase Analytics data exported to BigQuery
-- Project: justdata-f7da7
-- Firebase Export Dataset: analytics_520863329
-- Analytics Views Dataset: justdata_analytics

-- ============================================================================
-- PREREQUISITES:
-- 1. Enable Firebase Analytics -> BigQuery export in Firebase Console:
--    Project Settings -> Integrations -> BigQuery -> Link
-- 2. Dataset name: analytics_520863329 (Firebase export)
-- 3. Grant BigQuery Data Viewer role to Cloud Run service account on hdma1-242116
--    for access to historical backfilled data
-- ============================================================================

-- ============================================================================
-- UNIFIED ALL_EVENTS VIEW (CRITICAL - Required by Analytics Dashboard)
-- Combines historical backfilled data with live Firebase export
-- ============================================================================

CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.all_events` AS

-- Historical backfilled data (Nov 24, 2025 - Jan 22, 2026)
-- Source: hdma1-242116.justdata_analytics.backfilled_events
SELECT
    event_id,
    event_timestamp,
    event_name,
    user_id,
    user_type,
    organization_name,
    county_fips,
    county_name,
    state,
    lender_id,
    lender_name,
    hubspot_contact_id,
    hubspot_company_id
FROM `hdma1-242116.justdata_analytics.backfilled_events`

UNION ALL

-- Live Firebase export (Jan 23, 2026 onwards)
-- Source: justdata-f7da7.analytics_520863329.events_*
-- Note: user_type, organization_name are enriched from Firestore at runtime
-- Use user_pseudo_id as fallback since user_id requires explicit setUserId() call
SELECT
    GENERATE_UUID() AS event_id,
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
    event_name,
    COALESCE(user_id, user_pseudo_id) AS user_id,
    CAST(NULL AS STRING) AS user_type,
    CAST(NULL AS STRING) AS organization_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'county_fips') AS county_fips,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'county_name') AS county_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'state') AS state,
    COALESCE(
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lender_id'),
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lei')
    ) AS lender_id,
    COALESCE(
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lender_name'),
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'respondent_name')
    ) AS lender_name,
    CAST(NULL AS STRING) AS hubspot_contact_id,
    CAST(NULL AS STRING) AS hubspot_company_id
FROM `justdata-f7da7.analytics_520863329.events_*`
WHERE
    _TABLE_SUFFIX >= '20260123'  -- Start after backfill end date
    AND event_name IN (
        'lendsight_report',
        'bizsight_report',
        'branchsight_report',
        'dataexplorer_area_report',
        'dataexplorer_lender_report',
        'mergermeter_report',
        'lenderprofile_view',
        'branchmapper_report'
    );


-- ============================================================================
-- ADDITIONAL VIEWS FOR SPECIFIC ANALYTICS FEATURES
-- ============================================================================

-- View: User Locations
-- Aggregates user locations from Firebase Analytics events
CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.user_locations` AS
SELECT
    user_pseudo_id,
    geo.city AS city,
    geo.region AS state,
    geo.country AS country,
    device.category AS device_category,
    device.operating_system AS os,
    MAX(event_timestamp) AS last_activity,
    COUNT(*) AS event_count
FROM `justdata-f7da7.analytics_520863329.events_*`
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
CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.research_activity` AS
SELECT
    user_pseudo_id,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'county_fips') AS county_fips,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'state') AS state,
    event_name AS app_name,
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
    geo.city AS researcher_city,
    geo.region AS researcher_state
FROM `justdata-f7da7.analytics_520863329.events_*`
WHERE
    event_name IN ('lendsight_report', 'bizsight_report', 'branchsight_report', 'dataexplorer_area_report')
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE());


-- View: Lender Interest
-- Tracks which lenders are being researched
CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.lender_interest` AS
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
FROM `justdata-f7da7.analytics_520863329.events_*`
WHERE
    event_name IN ('lendsight_report', 'lenderprofile_view', 'dataexplorer_lender_report', 'mergermeter_report')
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE());


-- View: Coalition Opportunities (Counties)
-- Identifies counties being researched by multiple users/organizations
CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.coalition_opportunities_county` AS
SELECT
    county_fips,
    state,
    COUNT(DISTINCT user_pseudo_id) AS unique_users,
    COUNT(*) AS total_events,
    ARRAY_AGG(DISTINCT researcher_state IGNORE NULLS) AS researcher_states,
    MAX(event_timestamp) AS last_activity
FROM `justdata-f7da7.justdata_analytics.research_activity`
WHERE county_fips IS NOT NULL
GROUP BY county_fips, state
HAVING COUNT(DISTINCT user_pseudo_id) >= 2
ORDER BY unique_users DESC;


-- View: Coalition Opportunities (Lenders)
-- Identifies lenders being researched by multiple users/organizations
CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.coalition_opportunities_lender` AS
SELECT
    lender_name,
    lender_id,
    COUNT(DISTINCT user_pseudo_id) AS unique_users,
    COUNT(*) AS total_events,
    ARRAY_AGG(DISTINCT researcher_state IGNORE NULLS) AS researcher_states,
    ARRAY_AGG(DISTINCT source_app IGNORE NULLS) AS source_apps,
    MAX(event_timestamp) AS last_activity
FROM `justdata-f7da7.justdata_analytics.lender_interest`
WHERE lender_name IS NOT NULL
GROUP BY lender_name, lender_id
HAVING COUNT(DISTINCT user_pseudo_id) >= 2
ORDER BY unique_users DESC;


-- View: App Usage Summary
-- Daily summary of app usage by application
CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.app_usage_summary` AS
SELECT
    DATE(TIMESTAMP_MICROS(event_timestamp)) AS event_date,
    event_name AS app_name,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS unique_users
FROM `justdata-f7da7.analytics_520863329.events_*`
WHERE
    event_name IN (
        'lendsight_report',
        'bizsight_report',
        'branchsight_report',
        'branchmapper_report',
        'mergermeter_report',
        'dataexplorer_area_report',
        'dataexplorer_lender_report',
        'lenderprofile_view'
    )
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY event_date, event_name
ORDER BY event_date DESC, event_count DESC;


-- View: User Activity Timeline
-- Daily activity counts for trend analysis
CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.user_activity_timeline` AS
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
    COUNTIF(event_name = 'dataexplorer_lender_report') AS dataexplorer_lender_events,
    COUNTIF(event_name = 'lenderprofile_view') AS lenderprofile_events
FROM `justdata-f7da7.analytics_520863329.events_*`
WHERE
    event_name IN (
        'lendsight_report',
        'bizsight_report',
        'branchsight_report',
        'branchmapper_report',
        'mergermeter_report',
        'dataexplorer_area_report',
        'dataexplorer_lender_report',
        'lenderprofile_view'
    )
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY activity_date
ORDER BY activity_date DESC;


-- View: Top Counties by Research Interest
-- Identifies the most researched counties
CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.top_counties` AS
SELECT
    county_fips,
    state,
    COUNT(DISTINCT user_pseudo_id) AS unique_researchers,
    COUNT(*) AS total_reports,
    ARRAY_AGG(DISTINCT app_name IGNORE NULLS) AS apps_used,
    MAX(event_timestamp) AS last_activity
FROM `justdata-f7da7.justdata_analytics.research_activity`
WHERE county_fips IS NOT NULL
GROUP BY county_fips, state
ORDER BY unique_researchers DESC, total_reports DESC
LIMIT 100;


-- View: Top Lenders by Research Interest
-- Identifies the most researched lenders
CREATE OR REPLACE VIEW `justdata-f7da7.justdata_analytics.top_lenders` AS
SELECT
    lender_name,
    lender_id,
    COUNT(DISTINCT user_pseudo_id) AS unique_researchers,
    COUNT(*) AS total_views,
    ARRAY_AGG(DISTINCT source_app IGNORE NULLS) AS apps_used,
    ARRAY_AGG(DISTINCT researcher_state IGNORE NULLS) AS researcher_states,
    MAX(event_timestamp) AS last_activity
FROM `justdata-f7da7.justdata_analytics.lender_interest`
WHERE lender_name IS NOT NULL
GROUP BY lender_name, lender_id
ORDER BY unique_researchers DESC, total_views DESC
LIMIT 100;


-- ============================================================================
-- SETUP INSTRUCTIONS:
--
-- 1. Firebase Analytics -> BigQuery export is ENABLED:
--    - Project: justdata-f7da7
--    - Dataset: analytics_520863329
--    - Export frequency: Daily
--
-- 2. Create the justdata_analytics dataset (if not exists):
--    CREATE SCHEMA IF NOT EXISTS `justdata-f7da7.justdata_analytics`;
--
-- 3. Run all CREATE OR REPLACE VIEW statements in BigQuery Console
--    IMPORTANT: Run the all_events view FIRST as other views may depend on it
--
-- 4. Grant cross-project access for the unified view:
--    The Cloud Run service account needs BigQuery Data Viewer role on hdma1-242116
--    to access historical backfilled data.
--
--    Service account: [PROJECT_NUMBER]-compute@developer.gserviceaccount.com
--    Or check Cloud Run service configuration for the actual service account.
--
--    In Google Cloud Console:
--    a) Go to hdma1-242116 project -> IAM
--    b) Add the service account from justdata-f7da7
--    c) Grant role: BigQuery Data Viewer
--
-- 5. Test the unified view:
--    SELECT COUNT(*) as total_events,
--           MIN(event_timestamp) as earliest,
--           MAX(event_timestamp) as latest
--    FROM `justdata-f7da7.justdata_analytics.all_events`;
--
--    Expected: Total should exceed 284 (backfill count), latest should be recent.
-- ============================================================================
