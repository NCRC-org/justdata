-- Analysis of Multi-Racial Borrower Race Combinations
-- This query identifies multi-racial borrowers (non-Hispanic with 2+ races)
-- and shows what race combinations they identify as

WITH multi_racial_loans AS (
    SELECT
        h.activity_year as year,
        -- Collect all valid race codes for this loan into a sorted array
        ARRAY(
            SELECT DISTINCT race_code
            FROM UNNEST([
                CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') THEN h.applicant_race_1 ELSE NULL END,
                CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') THEN h.applicant_race_2 ELSE NULL END,
                CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') THEN h.applicant_race_3 ELSE NULL END,
                CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') THEN h.applicant_race_4 ELSE NULL END,
                CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') THEN h.applicant_race_5 ELSE NULL END
            ]) AS race_code
            WHERE race_code IS NOT NULL
            ORDER BY race_code
        ) AS all_races
    FROM `hdma1-242116.hmda.hmda` h
    WHERE 
        -- Test data filters (matching area analysis test)
        h.county_code = '24031'  -- Baltimore County, MD
        AND CAST(h.activity_year AS INT64) BETWEEN 2020 AND 2024
        AND h.action_taken IN ('1')  -- Originations
        AND h.occupancy_type = '1'  -- Owner-occupied
        AND h.loan_purpose IN ('1','31','32','2','4')  -- Purchase, refinance, equity
        AND h.total_units IN ('1','2','3','4')  -- 1-4 units
        AND h.construction_method = '1'  -- Site-built
        AND h.reverse_mortgage != '1'  -- Exclude reverse mortgages
        -- Multi-racial criteria: Non-Hispanic with 2+ races
        AND (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
        AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
        AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
        AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
        AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
        -- Count valid race codes - must have 2 or more
        AND (CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') THEN 1 ELSE 0 END +
             CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') THEN 1 ELSE 0 END +
             CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') THEN 1 ELSE 0 END +
             CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') THEN 1 ELSE 0 END +
             CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') THEN 1 ELSE 0 END) >= 2
),
race_categories AS (
    SELECT
        year,
        all_races,
        -- Map each race code to its main category
        (SELECT ARRAY_AGG(DISTINCT cat ORDER BY cat)
         FROM (
             SELECT 
                 CASE 
                     WHEN race = '1' THEN '1'
                     WHEN race IN ('2','21','22','23','24','25','26','27') THEN '2'
                     WHEN race = '3' THEN '3'
                     WHEN race IN ('4','41','42','43','44') THEN '4'
                     WHEN race = '5' THEN '5'
                     ELSE race
                 END AS cat
             FROM UNNEST(all_races) AS race
         )) AS main_categories
    FROM multi_racial_loans
),
race_labels AS (
    SELECT
        year,
        main_categories,
        ARRAY_TO_STRING(
            ARRAY(
                SELECT 
                    CASE 
                        WHEN cat = '1' THEN 'Native American'
                        WHEN cat = '2' THEN 'Asian'
                        WHEN cat = '3' THEN 'Black'
                        WHEN cat = '4' THEN 'HoPI'
                        WHEN cat = '5' THEN 'White'
                        ELSE CONCAT('Unknown(', cat, ')')
                    END
                FROM UNNEST(main_categories) AS cat
            ),
            ' + '
        ) AS race_combination_label,
        ARRAY_TO_STRING(main_categories, '+') AS race_codes,
        ARRAY_LENGTH(main_categories) AS num_races
    FROM race_categories
)
SELECT
    race_combination_label AS race_combination,
    race_codes,
    num_races,
    COUNT(*) AS total_loans,
    COUNT(DISTINCT year) AS years_present
FROM race_labels
GROUP BY race_combination_label, race_codes, num_races
ORDER BY COUNT(*) DESC, race_combination_label
