        SELECT
            CASE
                -- JustData Apps (order matters - most specific first)
                WHEN LOWER(query) LIKE '%de_hmda%' OR LOWER(query) LIKE '%lendsight%' OR user_email LIKE 'lendsight@%' THEN 'LendSight'
                WHEN LOWER(query) LIKE '%sb_%' OR LOWER(query) LIKE '%bizsight%' OR LOWER(query) LIKE '%disclosure%' OR user_email LIKE 'bizsight@%' THEN 'BizSight'
                WHEN LOWER(query) LIKE '%sod%' OR LOWER(query) LIKE '%branchsight%' OR LOWER(query) LIKE '%fdic%' OR user_email LIKE 'branchsight@%' THEN 'BranchSight'
                WHEN LOWER(query) LIKE '%mergermeter%' OR user_email LIKE 'mergermeter@%' THEN 'MergerMeter'
                WHEN LOWER(query) LIKE '%dataexplorer%' OR user_email LIKE 'dataexplorer@%' THEN 'DataExplorer'
                WHEN LOWER(query) LIKE '%lenderprofile%' OR user_email LIKE 'lenderprofile@%' THEN 'LenderProfile'
                WHEN LOWER(query) LIKE '%electwatch%' OR user_email LIKE 'electwatch@%' THEN 'ElectWatch'
                WHEN user_email LIKE 'branchmapper@%' THEN 'BranchMapper'
                
                -- Platform Services
                WHEN LOWER(query) LIKE '%analytics%' OR LOWER(query) LIKE '%all_events%' OR LOWER(query) LIKE '%backfilled%' OR user_email LIKE 'analytics@%' THEN 'Analytics'
                WHEN user_email LIKE 'firebase-admin@%' OR LOWER(query) LIKE '%firebase_analytics%' THEN 'Firebase'
                WHEN LOWER(query) LIKE '%usage_log%' OR LOWER(query) LIKE '%.cache.%' THEN 'Cache/Logging'
                
                -- Infrastructure / Metadata
                WHEN LOWER(query) LIKE '%information_schema%' THEN 'Metadata Queries'
                WHEN LOWER(query) LIKE '%__tables__%' OR LOWER(query) LIKE '%__partitions__%' THEN 'Metadata Queries'
                
                -- External Tools
                WHEN user_email LIKE '%@bigquery-public-data%' THEN 'Public Data'
                WHEN user_email LIKE '%looker%' OR LOWER(query) LIKE '%looker%' THEN 'Looker/Data Studio'
                WHEN user_email LIKE '%dataform%' OR LOWER(query) LIKE '%dataform%' THEN 'Dataform'
                WHEN user_email LIKE '%scheduled%' OR job_id LIKE 'scheduled_query%' THEN 'Scheduled Queries'
                
                -- Console / Manual queries (catch-all for known GCP service accounts)
                WHEN user_email LIKE '%gserviceaccount.com' THEN 'Service Accounts'
                
                ELSE 'Other/Manual'
            END as app_name,
            COUNT(*) as query_count,
            SUM(total_bytes_processed) as total_bytes,
            SUM(total_bytes_billed) as total_bytes_billed
        FROM `{project}`.`{region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
            AND job_type = 'QUERY' AND state = 'DONE' AND error_result IS NULL
        GROUP BY app_name
