-- Create Tract-Level HMDA Summary Table
-- Aggregates loan-level data to tract level for minority/income tract tables
-- Run this in BigQuery Console connected to justdata project

-- =============================================================================
-- Create the tract summary table
-- Expected: ~500,000 rows per year (tracts × lenders × purposes)
-- =============================================================================
CREATE OR REPLACE TABLE `justdata-ncrc.lendsight.de_hmda_tract_summary`
PARTITION BY RANGE_BUCKET(year, GENERATE_ARRAY(2018, 2030, 1))
CLUSTER BY geoid5, lei
OPTIONS(
    description="Tract-level HMDA summary for LendSight minority/income tract tables and DataExplorer neighborhood analysis. Includes tract characteristics for quartile calculations."
)
AS
SELECT
    -- Identifiers + tract info (9 cols)
    lei,
    activity_year as year,
    LPAD(CAST(geoid5 AS STRING), 5, '0') as geoid5,
    county_state,
    tract_code,
    tract_minority_population_percent,  -- For quartile calculation
    tract_to_msa_income_percentage,     -- For income classification
    loan_purpose,
    MAX(lender_name) as lender_name,
    
    -- Race/ethnicity counts (5 cols - subset for tract tables)
    COUNT(*) as total_originations,
    COUNTIF(is_hispanic) as hispanic_originations,
    COUNTIF(is_black) as black_originations,
    COUNTIF(is_asian) as asian_originations,
    COUNTIF(is_white) as white_originations,
    
    -- Tract income breakdown (6 cols - needed for income tract tables)
    COUNTIF(is_lmict) as lmict_originations,
    COUNTIF(is_low_income_tract) as low_income_tract_originations,
    COUNTIF(is_moderate_income_tract) as moderate_income_tract_originations,
    COUNTIF(is_middle_income_tract) as middle_income_tract_originations,
    COUNTIF(is_upper_income_tract) as upper_income_tract_originations,
    COUNTIF(is_mmct) as mmct_originations,
    
    -- Loan amounts (1 col - no cost metrics needed at tract level)
    SUM(loan_amount) as total_loan_amount

FROM `hdma1-242116.justdata.de_hmda`
WHERE action_taken = '1' 
  AND occupancy_type = '1'
  AND total_units IN ('1','2','3','4') 
  AND construction_method = '1'
  AND (reverse_mortgage IS NULL OR reverse_mortgage != '1')
GROUP BY 
    lei, 
    activity_year, 
    geoid5, 
    county_state, 
    tract_code, 
    tract_minority_population_percent, 
    tract_to_msa_income_percentage, 
    loan_purpose;

-- =============================================================================
-- Verification
-- =============================================================================

-- Row counts by year
SELECT 
    year,
    COUNT(*) as row_count,
    SUM(total_originations) as total_loans,
    COUNT(DISTINCT tract_code) as tracts,
    COUNT(DISTINCT lei) as lenders
FROM `justdata-ncrc.lendsight.de_hmda_tract_summary`
GROUP BY year
ORDER BY year;

-- Compare totals to source (should match)
SELECT 
    'tract_summary' as source,
    SUM(total_originations) as total_loans
FROM `justdata-ncrc.lendsight.de_hmda_tract_summary`
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

-- Table size comparison
SELECT 
    table_id,
    ROUND(size_bytes / (1024*1024), 2) as size_mb,
    row_count
FROM `justdata-ncrc.lendsight.__TABLES__`
WHERE table_id IN ('de_hmda_county_summary', 'de_hmda_tract_summary');
