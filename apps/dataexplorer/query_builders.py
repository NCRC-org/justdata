#!/usr/bin/env python3
"""
Query builders for DataExplorer dashboard.
Builds flexible BigQuery queries for HMDA, Small Business, and Branch data
with comprehensive filtering options.
"""

from typing import List, Optional, Dict, Any
from .config import DataExplorerConfig


def build_hmda_query(
    geoids: List[str],
    years: List[int],
    leis: Optional[List[str]] = None,
    loan_purpose: Optional[List[str]] = None,
    action_taken: Optional[List[str]] = None,
    occupancy_type: Optional[List[str]] = None,
    total_units: Optional[List[str]] = None,
    construction_method: Optional[List[str]] = None,
    exclude_reverse_mortgages: bool = True,
    include_peer_comparison: bool = False,
    subject_lei: Optional[str] = None
) -> str:
    """
    Build HMDA query with flexible filtering.
    
    Args:
        geoids: List of GEOID5 codes (5-digit FIPS county codes)
        years: List of years to filter
        leis: Optional list of LEI codes to filter by lender
        loan_purpose: Optional list of loan purposes (e.g., ['1'] for home purchase)
        action_taken: Optional list of actions (e.g., ['1'] for originated)
        occupancy_type: Optional list of occupancy types (e.g., ['1'] for owner-occupied)
        total_units: Optional list of unit counts (e.g., ['1','2','3','4'] for 1-4 units)
        construction_method: Optional list of construction methods (e.g., ['1'] for site-built)
        exclude_reverse_mortgages: If True, exclude reverse mortgages (default: True)
        include_peer_comparison: If True, include peer comparison logic
        subject_lei: LEI of subject lender for peer comparison
    
    Returns:
        SQL query string
    """
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    # Format filters
    geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
    years_list = "', '".join([str(y) for y in years])
    
    # Build WHERE conditions
    # Filter by constructed geoid5 matching the provided geoids
    # Handle NULL values in state_code and county_code
    where_conditions = [
        f"CAST(h.activity_year AS STRING) IN ('{years_list}')",
        f"h.state_code IS NOT NULL",
        f"h.county_code IS NOT NULL",
        f"CONCAT(LPAD(CAST(h.state_code AS STRING), 2, '0'), LPAD(CAST(h.county_code AS STRING), 3, '0')) IN ('{geoid5_list}')"
    ]
    
    if leis:
        lei_list = "', '".join(leis)
        where_conditions.append(f"h.lei IN ('{lei_list}')")
    
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
    
    # Build demographic flags (similar to MergerMeter)
    query = f"""
WITH cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        cbsa_code,
        CBSA as cbsa_name
    FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
),
filtered_hmda AS (
    SELECT 
        CAST(h.activity_year AS STRING) as activity_year,
        c.cbsa_code,
        c.cbsa_name,
        CONCAT(LPAD(CAST(h.state_code AS STRING), 2, '0'), LPAD(CAST(h.county_code AS STRING), 3, '0')) as geoid5,
        h.lei,
        h.loan_amount,
        -- LMI Census Tract flag
        CASE 
            WHEN h.tract_to_msa_income_percentage IS NOT NULL
                AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80 
            THEN 1 ELSE 0 
        END as is_lmict,
        -- LMI Borrower flag
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
                ) = '5'
            THEN 1 ELSE 0 
        END as is_white
    FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
    LEFT JOIN cbsa_crosswalk c
        ON CONCAT(LPAD(CAST(h.state_code AS STRING), 2, '0'), LPAD(CAST(h.county_code AS STRING), 3, '0')) = LPAD(c.county_code, 5, '0')
    WHERE {where_clause}
"""
    
    # Add peer comparison logic if requested
    if include_peer_comparison and subject_lei:
        query += f"""
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
      AND al.lender_vol >= sv.subject_vol * {DataExplorerConfig.PEER_VOLUME_MIN}
      AND al.lender_vol <= sv.subject_vol * {DataExplorerConfig.PEER_VOLUME_MAX}
),
subject_data AS (
    SELECT f.*, 'subject' as lender_type
    FROM filtered_hmda f
    WHERE f.lei = '{subject_lei}'
),
peer_data AS (
    SELECT f.*, 'peer' as lender_type
    FROM filtered_hmda f
    INNER JOIN peers p
        ON f.activity_year = p.activity_year
        AND f.cbsa_code = p.cbsa_code
        AND f.lei = p.lei
)
SELECT * FROM subject_data
UNION ALL
SELECT * FROM peer_data
ORDER BY activity_year, cbsa_code, lender_type, lei
"""
    else:
        query += """
)
SELECT * FROM filtered_hmda
ORDER BY activity_year, cbsa_code, lei
LIMIT 100000
"""
    
    return query


