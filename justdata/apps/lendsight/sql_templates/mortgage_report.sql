-- Mortgage Report SQL Template
-- Uses NCRC Member Report methodology with COALESCE for race/ethnicity classification
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
-- Note: geoid5 is the same as county_code (already a 5-digit FIPS code)
-- Note: respondent_name is joined from the lenders18 table using LEI
-- Note: Race/ethnicity uses COALESCE to find first valid race code from race_1 through race_5

SELECT
    h.lei,
    h.activity_year as year,
    h.county_code,
    c.county_state,
    -- geoid5 is the same as county_code (already a 5-digit FIPS code)
    CAST(h.county_code AS STRING) as geoid5,
    -- Lender information from lenders18 table
    MAX(l.respondent_name) as lender_name,
    MAX(l.type_name) as lender_type,
    -- Loan counts
    COUNT(*) as total_originations,
    -- Borrower demographics (NCRC methodology: Check ethnicity first, then first race choice using COALESCE)
    -- First: Check if ANY ethnicity field indicates Hispanic (1, 11, 12, 13, 14)
    SUM(CASE 
        WHEN h.applicant_ethnicity_1 IN ('1','11','12','13','14')
            OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
            OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
            OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
            OR h.applicant_ethnicity_5 IN ('1','11','12','13','14')
        THEN 1 ELSE 0 
    END) as hispanic_originations,
    -- Race classifications: Only if NOT Hispanic, check FIRST race choice (race_1 first, then race_2, etc. using COALESCE)
    -- Black: first valid race code is '3'
    SUM(CASE 
        WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
            AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
            AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
            AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
            AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
            AND COALESCE(
                CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
                     THEN h.applicant_race_1 ELSE NULL END,
                CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
                     THEN h.applicant_race_2 ELSE NULL END,
                CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
                     THEN h.applicant_race_3 ELSE NULL END,
                CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
                     THEN h.applicant_race_4 ELSE NULL END,
                CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
                     THEN h.applicant_race_5 ELSE NULL END
            ) = '3'
        THEN 1 ELSE 0 
    END) as black_originations,
    -- Asian: first valid race code is '2' or '21'-'27'
    SUM(CASE 
        WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
            AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
            AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
            AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
            AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
            AND COALESCE(
                CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
                     THEN h.applicant_race_1 ELSE NULL END,
                CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
                     THEN h.applicant_race_2 ELSE NULL END,
                CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
                     THEN h.applicant_race_3 ELSE NULL END,
                CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
                     THEN h.applicant_race_4 ELSE NULL END,
                CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
                     THEN h.applicant_race_5 ELSE NULL END
            ) IN ('2','21','22','23','24','25','26','27')
        THEN 1 ELSE 0 
    END) as asian_originations,
    -- White: first valid race code is '5'
    SUM(CASE 
        WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
            AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
            AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
            AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
            AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
            AND COALESCE(
                CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
                     THEN h.applicant_race_1 ELSE NULL END,
                CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
                     THEN h.applicant_race_2 ELSE NULL END,
                CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
                     THEN h.applicant_race_3 ELSE NULL END,
                CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
                     THEN h.applicant_race_4 ELSE NULL END,
                CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
                     THEN h.applicant_race_5 ELSE NULL END
            ) = '5'
        THEN 1 ELSE 0 
    END) as white_originations,
    -- Native American: first valid race code is '1'
    SUM(CASE 
        WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
            AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
            AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
            AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
            AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
            AND COALESCE(
                CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
                     THEN h.applicant_race_1 ELSE NULL END,
                CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
                     THEN h.applicant_race_2 ELSE NULL END,
                CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
                     THEN h.applicant_race_3 ELSE NULL END,
                CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
                     THEN h.applicant_race_4 ELSE NULL END,
                CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
                     THEN h.applicant_race_5 ELSE NULL END
            ) = '1'
        THEN 1 ELSE 0 
    END) as native_american_originations,
    -- HoPI: first valid race code is '4', '41'-'44'
    SUM(CASE 
        WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
            AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
            AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
            AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
            AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
            AND COALESCE(
                CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
                     THEN h.applicant_race_1 ELSE NULL END,
                CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
                     THEN h.applicant_race_2 ELSE NULL END,
                CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
                     THEN h.applicant_race_3 ELSE NULL END,
                CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
                     THEN h.applicant_race_4 ELSE NULL END,
                CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
                     THEN h.applicant_race_5 ELSE NULL END
            ) IN ('4','41','42','43','44')
        THEN 1 ELSE 0 
    END) as hopi_originations,
    -- LMI Borrower (LMI Borrowers - based on income relative to MSA median)
    SUM(CASE 
        WHEN h.income IS NOT NULL
          AND h.ffiec_msa_md_median_family_income IS NOT NULL
          AND h.ffiec_msa_md_median_family_income > 0
          AND (CAST(h.income AS FLOAT64) * 1000.0) / 
              CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
        THEN 1 
        ELSE 0 
    END) as lmib_originations,
    -- LMICT (Low-to-Moderate Income Census Tract)
    SUM(CASE
        WHEN h.tract_to_msa_income_percentage IS NOT NULL
            AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80 
        THEN 1 ELSE 0 
    END) as lmict_originations,
    -- MMCT (Majority-Minority Census Tract)
    SUM(CASE
        WHEN h.tract_minority_population_percent IS NOT NULL
            AND CAST(h.tract_minority_population_percent AS FLOAT64) >= 50 
        THEN 1 ELSE 0 
    END) as mmct_originations,
    -- Loan amount totals
    SUM(h.loan_amount) as total_loan_amount,
    -- Average loan amount
    AVG(h.loan_amount) as avg_loan_amount,
    -- Income information
    AVG(h.income) as avg_income,
    -- Check if loan has demographic data (for denominator calculation)
    -- Must have either: Hispanic ethnicity OR explicit race selection
    SUM(CASE 
        WHEN (h.applicant_ethnicity_1 IN ('1','11','12','13','14')
              OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
              OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
              OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
              OR h.applicant_ethnicity_5 IN ('1','11','12','13','14'))
            OR COALESCE(
                CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
                     THEN h.applicant_race_1 ELSE NULL END,
                CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
                     THEN h.applicant_race_2 ELSE NULL END,
                CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
                     THEN h.applicant_race_3 ELSE NULL END,
                CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
                     THEN h.applicant_race_4 ELSE NULL END,
                CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
                     THEN h.applicant_race_5 ELSE NULL END
            ) IS NOT NULL
        THEN 1 ELSE 0 
    END) as loans_with_demographic_data
FROM hmda.hmda h
LEFT JOIN geo.cbsa_to_county c
    ON CAST(h.county_code AS STRING) = CAST(c.geoid5 AS STRING)
LEFT JOIN hmda.lenders18 l
    ON h.lei = l.lei
WHERE c.county_state = @county
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
GROUP BY 1, 2, 3, 4, 5
ORDER BY lender_name, county_state, year

