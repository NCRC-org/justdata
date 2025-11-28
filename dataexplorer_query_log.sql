-- Full Query Generated for Area Analysis
-- Generated at: 2025-11-27T12:11:07.035466
-- Geoids: ['12053', '12057', '12101', '12103']... (total: 4)
-- Years: [2020, 2021, 2022, 2023, 2024]
-- Loan Purpose: ['1', '2', '3']
-- Action Taken: ['1']
-- Occupancy: ['1']
-- Units: ['1', '2', '3', '4']
-- Construction: ['1']
-- Exclude Reverse Mortgages: True


WITH filtered_hmda AS (
    SELECT 
        CAST(h.activity_year AS STRING) as activity_year,
        LPAD(CAST(h.county_code AS STRING), 5, '0') as geoid5,
        h.lei,
        h.loan_purpose,
        h.loan_amount,
        h.census_tract,
        h.tract_minority_population_percent,
        -- LMI Census Tract flag
        CASE 
            WHEN h.tract_to_msa_income_percentage IS NOT NULL
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80 
            THEN 1 ELSE 0 
        END as is_lmict,
        -- Census Tract income bracket flags
        CASE 
            WHEN h.tract_to_msa_income_percentage IS NOT NULL
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 50 
            THEN 1 ELSE 0 
        END as is_low_income_tract,
        CASE 
            WHEN h.tract_to_msa_income_percentage IS NOT NULL
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) > 50
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80 
            THEN 1 ELSE 0 
        END as is_moderate_income_tract,
        CASE 
            WHEN h.tract_to_msa_income_percentage IS NOT NULL
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) > 80
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 120 
            THEN 1 ELSE 0 
        END as is_middle_income_tract,
        CASE 
            WHEN h.tract_to_msa_income_percentage IS NOT NULL
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) > 120 
            THEN 1 ELSE 0 
        END as is_upper_income_tract,
        -- Income bracket flags for borrowers
        CASE 
            WHEN h.income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income > 0
              AND (CAST(h.income AS FLOAT64) * 1000.0) / 
                  CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 50.0
            THEN 1 ELSE 0 
        END as is_low_income,
        CASE 
            WHEN h.income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income > 0
              AND (CAST(h.income AS FLOAT64) * 1000.0) / 
                  CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 > 50.0
              AND (CAST(h.income AS FLOAT64) * 1000.0) / 
                  CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
            THEN 1 ELSE 0 
        END as is_moderate_income,
        CASE 
            WHEN h.income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income > 0
              AND (CAST(h.income AS FLOAT64) * 1000.0) / 
                  CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 > 80.0
              AND (CAST(h.income AS FLOAT64) * 1000.0) / 
                  CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 120.0
            THEN 1 ELSE 0 
        END as is_middle_income,
        CASE 
            WHEN h.income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income > 0
              AND (CAST(h.income AS FLOAT64) * 1000.0) / 
                  CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 > 120.0
            THEN 1 ELSE 0 
        END as is_upper_income,
        -- LMI Borrower flag (for backward compatibility)
        CASE 
            WHEN h.income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income > 0
              AND (CAST(h.income AS FLOAT64) * 1000.0) / 
                  CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
            THEN 1 ELSE 0 
        END as is_lmib,
        -- Majority-Minority Census Tract flag
        CASE 
            WHEN h.tract_minority_population_percent IS NOT NULL
                AND CAST(h.tract_minority_population_percent AS FLOAT64) > 50 
            THEN 1 ELSE 0 
        END as is_mmct,
        -- Race/Ethnicity classification
        CASE 
            WHEN h.applicant_ethnicity_1 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_5 IN ('1','11','12','13','14')
            THEN 1 ELSE 0 
        END as is_hispanic,
        CASE 
            WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
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
        END as is_black,
        CASE 
            WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
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
        END as is_asian,
        CASE 
            WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
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
        END as is_native_american,
        CASE 
            WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
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
                ) = '4'
            THEN 1 ELSE 0 
        END as is_hawaiian_pacific_islander,
        CASE 
            WHEN (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
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
        END as is_white
    FROM `hdma1-242116.hmda.hmda` h
    WHERE CAST(h.activity_year AS STRING) IN ('2020', '2021', '2022', '2023', '2024') AND h.state_code IS NOT NULL AND h.county_code IS NOT NULL AND LPAD(CAST(h.county_code AS STRING), 5, '0') IN ('12053', '12057', '12101', '12103') AND h.loan_purpose IN ('1', '2', '3') AND h.action_taken IN ('1') AND h.occupancy_type IN ('1') AND h.total_units IN ('1', '2', '3', '4') AND h.construction_method IN ('1') AND (h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')
)
SELECT 
    f.activity_year,
    f.lei,
    f.loan_purpose,
    -- Lender information (use ANY_VALUE to avoid duplicates from join)
    ANY_VALUE(l.respondent_name) as lender_name,
    ANY_VALUE(l.type_name) as lender_type,
    -- Census tract for matching with race data (use ANY_VALUE since we're aggregating at lender level)
    ANY_VALUE(f.census_tract) as census_tract,
    f.geoid5,
    -- Total metrics - count rows directly (each row is one loan record)
    COUNT(*) as total_metric,
    -- Total loan amount
    SUM(COALESCE(f.loan_amount, 0)) as total_loan_amount,
    -- Race/Ethnicity breakdowns (applicant race - kept for backward compatibility)
    COUNTIF(is_hispanic = 1) as hispanic_metric,
    COUNTIF(is_black = 1) as black_metric,
    COUNTIF(is_asian = 1) as asian_metric,
    COUNTIF(is_native_american = 1) as native_american_metric,
    COUNTIF(is_hawaiian_pacific_islander = 1) as hawaiian_pacific_islander_metric,
    COUNTIF(is_white = 1) as white_metric,
    -- Income breakdowns
    COUNTIF(is_lmib = 1) as lmib_metric,
    COUNTIF(is_low_income = 1) as low_income_metric,
    COUNTIF(is_moderate_income = 1) as moderate_income_metric,
    COUNTIF(is_middle_income = 1) as middle_income_metric,
    COUNTIF(is_upper_income = 1) as upper_income_metric,
    -- Neighborhood breakdowns
    COUNTIF(is_lmict = 1) as lmict_metric,
    COUNTIF(is_low_income_tract = 1) as low_income_tract_metric,
    COUNTIF(is_moderate_income_tract = 1) as moderate_income_tract_metric,
    COUNTIF(is_middle_income_tract = 1) as middle_income_tract_metric,
    COUNTIF(is_upper_income_tract = 1) as upper_income_tract_metric,
    COUNTIF(is_mmct = 1) as mmct_metric
FROM filtered_hmda f
LEFT JOIN (
    SELECT lei, 
           ANY_VALUE(respondent_name) as respondent_name,
           ANY_VALUE(type_name) as type_name
    FROM `hdma1-242116.hmda.lenders18`
    GROUP BY lei
) l
    ON f.lei = l.lei
GROUP BY f.activity_year, f.lei, f.loan_purpose, f.geoid5
ORDER BY f.activity_year, total_metric DESC


-- END OF QUERY --
