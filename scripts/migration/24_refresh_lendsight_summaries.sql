-- Migration Script 24: Refresh LendSight summary tables from shared.de_hmda
-- Source: justdata-ncrc.shared.de_hmda
-- Destination: justdata-ncrc.lendsight.de_hmda_county_summary, de_hmda_tract_summary
-- Type: Aggregated refresh (~500K rows total)
-- Run AFTER de_hmda is copied (script 17)

-- Refresh county summary (with clustering)
CREATE OR REPLACE TABLE `justdata-ncrc.lendsight.de_hmda_county_summary`
CLUSTER BY year, geoid5 AS
SELECT
    activity_year as year,
    county_code as geoid5,
    lei,
    lender_name,
    COUNT(*) as total_applications,
    SUM(CASE WHEN action_taken = '1' THEN 1 ELSE 0 END) as total_originations,
    SUM(CASE WHEN action_taken = '1' THEN loan_amount ELSE 0 END) as total_loan_amount,
    -- Demographic breakdowns
    SUM(CASE WHEN action_taken = '1' AND is_hispanic THEN 1 ELSE 0 END) as hispanic_originations,
    SUM(CASE WHEN action_taken = '1' AND is_black THEN 1 ELSE 0 END) as black_originations,
    SUM(CASE WHEN action_taken = '1' AND is_white THEN 1 ELSE 0 END) as white_originations,
    SUM(CASE WHEN action_taken = '1' AND is_asian THEN 1 ELSE 0 END) as asian_originations,
    -- Income breakdowns
    SUM(CASE WHEN action_taken = '1' AND is_lmib THEN 1 ELSE 0 END) as lmi_borrower_originations,
    -- Tract characteristic breakdowns
    SUM(CASE WHEN action_taken = '1' AND is_lmict THEN 1 ELSE 0 END) as lmi_tract_originations,
    SUM(CASE WHEN action_taken = '1' AND is_mmct THEN 1 ELSE 0 END) as majority_minority_tract_originations,
    -- Loan purpose breakdowns
    SUM(CASE WHEN action_taken = '1' AND loan_purpose = '1' THEN 1 ELSE 0 END) as purchase_originations,
    SUM(CASE WHEN action_taken = '1' AND loan_purpose = '31' THEN 1 ELSE 0 END) as refinance_originations,
    SUM(CASE WHEN action_taken = '1' AND loan_purpose = '32' THEN 1 ELSE 0 END) as cash_out_refi_originations,
    SUM(CASE WHEN action_taken = '1' AND loan_purpose = '4' THEN 1 ELSE 0 END) as home_equity_originations
FROM `justdata-ncrc.shared.de_hmda`
WHERE county_code IS NOT NULL
GROUP BY activity_year, county_code, lei, lender_name;

-- Refresh tract summary (with clustering)
CREATE OR REPLACE TABLE `justdata-ncrc.lendsight.de_hmda_tract_summary`
CLUSTER BY year, geoid5, geoid11 AS
SELECT
    activity_year as year,
    census_tract as geoid11,
    county_code as geoid5,
    lei,
    lender_name,
    COUNT(*) as total_applications,
    SUM(CASE WHEN action_taken = '1' THEN 1 ELSE 0 END) as total_originations,
    SUM(CASE WHEN action_taken = '1' THEN loan_amount ELSE 0 END) as total_loan_amount,
    -- Demographic breakdowns
    SUM(CASE WHEN action_taken = '1' AND is_hispanic THEN 1 ELSE 0 END) as hispanic_originations,
    SUM(CASE WHEN action_taken = '1' AND is_black THEN 1 ELSE 0 END) as black_originations,
    SUM(CASE WHEN action_taken = '1' AND is_white THEN 1 ELSE 0 END) as white_originations,
    SUM(CASE WHEN action_taken = '1' AND is_asian THEN 1 ELSE 0 END) as asian_originations,
    -- Income breakdowns  
    SUM(CASE WHEN action_taken = '1' AND is_lmib THEN 1 ELSE 0 END) as lmi_borrower_originations,
    -- Tract characteristics
    MAX(CAST(is_lmict AS INT64)) as is_lmi_tract,
    MAX(CAST(is_mmct AS INT64)) as is_majority_minority_tract
FROM `justdata-ncrc.shared.de_hmda`
WHERE census_tract IS NOT NULL
GROUP BY activity_year, census_tract, county_code, lei, lender_name;

-- Verify row counts
SELECT 'de_hmda_county_summary' as table_name, COUNT(*) as row_count 
FROM `justdata-ncrc.lendsight.de_hmda_county_summary`
UNION ALL
SELECT 'de_hmda_tract_summary' as table_name, COUNT(*) as row_count 
FROM `justdata-ncrc.lendsight.de_hmda_tract_summary`;
