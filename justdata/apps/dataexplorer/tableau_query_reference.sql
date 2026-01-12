-- Tableau Query for Manufacturers and Traders Trust
-- Job ID: fdf9e906-2131-4f2a-b9b3-43a0e1befc44
-- Creation Time: 2025-12-22T22:24:19.854000+00:00
-- User: apiclient@hdma1-242116.iam.gserviceaccount.com


    SELECT
        job_id,
        creation_time,
        start_time,
        end_time,
        state,
        total_bytes_processed,
        user_email,
        query,
        statement_type,
        error_result
    FROM `hdma1-242116`.`region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
    WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 168 HOUR)
        AND job_type = 'QUERY'
        AND state = 'DONE'
        AND (
            UPPER(query) LIKE UPPER('%WWB2V0FCW3A0EE3ZJN75%')
            OR UPPER(query) LIKE UPPER('%Manufacturers%and%Traders%Trust%')
        )
    ORDER BY creation_time DESC
    LIMIT 50
    
