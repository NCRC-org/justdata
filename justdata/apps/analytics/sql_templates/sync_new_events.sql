            WITH new_events AS (
                SELECT
                    GENERATE_UUID() as event_id,
                    timestamp as event_timestamp,
                    CASE app_name
                        WHEN 'lendsight' THEN 'lendsight_report'
                        WHEN 'bizsight' THEN 'bizsight_report'
                        WHEN 'branchsight' THEN 'branchsight_report'
                        WHEN 'mergermeter' THEN 'mergermeter_report'
                        WHEN 'dataexplorer' THEN 'dataexplorer_report'
                        ELSE CONCAT(app_name, '_report')
                    END as event_name,
                    user_id,
                    user_email,
                    user_type,
                    CAST(NULL AS STRING) as organization_name,
                    -- Extract county_fips based on app type
                    CASE 
                        WHEN app_name = 'bizsight' THEN 
                            COALESCE(
                                JSON_VALUE(parameters_json, '$.county_data.geoid5'),
                                JSON_VALUE(parameters_json, '$.county_data.GEOID5')
                            )
                        WHEN app_name IN ('lendsight', 'branchsight') THEN
                            -- For lendsight/branchsight, counties is a string like "County, State; County2, State"
                            -- We can't easily extract FIPS from this, so leave NULL for now
                            -- The coordinates will be looked up by county name instead
                            CAST(NULL AS STRING)
                        ELSE CAST(NULL AS STRING)
                    END as county_fips,
                    -- Extract county_name based on app type
                    CASE 
                        WHEN app_name = 'bizsight' THEN 
                            JSON_VALUE(parameters_json, '$.county_data.name')
                        WHEN app_name IN ('lendsight', 'branchsight') THEN
                            -- Extract first county name from semicolon-separated list
                            SPLIT(JSON_VALUE(parameters_json, '$.counties'), ';')[SAFE_OFFSET(0)]
                        ELSE CAST(NULL AS STRING)
                    END as county_name,
                    -- Extract state based on app type
                    CASE 
                        WHEN app_name = 'bizsight' THEN 
                            JSON_VALUE(parameters_json, '$.county_data.state_name')
                        WHEN app_name IN ('lendsight', 'branchsight') THEN
                            JSON_VALUE(parameters_json, '$.state_code')
                        ELSE CAST(NULL AS STRING)
                    END as state,
                    -- Extract lender_id (for mergermeter)
                    CASE 
                        WHEN app_name = 'mergermeter' THEN 
                            COALESCE(
                                JSON_VALUE(parameters_json, '$.acquirer_lei'),
                                JSON_VALUE(parameters_json, '$.target_lei')
                            )
                        ELSE CAST(NULL AS STRING)
                    END as lender_id,
                    -- Extract lender_name (typically not in params, leave NULL)
                    CAST(NULL AS STRING) as lender_name,
                    CAST(NULL AS STRING) as hubspot_contact_id,
                    CAST(NULL AS STRING) as hubspot_company_id
                FROM `{BACKFILL_PROJECT}.{BACKFILL_DATASET}.usage_log`
                WHERE app_name IN ('lendsight', 'bizsight', 'branchsight', 'mergermeter', 'dataexplorer')
                    AND error_message IS NULL  -- Only successful reports
                    {timestamp_filter}
            )
            SELECT
                event_id,
                event_timestamp,
                event_name,
                user_id,
                user_email,
                user_type,
                organization_name,
                county_fips,
                county_name,
                state,
                lender_id,
                lender_name,
                hubspot_contact_id,
                hubspot_company_id
            FROM new_events
