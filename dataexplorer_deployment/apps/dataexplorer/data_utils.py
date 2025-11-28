#!/usr/bin/env python3
"""
Data utilities for DataExplorer dashboard.
Handles fetching available options (counties, lenders, etc.) and executing queries.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter, ArrayQueryParameter
from google.oauth2 import service_account
from .config import DataExplorerConfig

# Set up logger
logger = logging.getLogger(__name__)

# Add repo root to path to use shared utilities
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))


def get_bigquery_client():
    """Get BigQuery client with credential search like other apps."""
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    try:
        # First, check environment variable
        env_cred_path = None
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            env_cred_path = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
            if env_cred_path.exists():
                credentials = service_account.Credentials.from_service_account_file(str(env_cred_path))
                client = bigquery.Client(credentials=credentials, project=project_id)
                return client
        
        # Try to find credentials file in common locations (cross-platform)
        possible_paths = [
            # Environment-based paths
            Path("config/credentials/hdma1-242116-74024e2eb88f.json"),
            Path("hdma1-242116-74024e2eb88f.json"),
            REPO_ROOT / "config" / "credentials" / "hdma1-242116-74024e2eb88f.json",
            REPO_ROOT / "credentials" / "hdma1-242116-74024e2eb88f.json",
            # Windows-specific paths (if on Windows)
            Path("C:/DREAM/config/credentials/hdma1-242116-74024e2eb88f.json") if os.name == 'nt' else None,
            Path("C:/DREAM/config/credentials/hdma1-242116-74024e2eb88f_20251102_180816.json") if os.name == 'nt' else None,
            Path("C:/DREAM/hdma1-242116-74024e2eb88f.json") if os.name == 'nt' else None,
        ]
        
        # Filter out None values (non-Windows paths)
        possible_paths = [p for p in possible_paths if p is not None]
        
        # Also search the credentials directory for any matching JSON files
        # Try multiple possible credential directory locations
        cred_dirs = [
            REPO_ROOT / "config" / "credentials",
            REPO_ROOT / "credentials",
            Path("config/credentials"),
        ]
        if os.name == 'nt':  # Windows
            cred_dirs.append(Path("C:/DREAM/config/credentials"))
        
        for cred_dir in cred_dirs:
            if cred_dir.exists():
                for json_file in cred_dir.glob("hdma1-*.json"):
                    if json_file not in possible_paths:
                        possible_paths.append(json_file)
        
        cred_path = None
        for path in possible_paths:
            if path.exists():
                cred_path = path
                break
        
        if cred_path:
            credentials = service_account.Credentials.from_service_account_file(str(cred_path))
            client = bigquery.Client(credentials=credentials, project=project_id)
            return client
        
        # Fallback: try default service account
        logger.info("No credentials file found, trying default service account...")
        client = bigquery.Client(project=project_id)
        return client
        
    except Exception as e:
        logger.error(f"Error creating BigQuery client: {e}")
        # Try one more time with default credentials
        try:
            logger.info("Attempting to use default application credentials...")
            client = bigquery.Client(project=project_id)
            return client
        except Exception as e2:
            logger.error(f"Error with default credentials: {e2}")
            raise


def get_available_states() -> List[Dict[str, str]]:
    """Get list of available states."""
    try:
        client = get_bigquery_client()
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        
        query = f"""
        SELECT DISTINCT
            State as state_name,
            State_Code as state_code
        FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
        WHERE State IS NOT NULL
        ORDER BY State
        """
        
        query_job = client.query(query)
        results = query_job.result()
        return [{"name": row.state_name, "code": str(row.state_code)} for row in results]
    except Exception as e:
        print(f"Error in get_available_states: {e}")
        import traceback
        traceback.print_exc()
        raise


def get_available_counties(state_code: Optional[str] = None) -> List[Dict[str, str]]:
    """Get list of available counties, optionally filtered by state."""
    try:
        client = get_bigquery_client()
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        
        state_filter = ""
        if state_code:
            state_filter = f"AND State_Code = '{state_code}'"
        
        query = f"""
        SELECT DISTINCT
            geoid5,
            County as county_name,
            State as state_name,
            State_Code as state_code,
            CONCAT(County, ', ', State) as county_state
        FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
        WHERE County IS NOT NULL {state_filter}
        ORDER BY State, County
        """
        
        query_job = client.query(query)
        results = query_job.result()
        return [
            {
                "geoid5": str(row.geoid5).zfill(5),
                "name": row.county_name,
                "state": row.state_name,
                "state_code": str(row.state_code),
                "county_state": row.county_state
            }
            for row in results
        ]
    except Exception as e:
        print(f"Error in get_available_counties: {e}")
        import traceback
        traceback.print_exc()
        raise


def get_available_metros() -> List[Dict[str, str]]:
    """Get list of available metro areas (CBSAs)."""
    try:
        client = get_bigquery_client()
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        
        query = f"""
        SELECT DISTINCT
            cbsa_code,
            CBSA as cbsa_name
        FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
        WHERE cbsa_code IS NOT NULL
        ORDER BY CBSA
        """
        
        query_job = client.query(query)
        results = query_job.result()
        return [{"code": str(row.cbsa_code), "name": row.cbsa_name} for row in results]
    except Exception as e:
        print(f"Error in get_available_metros: {e}")
        import traceback
        traceback.print_exc()
        raise


def expand_geoids(geoids: List[str]) -> List[str]:
    """
    Expand geoids to county geoids. If a geoid is a metro code (CBSA) or state code,
    expand it to all counties in that metro/state.
    
    Args:
        geoids: List of geoids (can be county geoids, metro codes, or state codes)
    
    Returns:
        List of county geoids (5-digit strings)
    """
    if not geoids:
        return []
    
    client = get_bigquery_client()
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    # First, check which 5-digit codes are metro codes vs county geoids
    potential_metros = []
    potential_counties = []
    state_codes = []
    
    for geoid in geoids:
        geoid_str = str(geoid).strip()
        # State codes are 2 digits
        if len(geoid_str) == 2 and geoid_str.isdigit():
            state_codes.append(geoid_str.zfill(2))
        # 5-digit codes could be either metro codes or county geoids
        elif len(geoid_str) == 5:
            potential_metros.append(geoid_str)
        else:
            # Assume it's a county geoid
            potential_counties.append(geoid_str.zfill(5))
    
    expanded_geoids = set(potential_counties)
    
    # Check which 5-digit codes are metro codes by querying the database
    if potential_metros:
        metro_list = "', '".join(potential_metros)
        # First, find which ones are metro codes
        metro_check_query = f"""
        SELECT DISTINCT CAST(cbsa_code AS STRING) as cbsa_code
        FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
        WHERE CAST(cbsa_code AS STRING) IN ('{metro_list}')
        """
        try:
            query_job = client.query(metro_check_query)
            results = query_job.result()
            found_metros = {str(row.cbsa_code) for row in results}
            
            # Separate metros from counties
            actual_metros = [m for m in potential_metros if m in found_metros]
            actual_counties = [m for m in potential_metros if m not in found_metros]
            
            # Add actual counties to the set
            for county in actual_counties:
                expanded_geoids.add(county.zfill(5))
            
            # Expand metro codes to counties
            if actual_metros:
                metro_list_expand = "', '".join(actual_metros)
                expand_query = f"""
                SELECT DISTINCT CAST(geoid5 AS STRING) as geoid5
                FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
                WHERE CAST(cbsa_code AS STRING) IN ('{metro_list_expand}')
                """
                query_job = client.query(expand_query)
                results = query_job.result()
                for row in results:
                    expanded_geoids.add(str(row.geoid5).zfill(5))
        except Exception as e:
            print(f"Error checking/expanding metro codes: {e}")
            # On error, assume all 5-digit codes are counties
            for code in potential_metros:
                expanded_geoids.add(code.zfill(5))
    
    # Expand state codes to counties
    if state_codes:
        state_list = "', '".join(state_codes)
        query = f"""
        SELECT DISTINCT CAST(geoid5 AS STRING) as geoid5
        FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
        WHERE SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) IN ('{state_list}')
        """
        try:
            query_job = client.query(query)
            results = query_job.result()
            for row in results:
                expanded_geoids.add(str(row.geoid5).zfill(5))
        except Exception as e:
            print(f"Error expanding state codes: {e}")
    
    return sorted(list(expanded_geoids))


def get_available_hmda_lenders(geoids: Optional[List[str]] = None, years: Optional[List[int]] = None) -> List[Dict[str, str]]:
    """Get list of available HMDA lenders, optionally filtered by geography and years."""
    client = get_bigquery_client()
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    where_conditions = []
    
    if geoids:
        geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
        where_conditions.append(
            f"CONCAT(LPAD(CAST(state_code AS STRING), 2, '0'), LPAD(CAST(county_code AS STRING), 3, '0')) IN ('{geoid5_list}')"
        )
    
    if years:
        years_list = "', '".join([str(y) for y in years])
        where_conditions.append(f"CAST(activity_year AS STRING) IN ('{years_list}')")
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    query = f"""
    SELECT DISTINCT
        lei,
        COUNT(*) as loan_count
    FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}`
    WHERE {where_clause}
    GROUP BY lei
    HAVING loan_count > 0
    ORDER BY loan_count DESC
    LIMIT 1000
    """
    
    query_job = client.query(query)
    results = query_job.result()
    return [{"lei": row.lei, "loan_count": row.loan_count} for row in results]


def get_available_sb_lenders(geoids: Optional[List[str]] = None, years: Optional[List[int]] = None) -> List[Dict[str, str]]:
    """Get list of available Small Business lenders, optionally filtered by geography and years."""
    client = get_bigquery_client()
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    where_conditions = []
    
    if geoids:
        geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
        where_conditions.append(f"CAST(geoid5 AS STRING) IN ('{geoid5_list}')")
    
    if years:
        years_list = ", ".join([str(y) for y in years])
        where_conditions.append(f"CAST(year AS INT64) IN ({years_list})")
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    query = f"""
    SELECT DISTINCT
        d.respondent_id as sb_resid,
        l.sb_lender as lender_name,
        SUM(d.numsbrev_under_1m) as loan_count
    FROM `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_DISCLOSURE_TABLE}` d
    JOIN `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_LENDERS_TABLE}` l
        ON d.respondent_id = l.sb_resid
    WHERE {where_clause}
    GROUP BY d.respondent_id, l.sb_lender
    HAVING loan_count > 0
    ORDER BY loan_count DESC
    LIMIT 1000
    """
    
    query_job = client.query(query)
    results = query_job.result()
    return [
        {
            "respondent_id": row.sb_resid,
            "name": row.lender_name,
            "loan_count": row.loan_count
        }
        for row in results
    ]


def get_lender_counties_by_lending_activity(
    lender_id: str,
    years: Optional[List[int]] = None,
    action_taken: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """
    Get counties where lender has loan applications (action_taken 1-5).
    
    Args:
        lender_id: LEI for HMDA lender
        years: Optional list of years to consider
        action_taken: Optional list of action_taken codes (default: ['1','2','3','4','5'])
    
    Returns:
        List of dictionaries with county information
    """
    if not lender_id:
        return []
    
    if not action_taken:
        action_taken = ['1', '2', '3', '4', '5']  # All applications
    
    client = get_bigquery_client()
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    if not years:
        years = DataExplorerConfig.HMDA_YEARS[-3:]  # Last 3 years
    
    years_list = "', '".join([str(y) for y in years])
    action_list = "', '".join(action_taken)
    
    # Apply 1% threshold: only return counties where lender has ≥1% of their total applications
    query = f"""
    WITH lender_county_apps AS (
        SELECT 
            CONCAT(LPAD(CAST(h.state_code AS STRING), 2, '0'), LPAD(CAST(h.county_code AS STRING), 3, '0')) as geoid5,
            COUNT(*) as county_apps
        FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
        WHERE h.lei = '{lender_id}'
            AND CAST(h.activity_year AS STRING) IN ('{years_list}')
            AND h.action_taken IN ('{action_list}')
            AND h.state_code IS NOT NULL
            AND h.county_code IS NOT NULL
        GROUP BY geoid5
    ),
    lender_total_apps AS (
        SELECT SUM(county_apps) as total_apps
        FROM lender_county_apps
    )
    SELECT DISTINCT
        lca.geoid5,
        c.County as county_name,
        c.State as state_name,
        CONCAT(c.County, ', ', c.State) as county_state,
        lca.county_apps as application_count
    FROM lender_county_apps lca
    CROSS JOIN lender_total_apps lta
    JOIN `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}` c
        ON lca.geoid5 = CAST(c.geoid5 AS STRING)
    WHERE lta.total_apps > 0
        AND SAFE_DIVIDE(lca.county_apps, lta.total_apps) >= 0.01  -- 1% threshold
    ORDER BY c.State, c.County
    """
    
    try:
        query_job = client.query(query)
        results = query_job.result()
        return [
            {
                "geoid5": str(row.geoid5).zfill(5),
                "county_name": row.county_name,
                "state_name": row.state_name,
                "county_state": row.county_state,
                "application_count": row.application_count
            }
            for row in results
        ]
    except Exception as e:
        print(f"Error getting lender counties by lending activity: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_lender_target_counties(
    lender_id: str,
    data_type: str,
    years: Optional[List[int]] = None
) -> List[Dict[str, str]]:
    """
    Get target counties for a lender based on 1% threshold.
    
    A county is a target if:
    - Lender has a branch there (for branch data type), OR
    - Lender has ≥1% of their total lending in that county (for HMDA or SB)
    
    Args:
        lender_id: LEI (for HMDA), respondent_id (for SB), or RSSD (for branches)
        data_type: 'hmda', 'sb', or 'branches'
        years: Optional list of years to consider
    
    Returns:
        List of dictionaries with county information (geoid5, county_state, etc.)
    """
    if not lender_id:
        return []
    
    client = get_bigquery_client()
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    # Default to recent years if not specified
    if not years:
        if data_type == 'hmda':
            years = DataExplorerConfig.HMDA_YEARS[-3:]  # Last 3 years
        elif data_type == 'sb':
            years = DataExplorerConfig.SB_YEARS[-3:]  # Last 3 years
        else:
            years = DataExplorerConfig.BRANCH_YEARS[-1:]  # Most recent year
    
    # Validate years input
    if years:
        # Limit to reasonable number of years
        MAX_YEARS = 20
        if len(years) > MAX_YEARS:
            logger.warning(f"Too many years requested ({len(years)}), limiting to {MAX_YEARS}")
            years = years[:MAX_YEARS]
        # Validate year values
        valid_years = [y for y in years if isinstance(y, int) and 2000 <= y <= 2100]
        if len(valid_years) != len(years):
            logger.warning(f"Some invalid years filtered out: {years} -> {valid_years}")
        years = valid_years
    
    if data_type == 'branches':
        logger.debug(f"get_lender_target_counties called for branches: RSSD={lender_id}, years={years}")
        
        # For lender analysis, always use 2025 data (current branch network)
        # For area analysis, use the requested years
        # Determine which table(s) to use based on requested years
        # sod_legacy has years 2017-2024, sod25 has year 2025
        legacy_years = [y for y in years if y < 2025] if years else []
        sod25_years = [y for y in years if y >= 2025] if years else []
        
        # Use sod_legacy for historical years, sod25 for 2025+
        branch_table = DataExplorerConfig.BRANCHES_TABLE
        if legacy_years and not sod25_years:
            # Only historical years - use sod_legacy
            branch_table = 'sod_legacy'
        elif sod25_years and not legacy_years:
            # Only 2025+ - use sod25
            branch_table = DataExplorerConfig.BRANCHES_TABLE
        elif legacy_years and sod25_years:
            # Both - we'll need to query both tables and union
            branch_table = 'both'
        elif not years:
            # No years specified - default to 2025 for lender analysis
            branch_table = DataExplorerConfig.BRANCHES_TABLE
            years = [2025]
        
        logger.debug(f"Using branch table: {branch_table}, legacy_years={legacy_years}, sod25_years={sod25_years}")
        
        # Execute with parameterized query
        try:
            # Build query parameters - use array parameter for years
            query_params = [
                    ScalarQueryParameter("rssd", "STRING", str(lender_id).strip())
                ]
            
            # Add years as array parameter
            if years:
                year_strings = [str(y) for y in years]
                query_params.append(ArrayQueryParameter("years", "STRING", year_strings))
            
            job_config = QueryJobConfig(query_parameters=query_params)
            
            # First check: Does this RSSD exist at all?
            # Check in the appropriate table(s)
            if branch_table == 'both':
                # Check both tables
                check_query = f"""
                SELECT COUNT(*) as branch_count,
                       COUNT(DISTINCT CAST(b.year AS STRING)) as year_count,
                       STRING_AGG(DISTINCT CAST(b.year AS STRING), ', ' ORDER BY CAST(b.year AS STRING)) as available_years,
                       COUNT(DISTINCT b.geoid5) as unique_counties
                FROM (
                    SELECT year, geoid5 FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.sod_legacy` WHERE CAST(rssd AS STRING) = @rssd
                    UNION ALL
                    SELECT year, geoid5 FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}` WHERE CAST(rssd AS STRING) = @rssd
                ) b
                """
            else:
                check_query = f"""
                SELECT COUNT(*) as branch_count,
                       COUNT(DISTINCT CAST(b.year AS STRING)) as year_count,
                       STRING_AGG(DISTINCT CAST(b.year AS STRING), ', ' ORDER BY CAST(b.year AS STRING)) as available_years,
                       COUNT(DISTINCT b.geoid5) as unique_counties
                FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{branch_table}` b
                WHERE CAST(b.rssd AS STRING) = @rssd
                """
            check_job = client.query(check_query, job_config=job_config)
            check_results = list(check_job.result())
            
            with open(debug_file, 'a') as f:
                if check_results and check_results[0].branch_count > 0:
                    f.write(f"[DEBUG] RSSD {lender_id} exists in branch table:\n")
                    f.write(f"  - Total branches: {check_results[0].branch_count}\n")
                    f.write(f"  - Unique counties: {check_results[0].unique_counties}\n")
                    f.write(f"  - Years with data: {check_results[0].available_years}\n")
                    f.write(f"  - Requested years: {years}\n")
                else:
                    f.write(f"[DEBUG] RSSD {lender_id} not found in branch table at all\n")
                    f.flush()
                    return []
                f.flush()
            
            # Now check branches in the requested years
            years_in_query = f"('{years_list}')"
            
            with open(debug_file, 'a') as f:
                f.write(f"[DEBUG] Querying with years: {years_in_query}\n")
                f.write(f"[DEBUG] Years list format: {years_list}\n")
                f.flush()
            
            # For branches, return all counties where lender has at least 1 branch
            # (No 1% threshold - branch locations should show all operating counties)
            # Use parameterized query to prevent SQL injection
            # Note: geoid5 needs to be padded to 5 digits for proper matching
            if branch_table == 'both':
                # Query both tables and union
                query = f"""
                WITH lender_branches AS (
                    SELECT DISTINCT
                        LPAD(CAST(b.geoid5 AS STRING), 5, '0') as geoid5
                    FROM (
                        SELECT geoid5 FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.sod_legacy` 
                        WHERE CAST(rssd AS STRING) = @rssd
                            AND CAST(year AS STRING) IN {years_in_query}
                            AND geoid5 IS NOT NULL
                        UNION DISTINCT
                        SELECT geoid5 FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}` 
                        WHERE CAST(rssd AS STRING) = @rssd
                            AND CAST(year AS STRING) IN {years_in_query}
                            AND geoid5 IS NOT NULL
                    ) b
                )
                SELECT DISTINCT
                    LPAD(CAST(c.geoid5 AS STRING), 5, '0') as geoid5,
                    c.County as county_name,
                    c.State as state_name,
                    CONCAT(c.County, ', ', c.State) as county_state
                FROM lender_branches lb
                JOIN `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}` c
                    ON lb.geoid5 = LPAD(CAST(c.geoid5 AS STRING), 5, '0')
                ORDER BY c.State, c.County
                """
            else:
                query = f"""
                WITH lender_branches AS (
                    SELECT DISTINCT
                        LPAD(CAST(b.geoid5 AS STRING), 5, '0') as geoid5
                    FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{branch_table}` b
                    WHERE CAST(b.rssd AS STRING) = @rssd
                        AND CAST(b.year AS STRING) IN {years_in_query}
                        AND b.geoid5 IS NOT NULL
                )
                SELECT DISTINCT
                    LPAD(CAST(c.geoid5 AS STRING), 5, '0') as geoid5,
                    c.County as county_name,
                    c.State as state_name,
                    CONCAT(c.County, ', ', c.State) as county_state
                FROM lender_branches lb
                JOIN `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}` c
                    ON lb.geoid5 = LPAD(CAST(c.geoid5 AS STRING), 5, '0')
                ORDER BY c.State, c.County
                """
            
            with open(debug_file, 'a') as f:
                f.write(f"[DEBUG] Executing query for counties...\n")
                f.write(f"[DEBUG] Full SQL query (with RSSD placeholder):\n")
                f.write(query.replace("@rssd", f"'{lender_id}'") + "\n")
                f.flush()
            
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            
            counties = []
            for row in results:
                counties.append({
                    'geoid5': str(row.geoid5).zfill(5),  # Ensure 5-digit format
                    'county_name': row.county_name,
                    'state_name': row.state_name,
                    'county_state': row.county_state
                })
            
            with open(debug_file, 'a') as f:
                f.write(f"[DEBUG] Found {len(counties)} counties for RSSD {lender_id} in years {years}\n")
                f.flush()
            
            # If no counties found, try a simpler query without the join to see if we have geoid5s
            if len(counties) == 0:
                if branch_table == 'both':
                    simple_query = f"""
                    SELECT DISTINCT
                        LPAD(CAST(b.geoid5 AS STRING), 5, '0') as geoid5,
                        COUNT(*) as branch_count
                    FROM (
                        SELECT geoid5 FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.sod_legacy` 
                        WHERE CAST(rssd AS STRING) = @rssd
                            AND CAST(year AS STRING) IN {years_in_query}
                            AND geoid5 IS NOT NULL
                        UNION ALL
                        SELECT geoid5 FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}` 
                        WHERE CAST(rssd AS STRING) = @rssd
                            AND CAST(year AS STRING) IN {years_in_query}
                            AND geoid5 IS NOT NULL
                    ) b
                    GROUP BY geoid5
                    ORDER BY branch_count DESC
                    LIMIT 10
                    """
                else:
                    simple_query = f"""
                    SELECT DISTINCT
                        LPAD(CAST(b.geoid5 AS STRING), 5, '0') as geoid5,
                        COUNT(*) as branch_count
                    FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{branch_table}` b
                    WHERE CAST(b.rssd AS STRING) = @rssd
                        AND CAST(b.year AS STRING) IN {years_in_query}
                        AND b.geoid5 IS NOT NULL
                    GROUP BY geoid5
                    ORDER BY branch_count DESC
                    LIMIT 10
                    """
                simple_job = client.query(simple_query, job_config=job_config)
                simple_results = list(simple_job.result())
                with open(debug_file, 'a') as f:
                    if simple_results:
                        f.write(f"[DEBUG] Found {len(simple_results)} geoid5s in branch table (without join):\n")
                        for r in simple_results[:5]:
                            f.write(f"  - geoid5: {r.geoid5}, branches: {r.branch_count}\n")
                    else:
                        f.write(f"[DEBUG] No branches found in selected years {years} for RSSD {lender_id}\n")
                    f.flush()
            return counties
        except Exception as e:
            print(f"Error querying branch locations for RSSD {lender_id}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    elif data_type == 'hmda':
        # For HMDA, calculate total lending and county-level lending, filter by 1% threshold
        query = f"""
        WITH lender_lending AS (
            SELECT 
                CONCAT(LPAD(CAST(h.state_code AS STRING), 2, '0'), LPAD(CAST(h.county_code AS STRING), 3, '0')) as geoid5,
                COUNT(*) as county_loans,
                SUM(h.loan_amount) as county_amount
            FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
            WHERE h.lei = @lei
                AND CAST(h.activity_year AS STRING) IN ('{years_list}')
                AND h.state_code IS NOT NULL
                AND h.county_code IS NOT NULL
            GROUP BY geoid5
        ),
        total_lending AS (
            SELECT 
                SUM(county_loans) as total_loans,
                SUM(county_amount) as total_amount
            FROM lender_lending
        ),
        county_percentages AS (
            SELECT 
                ll.geoid5,
                ll.county_loans,
                ll.county_amount,
                SAFE_DIVIDE(ll.county_loans, tl.total_loans) * 100 as pct_loans,
                SAFE_DIVIDE(ll.county_amount, tl.total_amount) * 100 as pct_amount
            FROM lender_lending ll
            CROSS JOIN total_lending tl
        )
        SELECT DISTINCT
            CAST(cp.geoid5 AS STRING) as geoid5,
            c.County as county_name,
            c.State as state_name,
            CONCAT(c.County, ', ', c.State) as county_state,
            cp.county_loans,
            cp.pct_loans
        FROM county_percentages cp
        JOIN `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}` c
            ON cp.geoid5 = CAST(c.geoid5 AS STRING)
        WHERE cp.pct_loans >= 1.0 OR cp.pct_amount >= 1.0
        ORDER BY c.State, c.County
        """
        
        # Execute with parameterized query
        try:
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("lei", "STRING", str(lender_id).strip())
                ]
            )
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            
            counties = []
            for row in results:
                counties.append({
                    'geoid5': str(row.geoid5),
                    'county_name': row.county_name,
                    'state_name': row.state_name,
                    'county_state': row.county_state,
                    'county_loans': row.county_loans,
                    'pct_loans': row.pct_loans
                })
            
            return counties
        except Exception as e:
            print(f"Error querying HMDA target counties for LEI {lender_id}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    elif data_type == 'sb':
        # For Small Business, calculate total lending and county-level lending, filter by 1% threshold
        query = f"""
        WITH lender_lending AS (
            SELECT 
                CAST(d.geoid5 AS STRING) as geoid5,
                SUM(d.numsbrev_under_1m) as county_loans,
                SUM(d.amtsbrev_under_1m) as county_amount
            FROM `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_DISCLOSURE_TABLE}` d
            WHERE (d.respondent_id = '{lender_id}' OR d.respondent_id = CONCAT('0', '{lender_id}'))
                AND CAST(d.year AS INT64) IN ({', '.join([str(y) for y in years])})
                AND d.geoid5 IS NOT NULL
            GROUP BY geoid5
        ),
        total_lending AS (
            SELECT 
                SUM(county_loans) as total_loans,
                SUM(county_amount) as total_amount
            FROM lender_lending
        ),
        county_percentages AS (
            SELECT 
                ll.geoid5,
                ll.county_loans,
                ll.county_amount,
                SAFE_DIVIDE(ll.county_loans, tl.total_loans) * 100 as pct_loans,
                SAFE_DIVIDE(ll.county_amount, tl.total_amount) * 100 as pct_amount
            FROM lender_lending ll
            CROSS JOIN total_lending tl
        )
        SELECT DISTINCT
            CAST(cp.geoid5 AS STRING) as geoid5,
            c.County as county_name,
            c.State as state_name,
            CONCAT(c.County, ', ', c.State) as county_state,
            cp.county_loans,
            cp.pct_loans
        FROM county_percentages cp
        JOIN `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}` c
            ON cp.geoid5 = CAST(c.geoid5 AS STRING)
        WHERE cp.pct_loans >= 1.0 OR cp.pct_amount >= 1.0
        ORDER BY c.State, c.County
        """
    
    else:
        return []
    
    try:
        query_job = client.query(query)
        results = query_job.result()
        return [
            {
                "geoid5": str(row.geoid5).zfill(5),
                "county_name": row.county_name,
                "state_name": row.state_name,
                "county_state": row.county_state,
                "county_loans": getattr(row, 'county_loans', None),
                "pct_loans": getattr(row, 'pct_loans', None)
            }
            for row in results
        ]
    except Exception as e:
        print(f"Error getting lender target counties: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_available_branch_banks(geoids: Optional[List[str]] = None, years: Optional[List[int]] = None) -> List[Dict[str, str]]:
    """Get list of available banks with branches, optionally filtered by geography and years."""
    client = get_bigquery_client()
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    where_conditions = []
    
    if geoids:
        geoid5_list = "', '".join([str(g).zfill(5) for g in geoids])
        where_conditions.append(f"CAST(geoid5 AS STRING) IN ('{geoid5_list}')")
    
    if years:
        years_list = "', '".join([str(y) for y in years])
        where_conditions.append(f"CAST(year AS STRING) IN ('{years_list}')")
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    query = f"""
    SELECT DISTINCT
        CAST(rssd AS STRING) as rssd,
        bank_name,
        COUNT(*) as branch_count
    FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}`
    WHERE {where_clause}
    GROUP BY rssd, bank_name
    HAVING branch_count > 0
    ORDER BY branch_count DESC
    LIMIT 1000
    """
    
    query_job = client.query(query)
    results = query_job.result()
    return [
        {
            "rssd": str(row.rssd),
            "name": row.bank_name,
            "branch_count": row.branch_count
        }
        for row in results
    ]


def get_hmda_lenders_from_lenders18() -> List[Dict[str, str]]:
    """
    Get all lenders from HMDA lenders18 table with their names and LEIs.
    
    Returns:
        List of dictionaries with 'name' and 'lei' keys, sorted by name
    """
    client = get_bigquery_client()
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    try:
        query = f"""
        SELECT DISTINCT
            lei,
            respondent_name as name
        FROM `{project_id}.hmda.lenders18`
        WHERE respondent_name IS NOT NULL
            AND lei IS NOT NULL
        ORDER BY respondent_name
        """
        query_job = client.query(query)
        results = query_job.result()
        
        lenders = []
        for row in results:
            lenders.append({
                'name': row.name.strip() if row.name else '',
                'lei': row.lei
            })
        
        return lenders
    except Exception as e:
        print(f"Error fetching HMDA lenders from lenders18: {e}")
        return []


def get_lender_identifiers_by_lei(lei: str) -> Dict[str, Any]:
    """
    Get all associated identifiers (RSSD, Business Respondent ID) for a given LEI.
    
    Args:
        lei: Legal Entity Identifier (20 characters)
    
    Returns:
        Dictionary with lei, name, rssd, and respondent_id
    """
    client = get_bigquery_client()
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    result = {
        'lei': lei,
        'name': None,
        'rssd': None,
        'respondent_id': None
    }
    
    lei_clean = lei.strip().upper()
    if len(lei_clean) != 20:
        return result
    
    # First, get the lender name, city, state, and type from HMDA lenders18
    try:
        query = f"""
        SELECT DISTINCT
            lei,
            respondent_name,
            respondent_city,
            respondent_state,
            type_name
        FROM `{project_id}.hmda.lenders18`
        WHERE lei = @lei
        LIMIT 1
        """
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("lei", "STRING", lei_clean)
            ]
        )
        query_job = client.query(query, job_config=job_config)
        hmda_results = list(query_job.result())
        if hmda_results:
            row = hmda_results[0]
            result['name'] = row.respondent_name.strip() if row.respondent_name else None
            result['city'] = row.respondent_city.strip() if row.respondent_city else None
            result['state'] = row.respondent_state.strip() if row.respondent_state else None
            result['lender_type'] = row.type_name.strip() if row.type_name else None
    except Exception as e:
        print(f"Error looking up LEI in HMDA: {e}")
        # If columns don't exist, try without them
        try:
            query = f"""
            SELECT DISTINCT
                lei,
                respondent_name
            FROM `{project_id}.hmda.lenders18`
            WHERE lei = @lei
            LIMIT 1
            """
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("lei", "STRING", lei_clean)
                ]
            )
            query_job = client.query(query, job_config=job_config)
            hmda_results = list(query_job.result())
            if hmda_results:
                result['name'] = hmda_results[0].respondent_name.strip() if hmda_results[0].respondent_name else None
        except Exception as e2:
            print(f"Error in fallback lookup: {e2}")
    
    # Try to find RSSD by matching lender name in branch data
    if result['name']:
        try:
            # Clean name for matching (remove common suffixes and normalize)
            name_clean = result['name'].upper().strip()
            # Remove common suffixes
            for suffix in [' INC', ' INC.', ' LLC', ' L.L.C.', ' CORP', ' CORP.', ' CORPORATION', ' BANK', ' BANKING', ' NA', ' N.A.']:
                if name_clean.endswith(suffix):
                    name_clean = name_clean[:-len(suffix)].strip()
            
            query = f"""
            SELECT DISTINCT
                CAST(rssd AS STRING) as rssd,
                bank_name
            FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}`
            WHERE UPPER(TRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(bank_name, ' INC', ''), ' INC.', ''), ' LLC', ''), ' L.L.C.', ''), ' CORP', ''), ' CORP.', ''), ' CORPORATION', ''))) LIKE @name_pattern
            LIMIT 1
            """
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("name_pattern", "STRING", f"%{name_clean}%")
                ]
            )
            query_job = client.query(query, job_config=job_config)
            branch_results = list(query_job.result())
            if branch_results:
                result['rssd'] = str(branch_results[0].rssd)
                print(f"[DEBUG] Found RSSD {result['rssd']} for lender name '{result['name']}' (cleaned: '{name_clean}')")
            else:
                print(f"[DEBUG] No RSSD found for lender name '{result['name']}' (cleaned: '{name_clean}')")
        except Exception as e:
            print(f"Error looking up RSSD by name: {e}")
            import traceback
            traceback.print_exc()
        
        # Try to find Business Respondent ID by matching lender name in small business data
        try:
            name_clean = result['name'].upper().strip()
            # Remove common suffixes
            for suffix in [' INC', ' INC.', ' LLC', ' L.L.C.', ' CORP', ' CORP.', ' CORPORATION', ' BANK', ' BANKING', ' NA', ' N.A.']:
                if name_clean.endswith(suffix):
                    name_clean = name_clean[:-len(suffix)].strip()
            
            query = f"""
            SELECT DISTINCT
                CAST(l.sb_resid AS STRING) as sb_resid,
                l.sb_lender
            FROM `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_LENDERS_TABLE}` l
            WHERE UPPER(TRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(l.sb_lender, ' INC', ''), ' INC.', ''), ' LLC', ''), ' L.L.C.', ''), ' CORP', ''), ' CORP.', ''), ' CORPORATION', ''))) LIKE @name_pattern
            LIMIT 1
            """
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("name_pattern", "STRING", f"%{name_clean}%")
                ]
            )
            query_job = client.query(query, job_config=job_config)
            sb_results = list(query_job.result())
            if sb_results:
                result['respondent_id'] = str(sb_results[0].sb_resid)
        except Exception as e:
            print(f"Error looking up Business Respondent ID by name: {e}")
    
    return result


def lookup_lender(
    name: Optional[str] = None,
    lei: Optional[str] = None,
    rssd: Optional[str] = None,
    respondent_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Look up lender information by any identifier (name, LEI, RSSD, or Business Respondent ID).
    
    Args:
        name: Lender name (partial match supported)
        lei: Legal Entity Identifier (20 characters)
        rssd: RSSD ID (bank identifier)
        respondent_id: Small Business Respondent ID
    
    Returns:
        Dictionary with lender information including name, lei, rssd, respondent_id, and data_type,
        or None if not found
    """
    client = get_bigquery_client()
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    result = {
        'name': None,
        'lei': None,
        'rssd': None,
        'respondent_id': None,
        'city': None,
        'state': None,
        'lender_type': None,
        'data_type': None  # 'hmda', 'sb', 'branches', or 'multiple'
    }
    
    found_sources = []
    
    # Search by LEI (HMDA)
    if lei:
        lei_clean = lei.strip().upper()
        if len(lei_clean) == 20:
            try:
                # Try to find in HMDA lenders table
                query = f"""
                SELECT DISTINCT
                    lei,
                    respondent_name,
                    respondent_city,
                    respondent_state,
                    type_name
                FROM `{project_id}.hmda.lenders18`
                WHERE lei = @lei
                LIMIT 1
                """
                job_config = QueryJobConfig(
                    query_parameters=[
                        ScalarQueryParameter("lei", "STRING", lei_clean)
                    ]
                )
                query_job = client.query(query, job_config=job_config)
                results = list(query_job.result())
                if results:
                    row = results[0]
                    result['lei'] = row.lei
                    result['name'] = row.respondent_name.strip() if row.respondent_name else None
                    result['city'] = row.respondent_city.strip() if hasattr(row, 'respondent_city') and row.respondent_city else None
                    result['state'] = row.respondent_state.strip() if hasattr(row, 'respondent_state') and row.respondent_state else None
                    result['lender_type'] = row.type_name.strip() if hasattr(row, 'type_name') and row.type_name else None
                    found_sources.append('hmda')
            except Exception as e:
                print(f"Error looking up LEI in HMDA: {e}")
    
    # Search by RSSD (Branch banks)
    if rssd:
        rssd_clean = str(rssd).strip()
        try:
            query = f"""
            SELECT DISTINCT
                CAST(rssd AS STRING) as rssd,
                bank_name
            FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}`
            WHERE CAST(rssd AS STRING) = @rssd
            LIMIT 1
            """
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("rssd", "STRING", rssd_clean)
                ]
            )
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())
            if results:
                result['rssd'] = str(results[0].rssd)
                if not result['name']:
                    result['name'] = results[0].bank_name.strip() if results[0].bank_name else None
                found_sources.append('branches')
        except Exception as e:
            print(f"Error looking up RSSD: {e}")
    
    # Search by Business Respondent ID (Small Business)
    if respondent_id:
        respondent_id_clean = str(respondent_id).strip()
        try:
            query = f"""
            SELECT DISTINCT
                d.respondent_id as sb_resid,
                l.sb_lender as lender_name
            FROM `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_LENDERS_TABLE}` l
            LEFT JOIN `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_DISCLOSURE_TABLE}` d
                ON l.sb_resid = d.respondent_id
            WHERE CAST(l.sb_resid AS STRING) = @respondent_id
            LIMIT 1
            """
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("respondent_id", "STRING", respondent_id_clean)
                ]
            )
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())
            if results:
                result['respondent_id'] = str(results[0].sb_resid)
                if not result['name']:
                    result['name'] = results[0].lender_name.strip() if results[0].lender_name else None
                found_sources.append('sb')
        except Exception as e:
            print(f"Error looking up Respondent ID: {e}")
    
    # Search by name (try all sources)
    if name:
        name_clean = name.strip().replace("'", "''")  # Escape single quotes for SQL
        # Try HMDA lenders
        try:
            query = f"""
            SELECT DISTINCT
                lei,
                respondent_name,
                respondent_city,
                respondent_state,
                type_name
            FROM `{project_id}.hmda.lenders18`
            WHERE UPPER(respondent_name) LIKE UPPER('%' || @name || '%')
            LIMIT 1
            """
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("name", "STRING", name_clean)
                ]
            )
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())
            if results:
                row = results[0]
                result['lei'] = row.lei
                result['name'] = row.respondent_name.strip() if row.respondent_name else None
                result['city'] = row.respondent_city.strip() if hasattr(row, 'respondent_city') and row.respondent_city else None
                result['state'] = row.respondent_state.strip() if hasattr(row, 'respondent_state') and row.respondent_state else None
                result['lender_type'] = row.type_name.strip() if hasattr(row, 'type_name') and row.type_name else None
                if 'hmda' not in found_sources:
                    found_sources.append('hmda')
        except Exception as e:
            print(f"Error looking up name in HMDA: {e}")
        
        # Try Branch banks
        try:
            query = f"""
            SELECT DISTINCT
                CAST(rssd AS STRING) as rssd,
                bank_name
            FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}`
            WHERE UPPER(bank_name) LIKE UPPER('%' || @name || '%')
            LIMIT 1
            """
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("name", "STRING", name_clean)
                ]
            )
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())
            if results:
                result['rssd'] = str(results[0].rssd)
                if not result['name']:
                    result['name'] = results[0].bank_name.strip() if results[0].bank_name else None
                if 'branches' not in found_sources:
                    found_sources.append('branches')
        except Exception as e:
            print(f"Error looking up name in branches: {e}")
        
        # Try Small Business lenders
        try:
            query = f"""
            SELECT DISTINCT
                CAST(l.sb_resid AS STRING) as sb_resid,
                l.sb_lender as lender_name
            FROM `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_LENDERS_TABLE}` l
            WHERE UPPER(l.sb_lender) LIKE UPPER('%' || @name || '%')
            LIMIT 1
            """
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("name", "STRING", name_clean)
                ]
            )
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())
            if results:
                result['respondent_id'] = str(results[0].sb_resid)
                if not result['name']:
                    result['name'] = results[0].lender_name.strip() if results[0].lender_name else None
                if 'sb' not in found_sources:
                    found_sources.append('sb')
        except Exception as e:
            print(f"Error looking up name in SB: {e}")
    
    # Determine data_type
    if len(found_sources) == 1:
        result['data_type'] = found_sources[0]
    elif len(found_sources) > 1:
        result['data_type'] = 'multiple'
    
    # Return result if we found at least one identifier
    if result['name'] or result['lei'] or result['rssd'] or result['respondent_id']:
        return result
    
    return None


