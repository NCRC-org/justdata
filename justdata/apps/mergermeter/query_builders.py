"""
Query builders for MergerMeter analysis.
Generates BigQuery SQL for HMDA and Small Business data (subject and peer).
Uses 50%-200% volume rule for peer selection.
"""


def build_hmda_subject_query(
    subject_lei: str,
    assessment_area_geoids: list,
    years: list,
    loan_purpose: str = None,
    action_taken: str = '1',
    occupancy_type: str = '1',
    total_units: str = '1-4',
    construction_method: str = '1',
    not_reverse: str = '1'
) -> str:
    """
    Build HMDA query for subject bank.
    
    Args:
        subject_lei: Bank's LEI (string)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings)
        years: List of years as strings
        loan_purpose: Optional loan purpose filter (e.g., '1' for home purchase)
    
    Returns:
        SQL query string
    """
    if not assessment_area_geoids:
        return f"""
SELECT 
    CAST(NULL AS STRING) as activity_year,
    CAST(NULL AS STRING) as cbsa_code,
    CAST(NULL AS INT64) as total_loans,
    CAST(NULL AS FLOAT64) as total_amount,
    CAST(NULL AS INT64) as lmict_loans,
    CAST(NULL AS FLOAT64) as lmict_percentage,
    CAST(NULL AS INT64) as lmib_loans,
    CAST(NULL AS FLOAT64) as lmib_percentage,
    CAST(NULL AS FLOAT64) as lmib_amount,
    CAST(NULL AS INT64) as mmct_loans,
    CAST(NULL AS FLOAT64) as mmct_percentage,
    CAST(NULL AS INT64) as minb_loans,
    CAST(NULL AS FLOAT64) as minb_percentage
WHERE FALSE
"""
    
    geoid5_list = "', '".join([str(g).zfill(5) for g in assessment_area_geoids])
    years_list = "', '".join([str(y) for y in years])
    
    # Build filter conditions dynamically
    loan_purpose_filter = ""
    if loan_purpose:
        if ',' in loan_purpose:
            # Multiple loan purposes
            purposes = [p.strip() for p in loan_purpose.split(',')]
            purpose_list = "', '".join(purposes)
            loan_purpose_filter = f"AND h.loan_purpose IN ('{purpose_list}')"
        else:
            loan_purpose_filter = f"AND h.loan_purpose = '{loan_purpose.strip()}'"
    
    # Build action_taken filter
    action_taken_filter = ""
    if action_taken:
        if ',' in action_taken:
            # Multiple action types (Applications: 1,2,3,4,5)
            actions = [a.strip() for a in action_taken.split(',')]
            action_list = "', '".join(actions)
            action_taken_filter = f"AND h.action_taken IN ('{action_list}')"
        else:
            # Single action type (Originations: 1)
            action_taken_filter = f"AND h.action_taken = '{action_taken.strip()}'"
    
    # Build occupancy_type filter
    occupancy_filter = ""
    if occupancy_type:
        if ',' in occupancy_type:
            # Multiple occupancy types
            occupancies = [o.strip() for o in occupancy_type.split(',')]
            occupancy_list = "', '".join(occupancies)
            occupancy_filter = f"AND h.occupancy_type IN ('{occupancy_list}')"
        else:
            # Single occupancy type
            occupancy_filter = f"AND h.occupancy_type = '{occupancy_type.strip()}'"
    
    # Build total_units filter
    units_filter = ""
    if total_units:
        if ',' in total_units:
            # Multiple unit types
            units = [u.strip() for u in total_units.split(',')]
            units_list = "', '".join(units)
            units_filter = f"AND h.total_units IN ('{units_list}')"
        else:
            # Single unit type
            units_filter = f"AND h.total_units = '{total_units.strip()}'"
    
    # Build construction_method filter
    construction_filter = ""
    if construction_method:
        if ',' in construction_method:
            # Multiple construction methods
            constructions = [c.strip() for c in construction_method.split(',')]
            construction_list = "', '".join(constructions)
            construction_filter = f"AND h.construction_method IN ('{construction_list}')"
        else:
            # Single construction method
            construction_filter = f"AND h.construction_method = '{construction_method.strip()}'"
    
    # Build reverse_mortgage filter
    reverse_filter = ""
    if not_reverse:
        if ',' in not_reverse:
            # Multiple values - if includes '1' (Not Reverse), exclude reverse mortgages
            reverse_values = [r.strip() for r in not_reverse.split(',')]
            if '1' in reverse_values and '2' not in reverse_values:
                # Only "Not Reverse" selected
                reverse_filter = "AND h.reverse_mortgage != '1'"
            elif '2' in reverse_values and '1' not in reverse_values:
                # Only "Reverse Mortgage" selected
                reverse_filter = "AND h.reverse_mortgage = '1'"
            # If both selected, no filter (include all)
        else:
            # Single value
            if not_reverse == '1':
                reverse_filter = "AND h.reverse_mortgage != '1'"
            elif not_reverse == '2':
                reverse_filter = "AND h.reverse_mortgage = '1'"
    
    query = f"""
WITH cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        -- Treat NULL/empty cbsa_code as '99999' for rural areas
        COALESCE(NULLIF(CAST(cbsa_code AS STRING), ''), '99999') as cbsa_code,
        COALESCE(cbsa, 'Rural Area') as cbsa_name
    FROM `hdma1-242116.geo.cbsa_to_county`
),
-- Filter HMDA data to user-selected assessment area counties
filtered_hmda AS (
    SELECT
        CAST(h.activity_year AS STRING) as activity_year,
        -- Use COALESCE to treat NULL cbsa_code as '99999' for rural areas
        COALESCE(c.cbsa_code, '99999') as cbsa_code,
        h.loan_amount,
        CASE 
            WHEN h.tract_to_msa_income_percentage IS NOT NULL
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80 
            THEN 1 ELSE 0 
        END as is_lmict,
        CASE 
            WHEN h.income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income > 0
              AND (CAST(h.income AS FLOAT64) * 1000.0) / 
                  CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
            THEN 1 ELSE 0 
        END as is_lmib,
        CASE 
            WHEN h.tract_minority_population_percent IS NOT NULL
                AND CAST(h.tract_minority_population_percent AS FLOAT64) > 50 
            THEN 1 ELSE 0 
        END as is_mmct,
        -- Race/Ethnicity classification using COALESCE methodology
        -- First check for Hispanic ethnicity (if ANY ethnicity field indicates Hispanic)
        CASE 
            WHEN h.applicant_ethnicity_1 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_5 IN ('1','11','12','13','14')
            THEN 1 ELSE 0 
        END as is_hispanic,
        -- For non-Hispanic applicants, use COALESCE to find first valid race code
        -- Valid race codes exclude '6' (Not Provided), '7' (Not Applicable), '8' (No co-applicant)
        CASE 
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
        END as is_black,
        CASE 
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
        END as is_asian,
        CASE 
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
        END as is_native_american,
        CASE 
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
        END as is_hopi
    FROM `hdma1-242116.hmda.hmda` h
    LEFT JOIN cbsa_crosswalk c
        ON LPAD(CAST(h.county_code AS STRING), 5, '0') = c.county_code
    WHERE CAST(h.activity_year AS STRING) IN ('{years_list}')
        {action_taken_filter}
        {occupancy_filter}
        {reverse_filter}
        {construction_filter}
        {units_filter}
        AND h.lei = '{subject_lei}'
        {loan_purpose_filter}
        -- Filter to user-selected assessment area counties (county_code in HMDA is the 5-digit GEOID)
        AND LPAD(CAST(h.county_code AS STRING), 5, '0') IN ('{geoid5_list}')
),
aggregated_metrics AS (
    SELECT 
        activity_year,
        cbsa_code,
        COUNT(*) as total_loans,
        SUM(loan_amount) as total_amount,
        COUNTIF(is_lmict = 1) as lmict_loans,
        SAFE_DIVIDE(COUNTIF(is_lmict = 1), COUNT(*)) * 100 as lmict_percentage,
        COUNTIF(is_lmib = 1) as lmib_loans,
        SAFE_DIVIDE(COUNTIF(is_lmib = 1), COUNT(*)) * 100 as lmib_percentage,
        SUM(CASE WHEN is_lmib = 1 THEN loan_amount END) as lmib_amount,
        COUNTIF(is_mmct = 1) as mmct_loans,
        SAFE_DIVIDE(COUNTIF(is_mmct = 1), COUNT(*)) * 100 as mmct_percentage,
        COUNTIF(is_hispanic = 1 OR is_black = 1 OR is_asian = 1 
                OR is_native_american = 1 OR is_hopi = 1) as minb_loans,
        SAFE_DIVIDE(COUNTIF(is_hispanic = 1 OR is_black = 1 OR is_asian = 1 
                           OR is_native_american = 1 OR is_hopi = 1), COUNT(*)) * 100 as minb_percentage,
        -- Individual race/ethnicity counts (using total loans as denominator)
        COUNTIF(is_asian = 1) as asian_loans,
        SAFE_DIVIDE(COUNTIF(is_asian = 1), COUNT(*)) * 100 as asian_percentage,
        COUNTIF(is_black = 1) as black_loans,
        SAFE_DIVIDE(COUNTIF(is_black = 1), COUNT(*)) * 100 as black_percentage,
        COUNTIF(is_native_american = 1) as native_american_loans,
        SAFE_DIVIDE(COUNTIF(is_native_american = 1), COUNT(*)) * 100 as native_american_percentage,
        COUNTIF(is_hopi = 1) as hopi_loans,
        SAFE_DIVIDE(COUNTIF(is_hopi = 1), COUNT(*)) * 100 as hopi_percentage,
        COUNTIF(is_hispanic = 1) as hispanic_loans,
        SAFE_DIVIDE(COUNTIF(is_hispanic = 1), COUNT(*)) * 100 as hispanic_percentage
    FROM filtered_hmda
    GROUP BY activity_year, cbsa_code
)
SELECT * FROM aggregated_metrics
ORDER BY activity_year, cbsa_code
"""
    return query