def build_small_business_query(
    geoids: List[str],
    years: List[int],
    respondent_ids: Optional[List[str]] = None,
    include_peer_comparison: bool = False,
    subject_respondent_id: Optional[str] = None
) -> str:
    """
    Build Small Business lending query with flexible filtering.
    
    Args:
        geoids: List of GEOID5 codes (5-digit FIPS county codes)
        years: List of years to filter
        respondent_ids: Optional list of small business respondent IDs to filter by lender
        include_peer_comparison: If True, include peer comparison logic
        subject_respondent_id: Respondent ID of subject lender for peer comparison
    
    Returns:
        SQL query string
    """
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    # Format filters
    geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
    years_list = ", ".join([str(y) for y in years])
    
    # Build WHERE conditions
    where_conditions = [
        f"CAST(d.geoid5 AS STRING) IN ('{geoid5_list}')",
        f"CAST(d.year AS INT64) IN ({years_list})"
    ]
    
    if respondent_ids:
        # Handle both with and without prefix
        id_conditions = []
        for rid in respondent_ids:
            rid_clean = rid.replace('SB', '').replace('sb', '')
            id_conditions.append(f"(d.respondent_id = '{rid}' OR d.respondent_id = '{rid_clean}')")
        where_conditions.append(f"({' OR '.join(id_conditions)})")
    
    where_clause = " AND ".join(where_conditions)
    
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
    WHERE {where_clause}
        AND c.cbsa_code IS NOT NULL