def execute_query(query: str) -> List[Dict[str, Any]]:
    """Execute a BigQuery query and return results as list of dictionaries."""
    import logging
    logger = logging.getLogger(__name__)
    
    client = get_bigquery_client()
    
    # Log the query for monitoring/debugging
    logger.info("=" * 80)
    logger.info("EXECUTING BIGQUERY QUERY:")
    logger.info("=" * 80)
    logger.info(query)
    logger.info("=" * 80)
    
    # Also write to a query log file for easy comparison
    query_log_file = REPO_ROOT / 'dataexplorer_bigquery_queries.log'
    with open(query_log_file, 'a', encoding='utf-8') as f:
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"QUERY EXECUTED AT: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n")
        f.write(query + "\n")
        f.write("=" * 80 + "\n\n")
    
    query_job = client.query(query)
    results = query_job.result()
    
    # Log query statistics
    logger.info(f"Query job ID: {query_job.job_id}")
    logger.info(f"Query bytes processed: {query_job.total_bytes_processed if hasattr(query_job, 'total_bytes_processed') else 'N/A'}")
    logger.info(f"Query bytes billed: {query_job.total_bytes_billed if hasattr(query_job, 'total_bytes_billed') else 'N/A'}")
    
    # Convert to list of dictionaries
    rows = []
    row_count = 0
    for row in results:
        row_dict = {}
        for key, value in row.items():
            row_dict[key] = value
        rows.append(row_dict)
        row_count += 1
    
    logger.info(f"Query returned {row_count} rows")
    
    return rows