def build_hmda_peer_query(
    subject_lei: str,
    assessment_area_geoids: list,
    years: list,
    loan_purpose: str = None,
    action_taken: str = '1',
    occupancy_type: str = '1',
    total_units: str = '1-4',
    construction_method: str = '1',
    not_reverse: str = '1'
) -> str:
    """
    Build peer HMDA query.
    NOTE: Qualified counties are determined SOLELY by subject lender's applications.
    Peers have no role in determining which CBSAs/counties are included.
    """
    """
    Build HMDA query for peer banks (50%-200% volume rule).
    
    Args:
        subject_lei: Subject bank's LEI (string)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings)
        years: List of years as strings
        loan_purpose: Optional loan purpose filter
    
    Returns:
        SQL query string
    """
    if not assessment_area_geoids:
        return f"""
SELECT 
    CAST(NULL AS STRING) as activity_year,
    CAST(NULL AS STRING) as cbsa_code,
    CAST(NULL AS INT64) as total_loans,
    CAST(NULL AS FLOAT64) as total_amount,
    CAST(NULL AS INT64) as lmict_loans,
    CAST(NULL AS FLOAT64) as lmict_percentage,
    CAST(NULL AS INT64) as lmib_loans,
    CAST(NULL AS FLOAT64) as lmib_percentage,
    CAST(NULL AS FLOAT64) as lmib_amount,
    CAST(NULL AS INT64) as mmct_loans,
    CAST(NULL AS FLOAT64) as mmct_percentage,
    CAST(NULL AS INT64) as minb_loans,
    CAST(NULL AS FLOAT64) as minb_percentage
WHERE FALSE
"""
    
    geoid5_list = "', '".join([str(g).zfill(5) for g in assessment_area_geoids])
    years_list = "', '".join([str(y) for y in years])
    
    # Build filter conditions dynamically (same as subject query)
    loan_purpose_filter = ""
    if loan_purpose:
        if ',' in loan_purpose:
            purposes = [p.strip() for p in loan_purpose.split(',')]
            purpose_list = "', '".join(purposes)
            loan_purpose_filter = f"AND h.loan_purpose IN ('{purpose_list}')"
        else:
            loan_purpose_filter = f"AND h.loan_purpose = '{loan_purpose.strip()}'"
    
    # Build action_taken filter
    action_taken_filter = ""
    if action_taken:
        if ',' in action_taken:
            actions = [a.strip() for a in action_taken.split(',')]
            action_list = "', '".join(actions)
            action_taken_filter = f"AND h.action_taken IN ('{action_list}')"
        else:
            action_taken_filter = f"AND h.action_taken = '{action_taken.strip()}'"
    
    # Build occupancy_type filter
    occupancy_filter = ""
    if occupancy_type:
        if ',' in occupancy_type:
            # Multiple occupancy types
            occupancies = [o.strip() for o in occupancy_type.split(',')]
            occupancy_list = "', '".join(occupancies)
            occupancy_filter = f"AND h.occupancy_type IN ('{occupancy_list}')"
        else:
            # Single occupancy type
            occupancy_filter = f"AND h.occupancy_type = '{occupancy_type.strip()}'"
    
    # Build total_units filter
    units_filter = ""
    if total_units:
        if ',' in total_units:
            # Multiple unit types
            units = [u.strip() for u in total_units.split(',')]
            units_list = "', '".join(units)
            units_filter = f"AND h.total_units IN ('{units_list}')"
        else:
            # Single unit type
            units_filter = f"AND h.total_units = '{total_units.strip()}'"
    
    # Build construction_method filter
    construction_filter = ""
    if construction_method:
        if ',' in construction_method:
            # Multiple construction methods
            constructions = [c.strip() for c in construction_method.split(',')]
            construction_list = "', '".join(constructions)
            construction_filter = f"AND h.construction_method IN ('{construction_list}')"
        else:
            # Single construction method
            construction_filter = f"AND h.construction_method = '{construction_method.strip()}'"
    
    # Build reverse_mortgage filter
    reverse_filter = ""
    if not_reverse:
        if ',' in not_reverse:
            # Multiple values - if includes '1' (Not Reverse), exclude reverse mortgages
            reverse_values = [r.strip() for r in not_reverse.split(',')]
            if '1' in reverse_values and '2' not in reverse_values:
                # Only "Not Reverse" selected
                reverse_filter = "AND h.reverse_mortgage != '1'"
            elif '2' in reverse_values and '1' not in reverse_values:
                # Only "Reverse Mortgage" selected
                reverse_filter = "AND h.reverse_mortgage = '1'"
            # If both selected, no filter (include all)
        else:
            # Single value
            if not_reverse == '1':
                reverse_filter = "AND h.reverse_mortgage != '1'"
            elif not_reverse == '2':
                reverse_filter = "AND h.reverse_mortgage = '1'"
    
    query = f"""
WITH cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        -- Treat NULL/empty cbsa_code as '99999' for rural areas
        COALESCE(NULLIF(CAST(cbsa_code AS STRING), ''), '99999') as cbsa_code,
        COALESCE(cbsa, 'Rural Area') as cbsa_name
    FROM `hdma1-242116.geo.cbsa_to_county`
),
-- Filter HMDA data to user-selected assessment area counties (includes all lenders for peer comparison)
filtered_hmda AS (
    SELECT
        CAST(h.activity_year AS STRING) as activity_year,
        -- Use COALESCE to treat NULL cbsa_code as '99999' for rural areas
        COALESCE(c.cbsa_code, '99999') as cbsa_code,
        h.lei,
        h.loan_amount,
        CASE 
            WHEN h.tract_to_msa_income_percentage IS NOT NULL
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80 
            THEN 1 ELSE 0 
        END as is_lmict,
        CASE 
            WHEN h.income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income IS NOT NULL
              AND h.ffiec_msa_md_median_family_income > 0
              AND (CAST(h.income AS FLOAT64) * 1000.0) / 
                  CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
            THEN 1 ELSE 0 
        END as is_lmib,
        CASE 
            WHEN h.tract_minority_population_percent IS NOT NULL
                AND CAST(h.tract_minority_population_percent AS FLOAT64) > 50 
            THEN 1 ELSE 0 
        END as is_mmct,
        -- Race/Ethnicity classification using COALESCE methodology
        -- First check for Hispanic ethnicity (if ANY ethnicity field indicates Hispanic)
        CASE 
            WHEN h.applicant_ethnicity_1 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
                OR h.applicant_ethnicity_5 IN ('1','11','12','13','14')
            THEN 1 ELSE 0 
        END as is_hispanic,
        -- For non-Hispanic applicants, use COALESCE to find first valid race code
        -- Valid race codes exclude '6' (Not Provided), '7' (Not Applicable), '8' (No co-applicant)
        CASE 
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
        END as is_black,
        CASE 
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
        END as is_asian,
        CASE 
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
        END as is_native_american,
        CASE 
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
        END as is_hopi
    FROM `hdma1-242116.hmda.hmda` h
    LEFT JOIN cbsa_crosswalk c
        ON LPAD(CAST(h.county_code AS STRING), 5, '0') = c.county_code
    WHERE CAST(h.activity_year AS STRING) IN ('{years_list}')
        {action_taken_filter}
        {occupancy_filter}
        {reverse_filter}
        {construction_filter}
        {units_filter}
        {loan_purpose_filter}
        -- Filter to user-selected assessment area counties (county_code in HMDA is the 5-digit GEOID)
        AND LPAD(CAST(h.county_code AS STRING), 5, '0') IN ('{geoid5_list}')
),
subject_volume AS (
    SELECT 
        activity_year,
        cbsa_code,
        COUNT(*) as subject_vol
    FROM filtered_hmda
    WHERE lei = '{subject_lei}'
    GROUP BY activity_year, cbsa_code
),
all_lenders_volume AS (
    SELECT 
        activity_year,
        cbsa_code,
        lei,
        COUNT(*) as lender_vol
    FROM filtered_hmda
    GROUP BY activity_year, cbsa_code, lei
),
peers AS (
    SELECT DISTINCT
        al.activity_year,
        al.cbsa_code,
        al.lei
    FROM all_lenders_volume al
    INNER JOIN subject_volume sv
        ON al.activity_year = sv.activity_year
        AND al.cbsa_code = sv.cbsa_code
    WHERE al.lei != '{subject_lei}'
      AND al.lender_vol >= sv.subject_vol * 0.5
      AND al.lender_vol <= sv.subject_vol * 2.0
),
peer_hmda AS (
    SELECT f.*
    FROM filtered_hmda f
    INNER JOIN peers p
        ON f.activity_year = p.activity_year
        AND f.cbsa_code = p.cbsa_code
        AND f.lei = p.lei
),
aggregated_peer_metrics AS (
    SELECT 
        activity_year,
        cbsa_code,
        COUNT(*) as total_loans,
        SUM(loan_amount) as total_amount,
        COUNTIF(is_lmict = 1) as lmict_loans,
        SAFE_DIVIDE(COUNTIF(is_lmict = 1), COUNT(*)) * 100 as lmict_percentage,
        COUNTIF(is_lmib = 1) as lmib_loans,
        SAFE_DIVIDE(COUNTIF(is_lmib = 1), COUNT(*)) * 100 as lmib_percentage,
        SUM(CASE WHEN is_lmib = 1 THEN loan_amount END) as lmib_amount,
        COUNTIF(is_mmct = 1) as mmct_loans,
        SAFE_DIVIDE(COUNTIF(is_mmct = 1), COUNT(*)) * 100 as mmct_percentage,
        COUNTIF(is_hispanic = 1 OR is_black = 1 OR is_asian = 1 
                OR is_native_american = 1 OR is_hopi = 1) as minb_loans,
        SAFE_DIVIDE(COUNTIF(is_hispanic = 1 OR is_black = 1 OR is_asian = 1 
                           OR is_native_american = 1 OR is_hopi = 1), COUNT(*)) * 100 as minb_percentage,
        -- Individual race/ethnicity counts (using total loans as denominator)
        COUNTIF(is_asian = 1) as asian_loans,
        SAFE_DIVIDE(COUNTIF(is_asian = 1), COUNT(*)) * 100 as asian_percentage,
        COUNTIF(is_black = 1) as black_loans,
        SAFE_DIVIDE(COUNTIF(is_black = 1), COUNT(*)) * 100 as black_percentage,
        COUNTIF(is_native_american = 1) as native_american_loans,
        SAFE_DIVIDE(COUNTIF(is_native_american = 1), COUNT(*)) * 100 as native_american_percentage,
        COUNTIF(is_hopi = 1) as hopi_loans,
        SAFE_DIVIDE(COUNTIF(is_hopi = 1), COUNT(*)) * 100 as hopi_percentage,
        COUNTIF(is_hispanic = 1) as hispanic_loans,
        SAFE_DIVIDE(COUNTIF(is_hispanic = 1), COUNT(*)) * 100 as hispanic_percentage
    FROM peer_hmda
    GROUP BY activity_year, cbsa_code
)
SELECT * FROM aggregated_peer_metrics
ORDER BY activity_year, cbsa_code
"""
    return query


