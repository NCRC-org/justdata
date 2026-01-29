-- Migration Script 15: Copy hmda.lenders18 to justdata-ncrc
-- Source: hdma1-242116.hmda.lenders18 (~10K rows)
-- Destination: justdata-ncrc.lendsight.lenders18
-- Type: Full copy

-- Create or replace the table with full copy from source
CREATE OR REPLACE TABLE `justdata-ncrc.lendsight.lenders18` AS
SELECT *
FROM `hdma1-242116.hmda.lenders18`;

-- Verify row count
SELECT 'lenders18' as table_name, COUNT(*) as row_count
FROM `justdata-ncrc.lendsight.lenders18`;
