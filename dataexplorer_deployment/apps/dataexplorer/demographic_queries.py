#!/usr/bin/env python3
"""
Query builders for demographic analysis in DataExplorer.
Builds queries for HMDA and Small Business data broken down by demographics,
income, and neighborhood characteristics, showing all lenders in an area.
"""

from typing import List, Optional
from .config import DataExplorerConfig


def build_hmda_demographic_query(
    geoids: List[str],
    years: List[int],
    loan_purpose: Optional[List[str]] = None,
    action_taken: Optional[List[str]] = None,
    occupancy_type: Optional[List[str]] = None,
    total_units: Optional[List[str]] = None,
    construction_method: Optional[List[str]] = None,
    exclude_reverse_mortgages: bool = True,
    metric_type: str = 'count'  # 'count' or 'amount'
) -> str:
    """
    Build HMDA query broken down by demographics, income, and neighborhood for all lenders.
    
    Args:
        geoids: List of GEOID5 codes
        years: List of years
        loan_purpose: Optional loan purpose filter
        action_taken: Optional action taken filter
        occupancy_type: Optional occupancy type filter
        total_units: Optional total units filter
        construction_method: Optional construction method filter
        exclude_reverse_mortgages: Exclude reverse mortgages
        metric_type: 'count' for number of loans, 'amount' for dollar amounts
    
    Returns:
        SQL query string
    """
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
    years_list = "', '".join([str(y) for y in years])
    
    # Build WHERE conditions
    # Note: county_code in HMDA table is already the full 5-digit GEOID5
    where_conditions = [
        f"CAST(h.activity_year AS STRING) IN ('{years_list}')",
        f"h.state_code IS NOT NULL",
        f"h.county_code IS NOT NULL",
        f"LPAD(CAST(h.county_code AS STRING), 5, '0') IN ('{geoid5_list}')"
    ]
    
    if loan_purpose:
        purpose_list = "', '".join(loan_purpose)
        where_conditions.append(f"h.loan_purpose IN ('{purpose_list}')")
    
    if action_taken:
        action_list = "', '".join(action_taken)
        where_conditions.append(f"h.action_taken IN ('{action_list}')")
    
    if occupancy_type:
        occupancy_list = "', '".join(occupancy_type)
        where_conditions.append(f"h.occupancy_type IN ('{occupancy_list}')")
    
    if total_units:
        units_list = "', '".join(total_units)
        where_conditions.append(f"h.total_units IN ('{units_list}')")
    
    if construction_method:
        construction_list = "', '".join(construction_method)
        where_conditions.append(f"h.construction_method IN ('{construction_list}')")
    
    if exclude_reverse_mortgages:
        # Exclude reverse mortgages: only exclude '1' (includes NULLs and other values)
        where_conditions.append("(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')")
    
    where_clause = " AND ".join(where_conditions)
    
    # Build metric expressions based on metric_type
    if metric_type == 'count':
        # Count loans - since deduplicated_hmda already has one row per unique loan_key,
        # we can just use COUNT(*) to count the rows in each group
        # COUNT(*) counts the number of rows (loans) in each group after deduplication
        total_metric_expr = "COUNT(*)"
        hispanic_metric_expr = "COUNTIF(is_hispanic = 1)"
        black_metric_expr = "COUNTIF(is_black = 1)"
        asian_metric_expr = "COUNTIF(is_asian = 1)"
        native_american_metric_expr = "COUNTIF(is_native_american = 1)"
        hawaiian_pacific_islander_metric_expr = "COUNTIF(is_hawaiian_pacific_islander = 1)"
        white_metric_expr = "COUNTIF(is_white = 1)"
        lmib_metric_expr = "COUNTIF(is_lmib = 1)"
        low_income_metric_expr = "COUNTIF(is_low_income = 1)"
        moderate_income_metric_expr = "COUNTIF(is_moderate_income = 1)"
        middle_income_metric_expr = "COUNTIF(is_middle_income = 1)"
        upper_income_metric_expr = "COUNTIF(is_upper_income = 1)"
        lmict_metric_expr = "COUNTIF(is_lmict = 1)"
        low_income_tract_metric_expr = "COUNTIF(is_low_income_tract = 1)"
        moderate_income_tract_metric_expr = "COUNTIF(is_moderate_income_tract = 1)"
        middle_income_tract_metric_expr = "COUNTIF(is_middle_income_tract = 1)"
        upper_income_tract_metric_expr = "COUNTIF(is_upper_income_tract = 1)"
        mmct_metric_expr = "COUNTIF(is_mmct = 1)"
    else:
        total_metric_expr = "SUM(COALESCE(loan_amount, 0))"
        hispanic_metric_expr = "SUM(CASE WHEN is_hispanic = 1 THEN loan_amount ELSE 0 END)"
        black_metric_expr = "SUM(CASE WHEN is_black = 1 THEN loan_amount ELSE 0 END)"
        asian_metric_expr = "SUM(CASE WHEN is_asian = 1 THEN loan_amount ELSE 0 END)"
        native_american_metric_expr = "SUM(CASE WHEN is_native_american = 1 THEN loan_amount ELSE 0 END)"
        hawaiian_pacific_islander_metric_expr = "SUM(CASE WHEN is_hawaiian_pacific_islander = 1 THEN loan_amount ELSE 0 END)"
        white_metric_expr = "SUM(CASE WHEN is_white = 1 THEN loan_amount ELSE 0 END)"
        lmib_metric_expr = "SUM(CASE WHEN is_lmib = 1 THEN loan_amount ELSE 0 END)"
        low_income_metric_expr = "SUM(CASE WHEN is_low_income = 1 THEN loan_amount ELSE 0 END)"
        moderate_income_metric_expr = "SUM(CASE WHEN is_moderate_income = 1 THEN loan_amount ELSE 0 END)"
        middle_income_metric_expr = "SUM(CASE WHEN is_middle_income = 1 THEN loan_amount ELSE 0 END)"
        upper_income_metric_expr = "SUM(CASE WHEN is_upper_income = 1 THEN loan_amount ELSE 0 END)"
        lmict_metric_expr = "SUM(CASE WHEN is_lmict = 1 THEN loan_amount ELSE 0 END)"
        low_income_tract_metric_expr = "SUM(CASE WHEN is_low_income_tract = 1 THEN loan_amount ELSE 0 END)"
        moderate_income_tract_metric_expr = "SUM(CASE WHEN is_moderate_income_tract = 1 THEN loan_amount ELSE 0 END)"
        middle_income_tract_metric_expr = "SUM(CASE WHEN is_middle_income_tract = 1 THEN loan_amount ELSE 0 END)"
        upper_income_tract_metric_expr = "SUM(CASE WHEN is_upper_income_tract = 1 THEN loan_amount ELSE 0 END)"
        mmct_metric_expr = "SUM(CASE WHEN is_mmct = 1 THEN loan_amount ELSE 0 END)"
    
    query = f"""
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
    FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
    WHERE {where_clause}
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
    {total_metric_expr} as total_metric,
    -- Total loan amount
    SUM(COALESCE(f.loan_amount, 0)) as total_loan_amount,
    -- Race/Ethnicity breakdowns (applicant race - kept for backward compatibility)
    {hispanic_metric_expr} as hispanic_metric,
    {black_metric_expr} as black_metric,
    {asian_metric_expr} as asian_metric,
    {native_american_metric_expr} as native_american_metric,
    {hawaiian_pacific_islander_metric_expr} as hawaiian_pacific_islander_metric,
    {white_metric_expr} as white_metric,
    -- Income breakdowns
    {lmib_metric_expr} as lmib_metric,
    {low_income_metric_expr} as low_income_metric,
    {moderate_income_metric_expr} as moderate_income_metric,
    {middle_income_metric_expr} as middle_income_metric,
    {upper_income_metric_expr} as upper_income_metric,
    -- Neighborhood breakdowns
    {lmict_metric_expr} as lmict_metric,
    {low_income_tract_metric_expr} as low_income_tract_metric,
    {moderate_income_tract_metric_expr} as moderate_income_tract_metric,
    {middle_income_tract_metric_expr} as middle_income_tract_metric,
    {upper_income_tract_metric_expr} as upper_income_tract_metric,
    {mmct_metric_expr} as mmct_metric
FROM filtered_hmda f
LEFT JOIN (
    SELECT lei, 
           ANY_VALUE(respondent_name) as respondent_name,
           ANY_VALUE(type_name) as type_name
    FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.lenders18`
    GROUP BY lei
) l
    ON f.lei = l.lei
GROUP BY f.activity_year, f.lei, f.loan_purpose, f.geoid5
ORDER BY f.activity_year, total_metric DESC
"""
    
    return query