def build_sb_subject_query(
    sb_respondent_id: str,
    assessment_area_geoids: list,
    years: list
) -> str:
    """
    Build Small Business query for subject bank.
    
    Args:
        sb_respondent_id: Bank's SB Respondent ID (string, may have prefix)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings)
        years: List of years as strings
    
    Returns:
        SQL query string
    """
    if not assessment_area_geoids:
        return f"""
SELECT 
    CAST(NULL AS STRING) as year,
    CAST(NULL AS STRING) as cbsa_code,
    CAST(NULL AS STRING) as cbsa_name,
    CAST(NULL AS INT64) as sb_loans_count,
    CAST(NULL AS FLOAT64) as sb_loans_amount,
    CAST(NULL AS INT64) as lmict_loans_count,
    CAST(NULL AS FLOAT64) as lmict_loans_amount,
    CAST(NULL AS INT64) as loans_rev_under_1m,
    CAST(NULL AS FLOAT64) as amount_rev_under_1m
WHERE FALSE
"""
    
    geoid5_list = "', '".join([str(g).zfill(5) for g in assessment_area_geoids])
    years_list = "', '".join([str(y) for y in years])
    
    # Extract respondent ID without prefix
    if '-' in sb_respondent_id:
        respondent_id_no_prefix = sb_respondent_id.split('-', 1)[-1]
    else:
        respondent_id_no_prefix = sb_respondent_id
    
    query = f"""
-- CBSA crosswalk to get CBSA codes and names from GEOID5 (counties in assessment areas)
WITH cbsa_crosswalk AS (
    SELECT DISTINCT
        CAST(geoid5 AS STRING) as geoid5,
        CAST(cbsa_code AS STRING) as cbsa_code,
        CBSA as cbsa_name,
        State as state_name
    FROM `hdma1-242116.geo.cbsa_to_county`
    WHERE CAST(geoid5 AS STRING) IN ('{geoid5_list}')
),
filtered_sb_data AS (
    SELECT 
        CAST(d.year AS STRING) as year,
        COALESCE(c.cbsa_code, 'N/A') as cbsa_code,
        COALESCE(c.cbsa_name, 
            CASE 
                WHEN c.state_name IS NOT NULL THEN CONCAT(c.state_name, ' Non-MSA')
                ELSE 'Non-MSA'
            END
        ) as cbsa_name,
        (d.num_under_100k + d.num_100k_250k + d.num_250k_1m) as sb_loans_count,
        (d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m) as sb_loans_amount,
        CASE 
            WHEN d.income_group_total IN ('101', '102', '1', '2', '3', '4', '5', '6', '7', '8')
            THEN (d.num_under_100k + d.num_100k_250k + d.num_250k_1m)
            ELSE 0
        END as lmict_loans_count,
        CASE 
            WHEN d.income_group_total IN ('101', '102', '1', '2', '3', '4', '5', '6', '7', '8')
            THEN (d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m)
            ELSE 0
        END as lmict_loans_amount,
        d.numsbrev_under_1m as loans_rev_under_1m,
        d.amtsbrev_under_1m as amount_rev_under_1m
    FROM `hdma1-242116.sb.disclosure` d
    INNER JOIN `hdma1-242116.sb.lenders` l
        ON d.respondent_id = l.sb_resid
    LEFT JOIN cbsa_crosswalk c
        ON CAST(d.geoid5 AS STRING) = c.geoid5
    WHERE CAST(d.year AS STRING) IN ('{years_list}')
        AND CAST(d.geoid5 AS STRING) IN ('{geoid5_list}')
        AND (l.sb_resid = '{respondent_id_no_prefix}' OR l.sb_resid = '{sb_respondent_id}')
        AND c.cbsa_code IS NOT NULL  -- Only include counties that have a CBSA mapping (in assessment areas)
),
aggregated_sb_metrics AS (
    SELECT 
        year,
        cbsa_code,
        MAX(cbsa_name) as cbsa_name,  -- Get CBSA name (should be same for all rows with same cbsa_code)
        SUM(sb_loans_count) as sb_loans_count,
        SUM(sb_loans_amount) as sb_loans_amount,
        SUM(lmict_loans_count) as lmict_loans_count,
        SUM(lmict_loans_amount) as lmict_loans_amount,
        SUM(loans_rev_under_1m) as loans_rev_under_1m,
        SUM(amount_rev_under_1m) as amount_rev_under_1m
    FROM filtered_sb_data
    GROUP BY year, cbsa_code
)
SELECT * FROM aggregated_sb_metrics
ORDER BY year, cbsa_code
"""
    return query


