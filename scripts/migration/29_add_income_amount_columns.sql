-- Migration Script 29: Add income-based AMOUNT columns to sb_county_summary
-- The existing table has income-based LOAN COUNT columns (low_income_loans, etc.)
-- but loan AMOUNTS are not broken down by income category.
-- This migration rebuilds the table adding amount columns for each income group.
--
-- Source: hdma1-242116.sb.disclosure (income_group_total codes: '1'=Low, '2'=Moderate, '3'=Middle, '4'=Upper)
-- Destination: justdata-ncrc.bizsight.sb_county_summary

CREATE OR REPLACE TABLE `justdata-ncrc.bizsight.sb_county_summary` AS
SELECT
    CAST(d.year AS INT64) as year,
    d.geoid5,
    d.respondent_id,
    COALESCE(l.sb_lender, 'Unknown') as lender_name,
    -- Loan counts by size
    SUM(d.num_under_100k) as num_under_100k,
    SUM(d.num_100k_250k) as num_100k_250k,
    SUM(d.num_250k_1m) as num_250k_1m,
    SUM(d.num_under_100k + d.num_100k_250k + d.num_250k_1m) as total_loans,
    -- Loan amounts by size
    SUM(d.amt_under_100k) as amt_under_100k,
    SUM(d.amt_100k_250k) as amt_100k_250k,
    SUM(d.amt_250k_1m) as amt_250k_1m,
    -- Revenue-under-1M columns
    SUM(d.numsbrev_under_1m) as numsbrev_under_1m,
    SUM(d.amtsbrev_under_1m) as amtsbrev_under_1m,
    -- Income category LOAN COUNTS (existing)
    SUM(CASE WHEN d.income_group_total IN ('1', '2') THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as lmi_tract_loans,
    SUM(CASE WHEN d.income_group_total = '1' THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as low_income_loans,
    SUM(CASE WHEN d.income_group_total = '2' THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as moderate_income_loans,
    SUM(CASE WHEN d.income_group_total IN ('3', '4') THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as midu_income_loans,
    -- Income category LOAN AMOUNTS (NEW)
    SUM(CASE WHEN d.income_group_total IN ('1', '2') THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as lmi_tract_amount,
    SUM(CASE WHEN d.income_group_total = '1' THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as low_income_amount,
    SUM(CASE WHEN d.income_group_total = '2' THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as moderate_income_amount,
    SUM(CASE WHEN d.income_group_total IN ('3', '4') THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as midu_income_amount
FROM `hdma1-242116.sb.disclosure` d
LEFT JOIN `hdma1-242116.sb.lenders` l
    ON d.respondent_id = l.sb_resid AND d.year = l.sb_year
WHERE d.geoid5 IS NOT NULL
GROUP BY d.year, d.geoid5, d.respondent_id, l.sb_lender;

-- Verify: check that income amounts are populated
SELECT
    year,
    COUNT(*) as row_count,
    SUM(total_loans) as total_loans,
    SUM(low_income_loans) as low_income_loans_total,
    SUM(moderate_income_loans) as moderate_income_loans_total,
    SUM(low_income_amount) as low_income_amount_total,
    SUM(moderate_income_amount) as moderate_income_amount_total,
    SUM(lmi_tract_amount) as lmi_tract_amount_total,
    SUM(midu_income_amount) as midu_income_amount_total
FROM `justdata-ncrc.bizsight.sb_county_summary`
GROUP BY year
ORDER BY year;