def build_sb_demographic_query(
    geoids: List[str],
    years: List[int],
    metric_type: str = 'count'  # 'count' or 'amount'
) -> str:
    """
    Build Small Business query broken down by demographics, income, and loan size for all lenders.
    
    Args:
        geoids: List of GEOID5 codes
        years: List of years
        metric_type: 'count' for number of loans, 'amount' for dollar amounts
    
    Returns:
        SQL query string
    """
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
    years_list = ", ".join([str(y) for y in years])
    
    # Build metric expressions based on metric_type
    # Note: These expressions reference columns from filtered_sb_data CTE, not d directly
    if metric_type == 'count':
        # Total should be sum of ALL loan size categories, not just loans under $1M revenue
        total_metric_expr = "SUM(COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0))"
        low_income_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('001','002','003','005','101','1','2','3','5') THEN COALESCE(sb_loans_count, 0) ELSE 0 END)"
        moderate_income_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('006','007','008','102','6','7','8') THEN COALESCE(sb_loans_count, 0) ELSE 0 END)"
        middle_income_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('004','009','010','011','012','103','4','9','10','11','12') THEN COALESCE(sb_loans_count, 0) ELSE 0 END)"
        upper_income_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('013','014','104','13','14') THEN COALESCE(sb_loans_count, 0) ELSE 0 END)"
        # LMICT data is not available at disclosure level - calculate from income_group_total
        # Income groups 001-008 (low and moderate) represent LMI tracts
        lmict_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('001','002','003','005','006','007','008','101','102','1','2','3','5','6','7','8') THEN COALESCE(sb_loans_count, 0) ELSE 0 END)"
        loans_under_100k_metric_expr = "SUM(COALESCE(num_under_100k, 0))"
        loans_100k_250k_metric_expr = "SUM(COALESCE(num_100k_250k, 0))"
        loans_250k_1m_metric_expr = "SUM(COALESCE(num_250k_1m, 0))"
        # Revenue category - for count, use numsbrev_under_1m (which is aliased as sb_loans_count in CTE)
        # This correctly represents loans to businesses under $1M revenue
        rev_under_1m_metric_expr = "SUM(COALESCE(sb_loans_count, 0))"  # This is numsbrev_under_1m from CTE
    else:
        # Total should be sum of ALL loan size category amounts, not just loans under $1M revenue
        total_metric_expr = "SUM(COALESCE(amt_under_100k, 0) + COALESCE(amt_100k_250k, 0) + COALESCE(amt_250k_1m, 0))"
        low_income_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('001','002','003','005','101','1','2','3','5') THEN COALESCE(sb_loans_amount, 0) ELSE 0 END)"
        moderate_income_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('006','007','008','102','6','7','8') THEN COALESCE(sb_loans_amount, 0) ELSE 0 END)"
        middle_income_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('004','009','010','011','012','103','4','9','10','11','12') THEN COALESCE(sb_loans_amount, 0) ELSE 0 END)"
        upper_income_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('013','014','104','13','14') THEN COALESCE(sb_loans_amount, 0) ELSE 0 END)"
        # LMICT data is not available at disclosure level - calculate from income_group_total
        # Income groups 001-008 (low and moderate) represent LMI tracts
        lmict_metric_expr = "SUM(CASE WHEN CAST(income_group_total AS STRING) IN ('001','002','003','005','006','007','008','101','102','1','2','3','5','6','7','8') THEN COALESCE(sb_loans_amount, 0) ELSE 0 END)"
        loans_under_100k_metric_expr = "SUM(COALESCE(amt_under_100k, 0))"
        loans_100k_250k_metric_expr = "SUM(COALESCE(amt_100k_250k, 0))"
        loans_250k_1m_metric_expr = "SUM(COALESCE(amt_250k_1m, 0))"
        # Revenue category - for amount, use amtsbrev_under_1m (which is aliased as sb_loans_amount in CTE)
        # This correctly represents loan amounts to businesses under $1M revenue
        rev_under_1m_metric_expr = "SUM(COALESCE(sb_loans_amount, 0))"  # This is amtsbrev_under_1m from CTE
    
    query = f"""
WITH cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        cbsa_code,
        CBSA as cbsa_name
    FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
),
filtered_sb_data AS (
    SELECT 
        CAST(d.year AS INT64) as year,
        c.cbsa_code,
        c.cbsa_name,
        CAST(d.geoid5 AS STRING) as geoid5,
        d.respondent_id as sb_resid,
        l.sb_lender as lender_name,
        d.income_group_total,
        d.numsbrev_under_1m as sb_loans_count,
        d.amtsbrev_under_1m as sb_loans_amount,
        d.num_under_100k,
        d.amt_under_100k,
        d.num_100k_250k,
        d.amt_100k_250k,
        d.num_250k_1m,
        d.amt_250k_1m
    FROM `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_DISCLOSURE_TABLE}` d
    JOIN `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_LENDERS_TABLE}` l 
        ON d.respondent_id = l.sb_resid
    LEFT JOIN cbsa_crosswalk c
        ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(c.county_code AS STRING), 5, '0')
    WHERE LPAD(CAST(d.geoid5 AS STRING), 5, '0') IN ('{geoid5_list}')
        AND CAST(d.year AS INT64) IN ({years_list})
        AND c.cbsa_code IS NOT NULL
)
SELECT 
    year,
    sb_resid,
    MAX(lender_name) as lender_name,
    -- Total metrics
    {total_metric_expr} as total_metric,
    -- Income breakdowns
    {low_income_metric_expr} as low_income_metric,
    {moderate_income_metric_expr} as moderate_income_metric,
    {middle_income_metric_expr} as middle_income_metric,
    {upper_income_metric_expr} as upper_income_metric,
    -- Neighborhood breakdowns
    {lmict_metric_expr} as lmict_metric,
    -- Loan size breakdowns
    {loans_under_100k_metric_expr} as loans_under_100k_metric,
    {loans_100k_250k_metric_expr} as loans_100k_250k_metric,
    {loans_250k_1m_metric_expr} as loans_250k_1m_metric,
    -- Revenue category breakdowns (for HHI calculation)
    {rev_under_1m_metric_expr} as rev_under_1m_metric
FROM filtered_sb_data
GROUP BY year, sb_resid
ORDER BY year, total_metric DESC
"""
    
    return query