def build_branch_query(
    subject_rssd: str,
    assessment_area_geoids: list,
    year: int = 2025
) -> str:
    """
    Build branch query for a subject bank by assessment area.
    
    Args:
        subject_rssd: Bank's RSSD ID (string)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings) for assessment area counties
        year: Year for branch data (default: 2025)
    
    Returns:
        SQL query string ready for BigQuery
    
    Note:
        - Queries branches in assessment area counties
        - Calculates total branches, LMICT branches, and MMCT branches
        - Aggregates by assessment area (all counties combined)
    """
    
    # Format GEOID5 list - convert to strings with proper padding
    geoid5_list = [str(g).zfill(5) for g in assessment_area_geoids]
    geoid5_str = ', '.join([f"'{g}'" for g in geoid5_list])
    
    query = f"""
WITH assessment_area_counties AS (
    SELECT DISTINCT geoid5
    FROM UNNEST([{geoid5_str}]) as geoid5
),

-- CBSA crosswalk to get CBSA codes from GEOID5
cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        CAST(cbsa_code AS STRING) as cbsa_code,
        cbsa as cbsa_name,
        County as county_name,
        State as state_name,
        CONCAT(County, ', ', State) as county_state
    FROM `hdma1-242116.geo.cbsa_to_county`
),

-- Filter branches to assessment area counties and year
filtered_branches AS (
    SELECT 
        CAST(b.rssd AS STRING) as rssd,
        b.bank_name as institution_name,
        COALESCE(c.cbsa_code, 'N/A') as cbsa_code,
        COALESCE(c.cbsa_name, CONCAT(c.state_name, ' Non-MSA')) as cbsa_name,
        CAST(b.geoid5 AS STRING) as county_code,
        c.county_state,
        c.county_name,
        c.state_name,
        b.geoid,
        b.br_lmi,
        b.br_minority as cr_minority,
        b.uninumbr
    FROM `hdma1-242116.branches.sod25` b
    LEFT JOIN cbsa_crosswalk c
        ON CAST(b.geoid5 AS STRING) = c.county_code
    WHERE CAST(b.year AS STRING) = '{year}'
        AND CAST(b.geoid5 AS STRING) IN ({geoid5_str})
        AND CAST(b.rssd AS STRING) = '{subject_rssd}'
),

-- Deduplicate branches (use uninumbr as unique identifier)
deduplicated_branches AS (
    SELECT 
        rssd,
        institution_name,
        cbsa_code,
        cbsa_name,
        county_code,
        county_state,
        county_name,
        state_name,
        geoid,
        br_lmi,
        cr_minority
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY uninumbr ORDER BY rssd) as rn
        FROM filtered_branches
    )
    WHERE rn = 1
),

-- Prepare grouping key for Non-MSA areas
grouped_branches AS (
    SELECT 
        *,
        CASE 
            WHEN cbsa_code = 'N/A' OR cbsa_code IS NULL THEN CONCAT(state_name, ' Non-MSA')
            ELSE cbsa_code
        END as group_key,
        CASE 
            WHEN cbsa_code = 'N/A' OR cbsa_code IS NULL THEN CONCAT(state_name, ' Non-MSA')
            ELSE COALESCE(cbsa_name, cbsa_code)
        END as group_name
    FROM deduplicated_branches
)

-- Aggregate by CBSA for subject bank
-- For Non-MSA areas (cbsa_code = 'N/A'), group by state name
SELECT 
    group_key as cbsa_code,
    group_name as cbsa_name,
    COUNT(*) as total_branches,
    COUNTIF(br_lmi = 1) as branches_in_lmict,
    SAFE_DIVIDE(COUNTIF(br_lmi = 1), COUNT(*)) * 100 as pct_lmict,
    COUNTIF(cr_minority = 1) as branches_in_mmct,
    SAFE_DIVIDE(COUNTIF(cr_minority = 1), COUNT(*)) * 100 as pct_mmct,
    -- Count branches that are both LMICT and MMCT
    COUNTIF(br_lmi = 1 AND cr_minority = 1) as branches_lmict_mmct,
    -- Count branches that are LMI only (not MMCT)
    COUNTIF(br_lmi = 1 AND cr_minority = 0) as branches_lmi_only,
    -- Count branches that are MMCT only (not LMI)
    COUNTIF(br_lmi = 0 AND cr_minority = 1) as branches_mmct_only
FROM grouped_branches
GROUP BY group_key, group_name
ORDER BY group_key
"""
    
    return query


