-- Create County-Level HMDA Summary Table
-- Aggregates loan-level data to county level for ~99% query cost reduction
-- Run this in BigQuery Console connected to justdata project

-- =============================================================================
-- Create the county summary table
-- Expected: ~10,000 rows per year, ~70,000 total
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.lendsight.de_hmda_county_summary`
PARTITION BY RANGE_BUCKET(year, GENERATE_ARRAY(2018, 2030, 1))
CLUSTER BY geoid5, lei
OPTIONS(
    description="County-level HMDA summary for LendSight, DataExplorer, MergerMeter. Aggregated from de_hmda for ~99% cost reduction."
)
AS
SELECT
    -- Identifiers (6 cols)
    lei,
    activity_year as year,
    LPAD(CAST(geoid5 AS STRING), 5, '0') as geoid5,
    county_state,
    loan_purpose,
    MAX(lender_name) as lender_name,
    
    -- Race/ethnicity counts (8 cols)
    COUNT(*) as total_originations,
    COUNTIF(is_hispanic) as hispanic_originations,
    COUNTIF(is_black) as black_originations,
    COUNTIF(is_asian) as asian_originations,
    COUNTIF(is_white) as white_originations,
    COUNTIF(is_native_american) as native_american_originations,
    COUNTIF(is_hopi) as hopi_originations,
    COUNTIF(is_multi_racial) as multi_racial_originations,
    
    -- Borrower income counts (5 cols)
    COUNTIF(is_lmib) as lmib_originations,
    COUNTIF(is_low_income_borrower) as low_income_borrower_originations,
    COUNTIF(is_moderate_income_borrower) as moderate_income_borrower_originations,
    COUNTIF(is_middle_income_borrower) as middle_income_borrower_originations,
    COUNTIF(is_upper_income_borrower) as upper_income_borrower_originations,
    
    -- Tract category totals (2 cols - aggregated, no breakdown)
    COUNTIF(is_lmict) as lmict_originations,
    COUNTIF(is_mmct) as mmct_originations,
    
    -- Loan metrics (7 cols - for DataExplorer Loan Costs)
    SUM(loan_amount) as total_loan_amount,
    AVG(loan_amount) as avg_loan_amount,
    AVG(SAFE_CAST(property_value AS FLOAT64)) as avg_property_value,
    AVG(SAFE_CAST(interest_rate AS FLOAT64)) as avg_interest_rate,
    AVG(SAFE_CAST(total_loan_costs AS FLOAT64)) as avg_total_loan_costs,
    AVG(SAFE_CAST(origination_charges AS FLOAT64)) as avg_origination_charges,
    COUNTIF(has_demographic_data) as loans_with_demographic_data

FROM `hdma1-242116.justdata.de_hmda`
WHERE action_taken = '1' 
  AND occupancy_type = '1'
  AND total_units IN ('1','2','3','4') 
  AND construction_method = '1'
  AND (reverse_mortgage IS NULL OR reverse_mortgage != '1')
GROUP BY lei, activity_year, geoid5, county_state, loan_purpose;

-- =============================================================================
-- Verification
-- =============================================================================

-- Row counts by year
SELECT 
    year,
    COUNT(*) as row_count,
    SUM(total_originations) as total_loans,
    COUNT(DISTINCT geoid5) as counties,
    COUNT(DISTINCT lei) as lenders
FROM `justdata-ncrc.lendsight.de_hmda_county_summary`
GROUP BY year
ORDER BY year;

-- Compare totals to source (should match)
SELECT 
    'county_summary' as source,
    SUM(total_originations) as total_loans
FROM `justdata-ncrc.lendsight.de_hmda_county_summary`
UNION ALL
SELECT 
    'source_de_hmda' as source,
    COUNT(*) as total_loans
FROM `hdma1-242116.justdata.de_hmda`
WHERE action_taken = '1' 
  AND occupancy_type = '1'
  AND total_units IN ('1','2','3','4') 
  AND construction_method = '1'
  AND (reverse_mortgage IS NULL OR reverse_mortgage != '1');

-- Table size
SELECT 
    table_id,
    ROUND(size_bytes / (1024*1024), 2) as size_mb,
    row_count
FROM `justdata-ncrc.lendsight.__TABLES__`
WHERE table_id = 'de_hmda_county_summary';