def aggregate_hmda_data(data: List[Dict[str, Any]], group_by: List[str] = None) -> Dict[str, Any]:
    """Aggregate HMDA data by specified dimensions."""
    if not data:
        return {'data': [], 'total_rows': 0}
    
    if group_by is None:
        group_by = ['activity_year', 'lei']
    
    # Simple aggregation - in production, this would be more sophisticated
    aggregated = {}
    
    for row in data:
        key = tuple(str(row.get(g, '')) for g in group_by)
        if key not in aggregated:
            aggregated[key] = {
                'loan_count': 0,
                'total_amount': 0,
                'lmict_loans': 0,
                'lmib_loans': 0,
                'mmct_loans': 0,
                'hispanic_loans': 0,
                'black_loans': 0,
                'asian_loans': 0,
                **{g: row.get(g) for g in group_by}
            }
        
        agg = aggregated[key]
        agg['loan_count'] += 1
        agg['total_amount'] += row.get('loan_amount', 0) or 0
        if row.get('is_lmict'):
            agg['lmict_loans'] += 1
        if row.get('is_lmib'):
            agg['lmib_loans'] += 1
        if row.get('is_mmct'):
            agg['mmct_loans'] += 1
        if row.get('is_hispanic'):
            agg['hispanic_loans'] += 1
        if row.get('is_black'):
            agg['black_loans'] += 1
        if row.get('is_asian'):
            agg['asian_loans'] += 1
    
    # Convert to list and calculate percentages
    result = []
    for key, agg in aggregated.items():
        agg['lmict_percentage'] = (agg['lmict_loans'] / agg['loan_count'] * 100) if agg['loan_count'] > 0 else 0
        agg['lmib_percentage'] = (agg['lmib_loans'] / agg['loan_count'] * 100) if agg['loan_count'] > 0 else 0
        agg['mmct_percentage'] = (agg['mmct_loans'] / agg['loan_count'] * 100) if agg['loan_count'] > 0 else 0
        result.append(agg)
    
    return {'data': result, 'total_rows': len(data)}