def build_branch_market_query(
    subject_rssd: str,
    assessment_area_geoids: list,
    year: int = 2025
) -> str:
    """
    Build branch query for all OTHER banks (market) in the same CBSAs as the subject bank.
    
    Args:
        subject_rssd: Subject bank's RSSD ID (string) - will be excluded
        assessment_area_geoids: List of GEOID5 codes (5-digit strings) for assessment area counties
        year: Year for branch data (default: 2025)
    
    Returns:
        SQL query string ready for BigQuery that returns aggregated branch data for all other banks
    """
    
    # Format GEOID5 list - convert to strings with proper padding
    geoid5_list = [str(g).zfill(5) for g in assessment_area_geoids]
    geoid5_str = ', '.join([f"'{g}'" for g in geoid5_list])
    
    query = f"""
WITH assessment_area_counties AS (
    SELECT DISTINCT geoid5
    FROM UNNEST([{geoid5_str}]) as geoid5
),

-- CBSA crosswalk to get CBSA codes from GEOID5
cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        CAST(cbsa_code AS STRING) as cbsa_code,
        cbsa as cbsa_name,
        County as county_name,
        State as state_name,
        CONCAT(County, ', ', State) as county_state
    FROM `hdma1-242116.geo.cbsa_to_county`
),

-- Filter branches to assessment area counties and year, EXCLUDING subject bank
filtered_branches AS (
    SELECT 
        CAST(b.rssd AS STRING) as rssd,
        b.bank_name as institution_name,
        COALESCE(c.cbsa_code, 'N/A') as cbsa_code,
        COALESCE(c.cbsa_name, CONCAT(c.state_name, ' Non-MSA')) as cbsa_name,
        CAST(b.geoid5 AS STRING) as county_code,
        c.county_state,
        c.county_name,
        c.state_name,
        b.geoid,
        b.br_lmi,
        b.br_minority as cr_minority,
        b.uninumbr
    FROM `hdma1-242116.branches.sod25` b
    LEFT JOIN cbsa_crosswalk c
        ON CAST(b.geoid5 AS STRING) = c.county_code
    WHERE CAST(b.year AS STRING) = '{year}'
        AND CAST(b.geoid5 AS STRING) IN ({geoid5_str})
        AND CAST(b.rssd AS STRING) != '{subject_rssd}'  -- Exclude subject bank
),

-- Deduplicate branches (use uninumbr as unique identifier)
deduplicated_branches AS (
    SELECT 
        rssd,
        institution_name,
        cbsa_code,
        cbsa_name,
        county_code,
        county_state,
        county_name,
        state_name,
        geoid,
        br_lmi,
        cr_minority
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY uninumbr ORDER BY rssd) as rn
        FROM filtered_branches
    )
    WHERE rn = 1
),

-- Prepare grouping key for Non-MSA areas
grouped_branches AS (
    SELECT 
        *,
        CASE 
            WHEN cbsa_code = 'N/A' OR cbsa_code IS NULL THEN CONCAT(state_name, ' Non-MSA')
            ELSE cbsa_code
        END as group_key,
        CASE 
            WHEN cbsa_code = 'N/A' OR cbsa_code IS NULL THEN CONCAT(state_name, ' Non-MSA')
            ELSE COALESCE(cbsa_name, cbsa_code)
        END as group_name
    FROM deduplicated_branches
)

-- Aggregate by CBSA for market (all other banks)
SELECT 
    group_key as cbsa_code,
    group_name as cbsa_name,
    COUNT(*) as total_branches,
    COUNTIF(br_lmi = 1) as branches_in_lmict,
    SAFE_DIVIDE(COUNTIF(br_lmi = 1), COUNT(*)) * 100 as pct_lmict,
    COUNTIF(cr_minority = 1) as branches_in_mmct,
    SAFE_DIVIDE(COUNTIF(cr_minority = 1), COUNT(*)) * 100 as pct_mmct,
    -- Count branches that are both LMICT and MMCT
    COUNTIF(br_lmi = 1 AND cr_minority = 1) as branches_lmict_mmct,
    -- Count branches that are LMI only (not MMCT)
    COUNTIF(br_lmi = 1 AND cr_minority = 0) as branches_lmi_only,
    -- Count branches that are MMCT only (not LMI)
    COUNTIF(br_lmi = 0 AND cr_minority = 1) as branches_mmct_only
FROM grouped_branches
GROUP BY group_key, group_name
ORDER BY group_key
"""
    
    return query


