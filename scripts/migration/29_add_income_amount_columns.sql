-- Migration Script 29: Add income-based AMOUNT columns + unknown tracking to sb_county_summary
-- The existing table has income-based LOAN COUNT columns (low_income_loans, etc.)
-- but loan AMOUNTS are not broken down by income category.
-- This migration rebuilds the table adding amount columns for each income group,
-- plus unknown_income_loans and unknown_income_amount for correct denominator calculations.
--
-- Source: hdma1-242116.sb.disclosure
-- Destination: justdata-ncrc.bizsight.sb_county_summary
--
-- income_group_total encoding (4 formats, never mixed within a bank/county/year):
--   Format 1 (summary):     '101'=Low, '102'=Moderate, '103'=Middle, '104'=Upper, '105'-'106'=Unknown
--   Format 2 (subcategory):  '001'-'005'=Low, '006'-'008'=Moderate, '009'-'010'=Middle, '011'-'013'=Upper, '014'-'015'=Unknown
--   Format 3 (single-digit): '1'=Low, '2'=Moderate, '3'=Middle, '4'=Upper, '14'-'15'=Unknown
--   Format 4 (unpadded, 2019 only): '5'=Low, '6'-'8'=Moderate, '9'-'10'=Middle, '11'-'13'=Upper
--
-- Last run: 2026-02-07

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
    -- Income category LOAN COUNTS
    SUM(CASE WHEN d.income_group_total IN ('1','2','001','002','003','004','005','006','007','008','5','6','7','8','101','102')
        THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as lmi_tract_loans,
    SUM(CASE WHEN d.income_group_total IN ('1','001','002','003','004','005','5','101')
        THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as low_income_loans,
    SUM(CASE WHEN d.income_group_total IN ('2','006','007','008','6','7','8','102')
        THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as moderate_income_loans,
    SUM(CASE WHEN d.income_group_total IN ('3','4','009','010','011','012','013','9','10','11','12','13','103','104')
        THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as midu_income_loans,
    SUM(CASE WHEN d.income_group_total IN ('14','15','014','015','105','106')
        THEN d.num_under_100k + d.num_100k_250k + d.num_250k_1m ELSE 0 END) as unknown_income_loans,
    -- Income category LOAN AMOUNTS
    SUM(CASE WHEN d.income_group_total IN ('1','2','001','002','003','004','005','006','007','008','5','6','7','8','101','102')
        THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as lmi_tract_amount,
    SUM(CASE WHEN d.income_group_total IN ('1','001','002','003','004','005','5','101')
        THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as low_income_amount,
    SUM(CASE WHEN d.income_group_total IN ('2','006','007','008','6','7','8','102')
        THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as moderate_income_amount,
    SUM(CASE WHEN d.income_group_total IN ('3','4','009','010','011','012','013','9','10','11','12','13','103','104')
        THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as midu_income_amount,
    SUM(CASE WHEN d.income_group_total IN ('14','15','014','015','105','106')
        THEN d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m ELSE 0 END) as unknown_income_amount
FROM `hdma1-242116.sb.disclosure` d
LEFT JOIN `hdma1-242116.sb.lenders` l
    ON d.respondent_id = l.sb_resid AND d.year = l.sb_year
WHERE d.geoid5 IS NOT NULL
GROUP BY d.year, d.geoid5, d.respondent_id, l.sb_lender;

-- Verify: income categories should sum to total_loans (gap = 0 for all years)
SELECT
    year,
    SUM(total_loans) as total_loans,
    SUM(low_income_loans + moderate_income_loans + midu_income_loans + unknown_income_loans) as sum_of_categories,
    SUM(total_loans) - SUM(low_income_loans + moderate_income_loans + midu_income_loans + unknown_income_loans) as gap
FROM `justdata-ncrc.bizsight.sb_county_summary`
GROUP BY year
ORDER BY year;
