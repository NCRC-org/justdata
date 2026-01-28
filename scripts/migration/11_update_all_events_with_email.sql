-- Update all_events view to include user_email and display_name from event_params
-- Run with: bq query --project_id=justdata-ncrc --use_legacy_sql=false < scripts/migration/11_update_all_events_with_email.sql

CREATE OR REPLACE VIEW `justdata-ncrc.firebase_analytics.all_events` AS

-- Backfilled events from usage_log (historical data)
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
    hubspot_company_id,
    CAST(NULL AS STRING) AS user_email,
    CAST(NULL AS STRING) AS user_display_name
FROM `justdata-ncrc.firebase_analytics.backfilled_events`

UNION ALL

-- Firebase Analytics export (Jan 22-26, 2026 - from justdata-f7da7)
SELECT
    GENERATE_UUID() AS event_id,
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
    event_name,
    -- Prefer actual user_id, then firebase_uid from params, then user_pseudo_id
    COALESCE(
        NULLIF(user_id, ''),
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'firebase_uid'),
        user_pseudo_id
    ) AS user_id,
    -- Extract user_type from event_params
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'user_type') AS user_type,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'organization_name') AS organization_name,
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
    CAST(NULL AS STRING) AS hubspot_company_id,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'user_email') AS user_email,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'user_display_name') AS user_display_name
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

-- NEW: GA4 BigQuery export (Jan 27, 2026 onwards - justdata-ncrc)
SELECT
    GENERATE_UUID() AS event_id,
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
    event_name,
    -- Prefer actual user_id, then firebase_uid from params, then user_pseudo_id
    COALESCE(
        NULLIF(user_id, ''),
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'firebase_uid'),
        user_pseudo_id
    ) AS user_id,
    -- Extract user_type from event_params
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'user_type') AS user_type,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'organization_name') AS organization_name,
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
    CAST(NULL AS STRING) AS hubspot_company_id,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'user_email') AS user_email,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'user_display_name') AS user_display_name
FROM `justdata-ncrc.analytics_521852976.events_*`
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