def build_branch_details_query(
    subject_rssd: str,
    assessment_area_geoids: list,
    year: int = 2025
) -> str:
    """
    Build query for individual branch details (address, city, state, zip, etc.).
    
    Args:
        subject_rssd: Bank's RSSD ID (string)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings) for assessment area counties
        year: Year for branch data (default: 2025)
    
    Returns:
        SQL query string ready for BigQuery that returns individual branch records
    """
    
    # Format GEOID5 list - convert to strings with proper padding
    geoid5_list = [str(g).zfill(5) for g in assessment_area_geoids]
    geoid5_str = ', '.join([f"'{g}'" for g in geoid5_list])
    
    query = f"""
WITH assessment_area_counties AS (
    SELECT DISTINCT geoid5
    FROM UNNEST([{geoid5_str}]) as geoid5
),

-- CBSA crosswalk to get CBSA codes and county info from GEOID5
cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        CAST(cbsa_code AS STRING) as cbsa_code,
        cbsa as cbsa_name,
        County as county_name,
        State as state_name,
        CONCAT(County, ', ', State) as county_state
    FROM `hdma1-242116.geo.cbsa_to_county`
),

-- Get individual branch details
filtered_branches AS (
    SELECT 
        CAST(b.rssd AS STRING) as rssd,
        b.bank_name,
        b.branch_name,
        b.address,
        b.city,
        COALESCE(c.state_name, b.state) as state,
        COALESCE(c.county_name, b.county) as county,
        b.zip,
        CAST(b.geoid AS STRING) as census_tract,
        CAST(b.latitude AS FLOAT64) as latitude,
        CAST(b.longitude AS FLOAT64) as longitude,
        CAST(b.geoid5 AS STRING) as geoid5,
        c.county_state,
        b.uninumbr
    FROM `hdma1-242116.branches.sod25` b
    LEFT JOIN cbsa_crosswalk c
        ON CAST(b.geoid5 AS STRING) = c.county_code
    WHERE CAST(b.year AS STRING) = '{year}'
        AND CAST(b.geoid5 AS STRING) IN ({geoid5_str})
        AND CAST(b.rssd AS STRING) = '{subject_rssd}'
)

-- Deduplicate branches (use uninumbr as unique identifier) and return individual records
SELECT 
    bank_name,
    branch_name,
    address,
    city,
    state,
    zip,
    county,
    census_tract,
    latitude,
    longitude
FROM (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY uninumbr ORDER BY rssd) as rn
    FROM filtered_branches
)
WHERE rn = 1
ORDER BY state, county, city, branch_name
"""
    
    return query


