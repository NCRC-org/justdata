-- Migration Script 20: Copy cu_call_reports to justdata-ncrc
-- Source: hdma1-242116.credit_unions.cu_call_reports (~50K rows)
-- Destination: justdata-ncrc.lenderprofile.cu_call_reports
-- Type: Full copy

-- Create or replace the table with full copy from source
CREATE OR REPLACE TABLE `justdata-ncrc.lenderprofile.cu_call_reports` AS
SELECT *
FROM `hdma1-242116.credit_unions.cu_call_reports`;

-- Verify row count
SELECT 'cu_call_reports' as table_name, COUNT(*) as row_count
FROM `justdata-ncrc.lenderprofile.cu_call_reports`;
