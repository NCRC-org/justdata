-- Migration Script 14: Expand sb_county_summary with revenue-under-1M columns
-- Source: hdma1-242116.sb.disclosure + sb.lenders
-- Destination: justdata-ncrc.bizsight.sb_county_summary
-- Type: Aggregated expansion (adds numsbrev_under_1m, amtsbrev_under_1m, respondent_id)

-- Note: Backup skipped if table doesn't exist

-- Create expanded summary table with additional columns for MergerMeter
-- Join with sb.lenders to get lender names
CREATE OR REPLACE TABLE `justdata-ncrc.bizsight.sb_county_summary` AS
SELECT
    CAST(d.year AS INT64) as year,
    d.geoid5,
    d.respondent_id,
    COALESCE(l.sb_lender, 'Unknown') as lender_name,
    -- Existing columns (pre-aggregated in disclosure table)
    SUM(d.num_under_100k) as num_under_100k,
    SUM(d.num_100k_250k) as num_100k_250k,
    SUM(d.num_250k_1m) as num_250k_1m,
    SUM(d.num_under_100k + d.num_100k_250k + d.num_250k_1m) as total_loans,
    SUM(d.amt_under_100k) as amt_under_100k,
    SUM(d.amt_100k_250k) as amt_100k_250k,
    SUM(d.amt_250k_1m) as amt_250k_1m,
    -- NEW columns for MergerMeter revenue-under-1M analysis
    SUM(d.numsbrev_under_1m) as numsbrev_under_1m,
    SUM(d.amtsbrev_under_1m) as amtsbrev_under_1m,
    -- LMI tract loans (from income_group_total)
    SUM(CASE WHEN d.income_group_total IN ('1', '2') THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as lmi_tract_loans,
    SUM(CASE WHEN d.income_group_total = '1' THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as low_income_loans,
    SUM(CASE WHEN d.income_group_total = '2' THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as moderate_income_loans,
    SUM(CASE WHEN d.income_group_total IN ('3', '4') THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as midu_income_loans
FROM `hdma1-242116.sb.disclosure` d
LEFT JOIN `hdma1-242116.sb.lenders` l 
    ON d.respondent_id = l.sb_resid AND d.year = l.sb_year
WHERE d.geoid5 IS NOT NULL
GROUP BY d.year, d.geoid5, d.respondent_id, l.sb_lender;

-- Verify row count and new columns
SELECT 
    'sb_county_summary' as table_name, 
    COUNT(*) as row_count,
    COUNT(DISTINCT respondent_id) as unique_lenders,
    SUM(numsbrev_under_1m) as total_rev_under_1m_loans
FROM `justdata-ncrc.bizsight.sb_county_summary`;