def build_sb_peer_query(
    sb_respondent_id: str,
    assessment_area_geoids: list,
    years: list
) -> str:
    """
    Build Small Business query for peer banks (50%-200% volume rule).
    
    Args:
        sb_respondent_id: Subject bank's SB Respondent ID (string)
        assessment_area_geoids: List of GEOID5 codes (5-digit strings)
        years: List of years as strings
    
    Returns:
        SQL query string
    """
    if not assessment_area_geoids:
        return f"""
SELECT 
    CAST(NULL AS STRING) as year,
    CAST(NULL AS STRING) as cbsa_code,
    CAST(NULL AS STRING) as cbsa_name,
    CAST(NULL AS INT64) as sb_loans_count,
    CAST(NULL AS FLOAT64) as sb_loans_amount,
    CAST(NULL AS INT64) as lmict_loans_count,
    CAST(NULL AS FLOAT64) as lmict_loans_amount,
    CAST(NULL AS INT64) as loans_rev_under_1m,
    CAST(NULL AS FLOAT64) as amount_rev_under_1m
WHERE FALSE
"""
    
    geoid5_list = "', '".join([str(g).zfill(5) for g in assessment_area_geoids])
    years_list = "', '".join([str(y) for y in years])
    
    # Extract respondent ID without prefix
    if '-' in sb_respondent_id:
        respondent_id_no_prefix = sb_respondent_id.split('-', 1)[-1]
    else:
        respondent_id_no_prefix = sb_respondent_id
    
    query = f"""
-- CBSA crosswalk to get CBSA codes and names from GEOID5 (counties in assessment areas)
WITH cbsa_crosswalk AS (
    SELECT DISTINCT
        CAST(geoid5 AS STRING) as geoid5,
        CAST(cbsa_code AS STRING) as cbsa_code,
        CBSA as cbsa_name,
        State as state_name
    FROM `hdma1-242116.geo.cbsa_to_county`
    WHERE CAST(geoid5 AS STRING) IN ('{geoid5_list}')
),
filtered_sb_data AS (
    SELECT 
        CAST(d.year AS STRING) as year,
        COALESCE(c.cbsa_code, 'N/A') as cbsa_code,
        COALESCE(c.cbsa_name, 
            CASE 
                WHEN c.state_name IS NOT NULL THEN CONCAT(c.state_name, ' Non-MSA')
                ELSE 'Non-MSA'
            END
        ) as cbsa_name,
        l.sb_resid,
        (d.num_under_100k + d.num_100k_250k + d.num_250k_1m) as sb_loans_count,
        (d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m) as sb_loans_amount,
        CASE 
            WHEN d.income_group_total IN ('101', '102', '1', '2', '3', '4', '5', '6', '7', '8')
            THEN (d.num_under_100k + d.num_100k_250k + d.num_250k_1m)
            ELSE 0
        END as lmict_loans_count,
        CASE 
            WHEN d.income_group_total IN ('101', '102', '1', '2', '3', '4', '5', '6', '7', '8')
            THEN (d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m)
            ELSE 0
        END as lmict_loans_amount,
        d.numsbrev_under_1m as loans_rev_under_1m,
        d.amtsbrev_under_1m as amount_rev_under_1m
    FROM `hdma1-242116.sb.disclosure` d
    INNER JOIN `hdma1-242116.sb.lenders` l
        ON d.respondent_id = l.sb_resid
    LEFT JOIN cbsa_crosswalk c
        ON CAST(d.geoid5 AS STRING) = c.geoid5
    WHERE CAST(d.year AS STRING) IN ('{years_list}')
        AND CAST(d.geoid5 AS STRING) IN ('{geoid5_list}')
        AND c.cbsa_code IS NOT NULL  -- Only include counties that have a CBSA mapping (in assessment areas)
),
subject_sb_volume AS (
    SELECT 
        year,
        cbsa_code,
        SUM(sb_loans_count) as subject_sb_vol
    FROM filtered_sb_data
    WHERE sb_resid = '{respondent_id_no_prefix}' OR sb_resid = '{sb_respondent_id}'
    GROUP BY year, cbsa_code
),
all_lenders_sb_volume AS (
    SELECT 
        year,
        cbsa_code,
        sb_resid,
        SUM(sb_loans_count) as lender_sb_vol
    FROM filtered_sb_data
    GROUP BY year, cbsa_code, sb_resid
),
peers AS (
    SELECT DISTINCT
        al.year,
        al.cbsa_code,
        al.sb_resid
    FROM all_lenders_sb_volume al
    INNER JOIN subject_sb_volume sv
        ON al.year = sv.year
        AND al.cbsa_code = sv.cbsa_code
    WHERE (al.sb_resid != '{respondent_id_no_prefix}' AND al.sb_resid != '{sb_respondent_id}')
      AND al.lender_sb_vol >= sv.subject_sb_vol * 0.5
      AND al.lender_sb_vol <= sv.subject_sb_vol * 2.0
),
peer_sb AS (
    SELECT f.*
    FROM filtered_sb_data f
    INNER JOIN peers p
        ON f.year = p.year
        AND f.cbsa_code = p.cbsa_code
        AND f.sb_resid = p.sb_resid
),
aggregated_peer_sb_metrics AS (
    SELECT 
        year,
        cbsa_code,
        MAX(cbsa_name) as cbsa_name,  -- Get CBSA name (should be same for all rows with same cbsa_code)
        SUM(sb_loans_count) as sb_loans_count,
        SUM(sb_loans_amount) as sb_loans_amount,
        SUM(lmict_loans_count) as lmict_loans_count,
        SUM(lmict_loans_amount) as lmict_loans_amount,
        SUM(loans_rev_under_1m) as loans_rev_under_1m,
        SUM(amount_rev_under_1m) as amount_rev_under_1m
    FROM peer_sb
    GROUP BY year, cbsa_code
)
SELECT * FROM aggregated_peer_sb_metrics
ORDER BY year, cbsa_code
"""
    return query

