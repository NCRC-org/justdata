-- Migration Script 17: Copy de_hmda to justdata-ncrc
-- Source: hdma1-242116.justdata.de_hmda (~50M rows)
-- Destination: justdata-ncrc.shared.de_hmda
-- Type: Full copy (derived table - original source is hmda.hmda with joins)
-- Note: This is a large table, expect long execution time

-- Create or replace the table with full copy from existing derived table
CREATE OR REPLACE TABLE `justdata-ncrc.shared.de_hmda` AS
SELECT *
FROM `hdma1-242116.justdata.de_hmda`;

-- Verify row count
SELECT 'de_hmda' as table_name, COUNT(*) as row_count
FROM `justdata-ncrc.shared.de_hmda`;
