-- Migration Script 19: Copy cu_branches to justdata-ncrc
-- Source: hdma1-242116.credit_unions.cu_branches (~200K rows)
-- Destination: justdata-ncrc.lenderprofile.cu_branches
-- Type: Full copy

-- Create or replace the table with full copy from source
CREATE OR REPLACE TABLE `justdata-ncrc.lenderprofile.cu_branches` AS
SELECT *
FROM `hdma1-242116.credit_unions.cu_branches`;

-- Verify row count
SELECT 'cu_branches' as table_name, COUNT(*) as row_count
FROM `justdata-ncrc.lenderprofile.cu_branches`;
