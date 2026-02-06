-- SB County Summary Query Template
-- Queries sb_county_summary for BizSight reports
-- This is a pre-aggregated table for ~99% cost reduction
--
-- Parameters:
--   @geoid5: County FIPS code (5-digit, zero-padded)
--   @years: List of years to query (optional)

SELECT
    geoid5,
    year,
    lender_name,
    
    -- Loan counts by size
    num_under_100k,
    num_100k_250k,
    num_250k_1m,
    total_loans,
    
    -- Loan amounts
    amt_under_100k,
    amt_100k_250k,
    amt_250k_1m,
    
    -- Pre-aggregated income category metrics (counts)
    lmi_tract_loans,
    low_income_loans,
    moderate_income_loans,
    midu_income_loans,

    -- Pre-aggregated income category metrics (amounts)
    lmi_tract_amount,
    low_income_amount,
    moderate_income_amount,
    midu_income_amount

FROM `justdata-ncrc.bizsight.sb_county_summary`
WHERE geoid5 = @geoid5
    AND (@years IS NULL OR year IN UNNEST(@years))
ORDER BY year, lender_name
