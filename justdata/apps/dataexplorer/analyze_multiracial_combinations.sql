-- Analyze Multi-Racial Borrower Race Combinations Nationally
-- This query identifies all multi-racial borrowers across all HMDA data
-- and shows the breakdown of race combinations (Black/White, Black/Asian, etc.)

WITH multi_racial_loans AS (
    SELECT
        h.activity_year as year,
        -- Extract all main race categories for this borrower
        ARRAY(
            SELECT DISTINCT main_cat
            FROM UNNEST([
                CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_1 = '1' THEN '1'
                               WHEN h.applicant_race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_1 = '3' THEN '3'
                               WHEN h.applicant_race_1 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_1 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END,
                CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_2 = '1' THEN '1'
                               WHEN h.applicant_race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_2 = '3' THEN '3'
                               WHEN h.applicant_race_2 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_2 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END,
                CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_3 = '1' THEN '1'
                               WHEN h.applicant_race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_3 = '3' THEN '3'
                               WHEN h.applicant_race_3 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_3 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END,
                CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_4 = '1' THEN '1'
                               WHEN h.applicant_race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_4 = '3' THEN '3'
                               WHEN h.applicant_race_4 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_4 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END,
                CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_5 = '1' THEN '1'
                               WHEN h.applicant_race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_5 = '3' THEN '3'
                               WHEN h.applicant_race_5 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_5 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END
            ]) AS main_cat
            WHERE main_cat IS NOT NULL
            ORDER BY main_cat
        ) AS main_race_categories
    FROM `hdma1-242116.hmda.hmda` h
    WHERE 
        -- Multi-racial criteria: Non-Hispanic with 2+ distinct main race categories
        (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
        AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
        AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
        AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
        AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
        AND (
            SELECT COUNT(DISTINCT main_cat)
            FROM UNNEST([
                CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_1 = '1' THEN '1'
                               WHEN h.applicant_race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_1 = '3' THEN '3'
                               WHEN h.applicant_race_1 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_1 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END,
                CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_2 = '1' THEN '1'
                               WHEN h.applicant_race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_2 = '3' THEN '3'
                               WHEN h.applicant_race_2 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_2 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END,
                CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_3 = '1' THEN '1'
                               WHEN h.applicant_race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_3 = '3' THEN '3'
                               WHEN h.applicant_race_3 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_3 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END,
                CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_4 = '1' THEN '1'
                               WHEN h.applicant_race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_4 = '3' THEN '3'
                               WHEN h.applicant_race_4 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_4 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END,
                CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
                     THEN CASE WHEN h.applicant_race_5 = '1' THEN '1'
                               WHEN h.applicant_race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                               WHEN h.applicant_race_5 = '3' THEN '3'
                               WHEN h.applicant_race_5 IN ('4','41','42','43','44') THEN '4'
                               WHEN h.applicant_race_5 = '5' THEN '5'
                               ELSE NULL END
                     ELSE NULL END
            ]) AS main_cat
            WHERE main_cat IS NOT NULL
        ) >= 2
        AND CAST(h.activity_year AS INT64) >= 2018
),
race_combinations AS (
    SELECT
        -- Create a readable race combination string by mapping codes to names
        ARRAY_TO_STRING(
            ARRAY(
                SELECT 
                    CASE 
                        WHEN cat = '1' THEN 'Native American'
                        WHEN cat = '2' THEN 'Asian'
                        WHEN cat = '3' THEN 'Black'
                        WHEN cat = '4' THEN 'HoPI'
                        WHEN cat = '5' THEN 'White'
                        ELSE 'Unknown'
                    END
                FROM UNNEST(main_race_categories) AS cat
                ORDER BY cat
            ),
            '/'
        ) as race_combination,
        -- Also create a sorted string for grouping
        ARRAY_TO_STRING(main_race_categories, '/') as race_combo_code,
        COUNT(*) as loan_count
    FROM multi_racial_loans
    GROUP BY main_race_categories
)
SELECT
    race_combination,
    race_combo_code,
    loan_count,
    ROUND(loan_count * 100.0 / SUM(loan_count) OVER (), 2) as percentage
FROM race_combinations
ORDER BY loan_count DESC
LIMIT 50

