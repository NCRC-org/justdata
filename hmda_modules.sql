# BASE TABLES
WITH race AS (
    SELECT DISTINCT
        applicant_ethnicity_1,
        applicant_race_1,
        CASE
            WHEN CAST(applicant_ethnicity_1 AS INT64) IN (1, 11, 12, 13, 14) THEN 'Hispanic'
            WHEN CAST(applicant_race_1 AS INT64) = 1 THEN 'Native American'
            WHEN CAST(applicant_race_1 AS INT64) = 2 OR CAST(applicant_race_1 AS INT64) BETWEEN 21 AND 27 THEN 'Asian'
            WHEN CAST(applicant_race_1 AS INT64) = 3 THEN 'Black'
            WHEN CAST(applicant_race_1 AS INT64) = 4 OR CAST(applicant_race_1 AS INT64) BETWEEN 41 AND 44 THEN 'HoPI'
            WHEN CAST(applicant_race_1 AS INT64) = 5 THEN 'White'
            ELSE 'No Data'
        END AS combined_race_ethnicity
    FROM hmda.hmda
),
race_originations AS (
    SELECT
        activity_year,
        lei,
        county_code,
        combined_race_ethnicity,
        SUM(1) as total_originations
    FROM hmda.hmda
    LEFT JOIN justdata.race
        USING (applicant_race_1,applicant_ethnicity_1)
    WHERE
        action_taken = '1'
        AND occupancy_type = '1'
        AND loan_purpose = '1'
        AND total_units IN ('1','2','3','4')
        AND construction_method = '1'
        AND reverse_mortgage != '1'
    GROUP BY 1,2,3,4
),
borrower_tract_originations AS (
    SELECT
        activity_year,
        lei,
        county_code,
                SUM(CASE 
                        WHEN 
                            ((CASE
                                WHEN ffiec_msa_md_median_family_income = 0 THEN NULL
                                ELSE (income * 1000) / ffiec_msa_md_median_family_income
                            END) <= 0.8) 
                        THEN 1
                    ELSE 0
                    END) as lmib,
                SUM(CASE
                    WHEN tract_to_msa_income_percentage <= 80 THEN 1
                    ELSE 0
                END) as lmict,
                SUM(CASE
                    WHEN (tract_minority_population_percent >= 50) THEN 1
                    ELSE 0
                END) as mmct
    FROM hmda.hmda
    WHERE
        action_taken = '1'
        AND occupancy_type = '1'
        AND loan_purpose = '1'
        AND total_units IN ('1','2','3','4')
        AND construction_method = '1'
        AND reverse_mortgage != '1'
    GROUP BY 1,2,3
),


# MODULE 2 -- Mortgage Market Overview
module_2_race AS (
    SELECT
        activity_year,
        county_code,
        combined_race_ethnicity,
        SUM(1) as total_originations
    FROM hmda.hmda
    LEFT JOIN justdata.race
        USING (applicant_race_1,applicant_ethnicity_1)
    WHERE
        action_taken = '1'
        AND occupancy_type = '1'
        AND loan_purpose = '1'
        AND total_units IN ('1','2','3','4')
        AND construction_method = '1'
        AND reverse_mortgage != '1'
    GROUP BY 1,2,3,4
),
module_2_borrower_tract AS (
    SELECT
        activity_year,
        county_code,
                SUM(CASE 
                        WHEN 
                            ((CASE
                                WHEN ffiec_msa_md_median_family_income = 0 THEN NULL
                                ELSE (income * 1000) / ffiec_msa_md_median_family_income
                            END) <= 0.8) 
                        THEN 1
                    ELSE 0
                    END) as lmib,
                SUM(CASE
                    WHEN tract_to_msa_income_percentage <= 80 THEN 1
                    ELSE 0
                END) as lmict,
                SUM(CASE
                    WHEN (tract_minority_population_percent >= 50) THEN 1
                    ELSE 0
                END) as mmct
    FROM hmda.hmda
    WHERE
        action_taken = '1'
        AND occupancy_type = '1'
        AND loan_purpose = '1'
        AND total_units IN ('1','2','3','4')
        AND construction_method = '1'
        AND reverse_mortgage != '1'
    GROUP BY 1,2,3
),


