        SELECT
            timestamp AS event_timestamp,
            app_name AS report_type,
            JSON_VALUE(parameters_json, '$.acquirer_name') AS acquirer_name,
            JSON_VALUE(parameters_json, '$.target_name') AS target_name,
            JSON_VALUE(parameters_json, '$.acquirer_lei') AS acquirer_lei,
            JSON_VALUE(parameters_json, '$.target_lei') AS target_lei,
            user_id,
            user_email
        FROM `justdata-ncrc.cache.usage_log`
        WHERE app_name = 'mergermeter'
            AND error_message IS NULL
            AND (JSON_VALUE(parameters_json, '$.acquirer_lei') = '{lender_id}'
                 OR JSON_VALUE(parameters_json, '$.target_lei') = '{lender_id}')
            AND {user_filter_usage}
            {date_filter}
        ORDER BY timestamp DESC
        LIMIT 500
