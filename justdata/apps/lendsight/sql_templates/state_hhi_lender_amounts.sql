-- Statewide lender loan amounts for the HHI comparison (Workflow 13277160986)
-- Same source table and filters as mortgage_report.sql, with the state in
-- place of the county, so the statewide HHI is computed exactly as the
-- county one: total_loan_amount summed by lender_name per year and loan
-- purpose (report_builder/sections/concentration.py).
--
-- Parameters:
--   @state_fips: two-digit state FIPS code (first two digits of geoid5)
--   @years: ARRAY<INT64> of activity years
--   @loan_purpose: 'all' or comma-separated purposes, as in mortgage_report.sql

SELECT
    h.activity_year AS year,
    h.loan_purpose,
    MAX(h.lender_name) AS lender_name,
    SUM(h.loan_amount) AS total_loan_amount
FROM `justdata-ncrc.dataexplorer.de_hmda` h
WHERE SUBSTR(h.geoid5, 1, 2) = @state_fips
    AND h.activity_year IN UNNEST(@years)
    AND h.action_taken = '1'  -- Originated loans only
    AND h.occupancy_type = '1'  -- Owner-occupied
    AND h.total_units IN ('1','2','3','4')  -- 1-4 units
    AND h.construction_method = '1'  -- Site-built
    AND (h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages
    AND (
        @loan_purpose = 'all'
        OR (
            (REGEXP_CONTAINS(@loan_purpose, r'purchase') AND h.loan_purpose = '1')
            OR (REGEXP_CONTAINS(@loan_purpose, r'refinance') AND h.loan_purpose IN ('31','32'))
            OR (REGEXP_CONTAINS(@loan_purpose, r'equity') AND h.loan_purpose IN ('2','4'))
        )
    )
GROUP BY h.activity_year, h.loan_purpose, h.lei
