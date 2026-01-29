-- Mortgage Report SQL Template
-- Uses NCRC Member Report methodology with COALESCE for race/ethnicity classification
-- OPTIMIZED: Now uses justdata.de_hmda table with pre-computed race/ethnicity and income flags
-- This makes queries 5-10x faster by eliminating on-the-fly calculations
-- 
-- Filters: 
--   action_taken = '1' (originated loans only)
--   occupancy_type = '1' (owner-occupied)
--   loan_purpose: dynamic based on @loan_purpose parameter
--     - 'all': all loan purposes
--     - 'purchase': loan_purpose = '1' (home purchase)
--     - 'refinance': loan_purpose IN ('31','32') (refinance and cash-out refinance)
--     - 'equity': loan_purpose IN ('2','4') (home equity lending)
--   total_units IN ('1','2','3','4') (1-4 units)
--   construction_method = '1' (site-built)
--   reverse_mortgage != '1' (exclude reverse mortgages)
-- 
-- Note: Uses justdata.de_hmda table which has:
--   - Pre-computed race/ethnicity flags (is_hispanic, is_black, is_asian, etc.)
--   - Pre-computed income category flags (is_lmib, is_low_income_borrower, etc.)
--   - Pre-computed tract category flags (is_lmict, is_mmct, etc.)
--   - Connecticut planning region normalization already applied (geoid5)
--   - Lender names and types already joined
-- Note: Multi-racial is defined as 2+ DISTINCT main race categories (not just multiple subcategories of the same race)
--   Main categories: 1=Native American, 2=Asian (includes 2,21-27), 3=Black, 4=HoPI (includes 4,41-44), 5=White

SELECT
    h.lei,
    h.activity_year as year,
    h.county_code,
    h.county_state,  -- Already joined in de_hmda
    -- geoid5: Already normalized in de_hmda (Connecticut planning regions already applied)
    h.geoid5,
    -- Tract information for quartile calculation
    h.tract_code,
    h.tract_minority_population_percent,
    h.tract_to_msa_income_percentage,
    -- Lender information (already joined in de_hmda)
    MAX(h.lender_name) as lender_name,
    MAX(h.lender_type) as lender_type,
    -- Loan purpose (needed for market concentration analysis)
    h.loan_purpose,
    -- Loan counts
    COUNT(*) as total_originations,
    -- Borrower demographics (using pre-computed flags from de_hmda)
    -- Much faster than calculating on-the-fly!
    COUNTIF(h.is_hispanic) as hispanic_originations,
    -- Race classifications (using pre-computed flags from de_hmda)
    COUNTIF(h.is_black) as black_originations,
    COUNTIF(h.is_asian) as asian_originations,
    COUNTIF(h.is_white) as white_originations,
    COUNTIF(h.is_native_american) as native_american_originations,
    COUNTIF(h.is_hopi) as hopi_originations,
    COUNTIF(h.is_multi_racial) as multi_racial_originations,
    -- Income category counts (using pre-computed flags from de_hmda)
    COUNTIF(h.is_lmib) as lmib_originations,
    COUNTIF(h.is_low_income_borrower) as low_income_borrower_originations,
    COUNTIF(h.is_moderate_income_borrower) as moderate_income_borrower_originations,
    COUNTIF(h.is_middle_income_borrower) as middle_income_borrower_originations,
    COUNTIF(h.is_upper_income_borrower) as upper_income_borrower_originations,
    -- Tract category counts (using pre-computed flags from de_hmda)
    COUNTIF(h.is_lmict) as lmict_originations,
    COUNTIF(h.is_low_income_tract) as low_income_tract_originations,
    COUNTIF(h.is_moderate_income_tract) as moderate_income_tract_originations,
    COUNTIF(h.is_middle_income_tract) as middle_income_tract_originations,
    COUNTIF(h.is_upper_income_tract) as upper_income_tract_originations,
    COUNTIF(h.is_mmct) as mmct_originations,
    -- Loan amount totals
    SUM(h.loan_amount) as total_loan_amount,
    -- Average loan amount
    AVG(h.loan_amount) as avg_loan_amount,
    -- Loan cost metrics (for Loan Costs tables)
    AVG(h.property_value) as avg_property_value,
    AVG(h.interest_rate) as avg_interest_rate,
    AVG(h.total_loan_costs) as avg_total_loan_costs,
    AVG(h.origination_charges) as avg_origination_charges,
    -- Income information
    AVG(h.income) as avg_income,
    -- Check if loan has demographic data (using pre-computed flag from de_hmda)
    COUNTIF(h.has_demographic_data) as loans_with_demographic_data
FROM `justdata-ncrc.shared.de_hmda` h
-- No joins needed! Everything is already in de_hmda:
-- - county_state is already joined from geo.cbsa_to_county
-- - lender_name and lender_type are already joined from hmda.lenders18
-- - geoid5 is already normalized (Connecticut planning regions applied)
WHERE h.county_state = @county
    AND h.activity_year = @year
    AND h.action_taken = '1'  -- Originated loans only
    AND h.occupancy_type = '1'  -- Owner-occupied
    AND h.total_units IN ('1','2','3','4')  -- 1-4 units
    AND h.construction_method = '1'  -- Site-built
    AND (h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages
    -- Loan purpose filter (dynamic based on @loan_purpose parameter)
    -- @loan_purpose can be 'all' or comma-separated like 'purchase,refinance' or 'purchase'
    AND (
        -- If 'all' or all three types are selected, include all loan purposes
        @loan_purpose = 'all'
        OR
        -- Otherwise, filter by selected purposes using OR logic
        (
            (REGEXP_CONTAINS(@loan_purpose, r'purchase') AND h.loan_purpose = '1')
            OR
            (REGEXP_CONTAINS(@loan_purpose, r'refinance') AND h.loan_purpose IN ('31','32'))
            OR
            (REGEXP_CONTAINS(@loan_purpose, r'equity') AND h.loan_purpose IN ('2','4'))
        )
    )
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, h.loan_purpose
ORDER BY lender_name, county_state, year, tract_code, h.loan_purpose

