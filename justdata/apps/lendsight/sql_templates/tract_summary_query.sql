-- Tract Summary Query Template
-- Queries de_hmda_tract_summary for LendSight minority/income tract tables
-- Used for: Minority Tracts table, Income Tracts table (dynamic quartile calculations)
--
-- IMPORTANT: This table already has filters pre-applied:
--   - action_taken = '1' (originations)
--   - occupancy_type = '1' (owner-occupied)
--   - total_units IN ('1','2','3','4')
--   - construction_method = '1' (site-built)
--   - reverse_mortgage excluded
--
-- Parameters:
--   @county: County state name (e.g., 'Baltimore, MD')
--   @year: Activity year
--   @loan_purpose: 'all', 'purchase', 'refinance', or 'equity'

SELECT
    lei,
    year,
    geoid5,
    county_state,
    tract_code,
    tract_minority_population_percent,  -- For minority quartile calculation
    tract_to_msa_income_percentage,     -- For income tract classification
    loan_purpose,
    lender_name,
    
    -- Race/ethnicity counts (subset for tract tables)
    total_originations,
    hispanic_originations,
    black_originations,
    asian_originations,
    white_originations,
    
    -- Tract income breakdown
    lmict_originations,
    low_income_tract_originations,
    moderate_income_tract_originations,
    middle_income_tract_originations,
    upper_income_tract_originations,
    mmct_originations,
    
    -- Loan amounts
    total_loan_amount

FROM `justdata-ncrc.lendsight.de_hmda_tract_summary`
WHERE county_state = @county
    AND year = @year
    -- Loan purpose filter
    AND (
        @loan_purpose = 'all'
        OR (@loan_purpose = 'purchase' AND loan_purpose = '1')
        OR (@loan_purpose = 'refinance' AND loan_purpose IN ('31','32'))
        OR (@loan_purpose = 'equity' AND loan_purpose IN ('2','4'))
    )
ORDER BY lender_name, tract_code, year
