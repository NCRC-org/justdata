-- BigQuery Views for JustData Analytics
-- These views aggregate Firebase Analytics data exported to BigQuery
-- Project: justdata-f7da7
-- Dataset: analytics_MEASUREMENT_ID (where MEASUREMENT_ID is from Firebase)

-- ============================================================================
-- PREREQUISITES:
-- 1. Enable Firebase Analytics -> BigQuery export in Firebase Console:
--    Project Settings -> Integrations -> BigQuery -> Link
-- 2. Note the dataset name created (usually: analytics_MEASUREMENT_ID)
-- 3. Update the dataset references in these views accordingly
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
FROM `justdata-f7da7.analytics_*.events_*`
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
FROM `justdata-f7da7.analytics_*.events_*`
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
FROM `justdata-f7da7.analytics_*.events_*`
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
FROM `justdata-f7da7.analytics_*.events_*`
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
FROM `justdata-f7da7.analytics_*.events_*`
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
-- 1. Enable BigQuery export in Firebase Console:
--    - Go to Project Settings -> Integrations -> BigQuery
--    - Click "Link" to enable daily exports
--    - Note the dataset name (e.g., analytics_ZEJ2B1BG7B)
--
-- 2. Create the justdata_analytics dataset:
--    CREATE SCHEMA IF NOT EXISTS `justdata-f7da7.justdata_analytics`;
--
-- 3. Update the analytics_* references in these views to match your
--    Firebase Analytics dataset name (e.g., analytics_ZEJ2B1BG7B)
--
-- 4. Run each CREATE OR REPLACE VIEW statement in BigQuery Console
--
-- 5. Set up scheduled queries if you want materialized tables for performance
-- ============================================================================
