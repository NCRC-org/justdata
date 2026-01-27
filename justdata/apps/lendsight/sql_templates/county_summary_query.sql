-- County Summary Query Template
-- Queries de_hmda_county_summary for LendSight reports
-- Used for: Demographic Overview, Income Borrowers, Top Lenders, Market Concentration, Summary, Trends
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
    loan_purpose,
    lender_name,
    
    -- Race/ethnicity counts
    total_originations,
    hispanic_originations,
    black_originations,
    asian_originations,
    white_originations,
    native_american_originations,
    hopi_originations,
    multi_racial_originations,
    
    -- Borrower income counts
    lmib_originations,
    low_income_borrower_originations,
    moderate_income_borrower_originations,
    middle_income_borrower_originations,
    upper_income_borrower_originations,
    
    -- Tract category totals (aggregated)
    lmict_originations,
    mmct_originations,
    
    -- Loan metrics
    total_loan_amount,
    avg_loan_amount,
    avg_property_value,
    avg_interest_rate,
    avg_total_loan_costs,
    avg_origination_charges,
    loans_with_demographic_data

FROM `justdata-ncrc.lendsight.de_hmda_county_summary`
WHERE county_state = @county
    AND year = @year
    -- Loan purpose filter
    AND (
        @loan_purpose = 'all'
        OR (@loan_purpose = 'purchase' AND loan_purpose = '1')
        OR (@loan_purpose = 'refinance' AND loan_purpose IN ('31','32'))
        OR (@loan_purpose = 'equity' AND loan_purpose IN ('2','4'))
    )
ORDER BY lender_name, year
