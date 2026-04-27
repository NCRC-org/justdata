    CREATE OR REPLACE VIEW `{TARGET_PROJECT}.{TARGET_DATASET}.all_events` AS

    -- Backfilled events from usage_log
    SELECT
        event_id,
        event_name,
        event_timestamp,
        user_id,
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
    FROM `{TARGET_PROJECT}.{TARGET_DATASET}.backfilled_events`

    -- TODO: Add UNION ALL with Firebase Analytics events once export is enabled
    -- The Firebase data will be in justdata-f7da7.analytics_*.events_*
    -- You'll need cross-project access or copy the data to this project
