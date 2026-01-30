-- Migration: Add user_id and user_email columns to usage_log table
-- This enables tracking who generated each report for analytics

-- Add user_id column (Firebase Auth UID)
ALTER TABLE `justdata-ncrc.cache.usage_log`
ADD COLUMN IF NOT EXISTS user_id STRING;

-- Add user_email column
ALTER TABLE `justdata-ncrc.cache.usage_log`
ADD COLUMN IF NOT EXISTS user_email STRING;

-- Verify the changes
SELECT column_name, data_type 
FROM `justdata-ncrc.cache.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'usage_log'
ORDER BY ordinal_position;