"""
    
    # Add peer comparison logic if requested
    if include_peer_comparison and subject_respondent_id:
        respondent_id_no_prefix = subject_respondent_id.replace('SB', '').replace('sb', '')
        query += f"""
),
subject_sb_volume AS (
    SELECT 
        year,
        cbsa_code,
        SUM(sb_loans_count) as subject_sb_vol
    FROM filtered_sb_data
    WHERE sb_resid = '{respondent_id_no_prefix}' OR sb_resid = '{subject_respondent_id}'
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
    WHERE (al.sb_resid != '{respondent_id_no_prefix}' AND al.sb_resid != '{subject_respondent_id}')
      AND al.lender_sb_vol >= sv.subject_sb_vol * {DataExplorerConfig.PEER_VOLUME_MIN}
      AND al.lender_sb_vol <= sv.subject_sb_vol * {DataExplorerConfig.PEER_VOLUME_MAX}
),
subject_data AS (
    SELECT f.*, 'subject' as lender_type
    FROM filtered_sb_data f
    WHERE f.sb_resid = '{respondent_id_no_prefix}' OR f.sb_resid = '{subject_respondent_id}'
),
peer_data AS (
    SELECT f.*, 'peer' as lender_type
    FROM filtered_sb_data f
    INNER JOIN peers p
        ON f.year = p.year
        AND f.cbsa_code = p.cbsa_code
        AND f.sb_resid = p.sb_resid
)
SELECT * FROM subject_data
UNION ALL
SELECT * FROM peer_data
ORDER BY year, cbsa_code, lender_type, sb_resid
"""
    else:
        query += """
)
SELECT * FROM filtered_sb_data
ORDER BY year, cbsa_code, sb_resid
"""
    
    return query


def build_branch_query(
    geoids: List[str],
    years: List[int],
    rssd_ids: Optional[List[str]] = None,
    include_peer_comparison: bool = False,
    subject_rssd: Optional[str] = None
) -> str:
    """
    Build Branch (FDIC SOD) query with flexible filtering and income/minority tract categorization.
    
    Args:
        geoids: List of GEOID5 codes (5-digit FIPS county codes)
        years: List of years to filter
        rssd_ids: Optional list of RSSD IDs to filter by bank
        include_peer_comparison: If True, include peer comparison logic
        subject_rssd: RSSD ID of subject bank for peer comparison
    
    Returns:
        SQL query string
    """
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    # Format filters
    geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
    years_list = "', '".join([str(y) for y in years])
    
    # Build WHERE conditions
    where_conditions = [
        f"CAST(b.geoid5 AS STRING) IN ('{geoid5_list}')",
        f"CAST(b.year AS STRING) IN ('{years_list}')"
    ]
    
    if rssd_ids:
        rssd_list = "', '".join(rssd_ids)
        where_conditions.append(f"CAST(b.rssd AS STRING) IN ('{rssd_list}')")
    
    where_clause = " AND ".join(where_conditions)
    
    # Determine which tables to query based on years
    legacy_years = [y for y in years if y < 2025]
    sod25_years = [y for y in years if y >= 2025]
    
    # Build branch data CTE with proper table selection
    branch_table_queries = []
    
    if legacy_years:
        legacy_years_list = "', '".join([str(y) for y in legacy_years])
        branch_table_queries.append(f"""
            SELECT 
                CAST(year AS STRING) as year,
                CAST(geoid5 AS STRING) as geoid5,
                CAST(rssd AS STRING) as rssd,
                bank_name,
                branch_name,
                address,
                city,
                state,
                zip,
                CAST(deposits_000s AS FLOAT64) * 1000 as deposits,
                CAST(br_lmi AS INT64) as is_lmi_tract,
                CAST(br_minority AS INT64) as is_mmct_tract,
                uninumbr,
                geoid as census_tract
            FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.sod_legacy`
            WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') IN ('{geoid5_list}')
                AND CAST(year AS STRING) IN ('{legacy_years_list}')
        """)
    
    if sod25_years:
        sod25_years_list = "', '".join([str(y) for y in sod25_years])
        branch_table_queries.append(f"""
            SELECT 
                CAST(year AS STRING) as year,
                CAST(geoid5 AS STRING) as geoid5,
                CAST(rssd AS STRING) as rssd,
                bank_name,
                branch_name,
                address,
                city,
                state,
                zip,
                CAST(deposits_000s AS FLOAT64) * 1000 as deposits,
                CAST(br_lmi AS INT64) as is_lmi_tract,
                CAST(br_minority AS INT64) as is_mmct_tract,
                uninumbr,
                geoid as census_tract
            FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}`
                WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') IN ('{geoid5_list}')
                AND CAST(year AS STRING) IN ('{sod25_years_list}')
        """)
    
    # If no years match, use default table
    if not branch_table_queries:
        branch_table_queries.append(f"""
            SELECT 
                CAST(year AS STRING) as year,
                CAST(geoid5 AS STRING) as geoid5,
                CAST(rssd AS STRING) as rssd,
                bank_name,
                branch_name,
                address,
                city,
                state,
                zip,
                CAST(deposits_000s AS FLOAT64) * 1000 as deposits,
                CAST(br_lmi AS INT64) as is_lmi_tract,
                CAST(cr_minority AS INT64) as is_mmct_tract,
                uninumbr,
                census_tract
            FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}`
            WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') IN ('{geoid5_list}')
                AND CAST(year AS STRING) IN ('{years_list}')
        """)
    
    branch_union = " UNION ALL ".join(branch_table_queries)
    
    # Get tract-level income and minority percentages from HMDA table for categorization
    # We'll join on geoid5 and census_tract to get tract characteristics
    hmda_years_list = "', '".join([str(y) for y in years if y >= 2018 and y <= 2024])
    
    query = f"""
WITH cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        cbsa_code,
        CBSA as cbsa_name,
        County as county_name,
        State as state_name
    FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
),
branch_data AS (
    {branch_union}
),
tract_characteristics AS (
    SELECT DISTINCT
        CAST(h.activity_year AS STRING) as year,
        CONCAT(LPAD(CAST(h.state_code AS STRING), 2, '0'), LPAD(CAST(h.county_code AS STRING), 3, '0')) as geoid5,
        h.census_tract,
        CAST(h.tract_to_msa_income_percentage AS FLOAT64) as tract_to_msa_income_percentage,
        CAST(h.tract_minority_population_percent AS FLOAT64) as tract_minority_population_percent
    FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
    WHERE CONCAT(LPAD(CAST(h.state_code AS STRING), 2, '0'), LPAD(CAST(h.county_code AS STRING), 3, '0')) IN ('{geoid5_list}')
        AND CAST(h.activity_year AS STRING) IN ('{hmda_years_list}')
        AND h.census_tract IS NOT NULL
        AND h.tract_to_msa_income_percentage IS NOT NULL
        AND h.tract_minority_population_percent IS NOT NULL
),
filtered_branches AS (
    SELECT 
        b.year,
        c.cbsa_code,
        c.cbsa_name,
        b.geoid5,
        c.county_name,
        c.state_name,
        b.rssd,
        b.bank_name,
        b.branch_name,
        b.address,
        b.city,
        b.state,
        b.zip,
        b.deposits,
        b.is_lmi_tract,
        b.is_mmct_tract,
        b.uninumbr,
        b.census_tract,
        -- Income tract categorization (based on tract_to_msa_income_percentage)
        CASE 
            WHEN t.tract_to_msa_income_percentage IS NOT NULL
                AND t.tract_to_msa_income_percentage <= 50 
            THEN 1 ELSE 0 
        END as is_low_income_tract,
        CASE 
            WHEN t.tract_to_msa_income_percentage IS NOT NULL
                AND t.tract_to_msa_income_percentage > 50
                AND t.tract_to_msa_income_percentage <= 80 
            THEN 1 ELSE 0 
        END as is_moderate_income_tract,
        CASE 
            WHEN t.tract_to_msa_income_percentage IS NOT NULL
                AND t.tract_to_msa_income_percentage > 80
                AND t.tract_to_msa_income_percentage <= 120 
            THEN 1 ELSE 0 
        END as is_middle_income_tract,
        CASE 
            WHEN t.tract_to_msa_income_percentage IS NOT NULL
                AND t.tract_to_msa_income_percentage > 120 
            THEN 1 ELSE 0 
        END as is_upper_income_tract,
        -- Store tract percentages for minority categorization (done in post-processing)
        t.tract_to_msa_income_percentage,
        t.tract_minority_population_percent
    FROM branch_data b
    LEFT JOIN cbsa_crosswalk c
        ON LPAD(CAST(b.geoid5 AS STRING), 5, '0') = LPAD(CAST(c.county_code AS STRING), 5, '0')
    LEFT JOIN tract_characteristics t
        ON b.year = t.year
        AND b.geoid5 = t.geoid5
        AND CAST(b.census_tract AS STRING) = CAST(t.census_tract AS STRING)
    WHERE LPAD(CAST(b.geoid5 AS STRING), 5, '0') IN ('{geoid5_list}')
        AND CAST(b.year AS STRING) IN ('{years_list}')
"""
    
    # Add peer comparison logic if requested
    if include_peer_comparison and subject_rssd:
        query += f"""
),
subject_branch_volume AS (
    SELECT 
        year,
        cbsa_code,
        COUNT(*) as subject_branch_count,
        SUM(deposits) as subject_deposits
    FROM filtered_branches
    WHERE rssd = '{subject_rssd}'
    GROUP BY year, cbsa_code
),
all_banks_volume AS (
    SELECT 
        year,
        cbsa_code,
        rssd,
        COUNT(*) as bank_branch_count,
        SUM(deposits) as bank_deposits
    FROM filtered_branches
    GROUP BY year, cbsa_code, rssd
),
peers AS (
    SELECT DISTINCT
        ab.year,
        ab.cbsa_code,
        ab.rssd
    FROM all_banks_volume ab
    INNER JOIN subject_branch_volume sv
        ON ab.year = sv.year
        AND ab.cbsa_code = sv.cbsa_code
    WHERE ab.rssd != '{subject_rssd}'
      AND ab.bank_branch_count >= sv.subject_branch_count * {DataExplorerConfig.PEER_VOLUME_MIN}
      AND ab.bank_branch_count <= sv.subject_branch_count * {DataExplorerConfig.PEER_VOLUME_MAX}
),
subject_data AS (
    SELECT f.*, 'subject' as bank_type
    FROM filtered_branches f
    WHERE f.rssd = '{subject_rssd}'
),
peer_data AS (
    SELECT f.*, 'peer' as bank_type
    FROM filtered_branches f
    INNER JOIN peers p
        ON f.year = p.year
        AND f.cbsa_code = p.cbsa_code
        AND f.rssd = p.rssd
)
SELECT * FROM subject_data
UNION ALL
SELECT * FROM peer_data
ORDER BY year, cbsa_code, bank_type, rssd
"""
    else:
        query += """
)
SELECT * FROM filtered_branches
ORDER BY year, cbsa_code, rssd
"""
    
    return query


# ============================================================================
# Lender Analysis Query Builders (Adapted from MergerMeter)
# ============================================================================

def build_lender_hmda_subject_query(
    subject_lei: str,
    geoids: List[str],
    years: List[int],
    loan_purpose: Optional[List[str]] = None,
    action_taken: Optional[List[str]] = None,
    occupancy_type: Optional[List[str]] = None,
    total_units: Optional[List[str]] = None,
    construction_method: Optional[List[str]] = None,
    exclude_reverse_mortgages: bool = True
) -> str:
    """
    Build HMDA query for subject lender (adapted from MergerMeter).
    
    Args:
        subject_lei: Subject lender's LEI
        geoids: List of GEOID5 codes
        years: List of years
        loan_purpose: Optional list of loan purposes (e.g., ['1', '31,32'])
        action_taken: Optional list of action taken codes
        occupancy_type: Optional list of occupancy types
        total_units: Optional list of unit counts
        construction_method: Optional list of construction methods
        exclude_reverse_mortgages: If True, exclude reverse mortgages
    
    Returns:
        SQL query string
    """
    # Import MergerMeter query builder
    from apps.mergermeter.query_builders import build_hmda_subject_query
    
    # Convert Data Explorer format to MergerMeter format
    years_str = [str(y) for y in years]
    loan_purpose_str = ','.join(loan_purpose) if loan_purpose else None
    action_taken_str = ','.join(action_taken) if action_taken else '1,2,3,4,5'
    occupancy_type_str = ','.join(occupancy_type) if occupancy_type else '1'
    total_units_str = ','.join(total_units) if total_units else '1,2,3,4'
    construction_method_str = ','.join(construction_method) if construction_method else '1'
    not_reverse_str = '1' if exclude_reverse_mortgages else None
    
    return build_hmda_subject_query(
        subject_lei=subject_lei,
        assessment_area_geoids=geoids,
        years=years_str,
        loan_purpose=loan_purpose_str,
        action_taken=action_taken_str,
        occupancy_type=occupancy_type_str,
        total_units=total_units_str,
        construction_method=construction_method_str,
        not_reverse=not_reverse_str
    )


def build_lender_hmda_peer_query(
    subject_lei: str,
    geoids: List[str],
    years: List[int],
    loan_purpose: Optional[List[str]] = None,
    action_taken: Optional[List[str]] = None,
    occupancy_type: Optional[List[str]] = None,
    total_units: Optional[List[str]] = None,
    construction_method: Optional[List[str]] = None,
    exclude_reverse_mortgages: bool = True,
    custom_peer_leis: Optional[List[str]] = None
) -> str:
    """
    Build HMDA query for peer lenders (adapted from MergerMeter).
    
    Args:
        subject_lei: Subject lender's LEI
        geoids: List of GEOID5 codes
        years: List of years
        loan_purpose: Optional list of loan purposes
        action_taken: Optional list of action taken codes
        occupancy_type: Optional list of occupancy types
        total_units: Optional list of unit counts
        construction_method: Optional list of construction methods
        exclude_reverse_mortgages: If True, exclude reverse mortgages
        custom_peer_leis: Optional list of custom peer LEIs to include
    
    Returns:
        SQL query string
    """
    # Import MergerMeter query builder
    from apps.mergermeter.query_builders import build_hmda_peer_query
    
    # Convert Data Explorer format to MergerMeter format
    years_str = [str(y) for y in years]
    loan_purpose_str = ','.join(loan_purpose) if loan_purpose else None
    action_taken_str = ','.join(action_taken) if action_taken else '1,2,3,4,5'
    occupancy_type_str = ','.join(occupancy_type) if occupancy_type else '1'
    total_units_str = ','.join(total_units) if total_units else '1,2,3,4'
    construction_method_str = ','.join(construction_method) if construction_method else '1'
    not_reverse_str = '1' if exclude_reverse_mortgages else None
    
    # Build base peer query
    base_query = build_hmda_peer_query(
        subject_lei=subject_lei,
        assessment_area_geoids=geoids,
        years=years_str,
        loan_purpose=loan_purpose_str,
        action_taken=action_taken_str,
        occupancy_type=occupancy_type_str,
        total_units=total_units_str,
        construction_method=construction_method_str,
        not_reverse=not_reverse_str
    )
    
    # If custom peers specified, add UNION to include them
    if custom_peer_leis:
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
        years_list = "', '".join([str(y) for y in years])
        custom_lei_list = "', '".join(custom_peer_leis)
        
        # Build query for custom peers (similar structure but without volume filtering)
        custom_peer_query = f"""
UNION ALL
SELECT 
    CAST(h.activity_year AS STRING) as activity_year,
    c.cbsa_code,
    COUNT(*) as total_loans,
    SUM(h.loan_amount) as total_amount,
    COUNTIF(CASE WHEN h.tract_to_msa_income_percentage IS NOT NULL
        AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80 THEN 1 ELSE 0 END = 1) as lmict_loans,
    SAFE_DIVIDE(COUNTIF(CASE WHEN h.tract_to_msa_income_percentage IS NOT NULL
        AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80 THEN 1 ELSE 0 END = 1), COUNT(*)) * 100 as lmict_percentage,
    COUNTIF(CASE WHEN h.income IS NOT NULL
        AND h.ffiec_msa_md_median_family_income IS NOT NULL
        AND h.ffiec_msa_md_median_family_income > 0
        AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
        THEN 1 ELSE 0 END = 1) as lmib_loans,
    SAFE_DIVIDE(COUNTIF(CASE WHEN h.income IS NOT NULL
        AND h.ffiec_msa_md_median_family_income IS NOT NULL
        AND h.ffiec_msa_md_median_family_income > 0
        AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
        THEN 1 ELSE 0 END = 1), COUNT(*)) * 100 as lmib_percentage,
    SUM(CASE WHEN h.income IS NOT NULL
        AND h.ffiec_msa_md_median_family_income IS NOT NULL
        AND h.ffiec_msa_md_median_family_income > 0
        AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
        THEN h.loan_amount ELSE 0 END) as lmib_amount,
    COUNTIF(CASE WHEN h.tract_minority_population_percent IS NOT NULL
        AND CAST(h.tract_minority_population_percent AS FLOAT64) > 50 THEN 1 ELSE 0 END = 1) as mmct_loans,
    SAFE_DIVIDE(COUNTIF(CASE WHEN h.tract_minority_population_percent IS NOT NULL
        AND CAST(h.tract_minority_population_percent AS FLOAT64) > 50 THEN 1 ELSE 0 END = 1), COUNT(*)) * 100 as mmct_percentage,
    COUNTIF(CASE WHEN h.applicant_ethnicity_1 IN ('1','11','12','13','14')
        OR h.applicant_race_1 IN ('3','2','21','22','23','24','25','26','27','1','5','4','41','42','43','44')
        THEN 1 ELSE 0 END = 1) as minb_loans,
    SAFE_DIVIDE(COUNTIF(CASE WHEN h.applicant_ethnicity_1 IN ('1','11','12','13','14')
        OR h.applicant_race_1 IN ('3','2','21','22','23','24','25','26','27','1','5','4','41','42','43','44')
        THEN 1 ELSE 0 END = 1), COUNT(*)) * 100 as minb_percentage
FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
LEFT JOIN `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}` c
    ON CAST(h.county_code AS STRING) = c.county_code
WHERE CAST(h.activity_year AS STRING) IN ('{years_list}')
    AND CAST(h.county_code AS STRING) IN ('{geoid5_list}')
    AND h.lei IN ('{custom_lei_list}')
    AND h.lei != '{subject_lei}'
"""
        
        # Add filters
        if loan_purpose:
            purpose_list = "', '".join(loan_purpose)
            custom_peer_query += f"    AND h.loan_purpose IN ('{purpose_list}')\n"
        if action_taken:
            action_list = "', '".join(action_taken)
            custom_peer_query += f"    AND h.action_taken IN ('{action_list}')\n"
        if occupancy_type:
            occupancy_list = "', '".join(occupancy_type)
            custom_peer_query += f"    AND h.occupancy_type IN ('{occupancy_list}')\n"
        if total_units:
            units_list = "', '".join(total_units)
            custom_peer_query += f"    AND h.total_units IN ('{units_list}')\n"
        if construction_method:
            construction_list = "', '".join(construction_method)
            custom_peer_query += f"    AND h.construction_method IN ('{construction_list}')\n"
        if exclude_reverse_mortgages:
            custom_peer_query += "    AND h.reverse_mortgage != '1'\n"
        
        custom_peer_query += """GROUP BY activity_year, cbsa_code
"""
        return base_query + custom_peer_query
    
    return base_query


def build_lender_sb_subject_query(
    subject_respondent_id: str,
    geoids: List[str],
    years: List[int]
) -> str:
    """
    Build Small Business query for subject lender (adapted from MergerMeter).
    
    Args:
        subject_respondent_id: Subject lender's SB Respondent ID
        geoids: List of GEOID5 codes
        years: List of years
    
    Returns:
        SQL query string
    """
    from apps.mergermeter.query_builders import build_sb_subject_query
    
    years_str = [str(y) for y in years]
    return build_sb_subject_query(
        sb_respondent_id=subject_respondent_id,
        assessment_area_geoids=geoids,
        years=years_str
    )


def build_lender_sb_peer_query(
    subject_respondent_id: str,
    geoids: List[str],
    years: List[int],
    custom_peer_ids: Optional[List[str]] = None
) -> str:
    """
    Build Small Business query for peer lenders (adapted from MergerMeter).
    
    Args:
        subject_respondent_id: Subject lender's SB Respondent ID
        geoids: List of GEOID5 codes
        years: List of years
        custom_peer_ids: Optional list of custom peer respondent IDs
    
    Returns:
        SQL query string
    """
    from apps.mergermeter.query_builders import build_sb_peer_query
    
    years_str = [str(y) for y in years]
    base_query = build_sb_peer_query(
        sb_respondent_id=subject_respondent_id,
        assessment_area_geoids=geoids,
        years=years_str
    )
    
    # TODO: Add custom peer support for SB if needed
    # For now, return base query
    return base_query


def build_lender_branch_subject_query(
    subject_rssd: str,
    geoids: List[str],
    year: int = 2025
) -> str:
    """
    Build Branch query for subject lender (adapted from MergerMeter).
    
    Args:
        subject_rssd: Subject lender's RSSD
        geoids: List of GEOID5 codes
        year: Year for branch data (default: 2025)
    
    Returns:
        SQL query string
    """
    from apps.mergermeter.query_builders import build_branch_query
    
    return build_branch_query(
        subject_rssd=subject_rssd,
        assessment_area_geoids=geoids,
        year=year
    )


def build_lender_branch_peer_query(
    subject_rssd: str,
    geoids: List[str],
    year: int = 2025,
    custom_peer_rssds: Optional[List[str]] = None
) -> str:
    """
    Build Branch query for peer lenders (adapted from MergerMeter).
    
    Args:
        subject_rssd: Subject lender's RSSD
        geoids: List of GEOID5 codes
        year: Year for branch data (default: 2025)
        custom_peer_rssds: Optional list of custom peer RSSDs
    
    Returns:
        SQL query string
    """
    from apps.mergermeter.query_builders import build_branch_market_query
    
    base_query = build_branch_market_query(
        subject_rssd=subject_rssd,
        assessment_area_geoids=geoids,
        year=year
    )
    
    # TODO: Add custom peer support for branches if needed
    # For now, return base query (market query already includes all peers)
    return base_query

