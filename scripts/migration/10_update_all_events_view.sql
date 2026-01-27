-- Update all_events view to include new analytics dataset
-- Run this AFTER the first Firebase daily export completes (should be Jan 28, 2026)
-- 
-- Check if analytics dataset has data first:
-- SELECT COUNT(*) FROM `justdata-ncrc.analytics.events_*` WHERE _TABLE_SUFFIX >= '20260128'

CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.all_events` AS

-- Historical backfilled events (pre-Firebase migration)
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
FROM `justdata-ncrc.firebase_analytics.backfilled_events`

UNION ALL

-- Live Firebase export (Jan 22-26, 2026 - migrated from justdata-f7da7)
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
FROM `justdata-ncrc.firebase_analytics.events_*`
WHERE
    event_name IN (
        'lendsight_report',
        'bizsight_report',
        'branchsight_report',
        'dataexplorer_area_report',
        'dataexplorer_lender_report',
        'mergermeter_report',
        'lenderprofile_view',
        'branchmapper_report'
    )

UNION ALL

-- New Firebase export (Jan 28, 2026 onwards - from justdata-ncrc native Firebase)
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
FROM `justdata-ncrc.analytics.events_*`
WHERE
    _TABLE_SUFFIX >= '20260128'
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
