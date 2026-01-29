-- Migration Script 13: Copy sb.lenders to justdata-ncrc
-- Source: hdma1-242116.sb.lenders (~5K rows)
-- Destination: justdata-ncrc.bizsight.sb_lenders
-- Type: Full copy

-- Create or replace the table with full copy from source
CREATE OR REPLACE TABLE `justdata-ncrc.bizsight.sb_lenders` AS
SELECT *
FROM `hdma1-242116.sb.lenders`;

-- Verify row count
SELECT 'sb_lenders' as table_name, COUNT(*) as row_count
FROM `justdata-ncrc.bizsight.sb_lenders`;
