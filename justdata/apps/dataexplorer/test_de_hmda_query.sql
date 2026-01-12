-- ============================================================================
-- Test Query: Verify de_hmda table works with updated SQL template
-- ============================================================================
-- This query tests the updated mortgage_report.sql template using de_hmda
-- Run this to verify everything works before deploying
-- ============================================================================

-- Test with a single county and year
DECLARE county STRING DEFAULT 'Baltimore County, Maryland';
DECLARE year INT64 DEFAULT 2024;
DECLARE loan_purpose STRING DEFAULT 'all';

SELECT
    h.lei,
    h.activity_year as year,
    h.county_code,
    h.county_state,
    h.geoid5,
    h.tract_code,
    h.tract_minority_population_percent,
    h.tract_to_msa_income_percentage,
    MAX(h.lender_name) as lender_name,
    MAX(h.lender_type) as lender_type,
    h.loan_purpose,
    COUNT(*) as total_originations,
    -- Race/ethnicity counts (using pre-computed flags)
    COUNTIF(h.is_hispanic) as hispanic_originations,
    COUNTIF(h.is_black) as black_originations,
    COUNTIF(h.is_asian) as asian_originations,
    COUNTIF(h.is_white) as white_originations,
    COUNTIF(h.is_native_american) as native_american_originations,
    COUNTIF(h.is_hopi) as hopi_originations,
    COUNTIF(h.is_multi_racial) as multi_racial_originations,
    -- Income category counts
    COUNTIF(h.is_lmib) as lmib_originations,
    COUNTIF(h.is_low_income_borrower) as low_income_borrower_originations,
    COUNTIF(h.is_moderate_income_borrower) as moderate_income_borrower_originations,
    COUNTIF(h.is_middle_income_borrower) as middle_income_borrower_originations,
    COUNTIF(h.is_upper_income_borrower) as upper_income_borrower_originations,
    -- Tract category counts
    COUNTIF(h.is_lmict) as lmict_originations,
    COUNTIF(h.is_low_income_tract) as low_income_tract_originations,
    COUNTIF(h.is_moderate_income_tract) as moderate_income_tract_originations,
    COUNTIF(h.is_middle_income_tract) as middle_income_tract_originations,
    COUNTIF(h.is_upper_income_tract) as upper_income_tract_originations,
    COUNTIF(h.is_mmct) as mmct_originations,
    -- Loan amounts
    SUM(h.loan_amount) as total_loan_amount,
    AVG(h.loan_amount) as avg_loan_amount,
    AVG(h.property_value) as avg_property_value,
    AVG(h.interest_rate) as avg_interest_rate,
    AVG(h.total_loan_costs) as avg_total_loan_costs,
    AVG(h.origination_charges) as avg_origination_charges,
    AVG(h.income) as avg_income,
    COUNTIF(h.has_demographic_data) as loans_with_demographic_data
FROM `hdma1-242116.justdata.de_hmda` h
WHERE h.county_state = county
    AND CAST(h.activity_year AS INT64) = year
    AND h.action_taken = '1'  -- Originated loans only
    AND h.occupancy_type = '1'  -- Owner-occupied
    AND h.total_units IN ('1','2','3','4')  -- 1-4 units
    AND h.construction_method = '1'  -- Site-built
    AND (h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages
    -- Loan purpose filter
    AND (
        loan_purpose = 'all'
        OR
        (
            (REGEXP_CONTAINS(loan_purpose, r'purchase') AND h.loan_purpose = '1')
            OR
            (REGEXP_CONTAINS(loan_purpose, r'refinance') AND h.loan_purpose IN ('31','32'))
            OR
            (REGEXP_CONTAINS(loan_purpose, r'equity') AND h.loan_purpose IN ('2','4'))
        )
    )
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, h.loan_purpose
ORDER BY lender_name, county_state, year, tract_code, h.loan_purpose
LIMIT 100;

-- ============================================================================
-- Expected Results:
-- ============================================================================
-- This should return results similar to the old query, but much faster
-- Verify:
-- 1. Row counts match (or are close to) previous results
-- 2. Race/ethnicity counts are reasonable (should sum to <= total_originations)
-- 3. No errors in execution
-- 4. Query completes quickly (should be 5-10x faster than old query)
-- ============================================================================