# MODULE 3 -- Lender Peer Comparison
module_3_race AS (
    SELECT
        activity_year,
        lei,
        county_code,
        combined_race_ethnicity,
        SUM(1) as total_originations
    FROM hmda.hmda
    LEFT JOIN justdata.race
        USING (applicant_race_1,applicant_ethnicity_1)
    WHERE
        action_taken = '1'
        AND occupancy_type = '1'
        AND loan_purpose = '1'
        AND total_units IN ('1','2','3','4')
        AND construction_method = '1'
        AND reverse_mortgage != '1'
    GROUP BY 1,2,3,4
),
module_3_borrower_tract AS (
    SELECT
        activity_year,
        lei,
        county_code,
                SUM(CASE 
                        WHEN 
                            ((CASE
                                WHEN ffiec_msa_md_median_family_income = 0 THEN NULL
                                ELSE (income * 1000) / ffiec_msa_md_median_family_income
                            END) <= 0.8) 
                        THEN 1
                    ELSE 0
                    END) as lmib,
                SUM(CASE
                    WHEN tract_to_msa_income_percentage <= 80 THEN 1
                    ELSE 0
                END) as lmict,
                SUM(CASE
                    WHEN (tract_minority_population_percent >= 50) THEN 1
                    ELSE 0
                END) as mmct
    FROM hmda.hmda
    WHERE
        action_taken = '1'
        AND occupancy_type = '1'
        AND loan_purpose = '1'
        AND total_units IN ('1','2','3','4')
        AND construction_method = '1'
        AND reverse_mortgage != '1'
    GROUP BY 1,2,3
),


# MODULE 4 -- Denial Analysis
module_4_race AS (
        SELECT
        activity_year,
        county_code,
        combined_race_ethnicity,
        SUM(1) as total_originations
    FROM hmda.hmda
    LEFT JOIN justdata.race
        USING (applicant_race_1,applicant_ethnicity_1)
    WHERE
        action_taken = '3'
        AND occupancy_type = '1'
        AND loan_purpose = '1'
        AND total_units IN ('1','2','3','4')
        AND construction_method = '1'
        AND reverse_mortgage != '1'
    GROUP BY 1,2,3,4
),
module_4_borrower_tract AS (
    SELECT
        activity_year,
        county_code,
                SUM(CASE 
                        WHEN 
                            ((CASE
                                WHEN ffiec_msa_md_median_family_income = 0 THEN NULL
                                ELSE (income * 1000) / ffiec_msa_md_median_family_income
                            END) <= 0.8) 
                        THEN 1
                    ELSE 0
                    END) as lmib,
                SUM(CASE
                    WHEN tract_to_msa_income_percentage <= 80 THEN 1
                    ELSE 0
                END) as lmict,
                SUM(CASE
                    WHEN (tract_minority_population_percent >= 50) THEN 1
                    ELSE 0
                END) as mmct
    FROM hmda.hmda
    WHERE
        action_taken = '3'
        AND occupancy_type = '1'
        AND loan_purpose = '1'
        AND total_units IN ('1','2','3','4')
        AND construction_method = '1'
        AND reverse_mortgage != '1'
    GROUP BY 1,2,3
),


# MODULE 5 -- Loan Costs Analysis
module_5_lender_counts AS (
    SELECT
        activity_year,
        county_code,
        lei,
        SUM(total_originations) AS loan_volume
    FROM race_originations
    GROUP BY 1,2,3
    HAVING SUM(total_originations) > 1
),
module_5_peer_comparison AS (
    SELECT
        a.activity_year,
        a.county_code,
        a.lei,
        a.loan_volume AS subject_volume,
        ARRAY_AGG(
            STRUCT(b.lei AS peer_lei, b.loan_volume AS peer_volume)
            ORDER BY b.loan_volume DESC
            LIMIT 10
        ) AS peers
    FROM module_5_lender_counts a
    LEFT JOIN module_5_lender_counts b
        ON a.activity_year = b.activity_year
        AND a.county_code = b.county_code
        AND b.lei != a.lei
        AND b.loan_volume BETWEEN 0.50 * a.loan_volume AND 2.00 * a.loan_volume
    WHERE a.county_code IS NOT NULL
    GROUP BY 1,2,3,4
),

# MODULE 6 -- Geographic Disparities Analysis

# MODULE 7 -- Market Concentration Analysis

# MODULE 8 -- Loan Type Disparities Analysis

# MODULE 9 -- Investor vs Owner-Occupied Analysis

# MODULE 10 -- Fair Lending Statistical Testing -- ON HOLD