def aggregate_sb_data(data: List[Dict[str, Any]], group_by: List[str] = None) -> Dict[str, Any]:
    """Aggregate Small Business data by specified dimensions."""
    if not data:
        return {'data': [], 'total_rows': 0}
    
    if group_by is None:
        group_by = ['year', 'sb_resid']
    
    aggregated = {}
    
    for row in data:
        key = tuple(str(row.get(g, '')) for g in group_by)
        if key not in aggregated:
            aggregated[key] = {
                'sb_loans_count': 0,
                'sb_loans_amount': 0,
                'lmict_loans_count': 0,
                'lmict_loans_amount': 0,
                **{g: row.get(g) for g in group_by}
            }
        
        agg = aggregated[key]
        agg['sb_loans_count'] += row.get('sb_loans_count', 0) or 0
        agg['sb_loans_amount'] += row.get('sb_loans_amount', 0) or 0
        agg['lmict_loans_count'] += row.get('lmict_loans_count', 0) or 0
        agg['lmict_loans_amount'] += row.get('lmict_loans_amount', 0) or 0
    
    result = list(aggregated.values())
    return {'data': result, 'total_rows': len(data)}


def aggregate_branch_data(data: List[Dict[str, Any]], group_by: List[str] = None) -> Dict[str, Any]:
    """Aggregate Branch data by specified dimensions."""
    if not data:
        return {'data': [], 'total_rows': 0}
    
    if group_by is None:
        group_by = ['year', 'rssd']
    
    aggregated = {}
    
    for row in data:
        key = tuple(str(row.get(g, '')) for g in group_by)
        if key not in aggregated:
            aggregated[key] = {
                'branch_count': 0,
                'total_deposits': 0,
                'lmi_branches': 0,
                'mmct_branches': 0,
                **{g: row.get(g) for g in group_by}
            }
        
        agg = aggregated[key]
        agg['branch_count'] += 1
        agg['total_deposits'] += row.get('deposits', 0) or 0
        if row.get('is_lmi_tract'):
            agg['lmi_branches'] += 1
        if row.get('is_mmct_tract'):
            agg['mmct_branches'] += 1
    
    result = list(aggregated.values())
    return {'data': result, 'total_rows': len(data)}

