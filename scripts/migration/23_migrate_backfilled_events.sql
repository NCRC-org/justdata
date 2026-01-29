-- Migration Script 23: Ensure backfilled_events in firebase_analytics
-- Source: hdma1-242116.justdata_analytics.backfilled_events (if exists)
-- Destination: justdata-ncrc.firebase_analytics.backfilled_events
-- Type: Copy if needed (historical analytics data)

-- Note: This may already exist in firebase_analytics
-- Only run if backfilled_events doesn't exist in justdata-ncrc.firebase_analytics

-- Check if source exists and copy
CREATE TABLE IF NOT EXISTS `justdata-ncrc.firebase_analytics.backfilled_events` AS
SELECT *
FROM `hdma1-242116.justdata_analytics.backfilled_events`;

-- Verify row count
SELECT 'backfilled_events' as table_name, COUNT(*) as row_count
FROM `justdata-ncrc.firebase_analytics.backfilled_events`;
