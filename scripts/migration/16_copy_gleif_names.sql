-- Migration Script 16: Copy lender_names_gleif to justdata-ncrc
-- Source: hdma1-242116.hmda.lender_names_gleif (~15K rows)
-- Destination: justdata-ncrc.shared.lender_names_gleif
-- Type: Full copy

-- Create or replace the table with full copy from source
CREATE OR REPLACE TABLE `justdata-ncrc.shared.lender_names_gleif` AS
SELECT *
FROM `hdma1-242116.hmda.lender_names_gleif`;

-- Verify row count
SELECT 'lender_names_gleif' as table_name, COUNT(*) as row_count
FROM `justdata-ncrc.shared.lender_names_gleif`;
